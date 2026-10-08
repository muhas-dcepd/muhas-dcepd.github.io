#!/usr/bin/env python3
"""Read-only Project 75 catalogue. Standard library only; never export applicants."""
import argparse
import csv
import html
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK_PATH = ROOT / 'automation/project79-course-crosswalk.csv'
APPLY_URL = 'https://utafiti.muhas.ac.tz/surveys/?s=RCJLANHXKKMKXC7W'
API_URL = 'https://utafiti.muhas.ac.tz/api/'
MASTER_FIELDS = ['record_id', 'course_name', 'course_code', 'public_catalogue',
          'course_department_code', 'course_school_code', 'fee_per_person_tsh', 'cpd_points',
          'course_summary', 'course_duration', 'delivery_mode', 'target_audience',
          'learning_outcomes', 'certificate_awarded', 'date_next_offered',
          'course_requires_cv', 'course_requires_certificate']
RUN_FIELDS = ['record_id', 'run_start_date', 'run_end_date', 'run_application_open_date',
              'run_application_close_date', 'run_status']
FIELDS = MASTER_FIELDS + [f for f in RUN_FIELDS if f not in MASTER_FIELDS]
LABELS = dict(zip(FIELDS, ['Record ID', 'Course name', 'Course code', 'Listed in public catalogue?',
    'Department', 'School / institute / directorate', 'Fee per person (TZS)', 'CPD points',
    'Course summary', 'Course duration', 'Delivery mode', 'Target audience / eligibility',
    'Key learning outcomes', 'Certificate awarded', 'Next date offered',
    'Require applicants to upload a CV?', 'Require applicants to upload an academic / professional certificate?',
    'Run start date', 'Run end date', 'Application opening date', 'Application closing date', 'Run status']))

# Subject filtering is intentionally broader than the single editorial primary category.
# A course may therefore appear under more than one subject when its title/tags/catalogue text
# contain a strong subject-specific term. This affects discovery only, not accreditation/status.
SUBJECT_RULES = {
    'Digital Health, Data Science & Informatics': [
        'digital health', 'health data', 'data analytics', 'data science', 'informatics',
        'artificial intelligence', 'machine learning', 'programming', 'r programming',
        'cybersecurity', 'computer applications', 'computer programming'
    ],
    'Research Methods, Evidence & Scientific Writing': [
        'research method', 'research ethics', 'research integrity', 'scientific writing',
        'systematic review', 'meta analysis', 'qualitative', 'implementation science',
        'implementation research', 'grant writing', 'proposal writing', 'good clinical practice',
        'evidence synthesis', 'academic writing'
    ],
    'Pharmacy, Medicines & Supply Chains': [
        'pharmacy', 'pharmaceutical', 'pharmacokinetic', 'pharmacovigilance', 'medicine safety',
        'medicines', 'drug development', 'health commodities', 'supply chain',
        'forecasting', 'inventory control', 'rational use of antimicrobials',
        'antimicrobial stewardship'
    ],
    'Emergency, Critical Care & Patient Safety': [
        'emergency care', 'critical care', 'resuscitation', 'ambulance', 'paramedic',
        'anaesthesia', 'anesthesia', 'disaster response', 'prehospital'
    ],
    'Clinical Care & Diagnostics': [
        'clinical care', 'diagnosis', 'diagnostic', 'echocardiography', 'electrocardiography',
        'ultrasound', 'dialysis', 'palliative care', 'spirometry'
    ],
    'Public Health, One Health & Environment': [
        'public health', 'one health', 'climate and health', 'climate change and health',
        'surveillance', 'community engagement', 'epidemiology', 'occupational health',
        'environmental health', 'health system strengthening'
    ],
    'Maternal, Newborn & Child Health': [
        'maternal', 'obstetric', 'newborn', 'neonatal', 'paediatric', 'pediatric', 'child health'
    ],
    'Mental Health, Rehabilitation & Wellbeing': [
        'mental health', 'psychosocial', 'substance use', 'addiction', 'rehabilitation',
        'wellness', 'weight management'
    ],
    'Education, Mentorship & Simulation': [
        'mentorship', 'mentoring', 'teaching', 'clinical teaching', 'simulation',
        'supervision', 'competency based education', 'preceptorship'
    ],
    'Health Leadership, Management & Financing': [
        'leadership', 'management', 'financing', 'health economics', 'economic evaluation',
        'project management', 'entrepreneurship'
    ],
    'Traditional Medicine & Natural Products': [
        'traditional medicine', 'herbal medicine', 'medicinal plants', 'pharmacognosy',
        'natural products'
    ],
    'Laboratory Sciences, Genomics & Biotechnology': [
        'laboratory', 'genomics', 'omics', 'bioinformatics', 'microscopy', 'cytotechnology',
        'biosafety', 'gene therapy', 'biotechnology'
    ],
}

