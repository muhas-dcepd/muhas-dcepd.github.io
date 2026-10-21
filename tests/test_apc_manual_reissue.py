import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "process_accreditation_batch.py"
spec = importlib.util.spec_from_file_location("apc", SCRIPT)
apc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apc)


def fixture():
    admin = {
        "record_id": "1", "redcap_repeat_instrument": apc.ADMIN,
        "redcap_repeat_instance": "6", "apc_action_type": "2",
        "apc_trigger_requested": "1", "apc_trigger_warning_ack": "1",
        "apc_status": "4", "apc_trigger_date": "2026-10-21",
        "apc_process_fiscal_year": "FY2026_27", "apc_process_quarter": "1"
    }
    rows = [admin]
    for i in range(12):
        rows.append({
            "record_id": str(180 + i), "accreditation_date": "2026-09-15",
            "course_director_id": "D", "course_department_code": "DEP",
            "course_school_code": "SCH",
            "approval_reference": f"KB 328/364/25/{i+40:03d}" if i < 5 else "",
            "approval_date": "2026-10-01" if i < 5 else ""
        })
    return rows


class APCTest(unittest.TestCase):
    def run_claim(self, rows):
        writes = []
        def fake_import(new):
            writes.extend(new)
            for update in new:
                if update.get("redcap_repeat_instrument"):
                    continue
                target = next(x for x in rows if x["record_id"] == update["record_id"])
                target.update(update)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(apc, "OUT", Path(directory)), \
                 patch.object(apc, "STATE", Path(directory) / "state.json"), \
                 patch.object(apc, "export_records", side_effect=lambda: rows), \
                 patch.object(apc, "import_rows", side_effect=fake_import), \
                 patch.dict(os.environ, {"APC_RESUME_INSTANCE": "6"}):
                apc.claim()
                snapshot = list(Path(directory).glob("*prewrite.json"))
                snapshot_text = snapshot[0].read_text() if snapshot else ""
                return writes, snapshot_text

    def test_reissue_twelve_and_snapshot(self):
        rows = fixture()
        writes, snapshot = self.run_claim(rows)
        courses = [x for x in writes if x.get("approval_reference")]
        self.assertEqual(len(courses), 12)
        refs = [x["approval_reference"] for x in courses]
        self.assertEqual(len(set(refs)), 12)
        self.assertTrue(all(x["approval_date"] == "2026-10-21" for x in courses))
        self.assertTrue(all(int(x["approval_reference"].rsplit("/", 1)[-1]) > 44 for x in courses))
        self.assertIn("KB 328/364/25/040", snapshot)
        self.assertIn('"record_id": "180"', snapshot)

    def test_resume_blocks_existing_trigger_date(self):
        rows = fixture()
        rows[1]["approval_date"] = "2026-10-21"
        with self.assertRaisesRegex(RuntimeError, "manual reconciliation"):
            self.run_claim(rows)


if __name__ == "__main__":
    unittest.main()
