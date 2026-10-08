import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalogue', ROOT/'scripts/update_dcepd_catalogue.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CatalogueTests(unittest.TestCase):
    def row(self, rid='1', listed='Yes', repeat=''):
        return dict.fromkeys(m.FIELDS, '') | {'record_id': rid, 'course_name': 'Example <course>',
            'public_catalogue': listed, 'redcap_repeat_instrument': repeat,
            'private_email': 'PRIVATE_SENTINEL', 'dormant_flag': 'Dormant', 'course_status': 'Under review'}

    def build(self, rows):
        return m.build(rows, 'test', '2026-09-19', {'courses': {}, 'keyword_rules': []})

    def test_exact_inclusion_and_no_extra_eligibility_rules(self):
        result = self.build([self.row(), self.row('2', 'No'), self.row('3', ''), self.row('1', 'Yes', 'course_run_log')])
        self.assertEqual([c['id'] for c in result['courses']], ['1'])
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))

    def test_duplicate_ids_fail(self):
        with self.assertRaises(ValueError): self.build([self.row(), self.row()])

    def test_empty_is_valid_after_successful_export(self):
        self.assertEqual(self.build([])['count'], 0)

    def test_html_escaping_and_official_link(self):
        card = m.render_card(self.build([self.row()])['courses'][0])
        self.assertIn('&lt;course&gt;', card)
        self.assertNotIn('<course>', card)
        self.assertIn('Apply not open', card)

    def test_metadata_verifies_yes_code(self):
        metadata = [{'field_name': name, 'field_type': 'text'} for name in m.FIELDS]
        next(x for x in metadata if x['field_name'] == 'public_catalogue').update(
            field_type='radio', select_choices_or_calculations='7, Yes | 8, No')
        with patch.dict('os.environ', {'REDCAP_PROJECT75_TOKEN': 'test-only'}), patch.object(m, 'api_export', side_effect=[metadata, [], []]) as api:
            self.assertEqual(m.fetch_records(), [])
            args = api.call_args.args[2]
            self.assertEqual(args['filterLogic'], "[public_catalogue] = '7'")
            self.assertNotIn('private_email', str(args))

    def test_secondary_subject_matching(self):
        row = self.row()
        row['course_name'] = 'Applications of artificial intelligence in healthcare'
        course = self.build([row])['courses'][0]
        self.assertIn('Digital Health, Data Science & Informatics', m.subject_categories(course))

    def test_date_display_dmy(self):
        self.assertEqual(m.display_date_dmy('2026-10-30'), '30-10-2026')
        self.assertEqual(m.display_date_dmy('30-10-2026'), '30-10-2026')
        self.assertEqual(m.display_date_dmy(''), '')

    def test_open_run_builds_prefilled_application_link(self):
        master = self.row()
        master.update(course_requires_cv='Yes', course_requires_certificate='No')
        run = self.row('1', 'Yes', 'course_run_log')
        run.update(redcap_repeat_instance='2', run_start_date='20-10-2026',
                   run_application_open_date='2026-10-01', run_application_close_date='2026-10-19',
                   run_status='Open for applications')
        data = m.build([master, run], 'test', '2026-10-08', {'courses': {}, 'keyword_rules': []},
                       choice_by_course={'1':'77'})
        course = data['courses'][0]
        self.assertEqual(course['date_next_offered'], '20-10-2026')
        self.assertEqual(course['open_runs'][0]['run_id'], '1-2')
        self.assertIn('applied_course_id=77', course['open_runs'][0]['apply_url'])
        self.assertIn('applied_run_id=1-2', course['open_runs'][0]['apply_url'])
        self.assertIn('course_requires_cv=1', course['open_runs'][0]['apply_url'])

    def test_future_run_not_open_has_no_apply_link(self):
        master = self.row()
        run = self.row('1', 'Yes', 'course_run_log')
        run.update(redcap_repeat_instance='1', run_start_date='20-10-2026', run_status='Draft')
        course = m.build([master, run], 'test', '2026-10-08', {'courses': {}, 'keyword_rules': []},
                         choice_by_course={'1':'77'})['courses'][0]
        self.assertEqual(course['date_next_offered'], '20-10-2026')
        self.assertEqual(course['open_runs'], [])
        self.assertEqual(course['apply_url'], '')

    def test_published_schema(self):
        data = json.loads((ROOT/'dcepd-courses/catalogue.json').read_text())
        self.assertEqual(data['count'], len(data['courses']))
        self.assertEqual(len({c['id'] for c in data['courses']}), data['count'])
        allowed = {'id','title','source_title','code','school','department','fee_tzs','cpd_points','summary','duration','delivery_mode','target_audience','learning_outcomes','certificate_awarded','date_next_offered','category','tags','open_runs','apply_url'}
        for course in data['courses']:
            self.assertEqual(set(course), allowed)
            self.assertTrue(course['apply_url'] == '' or course['apply_url'].startswith(m.APPLY_URL))

if __name__ == '__main__': unittest.main()
