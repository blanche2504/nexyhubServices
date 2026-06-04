import os
import json
import time
from pathlib import Path
from flask import Flask, render_template, jsonify

from nexyhub_db.database import Database
from nexyhub_ipc.shared_mem import list_keys, atomic_read, SHARED_DIR

app = Flask(__name__)

DB_PATH = os.environ.get("NEXYHUB_DB_PATH", "/mnt/shared/nexyhub.db")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
SERVICE_TIMEOUT = int(os.environ.get("SERVICE_TIMEOUT", "120"))


def get_db():
    try:
        return Database(DB_PATH)
    except Exception:
        return None


def file_age(path: str) -> float | None:
    try:
        return time.time() - os.path.getmtime(path)
    except Exception:
        return None


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/services")
def api_services():
    db = get_db()
    now = time.time()
    services = {}

    # check each source by last db timestamp
    sources = {"can": "CAN bus", "serial": "serial port", "ble": "BLE scanner", "producer": "data producer"}
    for src, label in sources.items():
        if db:
            rows = db.get_readings(source=src, limit=1)
        else:
            rows = []
        last_ts = rows[0]["ts"] if rows else 0
        age = now - last_ts if last_ts else None
        services[src] = {
            "label": label,
            "alive": age is not None and age < SERVICE_TIMEOUT,
            "last_seen": round(age, 1) if age is not None else None,
            "readings": len(db.get_readings(source=src, limit=10000)) if db else 0,
        }

    # check shared memory files
    for key, label in [("producer/data.json", "data producer"),
                       ("ble_devices.json", "BLE scanner")]:
        age = file_age(str(SHARED_DIR / key))
        if age is not None:
            srv = key.split("/")[0]
            if srv in services:
                services[srv]["file_age"] = round(age, 1)
                if services[srv]["last_seen"] is None:
                    services[srv]["alive"] = age < SERVICE_TIMEOUT
                services[srv]["alive"] = services[srv]["alive"] or (age < SERVICE_TIMEOUT)

    # db health
    db_alive = False
    try:
        db_path = Path(DB_PATH)
        db_alive = db_path.exists() and file_age(DB_PATH) is not None
    except Exception:
        pass
    services["db"] = {
        "label": "SQLite database",
        "alive": db_alive,
        "path": DB_PATH,
    }

    services["ui"] = {
        "label": "UI dashboard",
        "alive": True,
        "uptime": round(time.time() - start_time, 1),
    }

    return jsonify(services)


@app.route("/api/status")
def api_status():
    db = get_db()
    readings = db.get_readings(limit=1) if db else []
    alarm_count = len(db.get_active_alarms()) if db else 0
    keys = list_keys()
    return jsonify({
        "uptime": round(time.time() - start_time, 1),
        "shared_dir": str(SHARED_DIR),
        "file_count": len(keys),
        "files": keys,
        "active_alarms": alarm_count,
        "total_readings": len(db.get_readings(limit=10000)) if db else 0,
    })


@app.route("/api/readings")
def api_readings():
    db = get_db()
    if not db:
        return jsonify([])
    rows = db.get_readings(limit=100)
    return jsonify(rows)


@app.route("/api/readings/<source>")
def api_readings_source(source):
    db = get_db()
    if not db:
        return jsonify([])
    rows = db.get_readings(source=source, limit=100)
    return jsonify(rows)


@app.route("/api/alarms")
def api_alarms():
    db = get_db()
    if not db:
        return jsonify({"active": [], "history": []})
    return jsonify({
        "active": db.get_active_alarms(),
        "history": db.get_alarm_history(limit=50),
    })


@app.route("/api/data/<path:key>")
def api_data(key):
    data = atomic_read(key)
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "not found"}), 404


start_time = time.time()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False)
