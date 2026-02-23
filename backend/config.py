"""Configuration management for grow tent automation system."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [CONFIG_DIR, DATA_DIR, LOGS_DIR, DATA_DIR / "photos", DATA_DIR / "timelapse", DATA_DIR / "videos"]:
    directory.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_PATH = DATA_DIR / "database.db"

# GPIO Pin assignments (BCM numbering) - 9 relays
# Active LOW logic: GPIO LOW = device ON, GPIO HIGH = device OFF
GPIO_PINS = {
    "lights":            5,   # Relay 1  - GPIO 5   (physical pin 29)
    "air_pump":          6,   # Relay 2  - GPIO 6   (physical pin 31) - Air Pump for oxygenation
    "nutrient_pump":     13,  # Relay 3  - GPIO 13  (physical pin 33) - Nutrient solution pump
    "circulatory_fan_1": 16,  # Relay 4  - GPIO 16  (physical pin 36)
    "circulatory_fan_2": 19,  # Relay 5  - GPIO 19  (physical pin 35)
    "exhaust_fan":       20,  # Relay 6  - GPIO 20  (physical pin 38)
    "humidifier":        21,  # Relay 7  - GPIO 21  (physical pin 40)
    "heater":            23,  # Relay 8  - GPIO 23  (physical pin 16)
    "dehumidifier":      24,  # Relay 9  - GPIO 24  (physical pin 18)
}

# Human-readable display names for devices
DEVICE_DISPLAY_NAMES = {
    "lights": "Lights",
    "air_pump": "Air Pump",
    "nutrient_pump": "Nutrient Pump",
    "circulatory_fan_1": "Circulatory Fan 1",
    "circulatory_fan_2": "Circulatory Fan 2",
    "exhaust_fan": "Exhaust Fan",
    "humidifier": "Humidifier",
    "heater": "Heater",
    "dehumidifier": "Dehumidifier",
}

# BME680 Sensor (I²C)
BME680_I2C_ADDRESS = 0x76  # Try 0x77 if this doesn't work

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8436198773:AAGn7MukZYgb2Fz4VhLq3G6dnpWeem_qn6o")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "632820309")

# Sensor reading intervals
SENSOR_READ_INTERVAL = 30  # seconds
DATA_LOG_INTERVAL = 60     # seconds

# Default device settings
DEFAULT_DEVICE_SETTINGS = {
    "lights": {
        "enabled": True,
        "schedule": [
            {"on": "06:00", "off": "22:00"}  # 16 hours on
        ],
        "mode": "schedule"
    },
    "exhaust_fan": {
        "enabled": True,
        "schedule": [
            {"duration": 15, "interval": 60}  # 15 min every hour
        ],
        "temp_threshold": 28.0,  # Turn on above 28°C
        "humidity_threshold": 75.0,  # Turn on above 75%
        "mode": "auto"  # schedule + thresholds
    },
    "circulatory_fan_1": {
        "enabled": True,
        "schedule": [
            {"on": "00:00", "off": "23:59"}  # Always on
        ],
        "mode": "schedule"
    },
    "circulatory_fan_2": {
        "enabled": True,
        "schedule": [
            {"on": "00:00", "off": "23:59"}  # Always on
        ],
        "mode": "schedule"
    },
    "humidifier": {
        "enabled": True,
        "humidity_threshold": 50.0,  # Turn on below 50%
        "mode": "threshold"
    },
    "dehumidifier": {
        "enabled": True,
        "humidity_threshold": 70.0,  # Turn on above 70%
        "mode": "threshold"
    },
    "heater": {
        "enabled": True,
        "temp_threshold": 18.0,  # Turn on below 18°C
        "mode": "threshold"
    },
    "nutrient_pump": {
        "enabled": True,
        "schedule": [
            {"time": "08:00", "duration": 5},  # 5 minutes at 8 AM
            {"time": "20:00", "duration": 5}   # 5 minutes at 8 PM
        ],
        "mode": "schedule"
    },
    "air_pump": {
        "enabled": True,
        "schedule": [
            {"on": "00:00", "off": "23:59"}  # Always on for oxygenation
        ],
        "mode": "schedule"
    }
}

# Default alert settings
DEFAULT_ALERT_SETTINGS = {
    "enabled": True,
    "temp_min": 15.0,
    "temp_max": 32.0,
    "humidity_min": 40.0,
    "humidity_max": 80.0,
    "notification_interval": 300  # seconds between repeated alerts
}

# Time-lapse settings
TIMELAPSE_INTERVAL = 300  # seconds (5 minutes)
TIMELAPSE_FPS = 30  # frames per second in final video

# Camera settings
CAMERA_RESOLUTION = (1920, 1080)
CAMERA_ROTATION = 0

# Web server settings
HOST = "0.0.0.0"
PORT = 8000

# Load custom configuration if exists
CONFIG_FILE = CONFIG_DIR / "config.yaml"

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to YAML file."""
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def get_device_display_name(device_name: str) -> str:
    """Get the human-readable display name for a device.
    
    Args:
        device_name: Internal device name
        
    Returns:
        Human-readable display name
    """
    return DEVICE_DISPLAY_NAMES.get(device_name, device_name.replace('_', ' ').title())
