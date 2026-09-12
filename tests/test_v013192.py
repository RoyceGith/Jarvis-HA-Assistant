import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
RUN = (ROOT / "zbrano/run.sh").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
RUNTIME = (ROOT / "zbrano/app/services/agent_runtime.py").read_text(encoding="utf-8")
RESPONSES = (ROOT / "zbrano/app/services/openai_responses.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/zbrano/CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class BringYourOwnAiReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.231"', CONFIG)
        self.assertIn('version="0.13.231"', MAIN)
        self.assertIn("HUD 0.13.231", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.231")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.230")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.231"))

    def test_home_assistant_configuration_protects_provider_keys(self):
        self.assertIn('chat_provider: "openai"', CONFIG)
        self.assertIn('chat_provider: "list(openai|openrouter)"', CONFIG)
        self.assertIn('openrouter_api_key: "password"', CONFIG)
        self.assertIn('openrouter_model: "openai/gpt-5-mini"', CONFIG)
        for variable in ("CHAT_PROVIDER", "OPENROUTER_API_KEY", "OPENROUTER_MODEL"):
            self.assertIn(f"export {variable}=", RUN)

    def test_active_provider_drives_responses_and_model_discovery(self):
        self.assertIn('AGENT_RESPONSES_URL = "https://openrouter.ai/api/v1/responses"', MAIN)
        self.assertIn('AGENT_MODELS_URL = "https://openrouter.ai/api/v1/models"', MAIN)
        self.assertIn("api_key=AGENT_API_KEY", MAIN)
        self.assertIn("responses_url=AGENT_RESPONSES_URL", MAIN)
        self.assertIn("provider=AGENT_PROVIDER_LABEL", MAIN)
        self.assertIn("MODEL_PROVIDER", RESPONSES)
        self.assertIn('MODEL_PROVIDER == "openrouter" and "/" not in model', RUNTIME)

    def test_non_openai_sessions_use_only_verified_tools(self):
        self.assertIn('tools = [tool for tool in tools if tool.get("type") == "function"]', MAIN)
        self.assertIn('return search_mode if CHAT_PROVIDER == "openai" else "off"', MAIN)
        self.assertIn("search_mode = agent_search_mode(search_mode)", MAIN)
        self.assertIn("agentModel.replaceChildren()", CORE)
        self.assertIn("data.selected_model || preferences?.agent_model", CORE)
        self.assertIn("local device tools available; web and remote plugins require OpenAI", CORE)


if __name__ == "__main__":
    unittest.main()
