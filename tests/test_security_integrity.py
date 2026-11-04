import hashlib
import tempfile
import unittest
from pathlib import Path

from lmlm_security import sha256_file


class IntegrityTests(unittest.TestCase):
    def test_hashes_file_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.bin"
            path.write_bytes(b"LMLM integrity fixture")
            before = path.read_bytes()
            result = sha256_file(path, chunk_size=3)
            self.assertEqual(result.sha256, hashlib.sha256(before).hexdigest())
            self.assertEqual(result.size_bytes, len(before))
            self.assertEqual(path.read_bytes(), before)

    def test_rejects_invalid_chunk_size(self):
        with self.assertRaises(ValueError):
            sha256_file(__file__, chunk_size=0)


if __name__ == "__main__":
    unittest.main()
