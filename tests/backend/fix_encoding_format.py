#!/usr/bin/env python3
"""
Fix face encoding format to match what the recognition engine expects
"""

import sys
import os
import asyncio
import base64
import pickle
import numpy as np
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, Attendee

async def fix_encoding_format():
    """Fix face encoding format from comma-separated string to base64"""
    db = SessionLocal()
    
    try:
        # Get attendees with face encodings
        attendees_with_encodings = db.query(Attendee).filter(
            Attendee.face_encoding.isnot(None),
            Attendee.face_encoding != ''
        ).all()
        
        print(f"Found {len(attendees_with_encodings)} attendees with face encodings to fix")
        
        for attendee in attendees_with_encodings:
            print(f"\nFixing encoding for: {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
            
            current_encoding = attendee.face_encoding
            print(f"Current encoding length: {len(current_encoding)}")
            print(f"First 100 chars: {current_encoding[:100]}")
            
            try:
                # Try to parse as comma-separated string
                if ',' in current_encoding:
                    print("Detected comma-separated format, converting to base64...")
                    
                    # Parse the comma-separated values
                    encoding_array = np.fromstring(current_encoding, sep=',')
                    print(f"Parsed array shape: {encoding_array.shape}")
                    
                    # Convert to base64 format expected by recognition engine
                    encoding_bytes = pickle.dumps(encoding_array)
                    encoding_b64 = base64.b64encode(encoding_bytes).decode('utf-8')
                    
                    # Update the attendee record
                    attendee.face_encoding = encoding_b64
                    attendee.face_encoding_version = 'v2_base64'
                    attendee.face_encoding_created = datetime.now()
                    
                    db.commit()
                    print(f"✅ Successfully converted encoding to base64 format")
                    print(f"New encoding length: {len(encoding_b64)}")
                    
                else:
                    print("Encoding format not recognized, skipping...")
                    
            except Exception as e:
                print(f"❌ Error converting encoding: {e}")
                continue
                
        print(f"\n✅ Successfully fixed {len(attendees_with_encodings)} face encodings")
        
    except Exception as e:
        print(f"Error fixing encoding format: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_encoding_format())
