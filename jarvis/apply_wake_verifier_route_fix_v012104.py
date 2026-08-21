import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.104 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def replace_count(text: str, old: str, new: str, count: int, label: str) -> str:
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"ZBRANO v0.12.104 patch expected {count} {label} markers; found {actual}")
    return text.replace(old, new)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.104 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '@app.post("/api/voice/wake-calibration/{label}")',
        '@app.post("/api/voice/wake-calibration/samples/{label}")',
        "non-conflicting calibration sample route",
    )
    frontend = replace_once(
        frontend,
        'fetch(`api/voice/wake-calibration/${label}`,{method:"POST",body})',
        'fetch(`api/voice/wake-calibration/samples/${label}`,{method:"POST",body})',
        "sample upload URL",
    )
    frontend = replace_once(
        frontend,
        '''  async function loadWakeCalibration(){''',
        '''  function wakeCalibrationError(data,status){
    const detail=data?.detail;if(typeof detail==="string")return detail;if(Array.isArray(detail))return detail.map(item=>item?.msg||JSON.stringify(item)).join("; ");if(detail&&typeof detail==="object")return JSON.stringify(detail);return `HTTP ${status}`;
  }
  async function loadWakeCalibration(){''',
        "structured calibration error formatter",
    )
    error_old = 'throw new Error(data.detail||`HTTP ${response.status}`)'
    error_new = 'throw new Error(wakeCalibrationError(data,response.status))'
    functions_start = frontend.find('  function wakeCalibrationError')
    functions_end = frontend.find('\n  function recordWakeCalibration', functions_start)
    if functions_start < 0 or functions_end < 0:
        raise RuntimeError("ZBRANO v0.12.104 could not isolate calibration functions")
    functions = replace_count(frontend[functions_start:functions_end], error_old, error_new, 2, "calibration function error")
    frontend = frontend[:functions_start] + functions + frontend[functions_end:]
    listeners_start = frontend.find('  wakeTrainVerifier.addEventListener')
    listeners_end = frontend.find('\n  loadWakeCalibration();', listeners_start)
    if listeners_start < 0 or listeners_end < 0:
        raise RuntimeError("ZBRANO v0.12.104 could not isolate calibration listeners")
    listeners = replace_count(frontend[listeners_start:listeners_end], error_old, error_new, 2, "calibration listener error")
    frontend = frontend[:listeners_start] + listeners + frontend[listeners_end:]

    backend = backend.replace('version="0.12.103"', 'version="0.12.104"')
    backend = backend.replace('"version": "0.12.103"', '"version": "0.12.104"')
    frontend = frontend.replace("HUD 0.12.103", "HUD 0.12.104")

    for marker, location in [
        ('version="0.12.104"', backend),
        ('@app.post("/api/voice/wake-calibration/samples/{label}")', backend),
        ('@app.post("/api/voice/wake-calibration/train")', backend),
        ('wakeCalibrationError(data,response.status)', frontend),
        ('api/voice/wake-calibration/samples/${label}', frontend),
        ('HUD 0.12.104', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
