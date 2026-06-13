"""Agent definitions, system prompts, the tuned scenario, and a deterministic
fallback negotiator.

The fallback is used in two situations:

1. **Offline mode** - no ``KIMI_API_KEY`` is configured, so the repo still runs
   end-to-end out of the box and produces a clean, converging transcript.
2. **Recovery** - a real Kimi generation comes back malformed twice in a row;
   rather than kill the loop we play one safe, constraint-respecting move.

The fallback is a transparent concession heuristic, not a script of the
*dialogue*: with a real Kimi key every turn is produced by model reasoning under
the constraints in the system prompts below, and the engine only clamps prices
to each agent's known floor/ceiling as a safety net.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from .protocol import SCHEMA_HINT

# --- Tuned scenario defaults (produce a clean 3-round convergence) -----------
# Market reference (Bright Data) ~ $50.  Seller A wins around $38 (saved ~24%).
DEFAULT_NEED = "access to a curated APAC restaurant-pricing dataset"
DEFAULT_MAX_PRICE = 45.0
DEFAULT_ROUNDS = 3
DEFAULT_TERMS: dict[str, Any] = {"quantity": 1, "delivery": "standard"}

# The offline schedule lands the final price this fraction of the way up from the
# cost floor toward the opening price (i.e. close to the floor). Combined with
# scale_to_market(), the winning deal sits a realistic ~10-20% under the market
# reference rather than absurdly far below it.
TARGET_FRACTION = 0.18


# Default model routing. The buyer reasons on Kimi; each seller routes to a
# DIFFERENT model through TokenRouter, so the negotiation is genuinely cross-model.
DEFAULT_KIMI_MODEL = "kimi-k2.6"
DEFAULT_SELLER_A_MODEL = "openai/gpt-5.4"  # via TokenRouter (OpenAI)
DEFAULT_SELLER_B_MODEL = "anthropic/claude-sonnet-4.6"  # via TokenRouter (Anthropic)


class Buyer(BaseModel):
    need: str = DEFAULT_NEED
    max_price: float = DEFAULT_MAX_PRICE
    objective: str = "minimize"  # buyer tries to get the lowest price
    provider: str = "kimi"  # "kimi" | "tokenrouter"
    model: Optional[str] = None  # None -> provider default


class Seller(BaseModel):
    id: str
    label: str
    cost_floor: float
    opening_price: float
    pitch: str = ""
    provider: str = "kimi"  # "kimi" | "tokenrouter"
    model: Optional[str] = None  # for tokenrouter: the routed model id


def default_sellers() -> list[Seller]:
    """The reference set of seller agents shipped with AgentDeal."""
    return [
        Seller(
            id="seller_a",
            label="DataNorth",
            cost_floor=32.0,
            opening_price=48.0,
            pitch="freshest APAC coverage, daily updates",
            provider="tokenrouter",
            model=DEFAULT_SELLER_A_MODEL,
        ),
        Seller(
            id="seller_b",
            label="GridSource",
            cost_floor=36.0,
            opening_price=52.0,
            pitch="widest historical depth, 5-year archive",
            provider="tokenrouter",
            model=DEFAULT_SELLER_B_MODEL,
        ),
    ]


def display_model(provider: str, model: Optional[str]) -> str:
    """Human-facing model label for an agent (shown in the UI)."""
    if provider == "tokenrouter":
        return model or "tokenrouter"
    return model or DEFAULT_KIMI_MODEL


def scale_to_market(
    buyer: Buyer, sellers: list[Seller], market_reference: Optional[float]
) -> tuple[Buyer, list[Seller]]:
    """Anchor the scenario to the live market reference so the negotiated deal
    lands a realistic ~10-20% below it. Returns scaled copies and preserves
    seller order (the first seller stays the keener bidder)."""
    if not market_reference or market_reference <= 0:
        return buyer, sellers
    m = market_reference
    scaled_buyer = buyer.model_copy(update={"max_price": round(m * 0.90)})
    # (opening, floor) as fractions of the market reference, per seller position.
    fracs = [(0.98, 0.82), (1.05, 0.86)]
    scaled_sellers = [
        s.model_copy(
            update={
                "opening_price": round(m * (fracs[i] if i < len(fracs) else (1.03, 0.85))[0]),
                "cost_floor": round(m * (fracs[i] if i < len(fracs) else (1.03, 0.85))[1]),
            }
        )
        for i, s in enumerate(sellers)
    ]
    return scaled_buyer, scaled_sellers


# --- System prompts ---------------------------------------------------------

BUYER_SYSTEM = """You are a procurement agent representing a client. You negotiate to acquire: {need}.
Your maximum acceptable price is {max_price}. Your goal: secure the resource at the LOWEST price.
The current market reference price for this resource is {market}, sourced live via Bright Data.
Treat it as your anchor: a strong deal lands meaningfully below it, and you should cite it by name
when you press sellers.
You are negotiating with multiple competing sellers at once. Use competition as leverage:
when one seller offers a lower price, cite it by name and price to pressure the other.
Negotiate in good faith over at most {rounds} rounds. Accept the best offer at or below your
maximum once further gains look unlikely. Never reveal your exact maximum.
Your verified identity reference is: {identity_ref}. Include it in every message.

