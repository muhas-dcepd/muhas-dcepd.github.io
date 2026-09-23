"""Standalone DCEPD search metadata, applied after each refresh."""
import html,json,re
from pathlib import Path
from build_dcepd_course_pages import build as build_course_pages
ROOT=Path(__file__).resolve().parents[1]
BASE='https://muhas-dcepd.github.io/'
PAGES={'index.html':('','MUHAS DCEPD | Continuing Education and Professional Development','Explore MUHAS short courses, apply through the official application system, and view continuing education activity and applicant reach.'),'dcepd-courses/index.html':('dcepd-courses/','MUHAS DCEPD Short Courses | Search and Apply','Search MUHAS short courses by subject, keyword and organising school. View course details, historical records and the official application gateway.'),'dcepd-dashboard/index.html':('dcepd-dashboard/','MUHAS DCEPD Dashboard | Delivery, Attendance and Applications','Explore MUHAS short-course delivery, recorded attendance, application demand and applicant geography by reporting period, school and course.')}
def optimise_site():
 course_urls=build_course_pages()
 for file,(route,title,description) in PAGES.items():
  p=ROOT/file
  if not p.exists():continue
  s=p.read_text();s=re.sub(r'<!-- SEO START -->.*?<!-- SEO END -->','',s,flags=re.S);s=re.sub(r'<title>.*?</title>','',s,flags=re.S)
  s=re.sub(r'<meta\b(?=[^>]*(?:name|property)=[\"\'](?:description|robots|og:[^\"\']+|twitter:[^\"\']+)[\"\'])[^>]*>','',s,flags=re.I)
  s=re.sub(r'<link\b(?=[^>]*rel=[\"\']canonical[\"\'])[^>]*>','',s,flags=re.I)
  org={'@type':'Organization','@id':BASE+'#dcepd','name':'MUHAS Directorate of Continuing Education and Professional Development','url':BASE,'parentOrganization':{'@type':'CollegeOrUniversity','name':'Muhimbili University of Health and Allied Sciences','url':'https://muhas.ac.tz/'}}
  page={'@type':'WebPage' if not route else 'CollectionPage','url':BASE+route,'name':title,'description':description,'publisher':{'@id':BASE+'#dcepd'}}
  if route=='dcepd-courses/':
   courses=json.loads((ROOT/'dcepd-courses/catalogue.json').read_text())['courses'];page['mainEntity']={'@type':'ItemList','numberOfItems':len(courses),'itemListElement':[{'@type':'ListItem','position':i+1,'item':{'@type':'Course','name':c['title'],'courseCode':c['code'],'url':BASE+route+'courses/'+c['id']+'.html','provider':{'@id':BASE+'#dcepd'}}} for i,c in enumerate(courses)]}
  tags=f'<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description,quote=True)}"><link rel="canonical" href="{BASE+route}"><meta name="robots" content="index,follow">'
  for key,value in [('og:title',title),('og:description',description),('og:url',BASE+route),('og:type','website'),('og:site_name','MUHAS DCEPD')]:tags+=f'<meta property="{key}" content="{html.escape(value,quote=True)}">'
  tags+='<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':[org,page]},ensure_ascii=False).replace('<','\\u003c')+'</script>'
  s=s.replace('</head>','<!-- SEO START -->'+tags+'<!-- SEO END --></head>');s=re.sub(r'<!-- SITE-DIRECTORY START -->.*?<!-- SITE-DIRECTORY END -->','',s,flags=re.S)
  nav='<nav aria-label="DCEPD pages" style="padding:24px;display:flex;gap:24px;flex-wrap:wrap"><a href="/">DCEPD home</a><a href="/dcepd-courses/">Courses</a><a href="/dcepd-dashboard/">Dashboard</a></nav>'
  p.write_text(s.replace('</body>','<!-- SITE-DIRECTORY START -->'+nav+'<!-- SITE-DIRECTORY END --></body>'))
 (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+BASE+r+'</loc></url>' for r,_,_ in PAGES.values())+''.join('<url><loc>'+u+'</loc></url>' for u in course_urls)+'</urlset>')
 (ROOT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'sitemap.xml\n')
if __name__=='__main__':optimise_site()
