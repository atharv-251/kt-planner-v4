import uuid
from datetime import datetime, date, time
from sqlalchemy import Column, String, Integer, Float, Date, Time, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Transition(Base):
    __tablename__ = "transitions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="development_and_ams")
    status = Column(String(50), default="draft")
    
    start_date = Column(Date, default=date(2026, 9, 20))
    end_date = Column(Date, default=date(2026, 10, 30))
    total_duration_days = Column(Integer, default=60)
    shadow_days = Column(Integer, default=10)
    reverse_shadow_days = Column(Integer, default=10)
    available_kt_days = Column(Integer, default=40)  # total - shadow - reverse_shadow
    daily_kt_hours = Column(Float, default=5.0)
    target_capacity_hours = Column(Float, default=200.0)  # available_kt_days * daily_kt_hours

    # Countries & Timezone (Calculated automatically, considering DST)
    primary_country = Column(String(100), default="India")
    timezone = Column(String(50), default="Asia/Kolkata")

    sme_country = Column(String(100), default="India")
    receiver_country = Column(String(100), default="India")
    sme_timezone = Column(String(50), default="Asia/Kolkata")
    receiver_timezone = Column(String(50), default="Asia/Kolkata")

    # Shift Hours (Default 8:00 AM - 5:00 PM local, customizable via toggle)
    sme_shift_start = Column(Time, default=time(8, 0))
    sme_shift_end = Column(Time, default=time(17, 0))
    receiver_shift_start = Column(Time, default=time(8, 0))
    receiver_shift_end = Column(Time, default=time(17, 0))
    custom_shifts_enabled = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("UploadedDocument", back_populates="transition", cascade="all, delete-orphan")
    raw_extractions = relationship("RawExtraction", back_populates="transition", cascade="all, delete-orphan")
    profile = relationship("ProjectProfile", back_populates="transition", uselist=False, cascade="all, delete-orphan")
    knowledge_nodes = relationship("KnowledgeNode", back_populates="transition", cascade="all, delete-orphan")
    kt_evaluations = relationship("KTLevelEvaluation", back_populates="transition", cascade="all, delete-orphan")
    stakeholders = relationship("Stakeholder", back_populates="transition", cascade="all, delete-orphan")
    sessions = relationship("KTSession", back_populates="transition", cascade="all, delete-orphan")
    patches = relationship("PlanPatch", back_populates="transition", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="transition", cascade="all, delete-orphan")


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100), default="application/octet-stream")
    checksum = Column(String(64), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    transition = relationship("Transition", back_populates="documents")


class RawExtraction(Base):
    __tablename__ = "raw_extractions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    raw_json_payload = Column(JSON, nullable=False)
    normalized_payload = Column(JSON, nullable=True)
    extracted_at = Column(DateTime, default=datetime.utcnow)

    transition = relationship("Transition", back_populates="raw_extractions")


class ProjectProfile(Base):
    __tablename__ = "project_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), unique=True, nullable=False)
    project_name = Column(String(255), nullable=False)
    business_purpose = Column(Text, default="")
    criticality = Column(String(100), default="Business-critical")
    technology_stack = Column(JSON, default=list)
    environments = Column(JSON, default=list)
    support_model = Column(String(100), default="AMS 2")
    integrations = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)
    kpis_slas = Column(JSON, default=list)
    risks_constraints = Column(JSON, default=list)
    evidence_citations = Column(JSON, default=list)
    evidence_gaps = Column(JSON, default=list)
    
    # Project Category: development_and_ams (Both), ams_operations (AMS), development (Development)
    project_category = Column(String(100), default="development_and_ams")
    # Intended Levels of support/development: subset of ["L1", "L2", "L3"]
    intended_levels = Column(JSON, default=lambda: ["L1", "L2", "L3"])

    is_approved = Column(Boolean, default=False)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transition = relationship("Transition", back_populates="profile")
