import unittest

from jarvis.app.services.workshop_cost_guard import (
    MAX_SINGLE_TOOL_OUTPUT_CHARS,
    bound_workshop_result,
    is_workshop_memory_intent,
    new_workshop_budget,
    note_workshop_write_completed,
    record_workshop_response_usage,
    reject_oversized_workshop_batch,
    reserve_workshop_call,
    workshop_budget_reason,
    workshop_response_controls,
    workshop_tools,
)


class WorkshopCostGuardTests(unittest.TestCase):
    def test_explicit_workshop_requests_are_scoped_to_workshop_tools(self):
        self.assertTrue(is_workshop_memory_intent("Update my Workshop Memory project note"))
        self.assertFalse(is_workshop_memory_intent("Turn on the workshop light"))
        selected = workshop_tools(
            [
                {"name": "list_projects"},
                {"name": "turn_on_home_assistant_entity"},
            ],
            [{"name": "write_project_note"}],
        )
        self.assertEqual(
            [tool["name"] for tool in selected],
            ["list_projects", "write_project_note"],
        )

    def test_workshop_requests_disable_parallel_calls_and_bound_output(self):
        self.assertEqual(
            workshop_response_controls(True),
            {"parallel_tool_calls": False, "max_output_tokens": 8192},
        )
        self.assertEqual(workshop_response_controls(False), {})

    def test_usage_accounting_stops_before_another_expensive_continuation(self):
        budget = new_workshop_budget("read Workshop Memory")
        reason = record_workshop_response_usage(
            budget,
            {
                "usage": {
                    "input_tokens": 80_000,
                    "output_tokens": 10,
                    "input_tokens_details": {
                        "cached_tokens": 20_000,
                        "cache_write_tokens": 50_000,
                    },
                }
            },
        )
        self.assertIn("input-token", reason)
        self.assertEqual(workshop_budget_reason(budget), reason)

    def test_duplicate_and_per_response_calls_are_not_executed(self):
        budget = new_workshop_budget("update Workshop Memory")
        call = {"name": "read_project_note", "arguments": '{"path":"A.md"}'}
        self.assertIsNone(reserve_workshop_call(budget, call, 0))
        self.assertIn("duplicate", reserve_workshop_call(budget, call, 1))
        note_workshop_write_completed(budget)
        self.assertIsNone(reserve_workshop_call(budget, call, 0))
        distinct = {"name": "list_projects", "arguments": "{}"}
        batch_budget = new_workshop_budget("update Workshop Memory")
        self.assertIn(
            "too many",
            reject_oversized_workshop_batch(batch_budget, [distinct] * 4),
        )
        self.assertIn("too many", reserve_workshop_call(batch_budget, distinct, 0))

    def test_oversized_read_is_never_returned_to_the_model(self):
        budget = new_workshop_budget("read Workshop Memory note")
        bounded = bound_workshop_result(
            budget,
            {"content": "x" * (MAX_SINGLE_TOOL_OUTPUT_CHARS + 1)},
            permission="read_only",
        )
        self.assertIn("error", bounded)
        self.assertIn("oversized result was not sent", bounded["error"])

    def test_large_write_echo_is_compacted(self):
        budget = new_workshop_budget("write Workshop Memory note")
        bounded = bound_workshop_result(
            budget,
            {"status": "written", "content": "x" * 10_000},
            permission="write",
        )
        self.assertEqual(bounded["status"], "written")
        self.assertIn("written content omitted", bounded["content"])


if __name__ == "__main__":
    unittest.main()
