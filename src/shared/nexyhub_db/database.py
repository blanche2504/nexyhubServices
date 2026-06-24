import os
import json
import time
import sqlite3
import threading
from pathlib import Path


class Database:
    def __init__(self, db_path: str, retention_hours: int = 24):
        self._path = db_path
        self._retention_hours = retention_hours
        self._prune_counter = 0
        self._lock = threading.Lock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()
        self._prune_if_needed(force=True)

    def _init_schema(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    source TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value REAL,
                    text_value TEXT,
                    unit TEXT
                );
                CREATE TABLE IF NOT EXISTS alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT,
                    cleared INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings(ts);
                CREATE INDEX IF NOT EXISTS idx_readings_source ON readings(source);
                CREATE INDEX IF NOT EXISTS idx_alarms_ts ON alarms(ts);
                CREATE INDEX IF NOT EXISTS idx_alarms_cleared ON alarms(cleared);
            """)
            self._conn.commit()

    def insert_reading(self, source: str, key: str, value: float | None = None,
                       text_value: str | None = None, unit: str | None = None):
        with self._lock:
            self._conn.execute(
                "INSERT INTO readings (ts, source, key, value, text_value, unit) VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), source, key, value, text_value, unit),
            )
            self._conn.commit()
        self._prune_if_needed()

    def insert_alarm(self, name: str, severity: str, message: str | None = None):
        with self._lock:
            self._conn.execute(
                "INSERT INTO alarms (ts, name, severity, message, cleared) VALUES (?, ?, ?, ?, 0)",
                (time.time(), name, severity, message),
            )
            self._conn.commit()

    def clear_alarm(self, name: str):
        with self._lock:
            self._conn.execute(
                "UPDATE alarms SET cleared=1 WHERE name=? AND cleared=0",
                (name,),
            )
            self._conn.commit()

    def get_reading_count(self, source: str | None = None) -> int:
        with self._lock:
            parts = ["SELECT COUNT(*) FROM readings"]
            params = []
            if source:
                parts.append("WHERE source=?")
                params.append(source)
            row = self._conn.execute(" ".join(parts), params).fetchone()
            return row[0] if row else 0

    def get_readings(self, source: str | None = None, key: str | None = None,
                     limit: int = 100, since: float | None = None) -> list[dict]:
        with self._lock:
            parts = ["SELECT ts, source, key, value, text_value, unit FROM readings"]
            params = []
            conditions = []
            if source:
                conditions.append("source=?")
                params.append(source)
            if key:
                conditions.append("key=?")
                params.append(key)
            if since:
                conditions.append("ts>=?")
                params.append(since)
            if conditions:
                parts.append("WHERE " + " AND ".join(conditions))
            parts.append("ORDER BY ts DESC LIMIT ?")
            params.append(limit)
            rows = self._conn.execute(" ".join(parts), params).fetchall()
            return [
                {"ts": r[0], "source": r[1], "key": r[2],
                 "value": r[3], "text_value": r[4], "unit": r[5]}
                for r in rows
            ]

    def get_active_alarms(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, name, severity, message FROM alarms WHERE cleared=0 ORDER BY ts DESC"
            ).fetchall()
            return [
                {"ts": r[0], "name": r[1], "severity": r[2], "message": r[3]}
                for r in rows
            ]

    def get_alarm_history(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, name, severity, message, cleared FROM alarms ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {"ts": r[0], "name": r[1], "severity": r[2], "message": r[3], "cleared": bool(r[4])}
                for r in rows
            ]

    def delete_old_readings(self, days: int):
        cutoff = time.time() - days * 86400
        with self._lock:
            self._conn.execute("DELETE FROM readings WHERE ts<?", (cutoff,))
            self._conn.execute("DELETE FROM alarms WHERE ts<? AND cleared=1", (cutoff,))
            self._conn.commit()

    def prune_readings(self, hours: int | None = None) -> int:
        cutoff = time.time() - (hours or self._retention_hours) * 3600
        with self._lock:
            deleted = self._conn.execute(
                "DELETE FROM readings WHERE ts<?", (cutoff,)
            ).rowcount
            self._conn.execute("DELETE FROM alarms WHERE ts<? AND cleared=1", (cutoff,))
            self._conn.execute("PRAGMA optimize")
            self._conn.commit()
            if deleted > 1000:
                self._conn.execute("VACUUM")
                self._conn.commit()
            return deleted

    def _prune_if_needed(self, force: bool = False):
        self._prune_counter += 1
        if force or self._prune_counter >= 500:
            self._prune_counter = 0
            self.prune_readings()

    def count_readings(self, source: str | None = None) -> int:
        with self._lock:
            if source:
                row = self._conn.execute(
                    "SELECT COUNT(*) FROM readings WHERE source=?", (source,)
                ).fetchone()
            else:
                row = self._conn.execute("SELECT COUNT(*) FROM readings").fetchone()
            return row[0]

    def db_size(self) -> int:
        try:
            return os.path.getsize(self._path)
        except Exception:
            return 0

    def close(self):
        self._conn.close()
