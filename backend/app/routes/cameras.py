from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from app.database import get_db, Camera
from app.schemas import CameraCreate, CameraResponse

router = APIRouter()

@router.get("/", response_model=List[CameraResponse])
async def list_cameras(db: Session = Depends(get_db)):
    """Get all cameras"""
    cameras = db.query(Camera).filter(Camera.is_active == True).all()
    return cameras

@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: Session = Depends(get_db)):
    """Get camera by ID"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.post("/", response_model=CameraResponse)
async def create_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    """Create a new camera"""
    db_camera = Camera(
        name=camera.name,
        source=camera.source,
        location=camera.location,
        resolution=camera.resolution,
        fps=camera.fps
    )
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera

@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: int, camera: CameraCreate, db: Session = Depends(get_db)):
    """Update camera settings"""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    for field, value in camera.dict(exclude_unset=True).items():
        setattr(db_camera, field, value)
    
    db.commit()
    db.refresh(db_camera)
    return db_camera

@router.delete("/{camera_id}")
async def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    """Delete camera (soft delete)"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    camera.is_active = False
    db.commit()
    return {"message": "Camera deleted successfully"}

@router.get("/{camera_id}/stream")
async def get_camera_stream(camera_id: int, db: Session = Depends(get_db)):
    """Get camera stream URL"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {"stream_url": camera.source, "camera_name": camera.name}
