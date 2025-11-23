from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os
import time
import logging

logger = logging.getLogger(__name__)

from app.database import get_db, Attendee, Visit
from app.schemas import AttendeeCreate, AttendeeResponse, AttendeeUpdate
from app.recognition_engine import FaceRecognitionEngine

router = APIRouter()
face_engine = FaceRecognitionEngine()

@router.get("/", response_model=List[AttendeeResponse])
async def list_attendees(
    skip: int = 0,
    limit: int = 100,
    is_vip: Optional[bool] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all attendees with optional filtering"""
    query = db.query(Attendee)
    
    if is_vip is not None:
        query = query.filter(Attendee.is_vip == is_vip)
    
    if status:
        query = query.filter(Attendee.status == status)
    
    attendees = query.offset(skip).limit(limit).all()
    return attendees

@router.get("/{attendee_id}", response_model=AttendeeResponse)
async def get_attendee(attendee_id: int, db: Session = Depends(get_db)):
    """Get attendee by ID"""
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return attendee

@router.post("/", response_model=AttendeeResponse)
async def create_attendee(attendee: AttendeeCreate, db: Session = Depends(get_db)):
    """Create a new attendee"""
    # Check if email already exists
    existing_attendee = db.query(Attendee).filter(Attendee.email == attendee.email).first()
    if existing_attendee:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate unique QR code
    qr_code = str(uuid.uuid4())
    
    db_attendee = Attendee(
        first_name=attendee.first_name,
        last_name=attendee.last_name,
        email=attendee.email,
        company=attendee.company,
        position=attendee.position,
        phone=attendee.phone,
        is_vip=attendee.is_vip,
        qr_code=qr_code
    )
    
    db.add(db_attendee)
    db.commit()
    db.refresh(db_attendee)
    
    return db_attendee

@router.put("/{attendee_id}", response_model=AttendeeResponse)
async def update_attendee(attendee_id: int, attendee: AttendeeUpdate, db: Session = Depends(get_db)):
    """Update attendee information"""
    db_attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not db_attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    # Check if email is being changed and already exists
    if attendee.email and attendee.email != db_attendee.email:
        existing_attendee = db.query(Attendee).filter(Attendee.email == attendee.email).first()
        if existing_attendee:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    for field, value in attendee.dict(exclude_unset=True).items():
        setattr(db_attendee, field, value)
    
    db.commit()
    db.refresh(db_attendee)
    return db_attendee

@router.delete("/{attendee_id}")
async def delete_attendee(attendee_id: int, db: Session = Depends(get_db)):
    """Delete attendee"""
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    db.delete(attendee)
    db.commit()
    return {"message": "Attendee deleted successfully"}

@router.post("/{attendee_id}/upload-photo")
async def upload_attendee_photo(
    attendee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process attendee photo for face recognition"""
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    try:
        # Read file content
        contents = await file.read()
        logger.info(f"Received file: {file.filename}, size: {len(contents)} bytes")
        
        # Save the actual file first
        os.makedirs("/app/data/faces", exist_ok=True)
        file_path = f"/app/data/faces/{attendee_id}.jpg"
        with open(file_path, "wb") as f:
            f.write(contents)
        logger.info(f"Saved photo to: {file_path}")
        
        # Try to process face encoding, but don't fail if it doesn't work
        face_encoding_saved = False
        face_detection_details = {
            "success": False,
            "message": "No face detected in the image",
            "num_faces_found": 0,
            "face_locations": []
        }
        
        try:
            encoding_result = await face_engine.encode_face(contents)
            if encoding_result:
                # Save face encoding to database
                attendee.face_encoding = encoding_result[0]['encoding']
                attendee.face_encoding_version = "v1"
                attendee.face_encoding_quality = "standard"
                face_encoding_saved = True
                
                # Update face detection details
                face_detection_details = {
                    "success": True,
                    "message": f"Successfully detected and encoded {len(encoding_result)} face(s)",
                    "num_faces_found": len(encoding_result),
                    "face_locations": [result.get('face_location', []) for result in encoding_result]
                }
                
                # Update the face cache
                face_engine.update_known_faces(
                    attendee_id, 
                    encoding_result[0]['encoding'],
                    {
                        'name': f"{attendee.first_name} {attendee.last_name}",
                        'company': attendee.company,
                        'is_vip': attendee.is_vip,
                        'last_updated': time.time()
                    }
                )
                logger.info(f"Face encoding saved for attendee {attendee_id}")
            else:
                # No faces detected
                face_detection_details = {
                    "success": False,
                    "message": "No face detected in the image. Please upload a clear photo with a visible face.",
                    "num_faces_found": 0,
                    "face_locations": []
                }
                logger.warning(f"No face detected in image for attendee {attendee_id}")
        except Exception as face_error:
            face_detection_details = {
                "success": False,
                "message": f"Face detection error: {str(face_error)}",
                "num_faces_found": 0,
                "face_locations": []
            }
            logger.warning(f"Face encoding failed: {face_error}")
        
        # Always save the photo URL, even if no face was detected
        attendee.photo_url = f"/api/attendees/{attendee_id}/photo"
        db.commit()
        logger.info(f"Updated attendee {attendee_id} with photo URL: {attendee.photo_url}")
        
        return {
            "message": "Photo uploaded successfully",
            "attendee_id": attendee_id,
            "face_encoding_saved": face_encoding_saved,
            "face_detection_details": face_detection_details,
            "photo_url": f"/api/attendees/{attendee_id}/photo"
        }
            
    except Exception as e:
        logger.error(f"Photo processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Photo processing failed: {str(e)}")

@router.get("/{attendee_id}/photo")
async def get_attendee_photo(attendee_id: int):
    """Serve attendee photo"""
    photo_path = f"/app/data/faces/{attendee_id}.jpg"
    
    if not os.path.exists(photo_path):
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Return the image file with cache control headers to prevent caching
    return FileResponse(
        photo_path, 
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.get("/{attendee_id}/visits")
async def get_attendee_visits(attendee_id: int, db: Session = Depends(get_db)):
    """Get visit history for an attendee"""
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    visits = db.query(Visit).filter(Visit.attendee_id == attendee_id).all()
    
    return {
        "attendee": attendee,
        "visits": visits
    }

@router.post("/{attendee_id}/check-out")
async def check_out_attendee(attendee_id: int, db: Session = Depends(get_db)):
    """Check out an attendee"""
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    # Find the latest visit without check-out time
    latest_visit = db.query(Visit).filter(
        Visit.attendee_id == attendee_id,
        Visit.check_out_time.is_(None)
    ).order_by(Visit.check_in_time.desc()).first()
    
    if latest_visit:
        from datetime import datetime
        latest_visit.check_out_time = datetime.utcnow()
        attendee.status = "checked_out"
        db.commit()
        
        return {"message": "Attendee checked out successfully"}
    else:
        raise HTTPException(status_code=400, detail="No active visit found for this attendee")

@router.get("/search/{query}")
async def search_attendees(query: str, db: Session = Depends(get_db)):
    """Search attendees by name, email, or company"""
    attendees = db.query(Attendee).filter(
        (Attendee.first_name.ilike(f"%{query}%")) |
        (Attendee.last_name.ilike(f"%{query}%")) |
        (Attendee.email.ilike(f"%{query}%")) |
        (Attendee.company.ilike(f"%{query}%"))
    ).all()
    
    return attendees
