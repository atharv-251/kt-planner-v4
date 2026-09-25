from __future__ import annotations

import shutil
import smtplib
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.config import UPLOADS_DIR
from backend import config
from backend.database import get_db
from backend.models.knowledge import KnowledgeNode
from backend.models.scheduling import KTSession
from backend.models.tracker import KTTrackingActivity, KTTranscriptAssessment
from backend.models.transition import Transition, UploadedDocument
from backend.services.schedule_import_service import parse_schedule_csv
from backend.services.teams_scheduler_service import invite_was_sent, send_teams_invite, valid_recipients
from backend.services.transcript_analysis_service import analyze_transcript, extract_meeting_details, analyze_meeting_followups

router = APIRouter(tags=["KT Planner Modules"])


class TeamsInviteRequest(BaseModel):
    session_ids: list[str] | None = None
    recipients: list[str] | None = Field(default=None, description="Optional test recipients that replace session participants.")
    dry_run: bool = False
    max_invites_per_recipient: int = Field(default=1, ge=1, le=10)
    max_sessions: int | None = Field(default=None, ge=1, le=1000)


class TrackerActivityUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(planned|in_progress|completed|on_hold|cancelled)$")
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    blocker: str | None = Field(default=None, max_length=2000)
    risk: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    attendees: list[str] | None = Field(default=None, max_length=100)
    actual_hours: float | None = Field(default=None, ge=0, le=24)
    session_notes: str | None = Field(default=None, max_length=4000)
    open_questions: list[str] | None = Field(default=None, max_length=50)
    documents_delivered: list[str] | None = Field(default=None, max_length=100)
    shadowing_completed: bool | None = None
    reverse_shadowing_completed: bool | None = None
    readiness: str | None = Field(default=None, pattern="^(not_assessed|not_ready|partially_ready|ready|accepted)$")
    final_acceptance: bool | None = None


class TrackerSyncRequest(BaseModel):
    transcript_id: str | None = None


class MeetingReviewRequest(BaseModel):
    meeting_date: date
    activity_ids: list[str] = Field(min_length=1, max_length=100)


@router.get("/api/v1/modules")
def list_modules() -> list[dict[str, object]]:
    return [
        {"number": 13, "stage": 13, "name": "Stage 13: Teams KT Scheduler", "description": "Send Teams-compatible SMTP invitations for KT Planner sessions.", "path": "/api/v1/transitions/{transition_id}/teams-kt-scheduler"},
        {"number": 14, "stage": 14, "name": "Stage 14: KT Tracker", "description": "Attach and retrieve Teams transcripts for a transition.", "path": "/api/v1/transitions/{transition_id}/kt-tracker/transcripts"},
    ]


