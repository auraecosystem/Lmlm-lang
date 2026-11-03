import unittest

from lmlm_ir import IRValidationError, validate_ir


VALID = {
    "operation": "model.generate",
    "provider": "local",
    "model": "default",
    "input": {"type": "text", "source": "user_input"},
    "permissions": ["inference"],
    "verification": {"required": True},
}


class IRValidatorTests(unittest.TestCase):
    def test_valid_ir(self):
        self.assertEqual(validate_ir(VALID), VALID)

    def test_rejects_unknown_fields(self):
        with self.assertRaises(IRValidationError):
            validate_ir({**VALID, "shell": True})

    def test_rejects_unknown_operation(self):
        with self.assertRaises(IRValidationError):
            validate_ir({**VALID, "operation": "python.exec"})

    def test_rejects_unknown_provider(self):
        with self.assertRaises(IRValidationError):
            validate_ir({**VALID, "provider": "remote-untrusted"})

    def test_rejects_unapproved_capability(self):
        with self.assertRaises(IRValidationError):
            validate_ir({**VALID, "permissions": ["inference", "filesystem"]})

    def test_rejects_duplicate_permissions(self):
        with self.assertRaises(IRValidationError):
            validate_ir({**VALID, "permissions": ["inference", "inference"]})

    def test_rejects_invalid_verification_type(self):
        with self.assertRaises(IRValidationError):
            validate_ir({**VALID, "verification": {"required": "yes"}})


if __name__ == "__main__":
    unittest.main()
