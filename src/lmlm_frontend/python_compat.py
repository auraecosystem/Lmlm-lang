"""Restricted Python-compatible .lpy frontend.

Python's parser is used only to build an AST. Source is never imported,
evaluated, compiled to bytecode, or executed by this frontend.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from lmlm_ir import IRValidationError, validate_ir


class PythonFrontendError(ValueError):
    """Stable diagnostic for invalid or unsupported .lpy source."""

    def __init__(self, code: str, message: str, line: int | None = None,
                 column: int | None = None):
        self.code = code
        self.line = line
        self.column = column
        location = f" at {line}:{column}" if line is not None else ""
        super().__init__(f"{code}{location}: {message}")


@dataclass(frozen=True)
class PythonProgram:
    module_name: str
    model_name: str
    model_id: str
    method_name: str
    parameter_name: str
    imports: tuple[str, ...]


_ALLOWED_IMPORTS = {
    ("__future__", "annotations"),
    ("lmlm", "runtime"),
    ("lmlm.models", "local"),
}


def _fail(node: ast.AST, message: str, code: str = "E_SYNTAX_UNSUPPORTED"):
    raise PythonFrontendError(
        code, message, getattr(node, "lineno", None),
        getattr(node, "col_offset", None)
    )


def _is_name(node: ast.AST, value: str) -> bool:
    return isinstance(node, ast.Name) and node.id == value


def _is_string(node: ast.AST, value: str | None = None) -> bool:
    return (isinstance(node, ast.Constant) and isinstance(node.value, str)
            and (value is None or node.value == value))


def _call(node: ast.AST, function: ast.AST, positional: int) -> ast.Call:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        _fail(node, "expected an approved LMLM API call")
    if not isinstance(node.func.value, ast.Name) or not (
        (isinstance(function, ast.Attribute)
         and isinstance(function.value, ast.Name)
         and node.func.value.id == function.value.id
         and node.func.attr == function.attr)
    ):
        _fail(node, "unexpected API target")
    if len(node.args) != positional or node.keywords:
        _fail(node, "unexpected API arguments")
    return node


def parse(source: str) -> PythonProgram:
    """Parse the explicitly supported Python-compatible profile subset."""
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    try:
        tree = ast.parse(source, filename="<lmlm-source>", mode="exec",
                         feature_version=(3, 10), type_comments=False)
    except SyntaxError as exc:
        raise PythonFrontendError(
            "E_SYNTAX_UNSUPPORTED", exc.msg, exc.lineno, exc.offset
        ) from exc

    imports: list[str] = []
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            _fail(statement, "plain imports are not allowed in the .lpy profile",
                  "E_IMPORT_NOT_ALLOWED")
        elif isinstance(statement, ast.ImportFrom):
            if statement.level != 0 or len(statement.names) != 1:
                _fail(statement, "only single-name absolute imports are allowed",
                      "E_IMPORT_NOT_ALLOWED")
            key = (statement.module or "", statement.names[0].name)
            if key not in _ALLOWED_IMPORTS or statement.names[0].asname:
                _fail(statement, "import is not in the .lpy allowlist",
                      "E_IMPORT_NOT_ALLOWED")
            imports.append(f"{key[0]}.{key[1]}")
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.ClassDef)):
            break
        else:
            _fail(statement, "top-level executable statements are forbidden")

    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if len(classes) != 1 or len(tree.body) != len(imports) + 1:
        _fail(tree, "exactly one model class and approved imports are required")
    cls = classes[0]
    if cls.bases or cls.keywords:
        _fail(cls, "class inheritance and metaclass options are unsupported")
    if len(cls.decorator_list) != 2:
        _fail(cls, "class requires @runtime and @local.model decorators",
              "E_ANNOTATION_INVALID")

    runtime = cls.decorator_list[0]
    if not isinstance(runtime, ast.Call) or not _is_name(runtime.func, "runtime"):
        _fail(runtime, "first decorator must be @runtime(target=\"local\")",
              "E_ANNOTATION_INVALID")
    if runtime.args or len(runtime.keywords) != 1:
        _fail(runtime, "runtime decorator requires exactly target=\"local\"",
              "E_ANNOTATION_INVALID")
    if runtime.keywords[0].arg != "target" or not _is_string(
        runtime.keywords[0].value, "local"
    ):
        _fail(runtime, "only the local runtime target is supported",
              "E_ANNOTATION_INVALID")

    model_decorator = cls.decorator_list[1]
    if (not isinstance(model_decorator, ast.Call)
            or not isinstance(model_decorator.func, ast.Attribute)
            or not _is_name(model_decorator.func.value, "local")
            or model_decorator.func.attr != "model"
            or len(model_decorator.args) != 1
            or model_decorator.keywords
            or not _is_string(model_decorator.args[0])):
        _fail(model_decorator, "second decorator must be @local.model(\"model-id\")",
              "E_ANNOTATION_INVALID")
    model_id = model_decorator.args[0].value
    if not model_id.strip() or len(model_id) > 128:
        _fail(model_decorator, "model id must be 1..128 characters",
              "E_ANNOTATION_INVALID")

    methods = [node for node in cls.body if isinstance(node, ast.AsyncFunctionDef)]
    if len(methods) != 1 or len(cls.body) != 1:
        _fail(cls, "class must contain exactly one async execute method")
    method = methods[0]
    if method.name != "execute" or method.decorator_list:
        _fail(method, "only undecorated async def execute is supported")
    if (len(method.args.args) != 2 or method.args.args[0].arg != "self"
            or method.args.args[1].annotation is None
            or not _is_name(method.args.args[1].annotation, "str")
            or method.args.vararg or method.args.kwarg or method.args.kwonlyargs
            or method.args.defaults or method.args.kw_defaults
            or not _is_name(method.returns, "str")):
        _fail(method, "execute signature must be async def execute(self, prompt: str) -> str",
              "E_TYPE_MISMATCH")
    if len(method.body) != 2:
        _fail(method, "execute body must load a model then return its generation")

    assignment, returned = method.body
    if (not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
            or not _is_name(assignment.targets[0], "model")):
        _fail(assignment, "first statement must assign the approved model load")
    load_await = assignment.value
    if not isinstance(load_await, ast.Await):
        _fail(load_await, "model.load must be awaited")
    load_call = load_await.value
    if (not isinstance(load_call, ast.Call)
            or not isinstance(load_call.func, ast.Attribute)
            or not _is_name(load_call.func.value, "local")
            or load_call.func.attr != "load"
            or len(load_call.args) != 1 or load_call.keywords
            or not _is_string(load_call.args[0], model_id)):
        _fail(load_call, "model load must match the declared model id")

    if not isinstance(returned, ast.Return) or not isinstance(returned.value, ast.Await):
        _fail(returned, "second statement must return awaited model.generate(prompt)")
    generate = returned.value.value
    if (not isinstance(generate, ast.Call)
            or not isinstance(generate.func, ast.Attribute)
            or not _is_name(generate.func.value, "model")
            or generate.func.attr != "generate"
            or len(generate.args) != 1 or generate.keywords
            or not _is_name(generate.args[0], method.args.args[1].arg)):
        _fail(generate, "only model.generate(prompt) is supported")

    return PythonProgram(".".join(imports), cls.name, model_id, method.name,
                         method.args.args[1].arg, tuple(imports))


def lower(program: PythonProgram) -> dict[str, Any]:
    """Lower the restricted Python AST summary into normalized shared IR."""
    ir = {
        "operation": "model.generate",
        "provider": "local",
        "model": program.model_id,
        "input": {"type": "text", "source": "user_input"},
        "permissions": ["inference"],
        "verification": {"required": True},
    }
    try:
        return validate_ir(ir)
    except IRValidationError as exc:
        raise PythonFrontendError("E_IR_INVALID", str(exc)) from exc


def compile_source(source: str) -> dict[str, Any]:
    """Parse and lower source without importing or executing it."""
    return lower(parse(source))
