from __future__ import annotations

import hashlib
import json
import os
import smtplib
from base64 import b64decode
from binascii import Error as BinasciiError
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from backend.config import EXPORTS_DIR


def send_teams_invite(
    *,
    session_id: str,
    title: str,
    start_at: datetime,
    end_at: datetime,
    recipients: list[str],
    dry_run: bool,
) -> dict[str, str]:
    """Send one Outlook-compatible invitation for a KT Planner session."""
    uid = _invite_uid(session_id, start_at, end_at)
    state_key = _invite_state_key(uid, recipients)
    if state_key in _sent_invite_keys():
        return {"session_id": session_id, "status": "skipped", "message": "Invite was already sent."}

    if dry_run:
        return {"session_id": session_id, "status": "dry_run", "message": "Invite generated but not sent."}

    sender = _setting("KT_SCHEDULER_SENDER_EMAIL")
    server = _setting("KT_SCHEDULER_SMTP_SERVER")
    if not sender or not server:
        raise ValueError("Set KT_SCHEDULER_SENDER_EMAIL and KT_SCHEDULER_SMTP_SERVER before sending invites.")

    ics = _build_ics(uid=uid, title=title, start_at=start_at, end_at=end_at, sender=sender, recipients=recipients)
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = title
    message["Content-Class"] = "urn:content-classes:calendarmessage"
    message.set_content(f"{title}\n\nStart: {start_at}\nEnd: {end_at}")
    message.add_alternative(ics, subtype="calendar", params={"method": "REQUEST", "name": "invite.ics"})
    message.add_attachment(ics.encode("utf-8"), maintype="text", subtype="calendar", filename="invite.ics", params={"method": "REQUEST"})

    port = int(_setting("KT_SCHEDULER_SMTP_PORT", "25"))
    timeout = int(_setting("KT_SCHEDULER_SMTP_TIMEOUT_SECONDS", "30"))
    use_ssl = _setting("KT_SCHEDULER_SMTP_SSL", "").lower() in {"1", "true", "yes"} or port == 465
    username = _setting("KT_SCHEDULER_SMTP_USERNAME")
    password = _smtp_password()
    smtp_client = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_client(server, port, timeout=timeout) as smtp:
        if not use_ssl:
            smtp.ehlo()
        starttls_requested = _setting("KT_SCHEDULER_SMTP_STARTTLS", "false").lower() in {"1", "true", "yes"}
        if not use_ssl and (starttls_requested or (username and password and smtp.has_extn("starttls"))):
            smtp.starttls()
            smtp.ehlo()
        if username and password and smtp.has_extn("auth"):
            smtp.login(username, password)
        smtp.send_message(message)

    _record_sent_invite(state_key)
    return {"session_id": session_id, "status": "sent", "message": "Invite sent through SMTP."}


def invite_was_sent(*, session_id: str, start_at: datetime, end_at: datetime, recipients: list[str]) -> bool:
    uid = _invite_uid(session_id, start_at, end_at)
    return _invite_state_key(uid, recipients) in _sent_invite_keys()


def valid_recipients(values: Iterable[str | None]) -> list[str]:
    recipients: list[str] = []
    for value in values:
        email = str(value or "").strip().lower()
        if email and "@" in email and email not in recipients:
            recipients.append(email)
    return recipients


def _setting(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _smtp_password() -> str:
    password = _setting("KT_SCHEDULER_SMTP_PASSWORD")
    if password:
        return password
    encoded = _setting("KT_SCHEDULER_SMTP_PASSWORD_B64")
    if not encoded:
        return ""
    try:
        return b64decode(encoded, validate=True).decode("utf-8")
    except (BinasciiError, UnicodeDecodeError) as error:
        raise ValueError("KT_SCHEDULER_SMTP_PASSWORD_B64 must be valid Base64.") from error


def _invite_uid(session_id: str, start_at: datetime, end_at: datetime) -> str:
    fingerprint = hashlib.sha256(f"{session_id}|{start_at.isoformat()}|{end_at.isoformat()}".encode("utf-8")).hexdigest()[:20]
    return f"kt-planner-{fingerprint}@teams-kt-scheduler"


def _invite_state_key(uid: str, recipients: list[str]) -> str:
    return f"{uid}|{','.join(sorted(email.lower() for email in recipients))}"


def _build_ics(*, uid: str, title: str, start_at: datetime, end_at: datetime, sender: str, recipients: list[str]) -> str:
    attendees = [f"ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE:MAILTO:{email}" for email in recipients]
    lines = [
        "BEGIN:VCALENDAR", "PRODID:-//KT Planner//Teams KT Scheduler//EN", "VERSION:2.0", "CALSCALE:GREGORIAN", "METHOD:REQUEST",
        "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{_utc(datetime.now(timezone.utc))}", f"DTSTART:{_utc(start_at)}", f"DTEND:{_utc(end_at)}",
        f"SUMMARY:{_escape(title)}", f"ORGANIZER:MAILTO:{sender}", *attendees, "STATUS:CONFIRMED", "SEQUENCE:0", "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _state_path() -> Path:
    return EXPORTS_DIR / "teams_kt_scheduler_sent_invites.json"


def _sent_invite_keys() -> set[str]:
    path = _state_path()
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return set()


def _record_sent_invite(state_key: str) -> None:
    keys = _sent_invite_keys()
    keys.add(state_key)
    _state_path().write_text(json.dumps(sorted(keys), indent=2), encoding="utf-8")