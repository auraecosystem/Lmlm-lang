"""Deterministic lifecycle preflight checks; never execute inspected artifacts."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lmlm_security import IOCSet


@dataclass(frozen=True)
class LifecycleReport:
    status: str
    checks: dict[str, str]
    findings: list[dict[str, str]]
    limitations: tuple[str, ...] = (
        "This report is preflight evidence, not proof that an artifact is safe.",
        "No source code, model, binary, subprocess, or network request is executed.",
        "OS sandboxing and mandatory production runtime enforcement are not provided here.",
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_ioc_set(path: str | Path) -> IOCSet:
    """Load a local JSON indicator fixture without network access."""
    fixture = json.loads(Path(path).read_text(encoding="utf-8"))
    if fixture.get("handling") != "offline_only":
        raise ValueError("LSLC accepts only fixtures explicitly marked offline_only")
    if fixture.get("status") != "unverified_indicators":
        raise ValueError("IOC fixture must preserve unverified indicator status")
    return IOCSet.from_mapping(fixture)


def run_security_self_test(fixture_path: str | Path) -> LifecycleReport:
    """Validate fixture metadata and prove the matcher detects and rejects canaries."""
    checks: dict[str, str] = {}
    findings: list[dict[str, str]] = []
    try:
        iocs = load_ioc_set(fixture_path)
        checks["fixture_metadata"] = "passed"
        known_hash = next(iter(iocs.sha256), None)
        if known_hash is None:
            raise ValueError("fixture contains no SHA-256 indicators")
        # Exercise exact-hash matching with a deterministic synthetic byte string
        # whose digest is already present only if it can be represented safely.
        # Instead, validate matcher behavior with a local, temporary IOC set.
        import hashlib
        sample = b"lmlm-lslc-self-test"
        sample_iocs = IOCSet(sha256=frozenset({hashlib.sha256(sample).hexdigest()}))
        positive = sample_iocs.scan_bytes(sample)
        negative = sample_iocs.scan_bytes(b"benign-lmlm-input")
        if not positive or negative:
            raise RuntimeError("IOC matcher self-test failed")
        checks["ioc_positive_negative"] = "passed"
        checks["network_access"] = "not_used"
        checks["execution_of_scanned_content"] = "not_performed"
    except Exception as exc:
        checks["security_self_test"] = "failed"
        findings.append({
            "kind": "lifecycle_check_failure",
            "detail": type(exc).__name__,
        })
    status = "passed" if not findings else "failed"
    return LifecycleReport(status, checks, findings)
