from dataclasses import dataclass, field
from typing import Protocol


class ProviderUnavailable(Exception):
    """Safe operational failure; never return provider exception text to learners."""


@dataclass
class Generation:
    text: str
    model: str
    metadata: dict = field(default_factory=dict)


class Provider(Protocol):
    def health(self) -> bool: ...
    def generate(
        self, messages: list[dict], *, structured: dict | None = None
    ) -> Generation: ...
