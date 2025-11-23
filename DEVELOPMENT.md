# VIP Reception System - Development Guide

This guide provides instructions for setting up the development environment for the VIP Reception System.

## Prerequisites

### Required Software
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Git

### Optional Software
- Docker & Docker Compose (for containerized development)

## Development Setup

### Option 1: Docker Development (Recommended)

1. **Start the development environment**
   ```bash
   docker-compose up --build
   ```

2. **Access the services**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Database: localhost:5432

### Option 2: Manual Development Setup

#### Backend Setup

1. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL**
   - Install PostgreSQL 15+
   - Create database: `vip_reception`
   - Create user: `vip_user` with password `vip_password`
   - Or update `DATABASE_URL` in environment variables

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run the backend**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Run the frontend**
   ```bash
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Testing

### Backend Tests
```bash
cd backend
python ../test_backend.py
```

### API Testing
Once the backend is running, you can test the API endpoints:

1. **Check health endpoint**
   ```bash
   curl http://localhost:8000/health
   ```

2. **List cameras**
   ```bash
   curl http://localhost:8000/api/cameras/
   ```

3. **View API documentation**
   - Open http://localhost:8000/docs in your browser

## Development Workflow

### Adding New Features

1. **Backend (Python/FastAPI)**
   - Add new models in `app/database.py`
   - Create schemas in `app/schemas.py`
   - Implement routes in `app/routes/`
   - Update recognition logic in `app/recognition_engine.py`

2. **Frontend (React)**
   - Add new components in `frontend/src/`
   - Update API calls in `frontend/src/App.jsx`
   - Modify styles in `frontend/src/index.css`

### Database Migrations

For database schema changes:

1. **Generate migration**
   ```bash
   alembic revision --autogenerate -m "description"
   ```

2. **Apply migration**
   ```bash
   alembic upgrade head
   ```

## Project Structure Overview

### Backend Architecture
```
backend/
├── app/
│   ├── routes/           # API endpoints
│   ├── database.py       # Database models & connection
│   ├── schemas.py        # Pydantic validation schemas
│   ├── websocket_manager.py # WebSocket connections
│   └── recognition_engine.py # Face & QR recognition
├── database/
│   └── init.sql         # Initial database setup
└── main.py              # FastAPI application
```

### Frontend Architecture
```
frontend/
├── src/
│   ├── App.jsx          # Main application component
│   ├── main.jsx         # React entry point
│   └── index.css        # Global styles
├── package.json         # Dependencies & scripts
└── vite.config.js       # Build configuration
```

## API Development

### Adding New Endpoints

1. **Create route file** in `app/routes/`
2. **Define schemas** in `app/schemas.py`
3. **Import and include** in `main.py`
4. **Test** using the auto-generated docs

Example route structure:
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_items():
    return {"items": []}
```

## Recognition Engine Development

### Face Recognition
- Uses `face_recognition` library
- Encodes faces as base64 strings in database
- Configurable confidence threshold

### QR Code Recognition
- Uses `pyzbar` library
- Supports standard QR code formats
- Returns decoded string data

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env file
   - Verify database user permissions

2. **Import Errors**
   - Activate virtual environment
   - Run `pip install -r requirements.txt`
   - Check Python path

3. **Camera Access Issues**
   - Verify camera permissions
   - Check camera source URL/ID
   - Ensure camera is not in use

4. **Frontend Build Errors**
   - Run `npm install`
   - Clear node_modules and reinstall
   - Check Node.js version compatibility

### Debug Mode

Enable debug mode by setting:
```bash
DEBUG=true
```

This provides detailed error messages and stack traces.

## Deployment Preparation

### Production Checklist
- [ ] Update environment variables for production
- [ ] Set strong SECRET_KEY
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS
- [ ] Set up proper logging
- [ ] Configure database backups
- [ ] Test recognition accuracy
- [ ] Verify camera compatibility

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For development issues:
1. Check the troubleshooting section
2. Review API documentation
3. Check existing issues
4. Create a new issue with details
