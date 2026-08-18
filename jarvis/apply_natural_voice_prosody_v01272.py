import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.72 expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.72 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    old_chunker = r'''function extractSpeakableChunks(buffer, final = false) {
  const chunks = [];
  let remaining = buffer;
  const sentencePattern = /^([\s\S]{12,220}?[.!?](?:\s+|$))/;
  while (true) {
    const match = remaining.match(sentencePattern);
    if (!match) break;
    chunks.push(match[1].trim());
    remaining = remaining.slice(match[1].length);
  }
  if (final && remaining.trim()) {
    chunks.push(remaining.trim());
    remaining = "";
  } else if (!chunks.length && remaining.length >= 56) {
    const phraseLimit = Math.min(88, remaining.length);
    const splitAt = Math.max(
      remaining.lastIndexOf(", ", phraseLimit),
      remaining.lastIndexOf("; ", phraseLimit),
      remaining.lastIndexOf(": ", phraseLimit),
      remaining.lastIndexOf(" ", phraseLimit)
    );
    if (splitAt >= 32) {
      chunks.push(remaining.slice(0, splitAt).trim());
      remaining = remaining.slice(splitAt);
    }
  } else if (remaining.length > 220) {
    const splitAt = Math.max(
      remaining.lastIndexOf(", ", 170),
      remaining.lastIndexOf("; ", 170),
      remaining.lastIndexOf(" ", 170)
    );
    if (splitAt > 80) {
      chunks.push(remaining.slice(0, splitAt).trim());
      remaining = remaining.slice(splitAt);
    }
  }
  return {chunks, remaining};
}
'''
    new_chunker = r'''function extractSpeakableChunks(buffer, final = false) {
  const chunks = [];
  let remaining = buffer;
  // TTS treats every request boundary like punctuation. Keep requests on real
  // sentence or clause boundaries so streamed speech does not invent pauses.
  const sentencePattern = /^([\s\S]{36,320}?[.!?](?:["')\]]?)(?:\s+|$))/;
  while (true) {
    const match = remaining.match(sentencePattern);
    if (!match) break;
    chunks.push(match[1].trim());
    remaining = remaining.slice(match[0].length);
  }
  if (final && remaining.trim()) {
    chunks.push(remaining.trim());
    remaining = "";
  } else if (!chunks.length && remaining.length >= 120) {
    const clauseLimit = Math.min(200, remaining.length);
    const splitAt = Math.max(
      remaining.lastIndexOf(", ", clauseLimit),
      remaining.lastIndexOf("; ", clauseLimit),
      remaining.lastIndexOf(": ", clauseLimit),
      remaining.lastIndexOf(" — ", clauseLimit),
      remaining.lastIndexOf(" – ", clauseLimit)
    );
    if (splitAt >= 72) {
      const delimiterLength = remaining.startsWith(" — ", splitAt) || remaining.startsWith(" – ", splitAt) ? 2 : 1;
      chunks.push(remaining.slice(0, splitAt + delimiterLength).trim());
      remaining = remaining.slice(splitAt + delimiterLength).trimStart();
    }
  }
  // Preserve live playback for a rare, very long sentence with no natural
  // boundary. This is intentionally much later than the old 56-character cut.
  if (!chunks.length && !final && remaining.length > 360) {
    const splitAt = remaining.lastIndexOf(" ", 300);
    if (splitAt >= 220) {
      chunks.push(remaining.slice(0, splitAt).trim());
      remaining = remaining.slice(splitAt).trimStart();
    }
  }
  return {chunks, remaining};
}
'''
    frontend = replace_once(frontend, old_chunker, new_chunker, "natural speech chunker")

    frontend = replace_once(
        frontend,
        r'''    .replace(/`([^`]+)`/g, "$1")
    .trim();''',
        r'''    .replace(/`([^`]+)`/g, "$1")
    .replace(/\s*\n+\s*/g, " ")
    .replace(/[ \t]{2,}/g, " ")
    .trim();''',
        "speech whitespace normalization",
    )

    backend = backend.replace('version="0.12.71"', 'version="0.12.72"')
    backend = backend.replace('"version": "0.12.71"', '"version": "0.12.72"')
    backend = backend.replace(
        '"X-ZBRANO-Frontend-Version": "0.12.71"',
        '"X-ZBRANO-Frontend-Version": "0.12.72"',
    )
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.71"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.72"',
    )
    frontend = frontend.replace("HUD 0.12.71", "HUD 0.12.72")

    for marker in (
        "TTS treats every request boundary like punctuation",
        "{36,320}",
        "remaining.length >= 120",
        'remaining.lastIndexOf(", ", clauseLimit)',
        "splitAt + delimiterLength",
        "remaining.length > 360",
        '.replace(/\\s*\\n+\\s*/g, " ")',
        "speechPrefetch = {text, blob: fetchSpeechBlob(text, force)}",
        "speech.chunks.forEach(chunk => queueSpeech(chunk));",
        "HUD 0.12.72",
    ):
        require(frontend, marker, marker)
    require(backend, 'version="0.12.72"', "backend version")

    if 'remaining.lastIndexOf(" ", phraseLimit)' in frontend or "remaining.length >= 56" in frontend:
        raise RuntimeError("ZBRANO v0.12.72 retained the artificial early word-boundary split")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
