"""Offline tests for the draft Course Director applicant view; no REDCap or SMTP calls."""
import importlib.util
import io
import os
import zipfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from openpyxl import load_workbook

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "process_project79_applicant_packs.py"
with patch.dict(os.environ, {"REDCAP_PROJECT75_TOKEN": "offline", "REDCAP_PROJECT79_TOKEN": "offline"}):
    spec = importlib.util.spec_from_file_location("applicant_pack", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


class ApplicantPackPilotTests(unittest.TestCase):
    def test_hidden_other_education_is_not_exported(self):
        applicants = [{"record_id": "1", "applied_run_id": "206-1", "highest_education": "3"}]
        self.assertNotIn("other_education", module.director_columns(applicants))

    def test_conditional_field_visible_for_any_eligible_applicant(self):
        applicants = [
            {"record_id": "1", "applied_run_id": "206-1", "highest_education": "3"},
            {"record_id": "2", "applied_run_id": "206-1", "highest_education": "99", "other_education": "Clinical qualification"},
        ]
        self.assertIn("other_education", module.director_columns(applicants))
        workbook = load_workbook(io.BytesIO(module.build_workbook({}, applicants)))
        sheet = workbook["All Applicants"]
        headings = [c.value for c in sheet[1]]
        col = headings.index("other_education") + 1
        self.assertEqual(sheet.cell(2, col).value, None)
        self.assertEqual(sheet.cell(3, col).value, "Clinical qualification")

    def test_uploads_only_when_requested_and_present(self):
        applicant = {
            "applied_run_id": "206-1", "course_requires_cv": "1",
            "course_requires_certificate": "0", "upload_cv": "123",
            "upload_certificate": "456", "upload_support_letter": "",
        }
        self.assertEqual(module.applicable_upload_fields(applicant), ["upload_cv"])
        applicant["course_requires_cv"] = "0"
        self.assertEqual(module.applicable_upload_fields(applicant), [])
        applicant["upload_support_letter"] = "789"
        self.assertEqual(module.applicable_upload_fields(applicant), ["upload_support_letter"])

    def test_file_export_is_read_only_and_sanitizes_filename(self):
        response = Mock()
        response.content = b"%PDF-synthetic-test-data"
        response.headers = {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="../../unsafe.pdf"',
        }
        response.raise_for_status.return_value = None
        with patch.object(module.requests, "post", return_value=response) as post:
            content, name = module.fetch_private_upload("123", "upload_cv")
        self.assertEqual(content, b"%PDF-synthetic-test-data")
        self.assertNotIn("/", name)
        self.assertEqual(post.call_args.kwargs["data"]["action"], "export")
        self.assertEqual(post.call_args.kwargs["data"]["content"], "file")
        with self.assertRaises(ValueError):
            module.fetch_private_upload("123", "certificate_file")

    def test_file_export_rejects_json_error_payload(self):
        response = Mock()
        response.content = b'{"error":"file not found"}'
        response.headers = {"Content-Type": "application/json"}
        response.raise_for_status.return_value = None
        with patch.object(module.requests, "post", return_value=response):
            with self.assertRaises(RuntimeError):
                module.fetch_private_upload("123", "upload_cv")

    def test_reconciliation_separates_incomplete_and_missing_cv(self):
        rows = [
            {"record_id": "1", "applied_run_id": "206-1",
             "short_course_application_complete": "2",
             "course_requires_cv": "1", "upload_cv": ""},
            {"record_id": "2", "applied_run_id": "206-1",
             "short_course_application_complete": "0"},
            {"record_id": "3", "applied_run_id": "206-2",
             "short_course_application_complete": "2"},
        ]
        eligible, issues = module.reconcile_final_run(
            {"record_id": "206"}, "206-1", rows, {"206-1"})
        self.assertEqual([r["record_id"] for r in eligible], ["1"])
        self.assertEqual(len(issues), 2)
        self.assertTrue(any("upload_cv" in i["issue"] for i in issues))
        with self.assertRaises(ValueError):
            module.reconcile_final_run({"record_id": "206"}, "206-1", rows, set())

    def test_private_zip_requires_one_run(self):
        applicants = [{"record_id": "1", "applied_run_id": "206-1"},
                      {"record_id": "2", "applied_run_id": "206-2"}]
        with self.assertRaises(ValueError):
            module.build_private_run_zip({"record_id": "206"}, "206-1", applicants)
        with self.assertRaises(ValueError):
            module.build_private_run_zip({}, "206-1", [])

    def test_private_zip_rejects_course_run_mismatch(self):
        applicants = [{"record_id": "1", "applied_run_id": "206-1"}]
        with self.assertRaises(ValueError):
            module.build_private_run_zip({"record_id": "205"}, "206-1", applicants)

    def test_private_zip_contains_only_workbook_without_opt_in(self):
        applicants = [{"record_id": "1", "applied_run_id": "206-1",
                       "course_requires_cv": "1", "upload_cv": "123"}]
        with patch.object(module, "fetch_private_upload") as fetch:
            payload = module.build_private_run_zip({"record_id": "206"}, "206-1", applicants)
            fetch.assert_not_called()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(archive.namelist(), ["Applicant_Selection.xlsx"])

    def test_private_zip_includes_only_eligible_uploads_when_requested(self):
        applicants = [{"record_id": "1", "applied_run_id": "206-1",
                       "course_requires_cv": "1", "upload_cv": "123",
                       "course_requires_certificate": "0", "upload_certificate": "456"}]
        with patch.object(module, "fetch_private_upload", return_value=(b"synthetic", "cv.pdf")) as fetch:
            payload = module.build_private_run_zip({"record_id": "206"}, "206-1", applicants, include_documents=True)
            fetch.assert_called_once_with("1", "upload_cv")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(archive.namelist(),
                             ["Applicant_Selection.xlsx", "Documents/1/upload_cv_cv.pdf"])

    def test_applicant_text_cannot_become_excel_formula(self):
        applicant = {"record_id": "1", "applied_run_id": "206-1",
                     "full_name": "=HYPERLINK(\\\"https://example.invalid\\\")",
                     "why_apply": "+1+1"}
        workbook = load_workbook(io.BytesIO(module.build_workbook({}, [applicant])))
        all_sheet = workbook["All Applicants"]
        headers = [cell.value for cell in all_sheet[1]]
        for field in ("full_name", "why_apply"):
            cell = all_sheet.cell(2, headers.index(field) + 1)
            self.assertEqual(cell.data_type, "s")
            self.assertTrue(cell.value.startswith("'"))
        self.assertEqual(workbook["Selection Return"]["B2"].data_type, "s")

    def test_choice_labels_and_return_headers_unchanged(self):
        applicants = [{"record_id": "1", "applied_run_id": "206-1", "sex": "2", "full_name": "Pilot Applicant"}]
        workbook = load_workbook(io.BytesIO(module.build_workbook({}, applicants, {"sex": {"2": "Female"}})))
        sheet = workbook["All Applicants"]
        headings = [c.value for c in sheet[1]]
        self.assertEqual(sheet.cell(2, headings.index("sex") + 1).value, "Female")
        self.assertEqual([c.value for c in workbook["Selection Return"][1]],
                         ["record_id", "full_name", "selected_for_batch", "selected_batch_id",
                          "batch_role", "selection_date", "selection_by"])
        self.assertEqual([c.value for c in workbook["Cert-Graduands Return"][1]],
                         ["record_id", "full_name", "gepg_control_no", "attendance_verified",
                          "attendance_verified_date", "certificate_approved", "certification_notes"])


if __name__ == "__main__":
    unittest.main()
