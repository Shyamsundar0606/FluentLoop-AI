import time
from functools import lru_cache
from pathlib import Path
from app.config import get_settings
from app.speech.audio_processing import decode_audio
from app.speech.schemas import Transcription, Segment, Word
from app.speech.asr_provider import SpeechUnavailable


@lru_cache
def model():
    from faster_whisper import WhisperModel

    s = get_settings()
    if s.speech_asr_provider != "faster_whisper":
        raise SpeechUnavailable("Unsupported ASR provider")
    path = asr_model_path()
    if not (path / "model.bin").is_file():
        raise SpeechUnavailable("ASR model unavailable")
    return WhisperModel(
        str(path),
        device=s.speech_asr_device,
        compute_type=s.speech_asr_compute_type,
        cpu_threads=2,
        num_workers=1,
        local_files_only=True,
    )


def asr_model_path():
    settings = get_settings()
    # Keep existing Tiny installations and allow a separately provisioned Base.
    # Choosing a model must select its weights, not just relabel a Tiny result.
    directory = "asr" if settings.speech_asr_model == "tiny" else "asr-base"
    return Path(settings.speech_model_path) / directory


def transcribe(data):
    s = get_settings()
    started = time.monotonic()
    audio, duration, quality,metadata = decode_audio(data, s.speech_max_duration_seconds,include_metadata=True)
    base = dict(duration_ms=duration, model=s.speech_asr_model, audio_quality=quality,**metadata)
    if "silence_or_very_quiet" in quality:
        return Transcription(status="no_speech", **base).model_dump()
    if "clipping" in quality:
        return Transcription(status="insufficient_audio", **base).model_dump()
    # Keep independent language detection: forcing French alone is not evidence
    # that the recording contains French. Ambiguous language predictions need review.
    segments, info = model().transcribe(
        audio,
        language=None,
        task="transcribe",
        beam_size=3,
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
        temperature=0,
        initial_prompt=None,
        max_new_tokens=180,
    )
    base.update(
        detected_language=info.language,
        language_detection_probability=info.language_probability,
    )
    # VAD can remove all speech even when noise passes the signal-level check.
    # Its arbitrary language prediction on an empty waveform is not meaningful.
    if info.duration_after_vad <= 0:
        return Transcription(status="no_speech", **base).model_dump()
    constrained = False
    if info.language != "fr":
        if info.language_probability < 0.8:
            # A low-confidence top language is not a definitive non-French
            # finding. Show a French hypothesis as uncertain, never automatic
            # tutor input. Total recording length (including silence) must not
            # decide whether an ambiguous language prediction is recoverable.
            segments, _ = model().transcribe(
                audio,
                language="fr",
                task="transcribe",
                beam_size=3,
                word_timestamps=True,
                vad_filter=True,
                condition_on_previous_text=False,
                temperature=0,
                max_new_tokens=60,
            )
            constrained = True
        else:
            return Transcription(
                status="non_french", language=info.language, **base
            ).model_dump()
    rows = list(segments)
    if not rows:
        return Transcription(status="no_speech", language="fr", **base).model_dump()
    text = " ".join(x.text.strip() for x in rows).strip()
    uncertain = (
        constrained
        or info.language_probability < 0.45
        or any(x.avg_logprob < -1.2 or x.no_speech_prob > 0.75 for x in rows)
    )
    return Transcription(
        status="uncertain" if uncertain else "transcribed",
        language="fr",
        language_mode="constrained" if constrained else "detected",
        text=text[:4000],
        segments=[
            Segment(text=x.text[:4000], start=max(0, x.start), end=min(30, x.end))
            for x in rows[:100]
        ],
        words=[
            Word(text=w.word[:200], start=max(0, w.start), end=min(30, w.end))
            for x in rows
            for w in (x.words or [])
        ][:500],
        processing_ms=round((time.monotonic() - started) * 1000),
        **base
    ).model_dump()
