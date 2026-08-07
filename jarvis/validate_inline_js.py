from pathlib import Path
import re
import subprocess
import sys
import tempfile

path = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/jarvis/app/static/index.html")
html = path.read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.I | re.S)
if not scripts:
    raise SystemExit("No inline JavaScript found")

for index, script in enumerate(scripts, 1):
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
        sys.stderr.write(f"Inline script {index} failed JavaScript syntax validation:\n")
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)

print(f"Validated {len(scripts)} inline script block(s)")
