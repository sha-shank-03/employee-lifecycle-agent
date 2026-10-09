"""Pure synthetic provider tests. No HTTP server, socket, Java or model is started."""
import copy
from contextlib import redirect_stderr
import io
import unittest
from unittest.mock import patch
from agent import cli
from agent.bridge import ROOT
from agent.loop import run_loop
from agent.protocol import Clarification, FinalDraft, ToolCall, TOOLS
from agent.replay import ReplayProvider
from agent.responses import (HttpReply, HttpTransport, ProviderError, ResponsesProvider,
                             canonical, live_provider, parse_response, tool_definitions)
from tests.test_unit import FakeBridge

REQUEST = {"employee_id": "E-REPLAY", "intent": "offboard", "text": "Fictional protocol inspection only."}


def function_response(name="inspect_employee", arguments=None, *, number=1):
    return {"id": f"resp_{number}", "status": "completed", "output": [
        {"type": "function_call", "id": f"fc_{number}", "call_id": f"call_{number}", "name": name,
         "arguments": canonical(arguments or {"employee_id": "E-REPLAY"}).decode()}]}


def message_response(text="Operator review required.", *, refusal=False, number=2):
    return {"id": f"resp_{number}", "status": "completed", "output": [
        {"type": "message", "id": f"msg_{number}", "role": "assistant", "status": "completed",
         "content": [{"type": "refusal" if refusal else "output_text", "refusal" if refusal else "text": text}]}]}


class QueueTransport:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def __call__(self, body):
        self.requests.append(copy.deepcopy(__import__("json").loads(body)))
        return HttpReply(200, canonical(next(self.responses)))


