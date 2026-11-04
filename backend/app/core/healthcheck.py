from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check_http_status(url: str, timeout: int = 5) -> bool:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status < 400
    except (HTTPError, URLError, TimeoutError, OSError):
        return False
