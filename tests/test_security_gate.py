import unittest

from lmlm_security import Grant, PolicyDecision, PolicyEngine, Principal, SecurityGate


VALID = {
    "operation": "model.generate",
    "provider": "local",
    "model": "default",
    "input": {"type": "text", "source": "user_input"},
    "permissions": ["inference"],
    "verification": {"required": True},
}


class SecurityGateTests(unittest.TestCase):
    def test_valid_ir_still_denied_without_policy_grant(self):
        result = SecurityGate(PolicyEngine()).authorize_ir(Principal("agent-a"), VALID)
        self.assertEqual(result.decision, PolicyDecision.DENY)
        self.assertEqual(result.reason, "no_matching_active_grant")

    def test_valid_ir_allowed_with_exact_grant(self):
        grant = Grant("p-1", "agent-a", "model.generate", "local:default", frozenset({"inference"}))
        result = SecurityGate(PolicyEngine([grant])).authorize_ir(Principal("agent-a"), VALID)
        self.assertTrue(result.allowed)
        self.assertEqual(result.policy_id, "p-1")
        self.assertEqual(result.normalized_ir, VALID)

    def test_inactive_principal_denied(self):
        result = SecurityGate(PolicyEngine()).authorize_ir(Principal("agent-a", False), VALID)
        self.assertEqual(result.reason, "inactive_or_invalid_principal")

    def test_invalid_ir_denied_before_policy(self):
        result = SecurityGate(PolicyEngine()).authorize_ir(
            Principal("agent-a"), {**VALID, "operation": "python.exec"}
        )
        self.assertEqual(result.decision, PolicyDecision.DENY)
        self.assertTrue(result.reason.startswith("invalid_ir:"))


if __name__ == "__main__":
    unittest.main()
