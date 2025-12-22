# VIP Reception System - UML Sequence Diagrams

## Key Business Use Cases

### Use Case 1: Attendee Registration with Face Photo Upload

**Description**: Register a new attendee and upload their face photo for recognition encoding using placeholder engine with external service integration capability.

**Actors**: Admin User, System

**Preconditions**: 
- Admin is logged into the system
- Face recognition engine is initialized (placeholder mode)

**Postconditions**:
- Attendee is registered in the database with QR code
- Photo is saved to `/app/data/faces/{attendee_id}.jpg`
- Face encoding is attempted (placeholder/dummy encoding for development)
- Face cache is updated for external service integration

```mermaid
sequenceDiagram
    participant Admin as Admin User
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant FaceEngine as FaceRecognitionEngine (Placeholder)
    participant DB as Database
    participant FileSystem as File System

    Admin->>Frontend: Fill attendee form
    Frontend->>Backend: POST /api/attendees/
    Backend->>DB: Check email uniqueness
    Backend->>Backend: Generate UUID QR code
    Backend->>DB: Create attendee record
    DB-->>Backend: Attendee created (ID=123)
    Backend-->>Frontend: Attendee created response
    
    Admin->>Frontend: Upload face photo
    Frontend->>Backend: POST /api/attendees/123/upload-photo
    Backend->>FileSystem: Save photo to /app/data/faces/123.jpg
    Backend->>FaceEngine: encode_face(photo_data)
    
    Note over FaceEngine: Placeholder implementation with external service integration
    alt External service configured
        FaceEngine->>ExternalService: HTTP POST /encode
        ExternalService-->>FaceEngine: Face encoding result
    else Development/placeholder mode
        FaceEngine->>FaceEngine: Simulate encoding (0.1s delay)
        FaceEngine-->>Backend: Dummy encoding result
    end
    
    alt Face detected successfully
        Backend->>DB: Update attendee.face_encoding
        Backend->>DB: Update attendee.photo_url
        Backend->>FaceEngine: update_known_faces(attendee_id, encoding, metadata)
        Backend-->>Frontend: Success with face detection details
    else No face detected or error
        Backend->>DB: Update attendee.photo_url only
        Backend-->>Frontend: Warning with detection details
    end
    
    Frontend->>Frontend: Update UI with photo preview
    Frontend->>Frontend: Show face encoding status
```

### Use Case 2: Real-time Camera Streaming with WebSocket

**Description**: Stream live camera video via WebSocket with adaptive source handling (test patterns, webcam, RTSP, HTTP) and frame rate control.

**Actors**: Frontend User, Camera System, System

**Preconditions**:
- Camera is configured in database with source URL
- Backend WebSocket server is running
- Frontend can connect to backend WebSocket

**Postconditions**:
- WebSocket connection established with stream info
- Live video frames streamed at target FPS (default 15fps)
- Adaptive JPEG quality based on frame size
- Test mode fallback if real stream fails

```mermaid
sequenceDiagram
    participant User as Frontend User
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant WS as WebSocket Endpoint (/api/cameras/{id}/ws/stream)
    participant OpenCV as OpenCV VideoCapture
    participant DB as Database

    User->>Frontend: Select camera to view
    Frontend->>Backend: GET /api/cameras/{id}/stream
    Backend->>DB: Query camera configuration
    DB-->>Backend: Camera source, FPS, resolution
    Backend-->>Frontend: Stream info with WebSocket URL
    
    Frontend->>WS: Connect to WebSocket
    WS->>DB: Get camera details (new session)
    DB-->>WS: Camera source and settings
    
    Note over WS: Adaptive source handling
    alt Source is "0" or "test"
        WS->>OpenCV: Open webcam (source=0)
    else Source starts with "test://"
        WS->>WS: Enable test mode with pattern
    else Source starts with "rtsp://"
        WS->>OpenCV: Open RTSP with TCP transport
    else Other source (HTTP, file, etc.)
        WS->>OpenCV: Open video source
    end
    
    alt Stream opened successfully
        WS-->>Frontend: {"type": "connected", "camera_name": "...", "test_mode": false}
    else Stream failed to open
        WS->>WS: Fallback to test mode
        WS-->>Frontend: {"type": "connected", "test_mode": true}
    end
    
    WS-->>Frontend: {"type": "stream_info", "width": 640, "height": 480, "fps": 15, "format": "jpeg"}
    
    Note over WS,Frontend: Real-time video streaming with frame rate control
    loop Every frame (target FPS)
        alt Test mode active
            WS->>WS: generate_test_frame(frame_count, pattern)
        else Real stream
            WS->>OpenCV: Read frame
            OpenCV-->>WS: Frame data
        end
        
        WS->>WS: Resize frame (maintain aspect ratio, max 640px)
        WS->>WS: Encode as JPEG with adaptive quality
        WS->>WS: Convert to base64
        
        WS->>Frontend: {"type": "frame", "camera_id": id, "frame_id": N, "data": "base64...", "width": W, "height": H, "test_mode": bool}
        Frontend->>Frontend: Decode base64 and render on canvas
        
        Note over WS: Frame timing control
        WS->>WS: Calculate processing time
        WS->>WS: Sleep for (1/fps - processing_time)
    end
    
    Note over WS,Frontend: WebSocket keep-alive
    loop Periodically
        Frontend->>WS: {"type": "ping"}
        WS-->>Frontend: {"type": "pong", "timestamp": ...}
    end
    
    User->>Frontend: Close camera view
    Frontend->>WS: Close WebSocket connection
    alt Real stream was active
        WS->>OpenCV: Release capture
    end
    WS->>DB: Close database session
```

