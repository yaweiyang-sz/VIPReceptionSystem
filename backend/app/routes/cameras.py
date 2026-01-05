from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import asyncio
import cv2
import base64
import numpy as np
import os
from datetime import datetime

from app.database import get_db, Camera, SessionLocal
from app.schemas import CameraCreate, CameraResponse
from app.websocket_manager import manager
from app.recognition_engine import face_recognition_engine

# Read environment variable for dummy face detection toggle
DUMMY_FACE_DETECTION = os.getenv("DUMMY_FACE_DETECTION", "false").lower() == "true"
print(f"DEBUG: DUMMY_FACE_DETECTION environment variable is set to: {DUMMY_FACE_DETECTION}")

router = APIRouter()

# FIXED: Camera stream manager to handle single recognition pipeline per camera
class CameraStreamManager:
    """Manages camera streams with single recognition pipeline per camera"""
    
    def __init__(self):
        self.active_cameras = {}  # camera_id -> stream_context
        self.recognition_locks = {}  # camera_id -> asyncio.Lock for recognition serialization
    
    def is_camera_active(self, camera_id: int) -> bool:
        """Check if camera is currently streaming"""
        return camera_id in self.active_cameras
    
    def register_camera(self, camera_id: int):
        """Register a new camera stream"""
        if camera_id not in self.active_cameras:
            self.active_cameras[camera_id] = {
                'frame_count': 0,
                'last_recognition_frame': -1,
                'recognition_in_progress': False,
                'last_recognition_result': None,
                'last_recognition_time': 0,
                'created_at': datetime.now()
            }
            self.recognition_locks[camera_id] = asyncio.Lock()
            print(f"Registered camera {camera_id} for streaming")
    
    def unregister_camera(self, camera_id: int):
        """Unregister camera stream"""
        if camera_id in self.active_cameras:
            del self.active_cameras[camera_id]
        if camera_id in self.recognition_locks:
            del self.recognition_locks[camera_id]
        print(f"Unregistered camera {camera_id}")
    
    def get_frame_count(self, camera_id: int) -> int:
        """Get current frame count for camera"""
        if camera_id in self.active_cameras:
            return self.active_cameras[camera_id]['frame_count']
        return 0
    
    def increment_frame_count(self, camera_id: int):
        """Increment frame count"""
        if camera_id in self.active_cameras:
            self.active_cameras[camera_id]['frame_count'] += 1
    
    def should_run_recognition(self, camera_id: int, recognition_interval: int = 30) -> bool:
        """Determine if recognition should run for this frame"""
        if camera_id not in self.active_cameras:
            return False
        
        context = self.active_cameras[camera_id]
        frame_count = context['frame_count']
        
        # Don't run if recognition is already in progress
        if context['recognition_in_progress']:
            return False
        
        # Run recognition at intervals
        frames_since_last = frame_count - context['last_recognition_frame']
        return frames_since_last >= recognition_interval
    
    def mark_recognition_start(self, camera_id: int):
        """Mark that recognition has started"""
        if camera_id in self.active_cameras:
            context = self.active_cameras[camera_id]
            context['recognition_in_progress'] = True
            context['last_recognition_frame'] = context['frame_count']
    
    def mark_recognition_complete(self, camera_id: int, result: Optional[Dict]):
        """Mark that recognition has completed"""
        if camera_id in self.active_cameras:
            context = self.active_cameras[camera_id]
            context['recognition_in_progress'] = False
            context['last_recognition_result'] = result
            context['last_recognition_time'] = datetime.now().timestamp()
    
    def get_last_recognition_result(self, camera_id: int) -> Optional[Dict]:
        """Get the last recognition result (for overlay)"""
        if camera_id in self.active_cameras:
            return self.active_cameras[camera_id]['last_recognition_result']
        return None
    
    async def get_recognition_lock(self, camera_id: int) -> asyncio.Lock:
        """Get the recognition lock for a camera"""
        if camera_id not in self.recognition_locks:
            self.recognition_locks[camera_id] = asyncio.Lock()
        return self.recognition_locks[camera_id]

