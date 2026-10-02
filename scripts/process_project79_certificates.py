#!/usr/bin/env python3
import io
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

REDCAP_URL = os.getenv("REDCAP_API_URL", "https://utafiti.muhas.ac.tz/api/")
TOKEN = os.environ["REDCAP_PROJECT79_TOKEN"]
TZ = ZoneInfo("Africa/Dar_es_Salaam")
TEST_ONLY = {x.strip() for x in os.getenv("DCEPD_CERT_TEST_ONLY", "").split(",") if x.strip()}

GOVT_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MUHAS_LOGO_URL = "https://muhas.ac.tz/wp-content/uploads/2024/01/LOGO.png"

RUNS = {
    "DCEPD-SOP-173-2026_ARUSHA_20260928": {
        "course_title": "MASTERING INVENTORY CONTROL AND LOGISTICS FOR HEALTH COMMODITIES",
        "venue": "Palace Hotel, Arusha, Tanzania",
        "course_dates": "28 September - 2 October 2026",
        "signatory1_name": "Prof. Raphael Z. Sangeda",
        "signatory1_title": "Director, DCEPD - MUHAS",
        "signatory2_name": "Dr Betty Maganda",
        "signatory2_title": "Course Director",
    }
}

FIELDS = [
    "record_id", "full_name", "selected_for_batch", "selected_batch_id", "batch_role",
    "attendance_verified", "certificate_approved", "certificate_seq",
    "certificate_template_code", "certificate_template_ready",
    "certificate_generation_requested", "certificate_serial_no",
    "certificate_generated", "certificate_generated_date", "certificate_file"
]

def redcap_post(data, files=None):
    data = dict(data)
    data["token"] = TOKEN
    r = requests.post(REDCAP_URL, data=data, files=files, timeout=60)
    r.raise_for_status()
    return r

def export_records():
    r = redcap_post({
        "content": "record", "format": "json", "type": "flat",
        "fields": ",".join(FIELDS), "rawOrLabel": "raw", "rawOrLabelHeaders": "raw",
        "exportCheckboxLabel": "false", "returnFormat": "json"
    })
    return r.json()

def is_yes(v):
    return str(v).strip() == "1"

def eligible(rec):
    rid = str(rec.get("record_id", "")).strip()
    if TEST_ONLY and rid not in TEST_ONLY:
        return False
    if not is_yes(rec.get("selected_for_batch")):
        return False
    if str(rec.get("batch_role", "")).strip().lower() not in {"participant", "1"}:
        return False
    if not is_yes(rec.get("attendance_verified")):
        return False
    if not is_yes(rec.get("certificate_approved")):
        return False
    if not str(rec.get("certificate_seq", "")).strip():
        return False
    if str(rec.get("certificate_template_code", "")).strip() != "MUHAS_STD_01":
        return False
    if not is_yes(rec.get("certificate_template_ready")):
        return False
    if not is_yes(rec.get("certificate_generation_requested")):
        return False
    if not str(rec.get("certificate_serial_no", "")).strip():
        return False
    if is_yes(rec.get("certificate_generated")):
        return False
    batch = str(rec.get("selected_batch_id", "")).strip()
    return batch in RUNS

def draw_wrapped_centered(c, text, y, max_width, font="Times-Bold", size=18, leading=20):
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, font, size) <= max_width or not line:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    for ln in lines[:3]:
        c.setFont(font, size)
        c.drawCentredString(landscape(A4)[0]/2, y, ln)
        y -= leading
    return y

