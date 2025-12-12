# VIP Reception System - UML Sequence Diagrams

## Key Business Use Cases

### Use Case 1: Attendee Registration with Face Photo Upload

**Description**: Register a new attendee and upload their face photo for recognition encoding.

**Actors**: Admin User, System

**Preconditions**: 
- Admin is logged into the system
- Camera system is operational

**Postconditions**:
- Attendee is registered in the database
- Face encoding is generated and stored
- Photo is saved for display

```mermaid
sequenceDiagram
    participant Admin as Admin User
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant FaceEngine as FaceRecognitionEngine
    participant DB as Database

    Admin->>Frontend: Fill attendee form
    Admin->>Frontend: Upload face photo
    Frontend->>Backend: POST /api/attendees/
    Backend->>DB: Create attendee record
    DB-->>Backend: Attendee created (ID=123)
    Backend-->>Frontend: Attendee created response
    
    Frontend->>Backend: POST /api/attendees/123/upload-photo
    Backend->>Backend: Save photo to file system
    Backend->>FaceEngine: encode_face(photo_data)
    FaceEngine->>FaceEngine: Detect faces in image
    FaceEngine->>FaceEngine: Generate face encoding
    FaceEngine-->>Backend: Face encoding result
    
    alt Face detected successfully
        Backend->>DB: Update attendee with face_encoding
        Backend->>FaceEngine: update_known_faces(attendee_id, encoding)
        Backend-->>Frontend: Success: Face encoded
    else No face detected
        Backend-->>Frontend: Warning: No face detected
    end
    
    Frontend->>Frontend: Update UI with photo preview
    Frontend->>Frontend: Show face encoding status
```

### Use Case 2: Real-time Camera Streaming with WebSocket

**Description**: Stream live camera video via WebSocket for real-time display with dummy recognition placeholder.

**Actors**: Frontend User, Camera System, System

**Preconditions**:
- Camera is configured in database
- Backend WebSocket server is running
- Frontend can connect to backend WebSocket

**Postconditions**:
- WebSocket connection established
- Live video frames streamed to frontend
- Dummy recognition results simulated for demonstration

```mermaid
sequenceDiagram
    participant User as Frontend User
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant WS as WebSocket Endpoint
    participant CameraProc as Camera Stream Processor
    participant DB as Database
    participant DummyEngine as Dummy Recognition Engine

    User->>Frontend: Select camera to view
    Frontend->>Backend: GET /api/cameras/{id}/stream
    Backend->>DB: Query camera configuration
    DB-->>Backend: Camera source and details
    Backend-->>Frontend: Stream info with WebSocket URL
    
    Frontend->>WS: Connect to WebSocket (ws://host:8000/api/cameras/{id}/ws/stream)
    WS->>CameraProc: Initialize camera stream
    CameraProc->>CameraProc: Open camera source (test://color_bars)
    CameraProc-->>WS: Stream ready
    WS-->>Frontend: WebSocket connected
    
    Note over WS,Frontend: Real-time video streaming via WebSocket
    loop Every frame (15fps)
        CameraProc->>CameraProc: Generate/capture frame
        CameraProc->>CameraProc: Encode frame as JPEG
        CameraProc->>WS: Send frame as base64 JSON
        WS->>Frontend: {"type": "frame", "data": "base64...", "frame_id": N}
        Frontend->>Frontend: Decode and render frame on canvas
    end
    
    Note over CameraProc,DummyEngine: Dummy recognition for demonstration
    CameraProc->>DummyEngine: simulate_recognition(frame)
    DummyEngine->>DummyEngine: Generate simulated detection
    DummyEngine-->>CameraProc: Simulated recognition result
    
    alt Simulated face detected
        CameraProc->>WS: Send dummy recognition update
        WS->>Frontend: {"type": "detection", "method": "face", "confidence": 0.85}
        Frontend->>Frontend: Display simulated detection overlay
    end
    
    User->>Frontend: Close camera view
    Frontend->>WS: Close WebSocket connection
    WS->>CameraProc: Stop camera stream
    CameraProc->>CameraProc: Release camera resources
```

### Use Case 3: QR Code Check-in Process

**Description**: Attendee checks in using QR code displayed on their mobile device or badge.

**Actors**: Attendee, Camera System, System

**Preconditions**:
- Attendee has valid QR code
- Camera is active and streaming
- QR code scanning is enabled

**Postconditions**:
- Attendee is checked in via QR code
- Visit record is created
- Real-time notification is sent

