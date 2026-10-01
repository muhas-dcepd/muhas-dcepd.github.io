#!/usr/bin/env python3
import os, sys, json, csv, re, zipfile, smtplib, ssl
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo
from email.message import EmailMessage
import requests

REDCAP_URL=os.getenv('REDCAP_URL','https://utafiti.muhas.ac.tz/api/')
TOKEN=os.getenv('REDCAP_PROJECT75_TOKEN','')
TZ=ZoneInfo('Africa/Dar_es_Salaam')
ADMIN='accreditation_publication_control'
OUT=Path(os.getenv('APC_OUTPUT_DIR','.project75-runtime/accreditation'))
STATE=OUT/'state.json'
DEFAULT_STEM='KB 328/364/'
DEFAULT_VOLUME='25'

def api(data):
    if not TOKEN: raise RuntimeError('REDCAP_PROJECT75_TOKEN missing')
    r=requests.post(REDCAP_URL,data={'token':TOKEN,**data},timeout=90); r.raise_for_status(); return r

def export_records(label=False):
    return api({'content':'record','format':'json','type':'flat','rawOrLabel':'label' if label else 'raw','rawOrLabelHeaders':'raw','returnFormat':'json'}).json()

def import_rows(rows):
    if not rows:return
    api({'content':'record','format':'json','type':'flat','overwriteBehavior':'normal','forceAutoNumber':'false','data':json.dumps(rows,separators=(',',':')),'returnContent':'count','returnFormat':'json'})

def masters(rows): return [r for r in rows if not (r.get('redcap_repeat_instrument') or '').strip()]
def admins(rows): return [r for r in rows if r.get('record_id')=='1' and r.get('redcap_repeat_instrument')==ADMIN]
def inst(r):
    try:return int(r.get('redcap_repeat_instance') or 0)
    except:return 0

def pdate(s):
    try:return datetime.strptime((s or '').strip(),'%Y-%m-%d').date()
    except:return None

def quarter(d):
    y,m=d.year,d.month
    if 7<=m<=9:return date(y,7,1),date(y,9,30),'Q1',f'{y}/{(y+1)%100:02d}'
    if 10<=m<=12:return date(y,10,1),date(y,12,31),'Q2',f'{y}/{(y+1)%100:02d}'
    if m<=3:return date(y,1,1),date(y,3,31),'Q3',f'{y-1}/{y%100:02d}'
    return date(y,4,1),date(y,6,30),'Q4',f'{y-1}/{y%100:02d}'

def selected_period(fy_raw, q_raw):
    m=re.fullmatch(r'FY(\d{4})_(\d{2})',(fy_raw or '').strip())
    if not m: raise RuntimeError('Select a valid fiscal year before requesting the batch.')
    start_year=int(m.group(1))
    q=str(q_raw or '').strip()
    if q=='1': return date(start_year,7,1),date(start_year,9,30),'Q1',f'{start_year}/{(start_year+1)%100:02d}'
    if q=='2': return date(start_year,10,1),date(start_year,12,31),'Q2',f'{start_year}/{(start_year+1)%100:02d}'
    if q=='3': return date(start_year+1,1,1),date(start_year+1,3,31),'Q3',f'{start_year}/{(start_year+1)%100:02d}'
    if q=='4': return date(start_year+1,4,1),date(start_year+1,6,30),'Q4',f'{start_year}/{(start_year+1)%100:02d}'
    raise RuntimeError('Select a valid quarter before requesting the batch.')

def date_reset_allowed(today, selected_start, selected_end):
    current_start,current_end,_,_=quarter(today)
    if selected_start==current_start and selected_end==current_end:
        return True
    previous_end=current_start.fromordinal(current_start.toordinal()-1)
    previous_start,_,_,_=quarter(previous_end)
    return selected_start==previous_start and selected_end==previous_end and (today-current_start).days <= 19

def update_admin(i,fields):
    row={'record_id':'1','redcap_repeat_instrument':ADMIN,'redcap_repeat_instance':str(i),**{k:str(v) for k,v in fields.items()}}
    import_rows([row])

def current_settings(adm,ms):
    s=sorted([r for r in adm if r.get('apc_action_type')=='1'],key=inst)
    stem=(s[-1].get('apc_reference_stem') if s else '') or DEFAULT_STEM
    vol=(s[-1].get('apc_reference_volume') if s else '') or ''
    stem=stem.strip()
    if not vol:
        pat=re.compile(r'^'+re.escape(stem)+r'([^/]+)/([0-9]+)$'); c=[]
        for r in ms:
            m=pat.match((r.get('approval_reference') or '').strip())
            if m:c.append((pdate(r.get('accreditation_date')) or date.min,m.group(1)))
        vol=max(c,key=lambda x:x[0])[1] if c else DEFAULT_VOLUME
    return stem,vol.strip()

