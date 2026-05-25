from enum import StrEnum


class RunSourceType(StrEnum):
    CODEX = "codex"
    MANUAL = "manual"
    SYSTEM = "system"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentPhase(StrEnum):
    ANALYSIS = "analysis"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TEST = "test"
    INTEGRATION = "integration"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LogEventType(StrEnum):
    STATUS_CHANGE = "status_change"
    PHASE_CHANGE = "phase_change"
    PROGRESS_UPDATE = "progress_update"
    BLOCKING_UPDATE = "blocking_update"
    COMMENT = "comment"


class OperatorType(StrEnum):
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


class ReportSource(StrEnum):
    API = "api"
    REPORTER = "reporter"
    SYSTEM = "system"


class ResultStatus(StrEnum):
    SUCCESS = "success"
    REJECTED = "rejected"
    ERROR = "error"


class ArtifactType(StrEnum):
    FILE = "file"
    LINK = "link"
    SUMMARY = "summary"


class RiskType(StrEnum):
    BLOCKER = "blocker"
    DEPENDENCY = "dependency"
    QUALITY = "quality"
    OTHER = "other"


class RiskStatus(StrEnum):
    OPEN = "open"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
