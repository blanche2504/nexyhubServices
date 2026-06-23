from nexyhub_alarms.rules import AlarmRule, AlarmState


def _resolve_value(data: dict, source: str, field: str | None = None) -> float | None:
    parts = source.split(".")
    val = data
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return None
    if val is None:
        return None
    if field is not None and isinstance(val, dict):
        val = val.get(field)
    if isinstance(val, (int, float)):
        return float(val)
    return None


class AlarmEngine:
    def __init__(self, rules: list[AlarmRule] | None = None):
        self._rules: list[AlarmRule] = rules or []
        self._states: dict[str, AlarmState] = {}

    def add_rule(self, rule: AlarmRule):
        self._rules.append(rule)
        if rule.name not in self._states:
            self._states[rule.name] = AlarmState(name=rule.name)

    def evaluate(self, data: dict) -> list[dict]:
        events: list[dict] = []
        for rule in self._rules:
            value = _resolve_value(data, rule.source, rule.field)
            if value is None:
                continue
            state = self._states.setdefault(rule.name, AlarmState(name=rule.name))
            state.last_value = value
            triggered = False
            if rule.max is not None and value > rule.max:
                triggered = True
            if rule.min is not None and value < rule.min:
                triggered = True
            if triggered and not state.active:
                state.active = True
                state.message = f"{rule.name}: {value:.1f} out of range"
                events.append({
                    "name": rule.name,
                    "severity": rule.severity,
                    "message": state.message,
                    "type": "active",
                })
            elif not triggered and state.active:
                if rule.max is not None:
                    rearm = value <= rule.max - rule.hysteresis
                elif rule.min is not None:
                    rearm = value >= rule.min + rule.hysteresis
                else:
                    rearm = True
                if rearm:
                    state.active = False
                    state.message = f"{rule.name}: returned to normal ({value:.1f})"
                    events.append({
                        "name": rule.name,
                        "severity": rule.severity,
                        "message": state.message,
                        "type": "cleared",
                    })
        return events

    @property
    def active_alarms(self) -> list[AlarmState]:
        return [s for s in self._states.values() if s.active]

    @property
    def rules(self) -> list[AlarmRule]:
        return list(self._rules)
