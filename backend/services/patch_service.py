from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models.transition import Transition
from backend.models.governance import PlanPatch, AuditLog
from backend.models.scheduling import KTSession
from backend.models.knowledge import KnowledgeNode

class PatchService:
    @staticmethod
    def apply_patch(
        db: Session,
        transition_id: str,
        patch_type: str,
        diff_payload: Dict[str, Any],
        applied_by: str = "system",
        nl_prompt: Optional[str] = None
    ) -> PlanPatch:
        transition = db.query(Transition).filter(Transition.id == transition_id).first()
        if not transition:
            raise ValueError(f"Transition {transition_id} not found")

        # Determine latest version
        latest_patch = (
            db.query(PlanPatch)
            .filter(PlanPatch.transition_id == transition_id)
            .order_by(PlanPatch.version_number.desc())
            .first()
        )
        version_num = (latest_patch.version_number + 1) if latest_patch else 1

        # Execute modifications according to patch_type
        if patch_type == "update_session":
            session_id = diff_payload.get("session_id")
            updates = diff_payload.get("updates", {})
            sess = db.query(KTSession).filter(KTSession.id == session_id).first()
            if sess:
                for k, v in updates.items():
                    if hasattr(sess, k):
                        setattr(sess, k, v)
        elif patch_type == "update_node":
            node_id = diff_payload.get("node_id")
            updates = diff_payload.get("updates", {})
            node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
            if node:
                for k, v in updates.items():
                    if hasattr(node, k):
                        setattr(node, k, v)

        patch = PlanPatch(
            transition_id=transition_id,
            version_number=version_num,
            patch_type=patch_type,
            nl_prompt=nl_prompt,
            diff_payload=diff_payload,
            applied_by=applied_by,
            applied_at=datetime.utcnow(),
        )
        db.add(patch)

        audit = AuditLog(
            transition_id=transition_id,
            entity_type="PlanPatch",
            entity_id=patch.id,
            action="APPLY_PATCH",
            details={"version": version_num, "patch_type": patch_type, "diff": diff_payload},
            performed_by=applied_by,
        )
        db.add(audit)
        db.commit()
        db.refresh(patch)
        return patch

