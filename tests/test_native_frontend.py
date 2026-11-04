import unittest

from lmlm_frontend.native import (
    NativeSemanticError,
    NativeSyntaxError,
    compile_source,
    lower,
    parse,
)


SOURCE = """module LMLM.Assistant;

import LMLM.Models.Local;
import LMLM.Runtime;

@runtime(target: "local")
@model(provider: "local", name: "default")
@security(policy: "restricted")
@capability(value: ["inference"])
@verify(mode: "required")

model Assistant {
    execute(input: Text) -> Response {
        return model.generate(input);
    }
}
"""

EXPECTED = {
    "operation": "model.generate",
    "provider": "local",
    "model": "default",
    "input": {"type": "text", "source": "user_input"},
    "permissions": ["inference"],
    "verification": {"required": True},
}


class NativeFrontendTests(unittest.TestCase):
    def test_parse_program(self):
        program = parse(SOURCE)
        self.assertEqual(program.module, "LMLM.Assistant")
        self.assertEqual(program.imports, ("LMLM.Models.Local", "LMLM.Runtime"))
        self.assertEqual(program.model_name, "Assistant")
        self.assertEqual(program.parameter_name, "input")

    def test_compile_to_shared_ir(self):
        self.assertEqual(compile_source(SOURCE), EXPECTED)

    def test_lower_existing_ast(self):
        self.assertEqual(lower(parse(SOURCE)), EXPECTED)

    def test_rejects_unexpected_character(self):
        with self.assertRaises(NativeSyntaxError):
            parse(SOURCE + "$")

    def test_rejects_unsupported_method_body(self):
        with self.assertRaises(NativeSyntaxError):
            parse(SOURCE.replace("model.generate(input)", "system.shell(input)"))

    def test_rejects_trailing_source(self):
        with self.assertRaises(NativeSyntaxError):
            parse(SOURCE + "run();")

    def test_requires_security_annotations(self):
        with self.assertRaises(NativeSemanticError):
            compile_source(SOURCE.replace('@security(policy: "restricted")\n', ""))

    def test_rejects_unapproved_capability(self):
        with self.assertRaises(NativeSemanticError):
            compile_source(SOURCE.replace('["inference"]', '["inference", "filesystem"]'))

    def test_rejects_unknown_annotation(self):
        with self.assertRaises(NativeSemanticError):
            compile_source(SOURCE.replace('@runtime', '@shell'))

    def test_rejects_non_local_runtime(self):
        with self.assertRaises(NativeSemanticError):
            compile_source(SOURCE.replace('target: "local"', 'target: "remote"'))


if __name__ == "__main__":
    unittest.main()
