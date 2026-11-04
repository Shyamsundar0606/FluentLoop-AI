"""Run with the optional speech environment; fixtures are controlled signals."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("av")
from app.speech.audio_processing import decode_audio
from app.speech.pronunciation_service import assess
from test_speech import wav


def test_real_decoder_duration_silence_and_corruption():
    audio, duration, quality = decode_audio(wav(0.5, True))
    assert len(audio) == 8000 and duration == 500 and "silence_or_very_quiet" in quality
    with pytest.raises(Exception):
        decode_audio(b"RIFF" + b"broken" * 20)
    with pytest.raises(ValueError):
        decode_audio(wav(1.1), max_seconds=1)


def test_clipping_and_nonfinite():
    import wave
    from io import BytesIO

    out = BytesIO()
    with wave.open(out, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes((np.ones(8000) * 32767).astype("<i2").tobytes())
    _, _, quality = decode_audio(out.getvalue())
    assert "clipping" in quality


def test_float_nan_is_rejected():
    import struct

    samples = np.full(8000, np.nan, dtype="<f4").tobytes()
    fmt = struct.pack("<HHIIHH", 3, 1, 16000, 64000, 4, 32)
    data = (
        b"RIFF"
        + struct.pack("<I", 36 + len(samples))
        + b"WAVEfmt "
        + struct.pack("<I", 16)
        + fmt
        + b"data"
        + struct.pack("<I", len(samples))
        + samples
    )
    with pytest.raises(ValueError):
        decode_audio(data)


def test_webm_opus_resampling_preserves_duration_and_signal():
    from scripts.diagnose_speech_recognition import webm

    original = (.2 * np.sin(2 * np.pi * 440 * np.arange(32000) / 16000)).astype("float32")
    decoded, duration, quality, metadata = decode_audio(webm(original), include_metadata=True)
    assert metadata["codec"] == "opus" and "webm" in metadata["container"]
    assert decoded.dtype == np.float32 and decoded.ndim == 1
    assert decoded.size == 32000 and duration == 2000 and not quality
    assert np.isfinite(decoded).all()
    assert .12 < float(np.sqrt(np.mean(decoded**2))) < .16
    assert .17 < float(np.max(np.abs(decoded))) < .25
