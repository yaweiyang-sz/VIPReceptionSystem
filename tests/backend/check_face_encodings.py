#!/usr/bin/env python3
"""
Simple script to check if attendees have face encodings in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, Attendee

def check_face_encodings():
    """Check how many attendees have face encodings"""
    db = SessionLocal()
    try:
        # Count total attendees
        total_attendees = db.query(Attendee).count()
        
        # Count attendees with face encodings
        attendees_with_face = db.query(Attendee).filter(
            Attendee.face_encoding.isnot(None),
            Attendee.face_encoding != ''
        ).count()
        
        # Get some sample attendees with face encodings
        sample_attendees = db.query(Attendee).filter(
            Attendee.face_encoding.isnot(None),
            Attendee.face_encoding != ''
        ).limit(5).all()
        
        print(f"Total attendees: {total_attendees}")
        print(f"Attendees with face encodings: {attendees_with_face}")
        print(f"Percentage with face encodings: {(attendees_with_face/total_attendees)*100:.1f}%")
        
        if sample_attendees:
            print("\nSample attendees with face encodings:")
            for attendee in sample_attendees:
                print(f"  - {attendee.first_name} {attendee.last_name} (ID: {attendee.id})")
                print(f"    Face encoding length: {len(attendee.face_encoding) if attendee.face_encoding else 0} chars")
        else:
            print("\nNo attendees found with face encodings!")
            
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_face_encodings()