def get_pending(adm):
    x=[r for r in adm if r.get('apc_action_type')=='2' and r.get('apc_trigger_requested')=='1' and r.get('apc_trigger_warning_ack')=='1' and (r.get('apc_status') or '') in ('','1')]
    return min(x,key=inst) if x else None

def claim():
    rows=export_records(); adm=admins(rows); req=get_pending(adm); OUT.mkdir(parents=True,exist_ok=True)
    if not req:
        print('has_request=false'); return
    i=inst(req); now=datetime.now(TZ); today=now.date(); ms=masters(rows)
    qs,qe,q,fy=selected_period(req.get('apc_process_fiscal_year'),req.get('apc_process_quarter'))
    reset_dates=date_reset_allowed(today,qs,qe)
    sel=[r for r in ms if (d:=pdate(r.get('accreditation_date'))) and qs<=d<=qe]
    if not sel:
        update_admin(i,{
            'apc_status':'3',
            'apc_trigger_date':today,
            'apc_quarter':f'{fy} {q}',
            'apc_letters_generated':'0',
            'apc_qc_errors':'0',
            'apc_qc_warnings':'0',
            'apc_completed_at':now.strftime('%Y-%m-%d %H:%M:%S'),
            'apc_result_message':f'No action required: no courses accredited between {qs} and {qe}.'
        })
        print('has_request=false')
        print('no_action=true')
        return
    missing=[]
    for r in sel:
        for f in ('accreditation_date','course_director_id','course_department_code','course_school_code'):
            if not (r.get(f) or '').strip():missing.append(f"record {r['record_id']}: {f}")
    if missing:
        update_admin(i,{'apc_status':'4','apc_trigger_date':today,'apc_quarter':f'{fy} {q}','apc_qc_errors':len(missing),'apc_completed_at':now.strftime('%Y-%m-%d %H:%M:%S'),'apc_result_message':'Missing required fields: '+'; '.join(missing[:20])}); raise RuntimeError('; '.join(missing))
    stem,vol=current_settings(adm,ms); pat=re.compile(r'^'+re.escape(stem)+re.escape(vol)+r'/([0-9]+)$'); seen={}; mx=0
    for r in ms:
        m=pat.match((r.get('approval_reference') or '').strip())
        if m:
            n=int(m.group(1));mx=max(mx,n);seen.setdefault(n,[]).append(r['record_id'])
    dup={k:v for k,v in seen.items() if len(v)>1}
    if dup:raise RuntimeError('Duplicate serials: '+json.dumps(dup))
    refs={}; nxt=mx+1
    for r in sorted(sel,key=lambda r:(r.get('accreditation_date') or '',int(r['record_id']))):
        ref=(r.get('approval_reference') or '').strip()
        if not ref:ref=f'{stem}{vol}/{nxt:03d}';nxt+=1
        refs[r['record_id']]=ref
    update_admin(i,{'apc_status':'2','apc_trigger_date':today,'apc_quarter':f'{fy} {q}','apc_github_run_id':os.getenv('GITHUB_RUN_ID',''),'apc_result_message':f'Claimed by GitHub; processing {fy} {q}. Date reset allowed: {reset_dates}.'})
    writes=[]
    letter_dates={}
    for rid,ref in refs.items():
        row={'record_id':rid,'approval_reference':ref}
        if reset_dates:
            row['approval_date']=today.isoformat()
            letter_dates[rid]=today.isoformat()
        else:
            existing=(next(r for r in sel if r['record_id']==rid).get('approval_date') or '').strip()
            if not existing:
                raise RuntimeError(f'record {rid}: approval_date is blank and selected quarter is outside the automatic date-reset window')
            letter_dates[rid]=existing
        writes.append(row)
    import_rows(writes)
    chk={r['record_id']:r for r in masters(export_records())}
    bad=[]
    for rid,ref in refs.items():
        if chk.get(rid,{}).get('approval_reference')!=ref: bad.append(rid)
        if reset_dates and chk.get(rid,{}).get('approval_date')!=today.isoformat(): bad.append(rid)
    if bad:raise RuntimeError('Post-write verification failed: '+','.join(sorted(set(bad))))
    vals=list(refs.values()); state={'instance':i,'trigger_date':today.isoformat(),'quarter':q,'fiscal_year':fy,'period_start':qs.isoformat(),'period_end':qe.isoformat(),'date_reset_allowed':reset_dates,'record_ids':list(refs),'references':refs,'letter_dates':letter_dates,'reference_range':f'{vals[0]} – {vals[-1]}','requested_by':req.get('apc_triggered_by','')}
    STATE.write_text(json.dumps(state,indent=2),encoding='utf-8'); print('has_request=true');print(f'instance={i}');print(f'selected={len(refs)}')

