#!/usr/bin/env python3
"""
Project 79 certificate listener/generator.

Safety rules:
- Only processes records explicitly requested in REDCap.
- Requires participant role, attendance verified, certificate approved,
  running sequence, visible certificate number, approved template, and template-ready.
- Never regenerates a record already marked certificate_generated=1.
- Uploads the generated PDF back to REDCap before marking success.
- Initial release supports the approved MUHAS_STD_01 template and the
  DCEPD-SOP-173-2026_ARUSHA_20260928 controlled run.
"""
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

REDCAP_URL = os.getenv("REDCAP_URL", "https://utafiti.muhas.ac.tz/api/")
TOKEN79 = os.getenv("REDCAP_PROJECT79_TOKEN", "")
TOKEN75 = os.getenv("REDCAP_PROJECT75_TOKEN", "")
TZ = ZoneInfo("Africa/Dar_es_Salaam")
OUT = Path(os.getenv("CERT_OUTPUT_DIR", ".certificate-runtime/out"))
TEMPLATE = "MUHAS_STD_01"

RUN_CONFIGS = {
    "DCEPD-SOP-173-2026_ARUSHA_20260928": {
        "venue": "Palace Hotel, Arusha, Tanzania",
        "dates": "28 September - 2 October 2026",
        "template": TEMPLATE,
    }
}

DIRECTOR_NAME = os.getenv("DCEPD_DIRECTOR_NAME", "Prof. Raphael Z. Sangeda")
DIRECTOR_TITLE = os.getenv("DCEPD_DIRECTOR_TITLE", "Director, DCEPD - MUHAS")

GOVT_LOGO_URL = "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c2/Coat_of_arms_of_Tanzania.svg/250px-Coat_of_arms_of_Tanzania.svg.png"
MUHAS_LOGO_URL = "https://muhas.ac.tz/wp-content/uploads/2024/01/LOGO.png"


def api(token, data, files=None, timeout=90):
    if not token:
        raise RuntimeError("Required REDCap token missing")
    payload = {"token": token, **data}
    r = requests.post(REDCAP_URL, data=payload, files=files, timeout=timeout)
    r.raise_for_status()
    return r


def metadata79():
    return api(TOKEN79, {
        "content": "metadata", "format": "json", "returnFormat": "json"
    }).json()


def export79():
    return api(TOKEN79, {
        "content": "record", "format": "json", "type": "flat",
        "rawOrLabel": "raw", "rawOrLabelHeaders": "raw", "returnFormat": "json"
    }).json()


def export75(record_id, label=False):
    return api(TOKEN75, {
        "content": "record", "format": "json", "type": "flat",
        "records[0]": str(record_id),
        "rawOrLabel": "label" if label else "raw",
        "rawOrLabelHeaders": "raw", "returnFormat": "json"
    }).json()


def import79(rows):
    if not rows:
        return
    api(TOKEN79, {
        "content": "record", "format": "json", "type": "flat",
        "overwriteBehavior": "normal", "forceAutoNumber": "false",
        "data": json.dumps(rows, separators=(",", ":")),
        "returnContent": "count", "returnFormat": "json"
    })


def upload_pdf(record_id, pdf_path):
    with open(pdf_path, "rb") as fh:
        files = {"file": (pdf_path.name, fh, "application/pdf")}
        return api(TOKEN79, {
            "content": "file", "action": "import",
            "record": str(record_id), "field": "certificate_file",
            "returnFormat": "json"
        }, files=files).json()


def field_exists(name):
    return any(x.get("field_name") == name for x in metadata79())


def eligible(r):
    return (
        r.get("certificate_generation_requested") == "1"
        and r.get("certificate_generated") != "1"
        and r.get("selected_for_batch") == "1"
        and r.get("batch_role") == "1"
        and r.get("attendance_verified") == "1"
        and r.get("certificate_approved") == "1"
        and bool((r.get("certificate_seq") or "").strip())
        and bool((r.get("certificate_serial_no") or "").strip())
        and r.get("certificate_template_ready") == "1"
        and (r.get("certificate_template_code") or "").strip() == TEMPLATE
    )


def load_image_url(url):
    r = requests.get(url, timeout=45)
    r.raise_for_status()
    return ImageReader(io.BytesIO(r.content))


def fit_font(text, font, max_size, min_size, max_width):
    size = max_size
    while size > min_size and stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def draw_centered_paragraph(c, text, x, y, width, height, style):
    p = Paragraph(text, style)
    w, h = p.wrap(width, height)
    p.drawOn(c, x + (width - w) / 2, y + (height - h) / 2)


