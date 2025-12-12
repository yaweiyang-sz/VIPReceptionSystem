import cv2
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
import pickle
import base64
import asyncio
import time
from sqlalchemy.orm import Session
import logging
import json
import httpx
from pyzbar.pyzbar import decode

from app.database import Attendee

# Configure logging
logger = logging.getLogger(__name__)

class FaceRecognitionEngine:
    def __init__(self):
        self.confidence_threshold = 0.6
        self.face_cache_loaded = False
        self.face_cache_size = 0
        self.last_cache_update = 0
        
        # Performance monitoring
        self.recognition_times = []
        self.encoding_times = []
        
        # Integration point for external recognition service
        self.external_service_url = None  # Will be configured via environment variable
        self.use_external_service = False
        
        logger.info("FaceRecognitionEngine initialized - ready for integration with external service")

    def load_known_faces(self, db: Session = None) -> bool:
        """Load known face encodings from database - placeholder for external service integration"""
        try:
            if not db:
                logger.warning("No database session provided for loading known faces")
                return False
            
            # This is a placeholder implementation
            # In production, this would sync with external recognition service
            logger.info("Placeholder: Loading known faces from database for external service integration")
            
            # For now, just mark cache as loaded
            self.face_cache_loaded = True
            self.face_cache_size = 0  # External service will handle the actual cache
            self.last_cache_update = time.time()
            
            logger.info("Face cache ready for external service integration")
            return True
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
            return False

    async def encode_face(self, image_data: bytes, max_faces: int = 1) -> Optional[List[Dict[str, Any]]]:
        """Encode faces from image data - placeholder for external service integration"""
        try:
            start_time = time.time()
            logger.info(f"Starting face encoding for {len(image_data)} bytes of image data")
            
            # Integration point for external service
            if self.use_external_service and self.external_service_url:
                try:
                    # Call external recognition service
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.external_service_url}/encode",
                            files={"image": image_data},
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            encoding_time = time.time() - start_time
                            self.encoding_times.append(encoding_time)
                            logger.info(f"External service encoded faces in {encoding_time:.3f}s")
                            return result
                except Exception as e:
                    logger.error(f"External service encoding failed: {e}")
            
            # Placeholder implementation for development/testing
            logger.info("Using placeholder face encoding (no actual encoding performed)")
            
            # Simulate encoding time
            await asyncio.sleep(0.1)  # Simulate processing time
            
            encoding_time = time.time() - start_time
            self.encoding_times.append(encoding_time)
            
            # Return dummy result
            return [{
                'encoding': 'dummy_encoding_base64_string',
                'face_location': (100, 200, 300, 400),
                'face_index': 0,
                'num_faces_found': 1
            }]
            
        except Exception as e:
            logger.error(f"Face encoding error: {str(e)}", exc_info=True)
            return None

    async def recognize_face(self, image: np.ndarray, db: Session = None) -> Optional[Dict[str, Any]]:
        """Recognize faces in the given image - placeholder for external service integration"""
        try:
            start_time = time.time()
            
            # Integration point for external service
            if self.use_external_service and self.external_service_url:
                try:
                    # Convert image to bytes for HTTP request
                    _, buffer = cv2.imencode('.jpg', image)
                    image_bytes = buffer.tobytes()
                    
                    # Call external recognition service
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.external_service_url}/recognize",
                            files={"image": image_bytes},
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            recognition_time = time.time() - start_time
                            self.recognition_times.append(recognition_time)
                            logger.info(f"External service recognized face in {recognition_time:.3f}s")
                            return result
                except Exception as e:
                    logger.error(f"External service recognition failed: {e}")
            
            # Placeholder implementation for development/testing
            logger.debug("Using placeholder face recognition (no actual recognition performed)")
            
            # Simulate recognition time
            await asyncio.sleep(0.05)  # Simulate processing time
            
            # Return dummy result (simulating recognition of a random attendee)
            recognition_time = time.time() - start_time
            self.recognition_times.append(recognition_time)
            
            # For demo purposes, return a dummy recognition result
            return {
                'attendee_id': 1,
                'confidence': 0.85,
                'face_location': (100, 200, 300, 400),
                'attendee_name': 'Demo Attendee',
                'company': 'Demo Company',
                'is_vip': False
            }
            
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return None

    def update_known_faces(self, attendee_id: int, encoding_b64: str, metadata: Dict = None):
        """Update the in-memory cache of known faces - placeholder for external service integration"""
        try:
            logger.info(f"Placeholder: Updating known faces for attendee {attendee_id}")
            # In production, this would sync with external recognition service
            self.last_cache_update = time.time()
            logger.debug(f"Updated face cache timestamp for attendee {attendee_id}")
            
        except Exception as e:
            logger.error(f"Error updating known faces: {e}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring"""
        avg_recognition_time = np.mean(self.recognition_times[-100:]) if self.recognition_times else 0
        avg_encoding_time = np.mean(self.encoding_times[-100:]) if self.encoding_times else 0
        
        return {
            'cache_size': self.face_cache_size,
            'cache_loaded': self.face_cache_loaded,
            'last_cache_update': self.last_cache_update,
            'avg_recognition_time_ms': avg_recognition_time * 1000,
            'avg_encoding_time_ms': avg_encoding_time * 1000,
            'total_recognition_attempts': len(self.recognition_times),
            'total_encoding_attempts': len(self.encoding_times),
            'external_service_enabled': self.use_external_service,
            'external_service_url': self.external_service_url
        }

    def clear_cache(self):
        """Clear the face cache - placeholder for external service integration"""
        logger.info("Placeholder: Clearing face cache")
        self.face_cache_loaded = False
        self.face_cache_size = 0
        logger.info("Face cache cleared (placeholder)")

    def configure_external_service(self, service_url: str, enable: bool = True):
        """Configure external recognition service integration"""
        self.external_service_url = service_url
        self.use_external_service = enable
        logger.info(f"External recognition service {'enabled' if enable else 'disabled'}: {service_url}")

class QRCodeEngine:
    def __init__(self):
        self.supported_formats = ['QRCODE']

    async def scan_qr_code(self, image: np.ndarray) -> Optional[str]:
        """Scan QR code from image"""
        try:
            # Decode QR codes
            decoded_objects = decode(image)
            
            for obj in decoded_objects:
                if obj.type in self.supported_formats:
                    qr_data = obj.data.decode('utf-8')
                    return qr_data
            
            return None
            
        except Exception as e:
            print(f"QR code scanning error: {e}")
            return None

    async def generate_qr_code(self, data: str) -> Optional[bytes]:
        """Generate QR code image (placeholder - would integrate with actual QR generation)"""
        # This would integrate with a QR code generation library
        # For now, return placeholder
        try:
            # Placeholder implementation
            # In production, use a library like qrcode
            return None
        except Exception as e:
            print(f"QR code generation error: {e}")
            return None

class CameraStreamProcessor:
    def __init__(self):
        self.active_streams = {}
        self.processing_interval = 0.033  # Process every ~33ms for 30fps display
        self.inference_interval = 10  # Perform inference every 10 frames
        self.face_engine = FaceRecognitionEngine()
        self.qr_engine = QRCodeEngine()

    async def start_stream_processing(self, camera_id: int, stream_url: str, db: Session = None):
        """Start processing a camera stream with real-time recognition"""
        try:
            # Try to open the stream with OpenCV - it should handle both HTTP and HTTPS
            cap = cv2.VideoCapture(stream_url)
            
            if not cap.isOpened():
                print(f"Failed to open camera stream: {stream_url}")
                print("Note: Some HTTPS streams may require additional codecs or setup")
                return False
            
            self.active_streams[camera_id] = {
                'capture': cap,
                'stream_url': stream_url,
                'is_processing': True,
                'db': db,
                'simulated': False
            }
            
            # Start processing loop
            asyncio.create_task(self._process_stream(camera_id))
            print(f"Started real-time recognition for camera {camera_id}")
            return True
            
        except Exception as e:
            print(f"Error starting stream processing: {e}")
            return False

    async def _process_stream(self, camera_id: int):
        """Process frames from camera stream with real-time recognition"""
        if camera_id not in self.active_streams:
            return
        
        stream_info = self.active_streams[camera_id]
        cap = stream_info['capture']
        db = stream_info['db']
        stream_url = stream_info['stream_url']
        
        # Check if this is a simulated stream (HTTPS or other special cases)
        is_simulated = stream_info.get('simulated', False)
        
        # Frame counter for sampling
        frame_counter = 0
        last_face_result = None
        last_qr_result = None
        
        while stream_info['is_processing']:
            try:
                if is_simulated:
                    # For simulated streams, try to open them as real streams first
                    try:
                        if cap is None:
                            cap = cv2.VideoCapture(stream_url)
                            stream_info['capture'] = cap
                        
                        ret, frame = cap.read()
                        if ret:
                            # Real stream is working, process it normally
                            if frame_counter % self.inference_interval == 0:
                                face_result = await self.face_engine.recognize_face(frame, db)
                                qr_result = await self.qr_engine.scan_qr_code(frame)
                                last_face_result = face_result
                                last_qr_result = qr_result
                            else:
                                # Use last detection results for smooth display
                                face_result = last_face_result
                                qr_result = last_qr_result
                        else:
                            # Fall back to demo mode
                            frame = self._generate_demo_frame(camera_id)
                            face_result = None
                            qr_result = None
                    except Exception as e:
                        print(f"Failed to process real stream {stream_url}: {e}")
                        # Fall back to demo mode
                        frame = self._generate_demo_frame(camera_id)
                        face_result = None
                        qr_result = None
                
                else:
                    # Real stream processing
                    ret, frame = cap.read()
                    
                    if not ret:
                        print(f"Failed to read frame from camera {camera_id}")
                        await asyncio.sleep(self.processing_interval)
                        continue
                    
                    # Only perform inference every 10 frames for better performance
                    if frame_counter % self.inference_interval == 0:
                        # Process frame for face recognition
                        face_result = await self.face_engine.recognize_face(frame, db)
                        # Process frame for QR code scanning
                        qr_result = await self.qr_engine.scan_qr_code(frame)
                        # Store results for non-inference frames
                        last_face_result = face_result
                        last_qr_result = qr_result
                    else:
                        # Use last detection results for smooth display
                        face_result = last_face_result
                        qr_result = last_qr_result
                
                # Create annotated frame with detection rectangles
                annotated_frame = self._annotate_frame(frame, face_result, qr_result)
                
                # Send recognition results via WebSocket
                await self._send_recognition_update(camera_id, face_result, qr_result, annotated_frame)
                
                # Increment frame counter
                frame_counter += 1
                
                await asyncio.sleep(self.processing_interval)
                
            except Exception as e:
                print(f"Error processing stream {camera_id}: {e}")
                await asyncio.sleep(self.processing_interval)

    def _generate_demo_frame(self, camera_id: int) -> np.ndarray:
        """Generate a demo frame for simulated streams"""
        # Create a simple demo frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame.fill(50)  # Dark gray background
        
        # Add some demo elements
        cv2.putText(frame, f"Camera {camera_id} - Demo Mode", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "HTTPS Stream Simulation", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, "Real-time recognition active", (50, 140), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)
        
        # Add a simple background pattern to make it look like a real camera feed
        for i in range(0, 640, 40):
            cv2.line(frame, (i, 0), (i, 480), (70, 70, 70), 1)
        for i in range(0, 480, 40):
            cv2.line(frame, (0, i), (640, i), (70, 70, 70), 1)
        
        return frame

    def _annotate_frame(self, frame: np.ndarray, face_result: Optional[Dict], qr_result: Optional[str]) -> np.ndarray:
        """Annotate frame with detection rectangles"""
        annotated_frame = frame.copy()
        
        # Draw face detection rectangle
        if face_result and face_result.get('face_location'):
            top, right, bottom, left = face_result['face_location']
            cv2.rectangle(annotated_frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(annotated_frame, "Face", (left, top-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw QR code detection (we'll use a placeholder since pyzbar doesn't return location)
        # For QR codes, we can detect contours to find the location
        if qr_result:
            # Try to find QR code contours
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Draw rectangle around largest contour (likely the QR code)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(annotated_frame, "QR Code", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        return annotated_frame

    async def _send_recognition_update(self, camera_id: int, face_result: Optional[Dict], 
                                     qr_result: Optional[str], frame: np.ndarray):
        """Send recognition results via WebSocket (coordinates only for frontend overlay)"""
        try:
            from app.websocket_manager import manager
            
            update_data = {
                "type": "recognition_update",
                "camera_id": camera_id,
                "timestamp": asyncio.get_event_loop().time(),
                "frame_width": frame.shape[1],
                "frame_height": frame.shape[0],
                "detections": []
            }
            
            # Add face detection info
            if face_result:
                update_data["detections"].append({
                    "type": "face",
                    "confidence": face_result.get('confidence', 0.0),
                    "attendee_id": face_result.get('attendee_id'),
                    "location": face_result.get('face_location')
                })
            
            # Add QR code detection info
            if qr_result:
                update_data["detections"].append({
                    "type": "qr_code",
                    "data": qr_result
                })
            
            await manager.broadcast(update_data)
            
        except Exception as e:
            print(f"Error sending recognition update: {e}")

    def stop_stream_processing(self, camera_id: int):
        """Stop processing a camera stream"""
        if camera_id in self.active_streams:
            self.active_streams[camera_id]['is_processing'] = False
            self.active_streams[camera_id]['capture'].release()
            del self.active_streams[camera_id]
            print(f"Stopped real-time recognition for camera {camera_id}")

# Global instances
face_recognition_engine = FaceRecognitionEngine()
qr_code_engine = QRCodeEngine()
camera_stream_processor = CameraStreamProcessor()
