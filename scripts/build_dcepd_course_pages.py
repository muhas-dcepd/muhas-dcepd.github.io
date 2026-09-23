"""Generate one crawlable public page per listed DCEPD course."""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://muhas-dcepd.github.io/"
CATALOGUE = ROOT / "dcepd-courses" / "catalogue.json"
OUT = ROOT / "dcepd-courses" / "courses"


def safe_id(value):
    value = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Unsafe course ID in public catalogue.")
    return value


def e(value):
    return html.escape(str(value or ""), quote=True)


def course_url(course_id):
    return BASE + "dcepd-courses/courses/" + safe_id(course_id) + ".html"


def render(course):
    cid = safe_id(course["id"])
    title = course["title"].strip()
    if not title:
        raise ValueError("Public course has no title.")

    url = course_url(cid)
    code = course.get("code") or "Not yet recorded"
    school = course.get("school") or "MUHAS"
    department = course.get("department") or "Not recorded"
    category = course.get("category") or "Short course"
    fee = course.get("fee_tzs") or "Confirm with DCEPD"
    cpd = course.get("cpd_points") or "Confirm with DCEPD"
    apply_url = course.get("apply_url") or ""
    tags = [str(x).strip() for x in course.get("tags", []) if str(x).strip()]

    description = (
        f"{title}, a MUHAS DCEPD short course. Organising unit: {school}. "
        f"Category: {category}. View course information and use the official application gateway."
    )

    schema = {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": title,
        "courseCode": course.get("code") or None,
        "url": url,
        "keywords": tags,
        "provider": {
            "@type": "Organization",
            "name": "MUHAS Directorate of Continuing Education and Professional Development",
            "url": BASE,
            "parentOrganization": {
                "@type": "CollegeOrUniversity",
                "name": "Muhimbili University of Health and Allied Sciences",
                "url": "https://muhas.ac.tz/",
            },
        },
    }
    schema = {k: v for k, v in schema.items() if v not in (None, "", [])}

    tag_html = "".join(f"<span class='tag'>{e(t)}</span>" for t in tags)
    apply_html = (
        f"<a class='apply' href='{e(apply_url)}'>Apply through the official DCEPD form ↗</a>"
        if apply_url else
        "<p>Application link is not currently recorded.</p>"
    )

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | MUHAS DCEPD</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(url)}"><meta name="robots" content="index,follow">
<meta property="og:title" content="{e(title)} | MUHAS DCEPD">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}"><meta property="og:type" content="website">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace("<","\\u003c")}</script>
<style>
body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:920px;margin:auto;padding:28px;line-height:1.55;color:#17212b}}
a{{color:#075985}}header,footer{{padding:18px 0}}nav{{display:flex;gap:18px;flex-wrap:wrap}}.eyebrow{{font-weight:700;color:#475569;text-transform:uppercase;font-size:.82rem}}h1{{line-height:1.12}}dl{{display:grid;grid-template-columns:minmax(150px,220px) 1fr;gap:8px 18px}}dt{{font-weight:700}}dd{{margin:0}}.tag{{display:inline-block;background:#eef2f7;padding:5px 9px;margin:3px;border-radius:999px}}.apply{{display:inline-block;margin-top:18px;padding:11px 16px;border:1px solid #075985;border-radius:8px;text-decoration:none;font-weight:700}}.fine{{color:#475569;font-size:.93rem}}
</style></head><body>
<header><nav aria-label="DCEPD pages"><a href="/">DCEPD home</a><a href="/dcepd-courses/">All courses</a><a href="/dcepd-dashboard/">Dashboard</a></nav></header>
<main>
<p class="eyebrow">{e(category)}</p><h1>{e(title)}</h1>
<p>{e(school)}{(" · " + e(department)) if department != "Not recorded" else ""}</p>
<div>{tag_html}</div>
<h2>Course information</h2>
<dl>
<dt>Course code</dt><dd>{e(code)}</dd>
<dt>Organising unit</dt><dd>{e(department)}</dd>
<dt>School / institute / directorate</dt><dd>{e(school)}</dd>
<dt>Recorded fee (TZS)</dt><dd>{e(fee)}</dd>
<dt>CPD points</dt><dd>{e(cpd)}</dd>
</dl>
<p class="fine">Confirm the current fee, intake dates, delivery mode and CPD recognition before making arrangements.</p>
{apply_html}
<p><a href="/dcepd-courses/">← Return to the full course catalogue</a></p>
</main>
<footer>MUHAS Directorate of Continuing Education and Professional Development</footer>
</body></html>"""


def build():
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    courses = data.get("courses", [])
    if data.get("count") != len(courses):
        raise ValueError("Catalogue count does not match course list.")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    seen = set()
    for course in courses:
        cid = safe_id(course.get("id"))
        if cid in seen:
            raise ValueError("Duplicate public course ID.")
        seen.add(cid)
        (OUT / f"{cid}.html").write_text(render(course), encoding="utf-8")

    print(f"Built {len(courses)} public DCEPD course pages.")
    return [course_url(c["id"]) for c in courses]


if __name__ == "__main__":
    build()
