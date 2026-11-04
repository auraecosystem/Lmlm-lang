import asyncio
import unittest
from lmlm_frontend.hybrid import compile_source
from lmlm_runtime import AuthorizationError, ExecutionError, Policy, Principal, Runtime, RuntimeConfig

IR = {"operation":"model.generate","provider":"local","model":"default",
      "input":{"type":"text","source":"user_input"},"permissions":["inference"],
      "verification":{"required":True}}

class Adapter:
    def __init__(self): self.calls = 0
    async def generate(self, model, prompt):
        self.calls += 1
        return f"{model}:{prompt}"

class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_authorized_execution_and_verification(self):
        adapter = Adapter()
        runtime = Runtime(adapters={"local":adapter}, verifier=lambda text: text.endswith(":hello"))
        principal = Principal("test-user", frozenset({"inference"}), frozenset({"local"}), frozenset({"default"}))
        result = await runtime.execute(IR, principal, "hello")
        self.assertEqual(result.output, "default:hello")
        self.assertEqual(adapter.calls, 1)

    async def test_denial_happens_before_adapter(self):
        adapter = Adapter()
        runtime = Runtime(adapters={"local":adapter}, verifier=lambda _: True)
        principal = Principal("untrusted", frozenset(), frozenset({"local"}))
        with self.assertRaises(AuthorizationError):
            await runtime.execute(IR, principal, "hello")
        self.assertEqual(adapter.calls, 0)

    async def test_verification_is_mandatory(self):
        runtime = Runtime(adapters={"local":Adapter()})
        principal = Principal("test", frozenset({"inference"}))
        with self.assertRaises(ExecutionError):
            await runtime.execute(IR, principal, "hello")

    async def test_timeout(self):
        class Slow:
            async def generate(self, model, prompt):
                await asyncio.sleep(0.1)
                return "late"
        runtime = Runtime(config=RuntimeConfig(timeout_seconds=0.01), adapters={"local":Slow()}, verifier=lambda _: True)
        principal = Principal("test", frozenset({"inference"}))
        with self.assertRaises(ExecutionError):
            await runtime.execute(IR, principal, "hello")

if __name__ == "__main__":
    unittest.main()
