"""Main FastAPI application for grow tent automation system."""
import sys
import logging
import signal
import threading
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import HOST, PORT, BASE_DIR
from backend.utils.logger import setup_logging
from backend.automation.engine import AutomationEngine
from backend.telegram_bot.bot import TelegramBot

# Import API routers
from backend.api import projects, sensors, devices, settings, diary, timelapse, camera, plant_health

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
automation_engine: AutomationEngine = None
telegram_bot: TelegramBot = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global automation_engine, telegram_bot
    
    logger.info("🚀 Starting Grow Tent Automation System...")
    
    # Initialize automation engine
    automation_engine = AutomationEngine()
    automation_engine.start()
    
    # Set automation engine reference in API modules
    devices.set_automation_engine(automation_engine)
    camera.set_automation_engine(automation_engine)
    
    # Initialize Telegram bot in separate thread
    telegram_bot = TelegramBot(automation_engine)
    telegram_thread = threading.Thread(target=telegram_bot.start, daemon=True)
    telegram_thread.start()
    
    logger.info("✅ System started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    automation_engine.stop()
    telegram_bot.stop()
    logger.info("👋 Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Grow Tent Automation API",
    description="Production-ready Raspberry Pi grow tent automation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local network access
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
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "automation_engine": "running" if automation_engine and automation_engine.running else "stopped",
        "telegram_bot": "running" if telegram_bot and telegram_bot.running else "stopped"
    }

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
                "devices": list(GPIO_PINS.keys()),
                "automation_running": automation_engine.running if automation_engine else False,
                "telegram_enabled": telegram_bot is not None
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
