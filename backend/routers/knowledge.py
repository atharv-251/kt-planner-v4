from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from backend.database import get_db
from backend.models.transition import Transition
from backend.models.knowledge import KnowledgeNode
from backend.schemas.knowledge import KnowledgeNodeCreate, KnowledgeNodeUpdate, KnowledgeNodeResponse
from backend.ai.agents import KnowledgeGraphAgent, TopicDecompositionAgent

router = APIRouter(prefix="/api/v1/transitions/{transition_id}/hierarchy", tags=["Knowledge Hierarchy"])

@router.post("/generate")
def generate_hierarchy(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    try:
        nodes = KnowledgeGraphAgent.run(db, transition_id)
        transition.status = "hierarchy_generated"
        db.commit()
        return {
            "status": "success",
            "message": f"Generated {len(nodes)} knowledge hierarchy nodes across 6 architectural tiers.",
            "total_nodes": len(nodes),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[KnowledgeNodeResponse])
def get_hierarchy(
    transition_id: str,
    view: str = Query("nested", enum=["nested", "flat"]),
    db: Session = Depends(get_db)
):
    nodes = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.transition_id == transition_id)
        .order_by(KnowledgeNode.order_index)
        .all()
    )

    if view == "flat":
        return nodes

    # Build nested tree
    node_dict = {n.id: KnowledgeNodeResponse.model_validate(n) for n in nodes}
    for item in node_dict.values():
        item.children = []

    tree = []
    for item in node_dict.values():
        if item.parent_id and item.parent_id in node_dict:
            node_dict[item.parent_id].children.append(item)
        else:
            tree.append(item)

    return tree

@router.post("/decompose")
def decompose_topics_for_capacity(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    result = TopicDecompositionAgent.run(db, transition_id)
    return result

@router.post("/nodes", response_model=KnowledgeNodeResponse)
def create_node(
    transition_id: str,
    payload: KnowledgeNodeCreate,
    db: Session = Depends(get_db)
):
    node = KnowledgeNode(
        transition_id=transition_id,
        parent_id=payload.parent_id,
        node_type=payload.node_type,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        estimated_hours=payload.estimated_hours,
        recommended_method=payload.recommended_method,
        weightage_percent=payload.weightage_percent,
        evidence_references=payload.evidence_references,
        order_index=payload.order_index,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node

@router.put("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
def update_node(
    transition_id: str,
    node_id: str,
    payload: KnowledgeNodeUpdate,
    db: Session = Depends(get_db)
):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id, KnowledgeNode.transition_id == transition_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Knowledge node not found")

    update_dict = payload.dict(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(node, k, v)

    db.commit()
    db.refresh(node)
    return node

@router.delete("/nodes/{node_id}")
def delete_node(
    transition_id: str,
    node_id: str,
    db: Session = Depends(get_db)
):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id, KnowledgeNode.transition_id == transition_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Knowledge node not found")

    db.delete(node)
    db.commit()
    return {"status": "success", "message": "Node deleted"}
