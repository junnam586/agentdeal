"""TokenRouter adapter, route individual agents to different models/providers.

TokenRouter (https://tokenrouter.com) is an OpenAI-compatible router across many
providers (OpenAI, Anthropic, Google, DeepSeek, Qwen, xAI, and more). AgentDeal
uses it so the two seller agents can each reason with a different model while the
buyer stays on Kimi, a genuinely cross-model negotiation.

Internal contract:
    tokenrouter_chat(system: str, messages: list[dict], model: str) -> str
returning the agent's raw JSON protocol message as a string.

If TOKENROUTER_API_KEY is unset, tokenrouter_available() is False and the engine
drives that agent with the deterministic fallback instead.
"""

from __future__ import annotations

import httpx

from ..config import env

# The base URL already includes the API version (e.g. .../v1); we append the
# OpenAI-compatible chat-completions path.
DEFAULT_BASE_URL = "https://api.tokenrouter.com/v1"
TIMEOUT_SECONDS = 120.0


class TokenRouterUnavailable(RuntimeError):
    """Raised when TokenRouter is not configured or the call fails."""


def tokenrouter_available() -> bool:
    return env("TOKENROUTER_API_KEY") is not None


def tokenrouter_chat(system: str, messages: list[dict], model: str) -> str:
    """Run one chat completion through TokenRouter for model and return the text."""
    api_key = env("TOKENROUTER_API_KEY")
    if not api_key:
        raise TokenRouterUnavailable("TOKENROUTER_API_KEY is not set")

    base_url = (env("TOKENROUTER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
        # temperature intentionally omitted: the router fronts many models, some
        # of which reject non-default temperatures. Provider defaults are fine.
    }

    # TODO(sponsor-docs): confirm the chat-completions path + any model-id quirks
    # against the TokenRouter console docs.
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise TokenRouterUnavailable("TokenRouter returned empty content")
        return content
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise TokenRouterUnavailable(f"TokenRouter call failed ({model}): {exc}") from exc
