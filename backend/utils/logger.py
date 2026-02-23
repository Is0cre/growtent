"""Logging configuration for grow tent automation system."""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

from backend.config import (
    LOGS_DIR, LOG_LEVEL, LOG_MAX_SIZE, LOG_BACKUP_COUNT,
    get_setting
)


def setup_logging():
    """Configure logging for the application with rotation."""
    # Get logging settings
    level_str = get_setting('logging.level', LOG_LEVEL)
    max_size = get_setting('logging.max_file_size', LOG_MAX_SIZE)
    backup_count = get_setting('logging.backup_count', LOG_BACKUP_COUNT)
    log_to_console = get_setting('logging.log_to_console', True)
    log_to_file = get_setting('logging.log_to_file', True)
    
    # Map level string to logging level
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    level = level_map.get(level_str.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / f"grow_tent_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Also create an error-only log file
        error_log_file = LOGS_DIR / "errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    
    # Set levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized at {level_str} level")
    if log_to_file:
        logging.info(f"Log files in: {LOGS_DIR}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
