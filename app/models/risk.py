from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RiskLevel, RiskStatus, RiskType


class RunRisk(Base):
    __tablename__ = "run_risks"
    __table_args__ = (
        Index("idx_run_open_risk", "run_id", "status", "risk_level"),
        Index("idx_agent_opened", "agent_id", "opened_at"),
        Index("idx_status_updated", "status", "updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("run_agents.id"))
    risk_type: Mapped[RiskType] = mapped_column(
        Enum(RiskType, native_enum=False, length=32),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False, length=32),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RiskStatus] = mapped_column(
        Enum(RiskStatus, native_enum=False, length=32),
        default=RiskStatus.OPEN,
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds_snapshot: Mapped[int | None] = mapped_column(BigInteger)
    reported_by: Mapped[str] = mapped_column(String(128), nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    run = relationship("Run", back_populates="risks")
    agent = relationship("RunAgent", back_populates="risks")