### Use Case 3: QR Code Check-in Process

**Description**: Attendee checks in using QR code via API endpoint or real-time camera stream processing.

**Actors**: Attendee, Camera System, System

**Preconditions**:
- Attendee has valid QR code (UUID generated during registration)
- Camera is active and streaming (for real-time) OR image can be captured
- QR code scanning is enabled via pyzbar library

**Postconditions**:
- Attendee is checked in via QR code
- Visit record is created with method "qr_code"
- Attendee status updated to "checked_in"
- Real-time WebSocket notification sent to frontend

```mermaid
sequenceDiagram
    participant Attendee as Attendee
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant QREngine as QRCodeEngine (pyzbar)
    participant DB as Database
    participant WS as WebSocket Manager

    alt Method A: Direct API call with captured image
        Attendee->>Frontend: Show QR code to camera (capture)
        Frontend->>Frontend: Capture image as base64
        Frontend->>Backend: POST /api/recognition/qr
        Backend->>Backend: Decode base64 to image bytes
        Backend->>QREngine: scan_qr_code(image)
        QREngine->>QREngine: Detect QR code with pyzbar.decode()
        QREngine-->>Backend: QR data (UUID string)
        
    else Method B: Real-time stream processing
        Attendee->>Camera: Show QR code to live camera
        Camera->>CameraStreamProcessor: Stream frames
        CameraStreamProcessor->>QREngine: scan_qr_code(frame)
        QREngine->>QREngine: Detect QR code with pyzbar.decode()
        QREngine-->>CameraStreamProcessor: QR data (UUID string)
        CameraStreamProcessor->>Backend: Process QR recognition
    end
    
    alt Valid QR code decoded (UUID matches attendee)
        Backend->>DB: Query attendee by qr_code
        DB-->>Backend: Attendee record
        Backend->>DB: Create visit record (method: qr_code)
        Backend->>DB: Update attendee.status = "checked_in"
        DB-->>Backend: Records updated
        
        Backend->>WS: Broadcast attendee_recognized
        WS->>Frontend: {"type": "attendee_recognized", "recognition_method": "qr_code", ...}
        Frontend->>Frontend: Display check-in notification
        Frontend->>Frontend: Update attendee list
        
        Backend-->>Frontend: Success response with attendee details
    else Invalid or no QR code
        Backend-->>Frontend: Error: "Invalid or unrecognized QR code"
    end
```

### Use Case 4: Dual Recognition Fallback Process

**Description**: System attempts both face recognition and QR code scanning sequentially via /api/recognition/auto endpoint, using the first successful method.

**Actors**: Attendee, Camera System, System

**Preconditions**:
- Image can be captured (base64 encoded)
- Both recognition methods are available
- Attendee may have face encoding and/or QR code

**Postconditions**:
- Attendee is recognized by either method (face first, then QR)
- Visit record is created with successful method
- Attendee status updated to "checked_in"
- Real-time WebSocket notification sent

