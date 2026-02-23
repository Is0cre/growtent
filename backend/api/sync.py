"""External Server Sync API endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.database import db
from backend.external_sync import get_sync_module
from backend.config import DATA_DIR

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Reference to sync module (set by main.py)
_sync_module = None


def set_sync_module(module):
    """Set the sync module reference."""
    global _sync_module
    _sync_module = module


class SyncConfig(BaseModel):
    sync_photos: Optional[bool] = True
    sync_sensor_data: Optional[bool] = True
    sync_project_info: Optional[bool] = True


@router.get("/status")
async def get_sync_status():
    """Get external sync status."""
    try:
        sync_module = _sync_module or get_sync_module()
        
        if not sync_module:
            return {
                "success": True,
                "data": {
                    "enabled": False,
                    "configured": False,
                    "message": "Sync module not initialized"
                }
            }
        
        # Get last successful sync
        last_sync = db.get_last_successful_sync('full')
        
        return {
            "success": True,
            "data": {
                "enabled": sync_module.enabled,
                "configured": bool(sync_module.base_url),
                "base_url": sync_module.base_url if sync_module.enabled else None,
                "last_sync": last_sync.get('timestamp') if last_sync else None,
                "last_sync_items": last_sync.get('items_synced') if last_sync else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_sync_connection():
    """Test connection to external server."""
    try:
        sync_module = _sync_module or get_sync_module()
        
        if not sync_module:
            return {
                "success": False,
                "error": "Sync module not initialized"
            }
        
        result = sync_module.test_connection()
        
        return {
            "success": result.get('success', False),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/now")
async def sync_now(background_tasks: BackgroundTasks, config: Optional[SyncConfig] = None):
    """Trigger immediate sync to external server."""
    try:
        sync_module = _sync_module or get_sync_module()
        
        if not sync_module:
            raise HTTPException(status_code=400, detail="Sync module not initialized")
        
        if not sync_module.enabled:
            raise HTTPException(status_code=400, detail="External sync not enabled")
        
        # Run sync in background
        background_tasks.add_task(_run_sync, sync_module, config)
        
        return {
            "success": True,
            "message": "Sync started in background"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/photo")
async def sync_latest_photo():
    """Sync the latest photo to external server."""
    try:
        sync_module = _sync_module or get_sync_module()
        
        if not sync_module or not sync_module.enabled:
            raise HTTPException(status_code=400, detail="External sync not enabled")
        
        # Find latest photo
        photos_dir = DATA_DIR / "photos"
        if not photos_dir.exists():
            raise HTTPException(status_code=404, detail="No photos directory")
        
        photos = sorted(photos_dir.glob("*.jpg"))
        if not photos:
            raise HTTPException(status_code=404, detail="No photos available")
        
        latest_photo = photos[-1]
        
        # Get active project
        project = db.get_active_project()
        project_id = project['id'] if project else None
        
        # Sync photo
        result = sync_module.sync_photo(str(latest_photo), project_id, 'latest')
        
        # Log sync
        db.log_sync(
            sync_type='photo',
            status='success' if result.get('success') else 'failed',
            details=str(result),
            items_synced=1 if result.get('success') else 0
        )
        
        return {
            "success": result.get('success', False),
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        db.log_sync(
            sync_type='photo',
            status='error',
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sensor-data")
async def sync_sensor_data():
    """Sync latest sensor data to external server."""
    try:
        sync_module = _sync_module or get_sync_module()
        
        if not sync_module or not sync_module.enabled:
            raise HTTPException(status_code=400, detail="External sync not enabled")
        
        # Get latest sensor data
        sensor_data = db.get_latest_sensor_data()
        if not sensor_data:
            raise HTTPException(status_code=404, detail="No sensor data available")
        
        # Get active project
        project = db.get_active_project()
        project_id = project['id'] if project else None
        
        # Sync
        result = sync_module.sync_sensor_data(sensor_data, project_id)
        
        # Log sync
        db.log_sync(
            sync_type='sensor_data',
            status='success' if result.get('success') else 'failed',
            details=str(result),
            items_synced=1 if result.get('success') else 0
        )
        
        return {
            "success": result.get('success', False),
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        db.log_sync(
            sync_type='sensor_data',
            status='error',
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_sync_logs(sync_type: Optional[str] = None, limit: int = 50):
    """Get sync logs."""
    try:
        logs = db.get_sync_logs(sync_type, limit)
        return {
            "success": True,
            "data": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_sync(sync_module, config: Optional[SyncConfig] = None):
    """Background task to run full sync."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get data to sync
        project = db.get_active_project()
        sensor_data = db.get_latest_sensor_data()
        
        # Find latest photo
        photo_path = None
        photos_dir = DATA_DIR / "photos"
        if photos_dir.exists():
            photos = sorted(photos_dir.glob("*.jpg"))
            if photos:
                photo_path = str(photos[-1])
        
        # Get latest analysis
        analysis = None
        if project:
            analysis = db.get_latest_ai_analysis(project['id'])
        
        # Run sync
        result = sync_module.sync_all(
            sensor_data=sensor_data,
            project=project,
            photo_path=photo_path,
            analysis=analysis
        )
        
        # Log result
        db.log_sync(
            sync_type='full',
            status='success' if result.get('success') else 'partial',
            details=str(result.get('results', {})),
            items_synced=result.get('synced', 0)
        )
        
        logger.info(f"Sync completed: {result.get('synced')}/{result.get('total')} items")
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
        db.log_sync(
            sync_type='full',
            status='error',
            error_message=str(e)
        )
