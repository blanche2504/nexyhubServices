import os
import json
import time
from pathlib import Path

SHARED_DIR = Path(os.environ.get("IPC_SHARED_DIR", "/mnt/shared"))


def atomic_write(key: str, data: object) -> None:
    dest = SHARED_DIR / key
    tmp = dest.with_suffix(".tmp")
    try:
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.rename(dest)
    except Exception as e:
        raise OSError(f"atomic_write failed for {key}: {e}") from e


def atomic_read(key: str) -> object | None:
    path = SHARED_DIR / key
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {key}: {e}") from e


def list_keys(pattern: str = "**/*.json") -> list[str]:
    try:
        return sorted(str(p.relative_to(SHARED_DIR)) for p in SHARED_DIR.glob(pattern) if p.is_file())
    except FileNotFoundError:
        return []
