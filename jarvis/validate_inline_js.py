from pathlib import Path
import re
import subprocess
import sys
import tempfile

path = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/jarvis/app/static/index.html")
html = path.read_text(encoding="utf-8")
scripts: list[tuple[str, str]] = []
for index, match in enumerate(re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, flags=re.I | re.S), 1):
    attributes, inline = match.groups()
    source_match = re.search(r'\bsrc="([^"]+)"', attributes, flags=re.I)
    if source_match:
        source_path = (path.parent / source_match.group(1)).resolve()
        try:
            source_path.relative_to(path.parent.resolve())
        except ValueError as exc:
            raise SystemExit(f"Script {index} resolves outside the static directory") from exc
        if not source_path.is_file():
            raise SystemExit(f"Script {index} is missing: {source_match.group(1)}")
        scripts.append((source_match.group(1), source_path.read_text(encoding="utf-8")))
    else:
        scripts.append((f"inline script {index}", inline))
if not scripts:
    raise SystemExit("No JavaScript sources found")

for index, (label, script) in enumerate(scripts, 1):
    if not script.strip():
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
        handle.write(script)
        temp_name = handle.name
    result = subprocess.run(
        ["node", "--check", temp_name],
        text=True,
        capture_output=True,
    )
    Path(temp_name).unlink(missing_ok=True)
    if result.returncode:
        sys.stderr.write(f"JavaScript source {index} ({label}) failed syntax validation:\n")
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)

print(f"Validated {len(scripts)} JavaScript source(s)")
