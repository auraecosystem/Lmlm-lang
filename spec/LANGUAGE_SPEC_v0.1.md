# LMLM Language Specification v0.1

**Status:** Draft implementation baseline  
**Profiles:** Native `.lmlm`, Python-compatible `.lpy`, Hybrid `.lmx`

## 1. Goals and architecture

LMLM offers three source profiles with distinct grammars and developer trade-offs. All compile through semantic analysis into one normalized intermediate representation (IR). Only validated IR may be submitted to the LMLM policy engine and execution planner.

```text
Native .lmlm ─────┐
Python .lpy ──────┼─> AST ─> semantic analysis ─> normalized IR
Hybrid .lmx ──────┘                                  |
                                                     v
                                      IR validator + policy engine
                                                     |
                                                     v
                                        LMLM Core execution planner
                                                     |
                                                     v
                                    authorized adapters and execution
```

The frontends are not execution engines and cannot independently authorize operations.

## 2. Differential profile comparison

| Dimension | Native | Python-compatible | Hybrid |
|---|---|---|---|
| Grammar | LMLM-owned | Python grammar plus LMLM API | LMLM hybrid grammar |
| Compatibility | LMLM language versions | Selected Python syntax/runtime APIs | Explicit supported subset |
| Types | LMLM type system | Python annotations validated at boundaries | C#-style declarations plus LMLM types |
| Imports | LMLM module resolver | Python import resolver with allowlist | `using` and permitted `from` forms |
| Async | Native async semantics | Python `async/await` | C#-style `async/await` subset |
| Strength | Sovereignty and semantic control | Fastest ecosystem adoption | Migration/interoperability |
| Cost | New compiler and tooling | Compatibility and isolation burden | Highest grammar/semantic complexity |

Hybrid does not mean arbitrary C# and Python can be mixed. Unsupported constructs must produce diagnostics with source locations; never silently reinterpret them.

## 3. Shared annotation contract

The initial shared annotations are:

- `@runtime(target="local")`: requested execution target.
- `@model(provider="local", name="default")`: requested model provider and identifier.
- `@security(policy="restricted")`: requested security profile.
- `@capability(["inference"])`: declared capability requirements.
- `@timeout(seconds=60)`: requested execution deadline.
- `@verify(mode="required")`: verification requirement.

Annotations are declarative metadata. They are not grants. The policy engine evaluates the principal, requested operation, environment, and applicable policy before creating an authorized execution plan.

## 4. Import and initialization semantics

The original prototype syntax includes:

```text
using System;
from __future__ import annotations;
using __local__ import models;
using __ini__;
using in-builtModel;
using System.Linq;
using System.Data.Objects;
```

v0.1 interpretation:

- `System`, `System.Linq`, and `System.Data.Objects` are Hybrid namespace examples. They do not imply that the .NET runtime or full Base Class Library is embedded.
- `from __future__ import annotations` belongs to the Python profile; Hybrid may accept it only in a designated Python-directive region.
- `using __local__ import models` is a legacy spelling for the LMLM local-model registry.
- `using __ini__` requests the explicit LMLM initialization module.
- `using in-builtModel` is legacy spelling for the built-in model registry. Prefer `import LMLM.Models.Builtin;` in Native or the documented Python API in `.lpy`.
- All imports resolve through profile-specific allowlists. Arbitrary module, assembly, or native-library loading is outside v0.1.

Importing a module must not implicitly start inference, access remote services, or execute arbitrary source code. Initialization is an explicit lifecycle operation.

## 5. Native profile (.lmlm)

Illustrative program:

```lmlm
module LMLM.Assistant;

import LMLM.Models.Local;
import LMLM.Runtime;

@runtime(target: "local")
@model(provider: "local", name: "default")
@security(policy: "restricted")
@capability(["inference"])
@verify(mode: "required")

model Assistant {
    execute(input: Text) -> Response {
        return model.generate(input);
    }
}
```

Native owns its lexer, parser, AST, type checker, module resolution, standard library contract, and diagnostics. Its language semantics must not be defined as a thin alias of Python or C#.

## 6. Python-compatible profile (.lpy)

Illustrative program:

```python
from __future__ import annotations

from lmlm import runtime
from lmlm.models import local

@runtime(target="local")
@local.model("default")
class Assistant:
    async def execute(self, prompt: str) -> str:
        model = await local.load("default")
        return await model.generate(prompt)
```

The frontend parses with a pinned Python grammar, validates syntax and imports, resolves approved LMLM decorators/APIs, then lowers to common IR. It must not use unrestricted `eval` or `exec` as a compilation shortcut. Python type hints are checked at LMLM boundaries; they are not security controls.

## 7. Hybrid profile (.lmx)

Illustrative program:

```lmx
using System;
using LMLM.Models.Local;

from __future__ import annotations;

using __ini__;

@runtime(target="local")
@model(provider="local", name="default")
@security(policy="restricted")

class Assistant {
    public async Task<string> Execute(string prompt) {
        var model = await models.load("default");
        return await model.generate(prompt);
    }
}
```

Hybrid has a dedicated grammar with explicitly delimited C#-style declarations, permitted Python directives, and LMLM annotations/API calls. The parser rejects ambiguous mixed syntax. Each exposed namespace/API needs a documented implementation or adapter.

## 8. Shared normalized IR

v0.1 defines one operation, `model.generate`:

```json
{
  "operation": "model.generate",
  "provider": "local",
  "model": "default",
  "input": {"type": "text", "source": "user_input"},
  "permissions": ["inference"],
  "verification": {"required": true}
}
```

The complete machine-readable contract is `spec/IR_SCHEMA.json`. Unknown fields and unsupported operations/providers/capabilities fail closed. IR describes a request; it does not authorize it.

## 9. Compiler frontend contract

Each frontend implements the conceptual stages:

1. `parse(source) -> AST | Diagnostics`
2. `analyze(AST) -> TypedProgram | Diagnostics`
3. `lower(TypedProgram) -> IR | Diagnostics`
4. `IRValidator.validate(IR) -> ValidationResult`
5. `PolicyEngine.authorize(IR, principal) -> Decision`
6. `Runtime.execute(AuthorizedPlan) -> ExecutionResult`

Only the policy engine can issue an authorized plan. The runtime accepts an authorized plan, not raw source or unvalidated IR.

## 10. Diagnostics

Diagnostics include stable code, profile, message, source span (when available), and remediation. Minimum codes:

- `E_IMPORT_NOT_ALLOWED`
- `E_SYNTAX_UNSUPPORTED`
- `E_ANNOTATION_INVALID`
- `E_TYPE_MISMATCH`
- `E_IR_INVALID`
- `E_CAPABILITY_DENIED`
- `E_MODEL_NOT_FOUND`

## 11. Differential conformance

Equivalent programs in the three profiles must lower to identical normalized IR. Tests compare operation, provider, model, inputs, permissions, and verification requirements. Formatting and source spans may differ; execution semantics and requested authority may not.

A frontend fails conformance if it emits broader permissions, a different provider/model, or a weaker verification requirement for an equivalent fixture. Unsupported syntax must fail explicitly.

## 12. v0.1 non-goals

- Full Python or C# compatibility.
- Arbitrary module, assembly, or native-library loading.
- Arbitrary source execution.
- A production inference server or model registry.
- Remote execution without policy-governed adapters.
- Treating annotations as authorization.
