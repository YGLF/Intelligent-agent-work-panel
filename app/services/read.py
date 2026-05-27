from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.models.agent import RunAgent
from app.models.log import RunAgentLog
from app.models.risk import RunRisk
from app.models.run import Run
from app.schemas.read import AgentDetailRead, AgentListItemRead, AgentListRead, RiskItemRead, RiskListRead, RunMonitorItemRead, RunMonitorRead, RunOverviewRead, TimelineItemRead, TimelineRead
from scripts.codex_sync_projects import get_codex_inventory_counts


def _get_run_or_none(db: Session, run_id: int) -> Run | None:
    return db.get(Run, run_id)


def get_run_overview(db: Session, run_id: int) -> RunOverviewRead | None:
    run = _get_run_or_none(db, run_id)
    if run is None:
        return None

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    agent_rows = db.scalars(select(RunAgent).where(RunAgent.run_id == run_id)).all()

    total_agents = len(agent_rows)
    running_count = sum(1 for agent in agent_rows if agent.status.value == "running")
    completed_count = sum(1 for agent in agent_rows if agent.status.value == "completed")
    blocked_count = sum(1 for agent in agent_rows if agent.status.value == "blocked")
    failed_count = sum(1 for agent in agent_rows if agent.status.value == "failed")
    overall_progress = int(sum(agent.progress_percent for agent in agent_rows) / total_agents) if total_agents else 0

    phase_distribution: dict[str, int] = {}
    active_updates_last_1h = 0
    latest_agent_update: datetime | None = None
    for agent in agent_rows:
        if agent.phase is not None:
            phase_distribution[agent.phase.value] = phase_distribution.get(agent.phase.value, 0) + 1
        if agent.last_update_at is not None:
            if latest_agent_update is None or agent.last_update_at > latest_agent_update:
                latest_agent_update = agent.last_update_at
            candidate = agent.last_update_at
            if candidate.tzinfo is None:
                candidate = candidate.replace(tzinfo=timezone.utc)
            if candidate >= one_hour_ago:
                active_updates_last_1h += 1

    last_active_at = run.last_activity_at or latest_agent_update
    return RunOverviewRead(
        run_id=run.id,
        run_code=run.run_code,
        run_name=run.run_name,
        source_type=run.source_type,
        run_status=run.status,
        total_agents=total_agents,
        running_count=running_count,
        completed_count=completed_count,
        blocked_count=blocked_count,
        failed_count=failed_count,
        phase_distribution=phase_distribution,
        overall_progress=overall_progress,
        active_updates_last_1h=active_updates_last_1h,
        last_active_at=last_active_at,
        stale_hint=None,
    )


def _apply_agent_filters(
    stmt: Select,
    *,
    status: str | None,
    phase: str | None,
    owner_scope: str | None,
    risk_level: str | None,
    blocked_only: bool,
) -> Select:
    if status:
        stmt = stmt.where(RunAgent.status == status)
    if phase:
        stmt = stmt.where(RunAgent.phase == phase)
    if owner_scope:
        stmt = stmt.where(RunAgent.owner_scope == owner_scope)
    if risk_level:
        stmt = stmt.where(RunAgent.risk_level == risk_level)
    if blocked_only:
        stmt = stmt.where(RunAgent.status == "blocked")
    return stmt


def list_run_agents(
    db: Session,
    run_id: int,
    *,
    status: str | None,
    phase: str | None,
    owner_scope: str | None,
    risk_level: str | None,
    blocked_only: bool,
) -> tuple[Run | None, AgentListRead | None]:
    run = _get_run_or_none(db, run_id)
    if run is None:
        return None, None

    stmt = select(RunAgent).where(RunAgent.run_id == run_id).order_by(RunAgent.id.asc())
    stmt = _apply_agent_filters(
        stmt,
        status=status,
        phase=phase,
        owner_scope=owner_scope,
        risk_level=risk_level,
        blocked_only=blocked_only,
    )
    agents = db.scalars(stmt).all()
    items = [AgentListItemRead.model_validate(agent) for agent in agents]
    return run, AgentListRead(items=items)


