from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio
import cv2
import base64
import numpy as np

from app.database import get_db, Camera, SessionLocal
from app.schemas import CameraCreate, CameraResponse
from app.websocket_manager import manager
from app.recognition_engine import face_recognition_engine

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
    """WebSocket endpoint for real-time camera stream"""
    print(f"DEBUG: WebSocket connection started for camera {camera_id}")
    
    # Debug: Check what SessionLocal is
    print(f"DEBUG: SessionLocal type: {type(SessionLocal)}")
    print(f"DEBUG: SessionLocal(): {SessionLocal}")
    print(f"DEBUG: SessionLocal() type: {type(SessionLocal())}")
    
    await manager.connect(websocket)
    
    # Create database session
    db = SessionLocal()
    print(f"DEBUG: db type: {type(db)}")
    print(f"DEBUG: db has query attribute: {hasattr(db, 'query')}")
    
    # Initialize variables for finally block
    test_mode = False
    cap = None
    
    try:
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
        
        # For testing: If source is "0", use default camera (webcam)
        # If source is a test URL, generate test frames
        source = camera.source
        
        # Check if it's a test source
        if source == "0" or source.lower() == "test":
            # Use default camera (usually webcam)
            print(f"DEBUG: Using webcam (source=0) for camera {camera_id}")
            cap = cv2.VideoCapture(0)
            test_mode = False
        elif source.startswith("test://"):
            # Test mode with generated frames
            print(f"DEBUG: Using test mode for camera {camera_id}")
            cap = None
            test_mode = True
            test_pattern = source.replace("test://", "")
        else:
            # Real camera stream (RTSP, HTTP, etc.)
            # For RTSP streams, use TCP transport for better reliability
            if source.startswith("rtsp://"):
                # Add RTSP transport parameters
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
                # Try fallback to test mode
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
        
        frame_count = 0
        last_ping_time = asyncio.get_event_loop().time()
        
        # Frame timing control
        target_fps = camera.fps if camera.fps and camera.fps > 0 else 15
        frame_interval = 1.0 / target_fps
        last_frame_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                frame_start_time = asyncio.get_event_loop().time()
                
                # Check for client messages (ping/pong)
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)  # Reduced timeout
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": asyncio.get_event_loop().time()
                        }))
                        last_ping_time = asyncio.get_event_loop().time()
                        
                except asyncio.TimeoutError:
                    # No message received, continue with frame processing
                    pass
                
                # Generate or capture frame
                if test_mode:
                    # Generate test frame
                    frame = generate_test_frame(frame_count, test_pattern if 'test_pattern' in locals() else "default")
                    ret = True
                else:
                    # Read frame from camera
                    ret, frame = cap.read()
                    if not ret:
                        # Try to reopen the stream
                        print(f"Failed to read frame from camera {camera_id}, attempting to reopen...")
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
                            # Switch to test mode
                            cap = None
                            test_mode = True
                            test_pattern = "reconnect_fallback"
                            continue
                        else:
                            # Try reading again
                            ret, frame = cap.read()
                            if not ret:
                                continue
                
                # Perform face recognition on the captured frame (every 20 frames for performance)
                # Use a separate task to avoid blocking the frame processing
                recognition_interval = 20
                if frame_count % recognition_interval == 0:
                    # Create a copy of the frame for async processing to avoid frame modification issues
                    frame_copy = frame.copy() if hasattr(frame, 'copy') else frame
                    
                    # Run recognition asynchronously without waiting for completion
                    # This prevents blocking the frame streaming
                    async def process_recognition_async(frame_to_process, db_session, current_frame_count):
                        try:
                            recognition_result = await face_recognition_engine.recognize_face(frame_to_process, db_session)
                            if recognition_result:
                                print(f"DEBUG: Face recognized in frame {current_frame_count}: {recognition_result.get('attendee_name', 'Unknown')} with confidence {recognition_result.get('confidence', 0.0):.2f}")
                                # Send recognition results via WebSocket
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
                        except Exception as e:
                            print(f"DEBUG: Face recognition error in frame {current_frame_count}: {e}")
                    
                    # Start the recognition task without waiting for it to complete
                    asyncio.create_task(process_recognition_async(frame_copy, db, frame_count))
                
                # Increment frame count
                frame_count += 1

                # Get original frame dimensions
                original_height, original_width = frame.shape[:2]
                
                # Calculate target dimensions maintaining aspect ratio
                # Target max dimension 640px for better quality but reasonable bandwidth
                max_dimension = 640
                if original_width > original_height:
                    target_width = max_dimension
                    target_height = int(original_height * (max_dimension / original_width))
                else:
                    target_height = max_dimension
                    target_width = int(original_width * (max_dimension / original_height))
                
                # Ensure even dimensions (helps with some codecs)
                target_width = target_width - (target_width % 2)
                target_height = target_height - (target_height % 2)
                
                # Resize frame for optimal bandwidth/quality balance
                frame = cv2.resize(frame, (target_width, target_height))
                
                # Encode frame as JPEG with adaptive quality
                # Higher quality for smaller images, lower for larger
                jpeg_quality = max(50, 90 - (target_width * target_height) // 5000)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                frame_data = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame via WebSocket
                await websocket.send_text(json.dumps({
                    "type": "frame",
                    "camera_id": camera_id,  # Add camera_id for filtering
                    "frame_id": frame_count,
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": frame_data,
                    "width": target_width,
                    "height": target_height,
                    "original_width": original_width,
                    "original_height": original_height,
                    "test_mode": test_mode
                }))
                
                # Calculate dynamic sleep time based on target FPS
                processing_end = asyncio.get_event_loop().time()
                processing_time = processing_end - frame_start_time
                sleep_time = max(0.001, frame_interval - processing_time)
                
                # Update last frame time
                last_frame_time = processing_end
                
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
        # Clean up
        if not test_mode and cap is not None:
            cap.release()
        db.close()
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
        
        # Create gradient background using numpy vectorized operations (much faster)
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
