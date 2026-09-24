from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class ControlledSQLRequest(BaseModel):
    query: str = Field(..., json_schema_extra={"example": "SELECT count(*) as total_nodes FROM knowledge_nodes WHERE transition_id = :transition_id"})
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ControlledSQLResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int

class ValidationCheckItem(BaseModel):
    check_name: str
    category: str
    passed: bool
    severity: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ValidationReport(BaseModel):
    overall_status: str
    score_percent: float
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[ValidationCheckItem]

class NaturalLanguageRefinementRequest(BaseModel):
    prompt: str = Field(..., json_schema_extra={"example": "Increase duration of CI/CD pipeline session to 4 hours and assign to John Doe"})

class PlanPatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transition_id: str
    version_number: int
    patch_type: str
    nl_prompt: Optional[str] = None
    diff_payload: Dict[str, Any]
    applied_by: str
    applied_at: datetime

