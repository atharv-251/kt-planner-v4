import csv
import io
from datetime import date, datetime, time

REQUIRED_COLUMNS = {"title", "date", "start", "end"}
ATTENDEE_COLUMNS = ("required attendees", "optional attendees", "attendees", "recipients")


def parse_schedule_csv(content: bytes) -> list[dict[str, object]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Schedule CSV must be UTF-8 encoded.") from error
    reader = csv.DictReader(io.StringIO(text))
    headers = {str(header or "").strip().lower() for header in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise ValueError(f"Schedule CSV is missing required columns: {', '.join(sorted(missing))}.")
    sessions: list[dict[str, object]] = []
    for row_number, row in enumerate(reader, start=2):
        normalized = {str(key or "").strip().lower(): str(value or "").strip() for key, value in row.items()}
        try:
            title = normalized["title"]
            if not title:
                raise ValueError("title is empty")
            attendees = _attendees(normalized)
            sessions.append({
                "title": title[:255],
                "scheduled_date": _parse_date(normalized["date"]),
                "start_time": _parse_time(normalized["start"]),
                "end_time": _parse_time(normalized["end"]),
                "attendees": attendees,
            })
        except ValueError as error:
            raise ValueError(f"Schedule CSV row {row_number}: {error}") from error
    if not sessions:
        raise ValueError("Schedule CSV contains no sessions.")
    return sessions


def _attendees(row: dict[str, str]) -> list[str]:
    values = [row.get(column, "") for column in ATTENDEE_COLUMNS]
    attendees: list[str] = []
    for value in values:
        for email in value.replace(";", ",").split(","):
            normalized = email.strip().lower()
            if normalized and "@" in normalized and normalized not in attendees:
                attendees.append(normalized)
    return attendees


def _parse_date(value: str) -> date:
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValueError("date must use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY")


def _parse_time(value: str) -> time:
    for pattern in ("%H:%M", "%H:%M:%S", "%I:%M %p"):
        try:
            return datetime.strptime(value.upper(), pattern).time()
        except ValueError:
            pass
    raise ValueError("start and end must use HH:MM or H:MM AM/PM")