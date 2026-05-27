from typing import Dict, List
from fastapi import WebSocket
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ExpeditionMember, Expedition

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_expedition_event(self, db: AsyncSession, expedition_id: int, event_type: str, data: dict):
        result_exp = await db.execute(select(Expedition).where(Expedition.id == expedition_id))
        exp = result_exp.scalars().first()
        if not exp:
            return

        user_ids = {exp.chief_id}
        result_m = await db.execute(
            select(ExpeditionMember.user_id).where(ExpeditionMember.expedition_id == expedition_id)
        )
        for uid in result_m.scalars().all():
            user_ids.add(uid)

        message = {
            "event": event_type,
            "expedition_id": expedition_id,
            "data": data
        }

        for uid in user_ids:
            if uid in self.active_connections:
                for ws in self.active_connections[uid]:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        pass

manager = ConnectionManager()
