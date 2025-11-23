#!/usr/bin/env python3
"""
Simple test script to verify the VIP Reception System backend functionality
"""

import sys
import os

# Add backend to Python path (now we're in tests/backend, so go up two levels)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from app.database import engine, Base, get_db
        print("✓ Database module imported successfully")
    except Exception as e:
        print(f"✗ Database module import failed: {e}")
        return False
    
    try:
        from app.schemas import CameraCreate, AttendeeCreate, RecognitionRequest
        print("✓ Schemas module imported successfully")
    except Exception as e:
        print(f"✗ Schemas module import failed: {e}")
        return False
    
    try:
        from app.websocket_manager import ConnectionManager
        print("✓ WebSocket manager imported successfully")
    except Exception as e:
        print(f"✗ WebSocket manager import failed: {e}")
        return False
    
    try:
        from app.recognition_engine import FaceRecognitionEngine, QRCodeEngine
        print("✓ Recognition engine imported successfully")
    except Exception as e:
        print(f"✗ Recognition engine import failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connection and table creation"""
    print("\nTesting database connection...")
    
    try:
        from app.database import engine, Base
        
        # Try to create tables
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✓ Database connection test passed")
            
        return True
        
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False

def test_schema_validation():
    """Test Pydantic schema validation"""
    print("\nTesting schema validation...")
    
    try:
        from app.schemas import CameraCreate, AttendeeCreate, RecognitionRequest
        
        # Test CameraCreate schema
        camera_data = {
            "name": "Test Camera",
            "source": "0",
            "location": "Test Location",
            "resolution": "1920x1080",
            "fps": 30
        }
        camera = CameraCreate(**camera_data)
        print("✓ Camera schema validation passed")
        
        # Test AttendeeCreate schema
        attendee_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "company": "Test Company",
            "position": "Test Position",
            "phone": "+1234567890",
            "is_vip": False
        }
        attendee = AttendeeCreate(**attendee_data)
        print("✓ Attendee schema validation passed")
        
        # Test RecognitionRequest schema
        recognition_data = {
            "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=",
            "camera_id": 1
        }
        recognition = RecognitionRequest(**recognition_data)
        print("✓ Recognition schema validation passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema validation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("VIP Reception System - Backend Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 3
    
    # Run tests
    if test_imports():
        tests_passed += 1
    
    if test_database_connection():
        tests_passed += 1
    
    if test_schema_validation():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 All tests passed! The backend is ready for development.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
