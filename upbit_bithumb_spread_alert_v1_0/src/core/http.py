import time
from typing import Any, Dict, Optional

import requests


class HttpClient:
    def __init__(self, timeout: int = 10, retries: int = 3, backoff_seconds: float = 0.7):
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        raise RuntimeError(f"GET {url} failed after {self.retries} retries: {last_error}")
