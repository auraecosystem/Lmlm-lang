import tempfile
import unittest
from pathlib import Path

from lmlm_security import IOCSet


class ThreatIntelTests(unittest.TestCase):
    def setUp(self):
        self.iocs = IOCSet.from_mapping({
            "sha256": ["cc0ad05bfe85940a6067b3a72c182d3953339129206634141926d5d0b35973ec"],
            "binary_prefixes_hex": ["1b4c4a01"],
            "domains": ["insightjs.com"],
            "ips": ["89.127.233.127"],
            "paths": ["launcher\\log\\tinyget"],
            "text_markers": ["k2f.agent.state"],
        })

    def test_binary_prefix_match(self):
        matches = self.iocs.scan_bytes(bytes.fromhex("1b4c4a01") + b"fixture")
        self.assertTrue(any(item.indicator_type == "binary_prefix" for item in matches))

    def test_domain_ip_and_marker_match_offline(self):
        matches = self.iocs.scan_text("contact insightjs.com; 89.127.233.127; k2f.agent.state")
        self.assertEqual({item.indicator_type for item in matches}, {"domain", "ip", "text_marker"})

    def test_path_match(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Launcher" / "log" / "tinyget" / "sample.bin"
            path.parent.mkdir(parents=True)
            path.write_bytes(bytes.fromhex("1b4c4a01") + b"data")
            matches = self.iocs.scan_path(path)
            self.assertTrue(any(item.indicator_type == "path" for item in matches))
            self.assertTrue(any(item.indicator_type == "binary_prefix" for item in matches))

    def test_rejects_invalid_hash_indicator(self):
        with self.assertRaises(ValueError):
            IOCSet.from_mapping({"sha256": ["not-a-hash"]})


if __name__ == "__main__":
    unittest.main()
