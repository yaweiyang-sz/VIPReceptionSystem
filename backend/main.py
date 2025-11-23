from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
