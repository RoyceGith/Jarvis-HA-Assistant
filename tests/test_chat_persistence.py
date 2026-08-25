import ast
from collections import deque
import json
from pathlib import Path
import tempfile
import time
import unittest
from typing import Any
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "jarvis/app/main.py"
CONVERSATIONS_PATH = ROOT / "jarvis/app/domains/conversations.py"


def load_chat_functions(storage_path: Path):
    source = CONVERSATIONS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        "chat_title",
        "persist_chat_sessions",
        "load_chat_sessions",
        "get_chat_history",
        "is_internal_chat_session",
        "append_chat_message",
        "clear_chat_history",
    }
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {
        "Any": Any,
        "Path": Path,
        "json": json,
        "time": time,
        "deque": deque,
        "CHAT_HISTORY_MAX_MESSAGES": 200,
        "CHAT_SESSIONS_MAX": 100,
        "INTERNAL_CHAT_SESSION_PREFIXES": ("zbrano-diagnostic-", "zbrano-playwright-"),
        "CHAT_SESSIONS": {},
        "CHAT_SESSION_ORDER": deque(maxlen=100),
        "CHAT_SESSION_META": {},
        "LAST_ENTITY_BY_SESSION": {},
        "CHAT_STORAGE_PATH": storage_path,
        "CHAT_UPLOAD_ROOT": storage_path.parent / "uploads",
        "_attachment_message_parts": lambda content: (content, []),
        "schedule_fast_memory_extraction": lambda *args: None,
        "re": re,
        "shutil": shutil,
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(CONVERSATIONS_PATH), "exec"), namespace)
    return namespace


class ChatPersistenceTests(unittest.TestCase):
    def test_conversation_round_trip_and_delete(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage_path = Path(temporary) / "data/chat_sessions.json"
            namespace = load_chat_functions(storage_path)
            namespace["append_chat_message"]("session-1", "user", "Turn on workshop bench")
            namespace["append_chat_message"]("session-1", "assistant", "Workshop bench is on.")

            self.assertTrue(storage_path.is_file())
            namespace["CHAT_SESSIONS"].clear()
            namespace["CHAT_SESSION_ORDER"].clear()
            namespace["CHAT_SESSION_META"].clear()
            namespace["load_chat_sessions"]()

            restored = list(namespace["CHAT_SESSIONS"]["session-1"])
            self.assertEqual(restored[0]["content"], "Turn on workshop bench")
            self.assertEqual(restored[1]["content"], "Workshop bench is on.")
            self.assertEqual(namespace["CHAT_SESSION_META"]["session-1"]["title"], "Turn on workshop bench")

            namespace["clear_chat_history"]("session-1")
            payload = json.loads(storage_path.read_text(encoding="utf-8"))
            self.assertNotIn("session-1", payload["sessions"])


if __name__ == "__main__":
    unittest.main()