```mermaid
sequenceDiagram
    participant Attendee as Attendee
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant FaceEngine as FaceRecognitionEngine
    participant QREngine as QRCodeEngine
    participant DB as Database
    participant WS as WebSocket Manager

    Attendee->>Frontend: Show face/QR code to camera
    Frontend->>Frontend: Capture image as base64
    Frontend->>Backend: POST /api/recognition/auto
    
    Note over Backend: Sequential recognition attempts (face first, then QR)
    
    Backend->>Backend: Decode base64 to image
    Backend->>FaceEngine: recognize_face(image)
    
    alt Face recognition successful
        FaceEngine-->>Backend: Recognition result with attendee_id
        Backend->>DB: Query attendee by ID
        DB-->>Backend: Attendee record
        Backend->>DB: Create visit (method: face)
        Backend->>DB: Update attendee.status = "checked_in"
        DB-->>Backend: Records updated
        
        Backend->>WS: Broadcast attendee_recognized (method: face)
        WS->>Frontend: Real-time notification
        Backend-->>Frontend: Success response with face recognition details
        
    else Face recognition failed
        Backend->>QREngine: scan_qr_code(image)
        
        alt QR code recognition successful
            QREngine-->>Backend: QR data (UUID)
            Backend->>DB: Query attendee by qr_code
            DB-->>Backend: Attendee record
            Backend->>DB: Create visit (method: qr_code)
            Backend->>DB: Update attendee.status = "checked_in"
            DB-->>Backend: Records updated
            
            Backend->>WS: Broadcast attendee_recognized (method: qr_code)
            WS->>Frontend: Real-time notification
            Backend-->>Frontend: Success response with QR recognition details
            
        else Both methods failed
            Backend-->>Frontend: Error: "No matching attendee found"
        end
    end
    
    Frontend->>Frontend: Update UI based on recognition result
```

### Use Case 5: Camera Stream Management with WebSocket

**Description**: Admin configures and manages camera streams with WebSocket-based video streaming.

**Actors**: Admin User, System

