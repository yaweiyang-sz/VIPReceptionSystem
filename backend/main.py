from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os
import json
import asyncio

from app.database import engine, Base
from app.websocket_manager import ConnectionManager

# Import routers
from app.routes import cameras, recognition, attendees, admin

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("VIP Reception System starting up...")
    yield
    # Shutdown
    print("VIP Reception System shutting down...")

app = FastAPI(
    title="VIP Reception System",
    description="Visitor recognition system for aviation interior exhibition",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager
manager = ConnectionManager()

# Include routers
app.include_router(cameras.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(recognition.router, prefix="/api/recognition", tags=["recognition"])
app.include_router(attendees.router, prefix="/api/attendees", tags=["attendees"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

@app.get("/")
async def root():
    return {"message": "VIP Reception System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "VIP Reception System"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/api/ws/recognition")
async def recognition_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time recognition updates"""
    print("DEBUG: Recognition WebSocket connection attempt")
    await manager.connect(websocket)
    try:
        # Send initial connection confirmation
        print("DEBUG: Recognition WebSocket connected, sending confirmation")
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Connected to recognition updates",
            "timestamp": asyncio.get_event_loop().time()
        }))
        
        while True:
            try:
                print("DEBUG: Recognition WebSocket waiting for message")
                data = await websocket.receive_text()
                print(f"DEBUG: Recognition WebSocket received: {data}")
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                elif message.get("type") == "subscribe":
                    # Client wants to subscribe to a specific camera's recognition updates
                    camera_id = message.get("camera_id")
                    # Store subscription info (simplified - in production you'd want to track subscriptions per connection)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "camera_id": camera_id,
                        "message": f"Subscribed to recognition updates for camera {camera_id}"
                    }))
                    
            except WebSocketDisconnect:
                print("DEBUG: Recognition WebSocket disconnect exception")
                break
            except Exception as e:
                print(f"Recognition WebSocket error: {e}")
                # Continue the loop to keep connection alive
                await asyncio.sleep(0.1)
                
    except WebSocketDisconnect:
        print("Recognition WebSocket disconnected")
    except Exception as e:
        print(f"Recognition WebSocket connection error: {e}")
    finally:
        manager.disconnect(websocket)
        print("Recognition WebSocket connection closed")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
