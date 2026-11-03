"""Reciprocal institutional navigation, without unrelated cross-linking."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
OSP="https://muhas-osp.github.io/"
PROFILE="https://sangeda.github.io/"

class ReciprocalLinksTests(unittest.TestCase):
    def test_dcepd_homepage_has_osp_and_lower_profile(self):
        s=(ROOT/"index.html").read_text(encoding="utf-8")
        header=s.split("<header",1)[1].split("</header>",1)[0]
        footer=s.split("<footer",1)[1].split("</footer>",1)[0]
        self.assertIn(OSP,header)
        self.assertNotIn(PROFILE,header)
        self.assertIn(PROFILE,footer)
        self.assertIn(OSP,footer)

    def test_course_template_and_lower_related_directory(self):
        c=(ROOT/"scripts/dcepd_catalogue_template.html").read_text(encoding="utf-8")
        seo=(ROOT/"scripts/build_site_seo.py").read_text(encoding="utf-8")
        self.assertIn(OSP+"opportunities/",c)
        self.assertNotIn(PROFILE,c.split("</header>",1)[0])
        self.assertIn(OSP+"opportunities/",seo)
        self.assertIn(PROFILE,seo)
        for text in (c,seo):
            self.assertNotIn("sangeda.github.io/bpharm-projects",text)
            self.assertNotIn("sangeda.github.io/muhas-publications",text)

if __name__=="__main__":
    unittest.main()
