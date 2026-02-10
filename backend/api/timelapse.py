"""Time-lapse API endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from pathlib import Path
import subprocess
from datetime import datetime

from backend.database import db
from backend.config import DATA_DIR, TIMELAPSE_FPS

router = APIRouter(prefix="/api/timelapse", tags=["timelapse"])

@router.get("/images")
async def get_timelapse_images(project_id: Optional[int] = None):
    """Get all time-lapse images for a project."""
    try:
        if project_id is None:
            active_project = db.get_active_project()
            if not active_project:
                return {"success": True, "data": [], "message": "No active project"}
            project_id = active_project['id']
        
        images = db.get_timelapse_images(project_id)
        return {"success": True, "data": images, "count": len(images)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_timelapse(interval: int = 300):
    """Start time-lapse capture."""
    try:
        # Check if there's an active project
        active_project = db.get_active_project()
        if not active_project:
            raise HTTPException(status_code=400, detail="No active project. Create a project first.")
        
        # Enable time-lapse
        db.set_system_setting('timelapse_enabled', 'true')
        db.set_system_setting('timelapse_interval', str(interval))
        
        return {
            "success": True,
            "message": f"Time-lapse started (interval: {interval}s)",
            "data": {
                "enabled": True,
                "interval": interval
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_timelapse():
    """Stop time-lapse capture."""
    try:
        db.set_system_setting('timelapse_enabled', 'false')
        
        return {
            "success": True,
            "message": "Time-lapse stopped",
            "data": {"enabled": False}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_timelapse_status():
    """Get time-lapse capture status."""
    try:
        enabled = db.get_system_setting('timelapse_enabled') == 'true'
        interval = int(db.get_system_setting('timelapse_interval') or 300)
        
        # Get image count for active project
        image_count = 0
        active_project = db.get_active_project()
        if active_project:
            images = db.get_timelapse_images(active_project['id'])
            image_count = len(images)
        
        return {
            "success": True,
            "data": {
                "enabled": enabled,
                "interval": interval,
                "image_count": image_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_timelapse_video(
    background_tasks: BackgroundTasks,
    project_id: Optional[int] = None,
    fps: int = TIMELAPSE_FPS
):
    """Generate time-lapse video from images."""
    try:
        if project_id is None:
            active_project = db.get_active_project()
            if not active_project:
                raise HTTPException(status_code=400, detail="No active project")
            project_id = active_project['id']
        
        # Get images
        images = db.get_timelapse_images(project_id)
        if not images:
            raise HTTPException(status_code=400, detail="No images available for time-lapse")
        
        # Generate video in background
        background_tasks.add_task(_generate_video, project_id, images, fps)
        
        return {
            "success": True,
            "message": f"Video generation started ({len(images)} images at {fps} FPS)",
            "data": {
                "project_id": project_id,
                "image_count": len(images),
                "fps": fps
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _generate_video(project_id: int, images: list, fps: int):
    """Background task to generate video using ffmpeg."""
    try:
        # Create output directory
        videos_dir = DATA_DIR / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        
        # Output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = videos_dir / f"timelapse_project{project_id}_{timestamp}.mp4"
        
        # Create temporary file list for ffmpeg
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for img in images:
                # Write full path
                img_path = Path(img['filepath'])
                if not img_path.is_absolute():
                    img_path = Path.cwd() / img_path
                f.write(f"file '{img_path}'\n")
            filelist_path = f.name
        
        # Use ffmpeg to create video
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', filelist_path,
            '-vf', f'fps={fps}',
            '-pix_fmt', 'yuv420p',
            '-y',  # Overwrite output file
            str(output_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temp file
        Path(filelist_path).unlink()
        
        if result.returncode == 0:
            print(f"Time-lapse video generated: {output_file}")
        else:
            print(f"Error generating video: {result.stderr}")
            
    except Exception as e:
        print(f"Error in video generation: {e}")

@router.get("/videos")
async def list_timelapse_videos():
    """List available time-lapse videos."""
    try:
        videos_dir = DATA_DIR / "videos"
        if not videos_dir.exists():
            return {"success": True, "data": []}
        
        videos = []
        for video_file in videos_dir.glob("timelapse_*.mp4"):
            stat = video_file.stat()
            videos.append({
                "filename": video_file.name,
                "path": str(video_file.relative_to(DATA_DIR.parent)),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        videos.sort(key=lambda x: x['created'], reverse=True)
        
        return {"success": True, "data": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos/{filename}")
async def download_timelapse_video(filename: str):
    """Download a time-lapse video."""
    try:
        video_path = DATA_DIR / "videos" / filename
        
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        return FileResponse(
            video_path,
            media_type="video/mp4",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
