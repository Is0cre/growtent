"""Automation engine - main control loop for grow tent automation.

Runs in background thread and handles:
- Continuous sensor data reading
- Device control logic evaluation
- Data logging to database
- Alert checking and notifications
- Project-integrated time-lapse image capture
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from backend.hardware.relay import RelayController
from backend.hardware.sensor import BME680Sensor
from backend.hardware.camera import CameraController
from backend.database import db
from backend.automation.scheduler import Scheduler
from backend.config import (
    SENSOR_READ_INTERVAL, 
    DATA_LOG_INTERVAL,
    DEFAULT_DEVICE_SETTINGS,
    DEFAULT_ALERT_SETTINGS,
    GPIO_PINS,
    DATA_DIR,
    get_project_timelapse_dir
)

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Main automation engine for grow tent control."""
    
    def __init__(self):
        """Initialize automation engine."""
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Initialize hardware controllers with error handling
        logger.info("Initializing hardware controllers...")
        self.relay = self._init_relay()
        self.sensor = self._init_sensor()
        self.camera = self._init_camera()
        
        # Initialize scheduler
        self.scheduler = Scheduler()
        
        # Track last data log time
        self.last_data_log = datetime.now()
        self.last_alert_check = datetime.now()
        
        # Track timelapse per project
        self.project_timelapse_timers: Dict[int, datetime] = {}
        
        # Alert state tracking (to avoid spam)
        self.active_alerts: Dict[str, datetime] = {}
        
        # Hardware health status
        self.hardware_status = {
            'relay': self.relay is not None,
            'sensor': self.sensor is not None,
            'camera': self.camera is not None
        }
        
        # Initialize device settings if not in database
        self._init_device_settings()
        self._init_alert_settings()
        
        logger.info(f"Automation engine initialized. Hardware status: {self.hardware_status}")
    
    def _init_relay(self) -> Optional[RelayController]:
        """Initialize relay controller with error handling."""
        try:
            return RelayController()
        except Exception as e:
            logger.error(f"Failed to initialize relay controller: {e}")
            return None
    
    def _init_sensor(self) -> Optional[BME680Sensor]:
        """Initialize sensor with error handling."""
        try:
            return BME680Sensor()
        except Exception as e:
            logger.error(f"Failed to initialize BME680 sensor: {e}")
            return None
    
    def _init_camera(self) -> Optional[CameraController]:
        """Initialize camera with error handling."""
        try:
            return CameraController()
        except Exception as e:
            logger.error(f"Failed to initialize camera controller: {e}")
            return None
    
    def _init_device_settings(self):
        """Initialize default device settings in database if not present."""
        try:
            existing_settings = db.get_all_device_settings()
            
            for device_name in GPIO_PINS.keys():
                if device_name not in existing_settings:
                    default = DEFAULT_DEVICE_SETTINGS.get(device_name, {
                        "enabled": True,
                        "schedule": [],
                        "mode": "manual"
                    })
                    logger.info(f"Initializing default settings for {device_name}")
                    db.save_device_settings(device_name, default)
        except Exception as e:
            logger.error(f"Error initializing device settings: {e}")
    
    def _init_alert_settings(self):
        """Initialize default alert settings if not present."""
        try:
            existing_settings = db.get_alert_settings()
            if not existing_settings:
                logger.info("Initializing default alert settings")
                db.save_alert_settings(DEFAULT_ALERT_SETTINGS)
        except Exception as e:
            logger.error(f"Error initializing alert settings: {e}")
    
    def start(self):
        """Start the automation engine in a background thread."""
        if self.running:
            logger.warning("Automation engine already running")
            return
        
        logger.info("Starting automation engine...")
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Automation engine started")
    
    def stop(self):
        """Stop the automation engine."""
        if not self.running:
            logger.warning("Automation engine not running")
            return
        
        logger.info("Stopping automation engine...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=10)
        
        # Clean up hardware
        if self.relay:
            try:
                self.relay.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up relay: {e}")
        
        if self.camera:
            try:
                self.camera.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up camera: {e}")
        
        logger.info("Automation engine stopped")
    
    def _run(self):
        """Main automation loop (runs in background thread)."""
        logger.info("Automation engine main loop started")
        
        # Resume timelapse timers from database
        self._resume_timelapse_timers()
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.running:
            try:
                # Read sensor data
                sensor_data = None
                if self.sensor:
                    try:
                        sensor_data = self.sensor.read()
                    except Exception as e:
                        logger.error(f"Sensor read error: {e}")
                        self.hardware_status['sensor'] = False
                
                if sensor_data:
                    self.hardware_status['sensor'] = True
                    
                    # Log data to database periodically
                    if (datetime.now() - self.last_data_log).total_seconds() >= DATA_LOG_INTERVAL:
                        self._log_sensor_data(sensor_data)
                        self.last_data_log = datetime.now()
                    
                    # Evaluate control logic
                    self._evaluate_control_logic(sensor_data)
                    
                    # Check alerts
                    if (datetime.now() - self.last_alert_check).total_seconds() >= 60:
                        self._check_alerts(sensor_data)
                        self.last_alert_check = datetime.now()
                
                # Check project-based time-lapse capture
                self._check_project_timelapse_capture()
                
                # Reset error counter on success
                consecutive_errors = 0
                
                # Sleep before next iteration
                time.sleep(SENSOR_READ_INTERVAL)
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in automation loop (attempt {consecutive_errors}): {e}", exc_info=True)
                
                # If too many consecutive errors, wait longer
                if consecutive_errors >= max_consecutive_errors:
                    logger.warning(f"Too many consecutive errors, backing off for 60 seconds")
                    time.sleep(60)
                    consecutive_errors = 0
                else:
                    time.sleep(SENSOR_READ_INTERVAL)
    
    def _resume_timelapse_timers(self):
        """Resume timelapse timers from database for active projects."""
        try:
            projects = db.get_projects_needing_timelapse()
            for project in projects:
                project_id = project['id']
                last_capture = project.get('timelapse_last_capture')
                
                if last_capture:
                    # Parse datetime
                    if isinstance(last_capture, str):
                        try:
                            last_capture = datetime.fromisoformat(last_capture.replace('Z', '+00:00'))
                        except:
                            last_capture = datetime.now() - timedelta(hours=1)
                    self.project_timelapse_timers[project_id] = last_capture
                else:
                    # Start fresh
                    self.project_timelapse_timers[project_id] = datetime.now()
                
                logger.info(f"Resumed timelapse timer for project {project_id}: {project['name']}")
        except Exception as e:
            logger.error(f"Error resuming timelapse timers: {e}")
    
    def _log_sensor_data(self, sensor_data: Dict[str, float]):
        """Log sensor data to database."""
        try:
            project = db.get_active_project()
            project_id = project['id'] if project else None
            
            db.log_sensor_data(
                project_id=project_id,
                temperature=sensor_data['temperature'],
                humidity=sensor_data['humidity'],
                pressure=sensor_data['pressure'],
                gas_resistance=sensor_data['gas_resistance']
            )
            
            logger.debug(f"Logged sensor data for project {project_id}")
            
        except Exception as e:
            logger.error(f"Error logging sensor data: {e}")
    
    def _evaluate_control_logic(self, sensor_data: Dict[str, float]):
        """Evaluate control logic for all devices."""
        if not self.relay:
            return
        
        try:
            temp = sensor_data['temperature']
            humidity = sensor_data['humidity']
            
            all_settings = db.get_all_device_settings()
            
            for device_name in GPIO_PINS.keys():
                try:
                    settings = all_settings.get(device_name, DEFAULT_DEVICE_SETTINGS.get(device_name, {}))
                    
                    should_be_on = self.scheduler.evaluate_device(
                        device_name, settings, temp, humidity
                    )
                    
                    if should_be_on is None:
                        continue
                    
                    current_state = self.relay.get_state(device_name)
                    
                    if should_be_on and not current_state:
                        logger.info(f"Turning ON {device_name} (auto control)")
                        self.relay.turn_on(device_name)
                        db.update_device_state(device_name, 1)
                        
                    elif not should_be_on and current_state:
                        logger.info(f"Turning OFF {device_name} (auto control)")
                        self.relay.turn_off(device_name)
                        db.update_device_state(device_name, 0)
                        
                except Exception as e:
                    logger.error(f"Error evaluating control for {device_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error evaluating control logic: {e}")
    
    def _check_alerts(self, sensor_data: Dict[str, float]):
        """Check alert conditions and send notifications."""
        try:
            alert_settings = db.get_alert_settings()
            
            if not alert_settings or not alert_settings.get('enabled'):
                return
            
            temp = sensor_data['temperature']
            humidity = sensor_data['humidity']
            
            temp_min = alert_settings.get('temp_min')
            temp_max = alert_settings.get('temp_max')
            humidity_min = alert_settings.get('humidity_min')
            humidity_max = alert_settings.get('humidity_max')
            notification_interval = alert_settings.get('notification_interval', 300)
            
            alerts = []
            
            if temp_min is not None and temp < temp_min:
                alerts.append(f"🌡️ Temperature too LOW: {temp:.1f}°C (min: {temp_min}°C)")
            elif temp_max is not None and temp > temp_max:
                alerts.append(f"🌡️ Temperature too HIGH: {temp:.1f}°C (max: {temp_max}°C)")
            
            if humidity_min is not None and humidity < humidity_min:
                alerts.append(f"💧 Humidity too LOW: {humidity:.1f}% (min: {humidity_min}%)")
            elif humidity_max is not None and humidity > humidity_max:
                alerts.append(f"💧 Humidity too HIGH: {humidity:.1f}% (max: {humidity_max}%)")
            
            for alert_msg in alerts:
                alert_key = alert_msg[:50]
                
                if alert_key in self.active_alerts:
                    last_sent = self.active_alerts[alert_key]
                    if (datetime.now() - last_sent).total_seconds() < notification_interval:
                        continue
                
                self._send_telegram_alert(alert_msg)
                self.active_alerts[alert_key] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _send_telegram_alert(self, message: str):
        """Send alert via Telegram (placeholder)."""
        logger.warning(f"ALERT: {message}")
    
    def _check_project_timelapse_capture(self):
        """Check if any active projects need timelapse capture."""
        if not self.camera:
            return
        
        try:
            # Get all active projects with timelapse enabled
            projects = db.get_projects_needing_timelapse()
            
            for project in projects:
                project_id = project['id']
                interval = project.get('timelapse_interval', 300)
                
                # Get last capture time from our tracker or database
                last_capture = self.project_timelapse_timers.get(project_id)
                
                if last_capture is None:
                    # First capture for this project in this session
                    last_capture_db = project.get('timelapse_last_capture')
                    if last_capture_db:
                        if isinstance(last_capture_db, str):
                            try:
                                last_capture = datetime.fromisoformat(
                                    last_capture_db.replace('Z', '+00:00')
                                )
                            except:
                                last_capture = datetime.now() - timedelta(seconds=interval)
                        else:
                            last_capture = last_capture_db
                    else:
                        # Capture immediately for new projects
                        last_capture = datetime.now() - timedelta(seconds=interval)
                    
                    self.project_timelapse_timers[project_id] = last_capture
                
                # Check if enough time has passed
                elapsed = (datetime.now() - last_capture).total_seconds()
                if elapsed < interval:
                    continue
                
                # Capture image for this project
                self._capture_project_timelapse(project_id, project.get('name', 'Unknown'))
                
        except Exception as e:
            logger.error(f"Error checking project timelapse capture: {e}")
    
    def _capture_project_timelapse(self, project_id: int, project_name: str):
        """Capture a timelapse image for a specific project."""
        try:
            # Get project-specific timelapse directory
            timelapse_dir = get_project_timelapse_dir(project_id)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = timelapse_dir / f"timelapse_{timestamp}.jpg"
            
            # Capture image
            captured_path = self.camera.capture_image(filepath)
            
            if captured_path:
                # Save to database
                db.save_timelapse_image(project_id, str(captured_path))
                
                # Update project's last capture time
                db.update_timelapse_capture(project_id)
                
                # Update our tracker
                self.project_timelapse_timers[project_id] = datetime.now()
                
                logger.info(f"Captured timelapse for project '{project_name}': {captured_path}")
            else:
                logger.warning(f"Failed to capture timelapse for project {project_id}")
                
        except Exception as e:
            logger.error(f"Error capturing timelapse for project {project_id}: {e}")
    
    def start_project_timelapse(self, project_id: int):
        """Start timelapse capture for a project."""
        self.project_timelapse_timers[project_id] = datetime.now() - timedelta(hours=1)
        logger.info(f"Started timelapse for project {project_id}")
    
    def stop_project_timelapse(self, project_id: int):
        """Stop timelapse capture for a project."""
        if project_id in self.project_timelapse_timers:
            del self.project_timelapse_timers[project_id]
        logger.info(f"Stopped timelapse for project {project_id}")
    
    # Manual control methods
    
    def turn_device_on(self, device_name: str) -> bool:
        """Manually turn a device on."""
        if not self.relay:
            logger.error("Relay controller not available")
            return False
        
        try:
            if self.relay.turn_on(device_name):
                db.update_device_state(device_name, 1)
                logger.info(f"Manually turned ON {device_name}")
                return True
        except Exception as e:
            logger.error(f"Error turning on {device_name}: {e}")
        return False
    
    def turn_device_off(self, device_name: str) -> bool:
        """Manually turn a device off."""
        if not self.relay:
            logger.error("Relay controller not available")
            return False
        
        try:
            if self.relay.turn_off(device_name):
                db.update_device_state(device_name, 0)
                logger.info(f"Manually turned OFF {device_name}")
                return True
        except Exception as e:
            logger.error(f"Error turning off {device_name}: {e}")
        return False
    
    def get_device_states(self) -> Dict[str, bool]:
        """Get current states of all devices."""
        if not self.relay:
            return {}
        return self.relay.get_all_states()
    
    def get_sensor_data(self) -> Optional[Dict[str, float]]:
        """Get current sensor readings."""
        if not self.sensor:
            return None
        try:
            return self.sensor.read()
        except Exception as e:
            logger.error(f"Error reading sensor: {e}")
            return None
    
    def capture_photo(self, filepath: Optional[str] = None) -> Optional[str]:
        """Capture a photo with the camera."""
        if not self.camera:
            logger.error("Camera not available")
            return None
        
        try:
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                photos_dir = DATA_DIR / "photos"
                photos_dir.mkdir(parents=True, exist_ok=True)
                filepath = str(photos_dir / f"photo_{timestamp}.jpg")
            
            captured_path = self.camera.capture_image(Path(filepath))
            return str(captured_path) if captured_path else None
        except Exception as e:
            logger.error(f"Error capturing photo: {e}")
            return None
    
    def get_hardware_status(self) -> Dict[str, bool]:
        """Get hardware component status."""
        return self.hardware_status.copy()
