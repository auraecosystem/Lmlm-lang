"""Cross-profile checks for equivalent LMLM source programs."""
import unittest

from lmlm_frontend.native import compile_source as compile_native
from lmlm_frontend.python_compat import compile_source as compile_python


NATIVE = """module LMLM.Assistant;
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


class DifferentialFrontendTests(unittest.TestCase):
    def test_native_and_python_profiles_lower_to_identical_ir(self):
        self.assertEqual(compile_native(NATIVE), compile_python(PYTHON))


if __name__ == "__main__":
    unittest.main()
