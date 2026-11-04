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

The Native frontend supports a deliberately small `.lmlm` subset: module/import declarations, the documented annotations, and a single `model.generate` method body. It parses into an AST and lowers to the v0.1 IR.

The Python-compatible frontend uses Python AST parsing with the Python 3.10 grammar and accepts only the documented LMLM imports, decorators, async method signature, model-load call, and generation call. It does not import or execute source. Both frontends lower equivalent examples to identical normalized IR, covered by a differential test.

The Hybrid frontend is specified but not implemented yet. Neither frontend executes source, authorizes capabilities, loads models, or provides a production runtime.

## Secure Lifecycle Control (LSLC)

The `lmlm_lslc` package coordinates local and GitHub Actions preflight checks: offline IOC fixture validation, security matcher self-tests, unit tests, Python source compilation, package builds, and a fail-closed release eligibility job.

Run locally:

```bash
python -m pip install --editable .
python -m unittest discover -s tests -v
python -m lmlm_lslc.cli self-test --fixture fixtures/threatintel/nikke-k2f.json
```

The CI workflow is `.github/workflows/lmlm-secure-lifecycle.yml`. It uses read-only workflow permissions, does not use `pull_request_target`, and does not contact supplied IOC domains or IP addresses.

**Scope warning:** LSLC is currently a CI/preflight coordinator, not an OS sandbox, production runtime, artifact-signing system, or proof that an artifact is safe. Runtime authorization must remain mandatory and independently enforced by LMLM.

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
- `src/lmlm_frontend/python_compat.py` — restricted Python AST frontend and v0.1 IR lowering.
- `src/lmlm_security/` — policy engine, IR security gate, integrity measurement, offline threat intelligence, and audit writer.
- `src/lmlm_lslc/` — secure lifecycle preflight orchestration and CLI.
- `tests/` — IR validation, frontend, differential, security and LSLC tests.
- `fixtures/threatintel/` — offline, user-supplied unverified indicator fixtures.
- `docs/SECURITY_CONTROL_PLANE.md` and `docs/SECURE_LIFECYCLE.md` — security and lifecycle scope.

## Security invariants

1. No `eval`, unrestricted `exec`, or implicit execution during import.
2. Unknown IR fields, operations, providers, and capabilities fail closed.
3. Source annotations are metadata, not authorization.
4. Model loading, tools, filesystem access, and remote agents require explicit policy decisions.
5. Remote execution is mediated by authorized adapters; the LMLM control plane remains authoritative.
6. IOC matching is offline-only; matches are evidence for review, not proof of compromise.
7. CI success does not grant runtime capabilities or authorize execution.

See [Language Specification v0.1](spec/LANGUAGE_SPEC_v0.1.md), [Security Control Plane](docs/SECURITY_CONTROL_PLANE.md), and [Secure Lifecycle](docs/SECURE_LIFECYCLE.md).
