from datetime import datetime, date, time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.database import get_db
from backend.models.transition import Transition, ProjectProfile
from backend.models.knowledge import KnowledgeNode
from backend.models.stakeholder import Stakeholder
from backend.models.scheduling import KTSession
from backend.schemas.scheduling import (
    KTSessionResponse,
    KTSessionUpdate,
    AutoScheduleRequest,
)
from backend.services.scheduling_service import SchedulingService, LEVEL_WEIGHT

router = APIRouter(prefix="/api/v1/transitions/{transition_id}/schedule", tags=["Scheduling"])

@router.post("/auto-build")
def auto_build_schedule(
    transition_id: str,
    payload: AutoScheduleRequest,
    db: Session = Depends(get_db)
):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    sessions = SchedulingService.auto_schedule_sessions(
        db=db,
        transition_id=transition_id,
        start_date=payload.start_date or transition.start_date,
        daily_start_hour=payload.daily_start_hour,
        daily_max_hours=payload.daily_max_hours,
        auto_assign_smes=payload.auto_assign_smes,
    )
    transition.status = "scheduled"
    db.commit()

    return {
        "status": "success",
        "message": f"Successfully generated conflict-free schedule with {len(sessions)} KT sessions.",
        "total_sessions": len(sessions),
    }

@router.get("", response_model=List[KTSessionResponse])
def get_schedule(transition_id: str, db: Session = Depends(get_db)):
    sessions = (
        db.query(KTSession)
        .filter(KTSession.transition_id == transition_id)
        .order_by(KTSession.scheduled_date, KTSession.start_time)
        .all()
    )
    nodes = {n.id: n.name for n in db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).all()}
    stakeholders = {s.id: s for s in db.query(Stakeholder).filter(Stakeholder.transition_id == transition_id).all()}

    results = []
    for s in sessions:
        sme_obj = stakeholders.get(s.sme_id)
        rcv_obj = stakeholders.get(s.receiver_id)
        results.append(
            KTSessionResponse(
                id=s.id,
                transition_id=s.transition_id,
                node_id=s.node_id,
                node_name=nodes.get(s.node_id, "Unknown Topic"),
                sme_id=s.sme_id,
                sme_name=sme_obj.name if sme_obj else "Unassigned",
                sme_level=sme_obj.level if sme_obj else None,
                receiver_id=s.receiver_id,
                receiver_name=rcv_obj.name if rcv_obj else "Unassigned",
                receiver_level=rcv_obj.level if rcv_obj else None,
                session_title=s.session_title,
                level=s.level,
                duration_hours=s.duration_hours,
                scheduled_date=s.scheduled_date,
                start_time=s.start_time,
                end_time=s.end_time,
                delivery_mode=s.delivery_mode,
                status=s.status,
                conflict_flags=s.conflict_flags or [],
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
    return results

@router.get("/fullcalendar")
def get_fullcalendar_events(transition_id: str, db: Session = Depends(get_db)):
    """Provides formatted events ready for FullCalendar component."""
    sessions = (
        db.query(KTSession)
        .filter(KTSession.transition_id == transition_id)
        .all()
    )
    stakeholders = {s.id: s for s in db.query(Stakeholder).filter(Stakeholder.transition_id == transition_id).all()}

    # Level color coding
    color_map = {
        "L1": "#2563EB",  # Blue
        "L2": "#7C3AED",  # Purple
        "L3": "#059669",  # Green / Emerald
    }

    events = []
    for s in sessions:
        start_iso = f"{s.scheduled_date.isoformat()}T{s.start_time.strftime('%H:%M:%S')}"
        end_iso = f"{s.scheduled_date.isoformat()}T{s.end_time.strftime('%H:%M:%S')}"
        has_conflicts = len(s.conflict_flags or []) > 0

        bg_color = "#DC2626" if has_conflicts else color_map.get(s.level, "#4F46E5")
        sme_obj = stakeholders.get(s.sme_id)
        rcv_obj = stakeholders.get(s.receiver_id)
        sme_name = sme_obj.name if sme_obj else "Unassigned"
        rcv_name = rcv_obj.name if rcv_obj else "Unassigned"

        events.append({
            "id": s.id,
            "title": f"{s.session_title} ({sme_name} → {rcv_name})",
            "start": start_iso,
            "end": end_iso,
            "backgroundColor": bg_color,
            "borderColor": bg_color,
            "textColor": "#FFFFFF",
            "extendedProps": {
                "level": s.level,
                "duration_hours": s.duration_hours,
                "delivery_mode": s.delivery_mode,
                "sme_name": sme_name,
                "sme_level": sme_obj.level if sme_obj else None,
                "receiver_name": rcv_name,
                "receiver_level": rcv_obj.level if rcv_obj else None,
                "status": s.status,
                "conflicts": s.conflict_flags or [],
            },
        })
    return events

@router.put("/sessions/{session_id}", response_model=KTSessionResponse)
def update_session(
    transition_id: str,
    session_id: str,
    payload: KTSessionUpdate,
    db: Session = Depends(get_db)
):
    session = db.query(KTSession).filter(KTSession.id == session_id, KTSession.transition_id == transition_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    update_dict = payload.dict(exclude_unset=True)

    # Check KT Planning Rules
    sme_id_check = payload.sme_id if payload.sme_id is not None else session.sme_id
    rcv_id_check = payload.receiver_id if payload.receiver_id is not None else session.receiver_id
    topic_level = payload.level or session.level

    sme_obj = db.query(Stakeholder).filter(Stakeholder.id == sme_id_check).first() if sme_id_check else None
    rcv_obj = db.query(Stakeholder).filter(Stakeholder.id == rcv_id_check).first() if rcv_id_check else None

    # Check intended levels
    profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
    if profile and profile.intended_levels and topic_level not in profile.intended_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Topic level '{topic_level}' is not within intended levels ({', '.join(profile.intended_levels)})."
        )

    if sme_obj:
        if sme_obj.role != "sme":
            raise HTTPException(status_code=400, detail=f"Stakeholder '{sme_obj.name}' is registered as {sme_obj.role}, not SME.")
        is_valid, err_msg = SchedulingService.validate_kt_rules(
            sme_level=sme_obj.level,
            topic_level=topic_level,
            receiver_level=rcv_obj.level if rcv_obj else None,
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=err_msg)

    if rcv_obj:
        if rcv_obj.role != "receiver":
            raise HTTPException(status_code=400, detail=f"Stakeholder '{rcv_obj.name}' is registered as {rcv_obj.role}, not Receiver.")
        if LEVEL_WEIGHT.get(rcv_obj.level, 1) > LEVEL_WEIGHT.get(topic_level, 1):
            raise HTTPException(status_code=400, detail=f"Rule Violation: {rcv_obj.level} receiver cannot receive {topic_level} topic.")

    for k, v in update_dict.items():
        setattr(session, k, v)

    # Recheck conflicts
    from backend.services.availability_service import AvailabilityService
    sme_conflicts = AvailabilityService.check_slot_conflicts(
        db=db,
        transition_id=transition_id,
        target_date=session.scheduled_date,
        start_time=session.start_time,
        end_time=session.end_time,
        stakeholder_id=session.sme_id,
    )
    rcv_conflicts = []
    if session.receiver_id:
        rcv_conflicts = AvailabilityService.check_slot_conflicts(
            db=db,
            transition_id=transition_id,
            target_date=session.scheduled_date,
            start_time=session.start_time,
            end_time=session.end_time,
            stakeholder_id=session.receiver_id,
        )
    all_conflicts = sme_conflicts + rcv_conflicts
    session.conflict_flags = all_conflicts
    session.status = "proposed" if not all_conflicts else "rescheduled"
    session.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(session)

    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == session.node_id).first()
    sme = db.query(Stakeholder).filter(Stakeholder.id == session.sme_id).first()
    rcv = db.query(Stakeholder).filter(Stakeholder.id == session.receiver_id).first()

    return KTSessionResponse(
        id=session.id,
        transition_id=session.transition_id,
        node_id=session.node_id,
        node_name=node.name if node else "Topic",
        sme_id=session.sme_id,
        sme_name=sme.name if sme else "Unassigned",
        sme_level=sme.level if sme else None,
        receiver_id=session.receiver_id,
        receiver_name=rcv.name if rcv else "Unassigned",
        receiver_level=rcv.level if rcv else None,
        session_title=session.session_title,
        level=session.level,
        duration_hours=session.duration_hours,
        scheduled_date=session.scheduled_date,
        start_time=session.start_time,
        end_time=session.end_time,
        delivery_mode=session.delivery_mode,
        status=session.status,
        conflict_flags=session.conflict_flags or [],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )

