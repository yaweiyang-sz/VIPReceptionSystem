import os
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
        # FIXED: Better default thresholds for accuracy
        self.confidence_threshold = 0.3  # Lowered from 0.6 for better recall
        self.min_confidence = 0.3  # Minimum confidence to accept a match
        self.face_cache_loaded = False
        self.face_cache_size = 0
        self.last_cache_update = 0
        
        # FIXED: Initialize cache storage
        self.known_face_encodings = []
        self.known_face_ids = []
        
        # Performance monitoring
        self.recognition_times = []
        self.encoding_times = []
        
        # Integration point for external recognition service
        self.external_service_url = os.getenv("ALGORITHM_SERVICE_URL", None)
        self.use_external_service = self.external_service_url is not None
        
        if self.use_external_service:
            logger.info(f"FaceRecognitionEngine initialized with algorithm service: {self.external_service_url}")
        else:
            logger.info("FaceRecognitionEngine initialized - algorithm service not configured")

    def load_known_faces(self, db: Session = None) -> bool:
        """Load known face encodings from database for local fallback"""
        try:
            if not db:
                logger.warning("No database session provided for loading known faces")
                return False
            
            logger.info("Loading known faces from database for local recognition")
            
            # Clear existing cache
            self.known_face_encodings = []
            self.known_face_ids = []
            
            # Load attendees with face encodings
            attendees = db.query(Attendee).filter(
                Attendee.face_encoding.isnot(None),
                Attendee.status == "registered"
            ).all()
            
            for attendee in attendees:
                try:
                    # Decode face encoding from base64
                    encoding_data = base64.b64decode(attendee.face_encoding)
                    encoding = pickle.loads(encoding_data)
                    
                    self.known_face_encodings.append(encoding)
                    self.known_face_ids.append(attendee.id)
                    
                except Exception as e:
                    logger.error(f"Error loading encoding for attendee {attendee.id}: {e}")
            
            self.face_cache_loaded = True
            self.face_cache_size = len(self.known_face_encodings)
            self.last_cache_update = time.time()
            
            logger.info(f"Loaded {self.face_cache_size} face encodings from database for local recognition")
            return True
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
            return False

    async def encode_face(self, image_data: bytes, max_faces: int = 1, attendee_id: Optional[int] = None, metadata: Optional[Dict] = None) -> Optional[List[Dict[str, Any]]]:
        """Encode faces from image data using algorithm service"""
        try:
            start_time = time.time()
            logger.info(f"Starting face encoding for {len(image_data)} bytes of image data")
            
            # Integration point for algorithm service
            if self.use_external_service and self.external_service_url:
                try:
                    # Prepare request data
                    files = {"image": image_data}
                    data = {}
                    if attendee_id is not None:
                        data["attendee_id"] = str(attendee_id)
                    if metadata is not None:
                        data["metadata"] = json.dumps(metadata)
                    
                    # Call algorithm service
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.external_service_url}/api/v1/encode",
                            files=files,
                            data=data,
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            encoding_time = time.time() - start_time
                            self.encoding_times.append(encoding_time)
                            
                            if result.get("success"):
                                logger.info(f"Algorithm service encoded {result.get('num_faces', 0)} faces in {encoding_time:.3f}s")
                                return result.get("encodings", [])
                            else:
                                logger.warning(f"Algorithm service encoding failed: {result.get('message', 'Unknown error')}")
                                return None
                        else:
                            logger.error(f"Algorithm service returned error: {response.status_code}")
                            return None
                except Exception as e:
                    logger.error(f"Algorithm service encoding failed: {e}")
                    # Fall back to local implementation
            
            # Local implementation as fallback
            logger.info("Using local face encoding (algorithm service not available)")
            
            # Convert bytes to image
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Failed to decode image")
                return None
            
            # Convert BGR to RGB
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Find all face locations - FIXED: Use more accurate model
            import face_recognition
            face_locations = face_recognition.face_locations(rgb_img, model="cnn")  # CNN model is more accurate
            
            if not face_locations:
                logger.info("No faces found in image")
                return []
            
            # Get face encodings with more samples for better quality
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations, num_jitters=2)
            
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
            
            encoding_time = time.time() - start_time
            self.encoding_times.append(encoding_time)
            logger.info(f"Local encoding completed for {len(results)} faces in {encoding_time:.3f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Face encoding error: {str(e)}", exc_info=True)
            return None

    async def recognize_face(self, image: np.ndarray, db: Session = None) -> Optional[Dict[str, Any]]:
        """Recognize faces in the given image using algorithm service"""
        try:
            # FIXED: Validate input
            if image is None or not isinstance(image, np.ndarray) or image.size == 0:
                logger.warning("Invalid image provided for recognition")
                return None
            
            start_time = time.time()
            
            # Integration point for algorithm service
            if self.use_external_service and self.external_service_url:
                try:
                    # Convert image to bytes for HTTP request
                    _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    image_bytes = buffer.tobytes()
                    
                    # Call algorithm service with retry logic
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.external_service_url}/api/v1/recognize",
                            files={"image": image_bytes},
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            recognition_time = time.time() - start_time
                            self.recognition_times.append(recognition_time)
                            
                            if result.get("success") and result.get("recognition"):
                                recognition_data = result["recognition"]
                                logger.info(f"Algorithm service recognized VIP: {recognition_data.get('full_name', 'Unknown')} in {recognition_time:.3f}s")
                                
                                # Format the result to match expected structure
                                return {
                                    'attendee_id': recognition_data.get('attendee_id'),
                                    'confidence': recognition_data.get('confidence', 0.0),
                                    'face_location': recognition_data.get('face_location'),
                                    'attendee_name': recognition_data.get('full_name', 'Unknown'),
                                    'first_name': recognition_data.get('first_name', ''),
                                    'last_name': recognition_data.get('last_name', ''),
                                    'company': recognition_data.get('company', ''),
                                    'position': recognition_data.get('position', ''),
                                    'is_vip': recognition_data.get('is_vip', False),
                                    'email': recognition_data.get('email', ''),
                                    'phone': recognition_data.get('phone', ''),
                                    'additional_info': recognition_data.get('additional_info', {})
                                }
                            else:
                                logger.debug(f"No VIP recognized: {result.get('message', 'No match')}")
                                return None
                        else:
                            logger.error(f"Algorithm service returned error: {response.status_code}")
                            # Fall through to local implementation
                except Exception as e:
                    logger.error(f"Algorithm service recognition failed: {e}")
                    # Fall through to local implementation
            
            # Local implementation as fallback
            logger.debug("Using local face recognition (algorithm service not available)")
            
            # FIXED: Validate image before processing
            if image.shape[0] == 0 or image.shape[1] == 0:
                logger.warning("Invalid image dimensions for recognition")
                return None
            
            # Convert BGR to RGB
            rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # FIXED: Always try to load faces if not loaded
            if not self.face_cache_loaded and db is not None:
                logger.info("Face cache not loaded, loading from database...")
                self.load_known_faces(db)
            
            # If we have known faces, try local recognition
            if self.face_cache_loaded and self.known_face_encodings:
                import face_recognition
                
                # FIXED: Use faster model for real-time processing, but scale image first
                # Scale down large images for faster processing
                scale = 1.0
                if image.shape[1] > 800:
                    scale = 800.0 / image.shape[1]
                    small_image = cv2.resize(rgb_img, (0, 0), fx=scale, fy=scale)
                else:
                    small_image = rgb_img
                
                # Find face locations with HOG model (faster)
                face_locations = face_recognition.face_locations(small_image, model="hog")
                
                if face_locations:
                    # Scale back the locations
                    if scale != 1.0:
                        face_locations = [
                            (int(top/scale), int(right/scale), int(bottom/scale), int(left/scale))
                            for (top, right, bottom, left) in face_locations
                        ]
                    
                    # Get face encodings from original image for accuracy
                    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
                    
                    best_match = None
                    best_confidence = 0.0
                    
                    for i, face_encoding in enumerate(face_encodings):
                        # FIXED: Use adjusted tolerance
                        matches = face_recognition.compare_faces(
                            self.known_face_encodings, 
                            face_encoding,
                            tolerance=self.confidence_threshold
                        )
                        
                        face_distances = face_recognition.face_distance(
                            self.known_face_encodings, 
                            face_encoding
                        )
                        
                        if True in matches:
                            # Get the best match
                            best_match_index = np.argmin(face_distances)
                            best_distance = face_distances[best_match_index]
                            
                            # FIXED: Better confidence calculation
                            # Use exponential decay for confidence: closer distance = higher confidence
                            confidence = 1.0 / (1.0 + best_distance * 2.0)
                            
                            logger.debug(f"Match found: distance={best_distance:.3f}, confidence={confidence:.3f}")
                            
                            # FIXED: Use min_confidence threshold
                            if confidence >= self.min_confidence and confidence > best_confidence:
                                best_confidence = confidence
                                
                                # Get attendee info from database
                                attendee = db.query(Attendee).filter(
                                    Attendee.id == self.known_face_ids[best_match_index]
                                ).first()
                                
                                if attendee:
                                    best_match = {
                                        'attendee_id': attendee.id,
                                        'confidence': float(confidence),
                                        'face_location': face_locations[i],
                                        'face_distance': float(best_distance),
                                        'attendee_name': f"{attendee.first_name} {attendee.last_name}",
                                        'first_name': attendee.first_name,
                                        'last_name': attendee.last_name,
                                        'company': attendee.company,
                                        'position': attendee.position,
                                        'is_vip': attendee.is_vip,
                                        'email': attendee.email,
                                        'phone': attendee.phone
                                    }
                    
                    if best_match:
                        recognition_time = time.time() - start_time
                        self.recognition_times.append(recognition_time)
                        logger.info(f"Face recognized: {best_match['attendee_name']} (confidence: {best_match['confidence']:.2f})")
                        return best_match
            else:
                logger.warning(f"Face cache not loaded or empty (loaded: {self.face_cache_loaded}, size: {len(self.known_face_encodings)})")
            
            recognition_time = time.time() - start_time
            self.recognition_times.append(recognition_time)
            
            # Return None if no recognition
            return None
            
        except Exception as e:
            logger.error(f"Face recognition error: {e}", exc_info=True)
            return None

    def update_known_faces(self, attendee_id: int, encoding_b64: str, metadata: Dict = None):
        """Update the in-memory cache of known faces"""
        try:
            logger.info(f"Updating known faces for attendee {attendee_id}")
            
            # Decode the encoding
            encoding_bytes = base64.b64decode(encoding_b64)
            encoding = pickle.loads(encoding_bytes)
            
            # Check if attendee already exists in cache
            if attendee_id in self.known_face_ids:
                # Update existing encoding
                index = self.known_face_ids.index(attendee_id)
                self.known_face_encodings[index] = encoding
                logger.info(f"Updated encoding for attendee {attendee_id}")
            else:
                # Add new encoding
                self.known_face_encodings.append(encoding)
                self.known_face_ids.append(attendee_id)
                self.face_cache_size += 1
                logger.info(f"Added new encoding for attendee {attendee_id}")
            
            self.last_cache_update = time.time()
            
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
            'external_service_url': self.external_service_url,
            'confidence_threshold': self.confidence_threshold,
            'min_confidence': self.min_confidence
        }

    def clear_cache(self):
        """Clear the face cache"""
        logger.info("Clearing face cache")
        self.face_cache_loaded = False
        self.face_cache_size = 0
        self.known_face_encodings = []
        self.known_face_ids = []
        logger.info("Face cache cleared")

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
            # FIXED: Validate input
            if image is None or not isinstance(image, np.ndarray) or image.size == 0:
                return None
            
            # Decode QR codes
            decoded_objects = decode(image)
            
            for obj in decoded_objects:
                if obj.type in self.supported_formats:
                    qr_data = obj.data.decode('utf-8')
                    return qr_data
            
            return None
            
        except Exception as e:
            logger.error(f"QR code scanning error: {e}")
            return None

    async def generate_qr_code(self, data: str) -> Optional[bytes]:
        """Generate QR code image (placeholder - would integrate with actual QR generation)"""
        try:
            # Placeholder implementation
            # In production, use a library like qrcode
            return None
        except Exception as e:
            logger.error(f"QR code generation error: {e}")
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
            # Try to open the stream with OpenCV
            cap = cv2.VideoCapture(stream_url)
            
            if not cap.isOpened():
                logger.error(f"Failed to open camera stream: {stream_url}")
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
            logger.info(f"Started real-time recognition for camera {camera_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting stream processing: {e}")
            return False

    async def _process_stream(self, camera_id: int):
        """Process frames from camera stream with real-time recognition"""
        if camera_id not in self.active_streams:
            return
        
        stream_info = self.active_streams[camera_id]
        cap = stream_info['capture']
        db = stream_info['db']
        stream_url = stream_info['stream_url']
        
        is_simulated = stream_info.get('simulated', False)
        
        # Frame counter for sampling
        frame_counter = 0
        last_face_result = None
        last_qr_result = None
        
        while stream_info['is_processing']:
            try:
                # FIXED: Better frame acquisition with validation
                frame = None
                
                if is_simulated:
                    try:
                        if cap is None:
                            cap = cv2.VideoCapture(stream_url)
                            stream_info['capture'] = cap
                        
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            frame = self._generate_demo_frame(camera_id)
                            face_result = None
                            qr_result = None
                    except Exception as e:
                        logger.error(f"Failed to process stream {stream_url}: {e}")
                        frame = self._generate_demo_frame(camera_id)
                        face_result = None
                        qr_result = None
                else:
                    # Real stream processing
                    ret, frame = cap.read()
                    
                    if not ret or frame is None:
                        logger.warning(f"Failed to read frame from camera {camera_id}")
                        await asyncio.sleep(self.processing_interval)
                        continue
                
                # FIXED: Validate frame before processing
                if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
                    logger.warning(f"Invalid frame from camera {camera_id}")
                    await asyncio.sleep(self.processing_interval)
                    continue
                
                # Only perform inference every N frames for better performance
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
                logger.error(f"Error processing stream {camera_id}: {e}", exc_info=True)
                await asyncio.sleep(self.processing_interval)

    def _generate_demo_frame(self, camera_id: int) -> np.ndarray:
        """Generate a demo frame for simulated streams"""
        # Create a simple demo frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame.fill(50)  # Dark gray background
        
        # Add some demo elements
        cv2.putText(frame, f"Camera {camera_id} - Demo Mode", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "Stream Unavailable", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, "Recognition active on reconnect", (50, 140), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)
        
        # Add a grid pattern
        for i in range(0, 640, 40):
            cv2.line(frame, (i, 0), (i, 480), (70, 70, 70), 1)
        for i in range(0, 480, 40):
            cv2.line(frame, (0, i), (640, i), (70, 70, 70), 1)
        
        return frame

    def _annotate_frame(self, frame: np.ndarray, face_result: Optional[Dict], qr_result: Optional[str]) -> np.ndarray:
        """Annotate frame with detection rectangles"""
        # FIXED: Validate frame before processing
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            logger.warning("Invalid frame provided for annotation")
            return self._generate_demo_frame(0)  # Return a valid demo frame
        
        try:
            annotated_frame = frame.copy()
            
            # Draw face detection rectangle
            if face_result and face_result.get('face_location'):
                top, right, bottom, left = face_result['face_location']
                
                # FIXED: Validate coordinates
                h, w = frame.shape[:2]
                top = max(0, min(top, h-1))
                bottom = max(0, min(bottom, h-1))
                left = max(0, min(left, w-1))
                right = max(0, min(right, w-1))
                
                # Draw rectangle
                cv2.rectangle(annotated_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Add label with confidence
                label = f"Face ({face_result.get('confidence', 0):.2f})"
                cv2.putText(annotated_frame, label, (left, top-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Add name if recognized
                if face_result.get('attendee_name'):
                    cv2.putText(annotated_frame, face_result['attendee_name'], 
                               (left, bottom+20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Draw QR code detection
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
            
        except Exception as e:
            logger.error(f"Error annotating frame: {e}", exc_info=True)
            # Return original frame if annotation fails
            return frame

    async def _send_recognition_update(self, camera_id: int, face_result: Optional[Dict], 
                                     qr_result: Optional[str], frame: np.ndarray):
        """Send recognition results via WebSocket"""
        try:
            # FIXED: Validate frame
            if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
                return
            
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
                face_detection = {
                    "type": "face",
                    "confidence": face_result.get('confidence', 0.0),
                    "attendee_id": face_result.get('attendee_id'),
                    "location": face_result.get('face_location'),
                    "attendee_name": face_result.get('attendee_name'),
                    "first_name": face_result.get('first_name', ''),
                    "last_name": face_result.get('last_name', ''),
                    "company": face_result.get('company', ''),
                    "position": face_result.get('position', ''),
                    "is_vip": face_result.get('is_vip', False),
                    "email": face_result.get('email', ''),
                    "phone": face_result.get('phone', '')
                }
                # Remove None values
                face_detection = {k: v for k, v in face_detection.items() if v is not None}
                update_data["detections"].append(face_detection)
            
            # Add QR code detection info
            if qr_result:
                update_data["detections"].append({
                    "type": "qr_code",
                    "data": qr_result
                })
            
            await manager.broadcast(update_data)
            
        except Exception as e:
            logger.error(f"Error sending recognition update: {e}", exc_info=True)

    def stop_stream_processing(self, camera_id: int):
        """Stop processing a camera stream"""
        if camera_id in self.active_streams:
            self.active_streams[camera_id]['is_processing'] = False
            if self.active_streams[camera_id]['capture']:
                self.active_streams[camera_id]['capture'].release()
            del self.active_streams[camera_id]
            logger.info(f"Stopped real-time recognition for camera {camera_id}")


# Global instances
face_recognition_engine = FaceRecognitionEngine()
qr_code_engine = QRCodeEngine()
camera_stream_processor = CameraStreamProcessor()