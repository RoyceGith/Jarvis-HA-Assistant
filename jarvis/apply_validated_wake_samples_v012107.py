import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.107 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.107 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''def _wake_calibration_status() -> dict[str, Any]:
    positive = len(list(WAKE_POSITIVE_DIR.glob("*.wav"))) if WAKE_POSITIVE_DIR.is_dir() else 0
    negative = len(list(WAKE_NEGATIVE_DIR.glob("*.wav"))) if WAKE_NEGATIVE_DIR.is_dir() else 0
    return {
        "positive": positive,
        "negative": negative,
        "required_each": 20,
        "ready_to_train": positive >= 20 and negative >= 20,
        "verifier_trained": WAKE_VERIFIER_PATH.is_file(),
        "verifier_enabled": WAKE_VERIFIER_PATH.is_file() and WAKE_VERIFIER_ENABLED_PATH.is_file(),
    }''',
        '''def _wake_clip_quality(path: Path) -> dict[str, Any]:
    import array
    import math
    import wave

    try:
        with wave.open(str(path), "rb") as clip:
            frames = clip.readframes(clip.getnframes())
            sample_rate = clip.getframerate()
            sample_count = clip.getnframes()
        samples = array.array("h")
        samples.frombytes(frames)
        if not samples:
            raise ValueError("empty audio")
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768.0
        peak = max(abs(sample) for sample in samples) / 32768.0
        nonzero_fraction = sum(sample != 0 for sample in samples) / len(samples)
        clipped_fraction = sum(abs(sample) >= 32700 for sample in samples) / len(samples)
        valid = rms >= 0.003 and peak >= 0.03 and nonzero_fraction >= 0.08 and clipped_fraction <= 0.005
        return {
            "valid": valid,
            "rms": round(rms, 4),
            "peak": round(peak, 4),
            "nonzero_fraction": round(nonzero_fraction, 4),
            "clipped_fraction": round(clipped_fraction, 6),
            "duration_seconds": round(sample_count / max(1, sample_rate), 2),
        }
    except Exception as exc:
        return {"valid": False, "error": str(exc)}


def _wake_calibration_status() -> dict[str, Any]:
    paths = {
        "positive": sorted(WAKE_POSITIVE_DIR.glob("*.wav")) if WAKE_POSITIVE_DIR.is_dir() else [],
        "negative": sorted(WAKE_NEGATIVE_DIR.glob("*.wav")) if WAKE_NEGATIVE_DIR.is_dir() else [],
    }
    quality = {label: [_wake_clip_quality(path) for path in label_paths] for label, label_paths in paths.items()}
    positive = sum(item.get("valid") is True for item in quality["positive"])
    negative = sum(item.get("valid") is True for item in quality["negative"])
    return {
        "positive": positive,
        "negative": negative,
        "positive_total": len(paths["positive"]),
        "negative_total": len(paths["negative"]),
        "positive_invalid": len(paths["positive"]) - positive,
        "negative_invalid": len(paths["negative"]) - negative,
        "required_each": 20,
        "ready_to_train": positive >= 20 and negative >= 20,
        "verifier_trained": WAKE_VERIFIER_PATH.is_file(),
        "verifier_enabled": WAKE_VERIFIER_PATH.is_file() and WAKE_VERIFIER_ENABLED_PATH.is_file(),
    }''',
        "quality-aware calibration status",
    )
    backend = replace_once(
        backend,
        '''    destination.mkdir(parents=True, exist_ok=True)
    (destination / f"{time.time_ns()}.wav").write_bytes(content)
    return {"saved": True, **_wake_calibration_status()}''',
        '''    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{time.time_ns()}.wav"
    target.write_bytes(content)
    quality = _wake_clip_quality(target)
    if not quality.get("valid"):
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail=f"Recording rejected: RMS {quality.get('rms', 0):.4f}, peak {quality.get('peak', 0):.4f}. Speak once after the recorder says it is armed.",
        )
    return {"saved": True, "quality": quality, **_wake_calibration_status()}''',
        "server-side sample validation",
    )
    backend = replace_once(
        backend,
        '''    positive_paths = sorted(WAKE_POSITIVE_DIR.glob("*.wav"))
    negative_paths = sorted(WAKE_NEGATIVE_DIR.glob("*.wav"))''',
        '''    positive_paths = [path for path in sorted(WAKE_POSITIVE_DIR.glob("*.wav")) if _wake_clip_quality(path).get("valid")]
    negative_paths = [path for path in sorted(WAKE_NEGATIVE_DIR.glob("*.wav")) if _wake_clip_quality(path).get("valid")]''',
        "validated verifier inputs",
    )
    backend = replace_once(
        backend,
        '''@app.get("/api/voice/wake-calibration/export")''',
        '''@app.delete("/api/voice/wake-calibration/invalid")
