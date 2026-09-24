from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.models.transition import Transition
from backend.models.knowledge import KnowledgeNode

class CapacityService:
    @staticmethod
    def calculate_transition_capacity_targets(
        total_duration_days: int,
        shadow_days: int,
        reverse_shadow_days: int,
        daily_kt_hours: float = 5.0
    ) -> Dict[str, Any]:
        """
        Formula:
        Available KT Days = Transition Duration - Shadow Days - Reverse Shadow Days
        Target Capacity Hours = Available KT Days * Daily KT Hours
        """
        available_kt_days = max(0, total_duration_days - shadow_days - reverse_shadow_days)
        target_capacity_hours = round(available_kt_days * daily_kt_hours, 2)
        return {
            "total_duration_days": total_duration_days,
            "shadow_days": shadow_days,
            "reverse_shadow_days": reverse_shadow_days,
            "available_kt_days": available_kt_days,
            "daily_kt_hours": daily_kt_hours,
            "target_capacity_hours": target_capacity_hours,
        }

    @staticmethod
    def evaluate_capacity_balance(db: Session, transition_id: str) -> Dict[str, Any]:
        transition = db.query(Transition).filter(Transition.id == transition_id).first()
        if not transition:
            raise ValueError(f"Transition {transition_id} not found")

        targets = CapacityService.calculate_transition_capacity_targets(
            total_duration_days=transition.total_duration_days,
            shadow_days=transition.shadow_days,
            reverse_shadow_days=transition.reverse_shadow_days,
            daily_kt_hours=transition.daily_kt_hours,
        )
        target_hours = targets["target_capacity_hours"]

        # Calculate generated hours across topics/subtopics
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).all()
        
        # Determine leaf nodes (nodes with no children)
        parent_ids = {n.parent_id for n in nodes if n.parent_id is not None}
        leaf_nodes = [n for n in nodes if n.id not in parent_ids]
        
        # Sum hours from leaf nodes (or all nodes if no hierarchy yet)
        if leaf_nodes:
            generated_hours = sum(n.estimated_hours or 0.0 for n in leaf_nodes)
        else:
            generated_hours = sum(n.estimated_hours or 0.0 for n in nodes)

        generated_hours = round(generated_hours, 2)
        gap_hours = round(target_hours - generated_hours, 2)
        balance_ratio = round((generated_hours / target_hours) * 100, 1) if target_hours > 0 else 100.0

        if generated_hours < target_hours:
            status = "UNDER_ALLOCATED"
            recommendation = (
                f"Deficit of {gap_hours} hours. Topic decomposition required: Expand operational scenarios, "
                f"troubleshooting workshops, exception handling walkthroughs, or hands-on incident simulations."
            )
        elif generated_hours > target_hours:
            status = "OVER_ALLOCATED"
            recommendation = f"Excess of {abs(gap_hours)} hours. Consolidate subtopics or adjust session durations."
        else:
            status = "BALANCED"
            recommendation = "Capacity is 100% matched and fully utilized."

        # Category breakdown
        category_breakdown = {}
        for n in (leaf_nodes or nodes):
            cat = n.category or "uncategorized"
            category_breakdown[cat] = round(category_breakdown.get(cat, 0.0) + (n.estimated_hours or 0.0), 2)

        return {
            **targets,
            "generated_hours": generated_hours,
            "gap_hours": gap_hours,
            "balance_ratio_percent": balance_ratio,
            "status": status,
            "recommendation": recommendation,
            "category_breakdown": category_breakdown,
            "total_leaf_nodes": len(leaf_nodes or nodes),
        }

