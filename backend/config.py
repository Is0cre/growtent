"""Configuration management for grow tent automation system.

Loads configuration from:
- config/settings.yaml - Non-sensitive settings (can be committed to git)
- config/secrets.yaml - Sensitive data (API keys, tokens - NOT in git)
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Base paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [CONFIG_DIR, DATA_DIR, LOGS_DIR, 
                  DATA_DIR / "photos", DATA_DIR / "timelapse", 
                  DATA_DIR / "videos", DATA_DIR / "projects"]:
    directory.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_PATH = DATA_DIR / "database.db"

# Config file paths
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
SECRETS_FILE = CONFIG_DIR / "secrets.yaml"

logger = logging.getLogger(__name__)


def load_yaml_file(filepath: Path) -> Dict[str, Any]:
    """Load a YAML configuration file.
    
    Args:
        filepath: Path to the YAML file
        
    Returns:
        Dictionary containing the configuration
    """
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return {}
    return {}


def save_yaml_file(filepath: Path, data: Dict[str, Any]) -> bool:
    """Save configuration to a YAML file.
    
    Args:
        filepath: Path to the YAML file
        data: Configuration dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False


# Load configuration files
_settings: Dict[str, Any] = {}
_secrets: Dict[str, Any] = {}


def load_config() -> None:
    """Load all configuration from YAML files."""
    global _settings, _secrets
    _settings = load_yaml_file(SETTINGS_FILE)
    _secrets = load_yaml_file(SECRETS_FILE)
    logger.info("Configuration loaded from YAML files")


def get_settings() -> Dict[str, Any]:
    """Get all settings (non-sensitive config)."""
    if not _settings:
        load_config()
    return _settings


