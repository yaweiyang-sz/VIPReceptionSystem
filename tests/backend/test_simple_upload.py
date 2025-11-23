import requests
import os

def test_simple_upload():
    """Test photo upload with a simple approach"""
    print("Testing Simple Photo Upload...")
    
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
            print(f"Response Headers: {response.headers}")
            print(f"Response Content: {response.text}")
            
    except Exception as e:
        print(f"Error during upload: {e}")

def check_photo_endpoint():
    """Check if the photo endpoint works"""
    print("\nChecking Photo Endpoint...")
    attendee_id = 1
    
    try:
        response = requests.get(f'http://localhost:8000/api/attendees/{attendee_id}/photo')
        print(f"Photo Endpoint Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Photo endpoint is working!")
        else:
            print(f"❌ Photo endpoint failed: {response.text}")
    except Exception as e:
        print(f"Error checking photo endpoint: {e}")

if __name__ == "__main__":
    test_simple_upload()
    check_photo_endpoint()
