#!/usr/bin/env python3
"""Send one email through SES from the verified ears-conn.com identity.

Inputs come from environment variables (set by the send-email workflow):
  EMAIL_FROM       verified sender, e.g. noreply@ears-conn.com (name shown as EARS-CONN)
  EMAIL_TO         comma-separated recipients (required)
  EMAIL_CC         comma-separated CC (optional)
  EMAIL_BCC        comma-separated BCC (optional)
  EMAIL_REPLY_TO   comma-separated Reply-To (optional, defaults to EMAIL_CC)
  EMAIL_SUBJECT    subject line (required)
  EMAIL_BODY       plain-text body; blank lines separate paragraphs (required)
  DRY_RUN          "true" to build the message without sending
  AWS_REGION       defaults to us-east-1

The repository is public, so recipients and content are never printed.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr

ADDRESS_RE = re.compile(r"^[^@\s,<>]+@[^@\s,<>]+\.[^@\s,<>]+$")
URL_RE = re.compile(r"(https?://[^\s<]+[^\s<.,;:!?)\]])")


def addresses(var: str) -> list[str]:
    raw = os.environ.get(var, "")
    out = [a.strip() for a in re.split(r"[,;\n]", raw) if a.strip()]
    bad = [a for a in out if not ADDRESS_RE.match(a)]
    if bad:
        sys.exit(f"{var} has {len(bad)} invalid address(es).")
    return out


def body_to_html(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    rendered = []
    for p in paragraphs:
        escaped = html.escape(p)
        linked = URL_RE.sub(r'<a href="\1">\1</a>', escaped)
        rendered.append("<p>" + linked.replace("\n", "<br>\n") + "</p>")
    return "\n".join(rendered)


def main() -> None:
    raw_from = os.environ.get("EMAIL_FROM", "").strip()
    from_name, from_address = parseaddr(raw_from)
    if not from_address.lower().endswith("@ears-conn.com"):
        sys.exit("EMAIL_FROM must be an @ears-conn.com address.")
    from_name = from_name or "EARS-CONN"

    to = addresses("EMAIL_TO")
    cc = addresses("EMAIL_CC")
    bcc = addresses("EMAIL_BCC")
    reply_to = addresses("EMAIL_REPLY_TO") or cc
    subject = os.environ.get("EMAIL_SUBJECT", "").strip()
    body = os.environ.get("EMAIL_BODY", "").replace("\r\n", "\n").strip()
    if not to or not subject or not body:
        sys.exit("EMAIL_TO, EMAIL_SUBJECT, and EMAIL_BODY are required.")
    if len(to) + len(cc) + len(bcc) > 50:
        sys.exit("SES allows at most 50 recipients per message.")

    msg = EmailMessage()
    msg["From"] = formataddr((from_name, from_address))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = ", ".join(reply_to)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="ears-conn.com")
    msg.set_content(body + "\n")
    msg.add_alternative(body_to_html(body), subtype="html")

    print(f"Recipients: {len(to)} to, {len(cc)} cc, {len(bcc)} bcc")
    if os.environ.get("DRY_RUN", "").lower() == "true":
        print("Dry run: message built, not sent.")
        return

    payload = {
        "Source": from_address,
        "Destinations": to + cc + bcc,
        "RawMessage": {"Data": base64.b64encode(msg.as_bytes()).decode("ascii")},
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(payload, fh)
        path = fh.name
    try:
        result = subprocess.run(
            [
                "aws", "ses", "send-raw-email",
                "--region", os.environ.get("AWS_REGION", "us-east-1"),
                "--cli-input-json", f"file://{path}",
                "--query", "MessageId", "--output", "text",
            ],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(path)
    if result.returncode != 0:
        sys.exit("SES send failed: " + result.stderr.strip())
    print(f"Sent. SES MessageId={result.stdout.strip()}")


if __name__ == "__main__":
    main()