@router.get("/api/v1/transitions/{transition_id}/teams-kt-scheduler")
def get_teams_scheduler(transition_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    transition = _transition_or_404(transition_id, db)
    sessions = _sessions(transition_id, db)
    return {"module": 13, "stage": 13, "name": "Stage 13: Teams KT Scheduler", "sessions": [_session_payload(session, transition) for session in sessions]}


@router.post("/api/v1/transitions/{transition_id}/teams-kt-scheduler/schedule")
async def import_teams_schedule(transition_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, object]:
    transition = _transition_or_404(transition_id, db)
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Schedule imports must use a CSV file.")
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(status_code=413, detail="Schedule CSV must be 5 MB or smaller.")
    try:
        imported_sessions = parse_schedule_csv(content)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    source_node = KnowledgeNode(transition_id=transition_id, node_type="topic", name="Imported Teams Schedule")
    db.add(source_node)
    db.flush()
    sessions = [KTSession(
        transition_id=transition_id,
        node_id=source_node.id,
        session_title=item["title"],
        duration_hours=round((datetime.combine(date.min, item["end_time"]) - datetime.combine(date.min, item["start_time"])).seconds / 3600, 2),
        scheduled_date=item["scheduled_date"],
        start_time=item["start_time"],
        end_time=item["end_time"],
        delivery_mode="workshop",
        status="proposed",
        conflict_flags={"source_recipients": item["attendees"], "source": "teams_schedule_csv"},
    ) for item in imported_sessions]
    db.add_all(sessions)
    db.commit()
    return {"module": 13, "stage": 13, "imported": len(sessions), "sessions": [_session_payload(session, transition) for session in sessions]}


@router.post("/api/v1/transitions/{transition_id}/teams-kt-scheduler/invites")
def send_teams_invites(transition_id: str, payload: TeamsInviteRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    transition = _transition_or_404(transition_id, db)
    sessions = _sessions(transition_id, db)
    if payload.session_ids is not None:
        selected = set(payload.session_ids)
        sessions = [session for session in sessions if session.id in selected]
        if len(selected) != len(sessions):
            raise HTTPException(status_code=404, detail="One or more sessions were not found for this transition.")
    if not sessions:
        raise HTTPException(status_code=422, detail="No scheduled KT sessions are available for invitation.")
    if not payload.dry_run and (not os.getenv("KT_SCHEDULER_SENDER_EMAIL") or not os.getenv("KT_SCHEDULER_SMTP_SERVER")):
        raise HTTPException(
            status_code=503,
            detail="Email delivery is not configured. Set KT_SCHEDULER_SENDER_EMAIL and KT_SCHEDULER_SMTP_SERVER in .env, then restart the server.",
        )

    override_recipients = valid_recipients(payload.recipients or [])
    attempted: dict[str, int] = {}
    results: list[dict[str, str]] = []
    processed_sessions = 0
    for session in sessions:
        if payload.max_sessions is not None and processed_sessions >= payload.max_sessions:
            results.append({"session_id": session.id, "status": "skipped", "message": "Test session limit reached."})
            continue
        recipients = override_recipients or _session_recipients(session)
        recipients = [email for email in recipients if attempted.get(email, 0) < payload.max_invites_per_recipient]
        if not recipients:
            results.append({"session_id": session.id, "status": "skipped", "message": "Recipient invite limit reached or no recipient email is assigned."})
            continue
        try:
            result = send_teams_invite(session_id=session.id, title=session.session_title, start_at=_session_start(session, transition), end_at=_session_end(session, transition), recipients=recipients, dry_run=payload.dry_run)
            results.append(result)
            if result["status"] in {"sent", "dry_run"}:
                processed_sessions += 1
                for email in recipients:
                    attempted[email] = attempted.get(email, 0) + 1
        except (OSError, ValueError, smtplib.SMTPException) as error:
            results.append({"session_id": session.id, "status": "failed", "message": str(error)})

    return {"module": 13, "stage": 13, "dry_run": payload.dry_run, "total_sessions": len(sessions), "sent": sum(item["status"] == "sent" for item in results), "dry_run_count": sum(item["status"] == "dry_run" for item in results), "skipped": sum(item["status"] == "skipped" for item in results), "failed": sum(item["status"] == "failed" for item in results), "results": results}


@router.get("/api/v1/transitions/{transition_id}/kt-tracker/transcripts")
def list_teams_transcripts(transition_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    documents = db.query(UploadedDocument).filter(UploadedDocument.transition_id == transition_id).order_by(UploadedDocument.uploaded_at.desc()).all()
    transcripts = [document for document in documents if document.file_name.lower().endswith(".vtt")]
    return {"module": 14, "stage": 14, "name": "Stage 14: KT Tracker", "transcripts": [_document_payload(document) for document in transcripts]}


@router.post("/api/v1/transitions/{transition_id}/kt-tracker/sync-demo")
def sync_tracker_from_uploaded_transcript(
    transition_id: str,
    payload: TrackerSyncRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Run the Graph-shaped tracker lifecycle using local schedule and VTT data.

    This is deliberately the same downstream behavior expected from Graph: a
    scheduled meeting is deduplicated, its transcript is analyzed, and status
    changes only when transcript evidence supports completion.
    """
    _transition_or_404(transition_id, db)
    transcript_query = db.query(UploadedDocument).filter(
        UploadedDocument.transition_id == transition_id,
        UploadedDocument.file_name.ilike("%.vtt"),
    )
    if payload.transcript_id:
        transcript = transcript_query.filter(UploadedDocument.id == payload.transcript_id).first()
    else:
        transcript = transcript_query.order_by(UploadedDocument.uploaded_at.desc()).first()
    if not transcript:
        raise HTTPException(status_code=422, detail="Upload a Teams .vtt transcript before running demo sync.")

    try:
        transcript_text = Path(transcript.file_path).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Unable to read transcript: {error}") from error

    activities = _tracker_activities(transition_id, db)
    if not activities:
        _sync_session_activities(transition_id, [], db)
        db.commit()
        activities = _tracker_activities(transition_id, db)
    if not activities:
        raise HTTPException(status_code=422, detail="Create or import scheduled KT sessions before running tracker sync.")

    synced = []
    for activity in activities:
        session = db.query(KTSession).filter(KTSession.id == activity.session_id).first()
        if not session:
            continue
        expected_topics = activity.expected_topics or [session.session_title]
        analysis = analyze_transcript(transcript_text, expected_topics)
        analysis["source"] = "uploaded_transcript_demo_graph"
        analysis["transcript_id"] = transcript.id
        analysis["external_meeting_id"] = f"demo:{transition_id}:{session.id}"
        analysis["manual_evidence"] = _manual_evidence(activity)
        analysis["meeting_reviews"] = (activity.transcript_analysis or {}).get("meeting_reviews", {})
        activity.expected_topics = expected_topics
        activity.transcript_analysis = analysis
        activity.notes = (
            f"Demo Graph sync from {transcript.file_name}. "
            f"Follow-up topics: {', '.join(analysis['topics_partially_covered'] + analysis['topics_missed']) or 'none'}."
        )
        follow_up_topics = analysis["topics_partially_covered"] + analysis["topics_missed"]
        if not follow_up_topics and expected_topics and analysis["topics_covered"]:
            activity.status = "completed"
            activity.progress_percent = 100
        elif analysis["topics_covered"] or analysis["topics_partially_covered"]:
            activity.status = "in_progress"
            activity.progress_percent = round(100 * len(analysis["topics_covered"]) / len(expected_topics))
            activity.risk = f"Follow-up required: {', '.join(follow_up_topics)}" if follow_up_topics else ""
        else:
            activity.status = "in_progress"
            activity.progress_percent = 0
            activity.risk = "No expected topics were evidenced in the transcript."
        session.conflict_flags = {
            **(session.conflict_flags if isinstance(session.conflict_flags, dict) else {}),
            "external_meeting_id": f"demo:{transition_id}:{session.id}",
            "graph_mode": "demo",
            "transcript_id": transcript.id,
        }
        synced.append(_activity_payload(activity, db))

    db.commit()
    return {
        "mode": os.getenv("KT_GRAPH_MODE", "demo").lower(),
        "source": "uploaded_transcript",
        "transcript": transcript.file_name,
        "synced_count": len(synced),
        "activities": synced,
    }


@router.post("/api/v1/transitions/{transition_id}/kt-tracker/transcripts")
async def upload_teams_transcript(
    transition_id: str,
    file: UploadFile = File(...),
    activity_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".vtt"):
        raise HTTPException(status_code=422, detail="Teams transcripts must use the .vtt format.")
    target_path = UPLOADS_DIR / f"{transition_id}_teams_transcript_{uuid4().hex}.vtt"
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    document = UploadedDocument(transition_id=transition_id, file_name=filename, file_path=str(target_path), file_size=target_path.stat().st_size, mime_type="text/vtt")
    db.add(document)
    db.commit()
    db.refresh(document)
    if activity_id:
        activity = db.query(KTTrackingActivity).filter(
            KTTrackingActivity.id == activity_id,
            KTTrackingActivity.transition_id == transition_id,
        ).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Tracker activity not found")
        evidence = _manual_evidence(activity)
        evidence["transcript"] = _document_payload(document)
        activity.transcript_analysis = {**(activity.transcript_analysis or {}), "manual_evidence": evidence}
        db.commit()
    return {"module": 14, "transcript": _document_payload(document)}


@router.get("/api/v1/transitions/{transition_id}/kt-tracker")
def get_kt_tracker(transition_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    activities = _tracker_activities(transition_id, db)
    _sync_session_activities(transition_id, activities, db)
    db.commit()
    activities = _tracker_activities(transition_id, db)
    return {"module": 14, "summary": _tracker_summary(activities, db), "activities": [_activity_payload(activity, db) for activity in activities]}


@router.put("/api/v1/transitions/{transition_id}/kt-tracker/activities/{activity_id}")
def update_tracker_activity(transition_id: str, activity_id: str, payload: TrackerActivityUpdate, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    activity = db.query(KTTrackingActivity).filter(KTTrackingActivity.id == activity_id, KTTrackingActivity.transition_id == transition_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Tracker activity not found")
    update_data = payload.model_dump(exclude_unset=True)
    evidence_fields = {
        "attendees", "actual_hours", "session_notes", "open_questions",
        "documents_delivered", "shadowing_completed", "reverse_shadowing_completed",
        "readiness", "final_acceptance",
    }
    for field_name, value in update_data.items():
        if field_name in evidence_fields:
            continue
        setattr(activity, field_name, value)
    evidence_updates = {key: value for key, value in update_data.items() if key in evidence_fields}
    if evidence_updates:
        evidence = _manual_evidence(activity)
        evidence.update(evidence_updates)
        activity.transcript_analysis = {**(activity.transcript_analysis or {}), "manual_evidence": evidence}
    if activity.status == "completed":
        activity.progress_percent = 100
    db.commit()
    db.refresh(activity)
    return _activity_payload(activity, db)


@router.post("/api/v1/transitions/{transition_id}/kt-tracker/transcripts/{document_id}/analyze")
def analyze_teams_transcript(transition_id: str, document_id: str, activity_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    document = db.query(UploadedDocument).filter(UploadedDocument.id == document_id, UploadedDocument.transition_id == transition_id).first()
    activity = db.query(KTTrackingActivity).filter(KTTrackingActivity.id == activity_id, KTTrackingActivity.transition_id == transition_id).first()
    if not document or not document.file_name.lower().endswith(".vtt"):
        raise HTTPException(status_code=404, detail="Teams transcript not found")
    if not activity:
        raise HTTPException(status_code=404, detail="Tracker activity not found")
    try:
        transcript_text = Path(document.file_path).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Unable to read transcript: {error}") from error
    analysis = analyze_transcript(transcript_text, activity.expected_topics or [activity.activity_name])
    activity.transcript_analysis = {
        **(activity.transcript_analysis or {}),
        **analysis,
        "manual_evidence": _manual_evidence(activity),
        "transcript_id": document.id,
    }
    if analysis["topics_covered"] and not analysis["topics_partially_covered"] and not analysis["topics_missed"]:
        activity.status = "completed"
        activity.progress_percent = 100
    elif activity.status == "planned":
        activity.status = "in_progress"
    db.commit()
    db.refresh(activity)
    return {"analysis": analysis, "activity": _activity_payload(activity, db)}


@router.get("/api/v1/transitions/{transition_id}/kt-tracker/transcripts/{document_id}/review")
def review_tracker_meeting(transition_id: str, document_id: str, meeting_date: date, db: Session = Depends(get_db)) -> dict:
    document, details, raw_text = _meeting_details(transition_id, document_id, db)
    activities = _tracker_activities(transition_id, db)
    sessions = {session.id: session for session in _sessions(transition_id, db)}
    words = set(re.findall(r'[a-z]{3,}', ' '.join(item['text'] for item in details['highlights']).lower()))
    words.update(re.findall(r'[a-z]{3,}', re.sub(r'<[^>]*>', '', raw_text).lower()))
    ignored = {'the', 'and', 'for', 'with', 'overview', 'session', 'hands', 'exercises', 'workshop', 'introduction', 'domain', 'development'}
    suggestions = []
    for activity in activities:
        session = sessions.get(activity.session_id)
        if not session or activity.status == 'cancelled':
            continue
        keywords = set(re.findall(r'[a-z]{3,}', activity.activity_name.lower())) - ignored
        matched = sorted(keywords & words)
        same_day = session.scheduled_date == meeting_date
        score = len(matched) / max(len(keywords), 1)
        suggestions.append({
            'id': activity.id, 'activity_name': activity.activity_name,
            'scheduled_date': session.scheduled_date.isoformat(), 'status': activity.status,
            'suggested': same_day or (len(matched) >= 2 and score >= 0.6),
            'reason': 'Scheduled for this day' if same_day else f"Matching terms: {', '.join(matched)}" if matched else 'No topic match',
            'score': score, 'same_day': same_day,
        })
    suggestions.sort(key=lambda item: (not item['same_day'], not item['suggested'], -item['score'], item['scheduled_date']))
    assessment = db.query(KTTranscriptAssessment).filter_by(document_id=document_id, transition_id=transition_id).first()
    return {'transcript': _document_payload(document), 'meeting_date': meeting_date.isoformat(), 'details': details, 'activities': suggestions, 'ai_analysis': assessment.result if assessment else None}


@router.post("/api/v1/transitions/{transition_id}/kt-tracker/transcripts/{document_id}/ai-analysis")
async def analyze_tracker_followups(transition_id: str, document_id: str, refresh: bool = False, db: Session = Depends(get_db)) -> dict:
    document, details, raw_text = _meeting_details(transition_id, document_id, db)
    assessment = db.query(KTTranscriptAssessment).filter_by(document_id=document_id, transition_id=transition_id).first()
    if assessment and not refresh:
        return assessment.result
    if os.getenv('LLMAAS_API_KEY', '').strip() in {'', 'sk-local-dev-placeholder'}:
        raise HTTPException(status_code=503, detail='AI analysis needs a valid LLMAAS_API_KEY. Replace the local setup placeholder in your environment configuration and restart the server. Never paste credentials into chat.')
    try:
        result = await analyze_meeting_followups(raw_text, config.llm)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    result['analyzed_at'] = datetime.now(timezone.utc).isoformat()
    if assessment:
        assessment.result = result
    else:
        db.add(KTTranscriptAssessment(document_id=document.id, transition_id=transition_id, result=result))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        saved = db.query(KTTranscriptAssessment).filter_by(document_id=document_id, transition_id=transition_id).first()
        if not saved:
            raise
        return saved.result
    return result


@router.post("/api/v1/transitions/{transition_id}/kt-tracker/transcripts/{document_id}/review")
def confirm_tracker_meeting(transition_id: str, document_id: str, payload: MeetingReviewRequest, db: Session = Depends(get_db)) -> dict:
    document, details, raw_text = _meeting_details(transition_id, document_id, db)
    selected_ids = set(payload.activity_ids)
    activities = db.query(KTTrackingActivity).filter(
        KTTrackingActivity.transition_id == transition_id, KTTrackingActivity.id.in_(selected_ids),
    ).all()
    if len(activities) != len(selected_ids):
        raise HTTPException(status_code=404, detail='One or more activities do not belong to this transition.')
    if any(activity.status == 'cancelled' for activity in activities):
        raise HTTPException(status_code=422, detail='Cancelled activities cannot receive a meeting review.')
    meeting = {'transcript': _document_payload(document), 'meeting_date': payload.meeting_date.isoformat(), **details}
    for activity in _tracker_activities(transition_id, db):
        existing = activity.transcript_analysis or {}
        if activity.id not in selected_ids and document.id in existing.get('meeting_reviews', {}):
            meetings = dict(existing['meeting_reviews'])
            del meetings[document.id]
            activity.transcript_analysis = {**existing, 'meeting_reviews': meetings}
    for activity in activities:
        existing = activity.transcript_analysis or {}
        meetings = dict(existing.get('meeting_reviews') or {})
        meetings[document.id] = meeting
        activity.transcript_analysis = {**existing, 'meeting_reviews': meetings}
        if activity.status == 'planned':
            activity.status = 'in_progress'
    db.commit()
    return {'updated_count': len(activities), 'transcript_id': document.id}


def _meeting_details(transition_id: str, document_id: str, db: Session) -> tuple:
    _transition_or_404(transition_id, db)
    document = db.query(UploadedDocument).filter(UploadedDocument.id == document_id, UploadedDocument.transition_id == transition_id).first()
    if not document or not document.file_name.lower().endswith('.vtt'):
        raise HTTPException(status_code=404, detail='Teams transcript not found')
    try:
        raw_text = Path(document.file_path).read_text(encoding='utf-8-sig')
        details = extract_meeting_details(raw_text)
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=422, detail='Transcript must contain readable UTF-8 WebVTT speech and timestamps.') from error
    except OSError as error:
        raise HTTPException(status_code=404, detail='Transcript file is unavailable. Please upload it again.') from error
    return document, details, raw_text


def _transition_or_404(transition_id: str, db: Session) -> Transition:
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")
    return transition


def _sessions(transition_id: str, db: Session) -> list[KTSession]:
    return db.query(KTSession).filter(KTSession.transition_id == transition_id).order_by(KTSession.scheduled_date, KTSession.start_time).all()


def _session_payload(session: KTSession, transition: Transition) -> dict[str, object]:
    recipients = _session_recipients(session)
    return {"id": session.id, "title": session.session_title, "level": session.level, "scheduled_date": session.scheduled_date, "start_time": session.start_time, "end_time": session.end_time, "status": session.status, "recipients": recipients, "mail_sent": invite_was_sent(session_id=session.id, start_at=_session_start(session, transition), end_at=_session_end(session, transition), recipients=recipients)}


def _session_recipients(session: KTSession) -> list[str]:
    source_recipients = session.conflict_flags.get("source_recipients", []) if isinstance(session.conflict_flags, dict) else []
    return valid_recipients([session.sme.email if session.sme else None, session.receiver.email if session.receiver else None, *source_recipients])


def _session_start(session: KTSession, transition: Transition) -> datetime:
    return datetime.combine(session.scheduled_date, session.start_time).replace(tzinfo=_timezone(transition))


def _session_end(session: KTSession, transition: Transition) -> datetime:
    return datetime.combine(session.scheduled_date, session.end_time).replace(tzinfo=_timezone(transition))


def _timezone(transition: Transition) -> ZoneInfo:
    try:
        return ZoneInfo(transition.timezone or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _document_payload(document: UploadedDocument) -> dict[str, object]:
    return {
        "id": document.id,
        "file_name": document.file_name,
        "file_size": document.file_size,
        "mime_type": document.mime_type,
        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
    }


def _tracker_activities(transition_id: str, db: Session) -> list[KTTrackingActivity]:
    return db.query(KTTrackingActivity).filter(KTTrackingActivity.transition_id == transition_id).order_by(KTTrackingActivity.created_at).all()


def _sync_session_activities(transition_id: str, activities: list[KTTrackingActivity], db: Session) -> None:
    tracked_session_ids = {activity.session_id for activity in activities}
    for session in _sessions(transition_id, db):
        if session.id in tracked_session_ids:
            continue
        db.add(KTTrackingActivity(
            transition_id=transition_id,
            session_id=session.id,
            activity_name=session.session_title,
            status="completed" if session.status == "completed" else "planned",
            progress_percent=100 if session.status == "completed" else 0,
            expected_topics=[session.session_title],
        ))


def _tracker_summary(activities: list[KTTrackingActivity], db: Session) -> dict[str, object]:
    total = len(activities)
    planned = sum(activity.status == "planned" for activity in activities)
    completed = sum(activity.status == "completed" for activity in activities)
    pending = sum(activity.status in {"planned", "in_progress", "on_hold"} for activity in activities)
    session_dates = {
        session.id: session.scheduled_date
        for session in db.query(KTSession).filter(KTSession.id.in_([activity.session_id for activity in activities])).all()
    } if activities else {}
    delayed = sum(
        session_dates.get(activity.session_id, date.max) < date.today()
        and activity.status not in {"completed", "cancelled"}
        for activity in activities
    )
    blocked = sum(bool(activity.blocker.strip()) for activity in activities)
    risks = sum(bool(activity.risk.strip()) for activity in activities)
    progress = round(sum(activity.progress_percent for activity in activities) / total) if total else 0
    readiness = "accepted" if total and completed == total else "at_risk" if blocked or risks else "partially_ready" if progress else "not_assessed"
    accepted = sum(bool(_manual_evidence(activity).get("final_acceptance")) for activity in activities)
    return {"total_activities": total, "planned_activities": planned, "completed_activities": completed, "pending_activities": pending, "delayed_activities": delayed, "progress_percent": progress, "blocked_activities": blocked, "risk_activities": risks, "final_acceptance_count": accepted, "readiness": readiness}


def _activity_payload(activity: KTTrackingActivity, db: Session) -> dict[str, object]:
    session = db.query(KTSession).filter(KTSession.id == activity.session_id).first()
    evidence = _manual_evidence(activity)
    return {"id": activity.id, "session_id": activity.session_id, "activity_name": activity.activity_name, "scheduled_date": session.scheduled_date if session else None, "planned_hours": session.duration_hours if session else 0, "delivery_mode": session.delivery_mode if session else "", "status": activity.status, "progress_percent": activity.progress_percent, "blocker": activity.blocker, "risk": activity.risk, "notes": activity.notes, "expected_topics": activity.expected_topics or [], "transcript_analysis": activity.transcript_analysis, "manual_evidence": evidence, "external_meeting_id": (session.conflict_flags or {}).get("external_meeting_id") if session and isinstance(session.conflict_flags, dict) else None}


def _manual_evidence(activity: KTTrackingActivity) -> dict[str, object]:
    analysis = activity.transcript_analysis or {}
    return dict(analysis.get("manual_evidence") or {})