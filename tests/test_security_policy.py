import unittest
from datetime import datetime, timedelta, timezone

from lmlm_security import Grant, PolicyDecision, PolicyEngine, SecurityRequest


class PolicyEngineTests(unittest.TestCase):
    def setUp(self):
        self.request = SecurityRequest("agent-a", "model.generate", "local:default", ("inference",))
        self.grant = Grant("policy-1", "agent-a", "model.generate", "local:default", frozenset({"inference"}))

    def test_explicit_exact_grant_allows(self):
        engine = PolicyEngine([self.grant])
        self.assertEqual(engine.authorize(self.request)[0], PolicyDecision.ALLOW)

    def test_missing_grant_denies(self):
        self.assertEqual(PolicyEngine().authorize(self.request)[0], PolicyDecision.DENY)

    def test_other_principal_does_not_inherit_grant(self):
        request = SecurityRequest("agent-b", "model.generate", "local:default", ("inference",))
        self.assertEqual(PolicyEngine([self.grant]).authorize(request)[0], PolicyDecision.DENY)

    def test_other_resource_does_not_inherit_grant(self):
        request = SecurityRequest("agent-a", "model.generate", "local:other", ("inference",))
        self.assertEqual(PolicyEngine([self.grant]).authorize(request)[0], PolicyDecision.DENY)

    def test_expired_grant_denies(self):
        expired = Grant("expired", "agent-a", "model.generate", "local:default",
                        frozenset({"inference"}), datetime.now(timezone.utc) - timedelta(seconds=1))
        self.assertEqual(PolicyEngine([expired]).authorize(self.request)[0], PolicyDecision.DENY)

    def test_revoked_grant_denies(self):
        engine = PolicyEngine([self.grant])
        engine.revoke("policy-1")
        self.assertEqual(engine.authorize(self.request)[0], PolicyDecision.DENY)

    def test_capability_escalation_denies(self):
        request = SecurityRequest("agent-a", "model.generate", "local:default",
                                  ("inference", "filesystem.write"))
        self.assertEqual(PolicyEngine([self.grant]).authorize(request)[0], PolicyDecision.DENY)

    def test_wildcard_scope_does_not_match(self):
        wildcard = Grant("wild", "agent-a", "model.generate", "*", frozenset({"inference"}))
        self.assertEqual(PolicyEngine([wildcard]).authorize(self.request)[0], PolicyDecision.DENY)


if __name__ == "__main__":
    unittest.main()
