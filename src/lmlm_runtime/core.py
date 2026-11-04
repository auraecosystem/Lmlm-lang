"""Minimal production-oriented execution boundary for normalized LMLM IR.

No source evaluation, implicit model loading, shell access, or remote dispatch is
performed here. Applications inject explicitly configured provider adapters.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import time
from typing import Any, Awaitable, Callable, Mapping, Protocol

from lmlm_ir import IRValidationError, validate_ir


class AuthorizationError(PermissionError):
    """The principal or request is not authorized."""


class ExecutionError(RuntimeError):
    """An adapter failed or returned an invalid result."""


@dataclass(frozen=True)
class Principal:
    subject: str
    capabilities: frozenset[str]
    allowed_providers: frozenset[str] = frozenset({"local"})
    allowed_models: frozenset[str] = frozenset()
    active: bool = True


@dataclass(frozen=True)
class Policy:
    required_capabilities: frozenset[str] = frozenset({"inference"})
    allowed_providers: frozenset[str] = frozenset({"local"})
    max_input_chars: int = 32_000

    def authorize(self, ir: Mapping[str, Any], principal: Principal) -> dict[str, Any]:
        if not isinstance(principal, Principal) or not principal.active or not principal.subject.strip():
            raise AuthorizationError("an active authenticated principal is required")
        normalized = validate_ir(ir)
        required = set(normalized["permissions"]) | set(self.required_capabilities)
        if not required.issubset(principal.capabilities):
            raise AuthorizationError("principal lacks required capabilities")
        provider = normalized["provider"]
        if provider not in self.allowed_providers or provider not in principal.allowed_providers:
            raise AuthorizationError("provider is not authorized")
        if principal.allowed_models and normalized["model"] not in principal.allowed_models:
            raise AuthorizationError("model is not authorized")
        return normalized


@dataclass(frozen=True)
class RuntimeConfig:
    timeout_seconds: float = 60.0
    max_output_chars: int = 128_000

    def __post_init__(self):
        if not 0 < self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be in (0, 3600]")
        if self.max_output_chars < 1:
            raise ValueError("max_output_chars must be positive")


class ModelAdapter(Protocol):
    async def generate(self, model: str, prompt: str) -> str: ...


@dataclass(frozen=True)
class ExecutionResult:
    request_id: str
    status: str
    output: str
    elapsed_seconds: float
    provider: str
    model: str


@dataclass
class Runtime:
    policy: Policy = field(default_factory=Policy)
    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    adapters: Mapping[str, ModelAdapter] = field(default_factory=dict)
    verifier: Callable[[str], bool | Awaitable[bool]] | None = None

    async def execute(self, ir: Mapping[str, Any], principal: Principal, prompt: str,
                      *, request_id: str = "local-request") -> ExecutionResult:
        # Authorize before looking up or invoking any adapter.
        plan = self.policy.authorize(ir, principal)
        if not isinstance(prompt, str) or len(prompt) > self.policy.max_input_chars:
            raise ExecutionError("input must be text within the configured limit")
        adapter = self.adapters.get(plan["provider"])
        if adapter is None:
            raise ExecutionError(f"no adapter configured for provider {plan['provider']!r}")
        started = time.monotonic()
        try:
            output = await asyncio.wait_for(
                adapter.generate(plan["model"], prompt),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise ExecutionError("model execution timed out") from exc
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise ExecutionError("model adapter failed") from exc
        if not isinstance(output, str) or len(output) > self.config.max_output_chars:
            raise ExecutionError("adapter returned invalid or oversized output")
        if plan["verification"]["required"]:
            if self.verifier is None:
                raise ExecutionError("verification is required but no verifier is configured")
            verdict = self.verifier(output)
            if asyncio.iscoroutine(verdict):
                verdict = await verdict
            if verdict is not True:
                raise ExecutionError("output verification failed")
        return ExecutionResult(request_id, "succeeded", output,
                               time.monotonic() - started, plan["provider"], plan["model"])
