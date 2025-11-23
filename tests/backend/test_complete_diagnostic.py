#!/usr/bin/env python3
"""
Complete diagnostic test for face recognition system
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import face_recognition
from sqlalchemy import text
from app.database import SessionLocal
from app.recognition_engine import FaceRecognitionEngine

async def test_complete_diagnostic():
    """Complete diagnostic test for the face recognition system"""
    db = SessionLocal()
    face_engine = FaceRecognitionEngine()
    
    try:
        print("=== COMPLETE FACE RECOGNITION DIAGNOSTIC ===\n")
        
        # Test 1: Check database state
        print("1. DATABASE CHECK:")
        attendees_with_encodings = db.execute(text("""
            SELECT id, first_name, last_name, face_encoding, face_encoding_version
            FROM attendees 
            WHERE face_encoding IS NOT NULL
        """)).fetchall()
        
        print(f"   Found {len(attendees_with_encodings)} attendees with face encodings")
        for attendee in attendees_with_encodings:
            print(f"   - {attendee.first_name} {attendee.last_name} (ID: {attendee.id}) - Version: {attendee.face_encoding_version}")
        
        # Test 2: Test face encoding loading
        print("\n2. FACE ENCODING LOADING:")
        success = face_engine.load_known_faces(db)
        print(f"   Load success: {success}")
        print(f"   Cache size: {face_engine.face_cache_size}")
        print(f"   Cache loaded: {face_engine.face_cache_loaded}")
        
        # Test 3: Test face detection on stored photo
        print("\n3. FACE DETECTION TEST:")
        for attendee in attendees_with_encodings:
            print(f"\n   Testing attendee: {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
            
            photo_path = f"/app/data/faces/{attendee.id}.jpg"
            if os.path.exists(photo_path):
                print(f"   ✅ Photo file exists: {photo_path}")
                
                # Load image
                image = cv2.imread(photo_path)
                if image is not None:
                    print(f"   Image loaded: {image.shape}")
                    
                    # Test 3a: Direct face_recognition detection
                    print("\n   3a. DIRECT FACE_RECOGNITION DETECTION:")
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Try different detection methods
                    face_locations_hog = face_recognition.face_locations(rgb_image, model="hog")
                    face_locations_cnn = face_recognition.face_locations(rgb_image, model="cnn")
                    
                    print(f"      HOG model found {len(face_locations_hog)} faces")
                    print(f"      CNN model found {len(face_locations_cnn)} faces")
                    
                    if face_locations_hog or face_locations_cnn:
                        face_locations = face_locations_hog if face_locations_hog else face_locations_cnn
                        print(f"      Using {len(face_locations)} face location(s)")
                        
                        # Test encoding
                        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                        print(f"      Generated {len(face_encodings)} face encoding(s)")
                        
                        if face_encodings:
                            # Test recognition engine
                            print("\n   3b. RECOGNITION ENGINE TEST:")
                            recognition_result = await face_engine.recognize_face(image, db)
                            
                            if recognition_result:
                                print(f"      ✅ SUCCESS: Face recognized!")
                                print(f"      - Attendee ID: {recognition_result.get('attendee_id')}")
                                print(f"      - Confidence: {recognition_result.get('confidence'):.4f}")
                                print(f"      - Name: {recognition_result.get('attendee_name')}")
                            else:
                                print("      ❌ Recognition engine failed to recognize face")
                        else:
                            print("      ❌ Failed to generate face encodings")
                    else:
                        print("      ❌ No faces detected in the image")
                        
                        # Try OpenCV detection as fallback
                        print("\n   3c. OPENCV FALLBACK DETECTION:")
                        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                        faces_opencv = face_cascade.detectMultiScale(gray, 1.1, 4)
                        print(f"      OpenCV found {len(faces_opencv)} face(s)")
                        
                else:
                    print("   ❌ Failed to load image")
            else:
                print(f"   ❌ Photo file not found: {photo_path}")
        
        # Test 4: Performance statistics
        print("\n4. PERFORMANCE STATISTICS:")
        stats = face_engine.get_performance_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n=== DIAGNOSTIC SUMMARY ===")
        if face_engine.face_cache_size > 0:
            print("✅ Face encodings are properly stored and loaded")
        else:
            print("❌ No face encodings loaded")
            
        if stats['total_recognition_attempts'] > 0:
            print("✅ Recognition engine is processing images")
        else:
            print("❌ Recognition engine not processing images")
            
        print("\n🎉 DIAGNOSTIC COMPLETE!")
        
    except Exception as e:
        print(f"Error in diagnostic test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_complete_diagnostic())
