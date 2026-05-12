"""Registration API: POST unified form to DynamoDB (HTTP API + Lambda)."""

from __future__ import annotations

import base64
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["TABLE_NAME"]
PUBLIC_SITE_ORIGIN = (os.environ.get("PUBLIC_SITE_ORIGIN") or "https://ears-conn.com").rstrip("/")
THANK_YOU_PATH = os.environ.get("THANK_YOU_PATH") or "/register.html?thanks=1"

_ddb = boto3.resource("dynamodb")
_table = None

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
_ALLOWED_COUNTRY_CODES = frozenset(
    """AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW""".split()
)
_MAX_PHONE_LEN = 24
_ALLOWED_REGISTRATION_TIERS = frozenset(
    {
        "conf_early",
        "conf_student",
        "conf_standard",
        "workshop_full",
        "workshop_online",
    }
)
# Early bird (conf_early) ends at this instant (UTC): end of July 4, 2026 US Eastern.
_EARLY_BIRD_END_UTC = datetime(2026, 7, 5, 4, 0, 0, tzinfo=timezone.utc)


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


def _bad_request(msg: str) -> dict[str, Any]:
    return {
        "statusCode": 400,
        "headers": {"content-type": "text/html; charset=utf-8"},
        "body": (
            "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<title>Invalid submission</title></head><body><p>"
            + _html_escape(msg)
            + "</p></body></html>"
        ),
    }


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def handler(event, context):
    req = (event.get("requestContext") or {}).get("http") or {}
    method = req.get("method") or event.get("httpMethod") or ""

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": {}, "body": ""}

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
            return {
                "statusCode": 400,
                "headers": {"content-type": "text/html; charset=utf-8"},
                "body": (
                    "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                    "<title>Verification failed</title></head><body><p>Human verification failed or expired. "
                    "Please reload the page and try again.</p></body></html>"
                ),
            }

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
        return _bad_request("Full name is required.")
    if not email_raw or not _EMAIL_RE.match(email_raw):
        return _bad_request("A valid email address is required.")
    if not phone or not _phone_ok(phone):
        return _bad_request("A valid phone number is required (8–15 digits).")
    if not country_code or country_code not in _ALLOWED_COUNTRY_CODES:
        return _bad_request("Please select a valid country or territory.")
    if registration_tier not in _ALLOWED_REGISTRATION_TIERS:
        return _bad_request("Please select a registration option.")

    now_utc = datetime.now(timezone.utc)
    if registration_tier == "conf_early" and now_utc >= _EARLY_BIRD_END_UTC:
        return _bad_request("Early registration has ended. Please choose another registration option.")

    if registration_tier == "workshop_online":
        participation_mode = "remote"
    else:
        participation_mode = "in_person"

    if registration_tier in ("workshop_full", "workshop_online"):
        bring_laptop = _first(params, "bring_laptop").strip()
        if bring_laptop not in ("yes", "no"):
            return _bad_request("Please indicate whether you will bring a laptop.")
    else:
        bring_laptop = "no"

    if ack_limited_seats != "yes":
        return _bad_request("Please acknowledge the registration terms to continue.")

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
    }
    _get_table().put_item(Item=item)

    return {
        "statusCode": 302,
        "headers": {"location": _thank_you_location()},
        "body": "",
    }
