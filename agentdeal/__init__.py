"""AgentDeal - an open negotiation protocol and SDK for trusted agent-to-agent deals.

Quickstart::

    from agentdeal import negotiate, Buyer, Seller

    result = negotiate(
        buyer=Buyer(need="a curated APAC restaurant-pricing dataset", max_price=45.0),
        sellers=[
            Seller(id="seller_a", label="DataNorth",  cost_floor=32.0, opening_price=48.0,
                   pitch="freshest APAC coverage, daily updates"),
            Seller(id="seller_b", label="GridSource", cost_floor=36.0, opening_price=52.0,
                   pitch="widest historical depth, 5-year archive"),
        ],
        rounds=3,
        market_reference=True,
        fulfill=True,
    )
    print(result.final_price, result.winner, result.savings_pct)
"""

from __future__ import annotations

from .agents import Buyer, Seller, default_sellers
from .engine import negotiate
from .schemas import (
    FulfillmentResult,
    Identity,
    Message,
    NegotiationResult,
    Receipt,
)

__version__ = "0.1.0"

__all__ = [
    "negotiate",
    "Buyer",
    "Seller",
    "default_sellers",
    "Message",
    "Identity",
    "Receipt",
    "FulfillmentResult",
    "NegotiationResult",
    "__version__",
]
