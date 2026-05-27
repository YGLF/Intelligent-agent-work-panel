from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models.enums import RunSourceType, RunStatus
from app.models.run import Run


CODEX_HOME = Path.home() / ".codex"
SESSION_INDEX = CODEX_HOME / "session_index.jsonl"
GLOBAL_STATE = CODEX_HOME / ".codex-global-state.json"


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_session_index() -> dict[str, dict]:
    sessions: dict[str, dict] = {}
    if not SESSION_INDEX.exists():
        return sessions

    for line in SESSION_INDEX.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = item.get("id")
        if not session_id:
            continue
        sessions[session_id] = {
            "id": session_id,
            "thread_name": item.get("thread_name") or session_id,
            "updated_at": _parse_datetime(item.get("updated_at")),
        }
    return sessions


def _read_active_workspace_roots() -> list[str]:
    if not GLOBAL_STATE.exists():
        return []
    try:
        payload = json.loads(GLOBAL_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    roots = payload.get("active-workspace-roots")
    if not isinstance(roots, list):
        return []
    return [str(root) for root in roots if root]


def _workspace_run_code(root: str) -> str:
    normalized = str(Path(root).resolve()).lower().replace("\\", "/")
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"codex-workspace-{digest}"


def _dedupe_runs(db: SessionLocal) -> None:
    seen: dict[str, int] = {}
    runs = db.scalars(select(Run).where(Run.run_code.like("codex-session-%") | Run.run_code.like("codex-workspace-%")).order_by(Run.id.asc())).all()
    for run in runs:
        if run.run_code in seen:
            db.delete(run)
        else:
            seen[run.run_code] = run.id


def sync_codex_projects(limit: int = 200) -> tuple[int, int]:
    sessions = sorted(
        _read_session_index().values(),
        key=lambda item: item["updated_at"],
        reverse=True,
    )[:limit]
    active_workspace_roots = _read_active_workspace_roots()

    db = SessionLocal()
    created = 0
    updated = 0
    try:
        _dedupe_runs(db)
        for session in sessions:
            run_code = f"codex-session-{session['id']}"
            run = db.scalar(select(Run).where(Run.run_code == run_code))
            if run is None:
                run = Run(
                    run_code=run_code,
                    run_name=session["thread_name"],
                    source_type=RunSourceType.CODEX,
                    status=RunStatus.RUNNING,
                    started_at=session["updated_at"],
                    last_activity_at=session["updated_at"],
                    created_by="codex-local-sync",
                )
                db.add(run)
                created += 1
            else:
                run.run_name = session["thread_name"]
                run.source_type = RunSourceType.CODEX
                run.last_activity_at = session["updated_at"]
                updated += 1

        for root in active_workspace_roots:
            run_code = _workspace_run_code(root)
            run = db.scalar(select(Run).where(Run.run_code == run_code))
            name = f"当前工作区：{Path(root).name}"
            now = datetime.now(timezone.utc)
            if run is None:
                run = Run(
                    run_code=run_code,
                    run_name=name,
                    source_type=RunSourceType.CODEX,
                    status=RunStatus.RUNNING,
                    started_at=now,
                    last_activity_at=now,
                    created_by="codex-local-sync",
                )
                db.add(run)
                created += 1
            else:
                run.run_name = name
                run.status = RunStatus.RUNNING
                run.last_activity_at = now
                updated += 1

        db.commit()
        return created, updated
    finally:
        db.close()


def get_codex_inventory_counts() -> tuple[int, int]:
    sessions = _read_session_index()
    active_workspace_roots = _read_active_workspace_roots()
    return len(sessions), len(active_workspace_roots)


if __name__ == "__main__":
    created_count, updated_count = sync_codex_projects()
    print(f"synced codex projects: created={created_count}, updated={updated_count}")
