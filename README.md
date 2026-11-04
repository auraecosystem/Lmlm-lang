# LMLM Language

LMLM Language defines three source profiles that compile toward one shared intermediate representation (IR) and one policy-governed execution boundary.

## Profiles

| Profile | Extension | Purpose |
|---|---|---|
| Native LMLM | `.lmlm` | Independent LMLM grammar and semantics |
| Python-compatible | `.lpy` | Python syntax with a constrained LMLM API |
| Hybrid | `.lmx` | Explicit C#-style declarations and Python-style directives |

These are three frontends, not three independent runtimes. Equivalent programs must lower to equivalent normalized IR.

## Implementation status

The merged v0.1 foundation provides the language specification, source examples, IR schema, differential fixture, and fail-closed IR validator.

The Native frontend is now being implemented incrementally. The current implementation supports a deliberately small `.lmlm` subset: module/import declarations, the documented annotations, and a single `model.generate` method body. It parses into an AST and lowers to the v0.1 IR. It does not execute source, authorize capabilities, load models, or provide a production runtime.

Python-compatible and Hybrid frontends are specified but not implemented yet.

## Quick validation

Requires Python 3.10+.

```bash
python -m pip install --editable .
python -m unittest discover -s tests -v
```

GitHub Actions runs the test suite on Python 3.10, 3.11, and 3.12.

## Architecture

```text
.lmlm ──> Native frontend ─────┐
.lpy  ──> Python frontend ─────┼─> semantic analysis ─> normalized IR
.lmx  ──> Hybrid frontend ────┘                         |
                                                        v
                                            IR validation + policy
                                                        |
                                                        v
                                         LMLM Core execution planner
                                                        |
                                                        v
                                     authorized model/tool/agent adapters
```

The language frontends never grant capabilities. An annotation such as `@capability(["inference"])` records a requested capability; the policy engine must authorize it independently.

## Layout

- `spec/LANGUAGE_SPEC_v0.1.md` — language profiles, semantics, imports, annotations, diagnostics, and compiler contract.
- `spec/IR_SCHEMA.json` — machine-readable v0.1 IR schema.
- `src/lmlm_ir/validator.py` — fail-closed structural validator.
- `src/lmlm_frontend/native.py` — strict Native lexer/parser, AST, allowlisted imports, and v0.1 IR lowering.
- `tests/` — IR validator and Native frontend tests.
- `examples/` — equivalent Native, Python-compatible, and Hybrid examples.
- `fixtures/differential/` — canonical IR conformance fixture.

## Security invariants

1. No `eval`, unrestricted `exec`, or implicit execution during import.
2. Unknown IR fields, operations, providers, and capabilities fail closed.
3. Source annotations are metadata, not authorization.
4. Model loading, tools, filesystem access, and remote agents require explicit policy decisions.
5. Remote execution is mediated by authorized adapters; the LMLM control plane remains authoritative.

See [Language Specification v0.1](spec/LANGUAGE_SPEC_v0.1.md).
