# MUHAS DCEPD website

Public site: https://muhas-dcepd.github.io/

- `/dcepd-courses/`: Public Catalogue = Yes registry courses and official application gateway.
- `/dcepd-dashboard/`: Project 75 Run aggregates, Project 79 application summaries, applicant map and CSV exports.
- Historical workbook: dated snapshot under `dcepd-courses/downloads/`.

## Operation

Workflow `Refresh and deploy MUHAS DCEPD` runs daily at 01:37 UTC (04:37 EAT), on pushes and manually. Scheduler timing is approximate. Both repository secrets are required: `REDCAP_PROJECT75_TOKEN` and `REDCAP_PROJECT79_TOKEN`. Never put token values in files or logs. In Settings → Pages set Source to GitHub Actions. Failed exports stop publication; the last successful deployment remains live.

The dashboard is read-only. No identities, contact fields, finances, or private management data are exported. Private management hosting is a separate workstream. Courses, sessions, attendance, applications and completion are distinct. Missing attendance remains unknown. Historical courses contribute to activity irrespective of catalogue inclusion. The applicant map is deliberately independent of dashboard filters.

The public seed files were copied from the previously deployed sangeda.github.io DCEPD pages; their original source timestamps are retained until the first successful API refresh. No OpenAlex dependencies exist here. Old personal-site pages are retained during transition.

The organisation must administer its own GitHub members, API access and credentials. Submit `https://muhas-dcepd.github.io/sitemap.xml` in Search Console when ready.

## Development

Python 3.12 standard library is sufficient for daily refresh. Run `python -m unittest discover -s tests -p 'test_dcepd*.py'`. The one-off boundary conversion additionally uses pyshp, shapely and pyproj; the validated GeoJSON is already committed. Scripts stage an explicit public-file allowlist only.
