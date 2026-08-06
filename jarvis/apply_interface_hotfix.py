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
        ':root[data-theme="light"] {\n      color-scheme: light;\n      background: #edf1e8;\n      color: #17231d;\n      --phosphor: #42690f;\n      --phosphor-dim: #6e873f;\n      --cyan: #006779;\n      --cyan-dim: #4f8993;\n      --panel: rgba(248, 250, 244, .88);\n      --line: rgba(22, 82, 91, .27);\n      --surface: rgba(239,244,235,.9);\n      --surface-strong: rgba(250,252,247,.96);\n      --text-muted: #536b67;\n      --shadow: rgba(35,50,42,.18);\n      --node-core: 8, 12, 10;\n      --node-edge: 74, 108, 12;\n      --node-link: 55, 85, 15;\n    }',
        ':root[data-theme="light"] {\n      color-scheme: light;\n      background: #f7f8fa;\n      color: #172027;\n      --phosphor: #287052;\n      --phosphor-dim: #6d8d80;\n      --cyan: #006d82;\n      --cyan-dim: #6f9ca5;\n      --panel: rgba(255, 255, 255, .92);\n      --line: rgba(44, 76, 88, .20);\n      --surface: rgba(248, 250, 252, .94);\n      --surface-strong: rgba(255, 255, 255, .98);\n      --text-muted: #5f6d76;\n      --shadow: rgba(31, 42, 49, .14);\n      --node-core: 14, 20, 24;\n      --node-edge: 36, 118, 91;\n      --node-link: 55, 123, 104;\n    }',
        "neutral white light theme",
    )
    text = replace_required(
        text,
        ':root[data-theme="light"] body { background: radial-gradient(circle at 50% 38%, #fbfff2 0, #e9eee4 54%, #dce3da 100%); }',
        ':root[data-theme="light"] body { background: radial-gradient(circle at 50% 34%, #ffffff 0, #f5f7f9 56%, #e9edf1 100%); }',
        "white light background",
    )
    text = replace_required(
        text,
        '#brain-network { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; opacity: 1; filter: contrast(1.12) saturate(1.08); pointer-events: none; }',
        '#brain-network { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; opacity: .38; filter: contrast(1.02) saturate(.88); pointer-events: none; transition: opacity .65s ease, filter .65s ease; }\n    .core-stage.neuron-intense #brain-network { opacity: 1; filter: contrast(1.34) saturate(1.28) brightness(1.12); }\n    :root[data-theme="light"] .core-stage.neuron-intense #brain-network { opacity: .92; filter: contrast(1.28) saturate(1.12) brightness(.94); }',
        "dynamic neuron intensity",
    )
    text = replace_required(
        text,
        '.message h3 { margin: .2rem 0 .45rem; color: var(--phosphor); font-size: .92rem; letter-spacing: 0; }',
        '.message h2, .message h3, .message h4 { color: var(--phosphor); font-weight: 800; line-height: 1.28; letter-spacing: .01em; }\n    .message h2 { margin: .65rem 0 .6rem; font-size: 1.28rem; }\n    .message h3 { margin: .55rem 0 .5rem; font-size: 1.12rem; }\n    .message h4 { margin: .45rem 0 .42rem; font-size: 1.02rem; }\n    .message > h2:first-child, .message > h3:first-child, .message > h4:first-child { margin-top: .15rem; }',
        "response heading hierarchy",
    )
    text = replace_required(text, 'Workshop Intelligence Interface · HUD 0.8.5', 'Workshop Intelligence Interface · HUD 0.8.9', "HUD version")
    text = replace_required(
        text,
        'const numbered = trimmed.match(/^\\d+[.)]\\s+(.+)$/);\n    if (numbered) {\n      openList("ol");\n      html.push(`<li>${renderInlineMarkdown(numbered[1])}</li>`);',
        'const numbered = trimmed.match(/^(\\d+)[.)]\\s+(.+)$/);\n    if (numbered) {\n      openList("ol");\n      html.push(`<li value="${Number(numbered[1])}">${renderInlineMarkdown(numbered[2])}</li>`);',
        "ordered-list numbering",
    )
    text = replace_required(
        text,
        '    const heading = trimmed.match(/^#{1,3}\\s+(.+)$/);\n    if (heading) {\n      closeParagraph();\n      closeList();\n      html.push(`<h3>${renderInlineMarkdown(heading[1])}</h3>`);\n      continue;\n    }',
        '    const heading = trimmed.match(/^(#{1,3})\\s+(.+)$/);\n    if (heading) {\n      closeParagraph();\n      closeList();\n      const headingTag = heading[1].length === 1 ? "h2" : heading[1].length === 2 ? "h3" : "h4";\n      html.push(`<${headingTag}>${renderInlineMarkdown(heading[2])}</${headingTag}>`);\n      continue;\n    }\n\n    const standaloneBold = trimmed.match(/^\\*\\*([^*]+)\\*\\*$/);\n    if (standaloneBold) {\n      closeParagraph();\n      closeList();\n      html.push(`<h4>${renderInlineMarkdown(standaloneBold[1])}</h4>`);\n      continue;\n    }',
        "markdown title and subtitle rendering",
    )
    text = replace_required(
        text,
        '  for (const line of lines) {\n    const trimmed = line.trim();',
        '  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {\n    const line = lines[lineIndex];\n    const trimmed = line.trim();',
        "indexed markdown line loop",
    )
    text = replace_required(
        text,
        '    const numbered = trimmed.match(/^(\\d+)[.)]\\s+(.+)$/);\n    if (numbered) {\n      openList("ol");\n      html.push(`<li value="${Number(numbered[1])}">${renderInlineMarkdown(numbered[2])}</li>`);\n      continue;\n    }',
        '    const numbered = trimmed.match(/^(\\d+)[.)]\\s+(.+)$/);\n    if (numbered) {\n      let nextContent = "";\n      for (let nextIndex = lineIndex + 1; nextIndex < lines.length; nextIndex += 1) {\n        nextContent = lines[nextIndex].trim();\n        if (nextContent) break;\n      }\n      const followedByDetails = /^[-*]\\s+/.test(nextContent);\n      const looksLikeSectionTitle = followedByDetails && numbered[2].length <= 120;\n      if (looksLikeSectionTitle) {\n        closeParagraph();\n        closeList();\n        html.push(`<h3>${renderInlineMarkdown(`${numbered[1]}. ${numbered[2]}`)}</h3>`);\n      } else {\n        openList("ol");\n        html.push(`<li value="${Number(numbered[1])}">${renderInlineMarkdown(numbered[2])}</li>`);\n      }\n      continue;\n    }',
        "numbered section heading detection",
    )
    text = replace_required(
        text,
        'function addMessage(text, role) {',
        'function setNeuronIntensity(intense) {\n  document.querySelector(".core-stage")?.classList.toggle("neuron-intense", Boolean(intense));\n}\n\nfunction isNearMessagesBottom(threshold = 72) {\n  return messages.scrollHeight - messages.scrollTop - messages.clientHeight <= threshold;\n}\n\nfunction addMessage(text, role) {',
        "neuron and scroll helpers",
    )
    text = replace_required(text, 'function showChatWelcome() {\n  messages.innerHTML = "";\n  addMessage("Jarvis intelligence core online.", "jarvis");\n}', 'function showChatWelcome() {\n  messages.innerHTML = "";\n  setNeuronIntensity(true);\n  addMessage("Jarvis intelligence core online.", "jarvis");\n}', "intense empty chat state")
    text = replace_required(text, '    for (const message of data.messages || []) {\n      addMessage(message.content, message.role === "user" ? "user" : "jarvis");\n    }\n    if (!messages.children.length) showChatWelcome();', '    const restoredMessages = data.messages || [];\n    setNeuronIntensity(restoredMessages.length === 0);\n    for (const message of restoredMessages) {\n      addMessage(message.content, message.role === "user" ? "user" : "jarvis");\n    }\n    if (!messages.children.length) showChatWelcome();', "restored chat neuron state")
    text = replace_required(text, '  const jarvisMessage = addMessage("Connecting…", "jarvis");', '  setNeuronIntensity(false);\n  const jarvisMessage = addMessage("Connecting…", "jarvis");', "subdued active conversation state")
    text = replace_required(text, '      const delta = eventData.text || "";\n      answer += delta;\n      speechBuffer += delta;\n      renderMessageContent(jarvisMessage, answer);\n      messages.scrollTop = messages.scrollHeight;', '      const followLatest = isNearMessagesBottom();\n      const delta = eventData.text || "";\n      answer += delta;\n      speechBuffer += delta;\n      renderMessageContent(jarvisMessage, answer);\n      if (followLatest) messages.scrollTop = messages.scrollHeight;', "user-controlled streaming scroll")
    text = replace_required(text, 'const sentencePattern = /^([\\s\\S]{24,240}?[.!?](?:\\s+|$));', 'const sentencePattern = /^([\\s\\S]{12,160}?[.!?](?:\\s+|$));', "faster sentence speech chunks") if False else text
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.8.5"', 'version="0.8.9"')
    text = text.replace('"version": "0.8.5"', '"version": "0.8.9"')
    text = text.replace('"output_format": "mp3_44100_128", "optimize_streaming_latency": "4"', '"output_format": "mp3_22050_32", "optimize_streaming_latency": "4"')
    MAIN.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_index()
    patch_main()
