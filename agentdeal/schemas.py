"""Pydantic schemas for the AgentDeal protocol and negotiation results.

These are the wire types. ``Message`` is the single protocol message exchanged
by every party (see ``protocol.py`` and the README). Everything else describes
the artifacts a negotiation produces: verified identities, the settlement
receipt, fulfillment output, and the full ``NegotiationResult``.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Action = Literal["broadcast", "offer", "counter", "accept", "reject"]


class Message(BaseModel):
    """A single AgentDeal protocol message.

    ``from_`` serializes as ``"from"`` on the wire. ``identity`` is required and
    non-empty on every message - that is the protocol's whole point: untrusted
    agents cannot transact anonymously.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    identity: str
    action: Action
    price: Optional[float] = None
    terms: Optional[dict[str, Any]] = None
    message: str = ""
    round: int = 1
    ts: float = 0.0  # epoch seconds, stamped by the engine when appended


class Identity(BaseModel):
    """A verified agent identity issued by the trust layer (Terminal 3)."""

    label: str
    ref: str  # credential reference / DID
    verified: bool = False


class Receipt(BaseModel):
    """An attributable settlement record signed by the trust layer."""

    buyer: Identity
    seller: Identity
    price: float
    terms: dict[str, Any]
    signed_ref: str  # attributable record reference
    ts: float = 0.0


class FulfillmentResult(BaseModel):
    """Output of running the purchased capability in an isolated sandbox."""

    output: str
    sandbox_id: str


class NegotiationResult(BaseModel):
    """The structured outcome of a full negotiation."""

    id: str
    resource: str
    market_reference: Optional[float] = None
    market_sources: list[str] = Field(default_factory=list)
    final_price: float
    final_terms: dict[str, Any] = Field(default_factory=dict)
    winner: str  # seller id
    savings_pct: Optional[float] = None
    transcript: list[Message] = Field(default_factory=list)
    identities: dict[str, Identity] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)  # agent id -> model label
    receipt: Receipt
    fulfillment: Optional[FulfillmentResult] = None

    # Internal-only debugging flag; not surfaced in the UI.
    forced_close: bool = False
