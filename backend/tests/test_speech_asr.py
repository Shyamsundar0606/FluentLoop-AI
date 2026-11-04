"""Language policy tests; native inference is verified separately with fixtures."""
from types import SimpleNamespace

import pytest
from app.speech import faster_whisper_provider as asr


def segment(text=" Bonjour !", **values):
    return SimpleNamespace(text=text, start=0, end=1, words=[],
                           avg_logprob=values.get("avg_logprob", -.9),
                           no_speech_prob=values.get("no_speech_prob", .05))


def provider(monkeypatch, *, duration=5200, voiced=1.6, language="ru", probability=.785,
             rows=None, quality=()):
    calls = []
    audio = object()
    monkeypatch.setattr(asr, "decode_audio", lambda *a, **k:
                        (audio, duration, list(quality), {"codec": "opus", "container": "webm"}))

    def transcribe(waveform, **options):
        assert waveform is audio
        assert options["vad_filter"] is True
        assert options["task"] == "transcribe"
        assert options["condition_on_previous_text"] is False
        calls.append(options["language"])
        return iter(rows if rows is not None else [segment()]), SimpleNamespace(
            language=language, language_probability=probability, duration_after_vad=voiced)

    monkeypatch.setattr(asr, "model", lambda: SimpleNamespace(transcribe=transcribe))
    return calls


@pytest.mark.parametrize("duration", [1200, 5200, 29000])
def test_short_voiced_french_hypothesis_survives_recording_silence(monkeypatch, duration):
    calls = provider(monkeypatch, duration=duration)
    result = asr.transcribe(b"fixture")
    assert calls == [None, "fr"]
    assert result["status"] == "uncertain"  # never automatic tutor input
    assert result["text"] == "Bonjour !"
    assert result["detected_language"] == "ru"
    assert result["language_detection_probability"] == .785
    assert result["language_mode"] == "constrained"
    assert result["duration_ms"] == duration


@pytest.mark.parametrize("voiced,probability", [(1.6, .8), (1.6, .99), (3, .82), (8, .99)])
def test_confident_non_french_stays_rejected(monkeypatch, voiced, probability):
    calls = provider(monkeypatch, language="en", voiced=voiced, probability=probability)
    result = asr.transcribe(b"fixture")
    assert result["status"] == "non_french" and not result["text"]
    assert calls == [None]


def test_long_low_confidence_language_prediction_is_not_definitive(monkeypatch):
    calls = provider(monkeypatch, duration=13260, voiced=10, language="pt", probability=.38375)
    result = asr.transcribe(b"fixture")
    assert calls == [None, "fr"]
    assert result["status"] == "uncertain" and result["text"] == "Bonjour !"


def test_vad_empty_noise_is_not_language_evidence(monkeypatch):
    calls = provider(monkeypatch, voiced=0, language="en", probability=.24)
    result = asr.transcribe(b"noise")
    assert result["status"] == "no_speech" and not result["text"]
    assert calls == [None]


@pytest.mark.parametrize("quality,status", [("silence_or_very_quiet", "no_speech"),
                                           ("clipping", "insufficient_audio")])
def test_signal_safeguards_precede_inference(monkeypatch, quality, status):
    calls = provider(monkeypatch, quality=[quality])
    assert asr.transcribe(b"fixture")["status"] == status
    assert calls == []


@pytest.mark.parametrize("rows,status", [([], "no_speech"),
    ([segment(avg_logprob=-1.3)], "uncertain"), ([segment(no_speech_prob=.8)], "uncertain")])
def test_empty_and_unreliable_decoding_never_accepted(monkeypatch, rows, status):
    provider(monkeypatch, language="fr", probability=.99, rows=rows)
    assert asr.transcribe(b"fixture")["status"] == status


def test_clear_detected_french_stays_accepted(monkeypatch):
    calls = provider(monkeypatch, language="fr", voiced=5, probability=.99)
    assert asr.transcribe(b"fixture")["status"] == "transcribed"
    assert calls == [None]


@pytest.mark.parametrize("name,directory", [("tiny", "asr"), ("base", "asr-base")])
def test_selected_model_uses_distinct_weights(monkeypatch, tmp_path, name, directory):
    monkeypatch.setattr(asr, "get_settings", lambda: SimpleNamespace(
        speech_model_path=str(tmp_path), speech_asr_model=name))
    assert asr.asr_model_path() == tmp_path / directory
