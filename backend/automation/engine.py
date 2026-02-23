"""Automation engine - main control loop for grow tent automation.

Runs in background thread and handles:
- Continuous sensor data reading
- Device control logic evaluation
- Data logging to database
- Alert checking and notifications
- Time-lapse image capture
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

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
    GPIO_PINS
)

logger = logging.getLogger(__name__)

class AutomationEngine:
    """Main automation engine for grow tent control."""
    
    def __init__(self):
        """Initialize automation engine."""
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Initialize hardware controllers
        logger.info("Initializing hardware controllers...")
        self.relay = RelayController()
        self.sensor = BME680Sensor()
        self.camera = CameraController()
        
        # Initialize scheduler
        self.scheduler = Scheduler()
        
        # Track last data log time
        self.last_data_log = datetime.now()
        self.last_alert_check = datetime.now()
        self.last_timelapse_capture = datetime.now()
        
        # Alert state tracking (to avoid spam)
        self.active_alerts: Dict[str, datetime] = {}
        
        # Initialize device settings if not in database
        self._init_device_settings()
        self._init_alert_settings()
        
        logger.info("Automation engine initialized")
    
    def _init_device_settings(self):
        """Initialize default device settings in database if not present."""
        existing_settings = db.get_all_device_settings()
        
        # Initialize settings for all devices in GPIO_PINS
        for device_name in GPIO_PINS.keys():
            if device_name not in existing_settings:
                default = DEFAULT_DEVICE_SETTINGS.get(device_name, {
                    "enabled": True,
                    "schedule": [],
                    "mode": "manual"
                })
                logger.info(f"Initializing default settings for {device_name}")
                db.save_device_settings(device_name, default)
    
    def _init_alert_settings(self):
        """Initialize default alert settings if not present."""
        existing_settings = db.get_alert_settings()
        if not existing_settings:
            logger.info("Initializing default alert settings")
            db.save_alert_settings(DEFAULT_ALERT_SETTINGS)
    
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
        self.relay.cleanup()
        self.camera.cleanup()
        
        logger.info("Automation engine stopped")
    
    def _run(self):
        """Main automation loop (runs in background thread)."""
        logger.info("Automation engine main loop started")
        
        while self.running:
            try:
                # Read sensor data
                sensor_data = self.sensor.read()
                
                if sensor_data:
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
                
                # Check time-lapse capture
                self._check_timelapse_capture()
                
                # Sleep before next iteration
                time.sleep(SENSOR_READ_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in automation loop: {e}", exc_info=True)
                time.sleep(SENSOR_READ_INTERVAL)
    
    def _log_sensor_data(self, sensor_data: Dict[str, float]):
        """Log sensor data to database.
        
        Args:
            sensor_data: Dictionary containing sensor readings
        """
        try:
            # Get active project
            project = db.get_active_project()
            project_id = project['id'] if project else None
            
            # Log to database
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
        """Evaluate control logic for all devices.
        
        Args:
            sensor_data: Dictionary containing sensor readings
        """
        try:
            temp = sensor_data['temperature']
            humidity = sensor_data['humidity']
            
            # Get all device settings
            all_settings = db.get_all_device_settings()
            
            # Evaluate each device
            for device_name in GPIO_PINS.keys():
                # Get settings for this device (use defaults if not found)
                settings = all_settings.get(device_name, DEFAULT_DEVICE_SETTINGS.get(device_name, {}))
                
                # Evaluate if device should be on
                should_be_on = self.scheduler.evaluate_device(
                    device_name, settings, temp, humidity
                )
                
                # Skip if in manual mode (None return value)
                if should_be_on is None:
                    continue
                
                # Get current state
                current_state = self.relay.get_state(device_name)
                
                # Update device state if needed
                if should_be_on and not current_state:
                    logger.info(f"Turning ON {device_name} (auto control)")
                    self.relay.turn_on(device_name)
                    db.update_device_state(device_name, 1)
                    
                elif not should_be_on and current_state:
                    logger.info(f"Turning OFF {device_name} (auto control)")
                    self.relay.turn_off(device_name)
                    db.update_device_state(device_name, 0)
            
        except Exception as e:
            logger.error(f"Error evaluating control logic: {e}")
    
    def _check_alerts(self, sensor_data: Dict[str, float]):
        """Check alert conditions and send notifications.
        
        Args:
            sensor_data: Dictionary containing sensor readings
        """
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
            
            # Check temperature
            if temp_min is not None and temp < temp_min:
                alerts.append(f"🌡️ Temperature too LOW: {temp}°C (min: {temp_min}°C)")
            elif temp_max is not None and temp > temp_max:
                alerts.append(f"🌡️ Temperature too HIGH: {temp}°C (max: {temp_max}°C)")
            
            # Check humidity
            if humidity_min is not None and humidity < humidity_min:
                alerts.append(f"💧 Humidity too LOW: {humidity}% (min: {humidity_min}%)")
            elif humidity_max is not None and humidity > humidity_max:
                alerts.append(f"💧 Humidity too HIGH: {humidity}% (max: {humidity_max}%)")
            
            # Send alerts (with rate limiting)
            for alert_msg in alerts:
                alert_key = alert_msg[:50]  # Use first 50 chars as key
                
                # Check if we've recently sent this alert
                if alert_key in self.active_alerts:
                    last_sent = self.active_alerts[alert_key]
                    if (datetime.now() - last_sent).total_seconds() < notification_interval:
                        continue  # Skip, too soon
                
                # Send alert via Telegram
                self._send_telegram_alert(alert_msg)
                self.active_alerts[alert_key] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _send_telegram_alert(self, message: str):
        """Send alert via Telegram (placeholder - actual implementation in telegram_bot).
        
        Args:
            message: Alert message to send
        """
        # This will be implemented in the Telegram bot module
        logger.warning(f"ALERT: {message}")
        # TODO: Send via Telegram bot
    
    def _check_timelapse_capture(self):
        """Check if it's time to capture a time-lapse image."""
        try:
            # Check if time-lapse is enabled
            timelapse_enabled = db.get_system_setting('timelapse_enabled')
            if timelapse_enabled != 'true':
                return
            
            # Get time-lapse interval
            interval_str = db.get_system_setting('timelapse_interval')
            interval = int(interval_str) if interval_str else 300  # Default 5 minutes
            
            # Check if enough time has passed
            if (datetime.now() - self.last_timelapse_capture).total_seconds() < interval:
                return
            
            # Get active project
            project = db.get_active_project()
            if not project:
                return
            
            # Capture image
            from pathlib import Path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(f"data/timelapse/timelapse_{timestamp}.jpg")
            
            captured_path = self.camera.capture_image(filepath)
            if captured_path:
                # Save to database
                db.save_timelapse_image(project['id'], str(captured_path))
                logger.info(f"Captured time-lapse image: {captured_path}")
            
            self.last_timelapse_capture = datetime.now()
            
        except Exception as e:
            logger.error(f"Error capturing time-lapse image: {e}")
    
    # Manual control methods (for API/Telegram)
    
    def turn_device_on(self, device_name: str) -> bool:
        """Manually turn a device on.
        
        Args:
            device_name: Name of device to turn on
            
        Returns:
            True if successful, False otherwise
        """
        if self.relay.turn_on(device_name):
            db.update_device_state(device_name, 1)
            logger.info(f"Manually turned ON {device_name}")
            return True
        return False
    
    def turn_device_off(self, device_name: str) -> bool:
        """Manually turn a device off.
        
        Args:
            device_name: Name of device to turn off
            
        Returns:
            True if successful, False otherwise
        """
        if self.relay.turn_off(device_name):
            db.update_device_state(device_name, 0)
            logger.info(f"Manually turned OFF {device_name}")
            return True
        return False
    
    def get_device_states(self) -> Dict[str, bool]:
        """Get current states of all devices.
        
        Returns:
            Dictionary mapping device names to their states
        """
        return self.relay.get_all_states()
    
    def get_sensor_data(self) -> Optional[Dict[str, float]]:
        """Get current sensor readings.
        
        Returns:
            Dictionary containing sensor data or None
        """
        return self.sensor.read()
    
    def capture_photo(self) -> Optional[str]:
        """Capture a photo with the camera.
        
        Returns:
            Path to captured photo or None
        """
        from pathlib import Path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = Path(f"data/photos/photo_{timestamp}.jpg")
        
        captured_path = self.camera.capture_image(filepath)
        return str(captured_path) if captured_path else None
