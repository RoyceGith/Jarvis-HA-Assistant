import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.106 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.106 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    export_marker = '''@app.put("/api/voice/wake-calibration/verifier")'''
    export_api = '''@app.get("/api/voice/wake-calibration/export")
async def export_wake_calibration() -> Response:
    """Export only operator-recorded wake calibration WAV files for offline retraining."""
    import io
    import json
    import zipfile

    archive_buffer = io.BytesIO()
    counts = {"positive": 0, "negative": 0}
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for label, directory in (("positive", WAKE_POSITIVE_DIR), ("negative", WAKE_NEGATIVE_DIR)):
            if not directory.is_dir():
                continue
            for index, clip in enumerate(sorted(directory.glob("*.wav")), start=1):
                archive.write(clip, f"{label}/{label}_{index:03d}.wav")
                counts[label] += 1
        archive.writestr(
            "manifest.json",
            json.dumps({"wake_phrase": "Hey ZBRANO", "sample_rate_hz": 16000, "format": "mono PCM WAV", "counts": counts}, indent=2),
        )
    return Response(
        content=archive_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="zbrano-wake-calibration.zip"'},
    )


'''
    backend = replace_once(backend, export_marker, export_api + export_marker, "calibration export API")

    frontend = replace_once(
        frontend,
        '''<span>Live<strong id="wake-shadow-score">0.000</strong></span><span>Peak<strong id="wake-shadow-peak">0.000</strong></span><span>Detections<strong id="wake-shadow-detections">0</strong></span><span>Marked false<strong id="wake-shadow-false">0</strong></span><span>Runtime<strong id="wake-shadow-runtime">0m</strong></span>''',
        '''<span>Model live<strong id="wake-shadow-score">0.000</strong></span><span>Model peak<strong id="wake-shadow-peak">0.000</strong></span><span>Mic RMS<strong id="wake-mic-rms">0.000</strong></span><span>Mic peak<strong id="wake-mic-peak">0.000</strong></span><span>Detections<strong id="wake-shadow-detections">0</strong></span><span>Marked false<strong id="wake-shadow-false">0</strong></span><span>Runtime<strong id="wake-shadow-runtime">0m</strong></span>''',
        "microphone diagnostic metrics",
    )
    frontend = replace_once(
        frontend,
        '''<button id="wake-shadow-mark-false" type="button">Mark last detection false</button><button id="wake-shadow-reset" type="button">Reset shadow statistics</button>''',
        '''<button id="wake-test-phrase" type="button">Test one phrase</button><button id="wake-shadow-mark-false" type="button">Mark last detection false</button><button id="wake-shadow-reset" type="button">Reset shadow statistics</button>''',
        "bounded phrase test control",
    )
    frontend = replace_once(
        frontend,
        '''          <p id="wake-shadow-message" class="muted">Enable wake listening and shadow testing to begin local scoring.</p>''',
        '''          <p id="wake-shadow-message" class="muted">Enable wake listening and shadow testing to begin local scoring.</p>
          <ol id="wake-attempt-results" class="wake-attempt-results" aria-label="Recent wake phrase test results"></ol>''',
        "attempt results panel",
    )
    frontend = replace_once(
        frontend,
        '''<button id="wake-train-verifier" type="button" disabled>Train personal verifier</button><button id="wake-delete-verifier" type="button">Delete verifier only</button><button id="wake-reset-calibration" type="button">Delete all calibration</button>''',
        '''<button id="wake-train-verifier" type="button" disabled>Train personal verifier</button><button id="wake-export-calibration" type="button">Export recordings ZIP</button><button id="wake-delete-verifier" type="button">Delete verifier only</button><button id="wake-reset-calibration" type="button">Delete all calibration</button>''',
        "calibration export control",
    )
    frontend = replace_once(
        frontend,
        '''let wakeShadowHistory=[],wakeShadowLastCandidate=null,wakeCalibrationCapture=null,wakeCalibrationBusy=false;''',
        '''let wakeShadowHistory=[],wakeShadowLastCandidate=null,wakeCalibrationCapture=null,wakeCalibrationBusy=false,wakeShadowInputRms=0,wakeShadowInputPeak=0,wakeShadowAttempt=null,wakeShadowAttemptTimer=null,wakeShadowAttemptNumber=0;''',
        "wake diagnostic state",
    )
    frontend = replace_once(
        frontend,
        '''const wakeShadowFalse=document.getElementById("wake-shadow-false"),wakeShadowRuntime=document.getElementById("wake-shadow-runtime"),wakeShadowMessage=document.getElementById("wake-shadow-message");''',
        '''const wakeShadowFalse=document.getElementById("wake-shadow-false"),wakeShadowRuntime=document.getElementById("wake-shadow-runtime"),wakeShadowMessage=document.getElementById("wake-shadow-message");
  const wakeMicRms=document.getElementById("wake-mic-rms"),wakeMicPeak=document.getElementById("wake-mic-peak"),wakeAttemptResults=document.getElementById("wake-attempt-results"),wakeTestPhrase=document.getElementById("wake-test-phrase");''',
        "wake diagnostic controls",
    )
    frontend = replace_once(
        frontend,
        '''wakeShadowRuntime.textContent=activeMs<3600000?`${Math.floor(activeMs/60000)}m`:`${(activeMs/3600000).toFixed(1)}h`;''',
        '''wakeShadowRuntime.textContent=activeMs<3600000?`${Math.floor(activeMs/60000)}m`:`${(activeMs/3600000).toFixed(1)}h`;wakeMicRms.textContent=Number(wakeShadowInputRms||0).toFixed(3);wakeMicPeak.textContent=Number(wakeShadowInputPeak||0).toFixed(3);''',
        "live microphone rendering",
    )
    frontend = replace_once(
        frontend,
        '''  function handleWakeShadowScore(score){''',
        '''  function finishWakeShadowAttempt(){
    if(wakeShadowAttemptTimer)clearTimeout(wakeShadowAttemptTimer);wakeShadowAttemptTimer=null;const attempt=wakeShadowAttempt;wakeShadowAttempt=null;wakeTestPhrase.disabled=false;if(!attempt)return;
    const detected=attempt.detected===true,item=document.createElement("li");wakeShadowAttemptNumber++;item.dataset.result=detected?"detected":"missed";item.textContent=`Test ${wakeShadowAttemptNumber}: ${detected?"DETECTED":"MISSED"} · model ${attempt.score.toFixed(3)} · RMS ${attempt.rms.toFixed(3)} · mic peak ${attempt.peak.toFixed(3)}`;wakeAttemptResults.prepend(item);while(wakeAttemptResults.children.length>10)wakeAttemptResults.lastElementChild.remove();wakeShadowMessage.textContent=detected?"Phrase detected. Compare microphone level with missed tests.":"Phrase missed. The input measurements show whether audio reached the model.";
  }
  function startWakeShadowAttempt(){
    if(!wakeShadowSocket||wakeShadowSocket.readyState!==WebSocket.OPEN){wakeShadowMessage.textContent="Enable wake listening and Local Wake Shadow Test first.";return}if(wakeShadowAttempt)finishWakeShadowAttempt();wakeShadowAttempt={score:0,rms:0,peak:0,above:0,detected:false};wakeTestPhrase.disabled=true;wakeShadowMessage.textContent='Say “Hey ZBRANO” once now. Measuring for four seconds...';wakeShadowAttemptTimer=setTimeout(finishWakeShadowAttempt,4000);
  }
  function handleWakeShadowScore(score){''',
        "bounded phrase diagnostics",
    )
    frontend = replace_once(
        frontend,
        '''score=Math.max(0,Math.min(1,Number(score)||0));wakeShadowStats.frames++;wakeShadowStats.peak=Math.max(Number(wakeShadowStats.peak||0),score);''',
        '''score=Math.max(0,Math.min(1,Number(score)||0));wakeShadowStats.frames++;wakeShadowStats.peak=Math.max(Number(wakeShadowStats.peak||0),score);if(wakeShadowAttempt){wakeShadowAttempt.score=Math.max(wakeShadowAttempt.score,score);wakeShadowAttempt.above=score>=Number(wakeShadowThreshold.value||.5)?wakeShadowAttempt.above+1:0;if(wakeShadowAttempt.above>=2)wakeShadowAttempt.detected=true}''',
        "attempt model score",
    )
    processor_old = '''for(const sample of converted){wakeShadowPcm.push(sample);wakeShadowHistory.push(sample);if(wakeCalibrationCapture)wakeCalibrationCapture.samples.push(sample)}if(wakeShadowHistory.length>80000)'''
    processor_new = '''let energy=0,inputPeak=0;for(const sample of converted){const normalized=sample/32768;energy+=normalized*normalized;inputPeak=Math.max(inputPeak,Math.abs(normalized));wakeShadowPcm.push(sample);wakeShadowHistory.push(sample);if(wakeCalibrationCapture)wakeCalibrationCapture.samples.push(sample)}wakeShadowInputRms=Math.sqrt(energy/Math.max(1,converted.length));wakeShadowInputPeak=inputPeak;if(wakeShadowAttempt){wakeShadowAttempt.rms=Math.max(wakeShadowAttempt.rms,wakeShadowInputRms);wakeShadowAttempt.peak=Math.max(wakeShadowAttempt.peak,wakeShadowInputPeak)}if(wakeShadowHistory.length>80000)'''
    frontend = replace_once(frontend, processor_old, processor_new, "microphone input measurement")
    frontend = replace_once(
        frontend,
        '''if(wakeShadowSaveTimer)clearInterval(wakeShadowSaveTimer);wakeShadowSaveTimer=null;''',
        '''if(wakeShadowSaveTimer)clearInterval(wakeShadowSaveTimer);wakeShadowSaveTimer=null;if(wakeShadowAttemptTimer)clearTimeout(wakeShadowAttemptTimer);wakeShadowAttemptTimer=null;wakeShadowAttempt=null;wakeShadowInputRms=0;wakeShadowInputPeak=0;if(wakeTestPhrase)wakeTestPhrase.disabled=false;''',
        "diagnostic cleanup",
    )
    listener_marker = '''  wakeShadowEnabled.addEventListener("change",()=>{'''
    diagnostics_listeners = '''  wakeTestPhrase.addEventListener("click",startWakeShadowAttempt);
  document.getElementById("wake-export-calibration").addEventListener("click",()=>{const link=document.createElement("a");link.href=new URL("api/voice/wake-calibration/export",document.baseURI).toString();link.download="zbrano-wake-calibration.zip";document.body.appendChild(link);link.click();link.remove()});
'''
    frontend = replace_once(frontend, listener_marker, diagnostics_listeners + listener_marker, "wake diagnostic listeners")
    style_marker = '''    @media(max-width:700px){.wake-calibration-counts{grid-template-columns:1fr}}'''
    frontend = replace_once(
        frontend,
        style_marker,
        style_marker + '''
    .wake-attempt-results{display:grid;gap:.3rem;margin:0;padding:0;list-style:none}.wake-attempt-results:empty{display:none}.wake-attempt-results li{padding:.35rem .5rem;border:1px solid var(--line);border-radius:7px;font-size:.7rem}.wake-attempt-results li[data-result="detected"]{border-left:3px solid var(--phosphor)}.wake-attempt-results li[data-result="missed"]{border-left:3px solid #f39a32}''',
        "attempt result styling",
    )

    backend = backend.replace('version="0.12.105"', 'version="0.12.106"')
    backend = backend.replace('"version": "0.12.105"', '"version": "0.12.106"')
    frontend = frontend.replace("HUD 0.12.105", "HUD 0.12.106")

    for marker, location in [
        ('version="0.12.106"', backend),
        ('@app.get("/api/voice/wake-calibration/export")', backend),
        ('zbrano-wake-calibration.zip', backend),
        ('id="wake-mic-rms"', frontend),
        ('id="wake-test-phrase"', frontend),
        ('function startWakeShadowAttempt()', frontend),
        ('id="wake-export-calibration"', frontend),
        ('HUD 0.12.106', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
