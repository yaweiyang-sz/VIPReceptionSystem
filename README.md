# VIP Reception System - Aviation Interior Exhibition

A web-based visitor recognition system that identifies attendees via facial recognition OR QR codes and displays their information.

## Features
- Dual identification methods (face recognition + QR codes)
- Web-based application for cross-device compatibility
- Containerized deployment (Docker)
- Flexible camera configuration
- Real-time visitor information display
- Database-backed attendee management
- Admin dashboard for system management
- Real-time WebSocket notifications

## Architecture
- **Frontend**: React.js with Vite for responsive web interface
- **Backend**: Python FastAPI for RESTful API services
- **Database**: PostgreSQL for attendee data storage
- **Real-time**: WebSocket for live updates and notifications
- **Recognition**: OpenCV + face_recognition + pyzbar for dual recognition

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Deployment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd VIPReceptionSystem
   ```

2. **Start the system**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Environment Configuration

Copy the example environment file and modify as needed:
```bash
cp backend/.env.example backend/.env
```

### Troubleshooting

If you encounter port conflicts:
- Port 80 may be in use by other services
- The nginx service is commented out in docker-compose.yml by default
- For production, uncomment and configure nginx with appropriate ports

If Docker build fails due to CMake issues:
- The Dockerfile now includes CMake and build-essential packages
- This resolves dlib compilation issues

## Project Structure
```
VIPReceptionSystem/
├── frontend/                 # React.js frontend application
│   ├── src/
│   │   ├── App.jsx          # Main application component
│   │   ├── main.jsx         # React entry point
│   │   └── index.css        # Global styles
│   ├── package.json         # Frontend dependencies
│   ├── vite.config.js       # Vite configuration
│   └── index.html           # HTML template
├── backend/                  # FastAPI backend services
│   ├── app/
│   │   ├── routes/          # API route handlers
│   │   │   ├── cameras.py   # Camera management
│   │   │   ├── recognition.py # Recognition endpoints
│   │   │   ├── attendees.py # Attendee management
│   │   │   └── admin.py     # Admin dashboard
│   │   ├── database.py      # Database models and configuration
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── websocket_manager.py # WebSocket connection management
│   │   └── recognition_engine.py # Face and QR recognition logic
│   ├── database/
│   │   └── init.sql         # Database initialization script
│   ├── requirements.txt     # Python dependencies
│   ├── main.py             # FastAPI application entry point
│   └── .env.example        # Environment variables template
├── docker-compose.yml       # Multi-container orchestration
├── Dockerfile              # Backend container definition
├── Dockerfile.frontend     # Frontend container definition
├── .gitignore             # Git ignore rules
└── README.md              # Project documentation
```

## API Endpoints

### Cameras
- `GET /api/cameras/` - List all cameras
- `POST /api/cameras/` - Create new camera
- `GET /api/cameras/{id}` - Get camera details
- `PUT /api/cameras/{id}` - Update camera settings
- `DELETE /api/cameras/{id}` - Delete camera

### Recognition
- `POST /api/recognition/face` - Face recognition
- `POST /api/recognition/qr` - QR code recognition
- `POST /api/recognition/auto` - Automatic recognition (face + QR)

### Attendees
- `GET /api/attendees/` - List attendees
- `POST /api/attendees/` - Create attendee
- `PUT /api/attendees/{id}` - Update attendee
- `POST /api/attendees/{id}/upload-photo` - Upload face photo

### Admin
- `GET /api/admin/dashboard/stats` - Dashboard statistics
- `GET /api/admin/system/status` - System health check
- `GET /api/admin/reports/visits` - Visit reports

### WebSocket
- `ws://localhost:8000/ws` - Real-time notifications

## Configuration

### Camera Setup
The system supports multiple camera sources:
- Device IDs (0, 1, 2, etc.)
- RTSP streams (rtsp://...)
- HTTP streams (http://...)

### Recognition Settings
- Face recognition confidence threshold: 0.6
- Auto-recognition enabled by default
- Maximum file size: 5MB

## Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

## Production Deployment

### Using Docker Compose (Recommended)
```bash
docker-compose -f docker-compose.yml up -d
```

### Manual Deployment
1. Set up PostgreSQL database
2. Configure environment variables
3. Build and run backend
4. Build and serve frontend
5. Configure reverse proxy (nginx)

## Troubleshooting

### Common Issues

1. **Camera not accessible**
   - Check camera permissions
   - Verify camera source URL/ID
   - Ensure camera is not being used by another application

2. **Face recognition not working**
   - Verify face_recognition library installation
   - Check image quality and face visibility
   - Ensure proper lighting conditions

3. **Database connection issues**
   - Verify PostgreSQL is running
   - Check DATABASE_URL environment variable
   - Ensure database user has proper permissions

### Logs
- Backend logs: Check Docker container logs
- Database logs: PostgreSQL logs in container
- Frontend logs: Browser developer console

## Security Considerations

- Change default passwords in production
- Use HTTPS in production
- Configure proper CORS origins
- Secure database connections
- Regular security updates

## License

This project is licensed under the MIT License.

## Support

For issues and feature requests, please create an issue in the project repository.
