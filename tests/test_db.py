import os
import sys
import time
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexyhub_db.database import Database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)

    def tearDown(self):
        self.db.close()
        os.unlink(self.tmp.name)

    def test_insert_and_get_readings(self):
        self.db.insert_reading("can", "temperature", value=25.5, unit="C")
        self.db.insert_reading("can", "humidity", value=60.0, unit="%")
        rows = self.db.get_readings(limit=10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source"], "can")
        self.assertEqual(rows[0]["value"], 60.0)

    def test_get_readings_filter_by_source(self):
        self.db.insert_reading("can", "temp", value=30.0)
        self.db.insert_reading("serial", "temp", value=22.0)
        rows = self.db.get_readings(source="can")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "can")

    def test_get_readings_filter_by_key(self):
        self.db.insert_reading("can", "temp", value=30.0)
        self.db.insert_reading("can", "pressure", value=1013.0)
        rows = self.db.get_readings(key="temp")
        self.assertEqual(len(rows), 1)

    def test_get_readings_since(self):
        t0 = time.time() - 10
        self.db.insert_reading("can", "a", value=1.0)
        time.sleep(0.02)
        self.db.insert_reading("can", "b", value=2.0)
        rows = self.db.get_readings(since=t0)
        self.assertGreaterEqual(len(rows), 2)

    def test_insert_and_get_alarms(self):
        self.db.insert_alarm("high_temp", "critical", "temp exceeded 80C")
        active = self.db.get_active_alarms()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["name"], "high_temp")
        self.assertEqual(active[0]["severity"], "critical")

    def test_clear_alarm(self):
        self.db.insert_alarm("high_temp", "warning", "too hot")
        self.db.clear_alarm("high_temp")
        active = self.db.get_active_alarms()
        self.assertEqual(len(active), 0)

    def test_alarm_history(self):
        self.db.insert_alarm("a1", "warning", "msg1")
        self.db.clear_alarm("a1")
        history = self.db.get_alarm_history()
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["name"], "a1")
        self.assertTrue(history[0]["cleared"])

    def test_insert_reading_with_text_value(self):
        self.db.insert_reading("ble", "device", text_value="AA:BB:CC:DD:EE:FF")
        rows = self.db.get_readings(source="ble")
        self.assertEqual(rows[0]["text_value"], "AA:BB:CC:DD:EE:FF")

    def test_delete_old_readings(self):
        self.db.insert_reading("can", "old", value=1.0)
        # delete everything older than 0 days → should delete all
        self.db.delete_old_readings(0)
        rows = self.db.get_readings()
        self.assertEqual(len(rows), 0)
