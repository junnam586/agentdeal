"""Sponsor integration adapters, each behind a fixed internal contract.

- ``kimi_client`` - agent reasoning (hot path)
- ``identity``    - Terminal 3 verified identity + attributable receipt
- ``market``      - Bright Data real market reference price
- ``fulfillment`` - Daytona sandboxed fulfillment
"""

from .fulfillment import daytona_available, fulfill
from .identity import issue_identity, sign_settlement, terminal3_available
from .kimi_client import KimiUnavailable, kimi_available, kimi_chat
from .market import MarketReference, brightdata_available, get_market_reference
from .tokenrouter_client import TokenRouterUnavailable, tokenrouter_available, tokenrouter_chat

__all__ = [
    "kimi_chat",
    "kimi_available",
    "KimiUnavailable",
    "tokenrouter_chat",
    "tokenrouter_available",
    "TokenRouterUnavailable",
    "issue_identity",
    "sign_settlement",
    "terminal3_available",
    "get_market_reference",
    "MarketReference",
    "brightdata_available",
    "fulfill",
    "daytona_available",
]
