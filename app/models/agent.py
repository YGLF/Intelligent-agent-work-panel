from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.naming import conv

from app.models.base import Base
from app.models.enums import AgentPhase, RiskLevel, RunStatus


class RunAgent(Base):
    __tablename__ = "run_agents"
    __table_args__ = (
        UniqueConstraint("run_id", "agent_code", name="uk_run_agent"),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name=conv("ck_run_agents_progress_percent_range"),
        ),
        Index("idx_run_status", "run_id", "status"),
        Index("idx_run_phase", "run_id", "phase"),
        Index("idx_run_owner_scope", "run_id", "owner_scope"),
        Index("idx_run_last_update", "run_id", "last_update_at"),
        Index("idx_run_risk", "run_id", "risk_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    agent_code: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_scope: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=32),
        default=RunStatus.PENDING,
    )
    phase: Mapped[AgentPhase | None] = mapped_column(
        Enum(AgentPhase, native_enum=False, length=32),
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    current_task: Mapped[str | None] = mapped_column(String(500))
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False, length=32),
        default=RiskLevel.LOW,
    )
    blocking_reason: Mapped[str | None] = mapped_column(Text)
    depends_on_json: Mapped[list[str] | None] = mapped_column(JSON().with_variant(Text(), "mysql"))
    handoff_to: Mapped[str | None] = mapped_column(String(128))
    needs_input: Mapped[bool] = mapped_column(Boolean, default=False)
    deliverable_summary: Mapped[str | None] = mapped_column(Text)
    codex_agent_type: Mapped[str | None] = mapped_column(String(64))
    model_name: Mapped[str | None] = mapped_column(String(128))
    model_tier: Mapped[str | None] = mapped_column(String(64))
    is_main_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_agent_id: Mapped[int | None] = mapped_column(ForeignKey("run_agents.id"))
    conversation_ref: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    run = relationship("Run", back_populates="agents")
    logs = relationship("RunAgentLog", back_populates="agent")
    artifacts = relationship("RunAgentArtifact", back_populates="agent")
    risks = relationship("RunRisk", back_populates="agent")
    parent_agent = relationship("RunAgent", remote_side=[id], back_populates="child_agents")
    child_agents = relationship("RunAgent", back_populates="parent_agent")
