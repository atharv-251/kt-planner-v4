from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class KTLevelEvaluationUpdate(BaseModel):
    level_scope: Optional[str] = Field(None, json_schema_extra={"example": "L1+L2+L3"})
    applicability: Optional[str] = Field(None, json_schema_extra={"example": "applicable"})
    justification: Optional[str] = None
    learning_objective: Optional[str] = None
    expected_outcome: Optional[str] = None
    evidence: Optional[str] = None

class KTLevelEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transition_id: str
    node_id: str
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    level_scope: str
    applicability: str
    justification: str
    learning_objective: str
    expected_outcome: str
    evidence: str
    evaluated_at: datetime