**Preconditions**:
- Admin is logged into the system
- Camera is configured with source (test://, RTSP, HTTP, or webcam)

**Postconditions**:
- Camera configuration is saved to database
- WebSocket streaming endpoint is available
- Frontend can connect to stream camera video

```mermaid
sequenceDiagram
    participant Admin as Admin User
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant DB as Database
    participant WS as WebSocket Manager

    Admin->>Frontend: Open camera management
    Frontend->>Backend: GET /api/cameras/
    Backend->>DB: Query camera configurations
    DB-->>Backend: Camera list
    Backend-->>Frontend: Camera configurations
    
    Admin->>Frontend: Add/Edit camera
    Frontend->>Backend: POST/PUT /api/cameras/
    Backend->>DB: Save camera configuration
    DB-->>Backend: Camera saved
    Backend-->>Frontend: Camera saved successfully
    
    Note over Backend,WS: WebSocket endpoint automatically available at /api/cameras/{id}/ws/stream
    
    Admin->>Frontend: Test camera stream
    Frontend->>Backend: GET /api/cameras/{id}/stream
    Backend->>DB: Get camera details
    DB-->>Backend: Camera source and WebSocket URL
    Backend-->>Frontend: {"websocket_url": "/api/cameras/{id}/ws/stream", ...}
    
    Frontend->>WS: Connect to WebSocket stream
    WS->>WS: Initialize camera processor
    WS-->>Frontend: WebSocket connected
    WS->>Frontend: Send test frames (color bars or camera feed)
    Frontend->>Frontend: Display live video stream
    
    Admin->>Frontend: Update camera source
    Frontend->>Backend: PUT /api/cameras/{id}
    Backend->>DB: Update camera source
    DB-->>Backend: Camera updated
    Backend-->>Frontend: Camera updated
    
    Note over Frontend,WS: Existing WebSocket connections automatically use new source
    
    Admin->>Frontend: Delete camera (soft delete)
    Frontend->>Backend: DELETE /api/cameras/{id}
    Backend->>DB: Mark camera as inactive
    DB-->>Backend: Camera deactivated
    Backend-->>Frontend: Camera deleted
    Backend->>WS: Close active WebSocket connections for camera
```

### Use Case 6: System Performance Monitoring

**Description**: System administrator monitors recognition performance and system health.

**Actors**: Admin User, System

**Preconditions**:
- Admin is logged into admin dashboard
- System is operational with active cameras

**Postconditions**:
- Performance statistics are displayed
- System health status is updated
- Alerts are generated for issues

```mermaid
sequenceDiagram
    participant Admin as Admin User
    participant Frontend as Admin Dashboard
    participant Backend as Backend API
    participant FaceEngine as FaceRecognitionEngine
    participant Processor as CameraStreamProcessor
    participant DB as Database
    participant WS as WebSocket Manager

    Admin->>Frontend: Open performance dashboard
    Frontend->>Backend: GET /api/admin/performance
    Backend->>FaceEngine: get_performance_stats()
    FaceEngine-->>Backend: Recognition statistics
    Backend->>Processor: get_stream_status()
    Processor-->>Backend: Camera stream status
    Backend->>DB: Query system metrics
    DB-->>Backend: Performance data
    Backend-->>Frontend: Comprehensive performance report
    
    Note over Processor,WS: Real-time monitoring
    Processor->>WS: Broadcast recognition metrics
    WS->>Frontend: Live performance updates
    Frontend->>Frontend: Update performance charts
    
    alt Performance threshold exceeded
        Frontend->>Frontend: Show performance alert
        Frontend->>Admin: Display warning notification
    end
    
    Admin->>Frontend: Request detailed logs
    Frontend->>Backend: GET /api/admin/logs
    Backend->>DB: Query system logs
    DB-->>Backend: Log entries
    Backend-->>Frontend: System logs
```

## Key System Interactions Summary

1. **Registration Flow**: Admin → Frontend → Backend → Database (with QR generation) → File System (photo storage) → Face Recognition Engine (placeholder with external service integration)
2. **Video Streaming Flow**: Frontend → Backend → WebSocket Endpoint → OpenCV VideoCapture → Adaptive Frame Processing → Frontend Canvas Rendering
3. **Recognition Flow**: 
   - **Face**: Frontend → Backend → FaceRecognitionEngine (placeholder) → Database (visit creation) → WebSocket Broadcast
   - **QR Code**: Frontend → Backend → QRCodeEngine (pyzbar) → Database (attendee lookup) → Visit Creation → WebSocket Broadcast
   - **Auto**: Sequential attempt of face then QR with fallback
4. **Camera Management Flow**: Admin → Frontend → Backend → Database (CRUD operations) → Automatic WebSocket endpoint generation
5. **Monitoring Flow**: Admin Dashboard → Backend API → System Components (FaceEngine, CameraStreamProcessor) → Database Metrics → Real-time WebSocket Updates

### Current Implementation Architecture:

#### **WebSocket Video Streaming**:
- **Endpoint**: `/api/cameras/{id}/ws/stream` with connection management via `ConnectionManager`
- **Frame Processing**: Adaptive JPEG encoding with quality based on frame size, target FPS control (default 15fps)
- **Source Handling**: Supports webcam (source=0), RTSP (with TCP transport), HTTP streams, and test patterns (`test://color_bars`, `test://default`)
- **Fallback Mechanism**: Automatic switch to test mode if real stream fails to open
- **Frame Timing**: Dynamic sleep calculation to maintain consistent frame rate

#### **Recognition Engine Architecture**:
- **FaceRecognitionEngine**: Placeholder implementation with external service integration hooks
  - `encode_face()`: Simulates encoding (0.1s delay) or calls external service if configured
  - `recognize_face()`: Returns dummy results for demo (attendee_id=1, confidence=0.85)
  - External service integration via HTTP POST to configured endpoint
- **QRCodeEngine**: Functional implementation using `pyzbar` library
  - `scan_qr_code()`: Detects and decodes QR codes from images
  - Supports UUID QR codes generated during attendee registration
- **CameraStreamProcessor**: Real-time processing with parallel face and QR recognition
  - Processes frames every 10 frames for performance
  - Annotates frames with detection rectangles
  - Sends recognition updates via WebSocket

#### **Database Integration**:
- **Attendee Management**: Full CRUD with email uniqueness validation, QR code generation (UUID)
- **Visit Tracking**: Automatic visit record creation on successful recognition
- **Status Management**: Attendee status updates ("checked_in", "checked_out")
- **Photo Storage**: Files saved to `/app/data/faces/{attendee_id}.jpg` with serving endpoint

#### **API Endpoints**:
- **Cameras**: `/api/cameras/` - CRUD operations, stream info, WebSocket streaming
- **Recognition**: `/api/recognition/face`, `/api/recognition/qr`, `/api/recognition/auto` - recognition endpoints
- **Attendees**: `/api/attendees/` - CRUD, photo upload, visit history, check-out
- **Admin**: `/api/admin/` - performance monitoring, system logs

These sequence diagrams accurately reflect the current implementation of the VIP Reception System, showing both the placeholder/demo components ready for external service integration and the fully functional components (QR code scanning, WebSocket streaming, database management).
