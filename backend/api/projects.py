"""Project management API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from backend.database import db

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    notes: Optional[str] = ""

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

@router.get("/")
async def get_all_projects():
    """Get all projects."""
    try:
        projects = db.get_all_projects()
        return {"success": True, "data": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_project():
    """Get currently active project."""
    try:
        project = db.get_active_project()
        if not project:
            return {"success": True, "data": None}
        return {"success": True, "data": project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}")
async def get_project(project_id: int):
    """Get project by ID."""
    try:
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "data": project}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_project(project: ProjectCreate):
    """Create a new project."""
    try:
        # End any existing active projects first
        active_project = db.get_active_project()
        if active_project:
            db.end_project(active_project['id'])
        
        project_id = db.create_project(project.name, project.notes)
        new_project = db.get_project(project_id)
        return {"success": True, "data": new_project, "message": "Project created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{project_id}")
async def update_project(project_id: int, project: ProjectUpdate):
    """Update project details."""
    try:
        updates = {k: v for k, v in project.dict().items() if v is not None}
        success = db.update_project(project_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        updated_project = db.get_project(project_id)
        return {"success": True, "data": updated_project, "message": "Project updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{project_id}/end")
async def end_project(project_id: int):
    """End a project."""
    try:
        success = db.end_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = db.get_project(project_id)
        return {"success": True, "data": project, "message": "Project ended"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
