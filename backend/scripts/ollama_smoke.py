"""Explicit live-provider smoke checks; no database access or model downloads."""

from app.config import Settings
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.base import ProviderUnavailable
from app.ai.prompts import build_messages
from app.ai.response_schemas import Correction
from app.ai.orchestrator import validate_answer

model = "llama3.2:3b"
provider = OllamaProvider(
    Settings(ollama_base_url="http://127.0.0.1:11434", ollama_model=model)
)
assert provider.health()
for question, errors in [("Je suis 24 ans.", True), ("Je suis étudiant.", False)]:
    output = provider.generate(
        build_messages("A1", "correction", question, [], []),
        structured=Correction.model_json_schema(),
    )
    _, feedback = validate_answer(output, "correction", question, "A1", [])
    assert feedback.has_errors is errors
    if errors:
        assert feedback.corrected_text.replace("’", "'") == "J'ai 24 ans."
    else:
        assert feedback.corrected_text == question
    print("PASS live correction sample:", question)
answer = provider.generate(
    build_messages(
        "A1", "tutor", "What does bonjour mean? Give one short French example.", [], []
    )
)
assert answer.text
print("PASS live ungrounded A1 response; no platform sources supplied")
for label, settings in [
    (
        "connection refused",
        Settings(ollama_base_url="http://127.0.0.1:1", ollama_model=model),
    ),
    (
        "missing model",
        Settings(
            ollama_base_url="http://127.0.0.1:11434",
            ollama_model="missing-milestone05:no-download",
        ),
    ),
    (
        "one-second generation timeout",
        Settings(
            ollama_base_url="http://127.0.0.1:11434",
            ollama_model=model,
            ai_request_timeout_seconds=1,
        ),
    ),
]:
    test = OllamaProvider(settings)
    try:
        test.generate(
            [
                {
                    "role": "user",
                    "content": "Write a long detailed French essay of at least 1000 words about language learning.",
                }
            ]
        )
    except ProviderUnavailable:
        print("PASS live controlled failure:", label)
    else:
        raise AssertionError("Expected controlled failure: " + label)
    finally:
        test.client.close()
provider.client.close()
