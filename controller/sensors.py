from __future__ import annotations
import board, busio
import adafruit_bme680

def read_bme680():
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        bme = adafruit_bme680.Adafruit_BME680_I2C(i2c)
        return (
            float(bme.temperature),
            float(bme.humidity),
            float(bme.pressure),
            float(getattr(bme, "gas", 0.0)),
        )
    except Exception:
        # Graceful fallback if the sensor/solder is flaky
        return (None, None, None, None)
