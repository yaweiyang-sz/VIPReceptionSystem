from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vip_user:vip_password@localhost:5432/vip_reception")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Attendee(Base):
    __tablename__ = "attendees"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    company = Column(String(255))
    position = Column(String(255))
    phone = Column(String(50))
    photo_url = Column(Text)  # URL to stored face photo
    face_encoding = Column(Text)  # Serialized face encoding data (base64 + pickle)
    face_encoding_version = Column(String(10), default="v1")  # Encoding algorithm version
    qr_code = Column(String(100), unique=True, index=True)
    is_vip = Column(Boolean, default=False)
    status = Column(String(50), default="registered")  # registered, checked_in, checked_out
    face_encoding_quality = Column(String(20), default="standard")  # quality level used
    face_encoding_created = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    visits = relationship("Visit", back_populates="attendee")

class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    attendee_id = Column(Integer, ForeignKey("attendees.id"))
    check_in_time = Column(DateTime(timezone=True), server_default=func.now())
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    recognition_method = Column(String(50))  # face, qr_code
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    notes = Column(Text)

    attendee = relationship("Attendee", back_populates="visits")
    camera = relationship("Camera", back_populates="visits")

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    source = Column(String(255), nullable=False)  # RTSP URL, device ID, etc.
    location = Column(String(255))
    is_active = Column(Boolean, default=True)
    resolution = Column(String(50), default="1920x1080")
    fps = Column(Integer, default=30)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    visits = relationship("Visit", back_populates="camera")

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
