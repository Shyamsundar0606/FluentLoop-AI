"""Explicit human-fixture comparison, without expected-text hints or auto-correction.

MP3 research excerpts are decoded here only; production upload support is unchanged.
Download source assets only for local evaluation under their original terms.
"""
from io import BytesIO
import argparse
import json
from pathlib import Path
import time
import av
import numpy as np
from faster_whisper import WhisperModel
from app.speech.audio_processing import decode_audio


def excerpt(path, seconds=6):
    chunks = []
    with av.open(str(path)) as source:
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
        count = 0
        for frame in source.decode(audio=0):
            for converted in resampler.resample(frame):
                chunks.append(converted.to_ndarray().reshape(-1).copy())
                count += converted.samples
            if count >= seconds * 16000:
                break
        for converted in resampler.resample(None):
            chunks.append(converted.to_ndarray().reshape(-1).copy())
    return np.concatenate(chunks).astype("float32")[:seconds * 16000]


def run(root, output):
    fixtures = {p.stem: excerpt(p) for p in sorted((root / "human-comparison").glob("*.mp3"))}
    fixture_root = Path(__file__).resolve().parents[1] / "tests/fixtures/speech"
    for name in ("fr-bonjour.ogg", "en-us-hello.ogg"):
        fixtures[name] = decode_audio((fixture_root / name).read_bytes())[0]
    fixtures["silence"] = np.zeros(64000, dtype="float32")
    fixtures["noise"] = np.random.default_rng(42).normal(0, .03, 64000).astype("float32")
    english = root / "test-en.wav"
    if english.exists():
        fixtures["english_sentence_synthetic_control"] = decode_audio(english.read_bytes())[0]
    results = []
    for label, path in (("tiny", root / "asr"), ("base", root / "asr-base")):
        started = time.monotonic()
        model = WhisperModel(str(path), device="cpu", compute_type="int8", cpu_threads=2,
                             num_workers=1, local_files_only=True)
        load_seconds = round(time.monotonic() - started, 3)
        for name, audio in fixtures.items():
            for beam, language in ((3, None), (5, None), (5, "fr")):
                started = time.monotonic()
                rows, info = model.transcribe(audio, language=language, beam_size=beam,
                    task="transcribe", word_timestamps=True, vad_filter=True, temperature=0,
                    condition_on_previous_text=False, initial_prompt=None, max_new_tokens=180)
                rows = list(rows)
                row = dict(model=label, fixture=name, beam_size=beam, requested_language=language,
                    model_load_seconds=load_seconds, duration_seconds=len(audio)/16000,
                    elapsed_seconds=round(time.monotonic()-started, 3),
                    detected_language=info.language, language_probability=info.language_probability,
                    voiced_seconds=info.duration_after_vad, text=" ".join(s.text.strip() for s in rows),
                    segments=[dict(avg_logprob=s.avg_logprob, no_speech_prob=s.no_speech_prob) for s in rows])
                results.append(row)
                print(json.dumps(row, ensure_ascii=True), flush=True)
        del model
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.models, args.output)