def display_date_dmy(value):
    value = str(value or '').strip()
    if not value:
        return ''
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(value, fmt).strftime('%d-%m-%Y')
        except ValueError:
            pass
    return value

def normalise(text):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()).split())

def api_export(token, content, extra=None):
    body = dict(token=token, content=content, format='json', returnFormat='json')
    body.update(extra or {})
    try:
        with urlopen(Request(API_URL, data=urlencode(body).encode()), timeout=180) as response:
            value = json.load(response)
    except Exception:
        raise ValueError('Project 75 export failed. Check the API endpoint, token and export permissions; existing catalogue retained.') from None
    if not isinstance(value, list) or any(not isinstance(r, dict) for r in value):
        raise ValueError('Project 75 did not return a valid record list; existing catalogue retained.')
    return value

def fetch_records():
    token = os.environ.get('REDCAP_PROJECT75_TOKEN', '').strip()
    if not token:
        raise ValueError('Set the REDCAP_PROJECT75_TOKEN repository secret to enable the read-only refresh.')
    metadata = api_export(token, 'metadata')
    md = {m['field_name']: m for m in metadata}
    if not set(FIELDS).issubset(md):
        raise ValueError('Required Project 75 catalogue fields are missing.')
    field = md['public_catalogue']
    if field['field_type'] == 'yesno':
        yes_code = '1'
    else:
        options = [x.split(',', 1) for x in field.get('select_choices_or_calculations', '').split('|')]
        yes = [v[0].strip() for v in options if len(v) == 2 and v[1].strip().lower() == 'yes']
        if len(yes) != 1:
            raise ValueError('Cannot verify the stored Yes value for public_catalogue.')
        yes_code = yes[0]
    if not re.fullmatch(r'[A-Za-z0-9_]+', yes_code):
        raise ValueError('Unexpected catalogue choice code.')
    # Keep the public master export small and filtered. Fetch the repeating
    # Course Run Log separately with only run fields, then combine in memory.
    master_params = dict(action='export', type='flat', rawOrLabel='label', rawOrLabelHeaders='raw',
                  exportSurveyFields='false', exportDataAccessGroups='false',
                  filterLogic=f"[public_catalogue] = '{yes_code}'")
    master_params.update({f'fields[{i}]': f for i, f in enumerate(MASTER_FIELDS)})
    masters = api_export(token, 'record', master_params)

    run_params = dict(action='export', type='flat', rawOrLabel='label', rawOrLabelHeaders='raw',
                  exportSurveyFields='false', exportDataAccessGroups='false')
    run_params.update({f'fields[{i}]': f for i, f in enumerate(RUN_FIELDS)})
    runs = api_export(token, 'record', run_params)
    return masters + [r for r in runs if str(r.get('redcap_repeat_instrument', '')).strip()]


def parse_date(value):
    value = str(value or '').strip()
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None

