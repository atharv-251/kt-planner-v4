import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=True)
    
    # Hierarchy levels: application, domain, capability, process, topic, subtopic
    node_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    category = Column(String(100), default="functional")  # functional, technical, integration, ams_operations, etc.
    estimated_hours = Column(Float, default=0.0)
    recommended_method = Column(String(50), default="workshop")  # workshop, hands_on, shadowing, reverse_shadowing
    weightage_percent = Column(Float, default=0.0)
    evidence_references = Column(JSON, default=list)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transition = relationship("Transition", back_populates="knowledge_nodes")
    parent = relationship("KnowledgeNode", remote_side=[id], backref="children")
    evaluations = relationship("KTLevelEvaluation", back_populates="node", cascade="all, delete-orphan")
    sessions = relationship("KTSession", back_populates="node", cascade="all, delete-orphan")


class KTLevelEvaluation(Base):
    __tablename__ = "kt_level_evaluations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transition_id = Column(String(36), ForeignKey("transitions.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False)
    
    # Supported: L1, L2, L3, L1+L2, L1+L3, L2+L3, L1+L2+L3
    level_scope = Column(String(20), default="L1+L2")
    applicability = Column(String(50), default="applicable")  # applicable, not_applicable, conditional
    justification = Column(Text, default="")
    learning_objective = Column(Text, default="")
    expected_outcome = Column(Text, default="")
    evidence = Column(Text, default="")
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    transition = relationship("Transition", back_populates="kt_evaluations")
    node = relationship("KnowledgeNode", back_populates="evaluations")

