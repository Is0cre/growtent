"""Camera API endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional
from pathlib import Path
import io
from datetime import datetime

from backend.config import DATA_DIR

router = APIRouter(prefix="/api/camera", tags=["camera"])

# Global reference to automation engine (set in main.py)
automation_engine = None

def set_automation_engine(engine):
    """Set the automation engine reference."""
    global automation_engine
    automation_engine = engine

@router.get("/snapshot")
async def capture_snapshot():
    """Capture a snapshot from the camera."""
    try:
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        # Capture image
        photo_path = automation_engine.capture_photo()
        
        if not photo_path or not Path(photo_path).exists():
            raise HTTPException(status_code=500, detail="Failed to capture image")
        
        return {
            "success": True,
            "message": "Snapshot captured",
            "data": {
                "path": str(Path(photo_path).relative_to(DATA_DIR.parent)),
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream")
async def camera_stream():
    """Get camera stream (MJPEG)."""
    try:
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        def generate():
            """Generate MJPEG stream."""
            while True:
                try:
                    # Capture frame
                    frame_bytes = automation_engine.camera.capture_to_stream()
                    if frame_bytes:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    else:
                        break
                except Exception as e:
                    print(f"Stream error: {e}")
                    break
        
        return StreamingResponse(
            generate(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/live")
async def get_live_image():
    """Get a single live image from camera."""
    try:
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        # Capture to bytes
        image_bytes = automation_engine.camera.capture_to_stream()
        
        if not image_bytes:
            raise HTTPException(status_code=500, detail="Failed to capture image")
        
        return StreamingResponse(
            io.BytesIO(image_bytes),
            media_type="image/jpeg"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/photos")
async def list_photos():
    """List all captured photos."""
    try:
        photos_dir = DATA_DIR / "photos"
        if not photos_dir.exists():
            return {"success": True, "data": []}
        
        photos = []
        for photo_file in photos_dir.rglob("*.jpg"):
            if photo_file.is_file():
                stat = photo_file.stat()
                photos.append({
                    "filename": photo_file.name,
                    "path": str(photo_file.relative_to(DATA_DIR.parent)),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        photos.sort(key=lambda x: x['created'], reverse=True)
        
        return {"success": True, "data": photos[:100]}  # Limit to 100 most recent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
