"""IR-to-policy preflight seam; intentionally does not execute the request."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from lmlm_ir import IRValidationError, validate_ir

from .policy import PolicyEngine
from .types import PolicyDecision, Principal, SecurityRequest


@dataclass(frozen=True)
class AuthorizationResult:
    decision: PolicyDecision
    reason: str
    policy_id: str | None = None
    normalized_ir: dict[str, Any] | None = None

    @property
    def allowed(self) -> bool:
        return self.decision is PolicyDecision.ALLOW


class SecurityGate:
    """Validate IR, then require an independent explicit policy grant."""

    def __init__(self, policy: PolicyEngine) -> None:
        self._policy = policy

    def authorize_ir(
        self,
        principal: Principal,
        document: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> AuthorizationResult:
        if not principal.active or not principal.principal_id:
            return AuthorizationResult(PolicyDecision.DENY, "inactive_or_invalid_principal")
        try:
            normalized = validate_ir(document)
        except (IRValidationError, TypeError, KeyError) as exc:
            return AuthorizationResult(
                PolicyDecision.DENY, f"invalid_ir:{type(exc).__name__}"
            )

        request = SecurityRequest(
            principal_id=principal.principal_id,
            action=normalized["operation"],
            resource=f'{normalized["provider"]}:{normalized["model"]}',
            capabilities=tuple(normalized["permissions"]),
        )
        decision, reason, policy_id = self._policy.authorize(request, now=now)
        return AuthorizationResult(decision, reason, policy_id, normalized)
