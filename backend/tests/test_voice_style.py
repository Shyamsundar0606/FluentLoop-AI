import pytest
from app.ai.prompts import build_messages, POLICIES
from app.ai.orchestrator import validate_answer
from app.ai.providers.base import Generation, ProviderUnavailable
from app.speech.voice_orchestrator import french_portion


@pytest.mark.parametrize("level", ["A1", "A2", "B1", "B2", "C1", "C2"])
def test_voice_policy_replaces_text_style_and_keeps_identity_separate(level):
    messages = build_messages(level, "roleplay", "Je m'appelle Camille.", [], [],
        learner_first_name="Shyam", voice_practice=True)
    policy = messages[0]["content"]
    assert POLICIES[level] not in policy
    assert "Voice practice:" in policy and "at most one" in policy.lower()
    assert "Never mention learner profiles" in policy
    assert "explicitly identify the response as general model knowledge" not in policy
    assert "Shyam" not in policy and messages[-1]["content"] == "Je m'appelle Camille."
    assert "first_name" in messages[2]["content"]
    text = build_messages(level, "tutor", "Bonjour", [], [])
    assert POLICIES[level] in text[0]["content"] and "Voice practice:" not in text[0]["content"]


@pytest.mark.parametrize("answer", [
    "I obtained your name from your profile. Bonjour !",
    "D'après votre profil, vous vous appelez Shyam.",
    "The system instructions tell me your name.",
    "The retrieval metadata says this is a lesson.",
    "Bonjour ! Où habites-tu ? Tu aimes Paris ?",
    "Bonjour " + "très " * 36,
])
def test_voice_style_rejects_internal_explanations_and_long_or_multiple_questions(answer):
    with pytest.raises(ProviderUnavailable):
        validate_answer(Generation(answer, "fake"), "roleplay", "Bonjour", "A1", [], voice_practice=True)


def test_french_question_then_optional_english_is_accepted_and_only_french_spoken():
    answer = "Bonjour ! Tu aimes Paris ?\nEnglish: Aimes means like."
    result, _ = validate_answer(Generation(answer, "fake"), "roleplay", "Bonjour", "A1", [], voice_practice=True)
    assert result == answer
    assert french_portion(answer) == "Bonjour ! Tu aimes Paris ?"