def letter_pdf(rec,lab,ref,dt,path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.enums import TA_CENTER,TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=22*mm,rightMargin=22*mm,topMargin=14*mm,bottomMargin=14*mm)
    st=getSampleStyleSheet(); b=ParagraphStyle('b',parent=st['Normal'],fontSize=9.5,leading=12.3,alignment=TA_JUSTIFY,spaceAfter=4); c=ParagraphStyle('c',parent=b,alignment=TA_CENTER,fontName='Helvetica-Bold',fontSize=10.4,leading=13); t=ParagraphStyle('t',parent=b,alignment=TA_CENTER,fontName='Helvetica-Bold',fontSize=10.2,leading=12.5,spaceBefore=5,spaceAfter=6); sm=ParagraphStyle('sm',parent=b,fontSize=7,leading=8)
    course=(lab.get('course_name') or rec.get('course_name') or '').strip(); director=(lab.get('course_director_id') or '').strip(); dept=(lab.get('course_department_code') or '').strip(); school=(lab.get('course_school_code') or '').strip(); code=(rec.get('course_code') or '').strip(); ds=datetime.strptime(dt,'%Y-%m-%d').strftime('%-m/%-d/%Y')
    story=[Paragraph('UNITED REPUBLIC OF TANZANIA',c),Paragraph('<font color="#315D8A">MINISTRY OF EDUCATION, SCIENCE AND TECHNOLOGY<br/>MUHIMBILI UNIVERSITY OF HEALTH AND ALLIED SCIENCES</font>',c),Paragraph('OFFICE OF THE DIRECTOR – CONTINUING EDUCATION<br/>AND PROFESSIONAL DEVELOPMENT',c),Spacer(1,1*mm)]
    bar=Table([['']],colWidths=[170*mm],rowHeights=[0.6*mm]);bar.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#1D4E89'))]));story+=[bar,Spacer(1,2*mm),Paragraph('In reply quote;',b)]
    rr=Table([[Paragraph(f'<b>Ref. No: {ref}</b>',b),Paragraph(f'<b>Date: {ds}</b>',b)]],colWidths=[115*mm,55*mm]);rr.setStyle(TableStyle([('ALIGN',(1,0),(1,0),'RIGHT'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]));story+=[rr,Spacer(1,2*mm),Paragraph(director,b),Paragraph(('Department of '+dept if dept and not dept.lower().startswith('department') else dept)+',',b),Paragraph(school+', MUHAS',b),Spacer(1,3*mm),Paragraph(f'RE: &nbsp; ACCREDITATION OF SHORT COURSE “{course.upper()}”',t)]
    story+=[Paragraph(f'I am pleased to inform you that the Chairperson of the Senate Continuing Education and Professional Development (SCEPD) accredited the short course, namely <b>“{course.upper()}”</b> after you successfully addressed the comments that you were given. The course code shall be <b>{code}</b>. With this letter, you can initiate procedures to advertise and conduct the accredited short course.',b),Paragraph('Please note that you will have to register for this short course with the Professional Council(s) so that they can give credit points to professionals who have successfully attended the accredited short course.',b),Paragraph('As the course Director, you are requested to ensure that you accomplish the following: -',b)]
    for n,x in enumerate(['Conduct the accredited short course at least once annually.','Liaise with DCEPD at least a week before conducting the short course (include course advertisement that will be posted on the MUHAS website, timetable, and course venue.','Submit, before the end of training, a list of course participants and liaise with the DCEPD administrator to prepare certificates for participants.','Submit the activity report within a week of conducting the short course.'],1):story.append(Paragraph(f'{n}.&nbsp;&nbsp;{x}',b))
    story+=[Paragraph('I wish you success in running the short course that has been accredited.',b),Spacer(1,8*mm),Paragraph('______________________________<br/><i>Authorized signature</i>',b),Spacer(1,3*mm),Paragraph('Cc. Deputy Vice-Chancellor- Academics, <b>MUHAS</b>',b)]
    if school:story.append(Paragraph(f"Cc. {'Dean' if 'School' in school else 'Director'}, {school}, <b>MUHAS</b>",b))
    if dept:story.append(Paragraph(f'Cc. HOD, Department of {dept}, <b>MUHAS</b>',b))
    story+=[Spacer(1,2*mm),Paragraph('9 United Nations Road; Upanga West; P.O. Box 65001, Dar Es Salaam; Tel. G/Line: +255-22-2150302/6; Ext. 1236; Direct Line:+255-22-2152635; Telefax:+255-22-2150465; E-mail: dvcarc@muhas.ac.tz; Web: https://www.muhas.ac.tz',sm)];doc.build(story)

def finalize():
    st=json.loads(STATE.read_text()); raw=export_records(); lab=export_records(True); rm={r['record_id']:r for r in masters(raw)};lm={r['record_id']:r for r in masters(lab)};errs=[]
    for rid in st['record_ids']:
        r=rm.get(rid,{})
        if not r.get('course_code'):errs.append(f'record {rid}: course_code blank')
        if r.get('approval_reference')!=st['references'][rid] or r.get('approval_date')!=st['letter_dates'][rid]:errs.append(f'record {rid}: verification mismatch')
    if errs:raise RuntimeError('; '.join(errs))
    letters=OUT/'letters';letters.mkdir(parents=True,exist_ok=True);reg=[]
    for rid in st['record_ids']:
        r=rm[rid];l=lm.get(rid,r);ref=st['references'][rid];fn=re.sub(r'[^A-Za-z0-9._-]+','_',ref.replace('/','-')+'_'+(l.get('course_name') or rid))[:120]+'.pdf';letter_pdf(r,l,ref,st['letter_dates'][rid],letters/fn);reg.append({'record_id':rid,'approval_reference':ref,'letter_date':st['letter_dates'][rid],'course_code':r.get('course_code',''),'course_name':l.get('course_name',''),'course_director':l.get('course_director_id',''),'file':fn})
    regp=OUT/'accreditation_register.csv'
    with regp.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=reg[0]);w.writeheader();w.writerows(reg)
    zp=OUT/f"DCEPD_Accreditation_Pack_{st['fiscal_year'].replace('/','-')}_{st['quarter']}_{st['trigger_date']}.zip"
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:z.write(regp,regp.name);[z.write(p,'letters/'+p.name) for p in letters.glob('*.pdf')]
    email_status='0';email_msg='Package available as GitHub artifact; email not configured.';rec=[]
    for k in ('DCEPD_EMAIL_1','DCEPD_EMAIL_2','DCEPD_EMAIL_3','DCEPD_EMAIL_4'):
        if os.getenv(k,'').strip():rec.append(os.getenv(k).strip())
    host=os.getenv('DCEPD_SMTP_HOST','').strip();user=os.getenv('DCEPD_SMTP_USERNAME','').strip();pwd=os.getenv('DCEPD_SMTP_PASSWORD','').strip();port=int(os.getenv('DCEPD_SMTP_PORT','587'))
    if host and user and pwd and rec:
        try:
            m=EmailMessage();m['Subject']=f"DCEPD accreditation batch {st['fiscal_year']} {st['quarter']}";m['From']=user;m['To']=', '.join(rec);m.set_content(f"Batch completed. Letters: {len(reg)}\nReference range: {st['reference_range']}\nDate: {st['trigger_date']}");m.add_attachment(zp.read_bytes(),maintype='application',subtype='zip',filename=zp.name)
            with smtplib.SMTP(host,port,timeout=60) as s:s.starttls(context=ssl.create_default_context());s.login(user,pwd);s.send_message(m)
            email_status='1';email_msg=f'Package emailed to {len(rec)} recipient(s).'
        except Exception as e:email_status='3';email_msg='Email failed: '+str(e)[:300]
    now=datetime.now(TZ);update_admin(st['instance'],{'apc_status':'3','apc_selected_records':', '.join(st['record_ids']),'apc_reference_range':st['reference_range'],'apc_letters_generated':len(reg),'apc_qc_errors':'0','apc_qc_warnings':'0','apc_email_status':email_status,'apc_completed_at':now.strftime('%Y-%m-%d %H:%M:%S'),'apc_result_message':f'Successful. Generated {len(reg)} draft accreditation letter(s). {email_msg}'})

def fail():
    if not STATE.exists():return
    st=json.loads(STATE.read_text());update_admin(st['instance'],{'apc_status':'4','apc_qc_errors':'1','apc_completed_at':datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S'),'apc_result_message':os.getenv('APC_FAILURE_REASON','GitHub accreditation workflow failed; inspect logs.')[:1000]})

if __name__=='__main__':
    phase=sys.argv[1] if len(sys.argv)>1 else 'claim'
    try:{'claim':claim,'finalize':finalize,'fail':fail}[phase]()
    except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
