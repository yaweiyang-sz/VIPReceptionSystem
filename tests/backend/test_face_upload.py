#!/usr/bin/env python3
"""
Simple test script to verify face upload and recognition functionality
"""

import requests
import json
import base64
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGE_PATH = "test_face.jpg"  # Replace with your test image path

def test_face_upload():
    """Test the complete face upload and recognition workflow"""
    print("🧪 Testing Face Upload and Recognition System")
    print("=" * 50)
    
    # Step 1: Create a test attendee
    print("\n1. Creating test attendee...")
    attendee_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"test.user.{os.getpid()}@example.com",
        "company": "Test Company",
        "position": "Test Position",
        "phone": "+1234567890",
        "is_vip": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/attendees/", json=attendee_data)
        response.raise_for_status()
        attendee = response.json()
        print(f"✅ Created attendee: {attendee['first_name']} {attendee['last_name']} (ID: {attendee['id']})")
    except Exception as e:
        print(f"❌ Failed to create attendee: {e}")
        return
    
    # Step 2: Upload face photo
    print("\n2. Uploading face photo...")
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"❌ Test image not found: {TEST_IMAGE_PATH}")
        print("Please create a test image with a clear face and update TEST_IMAGE_PATH")
        return
    
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_IMAGE_PATH), f, 'image/jpeg')}
            response = requests.post(
                f"{BASE_URL}/api/attendees/{attendee['id']}/upload-photo",
                files=files
            )
            response.raise_for_status()
            result = response.json()
            print(f"✅ Photo uploaded: {result}")
    except Exception as e:
        print(f"❌ Failed to upload photo: {e}")
        return
    
    # Step 3: Verify face encoding was saved
    print("\n3. Verifying face encoding...")
    try:
        response = requests.get(f"{BASE_URL}/api/attendees/{attendee['id']}")
        response.raise_for_status()
        updated_attendee = response.json()
        
        if updated_attendee.get('face_encoding'):
            print("✅ Face encoding successfully saved to database")
            print(f"   - Photo URL: {updated_attendee.get('photo_url', 'N/A')}")
            print(f"   - Has face encoding: Yes")
        else:
            print("❌ Face encoding not found in attendee record")
            return
    except Exception as e:
        print(f"❌ Failed to verify encoding: {e}")
        return
    
    # Step 4: Test face recognition with the same image
    print("\n4. Testing face recognition...")
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        recognition_data = {
            "image_data": f"data:image/jpeg;base64,{image_b64}",
            "camera_id": 1
        }
        
        response = requests.post(f"{BASE_URL}/api/recognition/auto", json=recognition_data)
        response.raise_for_status()
        recognition_result = response.json()
        
        if recognition_result.get('success'):
            print("✅ Face recognition successful!")
            print(f"   - Attendee ID: {recognition_result.get('attendee_id')}")
            print(f"   - Confidence: {recognition_result.get('confidence', 0) * 100:.1f}%")
            print(f"   - Method: {recognition_result.get('method')}")
        else:
            print("❌ Face recognition failed")
            print(f"   - Message: {recognition_result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Failed to test recognition: {e}")
        return
    
    # Step 5: Check system statistics
    print("\n5. Checking system statistics...")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/dashboard/stats")
        response.raise_for_status()
        stats = response.json()
        
        print(f"✅ System Statistics:")
        print(f"   - Total attendees: {stats.get('total_attendees', 0)}")
        print(f"   - VIP attendees: {stats.get('vip_attendees', 0)}")
        print(f"   - Attendees with face encoding: {stats.get('attendees_with_face_encoding', 0)}")
        print(f"   - Active cameras: {stats.get('active_cameras', 0)}")
        
    except Exception as e:
        print(f"⚠ Could not fetch system stats: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Face upload and recognition test completed!")
    print(f"Test attendee ID: {attendee['id']}")
    print(f"You can now test real-time recognition with camera streams")

def check_system_health():
    """Check if the system is running and accessible"""
    print("\n🔍 Checking system health...")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/dashboard/stats")
        if response.status_code == 200:
            print("✅ Backend is running and accessible")
            return True
        else:
            print(f"❌ Backend returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("Make sure the Docker containers are running with: docker-compose up -d")
        return False

def list_attendees_with_faces():
    """List all attendees with face encodings"""
    print("\n📋 Attendees with face encodings:")
    try:
        response = requests.get(f"{BASE_URL}/api/attendees/")
        response.raise_for_status()
        attendees = response.json()
        
        attendees_with_faces = [a for a in attendees if a.get('face_encoding')]
        
        if attendees_with_faces:
            for attendee in attendees_with_faces:
                print(f"   - {attendee['first_name']} {attendee['last_name']} (ID: {attendee['id']})")
        else:
            print("   No attendees with face encodings found")
            
    except Exception as e:
        print(f"❌ Failed to list attendees: {e}")

if __name__ == "__main__":
    print("VIP Reception System - Face Upload Test")
    print("=" * 50)
    
    # Check if system is running
    if not check_system_health():
        exit(1)
    
    # List current attendees with faces
    list_attendees_with_faces()
    
    # Run the main test
    test_face_upload()
    
    print("\n📝 Instructions for testing:")
    print("1. Make sure you have a test image with a clear face")
    print("2. Update TEST_IMAGE_PATH in this script to point to your image")
    print("3. Run the script again to test the complete workflow")
    print("4. Use the web interface at http://localhost:3000 to manage attendees")
    print("5. Test real-time recognition with camera streams")
