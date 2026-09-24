from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ProjectProfileUpdate(BaseModel):
    project_name: Optional[str] = None
    business_purpose: Optional[str] = None
    criticality: Optional[str] = None
    technology_stack: Optional[List[str]] = None
    environments: Optional[List[str]] = None
    support_model: Optional[str] = None
    integrations: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    kpis_slas: Optional[List[str]] = None
    risks_constraints: Optional[List[str]] = None
    evidence_citations: Optional[List[str]] = None
    evidence_gaps: Optional[List[str]] = None
    
    # Project Category & Intended Levels
    project_category: Optional[str] = None # development_and_ams, ams_operations, development
    intended_levels: Optional[List[str]] = None # ["L1", "L2", "L3"]

class ProjectProfileApprove(BaseModel):
    approved_by: str
    comments: Optional[str] = None

class ProjectProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transition_id: str
    project_name: str
    business_purpose: str
    criticality: str
    technology_stack: List[str]
    environments: List[str]
    support_model: str
    integrations: List[str]
    dependencies: List[str]
    kpis_slas: List[str]
    risks_constraints: List[str]
    evidence_citations: List[str]
    evidence_gaps: List[str]
    
    project_category: str
    intended_levels: List[str]

    is_approved: bool
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
