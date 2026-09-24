from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class KTSessionCreate(BaseModel):
    node_id: str
    sme_id: Optional[str] = None
    receiver_id: Optional[str] = None
    session_title: str
    level: str = "L1"
    duration_hours: float = 2.0
    scheduled_date: date
    start_time: time
    end_time: time
    delivery_mode: str = "workshop"

class KTSessionUpdate(BaseModel):
    session_title: Optional[str] = None
    sme_id: Optional[str] = None
    receiver_id: Optional[str] = None
    level: Optional[str] = None
    duration_hours: Optional[float] = None
    scheduled_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    delivery_mode: Optional[str] = None
    status: Optional[str] = None

class KTSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transition_id: str
    node_id: str
    node_name: Optional[str] = None
    sme_id: Optional[str] = None
    sme_name: Optional[str] = None
    sme_level: Optional[str] = None
    receiver_id: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_level: Optional[str] = None
    session_title: str
    level: str
    duration_hours: float
    scheduled_date: date
    start_time: time
    end_time: time
    delivery_mode: str
    status: str
    conflict_flags: List[str] = []
    created_at: datetime
    updated_at: datetime

class AutoScheduleRequest(BaseModel):
    start_date: Optional[date] = None
    daily_start_hour: int = Field(default=10, description="Start hour (e.g. 10 for 10:00 AM)")
    daily_max_hours: float = Field(default=5.0, description="Max session hours scheduled per day")
    auto_assign_smes: bool = True
    enforce_shift_overlap: bool = True
