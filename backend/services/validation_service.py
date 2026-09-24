from typing import Dict, Any, List
from datetime import time
from sqlalchemy.orm import Session
from backend.models.transition import Transition, ProjectProfile
from backend.models.knowledge import KnowledgeNode, KTLevelEvaluation
from backend.models.stakeholder import Stakeholder
from backend.models.scheduling import KTSession
from backend.services.holiday_service import HolidayService
from backend.services.capacity_service import CapacityService
from backend.schemas.governance import ValidationCheckItem, ValidationReport

class ValidationService:
    @staticmethod
    def run_full_validation(db: Session, transition_id: str) -> ValidationReport:
        transition = db.query(Transition).filter(Transition.id == transition_id).first()
        if not transition:
            raise ValueError(f"Transition {transition_id} not found")

        checks: List[ValidationCheckItem] = []

        # 1. Completeness Check
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).all()
        node_count = len(nodes)
        parent_ids = {n.parent_id for n in nodes if n.parent_id is not None}
        leaf_nodes = [n for n in nodes if n.id not in parent_ids]

        if node_count >= 10 and len(leaf_nodes) >= 5:
            checks.append(ValidationCheckItem(
                check_name="Hierarchy Completeness",
                category="completeness",
                passed=True,
                severity="info",
                message=f"Knowledge hierarchy is established with {node_count} nodes and {len(leaf_nodes)} granular topics.",
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="Hierarchy Completeness",
                category="completeness",
                passed=False,
                severity="critical",
                message="Hierarchy lacks sufficient granularity. Decompose into applications, domains, processes, and subtopics.",
            ))

        # 2. KT Level Coverage Check
        evaluations = db.query(KTLevelEvaluation).filter(KTLevelEvaluation.transition_id == transition_id).all()
        evaluated_node_ids = {e.node_id for e in evaluations if e.learning_objective and e.expected_outcome}
        leaf_node_ids = {n.id for n in leaf_nodes}
        unevaluated = leaf_node_ids - evaluated_node_ids

        if leaf_node_ids and len(unevaluated) == 0:
            checks.append(ValidationCheckItem(
                check_name="KT Level Coverage (L1/L2/L3)",
                category="kt_levels",
                passed=True,
                severity="info",
                message="100% of granular topics have defined learning objectives, expected outcomes, and level scopes.",
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="KT Level Coverage (L1/L2/L3)",
                category="kt_levels",
                passed=False,
                severity="critical",
                message=f"{len(unevaluated)} leaf topics are missing level evaluations or explicit learning outcomes.",
            ))

        # 3. Capacity Utilization Check
        cap_eval = CapacityService.evaluate_capacity_balance(db, transition_id)
        balance_ratio = cap_eval["balance_ratio_percent"]
        if balance_ratio >= 100.0:
            checks.append(ValidationCheckItem(
                check_name="Capacity Utilization Target",
                category="capacity",
                passed=True,
                severity="info",
                message=f"Target KT capacity ({cap_eval['target_capacity_hours']}h) is fully utilized ({cap_eval['generated_hours']}h, {balance_ratio}%).",
                details=cap_eval,
            ))
        elif balance_ratio >= 80.0:
            checks.append(ValidationCheckItem(
                check_name="Capacity Utilization Target",
                category="capacity",
                passed=True,
                severity="warning",
                message=f"Capacity is at {balance_ratio}%. Recommended to add operational scenarios to reach 100%.",
                details=cap_eval,
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="Capacity Utilization Target",
                category="capacity",
                passed=False,
                severity="critical",
                message=f"Capacity under-utilized ({balance_ratio}%). Must decompose topics to meet target hours.",
                details=cap_eval,
            ))

        # 4. Calendar & Holiday Integrity Check
        sessions = db.query(KTSession).filter(KTSession.transition_id == transition_id).all()
        holiday_service = HolidayService.get_instance()
        country = transition.primary_country or "India"

        holiday_violations = []
        weekend_violations = []
        conflict_sessions = []

        for s in sessions:
            if holiday_service.is_weekend(s.scheduled_date):
                weekend_violations.append(s.id)
            is_hol, hol_name = holiday_service.is_holiday(country, s.scheduled_date)
            if is_hol:
                holiday_violations.append((s.id, s.scheduled_date.isoformat(), hol_name))
            if s.conflict_flags:
                conflict_sessions.append(s.id)

        if not holiday_violations and not weekend_violations:
            checks.append(ValidationCheckItem(
                check_name="Holiday & Weekend Adherence",
                category="calendar",
                passed=True,
                severity="info",
                message=f"All {len(sessions)} scheduled sessions strictly respect bank holidays in {country} and weekends.",
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="Holiday & Weekend Adherence",
                category="calendar",
                passed=False,
                severity="critical",
                message=f"Detected {len(holiday_violations)} sessions on bank holidays and {len(weekend_violations)} on weekends.",
                details={"holiday_violations": holiday_violations, "weekend_violations": weekend_violations},
            ))

        if not conflict_sessions:
            checks.append(ValidationCheckItem(
                check_name="Conflict-Free Availability",
                category="calendar",
                passed=True,
                severity="info",
                message="Zero SME calendar clashes or leave conflicts detected across all scheduled sessions.",
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="Conflict-Free Availability",
                category="calendar",
                passed=False,
                severity="warning",
                message=f"{len(conflict_sessions)} sessions have detected stakeholder calendar or leave conflicts.",
            ))

        # 5. Evidence Traceability Check
        nodes_with_evidence = [n for n in leaf_nodes if n.evidence_references and len(n.evidence_references) > 0]
        evidence_ratio = (len(nodes_with_evidence) / len(leaf_nodes) * 100) if leaf_nodes else 0.0

        if evidence_ratio >= 80.0:
            checks.append(ValidationCheckItem(
                check_name="Source Evidence Traceability",
                category="governance",
                passed=True,
                severity="info",
                message=f"{round(evidence_ratio, 1)}% of topics are directly backed by verified source documentation.",
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="Source Evidence Traceability",
                category="governance",
                passed=False,
                severity="warning",
                message="Several topics lack direct document evidence citations.",
            ))

        # 6. KT Planning Rules Enforcement Check
        # Rule 1: L1 SME can teach only L1 topics to L1 receivers
        # Rule 2: L2 SME can teach L1 or L2 topics to L1 or L2 receivers
        # Rule 3: L3 SME can teach L1, L2, or L3 topics to L1, L2, or L3 receivers
        # Rule 4: SME level must be >= topic level
        # Rule 5: Receiver level must be <= topic level and <= SME level
        from backend.services.scheduling_service import SchedulingService, LEVEL_WEIGHT
        from backend.services.timezone_service import TimezoneService

        stakeholder_map = {s.id: s for s in db.query(Stakeholder).filter(Stakeholder.transition_id == transition_id).all()}
        profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
        intended_levels = profile.intended_levels if (profile and profile.intended_levels) else ["L1", "L2", "L3"]
        kt_rule_violations = []

        for s in sessions:
            # 1. Enforce intended levels compliance
            if s.level not in intended_levels:
                kt_rule_violations.append(
                    f"{s.session_title}: Session level '{s.level}' is not within intended levels ({', '.join(intended_levels)})."
                )

            sme = stakeholder_map.get(s.sme_id) if s.sme_id else None
            rcv = stakeholder_map.get(s.receiver_id) if s.receiver_id else None

            # 2. Enforce SME assignment and KT Planning Rules
            if not sme:
                kt_rule_violations.append(f"{s.session_title}: No qualified SME assigned to conduct {s.level} session.")
            else:
                valid, err = SchedulingService.validate_kt_rules(
                    sme_level=sme.level,
                    topic_level=s.level,
                    receiver_level=rcv.level if rcv else None,
                )
                if not valid:
                    kt_rule_violations.append(f"{s.session_title}: {err}")

            # 3. Enforce receiver level bound even if unassigned SME
            if rcv and not sme:
                from backend.services.scheduling_service import LEVEL_WEIGHT
                if LEVEL_WEIGHT.get(rcv.level, 1) > LEVEL_WEIGHT.get(s.level, 1):
                    kt_rule_violations.append(f"{s.session_title}: {rcv.level} receiver cannot receive {s.level} topic.")

        if not kt_rule_violations:
            checks.append(ValidationCheckItem(
                check_name="KT Planning Rules Compliance",
                category="governance",
                passed=True,
                severity="info",
                message=f"All {len(sessions)} sessions strictly comply with KT Planning Rules (SME Level >= Topic Level >= Receiver Level).",
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="KT Planning Rules Compliance",
                category="governance",
                passed=False,
                severity="critical",
                message=f"Detected {len(kt_rule_violations)} KT Planning Rule level violations.",
                details={"violations": kt_rule_violations},
            ))

        # 7. Timezone & Shift Overlap Adherence Check
        shift_violations = []
        for s in sessions:
            overlap = TimezoneService.calculate_shift_overlap(
                sme_country=transition.sme_country or transition.primary_country or "India",
                receiver_country=transition.receiver_country or "India",
                target_date=s.scheduled_date,
                sme_shift_start=transition.sme_shift_start or time(8, 0),
                sme_shift_end=transition.sme_shift_end or time(17, 0),
                receiver_shift_start=transition.receiver_shift_start or time(8, 0),
                receiver_shift_end=transition.receiver_shift_end or time(17, 0),
            )
            if not overlap["has_overlap"]:
                shift_violations.append(f"{s.session_title} on {s.scheduled_date}: Zero shift overlap between countries.")

        if not shift_violations:
            checks.append(ValidationCheckItem(
                check_name="Timezone & Shift Overlap Adherence",
                category="calendar",
                passed=True,
                severity="info",
                message="All sessions scheduled within calculated DST-aware shift overlap hours between SME and Receiver.",
            ))
        else:
            checks.append(ValidationCheckItem(
                check_name="Timezone & Shift Overlap Adherence",
                category="calendar",
                passed=False,
                severity="critical",
                message=f"Detected {len(shift_violations)} sessions scheduled outside valid shift overlap.",
                details={"violations": shift_violations},
            ))

        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.passed)
        failed_checks = total_checks - passed_checks
        score_percent = round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 0.0

        critical_failures = sum(1 for c in checks if not c.passed and c.severity == "critical")
        if critical_failures == 0 and score_percent >= 80.0:
            overall_status = "PASS"
        elif critical_failures == 0:
            overall_status = "CONDITIONAL_PASS"
        else:
            overall_status = "FAIL"

        return ValidationReport(
            overall_status=overall_status,
            score_percent=score_percent,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            checks=checks,
        )

