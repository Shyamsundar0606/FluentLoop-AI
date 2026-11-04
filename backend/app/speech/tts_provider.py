from typing import Protocol


class TTSProvider(Protocol):
    def synthesize(self, text: str) -> bytes: ...
