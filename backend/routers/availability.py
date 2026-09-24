from datetime import date, time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from backend.database import get_db
from backend.models.transition import Transition
from backend.services.availability_service import AvailabilityService
from backend.services.holiday_service import HolidayService

router = APIRouter(prefix="/api/v1/transitions/{transition_id}/availability", tags=["Availability & Conflicts"])

@router.get("")
def get_availability_matrix(
    transition_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    try:
        matrix = AvailabilityService.get_transition_availability_matrix(
            db=db,
            transition_id=transition_id,
            start_date=start_date,
            end_date=end_date,
        )
        return matrix
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/holidays")
def get_transition_holidays(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    sme_country = transition.sme_country or transition.primary_country or "India"
    receiver_country = transition.receiver_country or "India"
    holiday_service = HolidayService.get_instance()
    
    sme_hols = holiday_service.get_holidays_in_range(
        country=sme_country,
        start_date=transition.start_date,
        end_date=transition.end_date,
    )
    rcv_hols = {}
    if receiver_country != sme_country:
        rcv_hols = holiday_service.get_holidays_in_range(
            country=receiver_country,
            start_date=transition.start_date,
            end_date=transition.end_date,
        )

    # Combined dictionary with country annotation if distinct
    combined_hols = {}
    for dt, name in sme_hols.items():
        combined_hols[dt] = f"{name} ({sme_country})" if sme_country != receiver_country else name
    for dt, name in rcv_hols.items():
        if dt in combined_hols:
            combined_hols[dt] = f"{combined_hols[dt]} / {name} ({receiver_country})"
        else:
            combined_hols[dt] = f"{name} ({receiver_country})"

    return {
        "sme_country": sme_country,
        "receiver_country": receiver_country,
        "country": f"{sme_country} & {receiver_country}" if sme_country != receiver_country else sme_country,
        "total_holidays": len(combined_hols),
        "holidays": combined_hols,
        "sme_holidays": sme_hols,
        "receiver_holidays": rcv_hols,
    }

@router.get("/countries")
def get_supported_countries():
    holiday_service = HolidayService.get_instance()
    countries = holiday_service.get_supported_countries()
    return {"countries": countries}

@router.get("/check-slot")
def check_slot(
    transition_id: str,
    target_date: date,
    start_time: str,  # format HH:MM
    end_time: str,    # format HH:MM
    stakeholder_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        s_parts = [int(p) for p in start_time.split(":")]
        e_parts = [int(p) for p in end_time.split(":")]
        st = time(s_parts[0], s_parts[1])
        et = time(e_parts[0], e_parts[1])

        conflicts = AvailabilityService.check_slot_conflicts(
            db=db,
            transition_id=transition_id,
            target_date=target_date,
            start_time=st,
            end_time=et,
            stakeholder_id=stakeholder_id,
        )
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

