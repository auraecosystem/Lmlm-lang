"""Offline indicator matching. No DNS, HTTP, sockets, or external lookups."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class IndicatorMatch:
    indicator_type: str
    indicator: str
    evidence: str


@dataclass(frozen=True)
class IOCSet:
    sha256: frozenset[str] = frozenset()
    binary_prefixes: tuple[bytes, ...] = ()
    domains: frozenset[str] = frozenset()
    ips: frozenset[str] = frozenset()
    paths: tuple[str, ...] = ()
    text_markers: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "IOCSet":
        hashes = frozenset(str(x).lower() for x in data.get("sha256", []))
        if any(len(x) != 64 or any(c not in "0123456789abcdef" for c in x) for x in hashes):
            raise ValueError("IOC SHA-256 values must be 64 hexadecimal characters")
        prefixes = tuple(bytes.fromhex(x) for x in data.get("binary_prefixes_hex", []))
        if any(not item for item in prefixes):
            raise ValueError("binary prefixes must not be empty")
        return cls(
            sha256=hashes,
            binary_prefixes=prefixes,
            domains=frozenset(str(x).lower().rstrip(".") for x in data.get("domains", [])),
            ips=frozenset(str(x) for x in data.get("ips", [])),
            paths=tuple(str(x).lower().replace("/", "\\") for x in data.get("paths", [])),
            text_markers=tuple(str(x).lower() for x in data.get("text_markers", [])),
        )

    def scan_bytes(self, content: bytes) -> list[IndicatorMatch]:
        found: list[IndicatorMatch] = []
        digest = hashlib.sha256(content).hexdigest()
        if digest in self.sha256:
            found.append(IndicatorMatch("sha256", digest, "exact_content_hash"))
        for prefix in self.binary_prefixes:
            if content.startswith(prefix):
                found.append(IndicatorMatch("binary_prefix", prefix.hex(), "file_prefix_match"))
        return found

    def scan_path(self, path: str | Path) -> list[IndicatorMatch]:
        target = Path(path)
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            prefix = stream.read(max((len(x) for x in self.binary_prefixes), default=0))
            digest.update(prefix)
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        found: list[IndicatorMatch] = []
        hexdigest = digest.hexdigest()
        if hexdigest in self.sha256:
            found.append(IndicatorMatch("sha256", hexdigest, "exact_content_hash"))
        for signature in self.binary_prefixes:
            if prefix.startswith(signature):
                found.append(IndicatorMatch("binary_prefix", signature.hex(), "file_prefix_match"))
        normalized_path = str(target).lower().replace("/", "\\")
        for indicator in self.paths:
            if indicator and indicator in normalized_path:
                found.append(IndicatorMatch("path", indicator, "path_substring_match"))
        return found

    def scan_text(self, text: str) -> list[IndicatorMatch]:
        lowered = text.lower()
        found: list[IndicatorMatch] = []
        for domain in self.domains:
            if domain and domain in lowered:
                found.append(IndicatorMatch("domain", domain, "literal_text_match"))
        for address in self.ips:
            if address and address in lowered:
                found.append(IndicatorMatch("ip", address, "literal_text_match"))
        for marker in self.text_markers:
            if marker and marker in lowered:
                found.append(IndicatorMatch("text_marker", marker, "literal_text_match"))
        return found
