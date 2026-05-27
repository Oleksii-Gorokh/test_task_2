from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, Expedition, ExpeditionMember
from app.schemas import ExpeditionCreate, ExpeditionResponse
from app.security import get_current_user
from app.websocket import manager


router = APIRouter(prefix="/expeditions", tags=["expeditions"])

@router.post("", response_model=ExpeditionResponse, status_code=status.HTTP_201_CREATED)
async def create_expedition(
    data: ExpeditionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "chief":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with the role 'chief' can create expeditions"
        )
    
    exp = Expedition(
        title=data.title,
        description=data.description,
        status="draft",
        start_at=data.start_at,
        end_at=data.end_at,
        capacity=data.capacity,
        chief_id=current_user.id
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp

@router.get("", response_model=list[ExpeditionResponse])
async def list_expeditions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "chief":
        result = await db.execute(select(Expedition).where(Expedition.chief_id == current_user.id))
    else:
        result = await db.execute(
            select(Expedition)
            .join(ExpeditionMember, ExpeditionMember.expedition_id == Expedition.id)
            .where(ExpeditionMember.user_id == current_user.id)
        )
    return result.scalars().all()

@router.post("/{id}/ready", response_model=ExpeditionResponse)
async def set_ready(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Expedition).where(Expedition.id == id))
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expedition not found")
    
    if exp.chief_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the chief can manage this expedition")
    
    if exp.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expedition must be in draft status to transition to ready"
        )
    
    exp.status = "ready"
    await db.commit()
    await db.refresh(exp)
    
    await manager.broadcast_expedition_event(
        db, exp.id, "expedition_status", {"status": exp.status}
    )
    return exp

@router.post("/{id}/active", response_model=ExpeditionResponse)
async def set_active(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Expedition).where(Expedition.id == id))
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expedition not found")
    
    if exp.chief_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the chief can manage this expedition")
    
    if exp.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expedition must be in ready status to transition to active"
        )
    
    if exp.start_at > datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start expedition before its start date/time"
        )
    
    result_m = await db.execute(
        select(ExpeditionMember)
        .where(ExpeditionMember.expedition_id == id, ExpeditionMember.state == "confirmed")
    )
    confirmed_members = result_m.scalars().all()
    count = len(confirmed_members)
    
    if count < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expedition needs at least 2 confirmed members to start"
        )
    
    if count > exp.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmed members ({count}) exceed expedition capacity ({exp.capacity})"
        )
    
    member_user_ids = [m.user_id for m in confirmed_members]
    result_active_exps = await db.execute(
        select(ExpeditionMember.user_id)
        .join(Expedition, Expedition.id == ExpeditionMember.expedition_id)
        .where(
            Expedition.status == "active",
            ExpeditionMember.state == "confirmed",
            ExpeditionMember.user_id.in_(member_user_ids),
            Expedition.id != id
        )
    )
    already_active_users = result_active_exps.scalars().all()
    if already_active_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Some confirmed members are already active in another expedition: {already_active_users}"
        )
    
    exp.status = "active"
    await db.commit()
    await db.refresh(exp)
    
    await manager.broadcast_expedition_event(
        db, exp.id, "expedition_status", {"status": exp.status}
    )
    return exp

@router.post("/{id}/finish", response_model=ExpeditionResponse)
async def set_finished(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Expedition).where(Expedition.id == id))
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expedition not found")
    
    if exp.chief_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the chief can manage this expedition")
    
    if exp.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expedition must be in active status to transition to finished"
        )
    
    exp.status = "finished"
    await db.commit()
    await db.refresh(exp)
    
    await manager.broadcast_expedition_event(
        db, exp.id, "expedition_status", {"status": exp.status}
    )
    return exp
