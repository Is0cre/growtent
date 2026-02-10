"""Sensor data API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from backend.database import db

router = APIRouter(prefix="/api/sensors", tags=["sensors"])

@router.get("/current")
async def get_current_sensor_data():
    """Get current/latest sensor readings."""
    try:
        data = db.get_latest_sensor_data()
        if not data:
            return {"success": True, "data": None, "message": "No sensor data available"}
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_sensor_history(
    project_id: Optional[int] = None,
    hours: Optional[int] = Query(24, description="Number of hours of history"),
    limit: int = Query(1000, le=10000)
):
    """Get historical sensor data."""
    try:
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours) if hours else None
        
        # Get active project if not specified
        if project_id is None:
            active_project = db.get_active_project()
            if active_project:
                project_id = active_project['id']
        
        data = db.get_sensor_data(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_sensor_stats(
    project_id: Optional[int] = None,
    hours: int = Query(24, description="Number of hours for statistics")
):
    """Get sensor statistics (min, max, avg)."""
    try:
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        if project_id is None:
            active_project = db.get_active_project()
            if active_project:
                project_id = active_project['id']
        
        data = db.get_sensor_data(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        if not data:
            return {"success": True, "data": None, "message": "No data available"}
        
        # Calculate statistics
        temps = [d['temperature'] for d in data if d['temperature'] is not None]
        humidities = [d['humidity'] for d in data if d['humidity'] is not None]
        pressures = [d['pressure'] for d in data if d['pressure'] is not None]
        
        stats = {
            "temperature": {
                "min": min(temps) if temps else None,
                "max": max(temps) if temps else None,
                "avg": sum(temps) / len(temps) if temps else None
            },
            "humidity": {
                "min": min(humidities) if humidities else None,
                "max": max(humidities) if humidities else None,
                "avg": sum(humidities) / len(humidities) if humidities else None
            },
            "pressure": {
                "min": min(pressures) if pressures else None,
                "max": max(pressures) if pressures else None,
                "avg": sum(pressures) / len(pressures) if pressures else None
            },
            "period_hours": hours,
            "data_points": len(data)
        }
        
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
