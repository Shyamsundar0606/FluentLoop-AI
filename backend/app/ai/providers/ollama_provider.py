import json
import logging
from functools import lru_cache
from threading import BoundedSemaphore
from urllib.parse import urlsplit

import httpx

from app.config import get_settings
from app.ai.providers.base import Generation, ProviderUnavailable

logger = logging.getLogger(__name__)


class OllamaProvider:
    def __init__(self, settings=None, transport=None):
        self.settings = settings or get_settings()
        url = urlsplit(self.settings.ollama_base_url)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ProviderUnavailable("Invalid provider configuration")
        self.client = httpx.Client(
            base_url=self.settings.ollama_base_url.rstrip("/"),
            timeout=httpx.Timeout(self.settings.ai_request_timeout_seconds, connect=5),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            transport=transport,
            trust_env=False,
            follow_redirects=False,
        )
        self.slots = BoundedSemaphore(self.settings.ai_max_concurrent_requests)

    def health(self):
        try:
            response = self.client.get("/api/tags", timeout=5)
            response.raise_for_status()
            return bool(self.settings.ollama_model) and any(
                item.get("name") == self.settings.ollama_model
                for item in response.json().get("models", [])
            )
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return False

    def generate(self, messages, *, structured=None):
        if not self.slots.acquire(blocking=False):
            raise ProviderUnavailable("Generation capacity reached")
        try:
            if not self.health():
                logger.warning(
                    "ai_configured_model_unavailable",
                    extra={
                        "provider": "ollama",
                        "model_configured": bool(self.settings.ollama_model),
                    },
                )
                raise ProviderUnavailable("Configured model unavailable")
            payload = {
                "model": self.settings.ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": self.settings.ai_max_output_tokens,
                    "num_ctx": 8192,
                    "temperature": 0.2,
                },
                "keep_alive": "2m",
            }
            if structured:
                payload["format"] = structured
            # Read incrementally: a faulty provider must not allocate an unlimited response.
            with self.client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 100_000:
                        raise ProviderUnavailable("Provider response too large")
                body = json.loads(data)
            answer = body["message"]["content"]
            if (
                not isinstance(answer, str)
                or not answer.strip()
                or len(answer) > 12000
                or body.get("done") is not True
            ):
                raise ProviderUnavailable("Invalid provider output")
            metadata = {
                key: body[key]
                for key in ("prompt_eval_count", "eval_count", "total_duration")
                if isinstance(body.get(key), int)
            }
            return Generation(answer.strip(), self.settings.ollama_model, metadata)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "ai_provider_failure", extra={"failure_type": type(exc).__name__}
            )
            raise ProviderUnavailable("Model service unavailable") from None
        finally:
            self.slots.release()


@lru_cache
def get_provider():
    settings = get_settings()
    if settings.ai_provider != "ollama":
        logger.warning("ai_unsupported_provider_configuration")
        raise ProviderUnavailable("Unsupported provider")
    return OllamaProvider(settings)
