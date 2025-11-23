import requests
import os

def test_photo_upload():
    """Test photo upload functionality"""
    print("Testing Photo Upload...")
    
    # First, let's create a simple test image
    test_image_path = "simple_test_image.jpg"
    
    # Create a simple colored image using PIL or use an existing test image
    try:
        from PIL import Image
        # Create a simple red image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        print(f"Created test image: {test_image_path}")
    except ImportError:
        print("PIL not available, trying to use existing test image...")
        if not os.path.exists(test_image_path):
            print("No test image available. Please create a test image manually.")
            return
    
    # Test with attendee ID 1 (John Smith)
    attendee_id = 1
    
    try:
        with open(test_image_path, 'rb') as f:
            files = {'file': ('test_photo.jpg', f, 'image/jpeg')}
            response = requests.post(
                f'http://localhost:8000/api/attendees/{attendee_id}/upload-photo',
                files=files
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Content: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Upload Result: {result}")
            else:
                print(f"Upload failed with status {response.status_code}")
                
    except Exception as e:
        print(f"Error during upload: {e}")

if __name__ == "__main__":
    test_photo_upload()
