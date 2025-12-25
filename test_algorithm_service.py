#!/usr/bin/env python3
"""
Test script for the algorithm service integration
"""
import requests
import json
import cv2
import numpy as np
import base64
import sys
import os

def test_algorithm_service():
    """Test the algorithm service endpoints"""
    
    # Algorithm service URL
    algorithm_url = "http://localhost:8001"
    
    print("Testing Algorithm Service Integration")
    print("=" * 50)
    
    # Test 1: Check service health
    print("\n1. Testing service health...")
    try:
        response = requests.get(f"{algorithm_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Service is healthy: {response.json()}")
        else:
            print(f"✗ Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to algorithm service: {e}")
        print("Make sure the algorithm service is running on port 8001")
        return False
    
    # Test 2: Check model status
    print("\n2. Testing model status...")
    try:
        response = requests.get(f"{algorithm_url}/api/v1/model/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✓ Model status: {status}")
        else:
            print(f"✗ Model status check failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Model status check error: {e}")
    
    # Test 3: Create a test image for encoding
    print("\n3. Testing face encoding...")
    try:
        # Create a simple test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image.fill(100)  # Gray background
        
        # Draw a simple face-like shape
        cv2.rectangle(test_image, (200, 150), (440, 350), (255, 255, 255), -1)  # Face
        cv2.circle(test_image, (280, 220), 20, (0, 0, 255), -1)  # Left eye
        cv2.circle(test_image, (360, 220), 20, (0, 0, 255), -1)  # Right eye
        cv2.ellipse(test_image, (320, 280), (60, 30), 0, 0, 180, (0, 255, 0), -1)  # Mouth
        
        # Encode image to bytes
        _, buffer = cv2.imencode('.jpg', test_image)
        image_bytes = buffer.tobytes()
        
        # Test encoding endpoint
        files = {'image': ('test_face.jpg', image_bytes, 'image/jpeg')}
        response = requests.post(f"{algorithm_url}/api/v1/encode", files=files, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                num_faces = result.get('num_faces', 0)
                print(f"✓ Face encoding successful: Found {num_faces} faces")
                if num_faces > 0:
                    print(f"  First encoding: {result['encodings'][0]['encoding'][:50]}...")
            else:
                print(f"✗ Face encoding failed: {result.get('message', 'Unknown error')}")
        else:
            print(f"✗ Face encoding request failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Face encoding test error: {e}")
    
    # Test 4: Test recognition with the same image
    print("\n4. Testing face recognition...")
    try:
        # Use the same test image
        files = {'image': ('test_face.jpg', image_bytes, 'image/jpeg')}
        response = requests.post(f"{algorithm_url}/api/v1/recognize", files=files, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                if result.get('recognition'):
                    recognition = result['recognition']
                    print(f"✓ Face recognition successful!")
                    print(f"  Recognized: {recognition.get('full_name', 'Unknown')}")
                    print(f"  Confidence: {recognition.get('confidence', 0):.2%}")
                    print(f"  VIP Status: {'Yes' if recognition.get('is_vip') else 'No'}")
                else:
                    print("✓ No face recognized (expected for test image)")
            else:
                print(f"✗ Face recognition failed: {result.get('message', 'Unknown error')}")
        else:
            print(f"✗ Face recognition request failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Face recognition test error: {e}")
    
    # Test 5: Test model update
    print("\n5. Testing model update...")
    try:
        response = requests.post(f"{algorithm_url}/api/v1/model/update", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✓ Model update successful: {result.get('message', 'Success')}")
            else:
                print(f"✗ Model update failed: {result.get('message', 'Unknown error')}")
        else:
            print(f"✗ Model update request failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Model update test error: {e}")
    
    print("\n" + "=" * 50)
    print("Algorithm Service Integration Test Complete!")
    print("\nNext steps:")
    print("1. Start the full system with: docker-compose up --build")
    print("2. Access the frontend at: http://localhost:3000")
    print("3. Add attendees with face photos through the admin interface")
    print("4. Configure cameras and test real-time recognition")
    
    return True

if __name__ == "__main__":
    success = test_algorithm_service()
    sys.exit(0 if success else 1)