# Global camera stream manager
stream_manager = CameraStreamManager()


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
    """Get camera stream information for WebSocket connection"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {
        "camera_id": camera.id,
        "camera_name": camera.name,
        "stream_source": camera.source,
        "stream_type": "websocket",
        "websocket_url": f"/api/cameras/{camera_id}/ws/stream"
    }

@router.websocket("/{camera_id}/ws/stream")
async def camera_stream_websocket(websocket: WebSocket, camera_id: int):
    """WebSocket endpoint for real-time camera stream with SINGLE recognition pipeline"""
    print(f"DEBUG: WebSocket connection started for camera {camera_id}")
    
    await manager.connect(websocket)
    
    # Create database session
    db = SessionLocal()
    
    # Initialize variables for finally block
    test_mode = False
    cap = None
    recognition_task = None
    
    try:
        # Register camera with stream manager
        stream_manager.register_camera(camera_id)
        
        # Get camera details
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            print(f"DEBUG: Camera {camera_id} not found in database")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Camera {camera_id} not found"
            }))
            await websocket.close(code=1008, reason="Camera not found")
            return
        
        print(f"DEBUG: Found camera {camera_id}: {camera.name}, source: {camera.source}")
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": f"Connected to camera {camera.name} stream",
            "camera_id": camera_id,
            "camera_name": camera.name,
            "source": camera.source
        }))
        
        # Initialize video capture
        source = camera.source
        
        # Check if it's a test source
        if source == "0" or source.lower() == "test":
            print(f"DEBUG: Using webcam (source=0) for camera {camera_id}")
            cap = cv2.VideoCapture(0)
            test_mode = False
        elif source.startswith("test://"):
            print(f"DEBUG: Using test mode for camera {camera_id}")
            cap = None
            test_mode = True
            test_pattern = source.replace("test://", "")
        else:
            # Real camera stream (RTSP, HTTP, etc.)
            if source.startswith("rtsp://"):
                source_with_params = f"{source}?rtsp_transport=tcp"
                print(f"DEBUG: Opening RTSP stream: {source_with_params}")
                cap = cv2.VideoCapture(source_with_params)
            else:
                print(f"DEBUG: Opening video source: {source}")
                cap = cv2.VideoCapture(source)
            test_mode = False
        
        if not test_mode:
            if cap.isOpened():
                print(f"DEBUG: Camera stream opened successfully for camera {camera_id}")
            else:
                print(f"DEBUG: Failed to open camera stream: {source}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Failed to open camera stream: {source}"
                }))
                cap = None
                test_mode = True
                test_pattern = "fallback"
                print(f"DEBUG: Falling back to test mode for camera {camera_id}")
        
        # Send stream information
        await websocket.send_text(json.dumps({
            "type": "stream_info",
            "width": 640,
            "height": 480,
            "fps": 15,
            "format": "jpeg",
            "test_mode": test_mode
        }))
        print(f"DEBUG: Sent stream info, test_mode={test_mode}")
        
        last_ping_time = asyncio.get_event_loop().time()
        
        # Frame timing control
        target_fps = camera.fps if camera.fps and camera.fps > 0 else 15
        frame_interval = 1.0 / target_fps
        
        # FIXED: Recognition configuration
        recognition_interval = 30  # Process recognition every 30 frames (2 seconds at 15fps)
        
        # FIXED: Single recognition worker task
        async def recognition_worker():
            """Single worker task for face recognition - processes frames sequentially"""
            print(f"DEBUG: Recognition worker started for camera {camera_id}")
            
            while stream_manager.is_camera_active(camera_id):
                try:
                    # Wait a bit before checking for new work
                    await asyncio.sleep(0.1)
                    
                    # Check if we should run recognition
                    if not stream_manager.should_run_recognition(camera_id, recognition_interval):
                        continue
                    
                    # Get lock to ensure single recognition at a time
                    lock = await stream_manager.get_recognition_lock(camera_id)
                    async with lock:
                        stream_manager.mark_recognition_start(camera_id)
                        
                        # Get current frame info
                        current_frame_count = stream_manager.get_frame_count(camera_id)
                        
                        print(f"DEBUG: Starting recognition for camera {camera_id}, frame {current_frame_count}")
                        
                        # Read a fresh frame for recognition
                        recognition_frame = None
                        if test_mode:
                            recognition_frame = generate_test_frame(current_frame_count, 
                                                                   test_pattern if 'test_pattern' in locals() else "default")
                        elif cap is not None and cap.isOpened():
                            ret, recognition_frame = cap.read()
                            if not ret or recognition_frame is None:
                                print(f"DEBUG: Failed to read frame for recognition on camera {camera_id}")
                                stream_manager.mark_recognition_complete(camera_id, None)
                                continue
                        
                        if recognition_frame is None:
                            stream_manager.mark_recognition_complete(camera_id, None)
                            continue
                        
                        # FIXED: Single recognition call with proper error handling
                        try:
                            # Check if dummy face detection is enabled
                            if DUMMY_FACE_DETECTION and current_frame_count % 100 == 0:
                                # Create dummy recognition result for testing
                                dummy_result = {
                                    'attendee_id': 999,
                                    'confidence': 0.85,
                                    'face_location': (100, 300, 200, 200),
                                    'attendee_name': 'John Doe (Test)',
                                    'first_name': 'John',
                                    'last_name': 'Doe',
                                    'company': 'Test Corporation',
                                    'position': 'VIP Guest',
                                    'is_vip': True,
                                    'email': 'john.doe@test.com',
                                    'phone': '+1-555-123-4567'
                                }
                                print(f"DEBUG: DUMMY Face recognized in frame {current_frame_count}: {dummy_result['attendee_name']} with confidence {dummy_result['confidence']:.2f}")
                                recognition_result = dummy_result
                            else:
                                # Normal face recognition
                                recognition_result = await face_recognition_engine.recognize_face(recognition_frame, db)
                            
                            if recognition_result:
                                print(f"DEBUG: Face recognized in frame {current_frame_count}: {recognition_result.get('attendee_name', 'Unknown')} with confidence {recognition_result.get('confidence', 0.0):.2f}")
                                
                                # Send recognition update via WebSocket manager
                                update_data = {
                                    "type": "recognition_update",
                                    "camera_id": camera_id,
                                    "timestamp": asyncio.get_event_loop().time(),
                                    "frame_number": current_frame_count,
                                    "frame_width": recognition_frame.shape[1],
                                    "frame_height": recognition_frame.shape[0],
                                    "detections": [{
                                        "type": "face",
                                        "confidence": recognition_result.get('confidence', 0.0),
                                        "attendee_id": recognition_result.get('attendee_id'),
                                        "attendee_name": recognition_result.get('attendee_name', 'Unknown'),
                                        "location": recognition_result.get('face_location'),
                                        "is_vip": recognition_result.get('is_vip', False),
                                        "company": recognition_result.get('company', ''),
                                        "position": recognition_result.get('position', '')
                                    }]
                                }
                                await manager.broadcast(update_data)
                                
                                # Also send to camera stream WebSocket
                                try:
                                    await websocket.send_text(json.dumps({
                                        "type": "recognition",
                                        "camera_id": camera_id,
                                        "frame_id": current_frame_count,
                                        "timestamp": asyncio.get_event_loop().time(),
                                        "result": recognition_result
                                    }))
                                except Exception as ws_error:
                                    print(f"DEBUG: Failed to send recognition result via WebSocket: {ws_error}")
                            else:
                                print(f"DEBUG: No face recognized in frame {current_frame_count}")
                            
                            # Store result for overlay
                            stream_manager.mark_recognition_complete(camera_id, recognition_result)
                            
                        except Exception as e:
                            print(f"ERROR: Face recognition error in frame {current_frame_count}: {e}")
                            stream_manager.mark_recognition_complete(camera_id, None)
                
                except asyncio.CancelledError:
                    print(f"DEBUG: Recognition worker cancelled for camera {camera_id}")
                    break
                except Exception as e:
                    print(f"ERROR: Recognition worker error for camera {camera_id}: {e}")
                    await asyncio.sleep(1)
            
            print(f"DEBUG: Recognition worker stopped for camera {camera_id}")
        
        # Start the recognition worker task
        recognition_task = asyncio.create_task(recognition_worker())
        
        # Main frame streaming loop
        while True:
            try:
                frame_start_time = asyncio.get_event_loop().time()
                
                # Check for client messages (ping/pong)
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": asyncio.get_event_loop().time()
                        }))
                        last_ping_time = asyncio.get_event_loop().time()
                        
                except asyncio.TimeoutError:
                    pass
                
                # Generate or capture frame
                if test_mode:
                    frame = generate_test_frame(stream_manager.get_frame_count(camera_id), 
                                              test_pattern if 'test_pattern' in locals() else "default")
                    ret = True
                else:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        print(f"Failed to read frame from camera {camera_id}, attempting to reopen...")
                        if cap:
                            cap.release()
                        await asyncio.sleep(1)
                        
                        if source.startswith("rtsp://"):
                            source_with_params = f"{source}?rtsp_transport=tcp"
                            cap = cv2.VideoCapture(source_with_params)
                        else:
                            cap = cv2.VideoCapture(source)
                        
                        if not cap.isOpened():
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "Camera stream disconnected"
                            }))
                            cap = None
                            test_mode = True
                            test_pattern = "reconnect_fallback"
                            continue
                        else:
                            ret, frame = cap.read()
                            if not ret:
                                continue
                
                # Increment frame count
                stream_manager.increment_frame_count(camera_id)
                current_frame_count = stream_manager.get_frame_count(camera_id)
                
                # Get original frame dimensions
                original_height, original_width = frame.shape[:2]
                
                # Calculate target dimensions maintaining aspect ratio
                max_dimension = 800  # Increased for better recognition quality
                if original_width > original_height:
                    target_width = max_dimension
                    target_height = int(original_height * (max_dimension / original_width))
                else:
                    target_height = max_dimension
                    target_width = int(original_width * (max_dimension / original_height))
                
                # Ensure even dimensions
                target_width = target_width - (target_width % 2)
                target_height = target_height - (target_height % 2)
                
                # Resize frame
                frame = cv2.resize(frame, (target_width, target_height))
                
                # Encode frame as JPEG with better quality
                jpeg_quality = max(75, 95 - (target_width * target_height) // 10000)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                frame_data = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame via WebSocket
                await websocket.send_text(json.dumps({
                    "type": "frame",
                    "camera_id": camera_id,
                    "frame_id": current_frame_count,
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": frame_data,
                    "width": target_width,
                    "height": target_height,
                    "original_width": original_width,
                    "original_height": original_height,
                    "test_mode": test_mode
                }))
                
                # Calculate dynamic sleep time
                processing_end = asyncio.get_event_loop().time()
                processing_time = processing_end - frame_start_time
                sleep_time = max(0.001, frame_interval - processing_time)
                
                await asyncio.sleep(sleep_time)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error processing camera stream {camera_id}: {e}")
                await asyncio.sleep(0.1)
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for camera {camera_id}")
    except Exception as e:
        print(f"WebSocket connection error for camera {camera_id}: {e}")
    finally:
        # Clean up recognition task
        if recognition_task and not recognition_task.done():
            recognition_task.cancel()
            try:
                await recognition_task
            except asyncio.CancelledError:
                pass
        
        # Unregister camera
        stream_manager.unregister_camera(camera_id)
        
        # Clean up capture
        if not test_mode and cap is not None:
            cap.release()
        
        # Close database
        db.close()
        
        # Disconnect websocket
        manager.disconnect(websocket)
        
        print(f"Camera stream WebSocket closed for camera {camera_id}")

def generate_test_frame(frame_count: int, pattern: str = "default") -> np.ndarray:
    """Generate a test frame for demonstration"""
    # Create a 480x640 frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    if pattern == "color_bars":
        # Color bars pattern
        colors = [
            (255, 255, 255),  # White
            (255, 255, 0),    # Yellow
            (0, 255, 255),    # Cyan
            (0, 255, 0),      # Green
            (255, 0, 255),    # Magenta
            (255, 0, 0),      # Red
            (0, 0, 255),      # Blue
            (0, 0, 0),        # Black
        ]
        bar_width = 640 // len(colors)
        for i, color in enumerate(colors):
            cv2.rectangle(frame, (i * bar_width, 0), ((i + 1) * bar_width, 480), color, -1)
    else:
        # Default moving pattern - optimized version
        center_x = 320 + int(200 * np.sin(frame_count * 0.1))
        center_y = 240 + int(150 * np.cos(frame_count * 0.07))
        
        # Create gradient background using numpy vectorized operations
        x = np.arange(640)
        y = np.arange(480)
        X, Y = np.meshgrid(x, y)
        
        # Calculate colors using vectorized operations
        r = (128 + 127 * np.sin(X * 0.01 + frame_count * 0.05)).astype(np.uint8)
        g = (128 + 127 * np.sin(Y * 0.01 + frame_count * 0.03)).astype(np.uint8)
        b = (128 + 127 * np.sin((X + Y) * 0.005 + frame_count * 0.02)).astype(np.uint8)
        
        # Combine channels
        frame = np.stack([b, g, r], axis=2)
        
        # Draw moving circle
        cv2.circle(frame, (center_x, center_y), 50, (0, 255, 0), 3)
        cv2.putText(frame, f"Test Frame {frame_count}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "VIP Reception System", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 255), 2)
        cv2.putText(frame, "Camera Stream Demo", (50, 140), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 255, 200), 2)
    
    return frame