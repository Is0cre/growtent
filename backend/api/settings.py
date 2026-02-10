"""Settings API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from backend.database import db
from backend.config import GPIO_PINS

router = APIRouter(prefix="/api/settings", tags=["settings"])

class DeviceSettings(BaseModel):
    enabled: bool = True
    mode: str = "schedule"  # schedule, threshold, auto, manual
    schedule: Optional[List[Dict[str, Any]]] = []
    thresholds: Optional[Dict[str, float]] = {}

class AlertSettings(BaseModel):
    enabled: bool = True
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    notification_interval: int = 300

@router.get("/devices")
async def get_all_device_settings():
    """Get settings for all devices."""
    try:
        settings = db.get_all_device_settings()
        return {"success": True, "data": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices/{device_name}")
async def get_device_settings(device_name: str):
    """Get settings for a specific device."""
    try:
        if device_name not in GPIO_PINS or device_name == 'unused':
            raise HTTPException(status_code=404, detail="Device not found")
        
        settings = db.get_device_settings(device_name)
        if not settings:
            return {"success": True, "data": None, "message": "No settings found"}
        
        return {"success": True, "data": settings}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/devices/{device_name}")
async def update_device_settings(device_name: str, settings: DeviceSettings):
    """Update settings for a specific device."""
    try:
        if device_name not in GPIO_PINS or device_name == 'unused':
            raise HTTPException(status_code=404, detail="Device not found")
        
        settings_dict = {
            "enabled": settings.enabled,
            "mode": settings.mode,
            "schedule": settings.schedule or [],
            "thresholds": settings.thresholds or {}
        }
        
        success = db.save_device_settings(device_name, settings_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save settings")
        
        return {
            "success": True,
            "message": f"Settings updated for {device_name}",
            "data": settings_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_alert_settings():
    """Get alert settings."""
    try:
        settings = db.get_alert_settings()
        return {"success": True, "data": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/alerts")
async def update_alert_settings(settings: AlertSettings):
    """Update alert settings."""
    try:
        settings_dict = settings.dict()
        success = db.save_alert_settings(settings_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save settings")
        
        return {
            "success": True,
            "message": "Alert settings updated",
            "data": settings_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system")
async def get_system_settings():
    """Get system settings."""
    try:
        timelapse_enabled = db.get_system_setting('timelapse_enabled') or 'false'
        timelapse_interval = db.get_system_setting('timelapse_interval') or '300'
        
        return {
            "success": True,
            "data": {
                "timelapse_enabled": timelapse_enabled == 'true',
                "timelapse_interval": int(timelapse_interval)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/system/timelapse")
async def update_timelapse_settings(enabled: bool, interval: int = 300):
    """Update time-lapse settings."""
    try:
        db.set_system_setting('timelapse_enabled', 'true' if enabled else 'false')
        db.set_system_setting('timelapse_interval', str(interval))
        
        return {
            "success": True,
            "message": "Time-lapse settings updated",
            "data": {
                "enabled": enabled,
                "interval": interval
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
