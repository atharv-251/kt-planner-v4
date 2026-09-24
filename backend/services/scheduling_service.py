from datetime import date, time, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.models.transition import Transition, ProjectProfile
from backend.models.knowledge import KnowledgeNode, KTLevelEvaluation
from backend.models.stakeholder import Stakeholder
from backend.models.scheduling import KTSession
from backend.services.holiday_service import HolidayService
from backend.services.availability_service import AvailabilityService
from backend.services.timezone_service import TimezoneService

LEVEL_WEIGHT = {"L1": 1, "L2": 2, "L3": 3}

class SchedulingService:
    @staticmethod
    def validate_kt_rules(sme_level: str, topic_level: str, receiver_level: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Enforces the 5 KT Planning Rules:
        1. L1 SME can teach only L1 topics to L1 receivers.
        2. L2 SME can teach L1 or L2 topics to L1 or L2 receivers.
        3. L3 SME can teach L1, L2, or L3 topics to L1, L2, or L3 receivers.
        4. SME level must be >= topic level.
        5. Receiver level must be <= topic level and <= SME level.
        """
        s_rank = LEVEL_WEIGHT.get(sme_level, 1)
        t_rank = LEVEL_WEIGHT.get(topic_level, 1)

        # Rule 4: SME level must be >= topic level
        if s_rank < t_rank:
            return False, f"Rule Violation: {sme_level} SME cannot teach {topic_level} topic (SME level must be >= topic level)."

        if receiver_level:
            r_rank = LEVEL_WEIGHT.get(receiver_level, 1)
            # Rule 5: Receiver level must be <= topic level and <= SME level
            if r_rank > s_rank:
                return False, f"Rule Violation: {sme_level} SME cannot teach {receiver_level} receiver (Receiver level must be <= SME level)."
            if r_rank > t_rank:
                return False, f"Rule Violation: {receiver_level} receiver cannot receive {topic_level} topic (Receiver level must be <= topic level)."

        return True, None

    @staticmethod
    def auto_schedule_sessions(
        db: Session,
        transition_id: str,
        start_date: Optional[date] = None,
        daily_start_hour: int = 10,
        daily_max_hours: float = 5.0,
        auto_assign_smes: bool = True,
        enforce_shift_overlap: bool = True,
    ) -> List[KTSession]:
        """
        Deterministic, conflict-free scheduling engine:
        1. Deletes any existing proposed sessions for this transition.
        2. Retrieves all leaf knowledge nodes with their KT level evaluations.
        3. Compulsorily calculates shift overlap between SME Country and Receiver Country (DST-aware).
        4. Strictly enforces KT Planning Rules:
           - SME Level >= Topic Level
           - Receiver Level <= Topic Level and <= SME Level
        5. Strictly excludes Bank Holidays of both SME and Receiver countries, weekends, and leaves.
        """
        transition = db.query(Transition).filter(Transition.id == transition_id).first()
        if not transition:
            raise ValueError(f"Transition {transition_id} not found")

        sme_country = transition.sme_country or transition.primary_country or "India"
        receiver_country = transition.receiver_country or "India"
        holiday_service = HolidayService.get_instance()
        s_date = start_date or transition.start_date
        e_date = transition.end_date

        # Clear existing sessions
        db.query(KTSession).filter(KTSession.transition_id == transition_id).delete()
        db.commit()

        # Retrieve knowledge nodes
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).all()
        if not nodes:
            return []

        # Find leaf nodes
        parent_ids = {n.parent_id for n in nodes if n.parent_id is not None}
        leaf_nodes = [n for n in nodes if n.id not in parent_ids]
        if not leaf_nodes:
            leaf_nodes = nodes

        # Fetch evaluations
        eval_map = {}
        evals = db.query(KTLevelEvaluation).filter(KTLevelEvaluation.transition_id == transition_id).all()
        for ev in evals:
            eval_map[ev.node_id] = ev

        # Fetch stakeholders: strictly partitioned into SMEs and Receivers
        all_stakeholders = db.query(Stakeholder).filter(Stakeholder.transition_id == transition_id).all()
        smes = [s for s in all_stakeholders if s.role == "sme"]
        receivers = [s for s in all_stakeholders if s.role == "receiver"]

        # Helper to pick eligible SME and Receiver enforcing KT rules:
        # Same level SME should be primary to give KT; only if no members of same level then higher SME conducts
        def pick_sme_and_receiver(node: KnowledgeNode, level: str) -> Tuple[Optional[Stakeholder], Optional[Stakeholder]]:
            if not auto_assign_smes:
                return None, None

            t_rank = LEVEL_WEIGHT.get(level, 1)

            # 1. Primary choice: same-level SMEs
            same_level_smes = [s for s in smes if LEVEL_WEIGHT.get(s.level, 1) == t_rank]
            # 2. Secondary choice: higher-level SMEs (sorted ascending so lowest higher level is selected first)
            higher_level_smes = [s for s in smes if LEVEL_WEIGHT.get(s.level, 1) > t_rank]
            higher_level_smes.sort(key=lambda s: LEVEL_WEIGHT.get(s.level, 1))

            candidate_smes = same_level_smes if same_level_smes else higher_level_smes
            picked_sme = None
            if candidate_smes:
                # Prioritize SME assigned to this node or matching primary domain
                for s in candidate_smes:
                    if s.assigned_node_ids and node.id in s.assigned_node_ids:
                        picked_sme = s
                        break
                    if s.primary_domain and s.primary_domain.lower() in (node.category or "").lower():
                        picked_sme = s
                        break
                if not picked_sme:
                    picked_sme = candidate_smes[0]

            # If no qualified SME is available (SME level must be >= topic level), do not assign an orphan session
            if not picked_sme:
                return None, None

            # Eligible Receivers: Receiver rank <= topic rank and <= SME rank
            s_rank = LEVEL_WEIGHT.get(picked_sme.level, 1)
            eligible_rcvs = [
                r for r in receivers
                if LEVEL_WEIGHT.get(r.level, 1) <= t_rank and LEVEL_WEIGHT.get(r.level, 1) <= s_rank
            ]
            picked_rcv = None
            if eligible_rcvs:
                # Prioritize same-level receiver if available, otherwise highest eligible receiver
                same_level_rcvs = [r for r in eligible_rcvs if LEVEL_WEIGHT.get(r.level, 1) == t_rank]
                pool = same_level_rcvs if same_level_rcvs else eligible_rcvs
                for r in pool:
                    if r.primary_domain and r.primary_domain.lower() in (node.category or "").lower():
                        picked_rcv = r
                        break
                if not picked_rcv:
                    pool.sort(key=lambda r: LEVEL_WEIGHT.get(r.level, 1), reverse=True)
                    picked_rcv = pool[0]

            return picked_sme, picked_rcv

        # Retrieve intended levels from project profile to strictly bound schedule generation
        profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
        intended_levels = profile.intended_levels if (profile and profile.intended_levels) else ["L1", "L2", "L3"]

        # Define session units to schedule
        sessions_to_schedule = []
        for node in leaf_nodes:
            ev = eval_map.get(node.id)
            level_scope = ev.level_scope if ev else "+".join(intended_levels)
            total_hours = node.estimated_hours or 2.0

            # Determine levels to generate: strictly constrained to intended_levels from Stage 2 profile review
            levels = []
            for candidate_lvl in ["L1", "L2", "L3"]:
                if candidate_lvl in level_scope and candidate_lvl in intended_levels:
                    levels.append(candidate_lvl)
            if not levels:
                levels = [intended_levels[-1]] if intended_levels else ["L1"]

            hours_per_level = round(total_hours / len(levels), 1)

            for lvl in levels:
                mode = node.recommended_method or "workshop"
                if lvl == "L3":
                    mode = "reverse_shadowing"
                elif lvl == "L2" and mode == "workshop":
                    mode = "hands_on"

                assigned_sme, assigned_rcv = pick_sme_and_receiver(node, lvl)

                sessions_to_schedule.append({
                    "node_id": node.id,
                    "title": f"[{lvl}] {node.name}",
                    "level": lvl,
                    "duration_hours": hours_per_level,
                    "delivery_mode": mode,
                    "sme_id": assigned_sme.id if assigned_sme else None,
                    "receiver_id": assigned_rcv.id if assigned_rcv else None,
                    "order_index": node.order_index,
                })

        # Priority sort: L1 first, then L2, then L3
        sessions_to_schedule.sort(key=lambda s: (LEVEL_WEIGHT.get(s["level"], 1), s["order_index"]))

        # Schedule day-by-day
        cur_date = s_date
        created_sessions = []
        session_idx = 0
        total_items = len(sessions_to_schedule)

        sme_s_time = transition.sme_shift_start or time(8, 0)
        sme_e_time = transition.sme_shift_end or time(17, 0)
        rcv_s_time = transition.receiver_shift_start or time(8, 0)
        rcv_e_time = transition.receiver_shift_end or time(17, 0)

        while session_idx < total_items and cur_date <= e_date:
            # 1. Check working day in SME country
            if not holiday_service.is_working_day(sme_country, cur_date):
                cur_date += timedelta(days=1)
                continue

            # 2. Check working day in Receiver country
            if sme_country != receiver_country and not holiday_service.is_working_day(receiver_country, cur_date):
                cur_date += timedelta(days=1)
                continue

            # 3. Compulsory calculation of Shift Overlap (DST-aware)
            overlap = TimezoneService.calculate_shift_overlap(
                sme_country=sme_country,
                receiver_country=receiver_country,
                target_date=cur_date,
                sme_shift_start=sme_s_time,
                sme_shift_end=sme_e_time,
                receiver_shift_start=rcv_s_time,
                receiver_shift_end=rcv_e_time,
            )

            has_valid_overlap = overlap.get("has_overlap") and overlap.get("overlap_hours", 0) > 0
            shift_conflict_note = None

            # Extract daily scheduling boundaries in SME local time
            if has_valid_overlap and overlap["sme"]["overlap_start_local"]:
                t_parts_s = [int(p) for p in overlap["sme"]["overlap_start_local"].split(":")]
                t_parts_e = [int(p) for p in overlap["sme"]["overlap_end_local"].split(":")]
                day_start_time = time(t_parts_s[0], t_parts_s[1])
                day_end_time = time(t_parts_e[0], t_parts_e[1])
                effective_max_hours = min(daily_max_hours, overlap["overlap_hours"])
            else:
                day_start_time = time(daily_start_hour, 0)
                day_end_time = time(min(23, daily_start_hour + int(daily_max_hours) + 1), 0)
                effective_max_hours = daily_max_hours
                if sme_country != receiver_country:
                    shift_conflict_note = (
                        f"Shift Overlap Conflict: {sme_country} and {receiver_country} have 0h standard shift overlap on {cur_date.isoformat()}. "
                        f"Enable custom shift hours in Stage 3."
                    )

            current_time = datetime.combine(cur_date, day_start_time)
            window_end = datetime.combine(cur_date, day_end_time)
            lunch_start = datetime.combine(cur_date, time(13, 0))
            lunch_end = datetime.combine(cur_date, time(14, 0))
            day_scheduled_hours = 0.0

            while session_idx < total_items and day_scheduled_hours < effective_max_hours and current_time < window_end:
                item = sessions_to_schedule[session_idx]
                available_in_window = (window_end - current_time).total_seconds() / 3600.0
                dur = min(item["duration_hours"], effective_max_hours - day_scheduled_hours, available_in_window)
                if dur < 0.5:
                    break

                potential_end = current_time + timedelta(hours=dur)

                # Check lunch overlap if applicable
                if current_time < lunch_start and potential_end > lunch_start:
                    if (lunch_start - current_time).total_seconds() >= 3600:
                        dur = (lunch_start - current_time).total_seconds() / 3600.0
                        potential_end = lunch_start
                    else:
                        current_time = lunch_end
                        potential_end = current_time + timedelta(hours=dur)

                if potential_end > window_end:
                    break

                # Detect conflicts for SME and Receiver
                sme_conflicts = AvailabilityService.check_slot_conflicts(
                    db=db,
                    transition_id=transition_id,
                    target_date=cur_date,
                    start_time=current_time.time(),
                    end_time=potential_end.time(),
                    stakeholder_id=item["sme_id"],
                )
                rcv_conflicts = []
                if item.get("receiver_id"):
                    rcv_conflicts = AvailabilityService.check_slot_conflicts(
                        db=db,
                        transition_id=transition_id,
                        target_date=cur_date,
                        start_time=current_time.time(),
                        end_time=potential_end.time(),
                        stakeholder_id=item["receiver_id"],
                    )

                all_conflicts = sme_conflicts + rcv_conflicts
                if shift_conflict_note:
                    all_conflicts.append(shift_conflict_note)

                sess = KTSession(
                    transition_id=transition_id,
                    node_id=item["node_id"],
                    sme_id=item["sme_id"],
                    receiver_id=item["receiver_id"],
                    session_title=item["title"],
                    level=item["level"],
                    duration_hours=round(dur, 1),
                    scheduled_date=cur_date,
                    start_time=current_time.time(),
                    end_time=potential_end.time(),
                    delivery_mode=item["delivery_mode"],
                    status="proposed" if not all_conflicts else "rescheduled",
                    conflict_flags=all_conflicts,
                )
                db.add(sess)
                created_sessions.append(sess)

                day_scheduled_hours += dur
                current_time = potential_end
                if current_time == lunch_start:
                    current_time = lunch_end

                session_idx += 1

            cur_date += timedelta(days=1)

        db.commit()
        return created_sessions
