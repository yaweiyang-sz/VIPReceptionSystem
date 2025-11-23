#!/usr/bin/env python3
"""
Test script to verify face encoding functionality
"""
import sys
import os
import cv2
import numpy as np

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.recognition_engine import FaceRecognitionEngine

def test_face_encoding():
    """Test face encoding with a sample image"""
    print("Testing face encoding functionality...")
    
    # Create a simple test image with a face (you can replace this with a real image)
    # For now, we'll create a simple colored image
    test_image = np.ones((200, 200, 3), dtype=np.uint8) * 128  # Gray image
    
    # Add some features to simulate a face
    cv2.rectangle(test_image, (80, 60), (120, 100), (255, 255, 255), -1)  # White rectangle for face
    cv2.circle(test_image, (90, 70), 5, (0, 0, 0), -1)  # Left eye
    cv2.circle(test_image, (110, 70), 5, (0, 0, 0), -1)  # Right eye
    cv2.line(test_image, (95, 90), (105, 90), (0, 0, 0), 2)  # Mouth
    
    # Convert to bytes
    success, encoded_image = cv2.imencode('.jpg', test_image)
    if not success:
        print("Failed to encode test image")
        return False
    
    image_bytes = encoded_image.tobytes()
    
    # Test face encoding
    engine = FaceRecognitionEngine()
    
    try:
        import asyncio
        result = asyncio.run(engine.encode_face(image_bytes))
        
        if result:
            print(f"✅ Face encoding successful! Found {len(result)} faces")
            print(f"Face locations: {[r['face_location'] for r in result]}")
            return True
        else:
            print("❌ No faces detected in test image")
            return False
            
    except Exception as e:
        print(f"❌ Face encoding failed with error: {e}")
        return False

def test_face_recognition_library():
    """Test if face_recognition library is working"""
    print("Testing face_recognition library...")
    
    try:
        import face_recognition
        print("✅ face_recognition library imported successfully")
        
        # Test basic functionality
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        face_locations = face_recognition.face_locations(test_image)
        print(f"Face locations found: {len(face_locations)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ face_recognition library not available: {e}")
        return False
    except Exception as e:
        print(f"❌ face_recognition library error: {e}")
        return False

if __name__ == "__main__":
    print("Running face encoding tests...")
    
    # Test library availability
    if not test_face_recognition_library():
        print("\n⚠️  Face recognition library is not working properly.")
        print("This might be due to missing dependencies or installation issues.")
        print("Please check that face_recognition and dlib are properly installed.")
        sys.exit(1)
    
    # Test face encoding
    if test_face_encoding():
        print("\n✅ All tests passed! Face encoding should work correctly.")
    else:
        print("\n⚠️  Face encoding test failed. This might be due to:")
        print("   - No actual face in the test image")
        print("   - Face detection parameters too strict")
        print("   - Image quality issues")
        print("\nTry uploading a real face photo to test the actual functionality.")
