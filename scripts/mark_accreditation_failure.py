#!/usr/bin/env python3
import json, os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

REDCAP_URL=os.getenv("REDCAP_URL","https://utafiti.muhas.ac.tz/api/")
TOKEN=os.getenv("REDCAP_PROJECT75_TOKEN","")
ADMIN="accreditation_publication_control"
TZ=ZoneInfo("Africa/Dar_es_Salaam")

def api(data):
    if not TOKEN:
        raise RuntimeError("REDCAP_PROJECT75_TOKEN missing")
    r=requests.post(REDCAP_URL,data={"token":TOKEN,**data},timeout=90)
    r.raise_for_status()
    return r

def export_records():
    return api({"content":"record","format":"json","type":"flat","rawOrLabel":"raw","rawOrLabelHeaders":"raw","returnFormat":"json"}).json()

def import_rows(rows):
    api({"content":"record","format":"json","type":"flat","overwriteBehavior":"normal","forceAutoNumber":"false","data":json.dumps(rows,separators=(",",":")),"returnContent":"count","returnFormat":"json"})

def inst(r):
    try:
        return int(r.get("redcap_repeat_instance") or 0)
    except Exception:
        return 0

def main():
    rows=export_records()
    pending=[
        r for r in rows
        if r.get("record_id")=="1"
        and r.get("redcap_repeat_instrument")==ADMIN
        and r.get("apc_action_type")=="2"
        and r.get("apc_trigger_requested")=="1"
        and r.get("apc_trigger_warning_ack")=="1"
        and (r.get("apc_status") or "") in ("","1","2")
    ]
    if not pending:
        print("failure_writeback=not_needed")
        return
    req=min(pending,key=inst)
    reason=os.getenv("APC_FAILURE_REASON","GitHub accreditation workflow failed. Review the workflow log before retrying.")[:1000]
    row={
        "record_id":"1",
        "redcap_repeat_instrument":ADMIN,
        "redcap_repeat_instance":str(inst(req)),
        "apc_status":"4",
        "apc_qc_errors":"1",
        "apc_completed_at":datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "apc_result_message":reason,
    }
    import_rows([row])
    print(f"failure_writeback=instance_{inst(req)}")

if __name__=="__main__":
    main()
