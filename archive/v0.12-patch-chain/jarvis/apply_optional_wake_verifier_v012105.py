import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.105 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.105 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''WAKE_VERIFIER_PATH = WAKE_CALIBRATION_DIR / "hey_zbrano_verifier.pkl"
WAKE_VERIFIER_TRAIN_LOCK = asyncio.Lock()''',
        '''WAKE_VERIFIER_PATH = WAKE_CALIBRATION_DIR / "hey_zbrano_verifier.pkl"
WAKE_VERIFIER_ENABLED_PATH = WAKE_CALIBRATION_DIR / "verifier_enabled"
WAKE_VERIFIER_TRAIN_LOCK = asyncio.Lock()''',
        "verifier preference storage",
    )
    backend = replace_once(
        backend,
        '''    verifier_enabled = WAKE_VERIFIER_PATH.is_file()
    if verifier_enabled:''',
        '''    verifier_enabled = WAKE_VERIFIER_PATH.is_file() and WAKE_VERIFIER_ENABLED_PATH.is_file()
    if verifier_enabled:''',
        "opt-in verifier loading",
    )
    backend = replace_once(
        backend,
        '''        "verifier_trained": WAKE_VERIFIER_PATH.is_file(),
    }''',
        '''        "verifier_trained": WAKE_VERIFIER_PATH.is_file(),
        "verifier_enabled": WAKE_VERIFIER_PATH.is_file() and WAKE_VERIFIER_ENABLED_PATH.is_file(),
    }''',
        "verifier status",
    )
    reset_marker = '''@app.delete("/api/voice/wake-calibration")
async def reset_wake_calibration() -> dict[str, Any]:'''
    verifier_api = '''@app.put("/api/voice/wake-calibration/verifier")
async def set_wake_verifier_enabled(enabled: bool) -> dict[str, Any]:
    if enabled and not WAKE_VERIFIER_PATH.is_file():
        raise HTTPException(status_code=409, detail="Train the personal verifier before enabling it")
    WAKE_CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    if enabled:
        WAKE_VERIFIER_ENABLED_PATH.write_text("enabled\\n", encoding="utf-8")
    else:
        WAKE_VERIFIER_ENABLED_PATH.unlink(missing_ok=True)
    return _wake_calibration_status()


@app.delete("/api/voice/wake-calibration/verifier")
async def delete_wake_verifier() -> dict[str, Any]:
    WAKE_VERIFIER_ENABLED_PATH.unlink(missing_ok=True)
    WAKE_VERIFIER_PATH.unlink(missing_ok=True)
    return {"deleted": True, **_wake_calibration_status()}


