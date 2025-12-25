# VIP Reception Algorithm Service

A separate Docker container service for face recognition algorithms in the VIP Reception System.

## Overview

This service provides RESTful APIs for:
1. **Face Encoding**: Encode faces from images (called from `encode_face` function in `recognition_engine.py`)
2. **Face Recognition**: Recognize VIPs from camera frames (called from `camera.py` each loop)

## Architecture

- **FastAPI** web framework
- **face-recognition** library (dlib ResNet model)
- **Redis** for caching face encodings
- **PostgreSQL** database connection for attendee data
- **Docker** container for isolation

## API Endpoints

### 1. Health Check
```
GET /health
```
Returns service health status.

### 2. Model Status
```
GET /api/v1/model/status
```
Returns current model status (loaded faces count, last update).

### 3. Encode Face
```
POST /api/v1/encode
```
Encodes faces from an image. Called from `recognition_engine.py` when adding new attendees.

**Parameters:**
- `image`: Image file (multipart/form-data)
- `attendee_id` (optional): Attendee ID to associate with encoding
- `metadata` (optional): JSON metadata for the attendee

**Response:**
```json
{
  "success": true,
  "encodings": [...],
  "num_faces": 1,
  "model_updated": true
}
```

### 4. Recognize VIP
```
POST /api/v1/recognize
```
Recognizes VIPs from an image frame. Called from `camera.py` each loop.

**Parameters:**
- `image`: Image file (multipart/form-data)

**Response:**
```json
{
  "success": true,
  "recognition": {
    "attendee_id": 1,
    "full_name": "John Doe",
    "confidence": 0.85,
    "is_vip": true,
    "company": "Acme Inc",
    "position": "CEO",
    "face_location": [top, right, bottom, left]
  }
}
```

### 5. Update Model
```
POST /api/v1/model/update
```
Forces reload of face encodings from database.

## Integration with Main System

### Backend Integration
The main backend service (`recognition_engine.py`) has been updated to:
1. Use environment variable `ALGORITHM_SERVICE_URL` to connect to this service
2. Fall back to local face recognition if algorithm service is unavailable
3. Call `/api/v1/encode` when encoding faces
4. Call `/api/v1/recognize` when recognizing faces from camera streams

### Docker Compose
The service is included in `docker-compose.yml` with:
- **algorithm**: Algorithm service container (port 8001)
- **redis**: Redis cache for face encodings
- Updated backend service with `ALGORITHM_SERVICE_URL` environment variable

## Setup and Deployment

### 1. Build and Start
```bash
# From project root
docker-compose up --build
```

### 2. Service URLs
- **Algorithm Service**: http://localhost:8001
- **Main Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432

### 3. Testing the Service
```bash
# Run the integration test
python test_algorithm_service.py
```

## Model Details

The service uses the `face-recognition` Python library which implements:
- **Face Detection**: HOG (Histogram of Oriented Gradients) algorithm
- **Face Encoding**: ResNet model trained on 3 million faces
- **Face Comparison**: Euclidean distance with confidence threshold

### Performance Considerations
- Face encodings are cached in Redis for faster recognition
- Model loads all known faces from database on startup
- Supports incremental updates when new attendees are added
- Configurable confidence threshold (default: 60%)

## Monitoring

### Health Checks
- Service health: `GET /health`
- Model status: `GET /api/v1/model/status`

### Logging
- All API calls are logged with timing information
- Recognition results include confidence scores
- Errors are logged with stack traces for debugging

## Troubleshooting

### Common Issues

1. **Service not starting**
   - Check Docker logs: `docker-compose logs algorithm`
   - Verify dependencies: `face-recognition` requires dlib which needs build tools

2. **Face recognition not working**
   - Check if faces are encoded in database
   - Verify Redis is running and accessible
   - Check model status endpoint

3. **High latency**
   - Consider reducing image resolution before sending to algorithm service
   - Enable Redis caching for face encodings
   - Adjust recognition frequency in camera processing

### Debugging
```bash
# Check algorithm service logs
docker-compose logs -f algorithm

# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Test API directly
curl http://localhost:8001/health
```

## Future Enhancements

1. **Multiple Models**: Support for different face recognition models
2. **GPU Acceleration**: CUDA support for faster processing
3. **Batch Processing**: Process multiple frames simultaneously
4. **Model Versioning**: Support for different encoding versions
5. **Metrics Export**: Prometheus metrics for monitoring
