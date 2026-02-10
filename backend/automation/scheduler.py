"""Scheduling logic for device control."""
import logging
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class Scheduler:
    """Handles scheduling logic for device control."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.device_timers: Dict[str, datetime] = {}  # Track when devices were last activated
        self.interval_trackers: Dict[str, Dict[str, Any]] = {}  # Track interval-based devices
    
    def should_turn_on_schedule(self, device_name: str, schedule: List[Dict[str, Any]], 
                                current_time: Optional[datetime] = None) -> bool:
        """Check if device should be ON based on time schedule.
        
        Args:
            device_name: Name of the device
            schedule: List of schedule entries
            current_time: Current time (defaults to now)
            
        Returns:
            True if device should be ON, False otherwise
        """
        if not schedule:
            return False
        
        if current_time is None:
            current_time = datetime.now()
        
        current_time_obj = current_time.time()
        
        for entry in schedule:
            # Handle simple on/off schedule
            if 'on' in entry and 'off' in entry:
                try:
                    on_time = datetime.strptime(entry['on'], "%H:%M").time()
                    off_time = datetime.strptime(entry['off'], "%H:%M").time()
                    
                    if on_time <= off_time:
                        # Same day range (e.g., 06:00 to 22:00)
                        if on_time <= current_time_obj < off_time:
                            return True
                    else:
                        # Crosses midnight (e.g., 22:00 to 06:00)
                        if current_time_obj >= on_time or current_time_obj < off_time:
                            return True
                except ValueError as e:
                    logger.error(f"Invalid time format in schedule for {device_name}: {e}")
            
            # Handle interval-based schedule (e.g., 15 min every hour)
            elif 'duration' in entry and 'interval' in entry:
                duration_min = entry['duration']
                interval_min = entry['interval']
                
                # Get or create interval tracker
                if device_name not in self.interval_trackers:
                    self.interval_trackers[device_name] = {
                        'last_start': None,
                        'running': False
                    }
                
                tracker = self.interval_trackers[device_name]
                
                # Check if we need to start a new cycle
                if tracker['last_start'] is None or \
                   (current_time - tracker['last_start']).total_seconds() >= interval_min * 60:
                    tracker['last_start'] = current_time
                    tracker['running'] = True
                
                # Check if still within duration
                if tracker['running']:
                    elapsed = (current_time - tracker['last_start']).total_seconds()
                    if elapsed < duration_min * 60:
                        return True
                    else:
                        tracker['running'] = False
            
            # Handle specific time with duration (e.g., pump at 08:00 for 5 min)
            elif 'time' in entry and 'duration' in entry:
                try:
                    trigger_time = datetime.strptime(entry['time'], "%H:%M").time()
                    duration_min = entry['duration']
                    
                    # Create datetime object for comparison
                    trigger_datetime = datetime.combine(current_time.date(), trigger_time)
                    
                    # Check if we're within the duration window
                    end_datetime = trigger_datetime + timedelta(minutes=duration_min)
                    
                    if trigger_datetime <= current_time < end_datetime:
                        return True
                    
                    # Also check if the trigger time was yesterday and we're still in the window
                    yesterday_trigger = trigger_datetime - timedelta(days=1)
                    yesterday_end = yesterday_trigger + timedelta(minutes=duration_min)
                    
                    if yesterday_trigger <= current_time < yesterday_end:
                        return True
                        
                except ValueError as e:
                    logger.error(f"Invalid time format in schedule for {device_name}: {e}")
        
        return False
    
    def should_turn_on_threshold(self, device_name: str, thresholds: Dict[str, float], 
                                 current_temp: Optional[float], 
                                 current_humidity: Optional[float]) -> bool:
        """Check if device should be ON based on environmental thresholds.
        
        Args:
            device_name: Name of the device
            thresholds: Dictionary of threshold values
            current_temp: Current temperature
            current_humidity: Current humidity
            
        Returns:
            True if device should be ON, False otherwise
        """
        if not thresholds:
            return False
        
        # Temperature-based threshold
        if 'temp_threshold' in thresholds and current_temp is not None:
            threshold = thresholds['temp_threshold']
            
            # Devices that turn on when temp is too high (exhaust fan, dehumidifier)
            if device_name in ['exhaust_fan', 'dehumidifier']:
                if current_temp >= threshold:
                    return True
            
            # Devices that turn on when temp is too low (heater)
            elif device_name == 'heater':
                if current_temp <= threshold:
                    return True
        
        # Humidity-based threshold
        if 'humidity_threshold' in thresholds and current_humidity is not None:
            threshold = thresholds['humidity_threshold']
            
            # Devices that turn on when humidity is too high (exhaust fan, dehumidifier)
            if device_name in ['exhaust_fan', 'dehumidifier']:
                if current_humidity >= threshold:
                    return True
            
            # Devices that turn on when humidity is too low (humidifier)
            elif device_name == 'humidifier':
                if current_humidity <= threshold:
                    return True
        
        return False
    
    def evaluate_device(self, device_name: str, settings: Dict[str, Any], 
                       current_temp: Optional[float], 
                       current_humidity: Optional[float]) -> bool:
        """Evaluate if device should be ON based on all criteria.
        
        Args:
            device_name: Name of the device
            settings: Device settings (schedule, thresholds, mode, enabled)
            current_temp: Current temperature
            current_humidity: Current humidity
            
        Returns:
            True if device should be ON, False otherwise
        """
        if not settings or not settings.get('enabled', True):
            return False
        
        mode = settings.get('mode', 'schedule')
        schedule = settings.get('schedule', [])
        thresholds = settings.get('thresholds', {})
        
        # Handle different modes
        if mode == 'schedule':
            return self.should_turn_on_schedule(device_name, schedule)
        
        elif mode == 'threshold':
            return self.should_turn_on_threshold(device_name, thresholds, 
                                                current_temp, current_humidity)
        
        elif mode == 'auto':
            # Auto mode: turn on if EITHER schedule OR threshold conditions are met
            schedule_on = self.should_turn_on_schedule(device_name, schedule)
            threshold_on = self.should_turn_on_threshold(device_name, thresholds, 
                                                         current_temp, current_humidity)
            return schedule_on or threshold_on
        
        elif mode == 'manual':
            # Manual mode: don't change state automatically
            return None  # Return None to indicate no automatic change
        
        return False