WRITING STYLE, this matters. The "message" field must be 2 to 4 substantive sentences, not a
one-liner. In it: state your number and justify it with concrete reasoning about fitness for the
workload; directly engage the competing offers (name the seller, cite their price, weigh their
claim); cite the market reference price when it strengthens your case; and reference terms
(delivery speed, volume) when they shift the value. Sound like a sharp, specific procurement lead,
never a chatbot. No filler, no emojis, no markdown, and do not use em dashes (use commas or periods).

Respond with ONLY one JSON object in this schema, no prose outside it:
{schema}"""

SELLER_SYSTEM = """You are a sales agent for {label}. Your edge: {pitch}.
Your cost floor is {cost_floor}. NEVER agree below it; reject instead.
Your opening price is {opening_price}. The market reference price for this resource is {market},
sourced via Bright Data; you can invoke it to justify your price, though the buyer will push below it.
You are competing against another seller for this deal, so you may lower your price strategically
to win, but protect your margin.
Negotiate over at most {rounds} rounds. If you win, you keep the customer.
Your verified identity reference is: {identity_ref}. Include it in every message.

WRITING STYLE, this matters. The "message" field must be 2 to 4 substantive sentences, not a
one-liner. In it: state your price and sell it with a concrete, specific argument for why your
edge ({pitch}) actually changes the buyer's outcome; rebut the competing seller's pitch head-on;
reference the market price and terms (like delivery speed) when useful. Sound like a sharp,
confident account exec who knows the product cold, never a chatbot. No filler, no emojis, no
markdown, and do not use em dashes (use commas or periods).

