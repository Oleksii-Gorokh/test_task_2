from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import SECRET_KEY, ALGORITHM
from app.database import Base, engine, SessionLocal, get_db
from app.models import User
from app.routers import auth, expeditions, members
from app.websocket import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Expedition Management API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(expeditions.router)
app.include_router(members.router)

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            await websocket.close(code=4008)
            return
    except Exception:
        await websocket.close(code=4008)
        return

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        await websocket.close(code=4008)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
