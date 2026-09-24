from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class KnowledgeNodeCreate(BaseModel):
    parent_id: Optional[str] = None
    node_type: str = Field(..., json_schema_extra={"example": "topic"})
    name: str
    description: Optional[str] = ""
    category: Optional[str] = "functional"
    estimated_hours: Optional[float] = 0.0
    recommended_method: Optional[str] = "workshop"
    weightage_percent: Optional[float] = 0.0
    evidence_references: Optional[List[str]] = []
    order_index: Optional[int] = 0

class KnowledgeNodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    estimated_hours: Optional[float] = None
    recommended_method: Optional[str] = None
    weightage_percent: Optional[float] = None
    evidence_references: Optional[List[str]] = None
    order_index: Optional[int] = None

class KnowledgeNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transition_id: str
    parent_id: Optional[str] = None
    node_type: str
    name: str
    description: str
    category: str
    estimated_hours: float
    recommended_method: str
    weightage_percent: float
    evidence_references: List[str]
    order_index: int
    created_at: datetime
    children: Optional[List["KnowledgeNodeResponse"]] = []

KnowledgeNodeResponse.model_rebuild()

