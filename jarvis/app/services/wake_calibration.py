from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


WAKE_SHADOW_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models/wakeword/hey_zbrano.onnx"
WAKE_SHADOW_MELSPEC_PATH = Path(__file__).resolve().parent.parent.parent / "models/wakeword/melspectrogram.onnx"
WAKE_SHADOW_EMBEDDING_PATH = Path(__file__).resolve().parent.parent.parent / "models/wakeword/embedding_model.onnx"
WAKE_CALIBRATION_DIR = Path("/data") / "wakeword_calibration"
WAKE_POSITIVE_DIR = WAKE_CALIBRATION_DIR / "positive"
WAKE_NEGATIVE_DIR = WAKE_CALIBRATION_DIR / "negative"
WAKE_VERIFIER_PATH = WAKE_CALIBRATION_DIR / "hey_zbrano_verifier.pkl"
WAKE_VERIFIER_ENABLED_PATH = WAKE_CALIBRATION_DIR / "verifier_enabled"
WAKE_VERIFIER_TRAIN_LOCK = asyncio.Lock()


def _new_wake_shadow_model() -> tuple[Any, Any, bool]:
    """Create an isolated streaming detector for one browser microphone."""
    import numpy as np
    from openwakeword.model import Model as OpenWakeWordModel

    required_models = (WAKE_SHADOW_MODEL_PATH, WAKE_SHADOW_MELSPEC_PATH, WAKE_SHADOW_EMBEDDING_PATH)
    missing_models = [path.name for path in required_models if not path.is_file()]
    if missing_models:
        raise RuntimeError(f"ZBRANO wake-word runtime model is missing: {', '.join(missing_models)}")
    model_kwargs: dict[str, Any] = {
        "wakeword_models": [str(WAKE_SHADOW_MODEL_PATH)],
        "inference_framework": "onnx",
        "melspec_model_path": str(WAKE_SHADOW_MELSPEC_PATH),
        "embedding_model_path": str(WAKE_SHADOW_EMBEDDING_PATH),
    }
    verifier_enabled = WAKE_VERIFIER_PATH.is_file() and WAKE_VERIFIER_ENABLED_PATH.is_file()
    if verifier_enabled:
        model_kwargs["custom_verifier_models"] = {WAKE_SHADOW_MODEL_PATH.stem: str(WAKE_VERIFIER_PATH)}
        model_kwargs["custom_verifier_threshold"] = 0.10
    model = OpenWakeWordModel(**model_kwargs)
    return model, np, verifier_enabled


def _wake_clip_quality(path: Path) -> dict[str, Any]:
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
    }


def _train_personal_wake_verifier() -> None:
    import pickle
    import numpy as np
    from openwakeword.custom_verifier_model import get_reference_clip_features, train_verifier_model
    from openwakeword.model import Model as OpenWakeWordModel

    positive_paths = [path for path in sorted(WAKE_POSITIVE_DIR.glob("*.wav")) if _wake_clip_quality(path).get("valid")]
    negative_paths = [path for path in sorted(WAKE_NEGATIVE_DIR.glob("*.wav")) if _wake_clip_quality(path).get("valid")]
    if len(positive_paths) < 20 or len(negative_paths) < 20:
        raise ValueError("Collect at least 20 positive and 20 other-speech samples first")
    model = OpenWakeWordModel(
        wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)],
        inference_framework="onnx",
        melspec_model_path=str(WAKE_SHADOW_MELSPEC_PATH),
        embedding_model_path=str(WAKE_SHADOW_EMBEDDING_PATH),
    )
    model_name = next(iter(model.models.keys()))
    positive_parts = [
        get_reference_clip_features(str(path), model, model_name, threshold=0.20, N=5)
        for path in positive_paths
    ]
    positive_parts = [part for part in positive_parts if part.shape[0]]
    if not positive_parts:
        raise ValueError("The base model could not find Hey ZBRANO in the positive recordings")
    negative_parts = [
        get_reference_clip_features(str(path), model, model_name, threshold=0.0, N=1)
        for path in negative_paths
    ]
    negative_parts = [part for part in negative_parts if part.shape[0]]
    if not negative_parts:
        raise ValueError("No usable other-speech features were found")
    positive_features = np.vstack(positive_parts)
    negative_features = np.vstack(negative_parts)
    verifier = train_verifier_model(
        np.vstack((positive_features, negative_features)),
        np.array([1] * positive_features.shape[0] + [0] * negative_features.shape[0]),
    )
    WAKE_CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    temporary = WAKE_VERIFIER_PATH.with_suffix(".tmp")
    with temporary.open("wb") as output:
        pickle.dump(verifier, output)
    temporary.replace(WAKE_VERIFIER_PATH)