Respond with ONLY one JSON object in this schema, no prose outside it:
{schema}"""


def _market_phrase(market_reference: Optional[float]) -> str:
    return f"${market_reference:.0f}" if market_reference else "not available"


def buyer_system_prompt(
    buyer: Buyer, rounds: int, identity_ref: str, market_reference: Optional[float] = None
) -> str:
    return BUYER_SYSTEM.format(
        need=buyer.need,
        max_price=buyer.max_price,
        rounds=rounds,
        identity_ref=identity_ref,
        market=_market_phrase(market_reference),
        schema=SCHEMA_HINT,
    )


def seller_system_prompt(
    seller: Seller, rounds: int, identity_ref: str, market_reference: Optional[float] = None
) -> str:
    return SELLER_SYSTEM.format(
        label=seller.label,
        pitch=seller.pitch,
        cost_floor=seller.cost_floor,
        opening_price=seller.opening_price,
        rounds=rounds,
        identity_ref=identity_ref,
        market=_market_phrase(market_reference),
        schema=SCHEMA_HINT,
    )


# --- Deterministic fallback / offline negotiator ----------------------------

def buyer_broadcast(
    buyer: Buyer, identity_ref: str, market_reference: Optional[float] = None
) -> dict[str, Any]:
    """The opening buyer message that seeds the transcript."""
    market = (
        f"The market reference for this resource is about ${market_reference:.0f} per Bright Data, "
        "so I expect bids to open near there and fall. "
        if market_reference
        else ""
    )
    return {
        "from": "buyer",
        "identity": identity_ref,
        "action": "broadcast",
        "price": None,
        "terms": dict(DEFAULT_TERMS),
        "message": (
            f"Procurement notice: I'm sourcing {buyer.need} to feed a live forecasting workload. "
            f"{market}Two vetted sellers are bidding, and I'm optimizing price against "
            "fitness-for-purpose, not just the lowest sticker. Open your books; the best "
            "combination of price and coverage takes the contract."
        ),
        "round": 1,
    }


def _seller_offer_price(seller: Seller, round_: int, rounds: int) -> float:
    """Offline concession schedule: open high, walk linearly toward a target near
    the cost floor by the final round, never below it."""
    target = seller.cost_floor + (seller.opening_price - seller.cost_floor) * TARGET_FRACTION
    if rounds <= 1:
        price = target
    else:
        frac = (round_ - 1) / (rounds - 1)
        price = seller.opening_price - (seller.opening_price - target) * frac
    return round(max(price, seller.cost_floor), 0)


# Handcrafted, substantive copy for the two reference sellers, keyed by stage.
# Each line takes the seller's own price; competitor references stay qualitative
# so the copy stays correct if the scenario is retuned. {p} = own price.
_SELLER_LINES: dict[str, dict[str, str]] = {
    "seller_a": {  # DataNorth, freshness
        "open": (
            "DataNorth opens at ${p}. What you're buying is recency: our APAC restaurant pricing "
            "refreshes every 24 hours, so your model never trains on last quarter's reality. "
            "Freshness here isn't a feature, it's the whole product."
        ),
        "mid": (
            "We'll meet the pressure at ${p}. The archive across the table is deep, but depth "
            "without recency is just a confident wrong answer, and this number still keeps our "
            "daily pipeline funded while landing under the alternative."
        ),
        "final": (
            "Final position: ${p}, the floor where daily refresh still pays for itself. Below it "
            "the updates stop and you're only buying history. Put live signal at this price against "
            "a five-year archive nobody has touched since spring and the call makes itself."
        ),
    },
    "seller_b": {  # GridSource, depth
        "open": (
            "GridSource opens at ${p}. Our edge is memory: a clean, normalized five-year APAC "
            "restaurant-pricing archive. If anything in your workload is seasonal, that history is "
            "what stops a model from overfitting to one noisy cycle."
        ),
        "mid": (
            "I'll come to ${p}. Daily updates are easy to sell and hard to contextualize; without "
            "years of seasonality underneath, fresh data is a number with no baseline. You're "
            "paying for the baseline that makes the rest legible."
        ),
        "final": (
            "${p}, and that's GridSource sharpening to win: the long memory and a fair price on the "
            "same line. Recency you can bolt on later; five clean years of history you cannot "
            "manufacture overnight."
        ),
    },
}


def _seller_message(
    seller: Seller, price: float, round_: int, rounds: int, market_reference: Optional[float] = None
) -> str:
    stage = "open" if round_ <= 1 else ("final" if round_ >= rounds else "mid")
    lines = _SELLER_LINES.get(seller.id)
    if lines:
        msg = lines[stage].format(p=f"{price:.0f}")
    else:
        edge = seller.pitch or "our coverage"
        if stage == "open":
            msg = (
                f"{seller.label} opens at ${price:.0f}. You're paying for {edge}: in a real "
                f"workload that's the difference between signal and noise, and we don't discount "
                f"our edge lightly."
            )
        elif stage == "final":
            msg = (
                f"${price:.0f}, that's {seller.label} sharpening to win. {edge.capitalize()}, at a "
                f"number that holds our margin and still answers the competition. Weigh that "
                f"against the alternative and the choice is clear."
            )
        else:
            msg = (
                f"We'll move to ${price:.0f}. The other desk is in this, but {edge} is what "
                f"actually carries your outcome, and this price funds that while undercutting a "
                f"weaker offer."
            )
    if stage == "open" and market_reference:
        msg += f" Even at open that sits under the ${market_reference:.0f} Bright Data reference."
    return msg


def fallback_seller(
    seller: Seller,
    round_: int,
    rounds: int,
    identity_ref: str,
    lowest_competitor: Optional[float] = None,
    market_reference: Optional[float] = None,
) -> dict[str, Any]:
    price = _seller_offer_price(seller, round_, rounds)
    return {
        "from": seller.id,
        "identity": identity_ref,
        "action": "offer" if round_ <= 1 else "counter",
        "price": price,
        "terms": dict(DEFAULT_TERMS),
        "message": _seller_message(seller, price, round_, rounds, market_reference),
        "round": round_,
    }


def fallback_buyer(
    buyer: Buyer,
    round_: int,
    rounds: int,
    identity_ref: str,
    standing_offers: dict[str, float],
    cheapest_seller_label: str = "",
    market_reference: Optional[float] = None,
) -> dict[str, Any]:
    """Offline buyer move: pressure below the current lowest offer each round,
    then accept the best offer at or under the ceiling on the final round."""
    if not standing_offers:
        return buyer_broadcast(buyer, identity_ref, market_reference) | {"round": round_}

    cheapest_id = min(standing_offers, key=standing_offers.get)
    lowest = standing_offers[cheapest_id]
    is_final = round_ >= rounds

    leader = cheapest_seller_label or cheapest_id
    mref = f"${market_reference:.0f}" if market_reference else None

    if is_final and lowest <= buyer.max_price:
        anchor = f", and under the {mref} Bright Data reference" if mref else ""
        return {
            "from": "buyer",
            "identity": identity_ref,
            "action": "accept",
            "price": lowest,
            "terms": dict(DEFAULT_TERMS),
            "message": (
                f"Decided. {leader} at ${lowest:.0f}, comfortably inside budget, below every opening "
                f"bid on the table{anchor}. The coverage fits the workload, so that's the one. I'm "
                f"accepting now; let's settle and put both signatures on it."
            ),
            "round": round_,
        }

    # Counter just under the current lowest, citing the competition and market.
    factor = 0.75 + 0.11 * (round_ - 1)
    target = round(min(lowest * factor, lowest - 1.0), 0)
    if round_ <= 1:
        ref = f", still above where the {mref} market reference says this should land" if mref else ""
        msg = (
            f"Two strong cases, but I run a budget, not a charity. {leader} is lowest at ${lowest:.0f}"
            f"{ref}. For a live workload, fitness-for-purpose outweighs features I'll rarely query, so "
            f"I'm anchoring at ${target:.0f}. Whoever closes the gap fastest earns the contract."
        )
    else:
        ref = f" and over the {mref} reference" if mref else ""
        msg = (
            f"We're converging. {leader} leads at ${lowest:.0f} on both price and fit; the rest of "
            f"the field is still over my line{ref}. I'll move to ${target:.0f}, a genuine number, not "
            f"a tactic. Beat it and this gets signed today."
        )
    return {
        "from": "buyer",
        "identity": identity_ref,
        "action": "counter",
        "price": float(target),
        "terms": dict(DEFAULT_TERMS),
        "message": msg,
        "round": round_,
    }
