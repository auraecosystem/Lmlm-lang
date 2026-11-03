"""Fail-closed structural validation for the LMLM IR v0.1.

Validation is not authorization. The LMLM policy engine must independently
authorize a validated request before any runtime operation is performed.
"""

from __future__ import annotations

from typing import Any, Mapping


class IRValidationError(ValueError):
    """Raised when an IR document violates the v0.1 contract."""


_TOP_LEVEL = {
    "operation", "provider", "model", "input", "permissions", "verification"
}
_INPUT = {"type", "source"}
_VERIFICATION = {"required"}
_ALLOWED_PERMISSIONS = {"inference"}


def _exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing keys: {sorted(missing)}")
        if extra:
            parts.append(f"unknown keys: {sorted(extra)}")
        raise IRValidationError(f"{where}: " + "; ".join(parts))


def validate_ir(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize an IR mapping without executing it."""
    if not isinstance(document, Mapping):
        raise IRValidationError("IR must be a mapping")
    _exact_keys(document, _TOP_LEVEL, "IR")

    if document["operation"] != "model.generate":
        raise IRValidationError("unsupported operation")
    if document["provider"] not in {"local", "builtin"}:
        raise IRValidationError("unsupported provider")

    model = document["model"]
    if not isinstance(model, str) or not model.strip() or len(model) > 128:
        raise IRValidationError("model must be a non-empty string of at most 128 characters")

    input_spec = document["input"]
    if not isinstance(input_spec, Mapping):
        raise IRValidationError("input must be a mapping")
    _exact_keys(input_spec, _INPUT, "input")
    if input_spec["type"] != "text" or input_spec["source"] != "user_input":
        raise IRValidationError("input must be text sourced from user_input")

    permissions = document["permissions"]
    if not isinstance(permissions, list) or not permissions:
        raise IRValidationError("permissions must be a non-empty list")
    if any(not isinstance(p, str) for p in permissions):
        raise IRValidationError("permissions must contain strings")
    if len(set(permissions)) != len(permissions):
        raise IRValidationError("permissions must not contain duplicates")
    unknown = set(permissions) - _ALLOWED_PERMISSIONS
    if unknown:
        raise IRValidationError(f"unsupported permissions: {sorted(unknown)}")

    verification = document["verification"]
    if not isinstance(verification, Mapping):
        raise IRValidationError("verification must be a mapping")
    _exact_keys(verification, _VERIFICATION, "verification")
    if not isinstance(verification["required"], bool):
        raise IRValidationError("verification.required must be a boolean")

    return {
        "operation": "model.generate",
        "provider": document["provider"],
        "model": model.strip(),
        "input": {"type": "text", "source": "user_input"},
        "permissions": sorted(permissions),
        "verification": {"required": verification["required"]},
    }
