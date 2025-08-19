from __future__ import annotations
import subprocess
import shlex
from pathlib import Path
from datetime import datetime
from .config import CAMERA_CMD, CAMERA_RES, CAPTURE_DIR

def capture_still(out_path: Path) -> Path:
    """
    Take a still image using rpicam-still or libcamera-still.
    Saves to out_path (jpg). Returns the path.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if CAMERA_CMD.endswith("rpicam-still"):
        cmd = f"{CAMERA_CMD} -o {shlex.quote(str(out_path))} -n -t 1 --width {CAMERA_RES.split(':')[0]} --height {CAMERA_RES.split(':')[1]}"
    else:
        # libcamera-still compatible
        w, h = CAMERA_RES.split(":")
        cmd = f"{CAMERA_CMD} -o {shlex.quote(str(out_path))} -n -t 1 --width {w} --height {h}"
    subprocess.run(cmd, shell=True, check=False)
    return out_path

def snapshot_path() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return CAPTURE_DIR / f"snapshot_{ts}.jpg"
