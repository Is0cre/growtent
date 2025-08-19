from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime

def read_latest_states(log_path: Path) -> dict:
    """
    Parse your service.log last known states.
    Expected line example (adapt if needed):
      [2025-01-01 12:34:56] Lights=ON Exhaust Fan=OFF Circulatory Fans=ON ...
    """
    out = {"timestamp": None, "states": {}}
    if not log_path.exists():
        return out
    try:
        *_, last = log_path.read_text(errors="ignore").splitlines()
    except ValueError:
        return out

    # crude parse: key=value tokens
    tokens = re.findall(r"([\w\s]+)=(ON|OFF)", last)
    for k, v in tokens:
        out["states"][k.strip()] = v
    ts = re.search(r"\[(.*?)\]", last)
    if ts:
        out["timestamp"] = ts.group(1)
    return out

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
