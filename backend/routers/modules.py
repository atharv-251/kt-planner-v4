from __future__ import annotations

import shutil
import smtplib
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import UPLOADS_DIR
from backend.database import get_db
from backend.models.scheduling import KTSession
from backend.models.transition import Transition, UploadedDocument
from backend.services.teams_scheduler_service import send_teams_invite, valid_recipients

router = APIRouter(tags=["KT Planner Modules"])


class TeamsInviteRequest(BaseModel):
    session_ids: list[str] | None = None
    recipients: list[str] | None = Field(default=None, description="Optional test recipients that replace session participants.")
    dry_run: bool = True
    max_invites_per_recipient: int = Field(default=1, ge=1, le=10)


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
        recipients = override_recipients or valid_recipients([session.sme.email if session.sme else None, session.receiver.email if session.receiver else None])
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


def _transition_or_404(transition_id: str, db: Session) -> Transition:
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")
    return transition


def _sessions(transition_id: str, db: Session) -> list[KTSession]:
    return db.query(KTSession).filter(KTSession.transition_id == transition_id).order_by(KTSession.scheduled_date, KTSession.start_time).all()


def _session_payload(session: KTSession) -> dict[str, object]:
    return {"id": session.id, "title": session.session_title, "level": session.level, "scheduled_date": session.scheduled_date, "start_time": session.start_time, "end_time": session.end_time, "status": session.status, "recipients": valid_recipients([session.sme.email if session.sme else None, session.receiver.email if session.receiver else None])}


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