from datetime import datetime
from backend.services.calendar_service import CalendarImportService
from backend.database import SessionLocal, Base, engine
from backend.models.transition import Transition
from backend.models.stakeholder import Stakeholder

def test_outlook_csv_parser():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        t = Transition(name="Test Transition")
        db.add(t)
        db.commit()

        sme = Stakeholder(transition_id=t.id, name="Alice SME", role="sme")
        db.add(sme)
        db.commit()

        # Outlook standard CSV format
        sample_csv = """Subject,Start Date,Start Time,End Date,End Time,All day event,Reminder on/off
Architecture Review,2026-09-22,10:00:00,2026-09-22,12:00:00,False,True
Team Standup,2026-09-23,09:30:00,2026-09-23,10:00:00,False,False
Sprint Planning,2026-09-24,00:00:00,2026-09-24,23:59:59,True,False
"""
        events = CalendarImportService.parse_outlook_csv(
            csv_content=sample_csv,
            stakeholder_id=sme.id,
            db=db,
            mask_subjects=False,
        )
        assert len(events) == 3
        assert events[0].subject == "Architecture Review"
        assert events[0].is_all_day is False
        assert events[2].is_all_day is True

        # Test with subject masking
        events_masked = CalendarImportService.parse_outlook_csv(
            csv_content=sample_csv,
            stakeholder_id=sme.id,
            db=db,
            mask_subjects=True,
        )
        assert len(events_masked) == 3
        assert events_masked[0].subject == "Busy Event"
    finally:
        db.close()

