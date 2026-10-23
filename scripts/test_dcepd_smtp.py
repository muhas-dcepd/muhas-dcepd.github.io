#!/usr/bin/env python3
"""Isolated manual SMTP probe: no REDCap access, report data, or attachments."""
import os
import smtplib
import ssl
from email.message import EmailMessage

def main():
    host = os.environ.get("DCEPD_SMTP_HOST", "").strip()
    username = os.environ.get("DCEPD_SMTP_USERNAME", "").strip()
    password = os.environ.get("DCEPD_SMTP_PASSWORD", "").strip()
    if not all((host, username, password)):
        raise RuntimeError("SMTP configuration incomplete; no email attempted")
    port = int(os.getenv("DCEPD_SMTP_PORT") or ("465" if "gmail" in host.lower() else "587"))
    if port not in (465, 587):
        raise RuntimeError("SMTP test requires port 465 or 587")
    msg = EmailMessage()
    msg["From"] = username
    msg["To"] = "sangeda@gmail.com"
    msg["Subject"] = "[TEST] DCEPD SMTP delivery check"
    msg.set_content("This is an isolated DCEPD technical email test. No REDCap records or management report were accessed.")
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(msg)
    print("SMTP accepted isolated test message for one technical recipient.")

if __name__ == "__main__":
    main()
