#!/usr/bin/env python3
"""Read-only QC for Project 79 applied_course_id choices against Project 75."""
import csv, json, os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = os.getenv("REDCAP_API_URL", "https://utafiti.muhas.ac.tz/api/")
CROSSWALK = ROOT / "automation/project79-course-crosswalk.csv"
OUT = ROOT / "project79-choice-qc" / "project79_course_choice_qc.csv"

def post(token, content, extra=None):
    body=dict(token=token,content=content,format="json",returnFormat="json")
    body.update(extra or {})
    with urlopen(Request(API,data=urlencode(body).encode()),timeout=90) as r:
        value=json.load(r)
    if not isinstance(value,list): raise ValueError("Unexpected REDCap response.")
    return value

def choice_map(metadata, field):
    item=next((m for m in metadata if m.get("field_name")==field),None)
    if not item: raise ValueError(f"Missing Project 79 field: {field}")
    out={}
    for part in (item.get("select_choices_or_calculations") or "").split("|"):
        if "," not in part: continue
        value,label=part.split(",",1)
        out[value.strip()]=label.strip()
    return out

def load_crosswalk():
    with CROSSWALK.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    if not rows or not {"p79_choice_value","p75_record_id"}<=set(rows[0]): raise ValueError("Invalid verified crosswalk.")
    return rows

def main():
    t75=os.environ["REDCAP_PROJECT75_TOKEN"]; t79=os.environ["REDCAP_PROJECT79_TOKEN"]
    fields=["record_id","course_code","course_name"]
    params=dict(action="export",type="flat",rawOrLabel="raw",rawOrLabelHeaders="raw",exportSurveyFields="false",exportDataAccessGroups="false")
    params.update({f"fields[{i}]":v for i,v in enumerate(fields)})
    p75=[r for r in post(t75,"record",params) if not str(r.get("redcap_repeat_instrument","")).strip()]
    choices=choice_map(post(t79,"metadata"),"applied_course_id")
    cross=load_crosswalk()
    by75={}
    mapped_choices=set()
    for row in cross:
        choice=(row.get("p79_choice_value") or "").strip(); rid=(row.get("p75_record_id") or "").strip()
        if choice and rid:
            by75.setdefault(rid,[]).append(choice); mapped_choices.add(choice)
    courses={str(r.get("record_id","")).strip():r for r in p75 if str(r.get("record_id","")).strip()}
    out=[]
    for rid,r in courses.items():
        code=str(r.get("course_code","")).strip(); name=" ".join(str(r.get("course_name","")).split())
        if not code or not name: continue
        expected=f"{code} — {name}"
        mapped=by75.get(rid,[])
        if not mapped:
            out.append(dict(issue_type="ADD_CHOICE",p79_choice_value="",p75_record_id=rid,current_p79_label="",expected_p79_label=expected,action="Review and add a new Project 79 lookup choice; then update the verified crosswalk."))
            continue
        for choice in mapped:
            current=choices.get(choice,"")
            if not current:
                out.append(dict(issue_type="MISSING_CHOICE_VALUE",p79_choice_value=choice,p75_record_id=rid,current_p79_label="",expected_p79_label=expected,action="Restore/review this mapped Project 79 choice value."))
            elif current != expected:
                out.append(dict(issue_type="UPDATE_LABEL",p79_choice_value=choice,p75_record_id=rid,current_p79_label=current,expected_p79_label=expected,action="Review and update label only; do not change the choice value."))
    for choice,label in choices.items():
        if choice not in mapped_choices:
            out.append(dict(issue_type="UNMAPPED_CHOICE",p79_choice_value=choice,p75_record_id="",current_p79_label=label,expected_p79_label="",action="Review; map to the correct Project 75 record or retire through the controlled process."))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    fields=["issue_type","p79_choice_value","p75_record_id","current_p79_label","expected_p79_label","action"]
    with OUT.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
    print(json.dumps({"qc_issues":len(out),"output":str(OUT)}))
if __name__=="__main__": main()