def render_certificate(record, course_name, course_director, cfg, pdf_path):
    OUT.mkdir(parents=True, exist_ok=True)
    width, height = landscape(A4)
    c = canvas.Canvas(str(pdf_path), pagesize=(width, height))

    blue = colors.HexColor("#17658B")
    dark_blue = colors.HexColor("#0D4163")
    green = colors.HexColor("#1B6A44")
    red = colors.HexColor("#B51616")
    dark = colors.HexColor("#222222")

    c.setStrokeColor(blue)
    c.setLineWidth(2.2)
    c.rect(18, 18, width - 36, height - 36)
    c.setFillColor(green)
    c.rect(18, height - 27, width - 36, 9, fill=1, stroke=0)
    c.setFillColor(blue)
    c.rect(18, height - 88, width - 36, 58, fill=1, stroke=0)

    govt = load_image_url(GOVT_LOGO_URL)
    muhas = load_image_url(MUHAS_LOGO_URL)
    c.drawImage(govt, 34, height - 157, width=58, height=66, preserveAspectRatio=True, mask="auto")
    c.drawImage(muhas, width - 96, height - 155, width=62, height=62, preserveAspectRatio=True, mask="auto")

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 57, "MUHIMBILI UNIVERSITY OF HEALTH AND ALLIED SCIENCES")
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(width / 2, height - 76, "DIRECTORATE OF CONTINUING EDUCATION AND PROFESSIONAL DEVELOPMENT")

    c.setFillColor(dark_blue)
    c.setFont("Times-Bold", 18)
    c.drawCentredString(width / 2, height - 124, "CERTIFICATE OF SUCCESSFUL PARTICIPATION")

    c.setFillColor(dark)
    c.setFont("Times-Italic", 12.5)
    c.drawCentredString(width / 2, height - 154, "This is to certify that")

    name = (record.get("full_name") or "").strip()
    name_size = fit_font(name, "Times-Bold", 25, 18, width - 170)
    c.setFillColor(red)
    c.setFont("Times-Bold", name_size)
    c.drawCentredString(width / 2, height - 188, name)

    c.setFillColor(dark)
    c.setFont("Times-Roman", 11.5)
    c.drawCentredString(width / 2, height - 214, "has successfully participated in the short course")

    course_style = ParagraphStyle(
        "course", fontName="Times-Bold", fontSize=16.2, leading=17.5,
        textColor=dark_blue, alignment=1
    )
    draw_centered_paragraph(
        c, course_name.upper(), 65, height - 275, width - 130, 50, course_style
    )

    c.setFillColor(dark)
    c.setFont("Times-Roman", 10.5)
    c.drawCentredString(width / 2, height - 295, f"held at {cfg['venue']}")
    c.drawCentredString(width / 2, height - 311, cfg["dates"])

    sig_y = 112
    c.setStrokeColor(colors.HexColor("#555555"))
    c.setLineWidth(0.8)
    c.line(65, sig_y + 42, 260, sig_y + 42)
    c.line(width - 260, sig_y + 42, width - 65, sig_y + 42)

    c.setFillColor(dark)
    c.setFont("Times-Roman", 9)
    c.drawString(65, sig_y + 25, DIRECTOR_NAME)
    c.setFont("Times-Bold", 8.6)
    c.setFillColor(dark_blue)
    c.drawString(65, sig_y + 10, DIRECTOR_TITLE)

    c.setFillColor(dark)
    c.setFont("Times-Roman", 9)
    right_name = course_director or "Course Director"
    c.drawRightString(width - 65, sig_y + 25, right_name)
    c.setFont("Times-Bold", 8.6)
    c.setFillColor(dark_blue)
    c.drawRightString(width - 65, sig_y + 10, "Course Director")

    c.setFillColor(colors.HexColor("#333333"))
    c.setFont("Helvetica", 7.7)
    c.drawString(35, 34, f"Certificate No: {record.get('certificate_serial_no', '')}")
    c.drawRightString(width - 35, 34, f"Application ID: {record.get('record_id', '')}")

    c.showPage()
    c.save()


def course_info(course_id):
    raw = [
        r for r in export75(course_id, label=False)
        if not (r.get("redcap_repeat_instrument") or "").strip()
    ]
    lab = [
        r for r in export75(course_id, label=True)
        if not (r.get("redcap_repeat_instrument") or "").strip()
    ]
    if not raw:
        raise RuntimeError(f"Project 75 course record {course_id} not found")
    rr = raw[0]
    ll = lab[0] if lab else {}
    return (
        (rr.get("course_name") or "").strip(),
        (ll.get("course_director_id") or "").strip(),
    )


def pending_records(limit=None):
    if not field_exists("certificate_file"):
        print("has_request=false")
        print("reason=certificate_file_field_missing")
        return []

    rows = [r for r in export79() if eligible(r)]
    rows.sort(key=lambda r: int(r.get("certificate_seq") or "999999999"))
    if limit:
        rows = rows[:limit]
    return rows


def peek():
    rows = pending_records()
    print("has_request=" + ("true" if rows else "false"))
    print(f"pending_count={len(rows)}")
    if rows:
        print("record_ids=" + ",".join(str(r.get("record_id")) for r in rows))


def process(limit=None):
    rows = pending_records(limit=limit)
    if not rows:
        print("processed_count=0")
        return

    processed = 0
    for r in rows:
        rid = str(r.get("record_id"))
        batch = (r.get("selected_batch_id") or "").strip()
        cfg = RUN_CONFIGS.get(batch)
        if not cfg:
            print(f"skip_record={rid};reason=unsupported_batch:{batch}")
            continue

        course_id = (r.get("applied_course_id") or "").strip()
        course_name, course_director = course_info(course_id)
        if not course_name:
            raise RuntimeError(f"Course title missing for record {rid}")
        if not course_director:
            raise RuntimeError(f"Course director missing for Project 75 course {course_id}")

        serial_safe = (
            r.get("certificate_serial_no") or rid
        ).replace("/", "_").replace("\\", "_")
        pdf_path = OUT / f"{serial_safe}_{rid}.pdf"
        render_certificate(r, course_name, course_director, cfg, pdf_path)

        upload_pdf(rid, pdf_path)
        today = datetime.now(TZ).strftime("%d/%m/%Y")
        import79([{
            "record_id": rid,
            "certificate_generated": "1",
            "certificate_generated_date": today,
            "certificate_generation_requested": "0",
        }])
        processed += 1
        print(f"generated_record={rid};file={pdf_path.name}")

    print(f"processed_count={processed}")


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "peek"
    if command == "peek":
        peek()
    elif command == "process":
        limit = int(os.getenv("CERT_PROCESS_LIMIT", "0") or "0") or None
        process(limit=limit)
    else:
        raise SystemExit("Usage: process_certificate_requests.py [peek|process]")


if __name__ == "__main__":
    main()
