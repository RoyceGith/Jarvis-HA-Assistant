from pathlib import Path


ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app" / "static" / "index.html"
MAIN = ROOT / "app" / "main.py"


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Jarvis interface hotfix could not find: {label}")
    return text.replace(old, new, 1)


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    text = replace_required(
        text,
        '.message h3 { margin: .2rem 0 .45rem; color: var(--phosphor); font-size: .92rem; letter-spacing: 0; }',
        '.message h3 { margin: .3rem 0 .55rem; color: var(--phosphor); font-size: 1.08rem; font-weight: 800; line-height: 1.3; letter-spacing: .01em; }',
        "larger bold response headings",
    )

    text = replace_required(
        text,
        'const numbered = trimmed.match(/^\\d+[.)]\\s+(.+)$/);\n    if (numbered) {\n      openList("ol");\n      html.push(`<li>${renderInlineMarkdown(numbered[1])}</li>`);',
        'const numbered = trimmed.match(/^(\\d+)[.)]\\s+(.+)$/);\n    if (numbered) {\n      openList("ol");\n      html.push(`<li value="${Number(numbered[1])}">${renderInlineMarkdown(numbered[2])}</li>`);',
        "ordered-list numbering",
    )

    text = replace_required(
        text,
        'function addMessage(text, role) {',
        'function isNearMessagesBottom(threshold = 72) {\n  return messages.scrollHeight - messages.scrollTop - messages.clientHeight <= threshold;\n}\n\nfunction addMessage(text, role) {',
        "scroll position helper",
    )

    text = replace_required(
        text,
        '      const delta = eventData.text || "";\n      answer += delta;\n      speechBuffer += delta;\n      renderMessageContent(jarvisMessage, answer);\n      messages.scrollTop = messages.scrollHeight;',
        '      const followLatest = isNearMessagesBottom();\n      const delta = eventData.text || "";\n      answer += delta;\n      speechBuffer += delta;\n      renderMessageContent(jarvisMessage, answer);\n      if (followLatest) messages.scrollTop = messages.scrollHeight;',
        "user-controlled streaming scroll",
    )

    text = replace_required(
        text,
        'const sentencePattern = /^([\\s\\S]{24,240}?[.!?](?:\\s+|$))/;',
        'const sentencePattern = /^([\\s\\S]{12,160}?[.!?](?:\\s+|$))/;',
        "faster sentence speech chunks",
    )

    text = replace_required(
        text,
        '  } else if (remaining.length > 240) {\n    const splitAt = Math.max(\n      remaining.lastIndexOf(", ", 180),\n      remaining.lastIndexOf("; ", 180),\n      remaining.lastIndexOf(" ", 180)\n    );\n    if (splitAt > 80) {',
        '  } else if (remaining.length > 120) {\n    const splitAt = Math.max(\n      remaining.lastIndexOf(", ", 105),\n      remaining.lastIndexOf("; ", 105),\n      remaining.lastIndexOf(": ", 105),\n      remaining.lastIndexOf(" ", 105)\n    );\n    if (splitAt > 55) {',
        "early clause speech flush",
    )

    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace(
        '"output_format": "mp3_44100_128", "optimize_streaming_latency": "4"',
        '"output_format": "mp3_22050_32", "optimize_streaming_latency": "4"',
    )
    MAIN.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_index()
    patch_main()
