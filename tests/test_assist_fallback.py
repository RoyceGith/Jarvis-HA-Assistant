import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "distribution/public-repository/custom_components/zbrano"
FLOW = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
CONVERSATION = (COMPONENT / "conversation.py").read_text(encoding="utf-8")
API = (COMPONENT / "api.py").read_text(encoding="utf-8")


class AssistOfflineFallbackTests(unittest.TestCase):
    def test_fallback_agent_is_selected_during_setup(self):
        self.assertIn("ConversationAgentSelector", FLOW)
        self.assertIn("CONF_FALLBACK_AGENT", FLOW)
        self.assertIn("HOME_ASSISTANT_AGENT", FLOW)
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.1.1")

    def test_only_confirmed_preflight_failure_uses_fallback(self):
        self.assertLess(
            CONVERSATION.index("health = await self._api.health()"),
            CONVERSATION.index("payload = await self._api.converse("),
        )
        self.assertIn("return await self._async_fallback(user_input)", CONVERSATION)
        self.assertIn("conversation.async_converse(", CONVERSATION)
        self.assertIn("cannot be ZBRANO itself", CONVERSATION)
        self.assertIn("It was not repeated through the fallback assistant", CONVERSATION)
        self.assertIn("timeout=HEALTH_TIMEOUT", API)

    def test_every_translation_names_the_fallback_field(self):
        for language in ("en", "el", "it", "fr"):
            payload = json.loads(
                (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
            )
            steps = payload["config"]["step"]
            self.assertIn("fallback_agent", steps["user"]["data"])
            self.assertIn("fallback_agent", steps["reconfigure"]["data"])


if __name__ == "__main__":
    unittest.main()
