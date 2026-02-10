"""Device control API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from backend.database import db
from backend.config import GPIO_PINS

router = APIRouter(prefix="/api/devices", tags=["devices"])

# Global reference to automation engine (set in main.py)
automation_engine = None

def set_automation_engine(engine):
    """Set the automation engine reference."""
    global automation_engine
    automation_engine = engine

class DeviceControl(BaseModel):
    action: str  # "on" or "off"

@router.get("/")
async def get_all_devices():
    """Get all devices and their current states."""
    try:
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        states = automation_engine.get_device_states()
        
        devices = []
        for device_name, state in states.items():
            if device_name != 'unused':
                devices.append({
                    "name": device_name,
                    "display_name": device_name.replace('_', ' ').title(),
                    "state": state,
                    "gpio_pin": GPIO_PINS.get(device_name)
                })
        
        return {"success": True, "data": devices}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_name}")
async def get_device_state(device_name: str):
    """Get state of a specific device."""
    try:
        if device_name not in GPIO_PINS or device_name == 'unused':
            raise HTTPException(status_code=404, detail="Device not found")
        
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        state = automation_engine.relay.get_state(device_name)
        
        return {
            "success": True,
            "data": {
                "name": device_name,
                "display_name": device_name.replace('_', ' ').title(),
                "state": state,
                "gpio_pin": GPIO_PINS.get(device_name)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{device_name}/control")
async def control_device(device_name: str, control: DeviceControl):
    """Turn device on or off."""
    try:
        if device_name not in GPIO_PINS or device_name == 'unused':
            raise HTTPException(status_code=404, detail="Device not found")
        
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        if control.action == "on":
            success = automation_engine.turn_device_on(device_name)
            message = f"Turned {device_name} ON"
        elif control.action == "off":
            success = automation_engine.turn_device_off(device_name)
            message = f"Turned {device_name} OFF"
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'on' or 'off'")
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to control device")
        
        return {
            "success": True,
            "message": message,
            "data": {
                "name": device_name,
                "state": control.action == "on"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{device_name}/toggle")
async def toggle_device(device_name: str):
    """Toggle device state."""
    try:
        if device_name not in GPIO_PINS or device_name == 'unused':
            raise HTTPException(status_code=404, detail="Device not found")
        
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        current_state = automation_engine.relay.get_state(device_name)
        
        if current_state:
            success = automation_engine.turn_device_off(device_name)
            new_state = False
            message = f"Turned {device_name} OFF"
        else:
            success = automation_engine.turn_device_on(device_name)
            new_state = True
            message = f"Turned {device_name} ON"
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to toggle device")
        
        return {
            "success": True,
            "message": message,
            "data": {
                "name": device_name,
                "state": new_state
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
