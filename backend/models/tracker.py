import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from backend.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class KTTrackingActivity(Base):
    __tablename__ = "kt_tracking_activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("kt_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    activity_name = Column(String(255), nullable=False)
    status = Column(String(50), default="planned")
    progress_percent = Column(Integer, default=0)
    blocker = Column(Text, default="")
    risk = Column(Text, default="")
    notes = Column(Text, default="")
    expected_topics = Column(JSON, default=list)
    transcript_analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KTTranscriptAssessment(Base):
    __tablename__ = "kt_transcript_assessments"

    document_id = Column(String(36), ForeignKey("uploaded_documents.id", ondelete="CASCADE"), primary_key=True)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False, index=True)
    result = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)