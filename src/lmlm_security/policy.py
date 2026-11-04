"""Deny-by-default policy evaluation with exact principal and resource scopes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .types import Grant, PolicyDecision, SecurityRequest


class PolicyEngine:
    """Evaluate requests against explicit grants; never infer permissions."""

    def __init__(self, grants: Iterable[Grant] = ()) -> None:
        self._grants = tuple(grants)
        self._revoked: set[str] = set()

    def revoke(self, policy_id: str) -> None:
        if not policy_id:
            raise ValueError("policy_id must not be empty")
        self._revoked.add(policy_id)

    def authorize(
        self, request: SecurityRequest, *, now: datetime | None = None
    ) -> tuple[PolicyDecision, str, str | None]:
        if not request.principal_id or not request.action or not request.resource:
            return PolicyDecision.DENY, "invalid_request_scope", None
        if not request.capabilities or any(not item for item in request.capabilities):
            return PolicyDecision.DENY, "missing_or_invalid_capabilities", None

        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            return PolicyDecision.DENY, "clock_must_be_timezone_aware", None

        candidates = (
            grant for grant in self._grants
            if grant.principal_id == request.principal_id
            and grant.action == request.action
            and grant.resource == request.resource
        )
        for grant in candidates:
            if grant.policy_id in self._revoked:
                continue
            if grant.expires_at is not None:
                if grant.expires_at.tzinfo is None or grant.expires_at <= current:
                    continue
            if set(request.capabilities).issubset(grant.capabilities):
                return PolicyDecision.ALLOW, "explicit_grant", grant.policy_id

        return PolicyDecision.DENY, "no_matching_active_grant", None
