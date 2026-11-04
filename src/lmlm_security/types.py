"""Typed, immutable inputs and decisions for LMLM policy evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"


@dataclass(frozen=True)
class Principal:
    principal_id: str
    active: bool = True


@dataclass(frozen=True)
class SecurityRequest:
    principal_id: str
    action: str
    resource: str
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class Grant:
    """An explicit, exact-scope grant issued by the control plane.

    Wildcards are intentionally unsupported in this first implementation.
    """
    policy_id: str
    principal_id: str
    action: str
    resource: str
    capabilities: frozenset[str]
    expires_at: datetime | None = None
