from datetime import date, time

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models.knowledge import KnowledgeNode
from backend.models.scheduling import KTSession
from backend.models.stakeholder import Stakeholder
from backend.models.transition import Transition


client = TestClient(app)


def test_teams_scheduler_and_tracker_modules(monkeypatch):
    db = SessionLocal()
    transition = Transition(name="Modules API Test")
    db.add(transition)
    db.flush()

    node = KnowledgeNode(transition_id=transition.id, node_type="topic", name="Modules Topic")
    sme = Stakeholder(transition_id=transition.id, name="Scheduler SME", email="vivek.chaurasia@vwgds.in", role="sme")
    receiver = Stakeholder(transition_id=transition.id, name="Scheduler Receiver", email="atharva.utekar@vwgds.in", role="receiver")
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
        assert scheduler_session["recipients"] == ["vivek.chaurasia@vwgds.in", "atharva.utekar@vwgds.in"]

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
            json={"dry_run": True, "max_sessions": 1},
        )
        assert invite_response.status_code == 200
        assert invite_response.json()["dry_run_count"] == 1
        assert invite_response.json()["skipped"] == 1

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
            json={
                "progress_percent": 40,
                "blocker": "Awaiting environment access",
                "attendees": ["sme@example.com", "receiver@example.com"],
                "actual_hours": 1.5,
                "session_notes": "Walkthrough completed with follow-up actions.",
                "open_questions": ["Who owns production deployment?"],
                "documents_delivered": ["Runbook.pdf"],
                "shadowing_completed": True,
                "reverse_shadowing_completed": False,
                "readiness": "partially_ready",
                "final_acceptance": False,
            },
        )
        assert update_activity.status_code == 200
        assert update_activity.json()["blocker"] == "Awaiting environment access"
        assert update_activity.json()["manual_evidence"]["actual_hours"] == 1.5

        linked_upload = client.post(
            f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts",
            data={"activity_id": test_activity["id"]},
            files={"file": ("linked.vtt", b"WEBVTT\n\n00:00.000 --> 00:01.000\nLinked tracker transcript", "text/vtt")},
        )
        assert linked_upload.status_code == 200
        tracker_with_link = client.get(f"/api/v1/transitions/{transition.id}/kt-tracker")
        linked_activity = next(activity for activity in tracker_with_link.json()["activities"] if activity["id"] == test_activity["id"])
        assert linked_activity["manual_evidence"]["transcript"]["file_name"] == "linked.vtt"

        document_id = linked_upload.json()['transcript']['id']
        review_url = f'/api/v1/transitions/{transition.id}/kt-tracker/transcripts/{document_id}/review'
        preview = client.get(review_url, params={'meeting_date': '2026-09-28'})
        assert preview.status_code == 200
        assert preview.json()['activities'][0]['id'] == test_activity['id']
        assert preview.json()['activities'][0]['reason'] == 'Scheduled for this day'
        assert linked_activity['status'] == 'planned'
        from backend.routers import modules
        calls = []

        async def fake_assessment(raw_text, model):
            calls.append(raw_text)
            return {'source': 'ai', 'summary': 'No supported open issues identified.', 'findings': []}

        monkeypatch.setattr(modules, 'analyze_meeting_followups', fake_assessment)
        analysis_url = f'/api/v1/transitions/{transition.id}/kt-tracker/transcripts/{document_id}/ai-analysis'
        monkeypatch.setenv('LLMAAS_API_KEY', 'sk-local-dev-placeholder')
        assert client.post(analysis_url).status_code == 503
        assert calls == []
        monkeypatch.setenv('LLMAAS_API_KEY', 'test-configured-key')
        assert client.post(analysis_url).status_code == 200
        assert client.post(analysis_url).status_code == 200
        assert len(calls) == 1
        saved_preview = client.get(review_url, params={'meeting_date': '2026-09-28'}).json()
        assert saved_preview['ai_analysis']['source'] == 'ai'
        assert client.post(analysis_url.replace(transition.id, 'unknown-transition')).status_code == 404

        async def unavailable_assessment(raw_text, model):
            raise RuntimeError('AI provider unavailable')

        monkeypatch.setattr(modules, 'analyze_meeting_followups', unavailable_assessment)
        assert client.post(analysis_url + '?refresh=true').status_code == 503
        assert client.post(analysis_url).json()['summary'] == 'No supported open issues identified.'
        invalid_review = client.post(review_url, json={'meeting_date': '2026-09-28', 'activity_ids': ['missing']})
        assert invalid_review.status_code == 404
        for attempt in range(2):
            saved = client.post(review_url, json={'meeting_date': '2026-09-28', 'activity_ids': [test_activity['id']]})
            assert saved.status_code == 200
        reviewed_activities = client.get(f'/api/v1/transitions/{transition.id}/kt-tracker').json()['activities']
        reviewed = next(activity for activity in reviewed_activities if activity['id'] == test_activity['id'])
        assert reviewed['status'] == 'in_progress'
        assert reviewed['manual_evidence']['actual_hours'] == 1.5
        assert len(reviewed['transcript_analysis']['meeting_reviews']) == 1
        assert all(activity['status'] == 'planned' for activity in reviewed_activities if activity['id'] != test_activity['id'])

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
        assert analysis_response.json()["activity"]["manual_evidence"]["attendees"] == ["sme@example.com", "receiver@example.com"]
        assert analysis_response.json()["activity"]["manual_evidence"]["documents_delivered"] == ["Runbook.pdf"]
        assert len(analysis_response.json()['activity']['transcript_analysis']['meeting_reviews']) == 1

        other_activity = next(activity for activity in reviewed_activities if activity['id'] != test_activity['id'])
        relinked = client.post(review_url, json={'meeting_date': '2026-09-29', 'activity_ids': [other_activity['id']]})
        assert relinked.status_code == 200
        refreshed = client.get(f'/api/v1/transitions/{transition.id}/kt-tracker').json()['activities']
        original = next(activity for activity in refreshed if activity['id'] == test_activity['id'])
        assert original['status'] == 'completed'
        assert original['transcript_analysis']['meeting_reviews'] == {}

        transcripts_response = client.get(f"/api/v1/transitions/{transition.id}/kt-tracker/transcripts")
        assert transcripts_response.status_code == 200
        assert {document["file_name"] for document in transcripts_response.json()["transcripts"]} == {"meeting.vtt", "linked.vtt", "covered.vtt"}
    finally:
        db.query(Transition).filter(Transition.id == transition.id).delete()
        db.commit()
        db.close()


