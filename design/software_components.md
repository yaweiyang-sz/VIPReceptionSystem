# VIP Reception System - Software Components Design

## System Architecture Overview

The VIP Reception System is a web-based visitor recognition system designed for aviation interior exhibitions. It provides dual identification methods (face recognition + QR codes) with real-time visitor information display.

## Core Components Architecture

### 1. Frontend Layer
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/Vue.js)                  │
├─────────────────────────────────────────────────────────────┤
│  • AttendeeManager Component                                │
│  • CameraManager Component                                  │
│  • LiveCameraView Component                                 │
│  • WebSocket Client                                         │
│  • API Client                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2. Backend Layer
```
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│  • API Routes Layer                                         │
│  • Recognition Engine Layer                                 │
│  • Data Access Layer                                        │
│  • WebSocket Manager                                        │
└─────────────────────────────────────────────────────────────┘
```

### 3. Data Layer
```
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
├─────────────────────────────────────────────────────────────┤
│  • PostgreSQL Database                                      │
│  • File Storage (Face Images)                               │
│  • In-Memory Cache (Face Encodings)                         │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Component Specifications

### Frontend Components

#### AttendeeManager Component
- **Purpose**: Manage attendee registration and data
- **Responsibilities**:
  - Create, read, update, delete attendees
  - Upload and process face photos
  - Display attendee information
  - Handle face encoding status
- **Dependencies**: API Client, File Upload Service

#### CameraManager Component
- **Purpose**: Configure and manage camera streams
- **Responsibilities**:
  - Add/remove camera configurations
  - Start/stop camera streams
  - Monitor camera status
- **Dependencies**: API Client, WebSocket Client

#### LiveCameraView Component
- **Purpose**: Display real-time camera feeds with recognition overlays
- **Responsibilities**:
  - Render camera video streams
  - Display face detection rectangles
  - Show QR code detection areas
  - Update recognition results in real-time
- **Dependencies**: WebSocket Client, Video Streaming Service

### Backend Components

#### API Routes Layer
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  AttendeeRoutes │  │  CameraRoutes   │  │ RecognitionRoutes│
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • CRUD ops      │  │ • Camera config │  │ • Face recog    │
│ • Photo upload  │  │ • Stream mgmt   │  │ • QR scanning   │
│ • Visit history │  │ • Status check  │  │ • Real-time     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

#### Recognition Engine Layer
```
┌─────────────────────────────────────────────────────────────┐
│                 Recognition Engine                          │
├─────────────────────────────────────────────────────────────┤
│  • FaceRecognitionEngine                                    │
│    - Face detection & encoding                              │
│    - Face matching & recognition                            │
│    - Performance optimization                               │
│  • QRCodeEngine                                             │
│    - QR code scanning                                       │
│    - QR code generation                                     │
│  • CameraStreamProcessor                                    │
│    - Real-time stream processing                            │
│    - Frame analysis & annotation                            │
└─────────────────────────────────────────────────────────────┘
```

#### Data Access Layer
```
┌─────────────────────────────────────────────────────────────┐
│                   Data Access Layer                         │
├─────────────────────────────────────────────────────────────┤
│  • Database Models                                          │
│    - Attendee model                                         │
│    - Visit model                                            │
│    - Camera model                                           │
│  • Repository Pattern                                       │
│    - AttendeeRepository                                     │
│    - VisitRepository                                        │
│    - CameraRepository                                       │
│  • Data Validation                                          │
│    - Pydantic schemas                                       │
│    - Input validation                                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Interfaces

### FaceRecognitionEngine Interface
```python
class FaceRecognitionEngine:
    async def encode_face(image_data: bytes) -> Optional[Dict]
    async def recognize_face(image: np.ndarray, db: Session) -> Optional[Dict]
    def load_known_faces(db: Session) -> bool
    def update_known_faces(attendee_id: int, encoding_b64: str, metadata: Dict)
    def get_performance_stats() -> Dict[str, Any]
```

### QRCodeEngine Interface
```python
class QRCodeEngine:
    async def scan_qr_code(image: np.ndarray) -> Optional[str]
    async def generate_qr_code(data: str) -> Optional[bytes]
```

### CameraStreamProcessor Interface
```python
class CameraStreamProcessor:
    async def start_stream_processing(camera_id: int, stream_url: str, db: Session)
    def stop_stream_processing(camera_id: int)
    async def _process_stream(camera_id: int)
    async def _send_recognition_update(camera_id: int, face_result: Dict, qr_result: str, frame: np.ndarray)
```

## Data Models

### Attendee Model
```python
class Attendee(Base):
    id: int
    first_name: str
    last_name: str
    email: str
    company: str
    position: str
    phone: str
    is_vip: bool
    qr_code: str
    photo_url: str
    face_encoding: str
    status: str
    created_at: datetime
    updated_at: datetime
```

### Visit Model
```python
class Visit(Base):
    id: int
    attendee_id: int
    check_in_time: datetime
    check_out_time: Optional[datetime]
    recognition_method: str  # 'face' or 'qr'
    camera_id: int
```

### Camera Model
```python
class Camera(Base):
    id: int
    name: str
    source: str
    location: str
    resolution: str
    fps: int
    is_active: bool
    created_at: datetime
```

## Integration Points

### WebSocket Communication
- **Protocol**: WebSocket for real-time updates
- **Messages**: Recognition updates, camera status, system alerts
- **Clients**: Frontend components, admin dashboard

### External Dependencies
- **OpenCV**: Computer vision operations
- **face_recognition**: Face detection and recognition
- **pyzbar**: QR code scanning
- **PostgreSQL**: Data persistence
- **SQLAlchemy**: ORM and database operations

## Performance Considerations

### Face Recognition Optimization
- Batch processing for large datasets
- In-memory caching of face encodings
- Configurable confidence thresholds
- Performance monitoring and statistics

### Real-time Processing
- Frame sampling for inference optimization
- Asynchronous processing for multiple cameras
- WebSocket broadcasting for real-time updates
- Resource management for concurrent streams

## Security Considerations

### Data Protection
- Secure storage of face encodings
- Access control for camera streams
- Input validation for all endpoints
- Secure file upload handling

### Privacy Compliance
- GDPR-compliant data handling
- Secure deletion of attendee data
- Privacy-focused face recognition
- Audit logging for data access
