import os
from pathlib import Path

# Root dirs (safe defaults)
ROOT = Path(os.getenv("GROWTENT_ROOT", Path(__file__).resolve().parent.parent))
DATA_DIR = ROOT / "graphs"
CAPTURE_DIR = ROOT / "graphs" / "captures"
LOG_FILE = ROOT / "controller" / "service.log"  # your existing file path

# Camera
CAMERA_CMD = os.getenv("CAMERA_CMD", "rpicam-still")  # or "libcamera-still"
CAMERA_RES = os.getenv("CAMERA_RES", "1920:1080")     # WxH with colon for rpicam

# Timelapse
TL_ACTIVE_FLAG = ROOT / "graphs" / ".timelapse_on"
TL_INTERVAL_SEC = int(os.getenv("TL_INTERVAL_SEC", "300"))  # default 5 min
TL_DAY_START = os.getenv("TL_DAY_START", "06:00")
TL_DAY_END   = os.getenv("TL_DAY_END",   "23:59")

# UI
SECRET_KEY = os.getenv("FLASK_SECRET", "dev-secret")
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

# Ensure dirs exist
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
