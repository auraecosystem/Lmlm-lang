"""Fail-closed parser/lowerer for the documented Hybrid .lmx subset.

This is intentionally a small grammar, not a C# or Python interpreter.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from lmlm_ir import IRValidationError, validate_ir


class HybridFrontendError(ValueError):
    def __init__(self, code: str, message: str, line: int | None = None):
        self.code, self.line = code, line
        suffix = f" at line {line}" if line is not None else ""
        super().__init__(f"{code}{suffix}: {message}")


@dataclass(frozen=True)
class HybridProgram:
    model: str
    provider: str
    class_name: str
    imports: tuple[str, ...]


_IMPORT = re.compile(r"^using\s+([A-Za-z_][\w.]*)\s*;\s*$")
_DIRECTIVE = re.compile(r"^from\s+__future__\s+import\s+annotations\s*;?\s*$")
_ANNOTATION = re.compile(r'^@(runtime|model|security)\((.*)\)\s*$')
_CLASS = re.compile(r"^class\s+([A-Za-z_]\w*)\s*\{\s*$")
_METHOD = re.compile(r"^public\s+async\s+Task<string>\s+Execute\(string\s+(\w+)\)\s*\{\s*$")


def parse(source: str) -> HybridProgram:
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    lines = [line.strip() for line in source.splitlines()]
    lines = [(i + 1, line) for i, line in enumerate(lines) if line and not line.startswith("//")]
    imports: list[str] = []
    annotations: dict[str, dict[str, str]] = {}
    class_name = model = provider = parameter = None
    phase = "header"
    body: list[str] = []
    for number, line in lines:
        if phase == "header":
            if _IMPORT.fullmatch(line):
                name = _IMPORT.fullmatch(line).group(1)
                if name not in {"System", "LMLM.Models.Local"}:
                    raise HybridFrontendError("E_IMPORT_NOT_ALLOWED", f"import {name!r} is not allowlisted", number)
                imports.append(name)
            elif _DIRECTIVE.fullmatch(line) or line == "using __ini__;":
                continue
            elif (m := _ANNOTATION.fullmatch(line)):
                name, raw = m.groups()
                if name in annotations:
                    raise HybridFrontendError("E_ANNOTATION_INVALID", f"duplicate @{name}", number)
                pairs = re.findall(r'(\w+)\s*=\s*"([^"\n]*)"', raw)
                residue = re.sub(r'(\w+)\s*=\s*"[^"\n]*"', "", raw).strip().strip(",")
                if residue or len(pairs) != len(set(k for k, _ in pairs)):
                    raise HybridFrontendError("E_ANNOTATION_INVALID", "annotation arguments must be unique string key/value pairs", number)
                annotations[name] = dict(pairs)
            elif (m := _CLASS.fullmatch(line)):
                class_name = m.group(1)
                phase = "method"
            else:
                raise HybridFrontendError("E_SYNTAX_UNSUPPORTED", "unexpected Hybrid header declaration", number)
        elif phase == "method":
            m = _METHOD.fullmatch(line)
            if not m:
                raise HybridFrontendError("E_SYNTAX_UNSUPPORTED", "expected public async Task<string> Execute(string name)", number)
            parameter = m.group(1)
            phase = "body"
        elif phase == "body":
            body.append(line)
    if phase != "body" or len(body) != 4 or body[0] != "var model = await models.load(\"default\");" or body[1] != f"return await model.generate({parameter});" or body[2:] != ["}", "}"]:
        raise HybridFrontendError("E_SYNTAX_UNSUPPORTED", "method body must contain only the approved load and generation calls")
    if set(annotations) != {"runtime", "model", "security"}:
        raise HybridFrontendError("E_ANNOTATION_INVALID", "runtime, model, and security annotations are required")
    if annotations["runtime"] != {"target": "local"}:
        raise HybridFrontendError("E_ANNOTATION_INVALID", "only local runtime is supported")
    model_args = annotations["model"]
    if set(model_args) != {"provider", "name"} or model_args["provider"] not in {"local", "builtin"}:
        raise HybridFrontendError("E_ANNOTATION_INVALID", "model requires supported provider and name")
    if annotations["security"] != {"policy": "restricted"}:
        raise HybridFrontendError("E_ANNOTATION_INVALID", "restricted security policy is required")
    model = model_args["name"]
    if not model.strip() or len(model) > 128:
        raise HybridFrontendError("E_ANNOTATION_INVALID", "model name must be 1..128 characters")
    if model != "default":
        raise HybridFrontendError("E_SYNTAX_UNSUPPORTED", "the initial Hybrid subset binds load() to the declared default model")
    return HybridProgram(model, model_args["provider"], class_name or "", tuple(imports))


def lower(program: HybridProgram) -> dict[str, Any]:
    ir = {"operation": "model.generate", "provider": program.provider, "model": program.model,
          "input": {"type": "text", "source": "user_input"}, "permissions": ["inference"],
          "verification": {"required": True}}
    try:
        return validate_ir(ir)
    except IRValidationError as exc:
        raise HybridFrontendError("E_IR_INVALID", str(exc)) from exc


def compile_source(source: str) -> dict[str, Any]:
    return lower(parse(source))
