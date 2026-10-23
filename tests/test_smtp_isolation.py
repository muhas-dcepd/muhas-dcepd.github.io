"""Offline tests: no network connections or emails are made."""
import importlib.util
import os
import pathlib
import unittest
from unittest.mock import patch, MagicMock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "test_dcepd_smtp.py"
spec = importlib.util.spec_from_file_location("dcepd_smtp_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class SMTPIsolationTests(unittest.TestCase):
    def test_missing_credentials_fail_before_connection(self):
        with patch.dict(os.environ, {"DCEPD_SMTP_HOST": "", "DCEPD_SMTP_USERNAME": "", "DCEPD_SMTP_PASSWORD": ""}):
            with patch.object(probe.smtplib, "SMTP_SSL") as ssl_smtp:
                with self.assertRaisesRegex(RuntimeError, "incomplete"):
                    probe.main()
                ssl_smtp.assert_not_called()

    def test_test_mail_has_one_recipient_and_no_attachment(self):
        captured = []
        connection = MagicMock()
        connection.__enter__.return_value.send_message.side_effect = lambda msg: captured.append(msg)
        with patch.dict(os.environ, {"DCEPD_SMTP_HOST": "smtp.example.test", "DCEPD_SMTP_PORT": "465", "DCEPD_SMTP_USERNAME": "sender@example.test", "DCEPD_SMTP_PASSWORD": "dummy"}):
            with patch.object(probe.smtplib, "SMTP_SSL", return_value=connection):
                probe.main()
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["To"], "sangeda@gmail.com")
        self.assertIsNone(captured[0]["Cc"])
        self.assertEqual(len(list(captured[0].iter_attachments())), 0)
        self.assertIn("[TEST]", captured[0]["Subject"])

    def test_rejects_unapproved_port(self):
        with patch.dict(os.environ, {"DCEPD_SMTP_HOST": "smtp.example.test", "DCEPD_SMTP_PORT": "25", "DCEPD_SMTP_USERNAME": "sender@example.test", "DCEPD_SMTP_PASSWORD": "dummy"}):
            with patch.object(probe.smtplib, "SMTP") as smtp:
                with self.assertRaisesRegex(RuntimeError, "465 or 587"):
                    probe.main()
                smtp.assert_not_called()

if __name__ == "__main__":
    unittest.main()
