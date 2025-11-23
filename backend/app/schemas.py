from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# Camera Schemas
class CameraBase(BaseModel):
    name: str
    source: str
    location: Optional[str] = None
    resolution: Optional[str] = "1920x1080"
    fps: Optional[int] = 30

class CameraCreate(CameraBase):
    pass

class CameraResponse(CameraBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Attendee Schemas
class AttendeeBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    company: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    is_vip: Optional[bool] = False

class AttendeeCreate(AttendeeBase):
    pass

class AttendeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    is_vip: Optional[bool] = None
    status: Optional[str] = None

class AttendeeResponse(AttendeeBase):
    id: int
    qr_code: str
    status: str
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Recognition Schemas
class RecognitionRequest(BaseModel):
    image_data: str  # Base64 encoded image
    camera_id: int

class RecognitionResponse(BaseModel):
    success: bool
    attendee: Optional[AttendeeResponse] = None
    confidence: Optional[float] = None
    method: Optional[str] = None
    message: Optional[str] = None

# Visit Schemas
class VisitBase(BaseModel):
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    recognition_method: Optional[str] = None
    notes: Optional[str] = None

class VisitResponse(VisitBase):
    id: int
    attendee_id: int
    camera_id: int
    attendee: Optional[AttendeeResponse] = None
    camera: Optional[CameraResponse] = None

    class Config:
        from_attributes = True

# Admin Dashboard Schemas
class DashboardStats(BaseModel):
    total_attendees: int
    vip_attendees: int
    checked_in_attendees: int
    today_visits: int
    active_cameras: int
    recent_visits: int

class SystemStatus(BaseModel):
    database_status: str
    camera_status: Dict[str, Any]
    system_config: Dict[str, str]
    uptime: str
    last_updated: datetime

# System Config Schemas
class SystemConfigBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SystemConfigResponse(SystemConfigBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# WebSocket Message Schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]

class RecognitionNotification(BaseModel):
    type: str = "attendee_recognized"
    attendee: Dict[str, Any]
    recognition_method: str
    camera_id: int
    timestamp: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

# Search and Filter Schemas
class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 50

class AttendeeFilter(BaseModel):
    is_vip: Optional[bool] = None
    status: Optional[str] = None
    company: Optional[str] = None
    skip: Optional[int] = 0
    limit: Optional[int] = 100

# File Upload Schemas
class FileUploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    message: str

# Error Response Schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

class ValidationError(BaseModel):
    loc: List[str]
    msg: str
    type: str

class HTTPValidationError(BaseModel):
    detail: List[ValidationError]
