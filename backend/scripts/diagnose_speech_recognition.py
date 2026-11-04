"""Explicit local fixture diagnostic; never reads stored learner recordings."""
import json
from io import BytesIO
from pathlib import Path
import wave

import av
import numpy as np
from app.speech.audio_processing import decode_audio
from app.speech.faster_whisper_provider import model, transcribe

ROOT = Path(__file__).resolve().parents[2]


def pcm(audio):
    buffer = BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes((audio * 32767).astype("<i2").tobytes())
    return buffer.getvalue()


def webm(audio):
    buffer = BytesIO()
    with av.open(buffer, mode="w", format="webm") as output:
        stream = output.add_stream("libopus", rate=48000)
        stream.layout = "mono"
        resampler = av.AudioResampler(format="flt", layout="mono", rate=48000)
        frame = av.AudioFrame.from_ndarray(audio.reshape(1, -1), format="flt", layout="mono")
        frame.sample_rate = 16000
        for converted in [*resampler.resample(frame), *resampler.resample(None)]:
            for packet in stream.encode(converted):
                output.mux(packet)
        for packet in stream.encode(None):
            output.mux(packet)
    return buffer.getvalue()


def run():
    human = (ROOT / "backend/tests/fixtures/speech/fr-bonjour.ogg").read_bytes()
    audio, _, _ = decode_audio(human)
    padded = np.pad(audio, (16000, 48000))
    cases = {"human_bonjour": human, "human_bonjour_padded": pcm(padded),
             "human_bonjour_webm": webm(padded), "silence": pcm(np.zeros(64000, dtype="float32")),
             "noise": pcm(np.random.default_rng(42).normal(0, .03, 64000).astype("float32"))}
    cases["human_english_hello"] = (ROOT / "backend/tests/fixtures/speech/en-us-hello.ogg").read_bytes()
    browser = ROOT / ".speech-models/browser-fr.webm"
    if browser.exists():
        cases["chromium_mediarecorder_french"] = browser.read_bytes()
    for name in ("test-fr", "test-en"):
        path = ROOT / ".speech-models" / f"{name}.wav"
        if path.exists():
            cases[name] = path.read_bytes()
    results = []
    for name, data in cases.items():
        audio, duration, quality, metadata = decode_audio(data, include_metadata=True)
        row = {"fixture": name, "decoded": {**metadata, "sample_rate": 16000, "samples": len(audio),
               "duration_ms": duration, "rms": float(np.sqrt(np.mean(audio**2))),
               "peak": float(np.max(np.abs(audio))), "quality": quality}, "comparisons": []}
        for language in (None, "fr"):
            segments, info = model().transcribe(audio, language=language, task="transcribe", beam_size=3,
                word_timestamps=True, vad_filter=True, condition_on_previous_text=False,
                temperature=0, max_new_tokens=180)
            row["comparisons"].append({"requested_language": language, "detected_language": info.language,
                "language_probability": info.language_probability, "vad_seconds": info.duration_after_vad,
                "top_language_probs": sorted(info.all_language_probs or [], key=lambda item: -item[1])[:5],
                "segments": [{"text": s.text, "avg_logprob": s.avg_logprob,
                              "no_speech_prob": s.no_speech_prob, "compression_ratio": s.compression_ratio}
                             for s in segments]})
        row["production"] = transcribe(data)
        expected = {
            "human_bonjour": "uncertain", "human_bonjour_padded": "uncertain",
            "human_bonjour_webm": "uncertain", "silence": "no_speech", "noise": "no_speech",
            "chromium_mediarecorder_french": "transcribed", "test-fr": "transcribed",
            "test-en": "non_french",
        }
        if name in expected:
            assert row["production"]["status"] == expected[name], name
        if name == "human_english_hello":
            assert row["production"]["status"] != "transcribed", name
        results.append(row)
        print(json.dumps(row, ensure_ascii=True), flush=True)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(run(), ensure_ascii=False, indent=2), encoding="utf-8")
