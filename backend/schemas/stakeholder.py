from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class StakeholderCreate(BaseModel):
    name: str
    email: Optional[str] = None
    role: str = Field(default="sme", description="sme or receiver") # strictly sme or receiver
    level: str = Field(default="L1", description="L1, L2, or L3")
    primary_domain: Optional[str] = None
    assigned_node_ids: Optional[List[str]] = []

class StakeholderUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    level: Optional[str] = None
    primary_domain: Optional[str] = None
    assigned_node_ids: Optional[List[str]] = None

class StakeholderLeaveCreate(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = "Annual Leave"

class StakeholderLeaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stakeholder_id: str
    start_date: date
    end_date: date
    reason: str
    created_at: datetime

class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stakeholder_id: str
    subject: str
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    has_reminder: bool
    imported_at: datetime

class StakeholderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transition_id: str
    name: str
    email: Optional[str] = None
    role: str # "sme" or "receiver"
    level: str # "L1", "L2", or "L3"
    primary_domain: Optional[str] = None
    assigned_node_ids: List[str]
    created_at: datetime
    leaves: List[StakeholderLeaveResponse] = []
    calendar_event_count: Optional[int] = 0
