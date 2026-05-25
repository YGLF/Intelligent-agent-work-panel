from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ArtifactType


class RunAgentArtifact(Base):
    __tablename__ = "run_agent_artifacts"
    __table_args__ = (
        Index("idx_agent_created", "agent_id", "created_at"),
        Index("idx_run_type", "run_id", "artifact_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("run_agents.id"), nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, native_enum=False, length=32),
        nullable=False,
    )
    artifact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    artifact_version: Mapped[str | None] = mapped_column(String(64))
    summary: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run = relationship("Run", back_populates="artifacts")
    agent = relationship("RunAgent", back_populates="artifacts")
