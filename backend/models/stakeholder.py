import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Date, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Stakeholder(Base):
    __tablename__ = "stakeholders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    
    # Exactly 2 roles: 'sme' or 'receiver'
    role = Column(String(50), default="sme")  # "sme", "receiver"
    
    # Replaced domain mapping with Levels (L1/L2/L3)
    level = Column(String(20), default="L1")  # "L1", "L2", "L3"
    primary_domain = Column(String(100), default="General", nullable=True) # legacy compat
    assigned_node_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    transition = relationship("Transition", back_populates="stakeholders")
    leaves = relationship("StakeholderLeave", back_populates="stakeholder", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="stakeholder", cascade="all, delete-orphan")


class StakeholderLeave(Base):
    __tablename__ = "stakeholder_leaves"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    stakeholder_id = Column(String(36), ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String(255), default="Annual Leave")
    created_at = Column(DateTime, default=datetime.utcnow)

    stakeholder = relationship("Stakeholder", back_populates="leaves")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    stakeholder_id = Column(String(36), ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False)
    
    # Matching Outlook standard CSV exports
    subject = Column(String(255), default="Busy")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_all_day = Column(Boolean, default=False)
    has_reminder = Column(Boolean, default=False)
    imported_at = Column(DateTime, default=datetime.utcnow)

    stakeholder = relationship("Stakeholder", back_populates="calendar_events")
