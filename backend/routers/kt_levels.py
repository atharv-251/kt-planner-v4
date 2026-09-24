from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models.transition import Transition
from backend.models.knowledge import KnowledgeNode, KTLevelEvaluation
from backend.schemas.kt_level import KTLevelEvaluationResponse, KTLevelEvaluationUpdate
from backend.ai.agents import KTLevelAgent

router = APIRouter(prefix="/api/v1/transitions/{transition_id}/levels", tags=["KT Level Evaluation"])

@router.post("/evaluate")
def evaluate_kt_levels(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    evals = KTLevelAgent.run(db, transition_id)
    transition.status = "levels_evaluated"
    db.commit()
    return {
        "status": "success",
        "message": f"Successfully evaluated {len(evals)} topics for L1/L2/L3 learning objectives and expected outcomes.",
        "total_evaluated": len(evals),
    }

@router.get("", response_model=List[KTLevelEvaluationResponse])
def get_evaluations(transition_id: str, db: Session = Depends(get_db)):
    evals = (
        db.query(KTLevelEvaluation)
        .filter(KTLevelEvaluation.transition_id == transition_id)
        .all()
    )
    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).all()
    node_map = {n.id: n for n in nodes}

    results = []
    for e in evals:
        node = node_map.get(e.node_id)
        resp = KTLevelEvaluationResponse(
            id=e.id,
            transition_id=e.transition_id,
            node_id=e.node_id,
            node_name=node.name if node else "Unknown Topic",
            node_type=node.node_type if node else "topic",
            level_scope=e.level_scope,
            applicability=e.applicability,
            justification=e.justification,
            learning_objective=e.learning_objective,
            expected_outcome=e.expected_outcome,
            evidence=e.evidence,
            evaluated_at=e.evaluated_at,
        )
        results.append(resp)
    return results

@router.put("/{evaluation_id}", response_model=KTLevelEvaluationResponse)
def update_evaluation(
    transition_id: str,
    evaluation_id: str,
    payload: KTLevelEvaluationUpdate,
    db: Session = Depends(get_db)
):
    ev = db.query(KTLevelEvaluation).filter(
        KTLevelEvaluation.id == evaluation_id,
        KTLevelEvaluation.transition_id == transition_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="KT Level Evaluation not found")

    update_dict = payload.dict(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(ev, k, v)

    db.commit()
    db.refresh(ev)

    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == ev.node_id).first()
    return KTLevelEvaluationResponse(
        id=ev.id,
        transition_id=ev.transition_id,
        node_id=ev.node_id,
        node_name=node.name if node else "Unknown Topic",
        node_type=node.node_type if node else "topic",
        level_scope=ev.level_scope,
        applicability=ev.applicability,
        justification=ev.justification,
        learning_objective=ev.learning_objective,
        expected_outcome=ev.expected_outcome,
        evidence=ev.evidence,
        evaluated_at=ev.evaluated_at,
    )

