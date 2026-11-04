import unittest
from lmlm_frontend.hybrid import HybridFrontendError, compile_source, parse
from lmlm_frontend.native import compile_source as native_compile
from lmlm_frontend.python_compat import compile_source as python_compile

HYBRID = """using System;
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
"""
NATIVE = """module LMLM.Assistant;
import LMLM.Models.Local;
import LMLM.Runtime;
@runtime(target: "local")
@model(provider: "local", name: "default")
@security(policy: "restricted")
@capability(["inference"])
@verify(mode: "required")
model Assistant { execute(input: Text) -> Response { return model.generate(input); } }
"""
PYTHON = """from __future__ import annotations
from lmlm import runtime
from lmlm.models import local
@runtime(target="local")
@local.model("default")
class Assistant:
 async def execute(self, prompt: str) -> str:
  model = await local.load("default")
  return await model.generate(prompt)
"""

class HybridTests(unittest.TestCase):
    def test_hybrid_lowers_to_shared_ir(self):
        self.assertEqual(compile_source(HYBRID), native_compile(NATIVE))
        self.assertEqual(compile_source(HYBRID), python_compile(PYTHON))

    def test_rejects_unapproved_import(self):
        with self.assertRaises(HybridFrontendError):
            compile_source(HYBRID.replace("using System;", "using System.IO;"))

    def test_rejects_extra_body_statement(self):
        with self.assertRaises(HybridFrontendError):
            compile_source(HYBRID.replace('var model =', 'Console.WriteLine(prompt);\nvar model ='))

    def test_rejects_remote_target(self):
        with self.assertRaises(HybridFrontendError):
            compile_source(HYBRID.replace('target="local"', 'target="remote"'))

if __name__ == "__main__":
    unittest.main()
