from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = Field(..., pattern="^(chief|member)$")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class ExpeditionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_at: datetime
    end_at: Optional[datetime] = None
    capacity: int = Field(..., gt=0)

class ExpeditionResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    start_at: datetime
    end_at: Optional[datetime]
    capacity: int
    chief_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ExpeditionMemberResponse(BaseModel):
    id: int
    expedition_id: int
    user_id: int
    state: str
    invited_at: datetime
    confirmed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
