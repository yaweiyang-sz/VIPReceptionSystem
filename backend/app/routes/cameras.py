from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import json
import os

from app.database import get_db, Camera
from app.schemas import CameraCreate, CameraResponse
from app.stream_converter import stream_converter

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
    """Get camera stream URL - converts RTSP to HLS if needed"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    source = camera.source
    
    # Check if it's an RTSP stream
    if source.startswith("rtsp://"):
        try:
            # Convert RTSP to HLS
            hls_url = stream_converter.convert_rtsp_to_hls(camera_id, source)
            return {
                "stream_url": hls_url,
                "camera_name": camera.name,
                "stream_type": "hls"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to convert RTSP stream: {str(e)}")
    else:
        # For HTTP streams, return as-is
        return {
            "stream_url": source,
            "camera_name": camera.name,
            "stream_type": "http"
        }

@router.get("/{camera_id}/hls/{filename}")
async def serve_hls_file(camera_id: int, filename: str):
    """Serve HLS files (playlist and segments)"""
    stream_info = stream_converter.get_stream_info(camera_id)
    if not stream_info:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    file_path = os.path.join(stream_info["output_dir"], filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Set appropriate content type
    if filename.endswith(".m3u8"):
        media_type = "application/vnd.apple.mpegurl"
    elif filename.endswith(".ts"):
        media_type = "video/mp2t"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(file_path, media_type=media_type)

@router.delete("/{camera_id}/stream")
async def stop_camera_stream(camera_id: int):
    """Stop the camera stream conversion"""
    stream_converter.stop_stream(camera_id)
    return {"message": "Stream stopped successfully"}
