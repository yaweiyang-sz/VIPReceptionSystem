#!/usr/bin/env python3
"""
Complete workflow test for face upload, display, and replacement functionality
"""

import requests
import json
import base64
import os
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGE_PATH = "test_face.jpg"  # Replace with your test image path

def test_complete_workflow():
    """Test the complete face upload, display, and replacement workflow"""
    print("🧪 Testing Complete Face Upload Workflow")
    print("=" * 60)
    
    # Step 1: Check system health
    print("\n1. Checking system health...")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/dashboard/stats")
        if response.status_code == 200:
            print("✅ Backend is running and accessible")
        else:
            print(f"❌ Backend returned status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("Make sure the Docker containers are running with: docker-compose up -d")
        return
    
    # Step 2: Create a test attendee
    print("\n2. Creating test attendee...")
    attendee_data = {
        "first_name": "Workflow",
        "last_name": "Test",
        "email": f"workflow.test.{int(time.time())}@example.com",
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
    
    # Step 3: Upload initial face photo
    print("\n3. Uploading initial face photo...")
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
            print(f"✅ Initial photo uploaded: {result['message']}")
            print(f"   - Face encoding saved: {result['face_encoding_saved']}")
            print(f"   - Photo URL: {result['photo_url']}")
    except Exception as e:
        print(f"❌ Failed to upload initial photo: {e}")
        return
    
    # Step 4: Verify attendee record was updated
    print("\n4. Verifying attendee record update...")
    try:
        response = requests.get(f"{BASE_URL}/api/attendees/{attendee['id']}")
        response.raise_for_status()
        updated_attendee = response.json()
        
        if updated_attendee.get('face_encoding'):
            print("✅ Face encoding successfully saved to database")
            print(f"   - Photo URL in database: {updated_attendee.get('photo_url', 'N/A')}")
            print(f"   - Has face encoding: Yes")
        else:
            print("❌ Face encoding not found in attendee record")
            return
    except Exception as e:
        print(f"❌ Failed to verify encoding: {e}")
        return
    
    # Step 5: Test photo serving endpoint
    print("\n5. Testing photo serving endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/attendees/{attendee['id']}/photo")
        if response.status_code == 200:
            print("✅ Photo serving endpoint working correctly")
            print(f"   - Content-Type: {response.headers.get('content-type')}")
            print(f"   - Content-Length: {len(response.content)} bytes")
        else:
            print(f"❌ Photo serving failed with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to test photo serving: {e}")
    
    # Step 6: Test face recognition with uploaded photo
    print("\n6. Testing face recognition with uploaded photo...")
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
            
            # Verify it recognized our test attendee
            if recognition_result.get('attendee_id') == attendee['id']:
                print("   - ✅ Correct attendee identified!")
            else:
                print(f"   - ⚠ Different attendee identified (expected {attendee['id']})")
        else:
            print("❌ Face recognition failed")
            print(f"   - Message: {recognition_result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Failed to test recognition: {e}")
    
    # Step 7: Test photo replacement (upload different photo)
    print("\n7. Testing photo replacement...")
    # Create a simple test image for replacement (you can use the same image for testing)
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'file': ('replacement_photo.jpg', f, 'image/jpeg')}
            response = requests.post(
                f"{BASE_URL}/api/attendees/{attendee['id']}/upload-photo",
                files=files
            )
            response.raise_for_status()
            replacement_result = response.json()
            print(f"✅ Photo replacement successful: {replacement_result['message']}")
            print(f"   - Face encoding updated: {replacement_result['face_encoding_saved']}")
    except Exception as e:
        print(f"❌ Failed to replace photo: {e}")
    
    # Step 8: Verify system statistics
    print("\n8. Checking system statistics...")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/dashboard/stats")
        response.raise_for_status()
        stats = response.json()
        
        print(f"✅ System Statistics:")
        print(f"   - Total attendees: {stats.get('total_attendees', 0)}")
        print(f"   - VIP attendees: {stats.get('vip_attendees', 0)}")
        print(f"   - Attendees with face encoding: {stats.get('attendees_with_face_encoding', 0)}")
        print(f"   - Face cache size: {stats.get('face_cache_size', 0)}")
        
    except Exception as e:
        print(f"⚠ Could not fetch system stats: {e}")
    
    # Step 9: Test attendee listing
    print("\n9. Testing attendee listing...")
    try:
        response = requests.get(f"{BASE_URL}/api/attendees/")
        response.raise_for_status()
        all_attendees = response.json()
        
        test_attendee = next((a for a in all_attendees if a['id'] == attendee['id']), None)
        if test_attendee:
            print(f"✅ Test attendee found in listing:")
            print(f"   - Name: {test_attendee['first_name']} {test_attendee['last_name']}")
            print(f"   - Has photo URL: {bool(test_attendee.get('photo_url'))}")
            print(f"   - Has face encoding: {bool(test_attendee.get('face_encoding'))}")
        else:
            print("❌ Test attendee not found in listing")
            
    except Exception as e:
        print(f"❌ Failed to list attendees: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Complete workflow test completed!")
    print(f"Test attendee ID: {attendee['id']}")
    print("\n📝 Next steps:")
    print("1. Access the web interface at http://localhost:3000")
    print("2. Go to 'Manage Attendees' tab")
    print("3. Click 'Edit' on the test attendee")
    print("4. Verify the uploaded photo is displayed")
    print("5. Try uploading a different photo to replace it")

def check_photo_urls():
    """Check all attendees and their photo URLs"""
    print("\n📋 Checking all attendees and photo URLs:")
    try:
        response = requests.get(f"{BASE_URL}/api/attendees/")
        response.raise_for_status()
        attendees = response.json()
        
        for attendee in attendees:
            photo_status = "No photo"
            if attendee.get('photo_url'):
                photo_status = f"Photo URL: {attendee['photo_url']}"
            elif attendee.get('face_encoding'):
                photo_status = "Has encoding but no URL"
            
            print(f"   - {attendee['first_name']} {attendee['last_name']} (ID: {attendee['id']}): {photo_status}")
            
    except Exception as e:
        print(f"❌ Failed to check attendees: {e}")

if __name__ == "__main__":
    print("VIP Reception System - Complete Workflow Test")
    print("=" * 60)
    
    # Run the complete workflow test
    test_complete_workflow()
    
    # Check all photo URLs
    check_photo_urls()
    
    print("\n🔧 Troubleshooting Tips:")
    print("1. If photos don't display, check browser console for CORS errors")
    print("2. Verify the backend is serving photos correctly")
    print("3. Check that face encodings are being stored in the database")
    print("4. Ensure the face cache is being updated after uploads")
