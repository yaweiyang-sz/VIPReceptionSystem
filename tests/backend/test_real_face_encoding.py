#!/usr/bin/env python3
"""
Test face encoding with actual photos from the database
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import face_recognition
from app.database import SessionLocal, Attendee
from app.recognition_engine import FaceRecognitionEngine

async def test_real_face_encoding():
    """Test face encoding with actual photos from the database"""
    db = SessionLocal()
    face_engine = FaceRecognitionEngine()
    
    try:
        # Get attendees with photos
        attendees_with_photos = db.query(Attendee).filter(
            Attendee.photo_url.isnot(None),
            Attendee.photo_url != ''
        ).all()
        
        print(f"Found {len(attendees_with_photos)} attendees with photos")
        
        for attendee in attendees_with_photos:
            print(f"\nTesting attendee: {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
            print(f"Photo URL: {attendee.photo_url}")
            
            # Check if photo file exists
            photo_path = f"/app/data/faces/{attendee.id}.jpg"
            if os.path.exists(photo_path):
                print(f"✅ Photo file exists: {photo_path}")
                
                # Read the image
                image = cv2.imread(photo_path)
                if image is not None:
                    print(f"✅ Image loaded successfully: {image.shape}")
                    
                    # Try face encoding
                    with open(photo_path, 'rb') as f:
                        image_data = f.read()
                    
                    print("Attempting face encoding...")
                    encoding_result = await face_engine.encode_face(image_data)
                    
                    if encoding_result:
                        print(f"✅ Face encoding successful! Found {len(encoding_result)} faces")
                        for result in encoding_result:
                            print(f"  - Face location: {result['face_location']}")
                            print(f"  - Encoding length: {len(result['encoding'])} chars")
                    else:
                        print("❌ No faces detected in the photo")
                        
                else:
                    print("❌ Failed to load image")
            else:
                print(f"❌ Photo file not found: {photo_path}")
                
    except Exception as e:
        print(f"Error testing face encoding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_real_face_encoding())
