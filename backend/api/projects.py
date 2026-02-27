"""Project management API endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import subprocess

from backend.database import db
from backend.config import (
    DATA_DIR, TIMELAPSE_FPS, TIMELAPSE_INTERVAL, TIMELAPSE_AUTO_START,
    get_project_timelapse_dir
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    notes: Optional[str] = ""
    timelapse_enabled: Optional[bool] = True
    timelapse_interval: Optional[int] = 300
    timelapse_only_with_lights: Optional[bool] = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    timelapse_enabled: Optional[bool] = None
    timelapse_interval: Optional[int] = None
    timelapse_only_with_lights: Optional[bool] = None


@router.get("/")
async def get_all_projects():
    """Get all projects."""
    try:
        projects = db.get_all_projects()
        
        # Add timelapse image count for each project
        for project in projects:
            project['timelapse_count'] = db.get_timelapse_image_count(project['id'])
            project['timelapse_enabled'] = bool(project.get('timelapse_enabled', 1))
        
        return {"success": True, "data": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_project():
    """Get currently active project."""
    try:
        project = db.get_active_project()
        if not project:
            return {"success": True, "data": None}
        
        # Add timelapse info
        project['timelapse_count'] = db.get_timelapse_image_count(project['id'])
        project['timelapse_enabled'] = bool(project.get('timelapse_enabled', 1))
        
        return {"success": True, "data": project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: int):
    """Get project by ID."""
    try:
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Add timelapse info
        project['timelapse_count'] = db.get_timelapse_image_count(project_id)
        project['timelapse_enabled'] = bool(project.get('timelapse_enabled', 1))
        
        return {"success": True, "data": project}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_project(project: ProjectCreate):
    """Create a new project."""
    try:
        # End any existing active projects first
        active_project = db.get_active_project()
        if active_project:
            db.end_project(active_project['id'])
        
        # Determine timelapse settings
        timelapse_enabled = project.timelapse_enabled if project.timelapse_enabled is not None else TIMELAPSE_AUTO_START
        timelapse_interval = project.timelapse_interval or TIMELAPSE_INTERVAL
        timelapse_only_with_lights = project.timelapse_only_with_lights if project.timelapse_only_with_lights is not None else True
        
        # Create project with timelapse settings
        project_id = db.create_project(
            project.name, 
            project.notes,
            timelapse_enabled=timelapse_enabled,
            timelapse_interval=timelapse_interval,
            timelapse_only_with_lights=timelapse_only_with_lights
        )
        
        # Create project-specific directories
        project_dir = get_project_timelapse_dir(project_id)
        
        new_project = db.get_project(project_id)
        new_project['timelapse_count'] = 0
        new_project['timelapse_enabled'] = timelapse_enabled
        new_project['timelapse_only_with_lights'] = timelapse_only_with_lights
        
        message = "Project created"
        if timelapse_enabled:
            message += " with time-lapse capture enabled"
            if timelapse_only_with_lights:
                message += " (smart mode: only when lights ON)"
        
        return {"success": True, "data": new_project, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: int, project: ProjectUpdate):
    """Update project details."""
    try:
        updates = {k: v for k, v in project.dict().items() if v is not None}
        
        # Convert boolean fields to int for database
        if 'timelapse_enabled' in updates:
            updates['timelapse_enabled'] = 1 if updates['timelapse_enabled'] else 0
        if 'timelapse_only_with_lights' in updates:
            updates['timelapse_only_with_lights'] = 1 if updates['timelapse_only_with_lights'] else 0
        
        success = db.update_project(project_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        updated_project = db.get_project(project_id)
        updated_project['timelapse_count'] = db.get_timelapse_image_count(project_id)
        updated_project['timelapse_enabled'] = bool(updated_project.get('timelapse_enabled', 1))
        updated_project['timelapse_only_with_lights'] = bool(updated_project.get('timelapse_only_with_lights', 1))
        
        return {"success": True, "data": updated_project, "message": "Project updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/end")
async def end_project(project_id: int, background_tasks: BackgroundTasks):
    """End a project and generate time-lapse video."""
    try:
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # End the project (this disables timelapse)
        success = db.end_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if we have timelapse images to generate video
        images = db.get_timelapse_images(project_id)
        if images and len(images) > 10:
            # Generate video in background
            background_tasks.add_task(_generate_project_video, project_id, project['name'], images)
            message = f"Project ended. Generating time-lapse video from {len(images)} images..."
        else:
            message = "Project ended"
            if images:
                message += f" ({len(images)} timelapse images captured)"
        
        project = db.get_project(project_id)
        project['timelapse_count'] = len(images)
        
        return {"success": True, "data": project, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/archive")
async def archive_project(project_id: int):
    """Archive a project."""
    try:
        success = db.archive_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = db.get_project(project_id)
        return {"success": True, "data": project, "message": "Project archived"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/timelapse/toggle")
async def toggle_project_timelapse(project_id: int, enabled: bool = True):
    """Enable or disable timelapse for a project."""
    try:
        success = db.update_project(project_id, timelapse_enabled=1 if enabled else 0)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = db.get_project(project_id)
        project['timelapse_enabled'] = enabled
        
        action = "enabled" if enabled else "disabled"
        return {"success": True, "data": project, "message": f"Time-lapse {action}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/timelapse/interval")
async def set_project_timelapse_interval(project_id: int, interval: int):
    """Set timelapse interval for a project."""
    try:
        if interval < 30:
            raise HTTPException(status_code=400, detail="Interval must be at least 30 seconds")
        
        success = db.update_project(project_id, timelapse_interval=interval)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = db.get_project(project_id)
        return {"success": True, "data": project, "message": f"Time-lapse interval set to {interval}s"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/generate-video")
async def generate_project_video(project_id: int, background_tasks: BackgroundTasks,
                                 fps: int = TIMELAPSE_FPS):
    """Generate time-lapse video for a project."""
    try:
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        images = db.get_timelapse_images(project_id)
        if not images:
            raise HTTPException(status_code=400, detail="No time-lapse images available")
        
        if len(images) < 5:
            raise HTTPException(status_code=400, detail="Need at least 5 images for video")
        
        # Generate video in background
        background_tasks.add_task(_generate_project_video, project_id, project['name'], images, fps)
        
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


@router.get("/{project_id}/statistics")
async def get_project_statistics(project_id: int):
    """Get statistics for a project."""
    try:
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get sensor data statistics
        sensor_data = db.get_sensor_data(project_id=project_id, limit=10000)
        
        stats = {
            "project": project,
            "timelapse_count": db.get_timelapse_image_count(project_id),
            "sensor_readings": len(sensor_data),
            "diary_entries": len(db.get_diary_entries(project_id)),
            "ai_analyses": len(db.get_ai_analyses(project_id=project_id))
        }
        
        if sensor_data:
            temps = [d['temperature'] for d in sensor_data if d.get('temperature')]
            humidities = [d['humidity'] for d in sensor_data if d.get('humidity')]
            
            if temps:
                stats['temperature'] = {
                    'min': min(temps),
                    'max': max(temps),
                    'avg': sum(temps) / len(temps)
                }
            
            if humidities:
                stats['humidity'] = {
                    'min': min(humidities),
                    'max': max(humidities),
                    'avg': sum(humidities) / len(humidities)
                }
        
        # Calculate project duration
        start_date = project.get('start_date')
        end_date = project.get('end_date') or datetime.now().isoformat()
        
        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                duration = end - start
                stats['duration_days'] = duration.days
            except:
                pass
        
        return {"success": True, "data": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _generate_project_video(project_id: int, project_name: str, 
                           images: list, fps: int = TIMELAPSE_FPS):
    """Background task to generate video using ffmpeg."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Create output directory
        videos_dir = DATA_DIR / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean project name for filename
        safe_name = "".join(c for c in project_name if c.isalnum() or c in ' -_').strip()
        safe_name = safe_name.replace(' ', '_')[:30]
        
        # Output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = videos_dir / f"timelapse_{safe_name}_{project_id}_{timestamp}.mp4"
        
        # Create temporary file list for ffmpeg
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for img in images:
                img_path = Path(img['filepath'])
                if not img_path.is_absolute():
                    img_path = Path.cwd() / img_path
                if img_path.exists():
                    f.write(f"file '{img_path}'\n")
                    f.write(f"duration {1/fps}\n")
            filelist_path = f.name
        
        # Use ffmpeg to create video
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', filelist_path,
            '-vsync', 'vfr',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-crf', '23',
            '-y',
            str(output_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        # Clean up temp file
        Path(filelist_path).unlink()
        
        if result.returncode == 0:
            logger.info(f"Time-lapse video generated: {output_file}")
        else:
            logger.error(f"Error generating video: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error in video generation: {e}")
