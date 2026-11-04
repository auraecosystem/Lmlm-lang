import json
import tempfile
import unittest
from pathlib import Path

from lmlm_lslc.runner import load_ioc_set, run_security_self_test


FIXTURE = Path(__file__).parents[1] / "fixtures" / "threatintel" / "nikke-k2f.json"


class LSLCTests(unittest.TestCase):
    def test_existing_offline_fixture_loads(self):
        iocs = load_ioc_set(FIXTURE)
        self.assertTrue(iocs.sha256)
        self.assertIn("insightjs.com", iocs.domains)

    def test_fixture_rejects_network_enabled_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "iocs.json"
            path.write_text(json.dumps({
                "status": "unverified_indicators",
                "handling": "network_lookup",
                "sha256": [],
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_ioc_set(path)

    def test_self_test_passes_without_network_or_execution(self):
        report = run_security_self_test(FIXTURE)
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.checks["network_access"], "not_used")
        self.assertEqual(report.checks["execution_of_scanned_content"], "not_performed")


if __name__ == "__main__":
    unittest.main()