def load_choice_by_course(path=CROSSWALK_PATH):
    """Return unambiguous Project 75 record -> Project 79 choice mappings."""
    if not path.exists():
        return {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows or not {'p79_choice_value', 'p75_record_id'} <= set(rows[0]):
        raise ValueError('Verified Project 79 course crosswalk has an invalid schema.')
    grouped = {}
    for row in rows:
        choice = str(row.get('p79_choice_value', '')).strip()
        rid = str(row.get('p75_record_id', '')).strip()
        if not choice or not rid:
            raise ValueError('Verified Project 79 course crosswalk contains a missing mapping.')
        grouped.setdefault(rid, []).append(choice)
    return {rid: choices[0] for rid, choices in grouped.items() if len(set(choices)) == 1}

def yes_flag(value):
    return '1' if str(value or '').strip().lower() in {'1', 'yes', 'true'} else '0'

def run_is_open(run, as_of):
    start = parse_date(run.get('run_start_date', ''))
    opened = parse_date(run.get('run_application_open_date', ''))
    closes = parse_date(run.get('run_application_close_date', ''))
    status = str(run.get('run_status', '')).strip().lower()
    return (
        status in {'1', 'open for applications'}
        and start is not None and start >= as_of
        and (opened is None or opened <= as_of)
        and (closes is None or closes >= as_of)
    )

def build_apply_url(choice, run_id, requires_cv, requires_certificate):
    params = urlencode({
        'applied_course_id': choice,
        'applied_run_id': run_id,
        'course_requires_cv': requires_cv,
        'course_requires_certificate': requires_certificate,
    })
    return APPLY_URL + '&' + params

def build(records, source, source_at, taxonomy, choice_by_course=None, as_of=None):
    choice_by_course = choice_by_course or {}
    if as_of is None:
        as_of = parse_date(str(source_at)[:10]) or datetime.now(timezone.utc).date()

    runs_by_course = {}
    for row in records:
        instrument = str(row.get('redcap_repeat_instrument', '')).strip()
        if instrument not in {'course_run_log', 'Course Run Log'}:
            continue
        rid = str(row.get('record_id', '')).strip()
        instance = str(row.get('redcap_repeat_instance', '')).strip()
        if not rid or not instance:
            continue
        run = dict(row)
        run['run_batch_id'] = f"{rid}-{instance}"
        runs_by_course.setdefault(rid, []).append(run)

    courses, seen = [], set()
    for row in records:
        if row.get('redcap_repeat_instrument', '').strip():
            continue
        if row.get('public_catalogue', '').strip().lower() != 'yes':
            continue
        if not set(MASTER_FIELDS).issubset(row):
            raise ValueError('Incomplete catalogue master record schema.')
        rid = row['record_id'].strip()
        if not rid or rid in seen:
            raise ValueError('Missing or duplicate master-course ID.')
        seen.add(rid)
        title = ' '.join(row['course_name'].split())
        if not title:
            raise ValueError('A listed course has no title; correct the source record.')
        classification = taxonomy['courses'].get(rid, {})
        if classification.get('source_title') != title:
            classification = {}
        category = classification.get('category', 'Other courses')
        tags = set(classification.get('tags', []))
        norm_title = normalise(title)
        for rule in taxonomy['keyword_rules']:
            if re.search(rule['pattern'], norm_title):
                tags.update(rule['tags'])

        future_runs = []
        open_runs = []
        choice = str(choice_by_course.get(rid, '')).strip()
        requires_cv = yes_flag(row.get('course_requires_cv', ''))
        requires_certificate = yes_flag(row.get('course_requires_certificate', ''))
        for run in runs_by_course.get(rid, []):
            start = parse_date(run.get('run_start_date', ''))
            status = str(run.get('run_status', '')).strip().lower()
            if start is not None and start >= as_of and status not in {'4', '5', 'cancelled', 'postponed'}:
                future_runs.append((start, run))
            if choice and run_is_open(run, as_of):
                open_runs.append(dict(
                    run_id=run['run_batch_id'],
                    start=display_date_dmy(run.get('run_start_date', '')),
                    end=display_date_dmy(run.get('run_end_date', '')),
                    application_close=display_date_dmy(run.get('run_application_close_date', '')),
                    apply_url=build_apply_url(choice, run['run_batch_id'], requires_cv, requires_certificate),
                ))
        future_runs.sort(key=lambda x: x[0])
        open_runs.sort(key=lambda x: parse_date(x['start']) or date.max)
        next_date = display_date_dmy(future_runs[0][1].get('run_start_date', '')) if future_runs else ''

        courses.append(dict(id=rid, title=classification.get('display_title', title), source_title=title,
            code=row['course_code'].strip(), school=row['course_school_code'].strip(),
            department=row['course_department_code'].strip(), fee_tzs=row['fee_per_person_tsh'].strip(),
            cpd_points=row['cpd_points'].strip(), summary=row['course_summary'].strip(),
            duration=row['course_duration'].strip(), delivery_mode=row['delivery_mode'].strip(),
            target_audience=row['target_audience'].strip(), learning_outcomes=row['learning_outcomes'].strip(),
            certificate_awarded=row['certificate_awarded'].strip(),
            date_next_offered=next_date,
            category=category, tags=sorted(tags), open_runs=open_runs,
            apply_url=open_runs[0]['apply_url'] if len(open_runs) == 1 else ''))
    courses.sort(key=lambda c: normalise(c['title']))
    return dict(schema_version=2, source=source, source_at=source_at,
                api_refreshed_at=source_at if source == 'Project 75 API' else None,
                count=len(courses), courses=courses)

def subject_categories(c):
    haystack = normalise(' '.join([
        c['title'], c['source_title'], c['category'], c['summary'],
        c['target_audience'], c['learning_outcomes'], *c['tags']
    ]))
    subjects = {c['category']}
    for subject, terms in SUBJECT_RULES.items():
        if any(normalise(term) in haystack for term in terms):
            subjects.add(subject)
    return sorted(subjects)

def render_card(c):
    e = lambda x: html.escape(str(x), quote=True)
    tags = ''.join(f'<span class="tag">{e(t)}</span>' for t in c['tags'])
    search = normalise(' '.join([c['title'], c['source_title'], c['code'], c['school'], c['department'], c['category'], c['summary'], c['target_audience'], c['learning_outcomes'], *c['tags']]))
    details = ''.join(f'<div><dt>{label}</dt><dd>{e(value)}</dd></div>' for label, value in [
        ('Course code', c['code'] or 'Not yet recorded'), ('Organising unit', c['department'] or 'Not recorded'),
        ('School / institute / directorate', c['school'] or 'Not recorded'),
        ('Duration', c['duration'] or 'Confirm with DCEPD'),
        ('Delivery mode', c['delivery_mode'] or 'Confirm with DCEPD'),
        ('Next offered', c['date_next_offered'] or 'To be announced'),
        ('Recorded fee (TZS)', c['fee_tzs'] or 'Confirm with DCEPD'),
        ('CPD points', c['cpd_points'] or 'Confirm with DCEPD'),
        ('Certificate', c['certificate_awarded'] or 'Confirm with DCEPD')])
    detail_url = f"courses/{e(c['id'])}.html"
    subjects = '|'.join(subject_categories(c))
    summary = f'<p class="summary">{e(c["summary"])}</p>' if c['summary'] else ''
    coming = f'<p class="coming-soon"><strong>Coming soon:</strong> {e(c["date_next_offered"])}</p>' if c['date_next_offered'] else ''
    if c['open_runs']:
        buttons = []
        for run in c['open_runs']:
            label = f"Apply · {run['start']}" if len(c['open_runs']) > 1 else "Apply now"
            buttons.append(f'<a class="apply" href="{e(run["apply_url"])}" aria-label="Apply: {e(c["title"])} · {e(run["start"])}">{e(label)} <span aria-hidden="true">↗</span></a>')
        actions = '<div class="card-actions">' + ''.join(buttons) + '<span>Open intake</span></div>'
    else:
        actions = '<div class="card-actions"><span class="apply" aria-disabled="true">Apply not open</span><span>Applications open after a future run is scheduled and opened in DCEPD.</span></div>'
    return f'''<article class="course" id="course-{e(c['id'])}" data-category="{e(c['category'])}" data-subjects="{e(subjects)}" data-school="{e(c['school'])}" data-search="{e(search)}">
    <p class="category">{e(c['category'])}</p><h3><a href="{detail_url}">{e(c['title'])}</a></h3>
    <p class="unit">{e(c['school'] or 'MUHAS')}</p>{coming}{summary}<div class="tags">{tags}</div>
    <details><summary>Course details</summary><dl>{details}</dl><p class="fine">Confirm the current fee, intake dates and CPD recognition before making arrangements.</p></details>
    {actions}</article>'''

def save(data):
    out = ROOT / 'dcepd-courses'
    template = (ROOT / 'scripts/dcepd_catalogue_template.html').read_text()
    categories = sorted(set(SUBJECT_RULES) | {c['category'] for c in data['courses']})
    schools = sorted({c['school'] for c in data['courses'] if c['school']})
    options = lambda values: ''.join(f'<option value="{html.escape(v, quote=True)}">{html.escape(v)}</option>' for v in values)
    replacements = {'CARDS': '\n'.join(render_card(c) for c in data['courses']), 'COUNT': str(data['count']),
        'CATEGORY_OPTIONS': options(categories), 'SCHOOL_OPTIONS': options(schools),
        'SOURCE': html.escape(data['source']), 'SOURCE_AT': html.escape(data['source_at']),
        'REFRESH_LABEL': 'Last successful API refresh' if data['api_refreshed_at'] else 'Registry export dated',
        'CATEGORY_COUNT': str(len(categories)), 'SCHOOL_COUNT': str(len(schools))}
    for key, value in replacements.items():
        template = template.replace('{{' + key + '}}', value)
    out.mkdir(exist_ok=True)
    # Build in memory first. Only successful extraction/validation replaces published outputs.
    for path, value in [(out/'catalogue.json', json.dumps(data, ensure_ascii=False, indent=2)+'\n'), (out/'index.html', template)]:
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(value, encoding='utf-8')
        tmp.replace(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed-csv', type=Path)
    parser.add_argument('--source-at')
    args = parser.parse_args()
    if args.seed_csv:
        if not args.source_at:
            parser.error('--source-at is required with --seed-csv')
        with args.seed_csv.open(encoding='utf-8-sig', newline='') as f:
            records = [{**{k: r.get(v, '') for k, v in LABELS.items()}, 'redcap_repeat_instrument': r.get('Repeat Instrument', ''), 'redcap_repeat_instance': r.get('Repeat Instance', '')} for r in csv.DictReader(f)]
        source, stamp = 'Supplied Project 75 export', args.source_at
    else:
        records = fetch_records()
        source, stamp = 'Project 75 API', datetime.now(timezone.utc).isoformat(timespec='seconds')
    taxonomy = json.loads((ROOT/'scripts/dcepd_taxonomy.json').read_text())
    data = build(records, source, stamp, taxonomy, choice_by_course=load_choice_by_course())
    save(data)
    from build_site_seo import optimise_site
    optimise_site()
    print(f"Published catalogue contains {data['count']} listed master-course records.")

if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        sys.exit(str(exc))
