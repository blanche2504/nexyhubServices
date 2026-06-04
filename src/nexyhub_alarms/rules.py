from dataclasses import dataclass, field


@dataclass
class AlarmRule:
    name: str
    source: str
    field: str | None = None
    min: float | None = None
    max: float | None = None
    hysteresis: float = 0.0
    severity: str = "warning"


@dataclass
class AlarmState:
    name: str
    active: bool = False
    last_value: float | None = None
    message: str = ""
