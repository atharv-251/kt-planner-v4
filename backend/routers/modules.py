from __future__ import annotations

import shutil
import smtplib
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import UPLOADS_DIR
from backend.database import get_db
from backend.models.knowledge import KnowledgeNode
from backend.models.scheduling import KTSession
from backend.models.tracker import KTTrackingActivity
from backend.models.transition import Transition, UploadedDocument
from backend.services.schedule_import_service import parse_schedule_csv
from backend.services.teams_scheduler_service import send_teams_invite, valid_recipients
from backend.services.transcript_analysis_service import analyze_transcript

router = APIRouter(tags=["KT Planner Modules"])


class TeamsInviteRequest(BaseModel):
    session_ids: list[str] | None = None
    recipients: list[str] | None = Field(default=None, description="Optional test recipients that replace session participants.")
    dry_run: bool = True
    max_invites_per_recipient: int = Field(default=1, ge=1, le=10)


class TrackerActivityUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(planned|in_progress|completed|on_hold|cancelled)$")
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    blocker: str | None = Field(default=None, max_length=2000)
    risk: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)


@router.get("/api/v1/modules")
def list_modules() -> list[dict[str, object]]:
    return [
        {"number": 13, "name": "Teams KT Scheduler", "description": "Send Teams-compatible SMTP invitations for KT Planner sessions.", "path": "/api/v1/transitions/{transition_id}/teams-kt-scheduler"},
        {"number": 14, "name": "KT Tracker", "description": "Attach and retrieve Teams transcripts for a transition.", "path": "/api/v1/transitions/{transition_id}/kt-tracker/transcripts"},
    ]


@router.get("/api/v1/transitions/{transition_id}/teams-kt-scheduler")
def get_teams_scheduler(transition_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    sessions = _sessions(transition_id, db)
    return {"module": 13, "name": "Teams KT Scheduler", "sessions": [_session_payload(session) for session in sessions]}


@router.post("/api/v1/transitions/{transition_id}/teams-kt-scheduler/schedule")
async def import_teams_schedule(transition_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
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
    return {"module": 13, "imported": len(sessions), "sessions": [_session_payload(session) for session in sessions]}


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

    override_recipients = valid_recipients(payload.recipients or [])
    attempted: dict[str, int] = {}
    results: list[dict[str, str]] = []
    for session in sessions:
        recipients = override_recipients or _session_recipients(session)
        recipients = [email for email in recipients if attempted.get(email, 0) < payload.max_invites_per_recipient]
        if not recipients:
            results.append({"session_id": session.id, "status": "skipped", "message": "Recipient invite limit reached or no recipient email is assigned."})
            continue
        for email in recipients:
            attempted[email] = attempted.get(email, 0) + 1
        try:
            results.append(send_teams_invite(session_id=session.id, title=session.session_title, start_at=_session_start(session, transition), end_at=_session_end(session, transition), recipients=recipients, dry_run=payload.dry_run))
        except (OSError, ValueError, smtplib.SMTPException) as error:
            results.append({"session_id": session.id, "status": "failed", "message": str(error)})

    return {"module": 13, "dry_run": payload.dry_run, "total_sessions": len(sessions), "sent": sum(item["status"] == "sent" for item in results), "dry_run_count": sum(item["status"] == "dry_run" for item in results), "skipped": sum(item["status"] == "skipped" for item in results), "failed": sum(item["status"] == "failed" for item in results), "results": results}


@router.get("/api/v1/transitions/{transition_id}/kt-tracker/transcripts")
def list_teams_transcripts(transition_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    documents = db.query(UploadedDocument).filter(UploadedDocument.transition_id == transition_id).order_by(UploadedDocument.uploaded_at.desc()).all()
    transcripts = [document for document in documents if document.file_name.lower().endswith(".vtt")]
    return {"module": 14, "name": "KT Tracker", "transcripts": [_document_payload(document) for document in transcripts]}


@router.post("/api/v1/transitions/{transition_id}/kt-tracker/transcripts")
async def upload_teams_transcript(transition_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, object]:
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
    return {"module": 14, "transcript": _document_payload(document)}


@router.get("/api/v1/transitions/{transition_id}/kt-tracker")
def get_kt_tracker(transition_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    activities = _tracker_activities(transition_id, db)
    _sync_session_activities(transition_id, activities, db)
    db.commit()
    activities = _tracker_activities(transition_id, db)
    return {"module": 14, "summary": _tracker_summary(activities), "activities": [_activity_payload(activity, db) for activity in activities]}


@router.put("/api/v1/transitions/{transition_id}/kt-tracker/activities/{activity_id}")
def update_tracker_activity(transition_id: str, activity_id: str, payload: TrackerActivityUpdate, db: Session = Depends(get_db)) -> dict[str, object]:
    _transition_or_404(transition_id, db)
    activity = db.query(KTTrackingActivity).filter(KTTrackingActivity.id == activity_id, KTTrackingActivity.transition_id == transition_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Tracker activity not found")
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, field_name, value)
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
    activity.transcript_analysis = analysis
    if analysis["topics_covered"] and not analysis["topics_partially_covered"] and not analysis["topics_missed"]:
        activity.status = "completed"
        activity.progress_percent = 100
    elif activity.status == "planned":
        activity.status = "in_progress"
    db.commit()
    db.refresh(activity)
    return {"analysis": analysis, "activity": _activity_payload(activity, db)}


def _transition_or_404(transition_id: str, db: Session) -> Transition:
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")
    return transition


def _sessions(transition_id: str, db: Session) -> list[KTSession]:
    return db.query(KTSession).filter(KTSession.transition_id == transition_id).order_by(KTSession.scheduled_date, KTSession.start_time).all()


def _session_payload(session: KTSession) -> dict[str, object]:
    return {"id": session.id, "title": session.session_title, "level": session.level, "scheduled_date": session.scheduled_date, "start_time": session.start_time, "end_time": session.end_time, "status": session.status, "recipients": _session_recipients(session)}


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
    return {"id": document.id, "file_name": document.file_name, "file_size": document.file_size, "mime_type": document.mime_type, "uploaded_at": document.uploaded_at}


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


def _tracker_summary(activities: list[KTTrackingActivity]) -> dict[str, object]:
    total = len(activities)
    completed = sum(activity.status == "completed" for activity in activities)
    blocked = sum(bool(activity.blocker.strip()) for activity in activities)
    risks = sum(bool(activity.risk.strip()) for activity in activities)
    progress = round(sum(activity.progress_percent for activity in activities) / total) if total else 0
    readiness = "accepted" if total and completed == total else "at_risk" if blocked or risks else "partially_ready" if progress else "not_assessed"
    return {"total_activities": total, "completed_activities": completed, "progress_percent": progress, "blocked_activities": blocked, "risk_activities": risks, "readiness": readiness}


def _activity_payload(activity: KTTrackingActivity, db: Session) -> dict[str, object]:
    session = db.query(KTSession).filter(KTSession.id == activity.session_id).first()
    return {"id": activity.id, "session_id": activity.session_id, "activity_name": activity.activity_name, "scheduled_date": session.scheduled_date if session else None, "status": activity.status, "progress_percent": activity.progress_percent, "blocker": activity.blocker, "risk": activity.risk, "notes": activity.notes, "expected_topics": activity.expected_topics or [], "transcript_analysis": activity.transcript_analysis}