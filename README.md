# LMLM Language

LMLM Language defines three source profiles that compile toward one shared intermediate representation (IR) and one policy-governed execution boundary.

## Profiles

| Profile | Extension | Purpose |
|---|---|---|
| Native LMLM | `.lmlm` | Independent LMLM grammar and semantics |
| Python-compatible | `.lpy` | Python syntax with a constrained LMLM API |
| Hybrid | `.lmx` | Explicit C#-style declarations and Python-style directives |

These are three frontends, not three independent runtimes. Equivalent programs must lower to equivalent normalized IR.

## Implementation

- Native `.lmlm`: strict lexer/parser and lowering for the documented `model.generate` subset.
- Python-compatible `.lpy`: Python 3.10 grammar parsed to AST; source is never imported or executed.
- Hybrid `.lmx`: dedicated, fail-closed parser for the documented C#-style class/method and approved LMLM calls. It is not a C# or Python interpreter.
- Shared v0.1 IR validator rejects unknown fields, operations, providers, and capabilities.
- Cross-profile differential tests assert identical normalized IR.

## Runtime boundary

```text
.lmlm ──> Native frontend ─────┐
.lpy  ──> Python frontend ─────┼─> normalized IR
.lmx  ──> Hybrid frontend ─────┘       |
                                       v
                              IR structural validation
                                       |
                                       v
                              independent policy engine
                                       |
                                       v
                              authorized runtime request
                                       |
                                       v
                          explicitly injected model adapter
```

The `lmlm_runtime` package supplies an execution boundary with:

- authenticated principal and capability checks;
- provider/model allowlists and deny-by-default policy;
- explicit adapter injection (no implicit model downloads or loading);
- bounded input/output, timeouts, and cancellation propagation;
- mandatory output verification when the IR requests it.

Example integration:

```python
from lmlm_frontend.hybrid import compile_source
from lmlm_runtime import Principal, Runtime

ir = compile_source(open("assistant.lmx", encoding="utf-8").read())
principal = Principal(
    subject="service-account",
    capabilities=frozenset({"inference"}),
    allowed_providers=frozenset({"local"}),
    allowed_models=frozenset({"default"}),
)
# Inject an application-owned adapter implementing async generate(model, prompt).
runtime = Runtime(adapters={"local": model_adapter}, verifier=verify_output)
result = await runtime.execute(ir, principal, "Hello")
print(result.output)
```

Adapters, credentials, model weights, and the verifier are application responsibilities. The repository does not claim a bundled inference server or a remotely hosted model. Remote execution must be implemented as a separately authorized adapter; the LMLM control plane remains authoritative.

## Validation

Requires Python 3.10+.

```bash
python -m pip install --editable .
python -m unittest discover -s tests -v
```

GitHub Actions runs tests on Python 3.10, 3.11, and 3.12.

## Layout

- `spec/LANGUAGE_SPEC_v0.1.md` — language profiles and compiler contract.
- `spec/IR_SCHEMA.json` — machine-readable IR schema.
- `src/lmlm_ir/` — shared IR validation.
- `src/lmlm_frontend/native.py` — Native frontend.
- `src/lmlm_frontend/python_compat.py` — Python-compatible frontend.
- `src/lmlm_frontend/hybrid.py` — Hybrid frontend.
- `src/lmlm_runtime/` — policy and execution boundary.
- `tests/` — validation, security-boundary, runtime, and differential tests.

## Security invariants

1. No `eval`, unrestricted `exec`, or implicit source execution.
2. Unknown IR fields, operations, providers, and capabilities fail closed.
3. Source annotations are metadata, not authorization.
4. Model loading, tools, filesystem access, and remote agents require explicit policy decisions.
5. Runtime accepts normalized IR and an authenticated principal; adapters are injected explicitly.
6. Model-generated tool calls require a separate authorization decision and are not implicitly executed.

See [Language Specification v0.1](spec/LANGUAGE_SPEC_v0.1.md).