def make_pdf(rec):
    cfg = RUNS[str(rec["selected_batch_id"]).strip()]
    buf = io.BytesIO()
    W, H = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(W, H))

    c.setStrokeColor(colors.HexColor("#0C6B4D"))
    c.setLineWidth(2.4)
    c.rect(18, 18, W-36, H-36)
    c.setFillColor(colors.HexColor("#1C7FA6"))
    c.rect(18, H-86, W-36, 68, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(W/2, H-52, "MUHIMBILI UNIVERSITY OF HEALTH AND ALLIED SCIENCES")
    c.setFont("Helvetica", 11)
    c.drawCentredString(W/2, H-70, "Dar es Salaam, Tanzania")

    q = requests.get(GOVT_COMMONS_API, headers={"User-Agent":"MUHAS-DCEPD-Certificate-System/1.0 (institutional automation)"}, params={
        "action": "query",
        "titles": "File:Coat of arms of Tanzania.svg",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "400",
        "format": "json"
    }, timeout=30)
    q.raise_for_status()
    pages = q.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    gov_url = page["imageinfo"][0].get("thumburl") or page["imageinfo"][0]["url"]
    gov_resp = requests.get(gov_url, headers={"User-Agent":"MUHAS-DCEPD-Certificate-System/1.0 (institutional automation)"}, timeout=30)
    gov_resp.raise_for_status()
    muh_resp = requests.get(MUHAS_LOGO_URL, headers={"User-Agent":"MUHAS-DCEPD-Certificate-System/1.0"}, timeout=30)
    muh_resp.raise_for_status()
    gov = ImageReader(io.BytesIO(gov_resp.content))
    muh = ImageReader(io.BytesIO(muh_resp.content))
    c.drawImage(gov, 46, H-170, width=74, height=82, preserveAspectRatio=True, mask="auto")
    c.drawImage(muh, W-125, H-166, width=78, height=78, preserveAspectRatio=True, mask="auto")

    c.setFillColor(colors.HexColor("#0B5675"))
    c.setFont("Times-Bold", 18)
    c.drawCentredString(W/2, H-120, "Certificate of successful participation")
    c.setFillColor(colors.black)
    c.setFont("Times-Roman", 14)
    c.drawCentredString(W/2, H-154, "This is to certify that")

    c.setFillColor(colors.HexColor("#A31515"))
    c.setFont("Times-Bold", 25)
    c.drawCentredString(W/2, H-194, str(rec.get("full_name", "")).strip())

    c.setFillColor(colors.black)
    c.setFont("Times-Roman", 13)
    c.drawCentredString(W/2, H-220, "has successfully participated in the short course")

    c.setFillColor(colors.HexColor("#07577B"))
    y = H-254
    y = draw_wrapped_centered(c, cfg["course_title"], y, W-150, size=19, leading=22)

    c.setFillColor(colors.black)
    c.setFont("Times-Roman", 11)
    c.drawCentredString(W/2, y-6, f'held at {cfg["venue"]}')
    c.drawCentredString(W/2, y-24, cfg["course_dates"])

    sig_y = 105
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.line(76, sig_y+35, 300, sig_y+35)
    c.line(W-300, sig_y+35, W-76, sig_y+35)
    c.setFont("Times-Roman", 10)
    c.drawString(76, sig_y+19, cfg["signatory1_name"])
    c.setFont("Times-Bold", 9)
    c.setFillColor(colors.HexColor("#07577B"))
    c.drawString(76, sig_y+5, cfg["signatory1_title"])
    c.setFillColor(colors.black)
    c.setFont("Times-Roman", 10)
    c.drawRightString(W-76, sig_y+19, cfg["signatory2_name"])
    c.setFont("Times-Bold", 9)
    c.setFillColor(colors.HexColor("#07577B"))
    c.drawRightString(W-76, sig_y+5, cfg["signatory2_title"])

    c.setFillColor(colors.HexColor("#333333"))
    c.setFont("Helvetica", 7.8)
    c.drawString(40, 38, f'Certificate No: {str(rec.get("certificate_serial_no", "")).strip()}')
    c.drawRightString(W-40, 38, f'Application ID: {str(rec.get("record_id", "")).strip()}')

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

def upload_certificate(rid, pdf_bytes):
    fn = f"DCEPD_Certificate_{rid}.pdf"
    r = redcap_post({
        "content": "file",
        "action": "import",
        "record": rid,
        "field": "certificate_file",
        "returnFormat": "json"
    }, files={"file": (fn, pdf_bytes, "application/pdf")})
    return r.json() if r.text.strip() else {"ok": True}

def mark_generated(rid):
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    payload = [{
        "record_id": rid,
        "certificate_generated": "1",
        "certificate_generated_date": today,
        "certificate_generation_requested": "0"
    }]
    r = redcap_post({
        "content": "record",
        "format": "json",
        "type": "flat",
        "overwriteBehavior": "normal",
        "data": json.dumps(payload),
        "returnContent": "count",
        "returnFormat": "json"
    })
    return r.json() if r.text.strip() else {"ok": True}

def main():
    records = export_records()
    todo = [r for r in records if eligible(r)]
    print(f"eligible={len(todo)}")
    if not todo:
        return 0
    failures = 0
    for rec in todo:
        rid = str(rec["record_id"]).strip()
        try:
            pdf = make_pdf(rec)
            upload_certificate(rid, pdf)
            mark_generated(rid)
            print(f"generated={rid} certificate={rec.get('certificate_serial_no','')}")
        except Exception as e:
            failures += 1
            print(f"ERROR record={rid}: {type(e).__name__}: {e}", file=sys.stderr)
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