def test_teams_vtt_meeting_extraction():
    from backend.services.transcript_analysis_service import extract_meeting_details, analyze_transcript
    transcript = '''WEBVTT

meeting-id/1-0
00:00:05.000 --> 00:00:10.000
<v Example, Alex>We will share the runbook. Production access is not available.</v>

meeting-id/2-0
00:01:00.000 --> 00:01:05.000
<v Example, Sam>Who owns deployment?</v>
'''
    details = extract_meeting_details(transcript)
    assert details['speakers'] == ['Example, Alex', 'Example, Sam']
    assert details['duration_minutes'] == 1
    assert details['questions'][0]['text'] == 'Who owns deployment?'
    assert details['actions'][0]['start'] == '00:00:05.000'
    assert details['concerns'][0]['text'] == 'Production access is not available.'
    assert details['documents_mentioned'][0]['text'] == 'We will share the runbook.'
    assert 'meeting-id' not in analyze_transcript(transcript, [])['summary']


def test_ai_meeting_followups_validate_evidence():
    import asyncio
    import json
    import pytest
    from backend.services.transcript_analysis_service import analyze_meeting_followups

    transcript = 'WEBVTT\n\n00:00:00.000 --> 00:00:04.000\n<v Alex>Production access is blocked. Discuss next call.</v>'
    response = {'summary': 'Access needs follow-up.', 'findings': [{
        'kind': 'open_issue', 'priority': 'high', 'status': 'open', 'title': 'Production access',
        'detail': 'Access is blocked.', 'next_call_question': 'Has production access been granted?',
        'suggested_action': 'Confirm access with the system owner.', 'evidence_ids': [0],
    }]}

    class FakeModel:
        async def ainvoke(self, messages):
            assert 'untrusted evidence' in messages[0]['content']
            assert 'Production access is blocked' in messages[1]['content']
            return {'content': json.dumps(response)}

    result = asyncio.run(analyze_meeting_followups(transcript, FakeModel()))
    assert result['source'] == 'ai'
    assert result['findings'][0]['evidence'][0]['speaker'] == 'Alex'
    assert result['findings'][0]['evidence'][0]['start'] == '00:00:00.000'
    response['findings'][0]['evidence_ids'] = [99]
    with pytest.raises(ValueError, match='unverifiable'):
        asyncio.run(analyze_meeting_followups(transcript, FakeModel()))
    response['findings'] = []
    assert asyncio.run(analyze_meeting_followups(transcript, FakeModel()))['findings'] == []
    with pytest.raises(RuntimeError, match='unavailable'):
        asyncio.run(analyze_meeting_followups(transcript, None))