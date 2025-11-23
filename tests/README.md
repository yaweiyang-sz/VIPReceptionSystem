# VIP Reception System - Test Suite

This directory contains all test files organized by category for the VIP Reception System.

## Directory Structure

### `/tests/backend/`
- **Unit tests** for backend components
- Face recognition engine tests
- API endpoint tests
- Database operation tests

### `/tests/frontend/`
- **Frontend tests** (currently empty - add React component tests here)
- Component unit tests
- UI interaction tests

### `/tests/integration/`
- **Integration tests** that test multiple components together
- End-to-end workflow tests
- System integration tests

### `/tests/data/`
- **Data utilities and test data**
- Database population scripts
- Test image files
- Data validation scripts

## Running Tests

### Backend Tests
```bash
cd tests/backend
python test_backend.py
python test_face_encoding.py
```

### Integration Tests
```bash
cd tests/integration
python test_complete_workflow.py
```

### Data Utilities
```bash
cd tests/data
python populate_database.py
python check_attendees.py
```

## Test Categories

### Unit Tests
- `test_backend.py` - Basic API functionality
- `test_face_encoding.py` - Face recognition encoding
- `test_face_upload.py` - Photo upload functionality
- `test_simple_upload.py` - Basic file upload tests

### Integration Tests
- `test_complete_workflow.py` - Full attendee management workflow
- `test_large_dataset.py` - Performance with large datasets
- `test_image_serving.py` - Image serving and display

### Data Utilities
- `populate_database.py` - Populate database with sample data
- `reset_and_populate.py` - Reset and repopulate database
- `check_attendees.py` - Verify attendee data integrity
- `create_test_face.py` - Create test face encodings

## Test Data Files
- `simple_test_image.jpg` - Generic test image
- `test_face.jpg` - Image with clear face for recognition tests
- `test_output.jpg` - Output from face detection tests

## Notes
- All test files have been moved from the root directory to this organized structure
- Update any scripts that reference these files to use the new paths
- Add new tests to the appropriate category folders
