from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RunSourceType, RunStatus


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("idx_status_last_activity_at", "status", "last_activity_at"),
        Index("idx_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_code: Mapped[str] = mapped_column(String(64), unique=True)
    run_name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[RunSourceType] = mapped_column(
        Enum(RunSourceType, native_enum=False, length=32),
        default=RunSourceType.CODEX,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=32),
        default=RunStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    agents = relationship("RunAgent", back_populates="run")
    logs = relationship("RunAgentLog", back_populates="run")
    artifacts = relationship("RunAgentArtifact", back_populates="run")
    risks = relationship("RunRisk", back_populates="run")
