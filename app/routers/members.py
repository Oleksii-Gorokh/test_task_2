from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, Expedition, ExpeditionMember
from app.schemas import ExpeditionMemberResponse
from app.security import get_current_user
from app.websocket import manager
from pydantic import BaseModel


router = APIRouter(tags=["members"])

class InviteRequest(BaseModel):
    user_id: int

@router.post("/expeditions/{expedition_id}/invite", response_model=ExpeditionMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    expedition_id: int,
    data: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result_exp = await db.execute(select(Expedition).where(Expedition.id == expedition_id))
    exp = result_exp.scalars().first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expedition not found")
        
    if exp.chief_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the chief can invite members")
        
    if exp.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only invite members when expedition is in draft status")
        
    result_user = await db.execute(select(User).where(User.id == data.user_id))
    target_user = result_user.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    if target_user.role != "member":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only users with the role 'member' can be invited")
        
    result_m = await db.execute(
        select(ExpeditionMember)
        .where(ExpeditionMember.expedition_id == expedition_id, ExpeditionMember.user_id == data.user_id)
    )
    existing_member = result_m.scalars().first()
    if existing_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already invited or confirmed for this expedition")
        
    member = ExpeditionMember(
        expedition_id=expedition_id,
        user_id=data.user_id,
        state="invited"
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    
    await manager.broadcast_expedition_event(
        db, expedition_id, "member_invited", {
            "id": member.id,
            "user_id": member.user_id,
            "state": member.state
        }
    )
    return member

@router.post("/members/{id}/confirm", response_model=ExpeditionMemberResponse)
async def confirm_member(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result_m = await db.execute(select(ExpeditionMember).where(ExpeditionMember.id == id))
    member = result_m.scalars().first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        
    if member.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the invited user can confirm participation")
        
    if member.state != "invited":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is already confirmed or in an invalid state")
        
    member.state = "confirmed"
    member.confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(member)
    
    await manager.broadcast_expedition_event(
        db, member.expedition_id, "member_confirmed", {
            "id": member.id,
            "user_id": member.user_id,
            "state": member.state
        }
    )
    return member