async def delete_invalid_wake_calibration() -> dict[str, Any]:
    removed = 0
    for directory in (WAKE_POSITIVE_DIR, WAKE_NEGATIVE_DIR):
        if not directory.is_dir():
            continue
        for clip in directory.glob("*.wav"):
            if not _wake_clip_quality(clip).get("valid"):
                clip.unlink(missing_ok=True)
                removed += 1
    return {"removed": removed, **_wake_calibration_status()}


@app.get("/api/voice/wake-calibration/export")''',
        "invalid recording cleanup API",
    )
    backend = replace_once(
        backend,
        '''            for index, clip in enumerate(sorted(directory.glob("*.wav")), start=1):
                archive.write(clip, f"{label}/{label}_{index:03d}.wav")
                counts[label] += 1''',
        '''            valid_index = 0
            for clip in sorted(directory.glob("*.wav")):
                if not _wake_clip_quality(clip).get("valid"):
                    continue
                valid_index += 1
                archive.write(clip, f"{label}/{label}_{valid_index:03d}.wav")
                counts[label] += 1''',
        "validated calibration export",
    )

    frontend = replace_once(
        frontend,
        '''<button id="wake-train-verifier" type="button" disabled>Train personal verifier</button><button id="wake-export-calibration" type="button">Export recordings ZIP</button><button id="wake-delete-verifier" type="button">Delete verifier only</button>''',
        '''<button id="wake-train-verifier" type="button" disabled>Train personal verifier</button><button id="wake-export-calibration" type="button">Export recordings ZIP</button><button id="wake-remove-invalid" type="button">Remove invalid recordings</button><button id="wake-delete-verifier" type="button">Delete verifier only</button>''',
        "invalid recording control",
    )
    frontend = replace_once(
        frontend,
        '''wakePositiveCount.textContent=`${data.positive} / ${data.required_each}`;wakeNegativeCount.textContent=`${data.negative} / ${data.required_each}`;''',
        '''wakePositiveCount.textContent=`${data.positive} / ${data.required_each} valid${data.positive_invalid?` · ${data.positive_invalid} invalid`:""}`;wakeNegativeCount.textContent=`${data.negative} / ${data.required_each} valid${data.negative_invalid?` · ${data.negative_invalid} invalid`:""}`;''',
        "valid recording counts",
    )
    frontend = replace_once(
        frontend,
        '''const response=await fetch(`api/voice/wake-calibration/samples/${label}`,{method:"POST",body}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent=message''',
        '''const response=await fetch(`api/voice/wake-calibration/samples/${label}`,{method:"POST",body}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));const quality=data.quality||{};wakeCalibrationMessage.textContent=`${message} RMS ${Number(quality.rms||0).toFixed(3)}, peak ${Number(quality.peak||0).toFixed(3)}.`''',
        "recording quality feedback",
    )
    frontend = replace_once(
        frontend,
        '''wakeCalibrationCapture={label,samples:[]};wakeCalibrationMessage.textContent=label==="positive"?'Recording now â€” say â€œHey ZBRANOâ€ once.':"Recording now â€” speak a normal sentence without the wake phrase.";''',
        '''wakeCalibrationCapture={label,samples:[],started:false,armedAt:performance.now(),lastVoiceAt:0};wakeCalibrationMessage.textContent=label==="positive"?'Armed â€” say â€œHey ZBRANOâ€ once. Recording begins when speech is detected.':"Armed â€” speak one normal sentence. Recording begins when speech is detected.";''',
        "speech-armed calibration",
    )
    old_capture = '''for(const sample of converted){const normalized=sample/32768;energy+=normalized*normalized;inputPeak=Math.max(inputPeak,Math.abs(normalized));wakeShadowPcm.push(sample);wakeShadowHistory.push(sample);if(wakeCalibrationCapture)wakeCalibrationCapture.samples.push(sample)}wakeShadowInputRms=Math.sqrt(energy/Math.max(1,converted.length));wakeShadowInputPeak=inputPeak;if(wakeShadowAttempt){wakeShadowAttempt.rms=Math.max(wakeShadowAttempt.rms,wakeShadowInputRms);wakeShadowAttempt.peak=Math.max(wakeShadowAttempt.peak,wakeShadowInputPeak)}if(wakeShadowHistory.length>80000)wakeShadowHistory.splice(0,wakeShadowHistory.length-80000);if(wakeCalibrationCapture&&wakeCalibrationCapture.samples.length>=56000)finishWakeCalibrationCapture();'''
    new_capture = '''for(const sample of converted){const normalized=sample/32768;energy+=normalized*normalized;inputPeak=Math.max(inputPeak,Math.abs(normalized));wakeShadowPcm.push(sample);wakeShadowHistory.push(sample)}wakeShadowInputRms=Math.sqrt(energy/Math.max(1,converted.length));wakeShadowInputPeak=inputPeak;if(wakeShadowAttempt){wakeShadowAttempt.rms=Math.max(wakeShadowAttempt.rms,wakeShadowInputRms);wakeShadowAttempt.peak=Math.max(wakeShadowAttempt.peak,wakeShadowInputPeak)}if(wakeShadowHistory.length>80000)wakeShadowHistory.splice(0,wakeShadowHistory.length-80000);if(wakeCalibrationCapture){const capture=wakeCalibrationCapture,now=performance.now();let startedNow=false;if(!capture.started&&wakeShadowInputRms>=.012){capture.started=true;startedNow=true;capture.samples=Array.from(wakeShadowHistory.slice(-8000));capture.lastVoiceAt=now;wakeCalibrationMessage.textContent="Speech detected â€” recording this utterance..."}if(capture.started){if(!startedNow)for(const sample of converted)capture.samples.push(sample);if(wakeShadowInputRms>=.008)capture.lastVoiceAt=now;if((capture.samples.length>=16000&&now-capture.lastVoiceAt>=650)||capture.samples.length>=64000)finishWakeCalibrationCapture()}else if(now-capture.armedAt>=8000){wakeCalibrationCapture=null;wakeCalibrationMessage.textContent="No speech detected in eight seconds. Check the live microphone level and try again."}}'''
    frontend = replace_once(frontend, old_capture, new_capture, "voice-activity calibration capture")
    listener_marker = '''  document.getElementById("wake-export-calibration").addEventListener("click",()=>{'''
    cleanup_listener = '''  document.getElementById("wake-remove-invalid").addEventListener("click",async()=>{if(!confirm("Remove recordings that are silent, too quiet, or materially clipped? Valid recordings will be preserved."))return;wakeCalibrationBusy=true;try{const response=await fetch("api/voice/wake-calibration/invalid",{method:"DELETE"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent=`Removed ${data.removed||0} invalid recording(s). Valid clips were preserved.`}catch(error){wakeCalibrationMessage.textContent=`Invalid-recording cleanup failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
'''
    frontend = replace_once(frontend, listener_marker, cleanup_listener + listener_marker, "invalid recording cleanup listener")

    backend = backend.replace('version="0.12.106"', 'version="0.12.107"')
    backend = backend.replace('"version": "0.12.106"', '"version": "0.12.107"')
    frontend = frontend.replace("HUD 0.12.106", "HUD 0.12.107")

    for marker, location in [
        ('version="0.12.107"', backend),
        ('def _wake_clip_quality', backend),
        ('@app.delete("/api/voice/wake-calibration/invalid")', backend),
        ('positive_paths = [path for path', backend),
        ('id="wake-remove-invalid"', frontend),
        ('Recording begins when speech is detected.', frontend),
        ('Speech detected â€” recording this utterance...', frontend),
        ('HUD 0.12.107', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
