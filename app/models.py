from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    expeditions_led = relationship("Expedition", back_populates="chief", cascade="all, delete-orphan")
    memberships = relationship("ExpeditionMember", back_populates="user", cascade="all, delete-orphan")

class Expedition(Base):
    __tablename__ = "expeditions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="draft", nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    capacity = Column(Integer, nullable=False)
    chief_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    chief = relationship("User", back_populates="expeditions_led")
    members = relationship("ExpeditionMember", back_populates="expedition", cascade="all, delete-orphan")

class ExpeditionMember(Base):
    __tablename__ = "expedition_members"

    id = Column(Integer, primary_key=True, index=True)
    expedition_id = Column(Integer, ForeignKey("expeditions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    state = Column(String, default="invited", nullable=False)
    invited_at = Column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime, nullable=True)

    expedition = relationship("Expedition", back_populates="members")
    user = relationship("User", back_populates="memberships")
