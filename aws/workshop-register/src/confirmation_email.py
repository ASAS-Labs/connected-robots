"""Registrant confirmation: date, time, location, and a calendar file."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
VENUE = (
    "Steinman Hall, Grove School of Engineering, "
    "The City College of New York, 160 Convent Avenue, New York, NY 10031"
)
EVENT_TITLE = "EARS-CONN 2027"
DAILY_HOURS = "8:30 AM–5:20 PM Eastern Time"

_WORKSHOP_TIERS = frozenset({"workshop_full", "workshop_online"})


def event_window(tier_key: str) -> dict[str, datetime | str]:
    """Conference is January 18–19. Workshop registration includes January 20–21."""
    start = datetime(2027, 1, 18, 8, 30, tzinfo=TZ)
    if tier_key in _WORKSHOP_TIERS:
        end = datetime(2027, 1, 21, 17, 20, tzinfo=TZ)
        when = "Monday, January 18 through Thursday, January 21, 2027"
    else:
        end = datetime(2027, 1, 19, 17, 20, tzinfo=TZ)
        when = "Monday, January 18 and Tuesday, January 19, 2027"
    return {"start": start, "end": end, "when": when, "hours": DAILY_HOURS}


def location_line(participation_mode: str) -> str:
    if participation_mode == "remote":
        return f"Online. In-person sessions are at {VENUE}."
    return VENUE


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _local_stamp(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%S")


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _fold(line: str) -> str:
    chunks: list[str] = []
    while len(line) > 73:
        chunks.append(line[:73])
        line = line[73:]
    chunks.append(line)
    return "\r\n ".join(chunks)


def build_ics(
    *,
    email: str,
    tier_key: str,
    start: datetime,
    end: datetime,
    location: str,
    description: str,
    site: str,
) -> str:
    uid_hash = hashlib.sha256(f"{email}|{tier_key}".encode()).hexdigest()[:16]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EARS-CONN//Registration//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:ears-conn-2027-{uid_hash}@ears-conn.com",
        f"DTSTAMP:{_stamp(datetime.now(timezone.utc))}",
        f"DTSTART:{_stamp(start)}",
        f"DTEND:{_stamp(end)}",
        f"SUMMARY:{_ics_escape(EVENT_TITLE)}",
        f"LOCATION:{_ics_escape(location)}",
        f"DESCRIPTION:{_ics_escape(description)}",
        f"URL:{site}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(_fold(line) for line in lines)


def _calendar_links(start: datetime, end: datetime, location: str, details: str) -> tuple[str, str]:
    google = "https://calendar.google.com/calendar/render?" + urlencode(
        {
            "action": "TEMPLATE",
            "text": EVENT_TITLE,
            "dates": f"{_local_stamp(start)}/{_local_stamp(end)}",
            "ctz": "America/New_York",
            "location": location,
            "details": details,
        }
    )
    outlook = "https://outlook.live.com/calendar/0/action/compose?" + urlencode(
        {
            "rru": "addevent",
            "subject": EVENT_TITLE,
            "startdt": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "enddt": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": location,
            "body": details,
        }
    )
    return google, outlook


def build_confirmation(
    *,
    name: str,
    email: str,
    tier_key: str,
    tier_label: str,
    site: str,
    participation_mode: str,
    next_steps: str,
) -> dict[str, str]:
    window = event_window(tier_key)
    start = window["start"]
    end = window["end"]
    assert isinstance(start, datetime) and isinstance(end, datetime)
    where = location_line(participation_mode)
    details = (
        f"{window['when']}. {window['hours']}. {where} "
        f"Agenda: {site}/agenda"
    )
    google, outlook = _calendar_links(start, end, where, details)
    # Apple Calendar and most mail apps open the attached .ics file.
    ics = build_ics(
        email=email,
        tier_key=tier_key,
        start=start,
        end=end,
        location=where,
        description=details,
        site=site,
    )
    subject = "EARS-CONN 2027 registration confirmation"
    text = (
        f"Hello {name},\n\n"
        "Your EARS-CONN 2027 registration is confirmed.\n\n"
        f"Date: {window['when']}\n"
        f"Time: {window['hours']}\n"
        f"Location: {where}\n"
        f"Registration option: {tier_label}\n\n"
        "Add to calendar:\n"
        f"Google Calendar: {google}\n"
        f"Outlook: {outlook}\n"
        "Apple Calendar and others: open the attached ears-conn-2027.ics file.\n\n"
        f"{next_steps}\n\n"
        f"Agenda: {site}/agenda\n"
        f"Venue: {site}/venue\n\n"
        "— EARS-CONN\n"
    )
    html = (
        f"<p>Hello {_esc(name)},</p>"
        "<p>Your <strong>EARS-CONN 2027</strong> registration is confirmed.</p>"
        "<p>"
        f"<strong>Date:</strong> {_esc(str(window['when']))}<br>"
        f"<strong>Time:</strong> {_esc(str(window['hours']))}<br>"
        f"<strong>Location:</strong> {_esc(where)}<br>"
        f"<strong>Registration option:</strong> {_esc(tier_label)}"
        "</p>"
        "<p><strong>Add to calendar</strong><br>"
        f'<a href="{_esc(google)}">Google Calendar</a><br>'
        f'<a href="{_esc(outlook)}">Outlook</a><br>'
        "Apple Calendar and others: open the attached ears-conn-2027.ics file."
        "</p>"
        f"<p>{_esc(next_steps)}</p>"
        f'<p><a href="{_esc(site)}/agenda">Agenda</a> · '
        f'<a href="{_esc(site)}/venue">Venue and directions</a></p>'
        "<p>— EARS-CONN</p>"
    )
    return {"subject": subject, "text": text, "html": html, "ics": ics, "google": google, "outlook": outlook}


def registrant_message(
    *,
    from_name: str,
    from_address: str,
    to_address: str,
    content: dict[str, str],
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = content["subject"]
    msg["From"] = formataddr((from_name, from_address))
    msg["To"] = to_address
    msg.set_content(content["text"])
    msg.add_alternative(content["html"], subtype="html")
    msg.add_attachment(
        content["ics"].encode("utf-8"),
        maintype="text",
        subtype="calendar",
        filename="ears-conn-2027.ics",
    )
    calendar = msg.get_payload()[-1]
    calendar.replace_header(
        "Content-Type",
        'text/calendar; method=PUBLISH; charset="UTF-8"; name="ears-conn-2027.ics"',
    )
    return msg


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
