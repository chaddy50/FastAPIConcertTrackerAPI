import enum


class PerformerType(str, enum.Enum):
    ORCHESTRA = "ORCHESTRA"
    ENSEMBLE = "ENSEMBLE"
    SOLO = "SOLO"
    CHORUS = "CHORUS"
    CONDUCTOR = "CONDUCTOR"
    OTHER = "OTHER"


class PerformanceStatus(str, enum.Enum):
    UPCOMING = "UPCOMING"
    ATTENDED = "ATTENDED"
    CANCELLED = "CANCELLED"
    MISSED = "MISSED"
    SKIPPED = "SKIPPED"
