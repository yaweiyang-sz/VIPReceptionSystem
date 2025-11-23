#!/usr/bin/env python3
"""
Fix face recognition by using OpenCV for detection and face_recognition for encoding
"""

import sys
import os
import asyncio
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import face_recognition
from app.database import SessionLocal, Attendee
from app.recognition_engine import FaceRecognitionEngine

async def fix_face_encodings():
    """Fix face encodings by using OpenCV for detection first"""
    db = SessionLocal()
    face_engine = FaceRecognitionEngine()
    
    try:
        # Get attendees with photos but no face encodings
        attendees_with_photos = db.query(Attendee).filter(
            Attendee.photo_url.isnot(None),
            Attendee.photo_url != '',
            Attendee.face_encoding.is_(None)
        ).all()
        
        print(f"Found {len(attendees_with_photos)} attendees with photos but no face encodings")
        
        for attendee in attendees_with_photos:
            print(f"\nProcessing attendee: {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
            
            photo_path = f"/app/data/faces/{attendee.id}.jpg"
            if os.path.exists(photo_path):
                print(f"✅ Photo file exists: {photo_path}")
                
                # Load image
                image = cv2.imread(photo_path)
                if image is not None:
                    print(f"Image loaded: {image.shape}")
                    
                    # Method 1: Try OpenCV face detection first
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    faces_opencv = face_cascade.detectMultiScale(gray, 1.1, 4)
                    
                    if len(faces_opencv) > 0:
                        print(f"✅ OpenCV found {len(faces_opencv)} face(s)")
                        
                        # Convert OpenCV face locations to face_recognition format
                        face_locations = []
                        for (x, y, w, h) in faces_opencv:
                            # Convert from (x, y, w, h) to (top, right, bottom, left)
                            top = y
                            right = x + w
                            bottom = y + h
                            left = x
                            face_locations.append((top, right, bottom, left))
                        
                        # Now use face_recognition to encode the detected faces
                        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        
                        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                        
                        if len(face_encodings) > 0:
                            print(f"✅ Successfully encoded {len(face_encodings)} face(s)")
                            
                            # Use the first face encoding (assuming one face per attendee)
                            face_encoding = face_encodings[0]
                            
                            # Convert numpy array to string for storage
                            encoding_str = ','.join(map(str, face_encoding))
                            
                            # Update the attendee record
                            attendee.face_encoding = encoding_str
                            attendee.face_encoding_version = 'v1'
                            attendee.face_encoding_quality = 'standard'
                            attendee.face_encoding_created = datetime.now()
                            
                            db.commit()
                            print(f"✅ Face encoding saved for attendee {attendee.id}")
                        else:
                            print("❌ Failed to encode detected faces")
                    else:
                        print("❌ No faces detected by OpenCV either")
                        
                else:
                    print("❌ Failed to load image")
            else:
                print(f"❌ Photo file not found: {photo_path}")
                
    except Exception as e:
        print(f"Error fixing face encodings: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_face_encodings())