def get_agent_detail(db: Session, run_id: int, agent_id: int) -> AgentDetailRead | None:
    stmt = select(RunAgent).where(RunAgent.id == agent_id, RunAgent.run_id == run_id)
    agent = db.scalar(stmt)
    if agent is None:
        return None

    return AgentDetailRead(
        **AgentListItemRead.model_validate(agent).model_dump(),
        depends_on=agent.depends_on_json,
        started_at=agent.started_at,
        finished_at=agent.finished_at,
    )


def get_run_timeline(db: Session, run_id: int) -> tuple[Run | None, TimelineRead | None]:
    run = _get_run_or_none(db, run_id)
    if run is None:
        return None, None

    logs = db.scalars(
        select(RunAgentLog)
        .where(RunAgentLog.run_id == run_id)
        .order_by(RunAgentLog.occurred_at.desc(), RunAgentLog.id.desc())
    ).all()
    items = [TimelineItemRead.model_validate(item) for item in logs]
    return run, TimelineRead(items=items)


def get_run_risks(db: Session, run_id: int) -> tuple[Run | None, RiskListRead | None]:
    run = _get_run_or_none(db, run_id)
    if run is None:
        return None, None

    risks = db.scalars(
        select(RunRisk)
        .where(RunRisk.run_id == run_id)
        .order_by(RunRisk.updated_at.desc(), RunRisk.id.desc())
    ).all()
    items = [RiskItemRead.model_validate(item) for item in risks]
    return run, RiskListRead(items=items)


def _count_subagents(agent_rows: list[RunAgent]) -> int:
    return sum(1 for agent in agent_rows if not agent.is_main_agent)


def get_run_monitor(db: Session) -> RunMonitorRead:
    runs = db.scalars(
        select(Run).order_by(
            case((Run.last_activity_at.is_(None), 1), else_=0).asc(),
            Run.last_activity_at.desc(),
            Run.updated_at.desc(),
            Run.id.desc(),
        )
    ).all()

    now = datetime.now(timezone.utc)
    items: list[RunMonitorItemRead] = []
    recent_active_runs: list[RunMonitorItemRead] = []
    blocked_runs: list[RunMonitorItemRead] = []
    total_agents = 0
    total_subagents = 0
    total_blocked_agents = 0
    active_runs = 0

    for run in runs:
        agent_rows = db.scalars(select(RunAgent).where(RunAgent.run_id == run.id)).all()
        overview = get_run_overview(db, run.id)
        if overview is None:
            continue
        agents = [AgentListItemRead.model_validate(agent) for agent in agent_rows]
        main_agents = [AgentListItemRead.model_validate(agent) for agent in agent_rows if agent.is_main_agent]
        child_agents = [AgentListItemRead.model_validate(agent) for agent in agent_rows if not agent.is_main_agent]
        subagent_count = _count_subagents(agent_rows)
        total_agents += overview.total_agents
        total_subagents += subagent_count
        total_blocked_agents += overview.blocked_count
        if overview.running_count or overview.blocked_count or overview.active_updates_last_1h:
            active_runs += 1
        items.append(
            RunMonitorItemRead(
                run_id=overview.run_id,
                run_code=overview.run_code,
                run_name=overview.run_name,
                source_type=overview.source_type,
                run_status=overview.run_status,
                total_agents=overview.total_agents,
                running_count=overview.running_count,
                completed_count=overview.completed_count,
                blocked_count=overview.blocked_count,
                failed_count=overview.failed_count,
                subagent_count=subagent_count,
                phase_distribution=overview.phase_distribution,
                overall_progress=overview.overall_progress,
                active_updates_last_1h=overview.active_updates_last_1h,
                last_active_at=overview.last_active_at,
                agents=agents,
                main_agents=main_agents,
                child_agents=child_agents,
            )
        )

    recent_active_runs = sorted(items, key=lambda item: item.last_active_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:5]
    blocked_runs = [item for item in items if item.blocked_count > 0]
    codex_session_count, codex_workspace_count = get_codex_inventory_counts()
    return RunMonitorRead(
        items=items,
        total_runs=len(runs),
        active_runs=active_runs,
        codex_session_count=codex_session_count,
        codex_workspace_count=codex_workspace_count,
        recent_active_runs=recent_active_runs,
        blocked_runs=blocked_runs,
        total_agents=total_agents,
        total_subagents=total_subagents,
        total_blocked_agents=total_blocked_agents,
        last_refresh_at=now,
    )
