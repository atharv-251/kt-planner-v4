import uuid
from datetime import datetime, date, time
from sqlalchemy import Column, String, Integer, Float, Date, Time, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class KTSession(Base):
    __tablename__ = "kt_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False)
    sme_id = Column(String(36), ForeignKey("stakeholders.id", ondelete="SET NULL"), nullable=True)
    receiver_id = Column(String(36), ForeignKey("stakeholders.id", ondelete="SET NULL"), nullable=True)

    session_title = Column(String(255), nullable=False)
    level = Column(String(20), default="L1")  # L1, L2, L3
    duration_hours = Column(Float, default=2.0)
    scheduled_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    delivery_mode = Column(String(50), default="workshop")  # workshop, hands_on, shadowing, reverse_shadowing
    status = Column(String(50), default="proposed")  # proposed, confirmed, completed, rescheduled
    conflict_flags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transition = relationship("Transition", back_populates="sessions")
    node = relationship("KnowledgeNode", back_populates="sessions")
    sme = relationship("Stakeholder", foreign_keys=[sme_id])
    receiver = relationship("Stakeholder", foreign_keys=[receiver_id])
