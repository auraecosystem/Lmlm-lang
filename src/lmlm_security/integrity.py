"""Read-only SHA-256 file integrity measurement."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IntegrityResult:
    path: str
    sha256: str
    size_bytes: int


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> IntegrityResult:
    """Hash a file without executing or modifying it."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    target = Path(path)
    digest = hashlib.sha256()
    size = 0
    with target.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return IntegrityResult(str(target), digest.hexdigest(), size)
