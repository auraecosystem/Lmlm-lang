"""Strict Native .lmlm frontend for the v0.1 model.generate subset.

This frontend parses source into a small AST and lowers only the explicitly
supported model declaration into the shared IR. It never executes source.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from lmlm_ir import IRValidationError, validate_ir


class NativeSyntaxError(ValueError):
    """A source error with a stable code and character offset."""

    code = "E_SYNTAX_UNSUPPORTED"

    def __init__(self, message: str, offset: int):
        super().__init__(f"{self.code} at offset {offset}: {message}")
        self.offset = offset


class NativeSemanticError(ValueError):
    """A well-formed source program outside the supported v0.1 subset."""

    code = "E_ANNOTATION_INVALID"


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    offset: int


@dataclass(frozen=True)
class Annotation:
    name: str
    arguments: dict[str, Any]
    offset: int


@dataclass(frozen=True)
class NativeProgram:
    module: str
    imports: tuple[str, ...]
    annotations: tuple[Annotation, ...]
    model_name: str
    parameter_name: str
    offset: int


_TOKEN = re.compile(
    r"""(?P<SPACE>\s+)|(?P<COMMENT>//[^\n]*)|"""
    r'''(?P<STRING>"(?:\\.|[^"\\])*")|'''
    r"(?P<ARROW>->)|(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)|"
    r"(?P<PUNCT>[{}():;,\.@\[\]])"""
)


def _lex(source: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(source):
        match = _TOKEN.match(source, pos)
        if not match:
            raise NativeSyntaxError(f"unexpected character {source[pos]!r}", pos)
        kind = match.lastgroup
        value = match.group()
        if kind not in {"SPACE", "COMMENT"}:
            tokens.append(Token(kind or "", value, pos))
        pos = match.end()
    tokens.append(Token("EOF", "", len(source)))
    return tokens


class _Parser:
    def __init__(self, source: str):
        self.tokens = _lex(source)
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def take(self, value: str | None = None, kind: str | None = None) -> Token:
        token = self.current
        if value is not None and token.value != value:
            raise NativeSyntaxError(f"expected {value!r}, got {token.value!r}", token.offset)
        if kind is not None and token.kind != kind:
            raise NativeSyntaxError(f"expected {kind}, got {token.value!r}", token.offset)
        self.index += 1
        return token

    def dotted_name(self) -> str:
        parts = [self.take(kind="IDENT").value]
        while self.current.value == ".":
            self.take(".")
            parts.append(self.take(kind="IDENT").value)
        return ".".join(parts)

    def value(self) -> Any:
        if self.current.kind == "STRING":
            raw = self.take(kind="STRING").value
            # JSON-compatible string syntax; no escape evaluation or code execution.
            import json
            try:
                return json.loads(raw)
            except ValueError as exc:
                raise NativeSyntaxError("invalid string literal", self.current.offset) from exc
        if self.current.value == "[":
            self.take("[")
            values: list[Any] = []
            if self.current.value != "]":
                values.append(self.value())
                while self.current.value == ",":
                    self.take(",")
                    if self.current.value == "]":
                        break
                    values.append(self.value())
            self.take("]")
            return values
        raise NativeSyntaxError("annotation values must be strings or string lists", self.current.offset)

    def annotation(self) -> Annotation:
        start = self.take("@").offset
        name = self.take(kind="IDENT").value
        self.take("(")
        args: dict[str, Any] = {}
        if self.current.value != ")":
            # A single positional value is supported for @capability([...]).
            if self.current.value == "[":
                args["value"] = self.value()
            else:
                while True:
                    key = self.take(kind="IDENT").value
                    self.take(":")
                    if key in args:
                        raise NativeSyntaxError(f"duplicate annotation argument {key!r}", self.current.offset)
                    args[key] = self.value()
                    if self.current.value != ",":
                        break
                    self.take(",")
                    if self.current.value == ")":
                        break
        self.take(")")
        return Annotation(name, args, start)

    def parse(self) -> NativeProgram:
        self.take("module")
        module = self.dotted_name()
        self.take(";")

        imports: list[str] = []
        while self.current.value == "import":
            self.take("import")
            imports.append(self.dotted_name())
            self.take(";")

        annotations: list[Annotation] = []
        while self.current.value == "@":
            annotations.append(self.annotation())

        self.take("model")
        model_name = self.take(kind="IDENT").value
        self.take("{")
        self.take("execute")
        self.take("(")
        parameter = self.take(kind="IDENT").value
        self.take(":")
        self.take("Text")
        self.take(")")
        self.take("->")
        self.take("Response")
        self.take("{")
        self.take("return")
        self.take("model")
        self.take(".")
        self.take("generate")
        self.take("(")
        self.take(parameter)
        self.take(")")
        self.take(";")
        self.take("}")
        self.take("}")
        if self.current.kind != "EOF":
            raise NativeSyntaxError("unexpected trailing source", self.current.offset)

        return NativeProgram(module, tuple(imports), tuple(annotations), model_name, parameter,
                             annotations[0].offset if annotations else 0)


def parse(source: str) -> NativeProgram:
    """Parse the supported Native v0.1 subset into an immutable AST."""
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    return _Parser(source).parse()


def lower(program: NativeProgram) -> dict[str, Any]:
    """Lower a supported Native AST to normalized, validated v0.1 IR."""
    allowed_imports = {"LMLM.Models.Local", "LMLM.Runtime"}
    unknown_imports = set(program.imports) - allowed_imports
    if unknown_imports:
        raise NativeSemanticError(
            f"imports are not allowlisted: {', '.join(sorted(unknown_imports))}"
        )

    by_name: dict[str, Annotation] = {}
    allowed = {"runtime", "model", "security", "capability", "verify"}
    for annotation in program.annotations:
        if annotation.name not in allowed:
            raise NativeSemanticError(f"unsupported annotation @{annotation.name}")
        if annotation.name in by_name:
            raise NativeSemanticError(f"duplicate annotation @{annotation.name}")
        by_name[annotation.name] = annotation

    required = {"runtime", "model", "security", "capability", "verify"}
    missing = required - by_name.keys()
    if missing:
        raise NativeSemanticError(f"missing annotations: {', '.join(sorted(missing))}")

    expected = {
        "runtime": {"target": "local"},
        "security": {"policy": "restricted"},
        "capability": {"value": ["inference"]},
        "verify": {"mode": "required"},
    }
    for name, fields in expected.items():
        args = by_name[name].arguments
        if name == "capability":
            valid = args == {"value": ["inference"]} or args == {"capabilities": ["inference"]}
        else:
            valid = args == fields
        if not valid:
            raise NativeSemanticError(f"unsupported @{name} annotation arguments")

    model_args = by_name["model"].arguments
    if set(model_args) != {"provider", "name"}:
        raise NativeSemanticError("@model requires exactly provider and name")
    provider = model_args["provider"]
    model = model_args["name"]
    if not isinstance(provider, str) or provider not in {"local", "builtin"}:
        raise NativeSemanticError("unsupported model provider")
    if not isinstance(model, str) or not model.strip() or len(model) > 128:
        raise NativeSemanticError("model name must be 1..128 characters")

    ir = {
        "operation": "model.generate",
        "provider": provider,
        "model": model,
        "input": {"type": "text", "source": "user_input"},
        "permissions": ["inference"],
        "verification": {"required": True},
    }
    try:
        return validate_ir(ir)
    except IRValidationError as exc:
        raise NativeSemanticError(str(exc)) from exc


def compile_source(source: str) -> dict[str, Any]:
    """Parse and lower source. Authorization and execution are separate stages."""
    return lower(parse(source))
