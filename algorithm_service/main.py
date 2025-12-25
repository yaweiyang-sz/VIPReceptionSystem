from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
import cv2
import face_recognition
import pickle
import base64
import json
import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="VIP Reception Algorithm Service", 
              description="Face recognition algorithm service for VIP reception system",
              version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vip_user:vip_password@db:5432/vip_reception")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis for caching
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Database models
class Attendee(Base):
    __tablename__ = "attendees"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    company = Column(String(255))
    position = Column(String(255))
    phone = Column(String(50))
    photo_url = Column(Text)
    face_encoding = Column(Text)
    face_encoding_version = Column(String(10), default="v1")
    qr_code = Column(String(100), unique=True, index=True)
    is_vip = Column(Boolean, default=False)
    status = Column(String(50), default="registered")
    face_encoding_quality = Column(String(20), default="standard")
    face_encoding_created = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Face recognition model manager
class FaceRecognitionModel:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_metadata = []  # List of dicts with attendee info
        self.model_loaded = False
        self.last_update_time = None
        self.cache_key = "face_recognition_model"
        
    def load_from_database(self, db: Session):
        """Load face encodings from database"""
        try:
            logger.info("Loading face encodings from database")
            attendees = db.query(Attendee).filter(
                Attendee.face_encoding.isnot(None),
                Attendee.status == "registered"
            ).all()
            
            self.known_face_encodings = []
            self.known_face_metadata = []
            
            for attendee in attendees:
                try:
                    # Decode face encoding from base64
                    encoding_data = base64.b64decode(attendee.face_encoding)
                    encoding = pickle.loads(encoding_data)
                    
                    self.known_face_encodings.append(encoding)
                    self.known_face_metadata.append({
                        'attendee_id': attendee.id,
                        'first_name': attendee.first_name,
                        'last_name': attendee.last_name,
                        'company': attendee.company,
                        'position': attendee.position,
                        'is_vip': attendee.is_vip,
                        'email': attendee.email,
                        'phone': attendee.phone
                    })
                    
                except Exception as e:
                    logger.error(f"Error loading encoding for attendee {attendee.id}: {e}")
            
            self.model_loaded = True
            self.last_update_time = datetime.now()
            logger.info(f"Loaded {len(self.known_face_encodings)} face encodings from database")
            
            # Cache the model in Redis
            self._cache_model()
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading face encodings from database: {e}")
            return False
    
    def _cache_model(self):
        """Cache the model in Redis for faster access"""
        try:
            # For simplicity, we'll cache metadata only
            cache_data = {
                'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
                'count': len(self.known_face_encodings),
                'metadata': json.dumps(self.known_face_metadata)
            }
            redis_client.hset(self.cache_key, mapping=cache_data)
            redis_client.expire(self.cache_key, 3600)  # Expire in 1 hour
        except Exception as e:
            logger.error(f"Error caching model: {e}")
    
    def add_face_encoding(self, encoding: np.ndarray, metadata: Dict[str, Any]):
        """Add a new face encoding to the model"""
        self.known_face_encodings.append(encoding)
        self.known_face_metadata.append(metadata)
        self.last_update_time = datetime.now()
        self._cache_model()
    
    def recognize_face(self, image: np.ndarray, tolerance: float = 0.6) -> Optional[Dict[str, Any]]:
        """Recognize faces in the given image"""
        if not self.model_loaded or len(self.known_face_encodings) == 0:
            logger.warning("Face recognition model not loaded or empty")
            return None
        
        try:
            # Find all face locations in the image
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return None
            
            # Get face encodings for each face
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return None
            
            # For each face, find matches
            for i, face_encoding in enumerate(face_encodings):
                # Compare with known faces
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding,
                    tolerance=tolerance
                )
                
                face_distances = face_recognition.face_distance(
                    self.known_face_encodings, 
                    face_encoding
                )
                
                # Find the best match
                best_match_index = None
                if True in matches:
                    # Get the index of the best match (lowest distance)
                    best_match_index = np.argmin(face_distances)
                    best_distance = face_distances[best_match_index]
                    
                    # Convert distance to confidence (0-1, higher is better)
                    confidence = 1.0 - min(best_distance, 1.0)
                    
                    if confidence >= 0.5:  # Minimum confidence threshold
                        metadata = self.known_face_metadata[best_match_index]
                        
                        return {
                            'attendee_id': metadata['attendee_id'],
                            'first_name': metadata['first_name'],
                            'last_name': metadata['last_name'],
                            'full_name': f"{metadata['first_name']} {metadata['last_name']}",
                            'company': metadata['company'],
                            'position': metadata['position'],
                            'is_vip': metadata['is_vip'],
                            'email': metadata['email'],
                            'phone': metadata['phone'],
                            'confidence': float(confidence),
                            'face_location': face_locations[i],  # (top, right, bottom, left)
                            'face_index': i,
                            'num_faces_found': len(face_locations)
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            return None
    
    def encode_face(self, image: np.ndarray) -> Optional[List[Dict[str, Any]]]:
        """Encode faces in the given image"""
        try:
            # Find all face locations
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return []
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            results = []
            for i, (encoding, location) in enumerate(zip(face_encodings, face_locations)):
                # Convert encoding to base64 for storage
                encoding_bytes = pickle.dumps(encoding)
                encoding_b64 = base64.b64encode(encoding_bytes).decode('utf-8')
                
                results.append({
                    'encoding': encoding_b64,
                    'face_location': location,
                    'face_index': i,
                    'num_faces_found': len(face_locations)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error encoding face: {e}")
            return None

# Global model instance
face_model = FaceRecognitionModel()

# API endpoints
@app.get("/")
async def root():
    return {
        "service": "VIP Reception Algorithm Service",
        "version": "1.0.0",
        "status": "operational",
        "model_loaded": face_model.model_loaded,
        "faces_loaded": len(face_model.known_face_encodings)
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_status": "loaded" if face_model.model_loaded else "not_loaded"
    }

@app.post("/api/v1/recognize")
async def recognize_vip(
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Recognize VIP from image frame
    Called from camera.py each loop when successfully read a frame
    """
    try:
        # Read image file
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Ensure model is loaded
        if not face_model.model_loaded:
            face_model.load_from_database(db)
        
        # Perform face recognition
        recognition_result = face_model.recognize_face(rgb_img)
        
        if recognition_result:
            logger.info(f"Recognized VIP: {recognition_result['full_name']} (ID: {recognition_result['attendee_id']})")
            
            # Get additional information from database
            attendee = db.query(Attendee).filter(Attendee.id == recognition_result['attendee_id']).first()
            if attendee:
                recognition_result['additional_info'] = {
                    'qr_code': attendee.qr_code,
                    'photo_url': attendee.photo_url,
                    'status': attendee.status,
                    'created_at': attendee.created_at.isoformat() if attendee.created_at else None
                }
            
            return {
                "success": True,
                "recognition": recognition_result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": True,
                "recognition": None,
                "message": "No VIP recognized",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in recognition: {e}")
        raise HTTPException(status_code=500, detail=f"Recognition error: {str(e)}")

@app.post("/api/v1/encode")
async def encode_face(
    image: UploadFile = File(...),
    attendee_id: Optional[int] = None,
    metadata: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Encode face from image and optionally update model
    Called from encode_face function in recognition_engine.py
    """
    try:
        # Read image file
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # Convert BGR to RGB
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Encode face
        encoding_results = face_model.encode_face(rgb_img)
        
        if not encoding_results or len(encoding_results) == 0:
            return {
                "success": False,
                "message": "No faces found in image",
                "timestamp": datetime.now().isoformat()
            }
        
        response = {
            "success": True,
            "encodings": encoding_results,
            "num_faces": len(encoding_results),
            "timestamp": datetime.now().isoformat()
        }
        
        # If attendee_id is provided, update the model with this encoding
        if attendee_id is not None and len(encoding_results) > 0:
            try:
                # Get attendee from database
                attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
                if attendee:
                    # Update attendee's face encoding in database
                    attendee.face_encoding = encoding_results[0]['encoding']
                    attendee.face_encoding_created = datetime.now()
                    db.commit()
                    
                    # Update in-memory model
                    if metadata:
                        metadata_dict = json.loads(metadata)
                    else:
                        metadata_dict = {
                            'attendee_id': attendee.id,
                            'first_name': attendee.first_name,
                            'last_name': attendee.last_name,
                            'company': attendee.company,
                            'position': attendee.position,
                            'is_vip': attendee.is_vip,
                            'email': attendee.email,
                            'phone': attendee.phone
                        }
                    
                    # Decode encoding for model storage
                    encoding_bytes = base64.b64decode(encoding_results[0]['encoding'])
                    encoding_obj = pickle.loads(encoding_bytes)
                    face_model.add_face_encoding(encoding_obj, metadata_dict)
                    
                    response['model_updated'] = True
                    response['attendee_id'] = attendee_id
                    logger.info(f"Updated face encoding for attendee {attendee_id}")
                
            except Exception as e:
                logger.error(f"Error updating model for attendee {attendee_id}: {e}")
                response['model_update_error'] = str(e)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in face encoding: {e}")
        raise HTTPException(status_code=500, detail=f"Encoding error: {str(e)}")

@app.post("/api/v1/model/update")
async def update_model(db: Session = Depends(get_db)):
    """
    Force update the face recognition model from database
    """
    try:
        success = face_model.load_from_database(db)
        
        if success:
            return {
                "success": True,
                "message": f"Model updated with {len(face_model.known_face_encodings)} faces",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Failed to update model",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        raise HTTPException(status_code=500, detail=f"Model update error: {str(e)}")

@app.get("/api/v1/model/status")
async def model_status():
    """
    Get current model status
    """
    return {
        "model_loaded": face_model.model_loaded,
        "faces_loaded": len(face_model.known_face_encodings),
        "last_update": face_model.last_update_time.isoformat() if face_model.last_update_time else None,
        "timestamp": datetime.now().isoformat()
    }

# Startup event to load model
@app.on_event("startup")
async def startup_event():
    """Load face recognition model on startup"""
    logger.info("Starting up algorithm service...")
    # Model will be loaded on first request with database session

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
