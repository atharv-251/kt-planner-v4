from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import date, time
from backend.database import get_db
from backend.models.transition import Transition
from backend.models.knowledge import KnowledgeNode
from backend.schemas.transition import TransitionCreate, TransitionSettingsUpdate, TransitionResponse
from backend.services.capacity_service import CapacityService
from backend.services.timezone_service import TimezoneService

router = APIRouter(prefix="/api/v1/transitions", tags=["Transitions"])

class DomainHoursUpdate(BaseModel):
    domain_hours: Dict[str, float]

@router.post("", response_model=TransitionResponse)
def create_transition(payload: TransitionCreate, db: Session = Depends(get_db)):
    # Calculate capacity values
    cap = CapacityService.calculate_transition_capacity_targets(
        total_duration_days=payload.total_duration_days,
        shadow_days=payload.shadow_days,
        reverse_shadow_days=payload.reverse_shadow_days,
        daily_kt_hours=payload.daily_kt_hours,
    )
    sme_c = payload.sme_country or payload.primary_country or "India"
    rcv_c = payload.receiver_country or "India"
    sme_tz = TimezoneService.get_timezone_for_country(sme_c)
    rcv_tz = TimezoneService.get_timezone_for_country(rcv_c)

    transition = Transition(
        name=payload.name,
        category=payload.category,
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_duration_days=payload.total_duration_days,
        shadow_days=payload.shadow_days,
        reverse_shadow_days=payload.reverse_shadow_days,
        available_kt_days=cap["available_kt_days"],
        daily_kt_hours=payload.daily_kt_hours,
        target_capacity_hours=cap["target_capacity_hours"],
        primary_country=sme_c,
        timezone=sme_tz,
        sme_country=sme_c,
        receiver_country=rcv_c,
        sme_timezone=sme_tz,
        receiver_timezone=rcv_tz,
        custom_shifts_enabled=payload.custom_shifts_enabled,
        sme_shift_start=payload.sme_shift_start or time(8, 0),
        sme_shift_end=payload.sme_shift_end or time(17, 0),
        receiver_shift_start=payload.receiver_shift_start or time(8, 0),
        receiver_shift_end=payload.receiver_shift_end or time(17, 0),
        status="draft",
    )
    db.add(transition)
    db.commit()
    db.refresh(transition)
    return transition

@router.get("", response_model=List[TransitionResponse])
def list_transitions(db: Session = Depends(get_db)):
    return db.query(Transition).order_by(Transition.created_at.desc()).all()

@router.get("/{transition_id}", response_model=TransitionResponse)
def get_transition(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")
    return transition

@router.put("/{transition_id}/settings", response_model=TransitionResponse)
def update_transition_settings(
    transition_id: str,
    payload: TransitionSettingsUpdate,
    db: Session = Depends(get_db)
):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    update_data = payload.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(transition, k, v)

    # Sync country and timezone with DST consideration
    if payload.sme_country:
        transition.sme_timezone = TimezoneService.get_timezone_for_country(payload.sme_country)
        transition.primary_country = payload.sme_country
        transition.timezone = transition.sme_timezone
    elif payload.primary_country:
        transition.sme_country = payload.primary_country
        transition.sme_timezone = TimezoneService.get_timezone_for_country(payload.primary_country)
        transition.timezone = transition.sme_timezone

    if payload.receiver_country:
        transition.receiver_timezone = TimezoneService.get_timezone_for_country(payload.receiver_country)

    # Re-calculate capacity
    cap = CapacityService.calculate_transition_capacity_targets(
        total_duration_days=transition.total_duration_days,
        shadow_days=transition.shadow_days,
        reverse_shadow_days=transition.reverse_shadow_days,
        daily_kt_hours=transition.daily_kt_hours,
    )
    transition.available_kt_days = cap["available_kt_days"]
    transition.target_capacity_hours = cap["target_capacity_hours"]

    db.commit()
    db.refresh(transition)
    return transition

@router.get("/{transition_id}/shift-overlap")
def get_shift_overlap(
    transition_id: str,
    target_date: date = None,
    db: Session = Depends(get_db)
):
    """
    Computes local and UTC shift overlap between SME and Receiver,
    taking into account Daylight Saving Time (DST) changes.
    """
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    check_date = target_date or transition.start_date or date.today()

    overlap = TimezoneService.calculate_shift_overlap(
        sme_country=transition.sme_country or "India",
        receiver_country=transition.receiver_country or "India",
        target_date=check_date,
        sme_shift_start=transition.sme_shift_start or time(8, 0),
        sme_shift_end=transition.sme_shift_end or time(17, 0),
        receiver_shift_start=transition.receiver_shift_start or time(8, 0),
        receiver_shift_end=transition.receiver_shift_end or time(17, 0),
    )
    return overlap

@router.put("/{transition_id}/domain-hours")
def update_domain_hours(
    transition_id: str,
    payload: DomainHoursUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates effort hours by architectural domain with real-time recalculation
    and database persistence. Proportionally adjusts leaf node hours within each domain.
    """
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    all_nodes = db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).all()
    if not all_nodes:
        raise HTTPException(status_code=400, detail="No knowledge hierarchy nodes found to update")

    parent_ids = {n.parent_id for n in all_nodes if n.parent_id is not None}
    leaf_nodes = [n for n in all_nodes if n.id not in parent_ids]
    if not leaf_nodes:
        leaf_nodes = all_nodes

    # Group leaf nodes by category
    category_nodes: Dict[str, List[KnowledgeNode]] = {}
    for n in leaf_nodes:
        cat = n.category or "uncategorized"
        category_nodes.setdefault(cat, []).append(n)

    for cat_name, new_hours in payload.domain_hours.items():
        matched_nodes = category_nodes.get(cat_name)
        if not matched_nodes:
            # Try partial matching e.g. "functional" in cat_name
            for k, nodes in category_nodes.items():
                if k.lower() in cat_name.lower() or cat_name.lower() in k.lower():
                    matched_nodes = nodes
                    break

        if matched_nodes:
            curr_sum = sum(n.estimated_hours or 0.0 for n in matched_nodes)
            count = len(matched_nodes)
            running_sum = 0.0
            if curr_sum > 0:
                scale = float(new_hours) / curr_sum
                for i, n in enumerate(matched_nodes):
                    if i == count - 1:
                        n.estimated_hours = round(float(new_hours) - running_sum, 1)
                    else:
                        scaled_val = round((n.estimated_hours or 0.0) * scale, 1)
                        n.estimated_hours = scaled_val
                        running_sum += scaled_val
            else:
                per_node = round(float(new_hours) / count, 1)
                for i, n in enumerate(matched_nodes):
                    if i == count - 1:
                        n.estimated_hours = round(float(new_hours) - running_sum, 1)
                    else:
                        n.estimated_hours = per_node
                        running_sum += per_node

    db.commit()

    # Return updated capacity balance evaluation
    updated_cap = CapacityService.evaluate_capacity_balance(db, transition_id)
    return {
        "status": "success",
        "message": "Domain effort hours updated and persisted successfully.",
        "capacity": updated_cap,
    }
