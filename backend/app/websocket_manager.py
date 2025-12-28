from fastapi import WebSocket
from typing import List, Dict, Any
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            "connected_at": asyncio.get_event_loop().time(),
            "last_activity": asyncio.get_event_loop().time()
        }
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_data:
            del self.connection_data[websocket]
        print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
            self.connection_data[websocket]["last_activity"] = asyncio.get_event_loop().time()
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        message_json = json.dumps(message, default=str)
        
        # print(f"DEBUG: Broadcasting message to {len(self.active_connections)} connections: {message.get('type', 'unknown')}")
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
                self.connection_data[connection]["last_activity"] = asyncio.get_event_loop().time()
                # print(f"DEBUG: Successfully sent message to connection")
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_group(self, message: Dict[str, Any], group: str):
        """Broadcast message to a specific group of clients"""
        # This could be extended to support different client groups
        # For now, broadcast to all
        await self.broadcast(message)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        now = asyncio.get_event_loop().time()
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "connected_for": now - data["connected_at"],
                    "last_activity": now - data["last_activity"]
                }
                for data in self.connection_data.values()
            ]
        }

# Global instance
manager = ConnectionManager()
