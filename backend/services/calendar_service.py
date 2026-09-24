import csv
import io
from datetime import datetime, time, date
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser
from sqlalchemy.orm import Session
from backend.models.stakeholder import CalendarEvent, Stakeholder

class CalendarImportService:
    @staticmethod
    def parse_outlook_csv(
        csv_content: str,
        stakeholder_id: str,
        db: Session,
        mask_subjects: bool = False
    ) -> List[CalendarEvent]:
        """
        Parses Outlook exported CSV.
        Expected headers (case-insensitive):
        - Subject
        - Start Date
        - Start Time
        - End Date
        - End Time
        - All day event (True/False)
        - Reminder on/off (True/False)
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        normalized_fieldnames = {col.strip().lower(): col for col in reader.fieldnames or []}
        
        def get_val(row: dict, key: str, default: str = "") -> str:
            original_col = normalized_fieldnames.get(key.lower())
            if original_col and original_col in row:
                return (row[original_col] or "").strip()
            return default

        events = []
        for row in reader:
            subj = get_val(row, "subject", "Busy")
            start_date_str = get_val(row, "start date")
            start_time_str = get_val(row, "start time", "09:00:00")
            end_date_str = get_val(row, "end date", start_date_str)
            end_time_str = get_val(row, "end time", "10:00:00")
            all_day_str = get_val(row, "all day event", "False").lower()
            reminder_str = get_val(row, "reminder on/off", "False").lower()

            if not start_date_str:
                continue

            try:
                # Parse start datetime
                combined_start_str = f"{start_date_str} {start_time_str}"
                start_dt = date_parser.parse(combined_start_str)

                # Parse end datetime
                combined_end_str = f"{end_date_str} {end_time_str}"
                end_dt = date_parser.parse(combined_end_str)

                is_all_day = all_day_str in ("true", "1", "yes")
                has_reminder = reminder_str in ("true", "1", "yes")

                display_subject = "Busy Event" if mask_subjects else subj

                event = CalendarEvent(
                    stakeholder_id=stakeholder_id,
                    subject=display_subject,
                    start_time=start_dt,
                    end_time=end_dt,
                    is_all_day=is_all_day,
                    has_reminder=has_reminder,
                )
                db.add(event)
                events.append(event)
            except Exception:
                # Skip invalid date rows gracefully
                continue

        db.commit()
        return events

