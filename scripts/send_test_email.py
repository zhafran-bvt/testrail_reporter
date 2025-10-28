#!/usr/bin/env python3
"""
Send a simple test email using SMTP settings from .env

Usage:
  python scripts/send_test_email.py --to recipient@example.com [--subject "Test"] [--body "Hello"]

Works well for verifying Gmail (smtp.gmail.com:587 + App Password).
"""

import argparse
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv


def _parse_bool(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", default="SMTP Test", help="Email subject")
    parser.add_argument("--body", default="Hello from SMTP test.", help="Plaintext body")
    parser.add_argument("--server", default=None, help="Override SMTP server host (else from env)")
    parser.add_argument("--port", type=int, default=None, help="Override SMTP server port (else from env)")
    parser.add_argument("--ssl", action="store_true", help="Use SSL (implicit TLS) e.g. port 465")
    parser.add_argument("--no-starttls", dest="no_starttls", action="store_true", help="Disable STARTTLS")
    parser.add_argument("--debug", action="store_true", help="Enable SMTP protocol debug output")
    args = parser.parse_args()

    load_dotenv()

    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    server_host = args.server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
    server_port = int(args.port or os.getenv("SMTP_PORT", "587"))
    use_ssl = args.ssl or _parse_bool(os.getenv("SMTP_USE_SSL"), False)
    use_starttls = (not args.no_starttls) and _parse_bool(os.getenv("SMTP_STARTTLS"), True)

    if not user or not password:
        raise SystemExit("Missing SMTP_USER or SMTP_PASSWORD in environment/.env")

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg.attach(MIMEText(args.body, "plain"))

    print(f"Connecting to {server_host}:{server_port} (SSL={use_ssl}, STARTTLS={use_starttls}) as {user}...")
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(server_host, server_port) as s:
                if args.debug:
                    s.set_debuglevel(1)
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(server_host, server_port) as s:
                if args.debug:
                    s.set_debuglevel(1)
                s.ehlo()
                if use_starttls:
                    s.starttls()
                    s.ehlo()
                s.login(user, password)
                s.send_message(msg)
        print("✅ Test email sent to:", args.to)
    except smtplib.SMTPAuthenticationError as e:
        print("❌ Authentication failed.")
        if "gmail" in server_host.lower():
            print("Hint: For Gmail, enable 2-Step Verification and use an App Password.")
        print("Details:", e)
        raise SystemExit(1)
    except smtplib.SMTPException as e:
        print("❌ SMTP error:", e)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
