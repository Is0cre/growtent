"""Grow diary API endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import shutil
from datetime import datetime

from backend.database import db
from backend.config import DATA_DIR

router = APIRouter(prefix="/api/diary", tags=["diary"])

class DiaryEntryCreate(BaseModel):
    project_id: int
    title: str
    text: str

class DiaryEntryUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None

@router.get("/")
async def get_diary_entries(project_id: Optional[int] = None):
    """Get all diary entries for a project."""
    try:
        if project_id is None:
            # Get active project
            active_project = db.get_active_project()
            if not active_project:
                return {"success": True, "data": [], "message": "No active project"}
            project_id = active_project['id']
        
        entries = db.get_diary_entries(project_id)
        return {"success": True, "data": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_diary_entry(
    project_id: int = Form(...),
    title: str = Form(...),
    text: str = Form(...),
    photos: List[UploadFile] = File(None)
):
    """Create a new diary entry with optional photos."""
    try:
        # Verify project exists
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Handle photo uploads
        photo_paths = []
        if photos:
            photos_dir = DATA_DIR / "photos" / f"project_{project_id}"
            photos_dir.mkdir(parents=True, exist_ok=True)
            
            for photo in photos:
                if photo.filename:
                    # Generate unique filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ext = Path(photo.filename).suffix
                    filename = f"diary_{timestamp}_{photo.filename}"
                    filepath = photos_dir / filename
                    
                    # Save file
                    with open(filepath, "wb") as buffer:
                        shutil.copyfileobj(photo.file, buffer)
                    
                    # Store relative path
                    photo_paths.append(str(filepath.relative_to(DATA_DIR.parent)))
        
        # Create diary entry
        entry_id = db.create_diary_entry(project_id, title, text, photo_paths)
        
        return {
            "success": True,
            "message": "Diary entry created",
            "data": {"id": entry_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{entry_id}")
async def update_diary_entry(entry_id: int, entry: DiaryEntryUpdate):
    """Update a diary entry."""
    try:
        success = db.update_diary_entry(
            entry_id,
            title=entry.title,
            text=entry.text
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Diary entry not found")
        
        return {"success": True, "message": "Diary entry updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{entry_id}")
async def delete_diary_entry(entry_id: int):
    """Delete a diary entry."""
    try:
        success = db.delete_diary_entry(entry_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Diary entry not found")
        
        return {"success": True, "message": "Diary entry deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
