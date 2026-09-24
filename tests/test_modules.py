from datetime import date, time

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models.knowledge import KnowledgeNode
from backend.models.scheduling import KTSession
from backend.models.stakeholder import Stakeholder
from backend.models.transition import Transition


client = TestClient(app)


def test_teams_scheduler_and_tracker_modules():
    db = SessionLocal()
    transition = Transition(name="Modules API Test")
    db.add(transition)
    db.flush()

    node = KnowledgeNode(transition_id=transition.id, node_type="topic", name="Modules Topic")
    sme = Stakeholder(transition_id=transition.id, name="Scheduler SME", email="sme@example.com", role="sme")
    receiver = Stakeholder(transition_id=transition.id, name="Scheduler Receiver", email="receiver@example.com", role="receiver")
    db.add_all([node, sme, receiver])
    db.flush()
    session = KTSession(
        transition_id=transition.id,
        node_id=node.id,
        sme_id=sme.id,
        receiver_id=receiver.id,
        session_title="Teams Scheduler Test Session",
        scheduled_date=date(2026, 9, 28),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    db.add(session)
    db.commit()

    try:
        modules_response = client.get("/api/v1/modules")
        assert modules_response.status_code == 200
        assert {module["number"] for module in modules_response.json()} == {13, 14}

        scheduler_response = client.get(f"/api/v1/transitions/{transition.id}/teams-kt-scheduler")
        assert scheduler_response.status_code == 200
        scheduler_session = scheduler_response.json()["sessions"][0]
        assert scheduler_session["id"] == session.id
        assert scheduler_session["recipients"] == ["sme@example.com", "receiver@example.com"]

        invalid_schedule = client.post(
            f"/api/v1/transitions/{transition.id}/teams-kt-scheduler/schedule",
            files={"file": ("schedule.txt", b"not csv", "text/plain")},
        )
        assert invalid_schedule.status_code == 422
        schedule_import = client.post(
            f"/api/v1/transitions/{transition.id}/teams-kt-scheduler/schedule",
            files={"file": ("teams-schedule.csv", b"Title,Date,Start,End,Required Attendees\nImported Teams Session,2026-09-29,13:00,14:00,source@example.com;other@example.com\n", "text/csv")},
        )
        assert schedule_import.status_code == 200
        assert schedule_import.json()["imported"] == 1
        assert schedule_import.json()["sessions"][0]["recipients"] == ["source@example.com", "other@example.com"]

        invite_response = client.post(
            f"/api/v1/transitions/{transition.id}/teams-kt-scheduler/invites",
            json={"session_ids": [session.id], "dry_run": True},
        )
        assert invite_response.status_code == 200
        assert invite_response.json()["dry_run_count"] == 1

        tracker_response = client.get(f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts")
        assert tracker_response.status_code == 200
        assert tracker_response.json()["transcripts"] == []

        invalid_upload = client.post(
            f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts",
            files={"file": ("notes.txt", b"not a transcript", "text/plain")},
        )
        assert invalid_upload.status_code == 422

        upload_response = client.post(
            f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts",
            files={"file": ("meeting.vtt", b"WEBVTT\n\n00:00.000 --> 00:01.000\nKT session", "text/vtt")},
        )
        assert upload_response.status_code == 200
        assert upload_response.json()["transcript"]["file_name"] == "meeting.vtt"

        tracker_dashboard = client.get(f"/api/v1/transitions/{transition.id}/kt-tracker")
        assert tracker_dashboard.status_code == 200
        activities = tracker_dashboard.json()["activities"]
        assert len(activities) == 2
        test_activity = next(activity for activity in activities if activity["session_id"] == session.id)
        update_activity = client.put(
            f"/api/v1/transitions/{transition.id}/kt-tracker/activities/{test_activity['id']}",
            json={"progress_percent": 40, "blocker": "Awaiting environment access"},
        )
        assert update_activity.status_code == 200
        assert update_activity.json()["blocker"] == "Awaiting environment access"

        substantive_transcript = client.post(
            f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts",
            files={"file": ("covered.vtt", b"WEBVTT\n\n00:00:00.000 --> 00:00:20.000\nTeams Scheduler Test Session was covered thoroughly with configuration details, demonstrations, ownership decisions, review steps, validation notes, and documented follow up actions.\n", "text/vtt")},
        )
        assert substantive_transcript.status_code == 200
        analysis_response = client.post(
            f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts/{substantive_transcript.json()['transcript']['id']}/analyze?activity_id={test_activity['id']}"
        )
        assert analysis_response.status_code == 200
        assert analysis_response.json()["analysis"]["topics_covered"] == ["Teams Scheduler Test Session"]
        assert analysis_response.json()["activity"]["status"] == "completed"

        transcripts_response = client.get(f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts")
        assert transcripts_response.status_code == 200
        assert {document["file_name"] for document in transcripts_response.json()["transcripts"]} == {"meeting.vtt", "covered.vtt"}
    finally:
        db.query(Transition).filter(Transition.id == transition.id).delete()
        db.commit()
        db.close()