class ProviderUnitTests(unittest.TestCase):
    def parse(self, response):
        return parse_response(HttpReply(200, canonical(response)), set(), set())[0]

    def test_tools_exclude_operator_authority_and_require_exact_string_fields(self):
        definitions = tool_definitions()
        self.assertEqual({d["name"] for d in definitions}, set(TOOLS))
        for definition in definitions:
            schema = definition["parameters"]
            self.assertTrue(definition["strict"])
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(set(schema["required"]), TOOLS[definition["name"]])
            self.assertTrue(all(p == {"type": "string"} for p in schema["properties"].values()))

    def test_credentials_alone_do_not_enable_live_provider(self):
        with patch.dict("os.environ", {"LIFECYCLE_OPENAI_API_KEY": "local-test-value"}), \
                self.assertRaises(ProviderError):
            live_provider("explicit-model", False)

    def test_model_is_explicit(self):
        with self.assertRaises(ProviderError):
            live_provider(None, True)

    def test_live_endpoint_cannot_be_replaced(self):
        with self.assertRaises(ProviderError):
            HttpTransport("https://example.invalid/v1/responses", allow_live=True, token="local-test-value")

    def test_loopback_cannot_carry_credentials(self):
        with self.assertRaises(ProviderError):
            HttpTransport("http://127.0.0.1:12345/v1/responses", loopback_test=True, token="local-test-value")

    def test_test_route_cannot_resolve_a_hostname(self):
        with self.assertRaises(ProviderError):
            HttpTransport("http://localhost:12345/v1/responses", loopback_test=True)

    def test_valid_function_call_is_typed(self):
        self.assertEqual(self.parse(function_response()), ToolCall("inspect_employee", {"employee_id": "E-REPLAY"}))

    def test_duplicate_json_argument_rejected(self):
        value = function_response()
        value["output"][0]["arguments"] = '{"employee_id":"E-REPLAY","employee_id":"other"}'
        with self.assertRaisesRegex(ProviderError, "finite tool"):
            self.parse(value)

    def test_extra_call_field_rejected(self):
        value = function_response()
        value["output"][0]["approval"] = "invented"
        with self.assertRaises(ProviderError):
            self.parse(value)

    def test_operator_tool_rejected(self):
        with self.assertRaises(ProviderError):
            self.parse(function_response("approve", {"digest": "invented"}))

    def test_extra_mutation_argument_rejected(self):
        with self.assertRaises(ProviderError):
            self.parse(function_response("execute_step", {"workflow_id": "w", "step_id": "enable_login", "grants": "admin"}))

    def test_multiple_calls_rejected_even_when_parallel_requested_false(self):
        value = function_response()
        value["output"].extend(function_response(number=2)["output"])
        with self.assertRaisesRegex(ProviderError, "exactly one"):
            self.parse(value)

    def test_call_and_final_together_rejected(self):
        value = function_response()
        value["output"].extend(message_response()["output"])
        with self.assertRaises(ProviderError):
            self.parse(value)

    def test_empty_output_rejected(self):
        with self.assertRaises(ProviderError):
            self.parse({"id": "r", "status": "completed", "output": []})

    def test_incomplete_output_rejected(self):
        value = function_response()
        value["status"] = "incomplete"
        with self.assertRaises(ProviderError):
            self.parse(value)

    def test_refusal_is_a_safe_typed_clarification(self):
        self.assertIsInstance(self.parse(message_response("Refused.", refusal=True)), Clarification)

    def test_claimed_success_is_only_a_draft(self):
        self.assertEqual(self.parse(message_response("Everything completed.")), FinalDraft("Everything completed."))

    def test_missing_call_id_rejected(self):
        value = function_response()
        del value["output"][0]["call_id"]
        with self.assertRaises(ProviderError):
            self.parse(value)

    def test_reused_response_id_rejected(self):
        with self.assertRaisesRegex(ProviderError, "response ID"):
            parse_response(HttpReply(200, canonical(function_response())), {"resp_1"}, set())

    def test_reused_call_id_rejected(self):
        with self.assertRaisesRegex(ProviderError, "call ID"):
            parse_response(HttpReply(200, canonical(function_response())), set(), {"call_1"})

    def test_unknown_output_item_rejected(self):
        with self.assertRaises(ProviderError):
            self.parse({"id": "r", "status": "completed", "output": [{"id": "x", "type": "shell_call"}]})

    def test_negative_usage_rejected(self):
        value = function_response()
        value["usage"] = {"input_tokens": -1}
        with self.assertRaises(ProviderError):
            self.parse(value)

    def test_non_json_and_oversized_bodies_rejected(self):
        for body in (b"not JSON", b"x" * 65_537):
            with self.subTest(size=len(body)), self.assertRaises(ProviderError):
                parse_response(HttpReply(200, body), set(), set())

    def test_http_error_body_is_not_exposed(self):
        with self.assertRaises(ProviderError) as caught:
            parse_response(HttpReply(429, b"sensitive diagnostic"), set(), set())
        self.assertNotIn("sensitive", str(caught.exception))

    def test_call_output_correlates_and_reasoning_items_are_preserved(self):
        first = function_response()
        reasoning = {"id": "rs_1", "type": "reasoning", "summary": [], "encrypted_content": "synthetic-opaque"}
        first["output"].insert(0, reasoning)
        transport = QueueTransport(first, message_response())
        provider = ResponsesProvider("synthetic-protocol-model", transport)
        call = provider.next_turn(REQUEST, [])
        result = {"code": "OK", "workflow_id": "wf-REPLAY-1", "administrative_status": "RECEIVED"}
        provider.next_turn(REQUEST, [{"tool": call.name, "arguments": call.arguments, "result": result}])
        sent = transport.requests[1]
        self.assertFalse(sent["parallel_tool_calls"])
        self.assertFalse(sent["store"])
        self.assertIn(reasoning, sent["input"])
        self.assertEqual(sent["input"][-1], {"type": "function_call_output", "call_id": "call_1", "output": canonical(result).decode()})
        self.assertTrue(all(t["validated"] for t in provider.trace))

    def test_wrong_observation_never_reaches_transport(self):
        transport = QueueTransport(function_response(), message_response())
        provider = ResponsesProvider("synthetic-protocol-model", transport)
        provider.next_turn(REQUEST, [])
        with self.assertRaisesRegex(ProviderError, "pending call"):
            provider.next_turn(REQUEST, [{"tool": "execute_step", "arguments": {}, "result": {"code": "OK"}}])
        self.assertEqual(len(transport.requests), 1)

    def test_labels_and_control_are_rejected_at_provider_boundary(self):
        transport = QueueTransport(function_response())
        with self.assertRaisesRegex(ProviderError, "labels"):
            ResponsesProvider("synthetic-protocol-model", transport).next_turn({**REQUEST, "expected": {}}, [])
        self.assertEqual(transport.requests, [])

    def test_failed_validation_retains_request_and_response_hashes(self):
        provider = ResponsesProvider("synthetic-protocol-model", QueueTransport({"id": "r", "status": "incomplete", "output": []}))
        with self.assertRaises(ProviderError):
            provider.next_turn(REQUEST, [])
        self.assertFalse(provider.trace[0]["validated"])
        self.assertEqual(len(provider.trace[0]["response_sha256"]), 64)

    def test_synthetic_replay_matches_context_and_finishes_without_model(self):
        provider = ReplayProvider(ROOT / "fixtures/providers/synthetic-inspect.json")
        bridge = FakeBridge({"code": "OK", "workflow_id": "wf-REPLAY-1", "administrative_status": "RECEIVED"})
        result = run_loop(provider, bridge, REQUEST)
        self.assertEqual(provider.position, 2)
        self.assertEqual(len(bridge.calls), 1)
        self.assertEqual(result["provider"], "synthetic-replay")
        self.assertEqual(result["draft"], "Operator review required.")

    def test_replay_cannot_select_by_fixture_id_or_ignore_changed_context(self):
        provider = ReplayProvider(ROOT / "fixtures/providers/synthetic-inspect.json")
        with self.assertRaisesRegex(ProviderError, "context mismatch"):
            provider.next_turn({**REQUEST, "employee_id": "another"}, [])
        self.assertEqual(provider.position, 0)

    def test_cli_live_flags_fail_before_java_or_file_reads(self):
        with patch("agent.cli.JavaBridge") as bridge, redirect_stderr(io.StringIO()):
            code = cli.main(["submit", "--run-dir", "unused", "--request", "unused", "--provider", "responses"])
        self.assertEqual(code, 1)
        bridge.assert_not_called()


if __name__ == "__main__":
    unittest.main()
