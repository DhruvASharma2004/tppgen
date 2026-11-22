"""Shared HTTP helper: retries, rate limiting, and a single place to see failures."""
from __future__ import annotations

import time
from typing import Any

import requests

USER_AGENT = "tppgen/0.1 (public-data TPP generator; research use)"


class ApiError(RuntimeError):
    """Raised when a source cannot be reached. Never swallowed into a fabricated field."""


def request(
    method: str,
    url: str,
    *,
    min_interval: float = 0.0,
    attempts: int = 3,
    **kwargs: Any,
) -> dict:
    """One request with backoff. min_interval spaces calls for sources that ask for it."""
    last: Exception | None = None
    headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
    for attempt in range(attempts):
        try:
            resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code >= 400:
                # A 4xx body usually names the problem (a GraphQL field that no
                # longer exists, a malformed search). Losing it makes the error useless.
                detail = resp.text[:600].replace("\n", " ")
                raise RuntimeError(f"HTTP {resp.status_code}: {detail}")
            if min_interval:
                time.sleep(min_interval)
            return resp.json()
        except RuntimeError as exc:  # a 4xx: our request is wrong, retrying cannot help
            raise ApiError(f"{method} {url} -> {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - surfaced, not hidden
            last = exc
            time.sleep(2 ** attempt)
    raise ApiError(f"{method} {url} failed after {attempts} attempts: {last}")
