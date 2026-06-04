import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexyhub_alarms.rules import AlarmRule, AlarmState
from nexyhub_alarms.engine import AlarmEngine


class TestAlarmRules(unittest.TestCase):
    def test_rule_defaults(self):
        r = AlarmRule(name="test", source="sensor.temp", max=100.0)
        self.assertEqual(r.severity, "warning")
        self.assertEqual(r.hysteresis, 0.0)

    def test_rule_with_field(self):
        r = AlarmRule(name="t", source="can", field="temp", min=0.0)
        self.assertEqual(r.field, "temp")


class TestAlarmState(unittest.TestCase):
    def test_default_state(self):
        s = AlarmState(name="test")
        self.assertFalse(s.active)
        self.assertIsNone(s.last_value)


class TestAlarmEngine(unittest.TestCase):
    def test_no_rules_no_events(self):
        engine = AlarmEngine()
        events = engine.evaluate({"sensor": {"temp": 50.0}})
        self.assertEqual(events, [])

    def test_max_threshold_triggers(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="high_temp", source="sensor.temp", max=80.0, severity="critical"))
        events = engine.evaluate({"sensor": {"temp": 85.0}})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "high_temp")
        self.assertEqual(events[0]["severity"], "critical")
        self.assertEqual(events[0]["type"], "active")

    def test_below_max_no_trigger(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="high_temp", source="sensor.temp", max=80.0))
        events = engine.evaluate({"sensor": {"temp": 50.0}})
        self.assertEqual(events, [])

    def test_min_threshold_triggers(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="low_temp", source="sensor.temp", min=10.0))
        events = engine.evaluate({"sensor": {"temp": 5.0}})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "active")

    def test_alarm_clears_with_hysteresis(self):
        engine = AlarmEngine()
        # max=80, hysteresis=5 → clears at 75
        engine.add_rule(AlarmRule(name="high_temp", source="sensor.temp", max=80.0, hysteresis=5.0))
        engine.evaluate({"sensor": {"temp": 85.0}})  # trigger
        events = engine.evaluate({"sensor": {"temp": 78.0}})  # still above 75, no clear
        self.assertEqual(len(events), 0)
        events = engine.evaluate({"sensor": {"temp": 70.0}})  # below 75, clears
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "cleared")

    def test_alarm_clears_min_with_hysteresis(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="low", source="val", min=20.0, hysteresis=2.0))
        engine.evaluate({"val": 10.0})  # trigger
        events = engine.evaluate({"val": 21.0})  # above 20, needs 22 for rearm, so no clear
        self.assertEqual(len(events), 0)
        events = engine.evaluate({"val": 23.0})  # above 22, clears
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "cleared")

    def test_active_alarms_property(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="h", source="x", max=50.0))
        self.assertEqual(len(engine.active_alarms), 0)
        engine.evaluate({"x": 60.0})
        self.assertEqual(len(engine.active_alarms), 1)

    def test_no_double_trigger(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="h", source="x", max=50.0))
        engine.evaluate({"x": 60.0})  # trigger
        events = engine.evaluate({"x": 70.0})  # still high, should not re-trigger
        self.assertEqual(len(events), 0)

    def test_rules_property(self):
        engine = AlarmEngine()
        r = AlarmRule(name="t", source="s", max=10.0)
        engine.add_rule(r)
        self.assertEqual(len(engine.rules), 1)
        self.assertIs(engine.rules[0], r)

    def test_missing_source_returns_no_events(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="x", source="nonexistent.path", max=10.0))
        events = engine.evaluate({"something": 5.0})
        self.assertEqual(events, [])

    def test_nested_source_resolution(self):
        engine = AlarmEngine()
        engine.add_rule(AlarmRule(name="deep", source="a.b.c", max=10.0))
        events = engine.evaluate({"a": {"b": {"c": 15.0}}})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "deep")
