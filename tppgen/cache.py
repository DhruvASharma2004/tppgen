"""Disk cache. Public APIs are rate-limited and slow; a repeat query should cost nothing."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path.home() / ".tppgen_cache"
DEFAULT_TTL = 60 * 60 * 24 * 7  # one week


def _key(namespace: str, payload: Any) -> Path:
    blob = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(blob.encode()).hexdigest()[:24]
    return CACHE_DIR / namespace / f"{digest}.json"


def get(namespace: str, payload: Any, ttl: int = DEFAULT_TTL) -> Any | None:
    path = _key(namespace, payload)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl:
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def put(namespace: str, payload: Any, value: Any) -> None:
    path = _key(namespace, payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
