import time, threading
from io import BytesIO

class _NoCam:
    available = False
    def capture_jpeg(self, size=(640,480), quality=75):
        raise RuntimeError("Camera not available")

def _impl():
    try:
        from picamera2 import Picamera2
        from PIL import Image
        _lock = threading.Lock()
        _picam = None
        _started = False
        class Camera:
            available = True
            def _ensure_started(self, size):
                nonlocal _picam, _started
                with _lock:
                    if _picam is None:
                        _picam = Picamera2()
                        cfg = _picam.create_still_configuration(main={"size": size, "format": "RGB888"})
                        _picam.configure(cfg)
                    if not _started:
                        _picam.start()
                        time.sleep(0.3)
            def capture_jpeg(self, size=(640,480), quality=75):
                self._ensure_started(size)
                frame = _picam.capture_array()
                from PIL import Image
                img = Image.fromarray(frame)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                return buf.getvalue()
        return Camera
    except Exception:
        return _NoCam
Camera = _impl()
