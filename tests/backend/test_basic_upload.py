import requests
import os

def test_basic_upload():
    """Test basic photo upload without face recognition"""
    print("Testing Basic Photo Upload (No Face Recognition)...")
    
    # Use the existing test face image
    test_image_path = "test_face.jpg"
    if not os.path.exists(test_image_path):
        print(f"Test image not found: {test_image_path}")
        return
    
    # Test with attendee ID 1 (John Smith)
    attendee_id = 1
    
    try:
        with open(test_image_path, 'rb') as f:
            files = {'file': ('test_face.jpg', f, 'image/jpeg')}
            response = requests.post(
                f'http://localhost:8000/api/attendees/{attendee_id}/upload-photo',
                files=files
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Content: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful: {result}")
                
                # Check if photo URL was set
                check_response = requests.get(f'http://localhost:8000/api/attendees/{attendee_id}')
                if check_response.status_code == 200:
                    attendee = check_response.json()
                    print(f"✅ Attendee updated:")
                    print(f"   - Photo URL: {attendee.get('photo_url', 'None')}")
                    print(f"   - Has Encoding: {bool(attendee.get('face_encoding'))}")
                    
                    # Try to access the photo
                    photo_response = requests.get(f'http://localhost:8000/api/attendees/{attendee_id}/photo')
                    print(f"Photo endpoint status: {photo_response.status_code}")
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                
    except Exception as e:
        print(f"Error during upload: {e}")

if __name__ == "__main__":
    test_basic_upload()
