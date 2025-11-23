#!/usr/bin/env python3
"""
Test face detection with a known good face image
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import face_recognition
from app.recognition_engine import FaceRecognitionEngine

async def test_face_detection():
    """Test face detection with different images"""
    face_engine = FaceRecognitionEngine()
    
    print("Testing face detection with different approaches...")
    
    # Test 1: Check the existing photos
    print("\n=== Testing existing photos ===")
    for attendee_id in [1, 6]:
        photo_path = f"/app/data/faces/{attendee_id}.jpg"
        if os.path.exists(photo_path):
            print(f"\nTesting photo {attendee_id}: {photo_path}")
            
            # Load image
            image = cv2.imread(photo_path)
            if image is not None:
                print(f"Image shape: {image.shape}")
                
                # Try direct face detection with face_recognition
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Method 1: HOG
                face_locations_hog = face_recognition.face_locations(rgb_image, model="hog")
                print(f"HOG faces found: {len(face_locations_hog)}")
                
                # Method 2: CNN
                face_locations_cnn = face_recognition.face_locations(rgb_image, model="cnn")
                print(f"CNN faces found: {len(face_locations_cnn)}")
                
                # Method 3: Try with OpenCV
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces_opencv = face_cascade.detectMultiScale(gray, 1.1, 4)
                print(f"OpenCV faces found: {len(faces_opencv)}")
                
                # Display image info
                print(f"Image dimensions: {image.shape[1]}x{image.shape[0]}")
                print(f"Image type: {image.dtype}")
                
                # Check if image is too small
                if image.shape[0] < 100 or image.shape[1] < 100:
                    print("⚠️  Image might be too small for face detection")
                else:
                    print("✅ Image size should be sufficient for face detection")
            else:
                print("❌ Failed to load image")
        else:
            print(f"❌ Photo not found: {photo_path}")
    
    # Test 2: Create a simple test image with a face-like pattern
    print("\n=== Creating test pattern ===")
    test_image = np.zeros((200, 200, 3), dtype=np.uint8)
    test_image.fill(128)  # Gray background
    
    # Add some face-like features
    cv2.circle(test_image, (100, 70), 30, (255, 255, 255), -1)  # Head
    cv2.circle(test_image, (80, 60), 5, (0, 0, 0), -1)  # Left eye
    cv2.circle(test_image, (120, 60), 5, (0, 0, 0), -1)  # Right eye
    cv2.ellipse(test_image, (100, 90), (20, 10), 0, 0, 180, (0, 0, 0), 2)  # Mouth
    
    print(f"Test image shape: {test_image.shape}")
    
    # Try face detection on test pattern
    rgb_test = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)
    face_locations_test = face_recognition.face_locations(rgb_test, model="hog")
    print(f"Test pattern faces found: {len(face_locations_test)}")
    
    if len(face_locations_test) == 0:
        print("⚠️  Even simple face patterns are not being detected")
        print("This suggests the face detection library might have issues")
    else:
        print("✅ Simple face patterns are being detected")

if __name__ == "__main__":
    asyncio.run(test_face_detection())
