from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Optional
import json
import base64
import cv2
import numpy as np
import asyncio

from app.database import get_db, Attendee, Visit, Camera
from app.schemas import RecognitionRequest, RecognitionResponse
from app.recognition_engine import FaceRecognitionEngine, QRCodeEngine, camera_stream_processor
from app.websocket_manager import manager

router = APIRouter()

# Initialize recognition engines
face_engine = FaceRecognitionEngine()
qr_engine = QRCodeEngine()

@router.post("/face", response_model=RecognitionResponse)
async def recognize_face(request: RecognitionRequest, db: Session = Depends(get_db)):
    """Recognize attendee by face"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_data.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Perform face recognition
        result = await face_engine.recognize_face(image)
        
        if result and result.get('attendee_id'):
            attendee = db.query(Attendee).filter(Attendee.id == result['attendee_id']).first()
            if attendee:
                # Log the visit
                visit = Visit(
                    attendee_id=attendee.id,
                    recognition_method="face",
                    camera_id=request.camera_id
                )
                db.add(visit)
                db.commit()
                
                # Update attendee status
                attendee.status = "checked_in"
                db.commit()
                
                # Send WebSocket notification
                await manager.broadcast({
                    "type": "attendee_recognized",
                    "attendee": {
                        "id": attendee.id,
                        "name": f"{attendee.first_name} {attendee.last_name}",
                        "company": attendee.company,
                        "position": attendee.position,
                        "is_vip": attendee.is_vip
                    },
                    "recognition_method": "face",
                    "camera_id": request.camera_id
                })
                
                return RecognitionResponse(
                    success=True,
                    attendee=attendee,
                    confidence=result.get('confidence', 0.0),
                    method="face"
                )
        
        return RecognitionResponse(
            success=False,
            message="No matching attendee found",
            method="face"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face recognition failed: {str(e)}")

@router.post("/qr", response_model=RecognitionResponse)
async def scan_qr_code(request: RecognitionRequest, db: Session = Depends(get_db)):
    """Recognize attendee by QR code"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_data.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Scan QR code
        qr_data = await qr_engine.scan_qr_code(image)
        
        if qr_data:
            attendee = db.query(Attendee).filter(Attendee.qr_code == qr_data).first()
            if attendee:
                # Log the visit
                visit = Visit(
                    attendee_id=attendee.id,
                    recognition_method="qr_code",
                    camera_id=request.camera_id
                )
                db.add(visit)
                db.commit()
                
                # Update attendee status
                attendee.status = "checked_in"
                db.commit()
                
                # Send WebSocket notification
                await manager.broadcast({
                    "type": "attendee_recognized",
                    "attendee": {
                        "id": attendee.id,
                        "name": f"{attendee.first_name} {attendee.last_name}",
                        "company": attendee.company,
                        "position": attendee.position,
                        "is_vip": attendee.is_vip
                    },
                    "recognition_method": "qr_code",
                    "camera_id": request.camera_id
                })
                
                return RecognitionResponse(
                    success=True,
                    attendee=attendee,
                    confidence=1.0,
                    method="qr_code"
                )
        
        return RecognitionResponse(
            success=False,
            message="Invalid or unrecognized QR code",
            method="qr_code"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR code scanning failed: {str(e)}")

@router.post("/auto")
async def auto_recognition(request: RecognitionRequest, db: Session = Depends(get_db)):
    """Automatically try both face recognition and QR code scanning"""
    try:
        # Try face recognition first
        face_result = await recognize_face(request, db)
        if face_result.success:
            return face_result
        
        # If face recognition fails, try QR code
        qr_result = await scan_qr_code(request, db)
        return qr_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto recognition failed: {str(e)}")

@router.post("/start-stream/{camera_id}")
async def start_recognition_stream(camera_id: int, db: Session = Depends(get_db)):
    """Start real-time recognition for a camera stream"""
    try:
        # Get camera details
        camera = db.query(Camera).filter(Camera.id == camera_id, Camera.is_active == True).first()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found or inactive")
        
        # Start stream processing
        success = await camera_stream_processor.start_stream_processing(
            camera_id=camera_id,
            stream_url=camera.source,
            db=db
        )
        
        if success:
            return {"message": f"Started real-time recognition for camera {camera_id}", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to start stream processing")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recognition stream: {str(e)}")

@router.post("/stop-stream/{camera_id}")
async def stop_recognition_stream(camera_id: int):
    """Stop real-time recognition for a camera stream"""
    try:
        camera_stream_processor.stop_stream_processing(camera_id)
        return {"message": f"Stopped real-time recognition for camera {camera_id}", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop recognition stream: {str(e)}")

@router.websocket("/ws/stream/{camera_id}")
async def recognition_stream(websocket: WebSocket, camera_id: int):
    """WebSocket endpoint for real-time recognition stream with annotated frames"""
    await manager.connect(websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": f"Connected to real-time recognition for camera {camera_id}",
            "camera_id": camera_id
        }))
        
        while True:
            try:
                # Keep connection alive and wait for messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error for camera {camera_id}: {e}")
                # Continue the loop to keep connection alive
                await asyncio.sleep(0.1)
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for camera {camera_id}")
    except Exception as e:
        print(f"WebSocket connection error for camera {camera_id}: {e}")
    finally:
        manager.disconnect(websocket)
        print(f"WebSocket connection closed for camera {camera_id}")
