"""System Settings API endpoints for web-based configuration."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import yaml

from backend.database import db
from backend.config import (
    get_settings, get_secrets, save_settings, save_secrets,
    reload_config, SETTINGS_FILE, SECRETS_FILE
)
from backend.task_scheduler import get_task_scheduler

router = APIRouter(prefix="/api/system-settings", tags=["system-settings"])


class TimelapseSettings(BaseModel):
    default_interval: int = 300
    default_fps: int = 30
    auto_start_on_project: bool = True


class AlertSettings(BaseModel):
    enabled: bool = True
    temp_min: float = 15.0
    temp_max: float = 32.0
    humidity_min: float = 40.0
    humidity_max: float = 80.0
    notification_interval: int = 300


class ExternalSyncSettings(BaseModel):
    enabled: bool = False
    sync_interval: int = 300
    sync_photos: bool = True
    sync_sensor_data: bool = True
    sync_project_info: bool = True
    sync_analysis_reports: bool = True


class ExternalServerSecrets(BaseModel):
    enabled: bool = False
    url: str = ""
    auth_type: str = "api_key"
    api_key: str = ""
    bearer_token: str = ""


class AIAnalysisSettings(BaseModel):
    enabled: bool = False
    daily_schedule_time: str = "12:00"
    send_to_telegram: bool = True
    send_to_external_server: bool = True


class OpenRouterSecrets(BaseModel):
    api_key: str = ""
    model: str = "anthropic/claude-3.5-sonnet"


class TelegramSecrets(BaseModel):
    bot_token: str = ""
    chat_id: str = ""


@router.get("/")
async def get_all_settings():
    """Get all system settings (non-sensitive)."""
    try:
        settings = get_settings()
        return {"success": True, "data": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timelapse")
async def get_timelapse_settings():
    """Get time-lapse settings."""
    try:
        settings = get_settings()
        timelapse = settings.get('timelapse', {
            'default_interval': 300,
            'default_fps': 30,
            'auto_start_on_project': True
        })
        return {"success": True, "data": timelapse}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/timelapse")
async def update_timelapse_settings(settings: TimelapseSettings):
    """Update time-lapse settings."""
    try:
        current = get_settings()
        current['timelapse'] = settings.dict()
        save_settings(current)
        reload_config()
        return {"success": True, "message": "Time-lapse settings updated", "data": settings.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alert_settings():
    """Get alert settings."""
    try:
        settings = get_settings()
        alerts = settings.get('alerts', {})
        
        # Flatten the structure for easier form handling
        result = {
            'enabled': alerts.get('enabled', True),
            'temp_min': alerts.get('temperature', {}).get('min', 15.0),
            'temp_max': alerts.get('temperature', {}).get('max', 32.0),
            'humidity_min': alerts.get('humidity', {}).get('min', 40.0),
            'humidity_max': alerts.get('humidity', {}).get('max', 80.0),
            'notification_interval': alerts.get('notification_interval', 300)
        }
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts")
async def update_alert_settings(settings: AlertSettings):
    """Update alert settings."""
    try:
        current = get_settings()
        current['alerts'] = {
            'enabled': settings.enabled,
            'temperature': {
                'min': settings.temp_min,
                'max': settings.temp_max
            },
            'humidity': {
                'min': settings.humidity_min,
                'max': settings.humidity_max
            },
            'notification_interval': settings.notification_interval
        }
        save_settings(current)
        reload_config()
        
        # Also update database alert settings
        db.save_alert_settings({
            'enabled': settings.enabled,
            'temp_min': settings.temp_min,
            'temp_max': settings.temp_max,
            'humidity_min': settings.humidity_min,
            'humidity_max': settings.humidity_max,
            'notification_interval': settings.notification_interval
        })
        
        return {"success": True, "message": "Alert settings updated", "data": settings.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/external-sync")
async def get_external_sync_settings():
    """Get external sync settings."""
    try:
        settings = get_settings()
        sync_settings = settings.get('external_sync', {})
        
        # Get secrets (mask sensitive values)
        secrets = get_secrets()
        server_secrets = secrets.get('external_server', {})
        
        result = {
            **sync_settings,
            'server_url': server_secrets.get('url', ''),
            'auth_type': server_secrets.get('auth_type', 'api_key'),
            'server_enabled': server_secrets.get('enabled', False),
            'has_api_key': bool(server_secrets.get('api_key')),
            'has_bearer_token': bool(server_secrets.get('bearer_token'))
        }
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/external-sync")
async def update_external_sync_settings(settings: ExternalSyncSettings):
    """Update external sync settings."""
    try:
        current = get_settings()
        current['external_sync'] = {
            **current.get('external_sync', {}),
            'enabled': settings.enabled,
            'sync_interval': settings.sync_interval,
            'sync_photos': settings.sync_photos,
            'sync_sensor_data': settings.sync_sensor_data,
            'sync_project_info': settings.sync_project_info,
            'sync_analysis_reports': settings.sync_analysis_reports
        }
        save_settings(current)
        reload_config()
        return {"success": True, "message": "External sync settings updated", "data": settings.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/external-server")
async def update_external_server_secrets(secrets_data: ExternalServerSecrets):
    """Update external server secrets."""
    try:
        current = get_secrets()
        current['external_server'] = {
            'enabled': secrets_data.enabled,
            'url': secrets_data.url,
            'auth_type': secrets_data.auth_type,
            'api_key': secrets_data.api_key if secrets_data.api_key else current.get('external_server', {}).get('api_key', ''),
            'bearer_token': secrets_data.bearer_token if secrets_data.bearer_token else current.get('external_server', {}).get('bearer_token', ''),
            'basic_username': current.get('external_server', {}).get('basic_username', ''),
            'basic_password': current.get('external_server', {}).get('basic_password', '')
        }
        save_secrets(current)
        reload_config()
        return {"success": True, "message": "External server settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-analysis")
async def get_ai_analysis_settings():
    """Get AI analysis settings."""
    try:
        settings = get_settings()
        ai_settings = settings.get('ai_analysis', {})
        
        # Check if API key is configured (support both openrouter and legacy openai)
        secrets = get_secrets()
        openrouter_secrets = secrets.get('openrouter', secrets.get('openai', {}))
        
        result = {
            'enabled': ai_settings.get('enabled', False),
            'daily_schedule_time': ai_settings.get('daily_schedule_time', '12:00'),
            'send_to_telegram': ai_settings.get('send_to_telegram', True),
            'send_to_external_server': ai_settings.get('send_to_external_server', True),
            'has_api_key': bool(openrouter_secrets.get('api_key')),
            'model': openrouter_secrets.get('model', 'anthropic/claude-3.5-sonnet')
        }
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ai-analysis")
async def update_ai_analysis_settings(settings: AIAnalysisSettings):
    """Update AI analysis settings."""
    try:
        current = get_settings()
        current['ai_analysis'] = {
            **current.get('ai_analysis', {}),
            'enabled': settings.enabled,
            'daily_schedule_time': settings.daily_schedule_time,
            'send_to_telegram': settings.send_to_telegram,
            'send_to_external_server': settings.send_to_external_server
        }
        save_settings(current)
        reload_config()
        return {"success": True, "message": "AI analysis settings updated", "data": settings.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/openrouter")
async def update_openrouter_secrets(secrets_data: OpenRouterSecrets):
    """Update OpenRouter API secrets."""
    try:
        current = get_secrets()
        current['openrouter'] = {
            'api_key': secrets_data.api_key if secrets_data.api_key else current.get('openrouter', current.get('openai', {})).get('api_key', ''),
            'model': secrets_data.model
        }
        # Remove legacy openai key if exists
        if 'openai' in current:
            del current['openai']
        save_secrets(current)
        reload_config()
        return {"success": True, "message": "OpenRouter settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openrouter/models")
async def get_openrouter_models():
    """Get available OpenRouter vision models."""
    from backend.analysis.ai_analyzer import OPENROUTER_VISION_MODELS
    return {"success": True, "data": OPENROUTER_VISION_MODELS}


@router.get("/telegram")
async def get_telegram_settings():
    """Get Telegram settings (masked)."""
    try:
        secrets = get_secrets()
        telegram = secrets.get('telegram', {})
        
        # Mask the bot token
        bot_token = telegram.get('bot_token', '')
        masked_token = f"{bot_token[:10]}...{bot_token[-5:]}" if len(bot_token) > 15 else '****'
        
        return {
            "success": True,
            "data": {
                "has_bot_token": bool(bot_token),
                "masked_bot_token": masked_token if bot_token else None,
                "chat_id": telegram.get('chat_id', '')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/telegram")
async def update_telegram_secrets(secrets_data: TelegramSecrets):
    """Update Telegram secrets."""
    try:
        current = get_secrets()
        current['telegram'] = {
            'bot_token': secrets_data.bot_token if secrets_data.bot_token else current.get('telegram', {}).get('bot_token', ''),
            'chat_id': secrets_data.chat_id if secrets_data.chat_id else current.get('telegram', {}).get('chat_id', '')
        }
        save_secrets(current)
        reload_config()
        return {"success": True, "message": "Telegram settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled-tasks")
async def get_scheduled_tasks():
    """Get scheduled task status."""
    try:
        scheduler = get_task_scheduler()
        if scheduler:
            tasks = scheduler.get_task_status()
        else:
            # Fall back to database
            tasks = db.get_all_scheduled_tasks()
        
        return {"success": True, "data": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-tasks/{task_id}/run")
async def run_scheduled_task(task_id: str):
    """Run a scheduled task immediately."""
    try:
        scheduler = get_task_scheduler()
        if not scheduler:
            raise HTTPException(status_code=400, detail="Scheduler not available")
        
        success = scheduler.run_task_now(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"success": True, "message": f"Task {task_id} executed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str, enabled: bool = True):
    """Enable or disable a scheduled task."""
    try:
        scheduler = get_task_scheduler()
        if not scheduler:
            raise HTTPException(status_code=400, detail="Scheduler not available")
        
        if enabled:
            success = scheduler.resume_task(task_id)
        else:
            success = scheduler.pause_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        
        action = "enabled" if enabled else "disabled"
        return {"success": True, "message": f"Task {task_id} {action}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_configuration():
    """Reload configuration from files."""
    try:
        reload_config()
        return {"success": True, "message": "Configuration reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
