from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.14 patch missing: {label}")


def replace_required(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new)


def patch_backend(backend: str) -> str:
    replacements = (
        ('title="Jarvis Workshop Assistant"', 'title="ZBRANO"', "API title"),
        ('version="0.12.13"', 'version="0.12.14"', "backend version"),
        ('"version": "0.12.13"', '"version": "0.12.14"', "runtime version marker"),
        ('default="Jarvis Workshop Assistant"', 'default="ZBRANO"', "default project name"),
        ("Find Jarvis-approved Home Assistant entities", "Find ZBRANO-approved Home Assistant entities", "entity search description"),
        ("Append one behavior or preference to Jarvis General Instructions.", "Append one behavior or preference to ZBRANO General Instructions.", "instruction tool description"),
        ("You are Jarvis, a practical workshop assistant.", "You are ZBRANO, a practical workshop intelligence core assistant.", "system identity"),
        ("enabled in Jarvis policy", "enabled in ZBRANO policy", "entity policy instructions"),
        ('"name": "jarvis-workshop-assistant"', '"name": "zbrano-workshop-assistant"', "Workshop Memory client identity"),
        ('"name":"Jarvis Plugin Manager"', '"name":"ZBRANO Plugin Manager"', "plugin client identity"),
        ("approved for Jarvis access", "approved for ZBRANO access", "entity access error"),
        ("approved for Jarvis control", "approved for ZBRANO control", "entity control error"),
        ("Jarvis tool loop ended unexpectedly", "ZBRANO tool loop ended unexpectedly", "tool loop error"),
        ("Jarvis streaming tool loop ended unexpectedly", "ZBRANO streaming tool loop ended unexpectedly", "stream tool loop error"),
        ("Jarvis add-on configuration", "ZBRANO add-on configuration", "GitHub configuration guidance"),
        ("Unsupported Jarvis backup format", "Unsupported ZBRANO backup format", "backup error"),
        ('filename=jarvis-backup.json', 'filename=zbrano-backup.json', "backup response filename"),
        ("for Jarvis access.", "for ZBRANO access.", "entity review summary"),
        ("Jarvis Workshop Assistant entity access catalog", "ZBRANO entity access catalog", "entity catalog label"),
        ("for Jarvis access\"", "for ZBRANO access\"", "entity review goal"),
        ("to Jarvis.\"", "to ZBRANO.\"", "entity approval action"),
        ('"jarvis-recording.webm"', '"zbrano-recording.webm"', "recording filename"),
        ("Jarvis workshop assistant. Preserve", "ZBRANO workshop intelligence core assistant. Preserve", "transcription prompt"),
        ('"X-Jarvis-Voice"', '"X-ZBRANO-Voice"', "voice response header"),
        ('"X-Jarvis-Speech-Provider"', '"X-ZBRANO-Speech-Provider"', "speech provider header"),
        ("Unsupported Jarvis voice", "Unsupported ZBRANO voice", "voice error"),
    )
    for old, new, label in replacements:
        backend = replace_required(backend, old, new, label)
    return backend


def patch_frontend(frontend: str) -> str:
    frontend = replace_required(frontend, "HUD 0.12.13", "HUD 0.12.14", "frontend version")
    frontend = replace_required(frontend, '= "Jarvis")', '= "ZBRANO")', "voice name fallback")
    frontend = replace_required(frontend, '|| "Jarvis")', '|| "ZBRANO")', "provider voice fallback")
    frontend = replace_required(frontend, 'link.download = "jarvis-backup.json"', 'link.download = "zbrano-backup.json"', "backup download name")
    frontend = replace_required(frontend, '`jarvis-recording.${extension}`', '`zbrano-recording.${extension}`', "browser recording filename")
    return frontend


def main() -> None:
    backend = patch_backend(MAIN.read_text(encoding="utf-8"))
    frontend = patch_frontend(INDEX.read_text(encoding="utf-8"))
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    for marker in (
        'title="ZBRANO"',
        'version="0.12.14"',
        "You are ZBRANO, a practical workshop intelligence core assistant.",
        '"name": "zbrano-workshop-assistant"',
        '"name":"ZBRANO Plugin Manager"',
        '"X-ZBRANO-Voice"',
    ):
        require(backend, marker, marker)
    for marker in ("HUD 0.12.14", 'link.download = "zbrano-backup.json"'):
        require(frontend, marker, marker)


if __name__ == "__main__":
    main()
    verify()
