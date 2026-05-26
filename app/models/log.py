from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AgentPhase, LogEventType, OperatorType, ReportSource, ResultStatus, RunStatus


class RunAgentLog(Base):
    __tablename__ = "run_agent_logs"
    __table_args__ = (
        UniqueConstraint("agent_id", "idempotency_key", name="uk_run_agent_logs_agent_id_idempotency_key"),
        Index("idx_agent_occurred", "agent_id", "occurred_at"),
        Index("idx_run_occurred", "run_id", "occurred_at"),
        Index("idx_event_type", "event_type", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("run_agents.id"), nullable=False)
    event_type: Mapped[LogEventType] = mapped_column(
        Enum(LogEventType, native_enum=False, length=32),
        nullable=False,
    )
    old_status: Mapped[RunStatus | None] = mapped_column(Enum(RunStatus, native_enum=False, length=32))
    new_status: Mapped[RunStatus | None] = mapped_column(Enum(RunStatus, native_enum=False, length=32))
    old_phase: Mapped[AgentPhase | None] = mapped_column(Enum(AgentPhase, native_enum=False, length=32))
    new_phase: Mapped[AgentPhase | None] = mapped_column(Enum(AgentPhase, native_enum=False, length=32))
    before_progress: Mapped[int | None] = mapped_column(Integer)
    after_progress: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    detail_json: Mapped[dict | list | None] = mapped_column(JSON)
    reported_by: Mapped[str] = mapped_column(String(128), nullable=False)
    operator_type: Mapped[OperatorType] = mapped_column(
        Enum(OperatorType, native_enum=False, length=32),
        nullable=False,
    )
    report_source: Mapped[ReportSource] = mapped_column(
        Enum(ReportSource, native_enum=False, length=32),
        nullable=False,
    )
    request_id: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    source_event_id: Mapped[str | None] = mapped_column(String(128))
    trace_id: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    server_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_status: Mapped[ResultStatus] = mapped_column(
        Enum(ResultStatus, native_enum=False, length=32),
        default=ResultStatus.SUCCESS,
    )
    result_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run = relationship("Run", back_populates="logs")
    agent = relationship("RunAgent", back_populates="logs")
