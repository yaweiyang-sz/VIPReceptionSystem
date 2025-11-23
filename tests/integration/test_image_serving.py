import requests

def test_image_serving():
    print("Testing image serving from backend...")
    
    # Test attendee 1 photo
    url = "http://localhost:8000/api/attendees/1/photo"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {len(response.content)}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Image serving is working correctly!")
            # Save a copy to verify it's a valid image
            with open("test_output.jpg", "wb") as f:
                f.write(response.content)
            print("✅ Image saved as test_output.jpg")
        else:
            print("❌ Image serving failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_image_serving()
