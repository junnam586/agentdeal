"""Kimi adapter - the reasoning behind every agent turn (buyer + sellers).

This is the only integration on the hot path: it is called once per agent per
round. Kimi (Moonshot) exposes an OpenAI-compatible chat-completions API, so the
adapter speaks that shape.

Internal contract:
    kimi_chat(system: str, messages: list[dict]) -> str
returning the agent's raw JSON protocol message as a string.

If ``KIMI_API_KEY`` is not set, ``kimi_available()`` is False and the engine
drives the negotiation with the deterministic fallback in ``agents.py`` instead
of fabricating a response here.
"""

from __future__ import annotations

import httpx

from ..config import env

DEFAULT_BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_MODEL = "kimi-k2.6"
# kimi-k2.* are reasoning models; longer-context turns can take a while. Keep a
# generous read timeout so genuine turns don't fall back to the deterministic move.
TIMEOUT_SECONDS = 120.0


class KimiUnavailable(RuntimeError):
    """Raised when Kimi is not configured or the call fails."""


def kimi_available() -> bool:
    return env("KIMI_API_KEY") is not None


def kimi_chat(system: str, messages: list[dict]) -> str:
    """Run one chat completion and return the assistant's raw text.

    ``messages`` is the running conversation as a list of ``{"role", "content"}``
    dicts; ``system`` is prepended as the system message.
    """
    api_key = env("KIMI_API_KEY")
    if not api_key:
        raise KimiUnavailable("KIMI_API_KEY is not set")

    base_url = (env("KIMI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = env("KIMI_MODEL") or DEFAULT_MODEL

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
        # kimi-k2.* models require temperature == 1 (they reject other values).
        "temperature": 1,
        # Nudge the model toward a single JSON object. Harmless if the endpoint
        # ignores it; many OpenAI-compatible servers honor it.
        "response_format": {"type": "json_object"},
    }

    # TODO(sponsor-docs): confirm endpoint path, model id, and that
    # response_format is supported per the Kimi/Moonshot console docs.
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise KimiUnavailable(f"Kimi call failed: {exc}") from exc
