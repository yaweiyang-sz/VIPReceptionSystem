#!/usr/bin/env python3
"""
Test the complete face recognition workflow
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

async def test_recognition_workflow():
    """Test the complete face recognition workflow"""
    db = SessionLocal()
    face_engine = FaceRecognitionEngine()
    
    try:
        print("=== Testing Face Recognition Workflow ===\n")
        
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
        
        # Load the known face encodings
        known_face_encodings = []
        known_attendee_ids = []
        
        for attendee in attendees_with_encodings:
            encoding_str = attendee.face_encoding
            if encoding_str:
                try:
                    # Convert string back to numpy array
                    encoding = np.fromstring(encoding_str, sep=',')
                    known_face_encodings.append(encoding)
                    known_attendee_ids.append(attendee.id)
                    print(f"✅ Loaded face encoding for {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
                except Exception as e:
                    print(f"❌ Failed to load encoding for attendee {attendee.id}: {e}")
        
        if not known_face_encodings:
            print("❌ No valid face encodings loaded")
            return
        
        print(f"\n✅ Successfully loaded {len(known_face_encodings)} face encodings")
        
        # Test 2: Try to recognize the same face from the stored photo
        print("\n=== Testing Face Recognition ===\n")
        
        for attendee_id in known_attendee_ids:
            print(f"Testing recognition for attendee ID: {attendee_id}")
            
            photo_path = f"/app/data/faces/{attendee_id}.jpg"
            if os.path.exists(photo_path):
                print(f"✅ Photo file exists: {photo_path}")
                
                # Load the image
                image = cv2.imread(photo_path)
                if image is not None:
                    print(f"Image loaded: {image.shape}")
                    
                    # Convert to RGB for face recognition
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Find faces in the image
                    face_locations = face_engine._find_faces(rgb_image)
                    
                    if len(face_locations) > 0:
                        print(f"✅ Found {len(face_locations)} face(s) in the image")
                        
                        # Encode the faces
                        face_encodings = face_engine._encode_faces(rgb_image, face_locations)
                        
                        if len(face_encodings) > 0:
                            print(f"✅ Encoded {len(face_encodings)} face(s)")
                            
                            # Try to match with known encodings
                            for face_encoding in face_encodings:
                                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                                
                                if True in matches:
                                    first_match_index = matches.index(True)
                                    matched_attendee_id = known_attendee_ids[first_match_index]
                                    print(f"🎉 SUCCESS: Face matched with attendee ID: {matched_attendee_id}")
                                    
                                    # Calculate face distance
                                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                                    best_match_index = np.argmin(face_distances)
                                    best_distance = face_distances[best_match_index]
                                    
                                    print(f"   Face distance: {best_distance:.4f}")
                                    print(f"   Match confidence: {(1 - best_distance) * 100:.2f}%")
                                    
                                    if best_distance < 0.6:  # Standard threshold for face recognition
                                        print("   ✅ Match is confident!")
                                    else:
                                        print("   ⚠️  Match is weak")
                                else:
                                    print("❌ No match found")
                        else:
                            print("❌ Failed to encode faces")
                    else:
                        print("❌ No faces found in the image")
                else:
                    print("❌ Failed to load image")
            else:
                print(f"❌ Photo file not found: {photo_path}")
        
        print("\n=== Testing Real-time Recognition Simulation ===\n")
        
        # Test 3: Simulate real-time recognition with the recognition engine
        print("Testing real-time recognition with FaceRecognitionEngine...")
        
        for attendee_id in known_attendee_ids:
            photo_path = f"/app/data/faces/{attendee_id}.jpg"
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    image_data = f.read()
                
                print(f"\nTesting recognition for attendee {attendee_id}...")
                recognition_result = await face_engine.recognize_faces(image_data)
                
                if recognition_result:
                    print(f"✅ Recognition successful! Found {len(recognition_result)} face(s)")
                    for result in recognition_result:
                        print(f"  - Attendee ID: {result.get('attendee_id', 'Unknown')}")
                        print(f"  - Confidence: {result.get('confidence', 0):.4f}")
                        print(f"  - Face location: {result.get('face_location', 'Unknown')}")
                else:
                    print("❌ No faces recognized")
        
        print("\n🎉 Face recognition workflow test completed successfully!")
        
    except Exception as e:
        print(f"Error testing recognition workflow: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_recognition_workflow())
