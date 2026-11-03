# LMLM Language

LMLM Language defines three source profiles that compile toward one shared intermediate representation (IR) and one policy-governed execution boundary.

## Profiles

| Profile | Extension | Purpose |
|---|---|---|
| Native LMLM | `.lmlm` | Independent LMLM grammar and semantics |
| Python-compatible | `.lpy` | Python syntax with a constrained LMLM API |
| Hybrid | `.lmx` | Explicit C#-style declarations and Python-style directives |

These are three frontends, not three independent runtimes. Equivalent programs must lower to equivalent normalized IR.

## Repository status

This repository was an empty language-project shell. The `feat/three-language-foundation` branch establishes the v0.1 specification, sample programs, IR schema, and a dependency-free IR validator. It is **not yet a complete compiler or executable runtime**.

## Quick validation

Requires Python 3.10+.

```bash
python -m unittest discover -s tests -v
```

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
- `tests/` — IR validation tests.
- `examples/` — equivalent Native, Python-compatible, and Hybrid examples.
- `fixtures/differential/` — canonical IR conformance fixture.

## Security invariants

1. No `eval`, unrestricted `exec`, or implicit execution during import.
2. Unknown IR fields, operations, providers, and capabilities fail closed.
3. Source annotations are metadata, not authorization.
4. Model loading, tools, filesystem access, and remote agents require explicit policy decisions.
5. Remote execution is mediated by authorized adapters; the LMLM control plane remains authoritative.

See [Language Specification v0.1](spec/LANGUAGE_SPEC_v0.1.md).
