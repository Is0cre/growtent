#!/usr/bin/env python3
"""Hardware testing script for grow tent automation."""
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.hardware.relay import RelayController
from backend.hardware.sensor import BME680Sensor
from backend.hardware.camera import CameraController
from backend.config import GPIO_PINS

def test_relay():
    """Test relay HAT."""
    print("\n🔌 Testing Relay HAT...")
    print("=" * 50)
    
    relay = RelayController()
    
    print(f"Simulation mode: {relay.simulation_mode}")
    print(f"\nConfigured devices: {list(GPIO_PINS.keys())}")
    
    for device in GPIO_PINS.keys():
        if device == 'unused':
            continue
        
        print(f"\n  Testing {device}...")
        print(f"    Turning ON...")
        relay.turn_on(device)
        time.sleep(1)
        print(f"    State: {'ON' if relay.get_state(device) else 'OFF'}")
        
        print(f"    Turning OFF...")
        relay.turn_off(device)
        time.sleep(1)
        print(f"    State: {'ON' if relay.get_state(device) else 'OFF'}")
    
    relay.cleanup()
    print("\n✅ Relay test complete")

def test_sensor():
    """Test BME680 sensor."""
    print("\n🌡️  Testing BME680 Sensor...")
    print("=" * 50)
    
    sensor = BME680Sensor()
    
    print(f"Simulation mode: {sensor.simulation_mode}")
    print(f"I2C Address: 0x{sensor.i2c_address:02x}")
    
    print("\n  Reading sensor data...")
    for i in range(3):
        data = sensor.read()
        if data:
            print(f"\n  Reading {i+1}:")
            print(f"    Temperature:  {data['temperature']:.2f} °C")
            print(f"    Humidity:     {data['humidity']:.2f} %")
            print(f"    Pressure:     {data['pressure']:.2f} hPa")
            print(f"    Gas:          {data['gas_resistance']:.0f} Ω")
        else:
            print(f"\n  Reading {i+1}: Failed")
        
        time.sleep(2)
    
    print("\n✅ Sensor test complete")

def test_camera():
    """Test camera."""
    print("\n📷 Testing Camera...")
    print("=" * 50)
    
    camera = CameraController()
    
    print(f"Simulation mode: {camera.simulation_mode}")
    print(f"Resolution: {camera.resolution}")
    print(f"Initialized: {camera.is_initialized}")
    
    print("\n  Capturing test image...")
    filepath = camera.capture_image(Path("test_image.jpg"))
    
    if filepath and filepath.exists():
        print(f"    ✓ Image saved: {filepath}")
        print(f"    Size: {filepath.stat().st_size} bytes")
    else:
        print("    ✗ Image capture failed")
    
    camera.cleanup()
    print("\n✅ Camera test complete")

def main():
    """Run all hardware tests."""
    print("\n" + "=" * 50)
    print("🧪 Grow Tent Automation - Hardware Test")
    print("=" * 50)
    
    try:
        # Test relay
        test_relay()
        
        # Test sensor
        test_sensor()
        
        # Test camera
        test_camera()
        
        print("\n" + "=" * 50)
        print("✅ All tests complete!")
        print("=" * 50)
        print("\nIf running in simulation mode, connect hardware and re-run.")
        print("If hardware is connected and tests failed, check:")
        print("  - I2C enabled: sudo raspi-config")
        print("  - Camera enabled: sudo raspi-config")
        print("  - Wiring connections")
        print("  - I2C devices: sudo i2cdetect -y 1")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
