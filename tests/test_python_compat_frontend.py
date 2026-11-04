import unittest

from lmlm_frontend.python_compat import (
    PythonFrontendError,
    compile_source,
    lower,
    parse,
)


SOURCE = """from __future__ import annotations

from lmlm import runtime
from lmlm.models import local

@runtime(target="local")
@local.model("default")
class Assistant:
    async def execute(self, prompt: str) -> str:
        model = await local.load("default")
        return await model.generate(prompt)
"""

EXPECTED = {
    "operation": "model.generate",
    "provider": "local",
    "model": "default",
    "input": {"type": "text", "source": "user_input"},
    "permissions": ["inference"],
    "verification": {"required": True},
}


class PythonCompatibleFrontendTests(unittest.TestCase):
    def test_parse_documented_example(self):
        program = parse(SOURCE)
        self.assertEqual(program.model_name, "Assistant")
        self.assertEqual(program.model_id, "default")
        self.assertEqual(program.method_name, "execute")
        self.assertEqual(program.parameter_name, "prompt")
        self.assertEqual(len(program.imports), 3)

    def test_compile_to_shared_ir(self):
        self.assertEqual(compile_source(SOURCE), EXPECTED)

    def test_lower_parsed_program(self):
        self.assertEqual(lower(parse(SOURCE)), EXPECTED)

    def test_rejects_arbitrary_import(self):
        with self.assertRaises(PythonFrontendError) as ctx:
            compile_source(SOURCE.replace("from lmlm import runtime",
                                          "import os"))
        self.assertEqual(ctx.exception.code, "E_IMPORT_NOT_ALLOWED")

    def test_rejects_top_level_execution(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace("class Assistant:", "print('unsafe')\n\nclass Assistant:"))

    def test_rejects_inheritance(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace("class Assistant:", "class Assistant(object):"))

    def test_rejects_non_local_target(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace('target="local"', 'target="remote"'))

    def test_rejects_unapproved_decorator(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace('@local.model("default")',
                                          '@local.model("default")\n@evil()'))

    def test_rejects_model_id_mismatch(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace('local.load("default")',
                                          'local.load("other")'))

    def test_rejects_non_awaited_generation(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace("return await model.generate(prompt)",
                                          "return model.generate(prompt)"))

    def test_rejects_extra_method_statement(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace('model = await local.load("default")',
                                          'print(prompt)\n        model = await local.load("default")'))

    def test_rejects_syntax_error(self):
        with self.assertRaises(PythonFrontendError):
            compile_source("class :")

    def test_rejects_extra_decorator_keyword(self):
        with self.assertRaises(PythonFrontendError):
            compile_source(SOURCE.replace('@runtime(target="local")',
                                          '@runtime(target="local", debug=True)'))


if __name__ == "__main__":
    unittest.main()
