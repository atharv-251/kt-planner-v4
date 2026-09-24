from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.transition import Transition, ProjectProfile
from backend.models.knowledge import KTLevelEvaluation
from backend.models.scheduling import KTSession
from backend.schemas.profile import ProjectProfileResponse, ProjectProfileUpdate, ProjectProfileApprove
from backend.ai.agents import ProjectProfileAgent

router = APIRouter(prefix="/api/v1/transitions/{transition_id}/profile", tags=["Project Profile"])

@router.post("/generate", response_model=ProjectProfileResponse)
def generate_profile(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    try:
        profile = ProjectProfileAgent.run(db, transition_id)
        transition.status = "profile_generated"
        db.commit()
        return profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=ProjectProfileResponse)
def get_profile(transition_id: str, db: Session = Depends(get_db)):
    profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Project profile not found. Please generate profile first.")
    return profile

@router.put("", response_model=ProjectProfileResponse)
def update_profile(
    transition_id: str,
    payload: ProjectProfileUpdate,
    db: Session = Depends(get_db)
):
    profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Project profile not found")

    update_dict = payload.dict(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(profile, k, v)

    # If intended levels are updated, strictly synchronize all existing evaluations and purge invalid sessions
    if "intended_levels" in update_dict and payload.intended_levels:
        new_levels = payload.intended_levels
        evals = db.query(KTLevelEvaluation).filter(KTLevelEvaluation.transition_id == transition_id).all()
        for ev in evals:
            if ev.level_scope:
                parts = [p.strip() for p in ev.level_scope.split("+") if p.strip()]
                filtered_parts = [p for p in parts if p in new_levels]
                if not filtered_parts:
                    filtered_parts = [new_levels[-1]]
                ev.level_scope = "+".join(filtered_parts)

        # Remove any sessions that were generated for levels that are no longer intended
        db.query(KTSession).filter(
            KTSession.transition_id == transition_id,
            ~KTSession.level.in_(new_levels)
        ).delete(synchronize_session=False)

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile

@router.post("/approve", response_model=ProjectProfileResponse)
def approve_profile(
    transition_id: str,
    payload: ProjectProfileApprove,
    db: Session = Depends(get_db)
):
    profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Project profile not found")

    profile.is_approved = True
    profile.approved_by = payload.approved_by
    profile.approved_at = datetime.utcnow()

    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if transition:
        transition.status = "profile_approved"

    db.commit()
    db.refresh(profile)
    return profile

