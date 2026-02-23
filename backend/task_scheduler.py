"""Background Task Scheduler for Grow Tent Automation.

Uses APScheduler for scheduled tasks including:
- Daily AI photo analysis
- Periodic external server sync
- Daily report generation
- Time-lapse capture management
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None

from backend.config import (
    BASE_DIR, DATA_DIR, DATABASE_PATH,
    get_settings, get_secrets,
    AI_ANALYSIS_SCHEDULE_TIME, EXTERNAL_SYNC_INTERVAL,
    DAILY_REPORT_TIME, SCHEDULER_ENABLED
)
from backend.database import db

logger = logging.getLogger(__name__)


class TaskSchedulerError(Exception):
    """Custom exception for task scheduler errors."""
    pass


class TaskScheduler:
    """Manages background scheduled tasks using APScheduler."""
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.scheduler: Optional[BackgroundScheduler] = None
        self.running = False
        self._tasks_registered = False
        
        # Store references to task functions
        self._task_functions: Dict[str, Callable] = {}
        
        # External references (set later)
        self._ai_analyzer = None
        self._sync_module = None
        self._telegram_bot = None
        self._camera = None
        
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not installed. Scheduled tasks disabled.")
            return
        
        if not SCHEDULER_ENABLED:
            logger.info("Scheduler disabled in configuration.")
            return
        
        self._init_scheduler()
    
    def _init_scheduler(self):
        """Initialize the APScheduler instance."""
        if not APSCHEDULER_AVAILABLE:
            return
        
        try:
            # Configure job stores - use SQLite for persistence
            jobstores = {
                'default': SQLAlchemyJobStore(
                    url=f'sqlite:///{DATABASE_PATH}'
                )
            }
            
            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(10)
            }
            
            # Job defaults
            job_defaults = {
                'coalesce': True,  # Combine missed executions
                'max_instances': 1,  # Only one instance of each job
                'misfire_grace_time': 300  # 5 minutes grace for missed jobs
            }
            
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            
            logger.info("Task scheduler initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            self.scheduler = None
    
    def set_dependencies(self, ai_analyzer=None, sync_module=None, 
                        telegram_bot=None, camera=None):
        """Set external dependencies for tasks.
        
        Args:
            ai_analyzer: AI analyzer instance
            sync_module: External sync module instance
            telegram_bot: Telegram bot instance
            camera: Camera controller instance
        """
        self._ai_analyzer = ai_analyzer
        self._sync_module = sync_module
        self._telegram_bot = telegram_bot
        self._camera = camera
    
    def start(self):
        """Start the task scheduler."""
        if not self.scheduler:
            logger.warning("Scheduler not available")
            return False
        
        if self.running:
            logger.warning("Scheduler already running")
            return True
        
        try:
            # Register default tasks if not already done
            if not self._tasks_registered:
                self._register_default_tasks()
            
            self.scheduler.start()
            self.running = True
            logger.info("Task scheduler started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    def stop(self):
        """Stop the task scheduler."""
        if not self.scheduler or not self.running:
            return
        
        try:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("Task scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def _register_default_tasks(self):
        """Register default scheduled tasks."""
        settings = get_settings()
        
        # Daily AI analysis task
        ai_config = settings.get('ai_analysis', {})
        if ai_config.get('enabled', False):
            schedule_time = ai_config.get('daily_schedule_time', '12:00')
            self.add_daily_task(
                'daily_ai_analysis',
                self._run_daily_ai_analysis,
                schedule_time,
                "Daily AI Photo Analysis"
            )
        
        # External sync task
        sync_config = settings.get('external_sync', {})
        if sync_config.get('enabled', False):
            interval = sync_config.get('sync_interval', 300)
            self.add_interval_task(
                'external_sync',
                self._run_external_sync,
                interval,
                "External Server Sync"
            )
        
        # Daily report task
        scheduler_config = settings.get('scheduler', {})
        report_time = scheduler_config.get('daily_report_time', '08:00')
        self.add_daily_task(
            'daily_report',
            self._run_daily_report,
            report_time,
            "Daily Report Generation"
        )
        
        self._tasks_registered = True
        logger.info("Default tasks registered")
    
    def add_daily_task(self, task_id: str, func: Callable, 
                       time_str: str, description: str = "") -> bool:
        """Add a daily scheduled task.
        
        Args:
            task_id: Unique task identifier
            func: Function to execute
            time_str: Time to run (HH:MM format)
            description: Task description
            
        Returns:
            True if successful
        """
        if not self.scheduler:
            return False
        
        try:
            hour, minute = map(int, time_str.split(':'))
            
            self.scheduler.add_job(
                func,
                CronTrigger(hour=hour, minute=minute),
                id=task_id,
                name=description or task_id,
                replace_existing=True
            )
            
            self._task_functions[task_id] = func
            
            # Save to database for UI display
            db.save_scheduled_task(
                task_id, description or task_id,
                'daily', time_str, True
            )
            
            logger.info(f"Added daily task: {task_id} at {time_str}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add daily task {task_id}: {e}")
            return False
    
    def add_interval_task(self, task_id: str, func: Callable,
                          interval_seconds: int, description: str = "") -> bool:
        """Add an interval-based scheduled task.
        
        Args:
            task_id: Unique task identifier
            func: Function to execute
            interval_seconds: Interval between executions
            description: Task description
            
        Returns:
            True if successful
        """
        if not self.scheduler:
            return False
        
        try:
            self.scheduler.add_job(
                func,
                IntervalTrigger(seconds=interval_seconds),
                id=task_id,
                name=description or task_id,
                replace_existing=True
            )
            
            self._task_functions[task_id] = func
            
            # Save to database
            db.save_scheduled_task(
                task_id, description or task_id,
                'interval', str(interval_seconds), True
            )
            
            logger.info(f"Added interval task: {task_id} every {interval_seconds}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add interval task {task_id}: {e}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if successful
        """
        if not self.scheduler:
            return False
        
        try:
            self.scheduler.remove_job(task_id)
            self._task_functions.pop(task_id, None)
            logger.info(f"Removed task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a scheduled task."""
        if not self.scheduler:
            return False
        
        try:
            self.scheduler.pause_job(task_id)
            db.toggle_scheduled_task(task_id, False)
            logger.info(f"Paused task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}")
            return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        if not self.scheduler:
            return False
        
        try:
            self.scheduler.resume_job(task_id)
            db.toggle_scheduled_task(task_id, True)
            logger.info(f"Resumed task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False
    
    def run_task_now(self, task_id: str) -> bool:
        """Run a task immediately.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if successful
        """
        if task_id in self._task_functions:
            try:
                func = self._task_functions[task_id]
                func()
                db.update_task_run_time(task_id)
                logger.info(f"Manually executed task: {task_id}")
                return True
            except Exception as e:
                logger.error(f"Error executing task {task_id}: {e}")
                return False
        
        logger.warning(f"Task not found: {task_id}")
        return False
    
    def get_task_status(self) -> List[Dict[str, Any]]:
        """Get status of all scheduled tasks.
        
        Returns:
            List of task status dictionaries
        """
        tasks = []
        
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                task_info = {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'pending': job.pending,
                    'paused': job.next_run_time is None
                }
                
                # Get additional info from database
                db_task = db.get_scheduled_task(job.id)
                if db_task:
                    task_info['last_run'] = db_task.get('last_run')
                    task_info['run_count'] = db_task.get('run_count', 0)
                
                tasks.append(task_info)
        
        return tasks
    
    # ========================================================================
    # Task Implementation Functions
    # ========================================================================
    
    def _run_daily_ai_analysis(self):
        """Execute daily AI photo analysis task."""
        logger.info("Running daily AI analysis task")
        
        try:
            # Get active project
            project = db.get_active_project()
            if not project:
                logger.info("No active project for AI analysis")
                return
            
            # Capture photo if camera available
            photo_path = None
            if self._camera:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    photo_dir = DATA_DIR / "photos"
                    photo_path = photo_dir / f"analysis_{timestamp}.jpg"
                    self._camera.capture_photo(str(photo_path))
                    logger.info(f"Captured photo for analysis: {photo_path}")
                except Exception as e:
                    logger.error(f"Failed to capture photo: {e}")
                    # Try to use latest timelapse image instead
                    images = db.get_timelapse_images(project['id'])
                    if images:
                        photo_path = images[-1]['filepath']
            
            if not photo_path:
                logger.warning("No photo available for analysis")
                return
            
            # Run AI analysis
            if self._ai_analyzer and self._ai_analyzer.enabled:
                try:
                    result = self._ai_analyzer.analyze_photo(str(photo_path))
                    
                    # Save to database
                    analysis_id = db.save_ai_analysis(
                        project_id=project['id'],
                        photo_path=str(photo_path),
                        analysis_text=result.get('analysis_text', ''),
                        health_score=result.get('health_score'),
                        recommendations=result.get('recommendations', ''),
                        model=result.get('model', ''),
                        tokens_used=result.get('tokens_used')
                    )
                    
                    logger.info(f"AI analysis saved: ID {analysis_id}")
                    
                    # Send to Telegram if configured
                    if self._telegram_bot and self._ai_analyzer.send_to_telegram:
                        message = self._ai_analyzer.format_telegram_message(
                            result, project.get('name', '')
                        )
                        self._telegram_bot.send_message(message)
                    
                    # Sync to external server if configured
                    if self._sync_module and self._ai_analyzer.send_to_external:
                        analysis_data = db.get_ai_analysis(analysis_id)
                        if analysis_data:
                            self._sync_module.sync_analysis_report(analysis_data)
                            db.mark_analysis_synced(analysis_id)
                    
                    # Update task run time
                    db.update_task_run_time('daily_ai_analysis')
                    
                except Exception as e:
                    logger.error(f"AI analysis failed: {e}")
            else:
                logger.info("AI analyzer not available or not enabled")
                
        except Exception as e:
            logger.error(f"Daily AI analysis task error: {e}")
    
    def _run_external_sync(self):
        """Execute external server sync task."""
        logger.info("Running external sync task")
        
        try:
            if not self._sync_module or not self._sync_module.enabled:
                return
            
            # Get active project
            project = db.get_active_project()
            
            # Get latest sensor data
            sensor_data = db.get_latest_sensor_data()
            
            # Get latest photo path
            photo_path = None
            photos_dir = DATA_DIR / "photos"
            if photos_dir.exists():
                photos = sorted(photos_dir.glob("*.jpg"))
                if photos:
                    photo_path = str(photos[-1])
            
            # Run sync
            result = self._sync_module.sync_all(
                sensor_data=sensor_data,
                project=project,
                photo_path=photo_path
            )
            
            # Log result
            status = 'success' if result.get('success') else 'failed'
            db.log_sync(
                sync_type='full',
                status=status,
                details=str(result.get('results', {})),
                items_synced=result.get('synced', 0)
            )
            
            db.update_task_run_time('external_sync')
            
            logger.info(f"External sync completed: {result.get('synced')}/{result.get('total')} items")
            
        except Exception as e:
            logger.error(f"External sync task error: {e}")
            db.log_sync(
                sync_type='full',
                status='error',
                error_message=str(e)
            )
    
    def _run_daily_report(self):
        """Execute daily report generation task."""
        logger.info("Running daily report task")
        
        try:
            project = db.get_active_project()
            if not project:
                logger.info("No active project for daily report")
                return
            
            # Get today's sensor data
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            sensor_data = db.get_sensor_data(
                project_id=project['id'],
                start_date=today,
                limit=1000
            )
            
            if not sensor_data:
                logger.info("No sensor data for today")
                return
            
            # Calculate statistics
            temps = [d['temperature'] for d in sensor_data if d.get('temperature')]
            humidities = [d['humidity'] for d in sensor_data if d.get('humidity')]
            
            report = f"\ud83d\udcca *Daily Report - {datetime.now().strftime('%Y-%m-%d')}*\n\n"
            report += f"\ud83c\udf3f *Project:* {project.get('name', 'Unknown')}\n\n"
            
            if temps:
                report += f"\ud83c\udf21 *Temperature:*\n"
                report += f"  Min: {min(temps):.1f}°C\n"
                report += f"  Max: {max(temps):.1f}°C\n"
                report += f"  Avg: {sum(temps)/len(temps):.1f}°C\n\n"
            
            if humidities:
                report += f"\ud83d\udca7 *Humidity:*\n"
                report += f"  Min: {min(humidities):.1f}%\n"
                report += f"  Max: {max(humidities):.1f}%\n"
                report += f"  Avg: {sum(humidities)/len(humidities):.1f}%\n\n"
            
            # Get timelapse count
            timelapse_count = db.get_timelapse_image_count(project['id'])
            report += f"\ud83d\udcf7 *Time-lapse Images:* {timelapse_count}\n"
            
            # Get latest AI analysis
            analysis = db.get_latest_ai_analysis(project['id'])
            if analysis:
                report += f"\n\ud83e\udd16 *Latest AI Health Score:* {analysis.get('health_score', 'N/A')}/10\n"
            
            # Send to Telegram
            if self._telegram_bot:
                self._telegram_bot.send_message(report)
            
            db.update_task_run_time('daily_report')
            logger.info("Daily report sent")
            
        except Exception as e:
            logger.error(f"Daily report task error: {e}")


# Singleton instance
_task_scheduler: Optional[TaskScheduler] = None


def get_task_scheduler() -> Optional[TaskScheduler]:
    """Get the global task scheduler instance."""
    return _task_scheduler


def init_task_scheduler() -> TaskScheduler:
    """Initialize the global task scheduler instance.
    
    Returns:
        Initialized TaskScheduler instance
    """
    global _task_scheduler
    _task_scheduler = TaskScheduler()
    return _task_scheduler
