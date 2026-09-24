from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.database import get_db
from backend.models.transition import Transition
from backend.models.governance import PlanPatch, TransitionApproval
from backend.schemas.governance import (
    ValidationReport,
    NaturalLanguageRefinementRequest,
    PlanPatchResponse,
)
from backend.services.validation_service import ValidationService
from backend.ai.agents import RefinementAgent

router = APIRouter(prefix="/api/v1/transitions/{transition_id}", tags=["Governance & Refinement"])

@router.get("/validation", response_model=ValidationReport)
def get_validation_report(transition_id: str, db: Session = Depends(get_db)):
    try:
        report = ValidationService.run_full_validation(db, transition_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/refine")
def refine_plan_with_natural_language(
    transition_id: str,
    payload: NaturalLanguageRefinementRequest,
    db: Session = Depends(get_db)
):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    try:
        result = RefinementAgent.run(db, transition_id, payload.prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/patches", response_model=List[PlanPatchResponse])
def get_version_patches(transition_id: str, db: Session = Depends(get_db)):
    patches = (
        db.query(PlanPatch)
        .filter(PlanPatch.transition_id == transition_id)
        .order_by(PlanPatch.version_number.desc())
        .all()
    )
    return patches

@router.post("/publish")
def publish_transition_plan(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    # Run validation check
    val = ValidationService.run_full_validation(db, transition_id)
    if val.overall_status == "FAIL":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish plan with critical governance failures. Validation score: {val.score_percent}%"
        )

    transition.status = "published"
    approval = TransitionApproval(
        transition_id=transition_id,
        stage="final_publish",
        status="approved",
        approver_name="Lead Architect / Transition Manager",
        comments="Plan verified, conflict-free, and locked for execution.",
        approved_at=datetime.utcnow(),
    )
    db.add(approval)
    db.commit()

    return {
        "status": "success",
        "message": "Transition plan published and finalized for delivery.",
        "validation_score": val.score_percent,
        "published_at": approval.approved_at.isoformat(),
    }

