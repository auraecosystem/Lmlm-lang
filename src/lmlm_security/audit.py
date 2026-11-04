"""Append-only JSONL audit writer with an allowlisted event schema."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


_ALLOWED_FIELDS = {
    "event_type", "principal_id", "action", "resource", "decision",
    "reason", "policy_id", "evidence_ids",
}


class AuditLog:
    """Write minimal security events; reject arbitrary fields that may leak secrets."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, event: Mapping[str, Any]) -> None:
        extra = set(event) - _ALLOWED_FIELDS
        if extra:
            raise ValueError(f"unsupported audit fields: {sorted(extra)}")
        if not isinstance(event.get("event_type"), str) or not event["event_type"]:
            raise ValueError("event_type is required")
        record = dict(event)
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "evidence_ids" in record:
            if not isinstance(record["evidence_ids"], list) or not all(
                isinstance(item, str) for item in record["evidence_ids"]
            ):
                raise ValueError("evidence_ids must be a list of strings")
        encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(descriptor, encoded)
        finally:
            os.close(descriptor)
