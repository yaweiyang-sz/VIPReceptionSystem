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

### Use Case 2: Real-time Face Recognition at Entry Point

**Description**: Recognize attendee via face recognition when they approach the exhibition entry.

**Actors**: Attendee, Camera System, System

**Preconditions**:
- Camera is active and streaming
- Attendee has registered face encoding
- System is running real-time recognition

**Postconditions**:
- Attendee is recognized and checked in
- Visit record is created
- Real-time notification is sent

```mermaid
sequenceDiagram
    participant Attendee as Attendee
    participant Camera as Camera Stream
    participant Processor as CameraStreamProcessor
    participant FaceEngine as FaceRecognitionEngine
    participant DB as Database
    participant WS as WebSocket Manager
    participant Frontend as Frontend Display

    Attendee->>Camera: Approach camera view
    Camera->>Processor: Stream video frames
    Processor->>Processor: Sample frame for inference
    Processor->>FaceEngine: recognize_face(frame)
    FaceEngine->>FaceEngine: Detect face locations
    FaceEngine->>FaceEngine: Extract face encoding
    FaceEngine->>FaceEngine: Compare with known faces
    FaceEngine-->>Processor: Recognition result (attendee_id, confidence)
    
    alt Face recognized with high confidence
        Processor->>DB: Create visit record
        DB-->>Processor: Visit created
        Processor->>WS: Broadcast recognition update
        WS->>Frontend: Real-time recognition alert
        Frontend->>Frontend: Display attendee info
        Frontend->>Frontend: Highlight recognized face
    else Face not recognized
        Processor->>WS: Broadcast unknown face
        WS->>Frontend: Show unknown face alert
    end
    
    Processor->>Processor: Annotate frame with detection
    Processor-->>Camera: Continue processing
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

### Use Case 5: Camera Stream Management

**Description**: Admin configures and manages camera streams for the recognition system.

**Actors**: Admin User, System

**Preconditions**:
- Admin is logged into the system
- Camera hardware is available

**Postconditions**:
- Camera configuration is saved
- Stream processing is started/stopped
- System status is updated

```mermaid
sequenceDiagram
    participant Admin as Admin User
    participant Frontend as Frontend UI
    participant Backend as Backend API
    participant Processor as CameraStreamProcessor
    participant DB as Database
    participant WS as WebSocket Manager

    Admin->>Frontend: Open camera management
    Frontend->>Backend: GET /api/cameras/
    Backend->>DB: Query camera configurations
    DB-->>Backend: Camera list
    Backend-->>Frontend: Camera configurations
    
    Admin->>Frontend: Add new camera
    Frontend->>Backend: POST /api/cameras/
    Backend->>DB: Create camera record
    DB-->>Backend: Camera created
    Backend->>Processor: start_stream_processing(camera_id, stream_url)
    Processor->>Processor: Initialize camera stream
    Processor-->>Backend: Stream started
    Backend-->>Frontend: Camera added successfully
    
    Processor->>WS: Broadcast camera status update
    WS->>Frontend: Real-time status update
    Frontend->>Frontend: Update camera status display
    
    Admin->>Frontend: Stop camera stream
    Frontend->>Backend: POST /api/cameras/{id}/stop
    Backend->>Processor: stop_stream_processing(camera_id)
    Processor->>Processor: Release camera resources
    Processor-->>Backend: Stream stopped
    Backend->>DB: Update camera status
    Backend-->>Frontend: Camera stopped
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

1. **Registration Flow**: Admin → Frontend → Backend → Database → Face Engine
2. **Recognition Flow**: Camera → Processor → Recognition Engine → Database → WebSocket → Frontend
3. **Management Flow**: Admin → Frontend → Backend → Processor → Database
4. **Monitoring Flow**: Admin → Frontend → Backend → System Components → Real-time Updates

These sequence diagrams illustrate the core business processes and system interactions that make the VIP Reception System functional and efficient for aviation exhibition management.
