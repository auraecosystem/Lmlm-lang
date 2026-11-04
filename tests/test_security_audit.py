import json
import tempfile
import unittest
from pathlib import Path

from lmlm_security import AuditLog


class AuditLogTests(unittest.TestCase):
    def test_writes_jsonl_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit" / "events.jsonl"
            AuditLog(path).write({
                "event_type": "execution_denied",
                "principal_id": "agent-a",
                "decision": "deny",
                "reason": "no_matching_active_grant",
            })
            record = json.loads(path.read_text().strip())
            self.assertEqual(record["event_type"], "execution_denied")
            self.assertIn("timestamp", record)

    def test_rejects_unapproved_fields_to_prevent_secret_logging(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                AuditLog(Path(directory) / "events.jsonl").write({
                    "event_type": "test", "api_key": "must-not-be-logged"
                })

    def test_requires_event_type(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                AuditLog(Path(directory) / "events.jsonl").write({"decision": "deny"})


if __name__ == "__main__":
    unittest.main()
