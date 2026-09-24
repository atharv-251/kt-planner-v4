from datetime import date, time, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.services.holiday_service import HolidayService
from backend.models.stakeholder import Stakeholder, StakeholderLeave, CalendarEvent
from backend.models.transition import Transition

class AvailabilityService:
    @staticmethod
    def check_slot_conflicts(
        db: Session,
        transition_id: str,
        target_date: date,
        start_time: time,
        end_time: time,
        stakeholder_id: Optional[str] = None,
    ) -> List[str]:
        """
        Detects conflicts for a given slot:
        1. Weekend check
        2. Country Bank Holiday check (via HolidayService & holidays.json)
        3. Stakeholder leave check
        4. Stakeholder calendar event (Outlook busy) check
        """
        conflicts = []
        transition = db.query(Transition).filter(Transition.id == transition_id).first()
        sme_country = (transition.sme_country or transition.primary_country or "India") if transition else "India"
        receiver_country = (transition.receiver_country or "India") if transition else "India"

        # 1. Weekend check
        if HolidayService.is_weekend(target_date):
            conflicts.append(f"Weekend Conflict: {target_date.strftime('%A')} is a non-working weekend.")

        # 2. Bank holiday check (both SME and Receiver countries)
        holiday_service = HolidayService.get_instance()
        is_sme_hol, sme_hol_name = holiday_service.is_holiday(sme_country, target_date)
        if is_sme_hol and sme_hol_name:
            conflicts.append(f"Bank Holiday Conflict (SME Country): {target_date.isoformat()} is '{sme_hol_name}' in {sme_country}.")

        if receiver_country != sme_country:
            is_rcv_hol, rcv_hol_name = holiday_service.is_holiday(receiver_country, target_date)
            if is_rcv_hol and rcv_hol_name:
                conflicts.append(f"Bank Holiday Conflict (Receiver Country): {target_date.isoformat()} is '{rcv_hol_name}' in {receiver_country}.")

        # If stakeholder is specified, check their leaves & calendar events
        if stakeholder_id:
            stakeholder = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
            sme_name = stakeholder.name if stakeholder else f"ID {stakeholder_id}"

            # 3. Leave check
            leaves = (
                db.query(StakeholderLeave)
                .filter(
                    StakeholderLeave.stakeholder_id == stakeholder_id,
                    StakeholderLeave.start_date <= target_date,
                    StakeholderLeave.end_date >= target_date,
                )
                .all()
            )
            for leave in leaves:
                conflicts.append(f"Leave Conflict: {sme_name} is on leave ({leave.reason}) on {target_date.isoformat()}.")

            # 4. Calendar event check
            slot_start_dt = datetime.combine(target_date, start_time)
            slot_end_dt = datetime.combine(target_date, end_time)

            day_start = datetime.combine(target_date, time(0, 0, 0))
            day_end = datetime.combine(target_date, time(23, 59, 59))

            cal_events = (
                db.query(CalendarEvent)
                .filter(
                    CalendarEvent.stakeholder_id == stakeholder_id,
                    CalendarEvent.start_time <= day_end,
                    CalendarEvent.end_time >= day_start,
                )
                .all()
            )

            for ev in cal_events:
                if ev.is_all_day:
                    conflicts.append(f"Calendar Conflict: {sme_name} has all-day event '{ev.subject}'.")
                else:
                    # Check overlap: (StartA < EndB) and (EndA > StartB)
                    if ev.start_time < slot_end_dt and ev.end_time > slot_start_dt:
                        conflicts.append(
                            f"Calendar Conflict: {sme_name} is busy '{ev.subject}' "
                            f"({ev.start_time.strftime('%H:%M')} - {ev.end_time.strftime('%H:%M')})."
                        )

        return conflicts

    @staticmethod
    def get_transition_availability_matrix(
        db: Session,
        transition_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Generates day-by-day availability summary for all transition stakeholders.
        """
        transition = db.query(Transition).filter(Transition.id == transition_id).first()
        if not transition:
            raise ValueError(f"Transition {transition_id} not found")

        sme_country = transition.sme_country or transition.primary_country or "India"
        receiver_country = transition.receiver_country or "India"
        s_date = start_date or transition.start_date
        e_date = end_date or transition.end_date
        stakeholders = db.query(Stakeholder).filter(Stakeholder.transition_id == transition_id).all()

        holiday_service = HolidayService.get_instance()
        days_summary = []

        cur = s_date
        while cur <= e_date:
            is_weekend = HolidayService.is_weekend(cur)
            is_sme_hol, sme_hol_name = holiday_service.is_holiday(sme_country, cur)
            is_rcv_hol, rcv_hol_name = (False, None)
            if receiver_country != sme_country:
                is_rcv_hol, rcv_hol_name = holiday_service.is_holiday(receiver_country, cur)

            is_hol = is_sme_hol or is_rcv_hol
            hol_name = None
            if is_sme_hol and is_rcv_hol:
                hol_name = f"{sme_hol_name} ({sme_country}) & {rcv_hol_name} ({receiver_country})"
            elif is_sme_hol:
                hol_name = f"{sme_hol_name} ({sme_country})"
            elif is_rcv_hol:
                hol_name = f"{rcv_hol_name} ({receiver_country})"

            day_status = "WORKING_DAY"
            if is_weekend:
                day_status = "WEEKEND"
            elif is_hol:
                day_status = "BANK_HOLIDAY"

            sme_statuses = {}
            for s in stakeholders:
                if day_status != "WORKING_DAY":
                    sme_statuses[s.id] = {"available": False, "reason": day_status}
                    continue

                # Check leave
                on_leave = (
                    db.query(StakeholderLeave)
                    .filter(
                        StakeholderLeave.stakeholder_id == s.id,
                        StakeholderLeave.start_date <= cur,
                        StakeholderLeave.end_date >= cur,
                    )
                    .first()
                )
                if on_leave:
                    sme_statuses[s.id] = {"available": False, "reason": f"Leave: {on_leave.reason}"}
                    continue

                # Count busy calendar hours
                day_start = datetime.combine(cur, time(0, 0, 0))
                day_end = datetime.combine(cur, time(23, 59, 59))
                events = (
                    db.query(CalendarEvent)
                    .filter(
                        CalendarEvent.stakeholder_id == s.id,
                        CalendarEvent.start_time <= day_end,
                        CalendarEvent.end_time >= day_start,
                    )
                    .all()
                )
                busy_hours = 0.0
                for ev in events:
                    if ev.is_all_day:
                        busy_hours = 8.0
                    else:
                        duration = (ev.end_time - ev.start_time).total_seconds() / 3600.0
                        busy_hours += duration

                available_hours = max(0.0, 8.0 - busy_hours)
                sme_statuses[s.id] = {
                    "available": available_hours >= 2.0,
                    "busy_hours": round(busy_hours, 1),
                    "available_hours": round(available_hours, 1),
                    "reason": "Calendar Commitments" if busy_hours > 0 else "Available",
                }

            days_summary.append({
                "date": cur.isoformat(),
                "day_of_week": cur.strftime("%A"),
                "status": day_status,
                "holiday_name": hol_name,
                "sme_statuses": sme_statuses,
            })
            cur += timedelta(days=1)

        return {
            "transition_id": transition_id,
            "sme_country": sme_country,
            "receiver_country": receiver_country,
            "country": f"{sme_country} & {receiver_country}" if sme_country != receiver_country else sme_country,
            "start_date": s_date.isoformat(),
            "end_date": e_date.isoformat(),
            "stakeholders": [{"id": s.id, "name": s.name, "role": s.role} for s in stakeholders],
            "days": days_summary,
        }

