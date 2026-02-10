"""BME680 environmental sensor control.

Reads temperature, humidity, pressure, and gas resistance from BME680 sensor via I²C.
"""
import logging
import time
from typing import Dict, Optional, Tuple
import random

try:
    import bme680
    BME680_AVAILABLE = True
except ImportError:
    BME680_AVAILABLE = False
    logging.warning("bme680 library not available. Running in simulation mode.")

from backend.config import BME680_I2C_ADDRESS

logger = logging.getLogger(__name__)

class BME680Sensor:
    """BME680 environmental sensor interface."""
    
    def __init__(self, i2c_address: int = BME680_I2C_ADDRESS):
        """Initialize BME680 sensor.
        
        Args:
            i2c_address: I²C address of the sensor (0x76 or 0x77)
        """
        self.i2c_address = i2c_address
        self.sensor = None
        self.simulation_mode = not BME680_AVAILABLE
        self.last_reading: Optional[Dict[str, float]] = None
        
        if not self.simulation_mode:
            self._init_sensor()
        else:
            logger.warning("Running in SIMULATION MODE - generating random sensor data")
    
    def _init_sensor(self):
        """Initialize the BME680 sensor."""
        try:
            # Try primary address first
            self.sensor = bme680.BME680(self.i2c_address)
            
            # Configure sensor settings
            self.sensor.set_humidity_oversample(bme680.OS_2X)
            self.sensor.set_pressure_oversample(bme680.OS_4X)
            self.sensor.set_temperature_oversample(bme680.OS_8X)
            self.sensor.set_filter(bme680.FILTER_SIZE_3)
            
            # Configure gas sensor
            self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
            self.sensor.set_gas_heater_temperature(320)
            self.sensor.set_gas_heater_duration(150)
            self.sensor.select_gas_heater_profile(0)
            
            logger.info(f"BME680 sensor initialized at I²C address 0x{self.i2c_address:02x}")
            
            # Perform initial reading to verify sensor
            if self.sensor.get_sensor_data():
                logger.info("BME680 sensor verified with test reading")
            else:
                logger.warning("BME680 sensor initialization: first reading failed")
                
        except Exception as e:
            logger.error(f"Error initializing BME680 sensor: {e}")
            # Try alternate address
            alternate_address = 0x77 if self.i2c_address == 0x76 else 0x76
            try:
                logger.info(f"Trying alternate I²C address 0x{alternate_address:02x}")
                self.sensor = bme680.BME680(alternate_address)
                self.i2c_address = alternate_address
                logger.info(f"BME680 sensor initialized at alternate address 0x{alternate_address:02x}")
            except Exception as e2:
                logger.error(f"Failed to initialize BME680 at both addresses: {e2}")
                self.simulation_mode = True
                logger.warning("Falling back to SIMULATION MODE")
    
    def read(self) -> Optional[Dict[str, float]]:
        """Read sensor data.
        
        Returns:
            Dictionary with keys: temperature, humidity, pressure, gas_resistance
            or None if reading failed
        """
        if self.simulation_mode:
            return self._simulate_reading()
        
        try:
            if self.sensor.get_sensor_data():
                data = {
                    'temperature': round(self.sensor.data.temperature, 2),
                    'humidity': round(self.sensor.data.humidity, 2),
                    'pressure': round(self.sensor.data.pressure, 2),
                    'gas_resistance': round(self.sensor.data.gas_resistance, 2)
                }
                self.last_reading = data
                logger.debug(f"Sensor reading: Temp={data['temperature']}°C, "
                           f"Humidity={data['humidity']}%, "
                           f"Pressure={data['pressure']}hPa, "
                           f"Gas={data['gas_resistance']}Ω")
                return data
            else:
                logger.warning("Failed to get sensor data")
                return self.last_reading  # Return last known good reading
        except Exception as e:
            logger.error(f"Error reading sensor: {e}")
            return self.last_reading
    
    def _simulate_reading(self) -> Dict[str, float]:
        """Generate simulated sensor readings for testing.
        
        Returns:
            Simulated sensor data
        """
        # Generate realistic values with some variation
        if self.last_reading:
            # Add small random variation to last reading
            temp = self.last_reading['temperature'] + random.uniform(-0.5, 0.5)
            humidity = self.last_reading['humidity'] + random.uniform(-2, 2)
            pressure = self.last_reading['pressure'] + random.uniform(-0.5, 0.5)
            gas = self.last_reading['gas_resistance'] + random.uniform(-1000, 1000)
        else:
            # Initial values
            temp = random.uniform(20, 26)
            humidity = random.uniform(50, 70)
            pressure = random.uniform(1000, 1020)
            gas = random.uniform(50000, 100000)
        
        # Keep values in realistic ranges
        temp = max(15, min(35, temp))
        humidity = max(30, min(90, humidity))
        pressure = max(990, min(1030, pressure))
        gas = max(10000, min(200000, gas))
        
        data = {
            'temperature': round(temp, 2),
            'humidity': round(humidity, 2),
            'pressure': round(pressure, 2),
            'gas_resistance': round(gas, 2)
        }
        
        self.last_reading = data
        return data
    
    def get_temperature(self) -> Optional[float]:
        """Get current temperature in Celsius."""
        data = self.read()
        return data['temperature'] if data else None
    
    def get_humidity(self) -> Optional[float]:
        """Get current relative humidity in percent."""
        data = self.read()
        return data['humidity'] if data else None
    
    def get_pressure(self) -> Optional[float]:
        """Get current pressure in hPa."""
        data = self.read()
        return data['pressure'] if data else None
    
    def get_gas_resistance(self) -> Optional[float]:
        """Get current gas resistance in Ohms."""
        data = self.read()
        return data['gas_resistance'] if data else None
    
    def is_available(self) -> bool:
        """Check if sensor is available and working.
        
        Returns:
            True if sensor is responding, False otherwise
        """
        if self.simulation_mode:
            return True
        
        try:
            return self.sensor.get_sensor_data()
        except Exception:
            return False
