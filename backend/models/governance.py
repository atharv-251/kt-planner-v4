import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class PlanPatch(Base):
    __tablename__ = "plan_patches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    patch_type = Column(String(100), default="manual_update")  # manual_update, nl_refinement, auto_balance, reschedule
    nl_prompt = Column(Text, nullable=True)
    diff_payload = Column(JSON, nullable=False)
    applied_by = Column(String(100), default="system")
    applied_at = Column(DateTime, default=datetime.utcnow)

    transition = relationship("Transition", back_populates="patches")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(36), nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, APPROVE, PUBLISH
    details = Column(JSON, default=dict)
    performed_by = Column(String(100), default="user")
    timestamp = Column(DateTime, default=datetime.utcnow)

    transition = relationship("Transition", back_populates="audit_logs")


class TransitionApproval(Base):
    __tablename__ = "transition_approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False)  # profile, hierarchy, levels, schedule, final_publish
    status = Column(String(50), default="pending")  # pending, approved, rejected
    approver_name = Column(String(100), nullable=False)
    comments = Column(Text, default="")
    approved_at = Column(DateTime, default=datetime.utcnow)

