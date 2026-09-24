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

        transcripts_response = client.get(f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts")
        assert transcripts_response.status_code == 200
        assert [document["file_name"] for document in transcripts_response.json()["transcripts"]] == ["meeting.vtt"]
    finally:
        db.query(Transition).filter(Transition.id == transition.id).delete()
        db.commit()
        db.close()