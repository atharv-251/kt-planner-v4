from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class TransitionCreate(BaseModel):
    name: str = Field(...)
    category: str = Field(default="development_and_ams")
    start_date: date = Field(default=date(2026, 9, 20))
    end_date: date = Field(default=date(2026, 10, 30))
    total_duration_days: int = Field(default=60)
    shadow_days: int = Field(default=10)
    reverse_shadow_days: int = Field(default=10)
    daily_kt_hours: float = Field(default=5.0)

    # SME & Receiver Country (Timezones auto-calculated based on country & DST)
    sme_country: str = Field(default="India")
    receiver_country: str = Field(default="India")
    primary_country: Optional[str] = None
    timezone: Optional[str] = None
    
    # Optional Custom Shift Hours (Default 8:00 - 17:00 local)
    custom_shifts_enabled: bool = Field(default=False)
    sme_shift_start: time = Field(default=time(8, 0))
    sme_shift_end: time = Field(default=time(17, 0))
    receiver_shift_start: time = Field(default=time(8, 0))
    receiver_shift_end: time = Field(default=time(17, 0))

class TransitionSettingsUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_duration_days: Optional[int] = None
    shadow_days: Optional[int] = None
    reverse_shadow_days: Optional[int] = None
    daily_kt_hours: Optional[float] = None
    
    primary_country: Optional[str] = None
    timezone: Optional[str] = None
    sme_country: Optional[str] = None
    receiver_country: Optional[str] = None
    custom_shifts_enabled: Optional[bool] = None
    sme_shift_start: Optional[time] = None
    sme_shift_end: Optional[time] = None
    receiver_shift_start: Optional[time] = None
    receiver_shift_end: Optional[time] = None

class TransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    status: str
    start_date: date
    end_date: date
    total_duration_days: int
    shadow_days: int
    reverse_shadow_days: int
    available_kt_days: int
    daily_kt_hours: float
    target_capacity_hours: float

    sme_country: str
    receiver_country: str
    sme_timezone: str
    receiver_timezone: str

    custom_shifts_enabled: bool
    sme_shift_start: time
    sme_shift_end: time
    receiver_shift_start: time
    receiver_shift_end: time

    created_at: datetime
    updated_at: datetime

class UploadedDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transition_id: str
    file_name: str
    file_size: int
    mime_type: str
    uploaded_at: datetime
