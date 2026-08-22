import ast
import asyncio
import contextlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from typing import AsyncIterator


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "jarvis/app/main.py"


class FakeResponse:
    is_error = False

    async def aiter_bytes(self):
        yield b"ID3-"
        yield b"elevenlabs-audio"

    async def aread(self):
        return b""

    async def aclose(self):
        pass


class FakeClient:
    last_call = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def build_request(self, method, url, **kwargs):
        FakeClient.last_call = (method, url, kwargs)
        return (method, url, kwargs)

    async def send(self, request, stream=False):
        FakeClient.last_stream = stream
        return FakeResponse()

    async def aclose(self):
        pass


class FakeHttpx:
    AsyncClient = FakeClient
    HTTPError = RuntimeError

    class Timeout:
        def __init__(self, *args, **kwargs):
            pass


class FakeFastApiResponse:
    def __init__(self, content, media_type, headers):
        self.body = content
        self.media_type = media_type
        self.headers = {key.lower(): value for key, value in headers.items()}


class FakeStreamingResponse(FakeFastApiResponse):
    def __init__(self, content, media_type, headers):
        super().__init__(b"", media_type, headers)
        self.body_iterator = content


class FakeHttpException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


def load_generate_speech():
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    selected = [
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "generate_speech"
    ]
    selected[0].decorator_list = []
    namespace = {
        "contextlib": contextlib,
        "httpx": FakeHttpx,
        "SpeechRequest": object,
        "Response": FakeFastApiResponse,
        "StreamingResponse": FakeStreamingResponse,
        "AsyncIterator": AsyncIterator,
        "HTTPException": FakeHttpException,
        "SPEECH_PROVIDER": "openai",
        "SPEECH_FALLBACK_TO_OPENAI": True,
        "ELEVENLABS_API_KEY": "secret-test-key",
        "ELEVENLABS_VOICE_ID": "voice-test-id",
        "ELEVENLABS_VOICE_NAME": "Workshop Jarvis",
        "ELEVENLABS_MODEL_ID": "eleven_flash_v2_5",
        "ELEVENLABS_SPEECH_URL": "https://api.elevenlabs.io/v1/text-to-speech",
        "OPENAI_API_KEY": "openai-test-key",
        "OPENAI_TTS_MODEL": "gpt-4o-mini-tts",
        "OPENAI_SPEECH_URL": "https://api.openai.com/v1/audio/speech",
        "TTS_VOICES": {"cedar"},
        "openai_error_message": lambda response: "test error",
        "load_elevenlabs_voice_settings": lambda: {
            "stability": 0.42,
            "similarity": 0.88,
            "style": 0.23,
            "speed": 1.05,
        },
        "load_preferences": lambda: {
            "elevenlabs_model": "eleven_flash_v2_5",
            "elevenlabs_speaker_boost": True,
        },
        "apply_pronunciation_dictionary": lambda text: text,
    }
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(MAIN_PATH), "exec"), namespace)
    return namespace["generate_speech"]


class ElevenLabsSpeechTests(unittest.TestCase):
    def test_elevenlabs_request_and_audio_response(self):
        generate_speech = load_generate_speech()
        request = SimpleNamespace(
            text="Workshop bench is on.",
            provider="elevenlabs",
            voice="__elevenlabs__",
        )
        response = asyncio.run(generate_speech(request))

        method, url, kwargs = FakeClient.last_call
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://api.elevenlabs.io/v1/text-to-speech/voice-test-id/stream")
        self.assertTrue(FakeClient.last_stream)
        self.assertEqual(kwargs["headers"]["xi-api-key"], "secret-test-key")
        self.assertEqual(kwargs["params"]["output_format"], "mp3_22050_32")
        self.assertEqual(kwargs["json"]["text"], "Workshop bench is on.")
        self.assertEqual(
            kwargs["json"]["voice_settings"],
            {
                "stability": 0.42,
                "similarity_boost": 0.88,
                "style": 0.23,
                "use_speaker_boost": True,
                "speed": 1.05,
            },
        )
        async def collect_audio():
            return b"".join([chunk async for chunk in response.body_iterator])
        self.assertEqual(asyncio.run(collect_audio()), b"ID3-elevenlabs-audio")
        self.assertEqual(response.media_type, "audio/mpeg")
        self.assertEqual(response.headers["x-zbrano-speech-provider"], "elevenlabs")


if __name__ == "__main__":
    unittest.main()
