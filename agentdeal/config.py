"""Central config: loads ``.env`` once and exposes small helpers.

Every credential lives in ``.env`` (see ``.env.example``). Each integration
reads its keys through here. When a key is absent the corresponding adapter
falls back to a clearly-labeled offline path so the repo runs out of the box.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


def env(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return default
    return val


def has(key: str) -> bool:
    return env(key) is not None
