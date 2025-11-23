#!/usr/bin/env python3
"""
Simple test for face recognition functionality
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import SessionLocal
from app.recognition_engine import FaceRecognitionEngine

async def test_simple_recognition():
    """Test the face recognition functionality using the public API"""
    db = SessionLocal()
    face_engine = FaceRecognitionEngine()
    
    try:
        print("=== Testing Simple Face Recognition ===\n")
        
        # Test 1: Check if we have attendees with face encodings
        attendees_with_encodings = db.execute(text("""
            SELECT id, first_name, last_name, face_encoding 
            FROM attendees 
            WHERE face_encoding IS NOT NULL
        """)).fetchall()
        
        print(f"Found {len(attendees_with_encodings)} attendees with face encodings")
        
        if len(attendees_with_encodings) == 0:
            print("❌ No attendees with face encodings found")
            return
        
        # Test 2: Test recognition with the stored photo
        for attendee in attendees_with_encodings:
            print(f"\nTesting recognition for: {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
            
            photo_path = f"/app/data/faces/{attendee.id}.jpg"
            if os.path.exists(photo_path):
                print(f"✅ Photo file exists: {photo_path}")
                
                # Read the image data
                with open(photo_path, 'rb') as f:
                    image_data = f.read()
                
                # Test recognition using the public API
                print("Testing face recognition...")
                recognition_result = await face_engine.recognize_faces(image_data)
                
                if recognition_result:
                    print(f"✅ Recognition successful! Found {len(recognition_result)} face(s)")
                    for result in recognition_result:
                        print(f"  - Attendee ID: {result.get('attendee_id', 'Unknown')}")
                        print(f"  - Confidence: {result.get('confidence', 0):.4f}")
                        print(f"  - Face location: {result.get('face_location', 'Unknown')}")
                        
                        # Check if the recognized attendee matches the expected one
                        if result.get('attendee_id') == attendee.id:
                            print(f"🎉 SUCCESS: Correctly recognized attendee {attendee.id}!")
                        else:
                            print(f"⚠️  Recognized different attendee: {result.get('attendee_id')}")
                else:
                    print("❌ No faces recognized")
            else:
                print(f"❌ Photo file not found: {photo_path}")
        
        print("\n🎉 Simple face recognition test completed!")
        
    except Exception as e:
        print(f"Error testing recognition: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_simple_recognition())