```mermaid
sequenceDiagram
    participant Attendee as Attendee
    participant Camera as Camera Stream
    participant Processor as CameraStreamProcessor
    participant QREngine as QRCodeEngine
    participant DB as Database
    participant WS as WebSocket Manager
    participant Frontend as Frontend Display

    Attendee->>Camera: Show QR code to camera
    Camera->>Processor: Stream video frames
    Processor->>Processor: Sample frame for QR detection
    Processor->>QREngine: scan_qr_code(frame)
    QREngine->>QREngine: Detect QR code in frame
    QREngine->>QREngine: Decode QR data
    QREngine-->>Processor: QR code data (attendee_id)
    
    alt Valid QR code decoded
        Processor->>DB: Verify attendee exists
        DB-->>Processor: Attendee data
        Processor->>DB: Create visit record
        DB-->>Processor: Visit created
        Processor->>WS: Broadcast QR check-in
        WS->>Frontend: Real-time check-in alert
        Frontend->>Frontend: Display attendee info
        Frontend->>Frontend: Highlight QR detection
    else Invalid or no QR code
        Processor->>WS: Broadcast QR scan failed
        WS->>Frontend: Show scan failed message
    end
    
    Processor->>Processor: Annotate frame with QR detection
    Processor-->>Camera: Continue processing
```

### Use Case 4: Dual Recognition Fallback Process

**Description**: System attempts both face recognition and QR code scanning, using the first successful method.

**Actors**: Attendee, Camera System, System

**Preconditions**:
- Camera is active and streaming
- Both recognition methods are enabled
- Attendee may have face encoding and/or QR code

**Postconditions**:
- Attendee is recognized by either method
- Visit record is created
- System logs which method was successful

```mermaid
sequenceDiagram
    participant Attendee as Attendee
    participant Camera as Camera Stream
    participant Processor as CameraStreamProcessor
    participant FaceEngine as FaceRecognitionEngine
    participant QREngine as QRCodeEngine
    participant DB as Database
    participant WS as WebSocket Manager

    Attendee->>Camera: Approach with face/QR code
    Camera->>Processor: Stream video frames
    
    Note over Processor: Parallel recognition attempts
    Processor->>FaceEngine: recognize_face(frame)
    Processor->>QREngine: scan_qr_code(frame)
    
    alt Face recognized first
        FaceEngine-->>Processor: Face recognition result
        Processor->>DB: Create visit (method: face)
        Processor->>WS: Broadcast face recognition
        Processor->>QREngine: Cancel QR processing
    else QR code recognized first
        QREngine-->>Processor: QR recognition result
        Processor->>DB: Create visit (method: qr)
        Processor->>WS: Broadcast QR recognition
        Processor->>FaceEngine: Cancel face processing
    else Both methods succeed
        Processor->>Processor: Use face recognition (higher priority)
        Processor->>DB: Create visit (method: face)
        Processor->>WS: Broadcast dual recognition
    else No recognition
        Processor->>WS: Broadcast no recognition
    end
    
    DB-->>Processor: Visit record created
    Processor->>Processor: Annotate frame with results
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

1. **Registration Flow**: Admin → Frontend → Backend → Database → Face Engine (Dummy)
2. **Video Streaming Flow**: Frontend → Backend → WebSocket → Camera Processor → Frame Generation → Frontend Display
3. **Camera Management Flow**: Admin → Frontend → Backend → Database → WebSocket Configuration
4. **Monitoring Flow**: Admin → Frontend → Backend → System Components → Real-time Updates

### Updated Architecture Highlights:

#### **WebSocket Video Streaming**:
- **Connection**: Frontend connects to `ws://host:8000/api/cameras/{id}/ws/stream`
- **Frame Transmission**: JPEG frames as base64 in JSON messages
- **Real-time Display**: Canvas-based rendering with smooth 30fps processing
- **LAN Access**: Dynamic host resolution for cross-device accessibility

#### **Dummy Recognition Implementation**:
- **Face Recognition**: Simulated results for demonstration
- **QR Code Scanning**: Placeholder for future integration
- **Interface Preservation**: Maintains API for easy external service integration

#### **Camera Source Support**:
- **Test Patterns**: `test://color_bars`, `test://default` for development
- **Real Cameras**: Webcam (source=0), RTSP, HTTP streams
- **Fallback**: Automatic switch to test mode on stream failure

These sequence diagrams illustrate the core business processes and system interactions that make the VIP Reception System functional and efficient for aviation exhibition management with WebSocket-based video streaming and ready-for-integration recognition architecture.
