from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models.transition import Transition
from backend.models.stakeholder import Stakeholder, StakeholderLeave, CalendarEvent
from backend.schemas.stakeholder import (
    StakeholderCreate,
    StakeholderUpdate,
    StakeholderResponse,
    StakeholderLeaveCreate,
    StakeholderLeaveResponse,
    CalendarEventResponse,
)
from backend.services.calendar_service import CalendarImportService

router = APIRouter(prefix="/api/v1/transitions/{transition_id}/stakeholders", tags=["Stakeholders & Calendars"])

@router.post("", response_model=StakeholderResponse)
def create_stakeholder(
    transition_id: str,
    payload: StakeholderCreate,
    db: Session = Depends(get_db)
):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    # Enforce strictly 2 roles: sme or receiver
    role = payload.role.lower().strip()
    if role not in ["sme", "receiver"]:
        role = "sme" if "sme" in role else "receiver"

    level = (payload.level or "L1").upper().strip()
    if level not in ["L1", "L2", "L3"]:
        level = "L1"

    # Enforce only selected intended levels from Stage 2
    from backend.models.transition import ProjectProfile
    profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
    if profile and profile.intended_levels and level not in profile.intended_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Level '{level}' is not in the selected intended levels ({', '.join(profile.intended_levels)}) for this transition."
        )

    s = Stakeholder(
        transition_id=transition_id,
        name=payload.name,
        email=payload.email,
        role=role,
        level=level,
        primary_domain=payload.primary_domain or "General",
        assigned_node_ids=payload.assigned_node_ids or [],
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return StakeholderResponse(
        id=s.id,
        transition_id=s.transition_id,
        name=s.name,
        email=s.email,
        role=s.role,
        level=s.level,
        primary_domain=s.primary_domain,
        assigned_node_ids=s.assigned_node_ids or [],
        created_at=s.created_at,
        leaves=[],
        calendar_event_count=0,
    )

@router.get("", response_model=List[StakeholderResponse])
def list_stakeholders(transition_id: str, db: Session = Depends(get_db)):
    stakeholders = db.query(Stakeholder).filter(Stakeholder.transition_id == transition_id).all()
    results = []
    for s in stakeholders:
        leaves = db.query(StakeholderLeave).filter(StakeholderLeave.stakeholder_id == s.id).all()
        cal_count = db.query(CalendarEvent).filter(CalendarEvent.stakeholder_id == s.id).count()
        results.append(
            StakeholderResponse(
                id=s.id,
                transition_id=s.transition_id,
                name=s.name,
                email=s.email,
                role=s.role,
                level=s.level or "L1",
                primary_domain=s.primary_domain,
                assigned_node_ids=s.assigned_node_ids or [],
                created_at=s.created_at,
                leaves=[StakeholderLeaveResponse.model_validate(l) for l in leaves],
                calendar_event_count=cal_count,
            )
        )
    return results

@router.post("/{stakeholder_id}/leaves", response_model=StakeholderLeaveResponse)
def add_stakeholder_leave(
    transition_id: str,
    stakeholder_id: str,
    payload: StakeholderLeaveCreate,
    db: Session = Depends(get_db)
):
    s = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id, Stakeholder.transition_id == transition_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stakeholder not found")

    leave = StakeholderLeave(
        stakeholder_id=stakeholder_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason or "Annual Leave",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave

@router.post("/{stakeholder_id}/calendar-csv")
async def upload_outlook_calendar(
    transition_id: str,
    stakeholder_id: str,
    file: UploadFile = File(...),
    mask_subjects: bool = Query(False),
    db: Session = Depends(get_db)
):
    s = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id, Stakeholder.transition_id == transition_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stakeholder not found")

    content = await file.read()
    csv_str = content.decode("utf-8-sig", errors="replace")

    events = CalendarImportService.parse_outlook_csv(
        csv_content=csv_str,
        stakeholder_id=stakeholder_id,
        db=db,
        mask_subjects=mask_subjects,
    )

    return {
        "status": "success",
        "message": f"Successfully parsed and imported {len(events)} Outlook calendar events.",
        "imported_events": len(events),
        "stakeholder_name": s.name,
    }

@router.delete("/{stakeholder_id}")
def delete_stakeholder(
    transition_id: str,
    stakeholder_id: str,
    db: Session = Depends(get_db)
):
    s = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id, Stakeholder.transition_id == transition_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    db.delete(s)
    db.commit()
    return {"status": "success", "message": "Stakeholder removed"}
