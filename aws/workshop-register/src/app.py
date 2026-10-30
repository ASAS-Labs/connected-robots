"""Registration API: POST unified form to DynamoDB (HTTP API + Lambda)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

import boto3
from boto3.dynamodb.conditions import Key

from confirmation_email import build_confirmation, registrant_message

TABLE_NAME = os.environ["TABLE_NAME"]
PUBLIC_SITE_ORIGIN = (os.environ.get("PUBLIC_SITE_ORIGIN") or "https://ears-conn.com").rstrip("/")
THANK_YOU_PATH = os.environ.get("THANK_YOU_PATH") or "/register.html?thanks=1"
CONFIRMATION_FROM_EMAIL = (os.environ.get("CONFIRMATION_FROM_EMAIL") or "").strip()
CONFIRMATION_FROM_NAME = "EARS-CONN"
ORGANIZER_NOTIFY_EMAIL = (os.environ.get("ORGANIZER_NOTIFY_EMAIL") or "").strip()

_ddb = boto3.resource("dynamodb")
_ses = boto3.client("ses")
_table = None
_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)

_TIER_LABELS = {
    "conf_early": "Conference — early bird ($50)",
    "conf_standard": "Conference — regular ($100)",
    "conf_student": "Conference — student ($20)",
    "conf_free_request": "Conference — limited free ticket request ($0, CUNY students only)",
    "conf_free": "Conference — free (verified CUNY student or access code)",
    "workshop_full": "Workshop — full in person ($600, includes conference)",
    "workshop_online": "Workshop — online ($500, includes conference)",
}

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
_ALLOWED_COUNTRY_CODES = frozenset(
    """AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW""".split()
)
_CUNY_EMAIL_RE = re.compile(r"^[^@\s]+@([a-z0-9-]+\.)*cuny\.edu$", re.IGNORECASE)
_MAX_PHONE_LEN = 24
_ALLOWED_REGISTRATION_TIERS = frozenset(
    {
        "conf_early",
        "conf_student",
        "conf_standard",
        "conf_free_request",
        "workshop_full",
        "workshop_online",
    }
)
# Early bird (conf_early) ends after December 18, 2026 US Eastern (midnight → Dec 19 05:00 UTC).
_EARLY_BIRD_END_UTC = datetime(2026, 12, 19, 5, 0, 0, tzinfo=timezone.utc)


def _get_table():
    global _table
    if _table is None:
        _table = _ddb.Table(TABLE_NAME)
    return _table


def _thank_you_location() -> str:
    path = THANK_YOU_PATH if THANK_YOU_PATH.startswith("/") else "/" + THANK_YOU_PATH
    return PUBLIC_SITE_ORIGIN + path


def _duplicate_location() -> str:
    return PUBLIC_SITE_ORIGIN + "/register.html?duplicate=1"


def _parse_form(body: str, is_base64: bool) -> dict[str, list[str]]:
    if is_base64:
        body = base64.b64decode(body).decode("utf-8", errors="replace")
    return parse_qs(body, keep_blank_values=True, strict_parsing=False)


def _first(params: dict[str, list[str]], key: str) -> str:
    vals = params.get(key) or []
    return (vals[0] if vals else "").strip()


def _verify_turnstile(token: str, secret: str, remote_ip: str) -> bool:
    if not token or not secret:
        return False
    data = urlencode(
        {"secret": secret, "response": token, "remoteip": remote_ip or ""}
    ).encode("utf-8")
    req = Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        parsed: dict[str, Any] = json.loads(raw)
        return bool(parsed.get("success"))
    except OSError:
        return False


def _phone_ok(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return 8 <= len(digits) <= 15 and len(phone) <= _MAX_PHONE_LEN


def _error_location(code: str) -> str:
    return PUBLIC_SITE_ORIGIN + "/register.html?error=" + code


def _bad_request(code: str) -> dict[str, Any]:
    return {
        "statusCode": 302,
        "headers": {"location": _error_location(code)},
        "body": "",
    }


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _tier_label(tier: str) -> str:
    return _TIER_LABELS.get(tier, tier)


def _from_parts(address: str) -> tuple[str, str]:
    """Display name plus the verified SES address."""
    address = address.strip()
    if "<" in address and address.endswith(">"):
        name, addr = address[:-1].split("<", 1)
        return name.strip().strip('"') or CONFIRMATION_FROM_NAME, addr.strip()
    return CONFIRMATION_FROM_NAME, address


def _ses_source(address: str) -> str:
    """Show a conference name in the inbox. The address itself stays the verified SES identity."""
    name, addr = _from_parts(address)
    return f"{name} <{addr}>"


def _send_confirmation_emails(item: dict[str, Any], *, registrant: bool = True) -> None:
    """Email the registrant (and optionally organizers). Failures are logged only."""
    if not CONFIRMATION_FROM_EMAIL:
        _log.info("CONFIRMATION_FROM_EMAIL unset; skipping confirmation email")
        return

    name = item.get("full_name") or "participant"
    to_addr = item.get("email") or ""
    tier_key = str(item.get("registration_tier") or "")
    tier = _tier_label(tier_key)
    site = PUBLIC_SITE_ORIGIN
    next_steps = (
        "Organizers will follow up by email with payment or access details, "
        "and with Autoware seat confirmation when applicable."
    )
    if tier_key == "conf_free_request":
        next_steps = (
            "Free tickets are only for CUNY students. "
            "Organizers will review this request and confirm eligibility by email."
        )

    if not registrant:
        pass
    elif not to_addr:
        _log.info("Registration %s has no email; skipping confirmation", item.get("id"))
    else:
        content = build_confirmation(
            name=name,
            email=to_addr,
            tier_key=tier_key,
            tier_label=tier,
            site=site,
            participation_mode=str(item.get("participation_mode") or ""),
            next_steps=next_steps,
        )
        from_name, from_address = _from_parts(CONFIRMATION_FROM_EMAIL)
        message = registrant_message(
            from_name=from_name,
            from_address=from_address,
            to_address=to_addr,
            content=content,
        )
        try:
            _ses.send_raw_email(
                Source=from_address,
                Destinations=[to_addr],
                RawMessage={"Data": message.as_bytes()},
            )
            _log.info("Confirmation email sent to %s", to_addr)
        except Exception:
            _log.exception("Failed to send confirmation email to %s", to_addr)

    if not ORGANIZER_NOTIFY_EMAIL:
        return

    org_subject = f"[EARS-CONN] New registration: {name}"
    org_text = (
        "New registration received.\n\n"
        f"Name: {name}\n"
        f"Email: {to_addr}\n"
        f"Phone: {item.get('phone') or ''}\n"
        f"Country: {item.get('country_code') or ''}\n"
        f"Tier: {tier}\n"
        f"Participation: {item.get('participation_mode') or ''}\n"
        f"Affiliation: {item.get('affiliation') or ''}\n"
        f"Role: {item.get('role') or ''}\n"
        f"Verified by: {item.get('verified_by') or ''}\n"
        f"Payment status: {item.get('payment_status') or ''}\n"
        f"Student ID: {item.get('student_id') or ''}\n"
        f"Submitted: {item.get('submittedAt') or ''}\n"
        f"Id: {item.get('id') or ''}\n"
    )
    try:
        _ses.send_email(
            Source=_ses_source(CONFIRMATION_FROM_EMAIL),
            Destination={"ToAddresses": [ORGANIZER_NOTIFY_EMAIL]},
            Message={
                "Subject": {"Data": org_subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": org_text, "Charset": "UTF-8"}},
            },
        )
        _log.info("Organizer notify email sent to %s", ORGANIZER_NOTIFY_EMAIL)
    except Exception:
        _log.exception("Failed to send organizer notify email")


_PAID_TIERS = frozenset(
    {"conf_early", "conf_standard", "conf_student", "workshop_full", "workshop_online"}
)
_OTP_TTL = timedelta(minutes=15)
_OTP_COOLDOWN = timedelta(seconds=60)
_OTP_HOUR_LIMIT = 3
_OTP_ATTEMPTS = 5


def _json_response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(payload),
    }


def _gate_error(message: str, status: int = 400) -> dict[str, Any]:
    return _json_response(status, {"ok": False, "error": message})


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_eq(left: str, right: str) -> bool:
    if not left or not right or len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def _normalize_access_code(raw: str) -> str:
    return re.sub(r"[\s-]", "", raw).upper()


def _access_code_ok(raw: str) -> bool:
    expected = (os.environ.get("FREE_ACCESS_KEY_SHA256") or "").strip().lower()
    if len(expected) != 64:
        return False
    digest = _sha256_hex(_normalize_access_code(raw))
    return _hash_eq(digest, expected)


def _free_form_ready() -> bool:
    form_id = (os.environ.get("FREE_FORM_ID") or "").strip()
    env_id = (os.environ.get("FREE_ENV_ID") or "").strip()
    return bool(form_id and env_id)


def _free_form_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "step": "form",
        "formId": (os.environ.get("FREE_FORM_ID") or "").strip(),
        "envId": (os.environ.get("FREE_ENV_ID") or "").strip(),
        "zone": "usa",
    }


def _parse_json_body(event: dict[str, Any]) -> dict[str, Any] | None:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8", errors="replace")
    if len(body) > 8000:
        return None
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _items_for_email(email_key: str) -> list[dict[str, Any]]:
    table = _get_table()
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {
        "IndexName": "email-index",
        "KeyConditionExpression": Key("email").eq(email_key),
    }
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items") or [])
        last = resp.get("LastEvaluatedKey")
        if not last:
            return items
        kwargs["ExclusiveStartKey"] = last


def _send_otp_email(to_addr: str, code: str) -> bool:
    if not CONFIRMATION_FROM_EMAIL:
        return False
    text = (
        f"Your EARS-CONN verification code is {code}.\n\n"
        "It expires in 15 minutes. If you did not request free registration "
        "for EARS-CONN 2027, you can ignore this message.\n"
    )
    try:
        _ses.send_email(
            Source=_ses_source(CONFIRMATION_FROM_EMAIL),
            Destination={"ToAddresses": [to_addr]},
            Message={
                "Subject": {"Data": "Your EARS-CONN verification code", "Charset": "UTF-8"},
                "Body": {"Text": {"Data": text, "Charset": "UTF-8"}},
            },
        )
        return True
    except Exception:
        _log.exception("Failed to send verification code to %s", to_addr)
        return False


def _put_registration(item: dict[str, Any]) -> None:
    item["record_kind"] = "registration"
    _get_table().put_item(Item=item)
    _send_confirmation_emails(item, registrant=False)


def _registration_item(
    *,
    email_key: str,
    full_name: str,
    tier: str,
    verified_by: str,
    payment_status: str,
    source_ip: str,
    student_id: str = "",
) -> dict[str, Any]:
    participation = "remote" if tier == "workshop_online" else "in_person"
    item: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "submittedAt": datetime.now(timezone.utc).isoformat(),
        "registration_tier": tier,
        "full_name": full_name,
        "email": email_key,
        "participation_mode": participation,
        "verified_by": verified_by,
        "payment_status": payment_status,
        "sourceIp": source_ip,
        "ack_limited_seats": "yes",
    }
    if student_id:
        item["student_id"] = student_id
    return item


def _otp_items(email_key: str) -> list[dict[str, Any]]:
    rows = [row for row in _items_for_email(email_key) if row.get("record_kind") == "otp"]
    rows.sort(key=lambda row: str(row.get("submittedAt") or ""), reverse=True)
    return rows


def _start_cuny_otp(email_key: str, full_name: str, student_id: str) -> dict[str, Any]:
    if not _free_form_ready():
        return _gate_error("Free registration is not available right now.")
    if not CONFIRMATION_FROM_EMAIL:
        return _gate_error("Email verification is not available right now.")

    now = datetime.now(timezone.utc)
    existing = _otp_items(email_key)
    recent = []
    for row in existing:
        sent = _parse_iso(str(row.get("submittedAt") or ""))
        if sent is not None and now - sent <= timedelta(hours=1):
            recent.append((sent, row))
    if len(recent) >= _OTP_HOUR_LIMIT:
        return _gate_error("Too many codes were sent. Try again later.")
    if recent and now - recent[0][0] < _OTP_COOLDOWN:
        return _json_response(200, {"ok": True, "step": "verify_email"})

    code = f"{secrets.randbelow(1_000_000):06d}"
    item_id = "otp-" + str(uuid.uuid4())
    _get_table().put_item(
        Item={
            "id": item_id,
            "email": email_key,
            "record_kind": "otp",
            "otp_hash": _sha256_hex(code),
            "expiresAt": (now + _OTP_TTL).isoformat(),
            "attempts": 0,
            "full_name": full_name,
            "student_id": student_id,
            "submittedAt": now.isoformat(),
        }
    )
    if not _send_otp_email(email_key, code):
        _get_table().delete_item(Key={"id": item_id})
        return _gate_error("We could not send the verification email. Try again.")
    _log.info("Verification code sent to %s", email_key)
    return _json_response(200, {"ok": True, "step": "verify_email"})


def _confirm_otp(email_key: str, full_name: str, otp: str, source_ip: str) -> dict[str, Any]:
    if not _free_form_ready():
        return _gate_error("Free registration is not available right now.")
    digits = re.sub(r"\D", "", otp)
    if len(digits) != 6:
        return _gate_error("Enter the 6-digit code from your email.")

    rows = _otp_items(email_key)
    if not rows:
        return _gate_error("That code is wrong or expired.")
    latest = rows[0]
    expires = _parse_iso(str(latest.get("expiresAt") or ""))
    attempts = int(latest.get("attempts") or 0)
    now = datetime.now(timezone.utc)
    if expires is None or now > expires or attempts >= _OTP_ATTEMPTS:
        return _gate_error("That code is wrong or expired.")
    if not _hash_eq(_sha256_hex(digits), str(latest.get("otp_hash") or "")):
        _get_table().update_item(
            Key={"id": latest["id"]},
            UpdateExpression="SET attempts = if_not_exists(attempts, :zero) + :one",
            ExpressionAttributeValues={":zero": 0, ":one": 1},
        )
        return _gate_error("That code is wrong or expired.")

    student_id = str(latest.get("student_id") or "")
    name = full_name or str(latest.get("full_name") or "")
    item = _registration_item(
        email_key=email_key,
        full_name=name,
        tier="conf_free",
        verified_by="cuny_email",
        payment_status="free_form",
        source_ip=source_ip,
        student_id=student_id,
    )
    _put_registration(item)
    for row in rows:
        _get_table().delete_item(Key={"id": row["id"]})
    _log.info("Free registration recorded for %s via cuny_email", email_key)
    return _json_response(200, _free_form_payload())


def _handle_gate(event: dict[str, Any], source_ip: str) -> dict[str, Any]:
    data = _parse_json_body(event)
    if data is None:
        return _gate_error("We could not read that registration.")
    if str(data.get("_gotcha") or "").strip():
        return _json_response(200, {"ok": True, "step": "done"})

    turnstile_secret = (os.environ.get("TURNSTILE_SECRET_KEY") or "").strip()
    if turnstile_secret:
        token = str(data.get("cf-turnstile-response") or "").strip()
        if not _verify_turnstile(token, turnstile_secret, source_ip):
            return _gate_error("Human verification failed or expired. Complete the check and try again.")

    full_name = str(data.get("full_name") or "").strip()[:200]
    email_raw = str(data.get("email") or "").strip()[:254]
    if not full_name:
        return _gate_error("Enter your full name.")
    if not email_raw or not _EMAIL_RE.match(email_raw):
        return _gate_error("Enter a valid email address.")
    email_key = email_raw.lower()
    kind = str(data.get("kind") or "").strip()

    if kind == "paid":
        tier = str(data.get("registration_tier") or "").strip()
        if tier not in _PAID_TIERS:
            return _gate_error("Choose a registration type.")
        if tier == "conf_early" and datetime.now(timezone.utc) >= _EARLY_BIRD_END_UTC:
            return _gate_error("Early registration has ended. Choose another option.")
        item = _registration_item(
            email_key=email_key,
            full_name=full_name,
            tier=tier,
            verified_by="paid",
            payment_status="sent_to_payment",
            source_ip=source_ip,
        )
        _put_registration(item)
        _log.info("Paid registration recorded for %s tier %s", email_key, tier)
        return _json_response(200, {"ok": True, "step": "payment"})

    if kind != "free":
        return _gate_error("Choose a registration type.")

    otp = str(data.get("otp") or "").strip()
    if otp:
        return _confirm_otp(email_key, full_name, otp, source_ip)

    access_code = str(data.get("access_code") or "").strip()
    student_digits = re.sub(r"\D", "", str(data.get("student_id") or ""))
    student_id = student_digits if len(student_digits) == 8 else ""
    if access_code:
        if not (os.environ.get("FREE_ACCESS_KEY_SHA256") or "").strip():
            return _gate_error("Free registration is not available right now.")
        if not _access_code_ok(access_code):
            return _gate_error("That access code is not valid.")
        if not _free_form_ready():
            return _gate_error("Free registration is not available right now.")
        item = _registration_item(
            email_key=email_key,
            full_name=full_name,
            tier="conf_free",
            verified_by="access_code",
            payment_status="free_form",
            source_ip=source_ip,
            student_id=student_id if len(student_id) == 8 else "",
        )
        _put_registration(item)
        _log.info("Free registration recorded for %s via access_code", email_key)
        return _json_response(200, _free_form_payload())

    if _CUNY_EMAIL_RE.match(email_key) and re.fullmatch(r"\d{8}", student_id):
        return _start_cuny_otp(email_key, full_name, student_id)
    return _gate_error("Use a CUNY email and your 8-digit student ID, or enter an access code.")


def handler(event, context):
    req = (event.get("requestContext") or {}).get("http") or {}
    method = req.get("method") or event.get("httpMethod") or ""

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": {}, "body": ""}

    path = req.get("path") or event.get("rawPath") or ""
    if path.rstrip("/").endswith("/register-gate"):
        if method != "POST":
            return {
                "statusCode": 405,
                "headers": {"content-type": "text/plain; charset=utf-8"},
                "body": "Method Not Allowed",
            }
        return _handle_gate(event, req.get("sourceIp") or "")

    if method != "POST":
        return {
            "statusCode": 405,
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "body": "Method Not Allowed",
        }

    params = _parse_form(event.get("body") or "", event.get("isBase64Encoded") or False)
    source_ip = req.get("sourceIp") or ""

    if _first(params, "_gotcha"):
        return {"statusCode": 302, "headers": {"location": _thank_you_location()}, "body": ""}

    turnstile_secret = (os.environ.get("TURNSTILE_SECRET_KEY") or "").strip()
    if turnstile_secret:
        token = _first(params, "cf-turnstile-response").strip()
        if not _verify_turnstile(token, turnstile_secret, source_ip):
            return _bad_request("verification")

    full_name = _first(params, "full_name").strip()[:200]
    email_raw = _first(params, "email").strip()[:254]
    phone = _first(params, "phone").strip()[:_MAX_PHONE_LEN]
    country_code = _first(params, "country_code").strip().upper()[:2]
    registration_tier = _first(params, "registration_tier").strip()
    recommended_by = _first(params, "recommended_by").strip()[:200]
    affiliation = _first(params, "affiliation").strip()[:200]
    role = _first(params, "role").strip()[:80]
    ros_autoware_experience = _first(params, "ros_autoware_experience").strip()[:40]
    accessibility_notes = _first(params, "accessibility_notes").strip()[:2000]
    ack_limited_seats = _first(params, "ack_limited_seats").strip()

    if not full_name:
        return _bad_request("name")
    if not email_raw or not _EMAIL_RE.match(email_raw):
        return _bad_request("email")
    if not phone or not _phone_ok(phone):
        return _bad_request("phone")
    if not country_code or country_code not in _ALLOWED_COUNTRY_CODES:
        return _bad_request("country")
    if registration_tier not in _ALLOWED_REGISTRATION_TIERS:
        return _bad_request("tier")

    now_utc = datetime.now(timezone.utc)
    if registration_tier == "conf_early" and now_utc >= _EARLY_BIRD_END_UTC:
        return _bad_request("early")
    if registration_tier == "conf_free_request" and not _CUNY_EMAIL_RE.match(email_raw):
        return _bad_request("cuny")

    if registration_tier == "workshop_online":
        participation_mode = "remote"
    else:
        participation_mode = "in_person"

    if registration_tier in ("workshop_full", "workshop_online"):
        bring_laptop = _first(params, "bring_laptop").strip()
        if bring_laptop not in ("yes", "no"):
            return _bad_request("laptop")
    else:
        bring_laptop = "no"

    if ack_limited_seats != "yes":
        return _bad_request("ack")

    email_key = email_raw.lower()

    existing = _get_table().query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email_key),
        Limit=1,
    )
    if existing.get("Items"):
        return {
            "statusCode": 302,
            "headers": {"location": _duplicate_location()},
            "body": "",
        }

    item_id = str(uuid.uuid4())
    submitted_at = datetime.now(timezone.utc).isoformat()

    item: dict[str, Any] = {
        "id": item_id,
        "submittedAt": submitted_at,
        "registration_tier": registration_tier,
        "full_name": full_name,
        "email": email_key,
        "phone": phone,
        "country_code": country_code,
        "participation_mode": participation_mode,
        "recommended_by": recommended_by,
        "affiliation": affiliation,
        "role": role,
        "ros_autoware_experience": ros_autoware_experience,
        "bring_laptop": bring_laptop,
        "accessibility_notes": accessibility_notes,
        "ack_limited_seats": ack_limited_seats,
        "sourceIp": source_ip,
        "record_kind": "registration",
    }
    _get_table().put_item(Item=item)
    _send_confirmation_emails(item)

    return {
        "statusCode": 302,
        "headers": {"location": _thank_you_location()},
        "body": "",
    }
