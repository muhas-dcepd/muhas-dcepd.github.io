"""Allowlist public files; no private records, management output or secrets."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
stage=ROOT/'_site'
if stage.exists():shutil.rmtree(stage)
stage.mkdir()
for name in ['dcepd-courses','dcepd-dashboard']:shutil.copytree(ROOT/name,stage/name)
for name in ['index.html','robots.txt','sitemap.xml','.nojekyll']:shutil.copy2(ROOT/name,stage/name)
# Preserve Search Console verification files exactly as uploaded.
for file in ROOT.glob('google*.html'):
    if file.is_file():
        shutil.copy2(file, stage/file.name)
print('Staged standalone public DCEPD site.')
