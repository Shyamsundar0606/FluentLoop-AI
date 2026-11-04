from functools import lru_cache
from io import BytesIO
from pathlib import Path
import json
import wave
from app.config import get_settings


@lru_cache
def voice():
    from piper import PiperVoice

    s = get_settings()
    if s.speech_tts_provider != "piper":
        raise ValueError("Unsupported TTS provider")
    path = Path(s.speech_model_path) / "tts" / (s.speech_tts_voice + ".onnx")
    config = json.loads(Path(str(path) + ".json").read_text(encoding="utf-8"))
    if not config.get("language", {}).get("code", "").startswith("fr"):
        raise ValueError("French voice required")
    return PiperVoice.load(str(path), use_cuda=False)


def synthesize(text):
    if not text.strip() or len(text) > 600:
        raise ValueError("TTS text size invalid")
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav:
        voice().synthesize_wav(text, wav)
    data = buffer.getvalue()
    if not data or len(data) > 6_000_000:
        raise ValueError("TTS output too large")
    return data
