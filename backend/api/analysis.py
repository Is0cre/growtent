"""AI Analysis API endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pathlib import Path

from backend.database import db
from backend.analysis.ai_analyzer import get_ai_analyzer, AIAnalysisError
from backend.config import DATA_DIR

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# References to modules (set by main.py)
_ai_analyzer = None
_telegram_bot = None
_sync_module = None
_camera = None


def set_modules(ai_analyzer=None, telegram_bot=None, sync_module=None, camera=None):
    """Set module references."""
    global _ai_analyzer, _telegram_bot, _sync_module, _camera
    if ai_analyzer:
        _ai_analyzer = ai_analyzer
    if telegram_bot:
        _telegram_bot = telegram_bot
    if sync_module:
        _sync_module = sync_module
    if camera:
        _camera = camera


class AnalysisRequest(BaseModel):
    photo_path: Optional[str] = None
    custom_prompt: Optional[str] = None
    send_to_telegram: Optional[bool] = True
    sync_to_external: Optional[bool] = True


@router.get("/status")
async def get_analysis_status():
    """Get AI analysis status."""
    try:
        ai_analyzer = _ai_analyzer or get_ai_analyzer()
        
        # Get latest analysis
        latest = db.get_latest_ai_analysis()
        
        return {
            "success": True,
            "data": {
                "enabled": ai_analyzer.enabled if ai_analyzer else False,
                "configured": bool(ai_analyzer and ai_analyzer.api_key) if ai_analyzer else False,
                "model": ai_analyzer.model if ai_analyzer else None,
                "latest_analysis": latest.get('timestamp') if latest else None,
                "latest_health_score": latest.get('health_score') if latest else None,
                "total_analyses": len(db.get_ai_analyses(limit=10000))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/now")
async def analyze_now(background_tasks: BackgroundTasks, request: Optional[AnalysisRequest] = None):
    """Run AI analysis now."""
    try:
        ai_analyzer = _ai_analyzer or get_ai_analyzer()
        
        if not ai_analyzer:
            raise HTTPException(status_code=400, detail="AI analyzer not initialized")
        
        if not ai_analyzer.enabled:
            raise HTTPException(status_code=400, detail="AI analysis not enabled. Configure OpenAI API key.")
        
        # Get or capture photo
        photo_path = None
        if request and request.photo_path:
            photo_path = request.photo_path
            if not Path(photo_path).exists():
                raise HTTPException(status_code=404, detail="Photo not found")
        else:
            # Try to capture new photo
            if _camera:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    photo_dir = DATA_DIR / "photos"
                    photo_dir.mkdir(parents=True, exist_ok=True)
                    photo_path = str(photo_dir / f"analysis_{timestamp}.jpg")
                    _camera.capture_photo(photo_path)
                except Exception as e:
                    # Try to use latest existing photo
                    pass
            
            # If no camera or capture failed, use latest photo
            if not photo_path or not Path(photo_path).exists():
                photos_dir = DATA_DIR / "photos"
                if photos_dir.exists():
                    photos = sorted(photos_dir.glob("*.jpg"))
                    if photos:
                        photo_path = str(photos[-1])
        
        if not photo_path or not Path(photo_path).exists():
            raise HTTPException(status_code=404, detail="No photo available for analysis")
        
        # Run analysis in background
        send_telegram = request.send_to_telegram if request else True
        sync_external = request.sync_to_external if request else True
        custom_prompt = request.custom_prompt if request else None
        
        background_tasks.add_task(
            _run_analysis, 
            photo_path, 
            custom_prompt,
            send_telegram, 
            sync_external
        )
        
        return {
            "success": True,
            "message": "Analysis started in background",
            "data": {"photo_path": photo_path}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_analyses(project_id: Optional[int] = None, limit: int = 50):
    """Get AI analyses."""
    try:
        analyses = db.get_ai_analyses(project_id=project_id, limit=limit)
        return {
            "success": True,
            "data": analyses,
            "count": len(analyses)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: int):
    """Get a specific AI analysis."""
    try:
        analysis = db.get_ai_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {"success": True, "data": analysis}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_analysis(project_id: Optional[int] = None):
    """Get the latest AI analysis."""
    try:
        analysis = db.get_latest_ai_analysis(project_id)
        if not analysis:
            return {"success": True, "data": None}
        
        return {"success": True, "data": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{analysis_id}/sync")
async def sync_analysis(analysis_id: int):
    """Sync a specific analysis to external server."""
    try:
        analysis = db.get_ai_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if not _sync_module or not _sync_module.enabled:
            raise HTTPException(status_code=400, detail="External sync not enabled")
        
        result = _sync_module.sync_analysis_report(analysis)
        
        if result.get('success'):
            db.mark_analysis_synced(analysis_id)
        
        return {
            "success": result.get('success', False),
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_analysis(photo_path: str, custom_prompt: Optional[str],
                       send_telegram: bool, sync_external: bool):
    """Background task to run AI analysis."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        ai_analyzer = _ai_analyzer or get_ai_analyzer()
        if not ai_analyzer:
            logger.error("AI analyzer not available")
            return
        
        # Run analysis
        result = ai_analyzer.analyze_photo(photo_path, custom_prompt)
        
        # Get active project
        project = db.get_active_project()
        project_id = project['id'] if project else None
        
        # Save to database
        analysis_id = db.save_ai_analysis(
            project_id=project_id,
            photo_path=photo_path,
            analysis_text=result.get('analysis_text', ''),
            health_score=result.get('health_score'),
            recommendations=result.get('recommendations', ''),
            model=result.get('model', ''),
            tokens_used=result.get('tokens_used')
        )
        
        logger.info(f"Analysis saved: ID {analysis_id}, health score: {result.get('health_score')}")
        
        # Send to Telegram
        if send_telegram and _telegram_bot and ai_analyzer.send_to_telegram:
            try:
                message = ai_analyzer.format_telegram_message(
                    result, project.get('name', '') if project else ''
                )
                _telegram_bot.send_message(message)
                logger.info("Analysis sent to Telegram")
            except Exception as e:
                logger.error(f"Failed to send to Telegram: {e}")
        
        # Sync to external server
        if sync_external and _sync_module and _sync_module.enabled:
            try:
                analysis_data = db.get_ai_analysis(analysis_id)
                if analysis_data:
                    _sync_module.sync_analysis_report(analysis_data)
                    db.mark_analysis_synced(analysis_id)
                    logger.info("Analysis synced to external server")
            except Exception as e:
                logger.error(f"Failed to sync analysis: {e}")
        
    except AIAnalysisError as e:
        logger.error(f"AI analysis error: {e}")
    except Exception as e:
        logger.error(f"Analysis task error: {e}")