def get_secrets() -> Dict[str, Any]:
    """Get all secrets (sensitive config)."""
    if not _secrets:
        load_config()
    return _secrets


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save settings to the settings.yaml file."""
    global _settings
    _settings = settings
    return save_yaml_file(SETTINGS_FILE, settings)


def save_secrets(secrets: Dict[str, Any]) -> bool:
    """Save secrets to the secrets.yaml file."""
    global _secrets
    _secrets = secrets
    return save_yaml_file(SECRETS_FILE, secrets)


def get_setting(key: str, default: Any = None) -> Any:
    """Get a specific setting value using dot notation.
    
    Args:
        key: Setting key (supports dot notation e.g., 'timelapse.default_interval')
        default: Default value if key not found
        
    Returns:
        Setting value or default
    """
    settings = get_settings()
    keys = key.split('.')
    value = settings
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value


def get_secret(key: str, default: Any = None) -> Any:
    """Get a specific secret value using dot notation.
    
    Args:
        key: Secret key (supports dot notation e.g., 'telegram.bot_token')
        default: Default value if key not found
        
    Returns:
        Secret value or default
    """
    secrets = get_secrets()
    keys = key.split('.')
    value = secrets
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value


def reload_config() -> None:
    """Reload configuration from files."""
    global _settings, _secrets
    _settings = {}
    _secrets = {}
    load_config()


# Initialize configuration on import
load_config()


# ============================================================================
# BACKWARD COMPATIBLE CONSTANTS (derived from YAML config)
# ============================================================================

# GPIO Pin assignments (BCM numbering) - 9 relays
# Active LOW logic: GPIO LOW = device ON, GPIO HIGH = device OFF
GPIO_PINS = get_setting('gpio_pins', {
    "lights":            5,
    "air_pump":          6,
    "nutrient_pump":     13,
    "circulatory_fan_1": 16,
    "circulatory_fan_2": 19,
    "exhaust_fan":       20,
    "humidifier":        21,
    "heater":            23,
    "dehumidifier":      24,
})

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
BME680_I2C_ADDRESS = get_setting('sensor.i2c_address', 0x76)

# Telegram Bot Configuration (from secrets)
TELEGRAM_BOT_TOKEN = get_secret('telegram.bot_token', 
                                os.getenv("TELEGRAM_BOT_TOKEN", ""))
TELEGRAM_CHAT_ID = get_secret('telegram.chat_id', 
                              os.getenv("TELEGRAM_CHAT_ID", ""))

# Sensor reading intervals
SENSOR_READ_INTERVAL = get_setting('sensor.read_interval', 30)
DATA_LOG_INTERVAL = get_setting('sensor.log_interval', 60)

# Time-lapse settings
TIMELAPSE_INTERVAL = get_setting('timelapse.default_interval', 300)
TIMELAPSE_FPS = get_setting('timelapse.default_fps', 30)
TIMELAPSE_AUTO_START = get_setting('timelapse.auto_start_on_project', True)

# Camera settings
_camera_config = get_setting('camera', {})
CAMERA_RESOLUTION = (
    _camera_config.get('resolution', {}).get('width', 1920),
    _camera_config.get('resolution', {}).get('height', 1080)
)
CAMERA_ROTATION = _camera_config.get('rotation', 0)

# Web server settings
HOST = get_setting('server.host', "0.0.0.0")
PORT = get_setting('server.port', 8000)

# Alert settings
_alert_config = get_setting('alerts', {})
DEFAULT_ALERT_SETTINGS = {
    "enabled": _alert_config.get('enabled', True),
    "temp_min": _alert_config.get('temperature', {}).get('min', 15.0),
    "temp_max": _alert_config.get('temperature', {}).get('max', 32.0),
    "humidity_min": _alert_config.get('humidity', {}).get('min', 40.0),
    "humidity_max": _alert_config.get('humidity', {}).get('max', 80.0),
    "notification_interval": _alert_config.get('notification_interval', 300)
}

# Default device settings
DEFAULT_DEVICE_SETTINGS = {
    "lights": {
        "enabled": True,
        "schedule": [
            {"on": "06:00", "off": "22:00"}
        ],
        "mode": "schedule"
    },
    "exhaust_fan": {
        "enabled": True,
        "schedule": [
            {"duration": 15, "interval": 60}
        ],
        "temp_threshold": 28.0,
        "humidity_threshold": 75.0,
        "mode": "auto"
    },
    "circulatory_fan_1": {
        "enabled": True,
        "schedule": [
            {"on": "00:00", "off": "23:59"}
        ],
        "mode": "schedule"
    },
    "circulatory_fan_2": {
        "enabled": True,
        "schedule": [
            {"on": "00:00", "off": "23:59"}
        ],
        "mode": "schedule"
    },
    "humidifier": {
        "enabled": True,
        "humidity_threshold": 50.0,
        "mode": "threshold"
    },
    "dehumidifier": {
        "enabled": True,
        "humidity_threshold": 70.0,
        "mode": "threshold"
    },
    "heater": {
        "enabled": True,
        "temp_threshold": 18.0,
        "mode": "threshold"
    },
    "nutrient_pump": {
        "enabled": True,
        "schedule": [
            {"time": "08:00", "duration": 5},
            {"time": "20:00", "duration": 5}
        ],
        "mode": "schedule"
    },
    "air_pump": {
        "enabled": True,
        "schedule": [
            {"on": "00:00", "off": "23:59"}
        ],
        "mode": "schedule"
    }
}

# External sync settings
EXTERNAL_SYNC_ENABLED = get_setting('external_sync.enabled', False)
EXTERNAL_SYNC_INTERVAL = get_setting('external_sync.sync_interval', 300)

# AI Analysis settings
AI_ANALYSIS_ENABLED = get_setting('ai_analysis.enabled', False)
AI_ANALYSIS_SCHEDULE_TIME = get_setting('ai_analysis.daily_schedule_time', "12:00")

# Scheduler settings
SCHEDULER_ENABLED = get_setting('scheduler.enabled', True)
DAILY_REPORT_TIME = get_setting('scheduler.daily_report_time', "08:00")

# Logging settings
LOG_LEVEL = get_setting('logging.level', "INFO")
LOG_MAX_SIZE = get_setting('logging.max_file_size', 10485760)
LOG_BACKUP_COUNT = get_setting('logging.backup_count', 5)


def get_device_display_name(device_name: str) -> str:
    """Get the human-readable display name for a device.
    
    Args:
        device_name: Internal device name
        
    Returns:
        Human-readable display name
    """
    return DEVICE_DISPLAY_NAMES.get(device_name, device_name.replace('_', ' ').title())


def get_project_timelapse_dir(project_id: int) -> Path:
    """Get the timelapse directory for a specific project.
    
    Args:
        project_id: Project ID
        
    Returns:
        Path to project's timelapse directory
    """
    project_dir = DATA_DIR / "projects" / str(project_id) / "timelapse"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def get_project_data_dir(project_id: int) -> Path:
    """Get the data directory for a specific project.
    
    Args:
        project_id: Project ID
        
    Returns:
        Path to project's data directory
    """
    project_dir = DATA_DIR / "projects" / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir
