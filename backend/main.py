"""Main FastAPI application for grow tent automation system."""
import sys
import logging
import signal
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import (
    HOST, PORT, BASE_DIR, DATA_DIR,
    get_settings, get_secrets,
    SCHEDULER_ENABLED
)
from backend.utils.logger import setup_logging
from backend.automation.engine import AutomationEngine
from backend.telegram_bot.bot import TelegramBot
from backend.external_sync import init_sync_module, get_sync_module
from backend.analysis.ai_analyzer import init_ai_analyzer, get_ai_analyzer
from backend.task_scheduler import init_task_scheduler, get_task_scheduler
from backend.database import db

# Import API routers
from backend.api import (
    projects, sensors, devices, settings, diary, 
    timelapse, camera, plant_health
)
from backend.api import sync as sync_api
from backend.api import analysis as analysis_api
from backend.api import system_settings as system_settings_api

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
automation_engine: AutomationEngine = None
telegram_bot: TelegramBot = None
sync_module = None
ai_analyzer = None
task_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global automation_engine, telegram_bot, sync_module, ai_analyzer, task_scheduler
    
    logger.info("🚀 Starting Grow Tent Automation System...")
    
    # Load configuration
    config = get_settings()
    secrets = get_secrets()
    
    # Initialize automation engine
    try:
        automation_engine = AutomationEngine()
        automation_engine.start()
        logger.info("✅ Automation engine started")
    except Exception as e:
        logger.error(f"Failed to start automation engine: {e}")
        automation_engine = None
    
    # Set automation engine reference in API modules
    if automation_engine:
        devices.set_automation_engine(automation_engine)
        camera.set_automation_engine(automation_engine)
    
    # Initialize external sync module
    try:
        sync_module = init_sync_module(config, secrets)
        sync_api.set_sync_module(sync_module)
        if sync_module.enabled:
            logger.info("✅ External sync module initialized")
        else:
            logger.info("ℹ️ External sync module disabled (not configured)")
    except Exception as e:
        logger.error(f"Failed to initialize sync module: {e}")
        sync_module = None
    
    # Initialize AI analyzer
    try:
        ai_analyzer = init_ai_analyzer(config, secrets)
        if ai_analyzer.enabled:
            logger.info("✅ AI analyzer initialized")
        else:
            logger.info("ℹ️ AI analyzer disabled (not configured)")
    except Exception as e:
        logger.error(f"Failed to initialize AI analyzer: {e}")
        ai_analyzer = None
    
    # Initialize Telegram bot in separate thread
    try:
        telegram_bot = TelegramBot(automation_engine)
        telegram_thread = threading.Thread(target=telegram_bot.start, daemon=True)
        telegram_thread.start()
        logger.info("✅ Telegram bot started")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")
        telegram_bot = None
    
    # Set module references for analysis API
    analysis_api.set_modules(
        ai_analyzer=ai_analyzer,
        telegram_bot=telegram_bot,
        sync_module=sync_module,
        camera=automation_engine.camera if automation_engine else None
    )
    
    # Initialize task scheduler
    if SCHEDULER_ENABLED:
        try:
            task_scheduler = init_task_scheduler()
            task_scheduler.set_dependencies(
                ai_analyzer=ai_analyzer,
                sync_module=sync_module,
                telegram_bot=telegram_bot,
                camera=automation_engine.camera if automation_engine else None
            )
            task_scheduler.start()
            logger.info("✅ Task scheduler started")
        except Exception as e:
            logger.error(f"Failed to start task scheduler: {e}")
            task_scheduler = None
    else:
        logger.info("ℹ️ Task scheduler disabled in configuration")
    
    # Resume time-lapse for active projects after restart
    _resume_timelapse_captures()
    
    logger.info("✅ System started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    
    if task_scheduler:
        task_scheduler.stop()
    
    if automation_engine:
        automation_engine.stop()
    
    if telegram_bot:
        telegram_bot.stop()
    
    logger.info("👋 Shutdown complete")


def _resume_timelapse_captures():
    """Resume time-lapse captures for active projects after restart."""
    try:
        projects_needing_timelapse = db.get_projects_needing_timelapse()
        for project in projects_needing_timelapse:
            logger.info(
                f"Resuming time-lapse for project: {project['name']} "
                f"(ID: {project['id']}, interval: {project.get('timelapse_interval', 300)}s)"
            )
            # The automation engine handles the actual capture based on project settings
    except Exception as e:
        logger.error(f"Error resuming timelapse captures: {e}")


# Create FastAPI app
app = FastAPI(
    title="Grow Tent Automation API",
    description="Production-ready Raspberry Pi grow tent automation system with AI analysis and external sync",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(projects.router)
app.include_router(sensors.router)
app.include_router(devices.router)
app.include_router(settings.router)
app.include_router(diary.router)
app.include_router(timelapse.router)
app.include_router(camera.router)
app.include_router(plant_health.router)
app.include_router(sync_api.router)
app.include_router(analysis_api.router)
app.include_router(system_settings_api.router)

# Mount static files
frontend_dir = BASE_DIR / "frontend"
data_dir = BASE_DIR / "data"

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - serve frontend."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Grow Tent Automation API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check automation engine
        automation_status = "running" if automation_engine and automation_engine.running else "stopped"
        
        # Check Telegram bot
        telegram_status = "running" if telegram_bot and telegram_bot.running else "stopped"
        
        # Check sync module
        sync_status = "enabled" if sync_module and sync_module.enabled else "disabled"
        
        # Check AI analyzer
        ai_status = "enabled" if ai_analyzer and ai_analyzer.enabled else "disabled"
        
        # Check scheduler
        scheduler_status = "running" if task_scheduler and task_scheduler.running else "stopped"
        
        # Get last sync status
        last_sync = db.get_last_successful_sync('full')
        
        # Get active project
        active_project = db.get_active_project()
        
        # Get latest sensor data
        sensor_data = db.get_latest_sensor_data()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "automation_engine": automation_status,
                "telegram_bot": telegram_status,
                "external_sync": sync_status,
                "ai_analyzer": ai_status,
                "task_scheduler": scheduler_status
            },
            "data": {
                "active_project": active_project.get('name') if active_project else None,
                "last_sync": last_sync.get('timestamp') if last_sync else None,
                "latest_sensor_reading": sensor_data.get('timestamp') if sensor_data else None
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/api/system/info")
async def system_info():
    """Get system information."""
    try:
        import platform
        from backend.config import GPIO_PINS
        
        return {
            "success": True,
            "data": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "api_version": "2.0.0",
                "devices": list(GPIO_PINS.keys()),
                "automation_running": automation_engine.running if automation_engine else False,
                "telegram_enabled": telegram_bot is not None and telegram_bot.running,
                "external_sync_enabled": sync_module.enabled if sync_module else False,
                "ai_analysis_enabled": ai_analyzer.enabled if ai_analyzer else False,
                "scheduler_enabled": task_scheduler is not None and task_scheduler.running
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/system/status")
async def system_status():
    """Get detailed system status."""
    try:
        # Get active project with timelapse info
        active_project = db.get_active_project()
        if active_project:
            active_project['timelapse_count'] = db.get_timelapse_image_count(active_project['id'])
        
        # Get latest sensor data
        sensor_data = db.get_latest_sensor_data()
        
        # Get latest AI analysis
        latest_analysis = db.get_latest_ai_analysis()
        
        # Get scheduled tasks status
        scheduled_tasks = []
        if task_scheduler:
            scheduled_tasks = task_scheduler.get_task_status()
        
        # Get sync status
        last_sync = db.get_last_successful_sync('full')
        
        return {
            "success": True,
            "data": {
                "active_project": active_project,
                "sensor_data": sensor_data,
                "latest_analysis": {
                    "timestamp": latest_analysis.get('timestamp') if latest_analysis else None,
                    "health_score": latest_analysis.get('health_score') if latest_analysis else None
                } if latest_analysis else None,
                "last_sync": {
                    "timestamp": last_sync.get('timestamp') if last_sync else None,
                    "items_synced": last_sync.get('items_synced') if last_sync else 0
                } if last_sync else None,
                "scheduled_tasks": scheduled_tasks
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Signal handlers for graceful shutdown
def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {HOST}:{PORT}")
    logger.info(f"Web UI: http://{HOST}:{PORT}")
    logger.info(f"API Docs: http://{HOST}:{PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    )
