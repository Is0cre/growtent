from __future__ import annotations
import threading, time
from datetime import datetime, time as dtime
from pathlib import Path
from .config import TL_ACTIVE_FLAG, TL_INTERVAL_SEC, CAPTURE_DIR
from .camera import capture_still

class TimelapseThread(threading.Thread):
    daemon = True
    def __init__(self):
        super().__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        # Simple loop controlled by presence of flag file
        while not self._stop.is_set():
            if TL_ACTIVE_FLAG.exists():
                # folder by date
                folder = CAPTURE_DIR / datetime.now().strftime("%Y-%m-%d")
                img = folder / f"{datetime.now():%H%M%S}.jpg"
                try:
                    capture_still(img)
                except Exception:
                    pass
                for _ in range(TL_INTERVAL_SEC):
                    if self._stop.is_set(): break
                    time.sleep(1)
            else:
                time.sleep(1)

TL = TimelapseThread()