'''
    backend = replace_once(backend, reset_marker, verifier_api + reset_marker, "verifier controls API")
    backend = replace_once(
        backend,
        '''    WAKE_VERIFIER_PATH.unlink(missing_ok=True)
    return {"reset": True, **_wake_calibration_status()}''',
        '''    WAKE_VERIFIER_ENABLED_PATH.unlink(missing_ok=True)
    WAKE_VERIFIER_PATH.unlink(missing_ok=True)
    return {"reset": True, **_wake_calibration_status()}''',
        "complete calibration reset",
    )

    frontend = replace_once(
        frontend,
        '''<button id="wake-train-verifier" type="button" disabled>Train personal verifier</button><button id="wake-reset-calibration" type="button">Delete calibration</button>''',
        '''<button id="wake-train-verifier" type="button" disabled>Train personal verifier</button><button id="wake-delete-verifier" type="button">Delete verifier only</button><button id="wake-reset-calibration" type="button">Delete all calibration</button>''',
        "separate verifier deletion",
    )
    frontend = replace_once(
        frontend,
        '''            <p id="wake-calibration-message" class="muted">Collect 20 samples of each type. Use different distances and natural speaking styles.</p>''',
        '''            <label class="toggle-row"><input id="wake-use-verifier" type="checkbox"> Use personal verifier <small>(optional extra false-trigger filter)</small></label>
            <p id="wake-calibration-message" class="muted">The broader base model remains active by default. Your recordings are preserved for optional verifier experiments.</p>''',
        "verifier opt-in toggle",
    )
    frontend = replace_once(
        frontend,
        '''const wakePositiveCount=document.getElementById("wake-positive-count"),wakeNegativeCount=document.getElementById("wake-negative-count"),wakeVerifierState=document.getElementById("wake-verifier-state"),wakeCalibrationMessage=document.getElementById("wake-calibration-message"),wakeTrainVerifier=document.getElementById("wake-train-verifier");''',
        '''const wakePositiveCount=document.getElementById("wake-positive-count"),wakeNegativeCount=document.getElementById("wake-negative-count"),wakeVerifierState=document.getElementById("wake-verifier-state"),wakeCalibrationMessage=document.getElementById("wake-calibration-message"),wakeTrainVerifier=document.getElementById("wake-train-verifier"),wakeUseVerifier=document.getElementById("wake-use-verifier"),wakeDeleteVerifier=document.getElementById("wake-delete-verifier");''',
        "verifier UI controls",
    )
    frontend = replace_once(
        frontend,
        '''wakeVerifierState.textContent=data.verifier_trained?"Trained":"Not trained";wakeTrainVerifier.disabled=!data.ready_to_train||wakeCalibrationBusy;return data''',
        '''wakeVerifierState.textContent=data.verifier_trained?(data.verifier_enabled?"Trained · enabled":"Trained · off"):"Not trained";wakeUseVerifier.checked=data.verifier_enabled===true;wakeUseVerifier.disabled=!data.verifier_trained||wakeCalibrationBusy;wakeDeleteVerifier.disabled=!data.verifier_trained||wakeCalibrationBusy;wakeTrainVerifier.disabled=!data.ready_to_train||wakeCalibrationBusy;return data''',
        "verifier status rendering",
    )
    frontend = replace_once(
        frontend,
        '''wakeCalibrationMessage.textContent="Personal verifier trained. Restarting silent shadow evaluation...";await loadWakeCalibration();stopWake();if(wakeEnabled.checked)scheduleWake()''',
        '''wakeCalibrationMessage.textContent="Personal verifier trained and saved. The broader base model remains active until you enable the verifier.";await loadWakeCalibration()''',
        "non-automatic verifier activation",
    )
    listener_marker = '''  document.getElementById("wake-reset-calibration").addEventListener("click",async()=>{'''
    verifier_listeners = '''  wakeUseVerifier.addEventListener("change",async()=>{if(wakeCalibrationBusy)return;wakeCalibrationBusy=true;wakeUseVerifier.disabled=true;try{const enabled=wakeUseVerifier.checked,response=await fetch(`api/voice/wake-calibration/verifier?enabled=${enabled}`,{method:"PUT"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent=enabled?"Personal verifier enabled. Restarting shadow evaluation...":"Personal verifier disabled. Broader base-model recognition restored.";stopWake();if(wakeEnabled.checked)scheduleWake()}catch(error){wakeCalibrationMessage.textContent=`Verifier setting failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
  wakeDeleteVerifier.addEventListener("click",async()=>{if(!confirm("Delete only the trained verifier? Your positive and negative recordings will be preserved."))return;wakeCalibrationBusy=true;try{const response=await fetch("api/voice/wake-calibration/verifier",{method:"DELETE"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent="Personal verifier deleted. All calibration recordings were preserved.";stopWake();if(wakeEnabled.checked)scheduleWake()}catch(error){wakeCalibrationMessage.textContent=`Verifier deletion failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
'''
    frontend = replace_once(frontend, listener_marker, verifier_listeners + listener_marker, "verifier event controls")

    backend = backend.replace('version="0.12.104"', 'version="0.12.105"')
    backend = backend.replace('"version": "0.12.104"', '"version": "0.12.105"')
    frontend = frontend.replace("HUD 0.12.104", "HUD 0.12.105")

    for marker, location in [
        ('version="0.12.105"', backend),
        ('WAKE_VERIFIER_ENABLED_PATH', backend),
        ('@app.put("/api/voice/wake-calibration/verifier")', backend),
        ('@app.delete("/api/voice/wake-calibration/verifier")', backend),
        ('id="wake-use-verifier"', frontend),
        ('id="wake-delete-verifier"', frontend),
        ('Broader base-model recognition restored.', frontend),
        ('HUD 0.12.105', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
