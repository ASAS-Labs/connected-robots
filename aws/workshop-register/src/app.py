"""Workshop pre-registration: POST form body -> DynamoDB -> 302 redirect."""

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
THANK_YOU_PATH = os.environ.get("THANK_YOU_PATH") or "/workshop-register.html?thanks=1"

_ddb = boto3.resource("dynamodb")
_table = None

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE_RE = re.compile(r"^[\d\s\-+().]{0,40}$")


def _get_table():
    global _table
    if _table is None:
        _table = _ddb.Table(TABLE_NAME)
    return _table


def _thank_you_location() -> str:
    path = THANK_YOU_PATH if THANK_YOU_PATH.startswith("/") else f"/{THANK_YOU_PATH}"
    return f"{PUBLIC_SITE_ORIGIN}{path}"


def _duplicate_location() -> str:
    return f"{PUBLIC_SITE_ORIGIN}/workshop-register.html?duplicate=1"


def _parse_form(body: str, is_base64: bool) -> dict[str, list[Any]]:
    if not body:
        return {}
    raw = base64.b64decode(body).decode("utf-8") if is_base64 else body
    return parse_qs(raw, keep_blank_values=True)


def _first(params: dict[str, list[Any]], key: str) -> str:
    lst = params.get(key) or []
    return lst[0] if lst else ""


def _verify_turnstile(token: str, secret: str, remote_ip: str) -> bool:
    if not token or not secret:
        return False
    payload = urlencode(
        {
            "secret": secret,
            "response": token,
            **({"remoteip": remote_ip} if remote_ip else {}),
        }
    ).encode()
    req = Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except OSError:
        return False
    return bool(data.get("success"))


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
    phone = _first(params, "phone").strip()[:40]
    recommended_by = _first(params, "recommended_by").strip()[:200]
    affiliation = _first(params, "affiliation").strip()[:200]
    role = _first(params, "role").strip()[:80]
    ros_autoware_experience = _first(params, "ros_autoware_experience").strip()[:40]
    bring_laptop = _first(params, "bring_laptop").strip()
    accessibility_notes = _first(params, "accessibility_notes").strip()[:2000]
    ack_limited_seats = _first(params, "ack_limited_seats")

    if not full_name or not email_raw or not bring_laptop or ack_limited_seats != "yes":
        return {
            "statusCode": 400,
            "headers": {"content-type": "text/html; charset=utf-8"},
            "body": (
                "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<title>Invalid submission</title></head><body><p>Missing or invalid required fields. "
                "Use the back button to correct your entry.</p></body></html>"
            ),
        }

    if not _EMAIL_RE.match(email_raw):
        return {
            "statusCode": 400,
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "body": "Invalid email address.",
        }

    email_key = email_raw.lower()
    if phone and not _PHONE_RE.match(phone):
        return {
            "statusCode": 400,
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "body": "Invalid phone number.",
        }

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

    _get_table().put_item(
        Item={
            "id": item_id,
            "submittedAt": submitted_at,
            "full_name": full_name,
            "email": email_key,
            "phone": phone,
            "recommended_by": recommended_by,
            "affiliation": affiliation,
            "role": role,
            "ros_autoware_experience": ros_autoware_experience,
            "bring_laptop": bring_laptop,
            "accessibility_notes": accessibility_notes,
            "ack_limited_seats": ack_limited_seats,
            "sourceIp": source_ip,
        }
    )

    return {
        "statusCode": 302,
        "headers": {"location": _thank_you_location()},
        "body": "",
    }
