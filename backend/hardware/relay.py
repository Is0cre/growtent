"""Relay HAT control using RPi.GPIO.

Handles 8-channel relay HAT with active LOW logic:
- GPIO.LOW = Relay energized = Device ON
- GPIO.HIGH = Relay de-energized = Device OFF
"""
import logging
from typing import Dict, Optional
import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available. Running in simulation mode.")

from backend.config import GPIO_PINS

logger = logging.getLogger(__name__)

class RelayController:
    """Control 8-channel relay HAT with active LOW logic."""
    
    def __init__(self, gpio_pins: Dict[str, int] = None):
        """Initialize relay controller.
        
        Args:
            gpio_pins: Dictionary mapping device names to GPIO pin numbers (BCM)
        """
        self.gpio_pins = gpio_pins or GPIO_PINS
        self.device_states: Dict[str, bool] = {}
        self.simulation_mode = not GPIO_AVAILABLE
        
        if not self.simulation_mode:
            self._setup_gpio()
        else:
            logger.warning("Running in SIMULATION MODE - no actual GPIO control")
            # Initialize simulated states
            for device in self.gpio_pins.keys():
                self.device_states[device] = False
    
    def _setup_gpio(self):
        """Setup GPIO pins for relay control."""
        try:
            # Use BCM numbering
            GPIO.setmode(GPIO.BCM)
            
            # Suppress warnings about pins already in use
            GPIO.setwarnings(False)
            
            # Setup all relay pins as outputs, default HIGH (OFF for active LOW)
            for device, pin in self.gpio_pins.items():
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
                self.device_states[device] = False
                logger.info(f"Initialized {device} on GPIO {pin} (default OFF)")
            
            logger.info("GPIO setup complete for all relays")
        except Exception as e:
            logger.error(f"Error setting up GPIO: {e}")
            raise
    
    def turn_on(self, device: str) -> bool:
        """Turn device ON (set GPIO LOW for active LOW relay).
        
        Args:
            device: Device name from GPIO_PINS
            
        Returns:
            True if successful, False otherwise
        """
        if device not in self.gpio_pins:
            logger.error(f"Unknown device: {device}")
            return False
        
        try:
            pin = self.gpio_pins[device]
            
            if self.simulation_mode:
                self.device_states[device] = True
                logger.info(f"[SIMULATION] Turned ON {device}")
            else:
                GPIO.output(pin, GPIO.LOW)  # LOW = ON for active LOW relay
                self.device_states[device] = True
                logger.info(f"Turned ON {device} (GPIO {pin} set LOW)")
            
            return True
        except Exception as e:
            logger.error(f"Error turning on {device}: {e}")
            return False
    
    def turn_off(self, device: str) -> bool:
        """Turn device OFF (set GPIO HIGH for active LOW relay).
        
        Args:
            device: Device name from GPIO_PINS
            
        Returns:
            True if successful, False otherwise
        """
        if device not in self.gpio_pins:
            logger.error(f"Unknown device: {device}")
            return False
        
        try:
            pin = self.gpio_pins[device]
            
            if self.simulation_mode:
                self.device_states[device] = False
                logger.info(f"[SIMULATION] Turned OFF {device}")
            else:
                GPIO.output(pin, GPIO.HIGH)  # HIGH = OFF for active LOW relay
                self.device_states[device] = False
                logger.info(f"Turned OFF {device} (GPIO {pin} set HIGH)")
            
            return True
        except Exception as e:
            logger.error(f"Error turning off {device}: {e}")
            return False
    
    def toggle(self, device: str) -> bool:
        """Toggle device state.
        
        Args:
            device: Device name from GPIO_PINS
            
        Returns:
            True if successful, False otherwise
        """
        current_state = self.get_state(device)
        if current_state:
            return self.turn_off(device)
        else:
            return self.turn_on(device)
    
    def get_state(self, device: str) -> Optional[bool]:
        """Get current device state.
        
        Args:
            device: Device name from GPIO_PINS
            
        Returns:
            True if ON, False if OFF, None if unknown device
        """
        if device not in self.gpio_pins:
            logger.error(f"Unknown device: {device}")
            return None
        
        return self.device_states.get(device, False)
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get states of all devices.
        
        Returns:
            Dictionary mapping device names to their states
        """
        return self.device_states.copy()
    
    def turn_all_off(self):
        """Turn off all devices (emergency/shutdown)."""
        logger.info("Turning off ALL devices")
        for device in self.gpio_pins.keys():
            self.turn_off(device)
    
    def cleanup(self):
        """Clean up GPIO resources."""
        logger.info("Cleaning up GPIO")
        self.turn_all_off()
        
        if not self.simulation_mode:
            try:
                GPIO.cleanup()
                logger.info("GPIO cleanup complete")
            except Exception as e:
                logger.error(f"Error during GPIO cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
