"""The AgentDeal Protocol.

A single message type is exchanged by every party in a negotiation. This module
defines that message, its validation rules, and the schema snippet that gets
injected into agent prompts so models emit conformant JSON.

Action semantics
----------------
- ``broadcast`` - the buyer announces the need + budget intent (``price`` may be
  null or a target).
- ``offer``     - a seller proposes a price/terms.
- ``counter``   - buyer or seller responds with a revised price/terms.
- ``accept``    - closes the deal at the most recent offer's price/terms.
- ``reject``    - declines to continue (e.g. a seller hitting its floor).

Validation rules (enforced by ``validate_message``)
---------------------------------------------------
- ``identity`` must be present and non-empty on EVERY message. A message without
  identity is invalid and rejected by the engine. This is the protocol's whole
  point: untrusted agents cannot transact anonymously.
- ``price`` is required for ``offer`` / ``counter`` / ``accept``.
- ``action`` must be in the allowed set.
- ``round`` must be a positive integer.
"""

from __future__ import annotations

import json
from typing import Any

from .schemas import Message

ALLOWED_ACTIONS = ("broadcast", "offer", "counter", "accept", "reject")
PRICE_REQUIRED_ACTIONS = ("offer", "counter", "accept")


class ProtocolError(ValueError):
    """Raised when a message violates the AgentDeal protocol."""


# Human-readable schema injected into agent system prompts. Kept terse on
# purpose: models copy its shape.
SCHEMA_HINT = json.dumps(
    {
        "from": "<your agent id>",
        "identity": "<your verified identity reference>",
        "action": "broadcast | offer | counter | accept | reject",
        "price": "number (required for offer/counter/accept; null for broadcast)",
        "terms": {"quantity": 1, "delivery": "standard | express"},
        "message": "2-4 substantive sentences: justify your price, engage the competing offer, cite terms",
        "round": 1,
    },
    indent=2,
)


def validate_message(raw: dict[str, Any]) -> Message:
    """Validate a raw decoded message dict and return a typed ``Message``.

    Raises ``ProtocolError`` on any violation of the rules above.
    """
    if not isinstance(raw, dict):
        raise ProtocolError(f"message must be a JSON object, got {type(raw).__name__}")

    # Accept both "from" (wire) and "from_" (python) keys.
    sender = raw.get("from", raw.get("from_"))
    if not sender or not str(sender).strip():
        raise ProtocolError("message is missing 'from'")

    identity = raw.get("identity")
    if not identity or not str(identity).strip():
        # The trust field. No identity -> not a valid party. Reject.
        raise ProtocolError("message is missing required 'identity' (anonymous agents are rejected)")

    action = raw.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ProtocolError(f"invalid action {action!r}; must be one of {ALLOWED_ACTIONS}")

    price = raw.get("price")
    if action in PRICE_REQUIRED_ACTIONS:
        if price is None:
            raise ProtocolError(f"action {action!r} requires a numeric 'price'")
        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ProtocolError(f"'price' must be numeric, got {price!r}")
    elif price is not None:
        try:
            price = float(price)
        except (TypeError, ValueError):
            price = None

    round_ = raw.get("round", 1)
    try:
        round_ = int(round_)
    except (TypeError, ValueError):
        raise ProtocolError(f"'round' must be an integer, got {round_!r}")
    if round_ < 1:
        raise ProtocolError("'round' must be a positive integer")

    terms = raw.get("terms")
    if terms is not None and not isinstance(terms, dict):
        raise ProtocolError("'terms' must be an object or null")

    return Message(
        from_=str(sender),
        identity=str(identity),
        action=action,
        price=price,
        terms=terms,
        message=str(raw.get("message", "")),
        round=round_,
    )


def is_closing(msg: Message) -> bool:
    """Whether a message closes the deal."""
    return msg.action == "accept"
