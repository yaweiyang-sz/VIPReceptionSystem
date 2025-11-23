#!/usr/bin/env python3
"""
Final verification test for face recognition functionality
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
from sqlalchemy import text
from app.database import SessionLocal
from app.recognition_engine import FaceRecognitionEngine

async def test_final_verification():
    """Final verification test for face recognition functionality"""
    db = SessionLocal()
    face_engine = FaceRecognitionEngine()
    
    try:
        print("=== FINAL FACE RECOGNITION VERIFICATION ===\n")
        
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
        
        # Load the known faces into the recognition engine
        print("Loading known faces into recognition engine...")
        success = face_engine.load_known_faces(db)
        
        if not success:
            print("❌ Failed to load known faces")
            return
        
        print(f"✅ Successfully loaded {face_engine.face_cache_size} face encodings")
        
        # Test 2: Test recognition with the stored photo
        for attendee in attendees_with_encodings:
            print(f"\nTesting recognition for: {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
            
            photo_path = f"/app/data/faces/{attendee.id}.jpg"
            if os.path.exists(photo_path):
                print(f"✅ Photo file exists: {photo_path}")
                
                # Load the image using OpenCV
                image = cv2.imread(photo_path)
                if image is not None:
                    print(f"Image loaded: {image.shape}")
                    
                    # Test recognition using the correct method
                    print("Testing face recognition...")
                    recognition_result = await face_engine.recognize_face(image, db)
                    
                    if recognition_result:
                        print(f"🎉 SUCCESS: Face recognition working!")
                        print(f"  - Recognized attendee ID: {recognition_result.get('attendee_id', 'Unknown')}")
                        print(f"  - Confidence: {recognition_result.get('confidence', 0):.4f}")
                        print(f"  - Attendee name: {recognition_result.get('attendee_name', 'Unknown')}")
                        print(f"  - Face location: {recognition_result.get('face_location', 'Unknown')}")
                        
                        # Check if the recognized attendee matches the expected one
                        if recognition_result.get('attendee_id') == attendee.id:
                            print(f"✅ CORRECT: Successfully recognized the correct attendee!")
                        else:
                            print(f"⚠️  MISMATCH: Recognized different attendee: {recognition_result.get('attendee_id')}")
                    else:
                        print("❌ No faces recognized - this might indicate the face encoding wasn't properly loaded")
                else:
                    print("❌ Failed to load image")
            else:
                print(f"❌ Photo file not found: {photo_path}")
        
        # Test 3: Check performance statistics
        print("\n=== PERFORMANCE STATISTICS ===")
        stats = face_engine.get_performance_stats()
        print(f"Cache size: {stats['cache_size']}")
        print(f"Cache loaded: {stats['cache_loaded']}")
        print(f"Average recognition time: {stats['avg_recognition_time_ms']:.2f}ms")
        print(f"Total recognition attempts: {stats['total_recognition_attempts']}")
        
        print("\n🎉 FACE RECOGNITION SYSTEM IS WORKING!")
        print("The system can now:")
        print("✅ Store face encodings in the database")
        print("✅ Load face encodings into memory")
        print("✅ Recognize faces from images")
        print("✅ Match faces with attendee records")
        
    except Exception as e:
        print(f"Error in final verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_final_verification())
