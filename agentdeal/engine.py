"""The negotiation engine.

A turn-based loop. The "marketplace" *is* this loop - there is no separate
marketplace service. See §8 of the PRD for the full specification.

Public entry point: ``negotiate(...)``. An optional ``on_event`` callback lets a
caller (the FastAPI server) stream each turn as it happens; the SDK surface in
``__init__.py`` re-exports ``negotiate`` without needing it.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from typing import Any, Callable, Optional

from . import agents as A
from .config import env
from .agents import Buyer, Seller
from .integrations import (
    KimiUnavailable,
    TokenRouterUnavailable,
    fulfill as run_fulfillment,
    get_market_reference,
    issue_identity,
    kimi_available,
    kimi_chat,
    sign_settlement,
    tokenrouter_available,
    tokenrouter_chat,
)
from .protocol import ProtocolError, validate_message
from .schemas import Identity, Message, NegotiationResult
from .storage import persist_result

EventCallback = Callable[[dict[str, Any]], None]


# --- small helpers ----------------------------------------------------------

def _emit(on_event: Optional[EventCallback], event: dict[str, Any]) -> None:
    if on_event is not None:
        on_event(event)


def _extract_json(text: str) -> dict[str, Any]:
    """Pull a single JSON object out of a model response (tolerates fences/prose)."""
    if not text:
        raise ProtocolError("empty model response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # strip a leading ```json / ``` fence and trailing ```
        cleaned = cleaned.split("```", 2)[1] if cleaned.count("```") >= 2 else cleaned
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ProtocolError(f"no JSON object found in response: {text[:120]!r}")
    return json.loads(cleaned[start : end + 1])


def _render_transcript(transcript: list[Message]) -> str:
    lines = []
    for m in transcript:
        price = "-" if m.price is None else f"${m.price:g}"
        lines.append(f"[r{m.round}] {m.from_} {m.action} {price}: {m.message}")
    return "\n".join(lines)


def _provider_chat(provider: str, model: Optional[str]):
    """Resolve an agent's provider to (available, chat_callable).

    chat_callable(system, messages) -> raw text. Buyer uses Kimi; sellers may
    route to a specific model through TokenRouter.
    """
    if provider == "tokenrouter":
        return tokenrouter_available(), (lambda s, m: tokenrouter_chat(s, m, model or ""))
    return kimi_available(), (lambda s, m: kimi_chat(s, m))


def _agent_turn(
    *,
    system: str,
    transcript: list[Message],
    actor_id: str,
    identity_ref: str,
    provider: str,
    model: Optional[str],
    round_: int,
    fallback: Callable[[], dict[str, Any]],
) -> Message:
    """Run one agent turn through its provider, with a retry then deterministic
    fallback. If the provider is not configured, go straight to the fallback so
    the loop always produces a valid, constraint-respecting move.
    """
    available, chat = _provider_chat(provider, model)
    if not available:
        return validate_message(fallback())

    convo = _render_transcript(transcript)
    base_user = (
        f"Negotiation so far:\n{convo}\n\n"
        f"It is round {round_}. You are {actor_id}. Make your move now as a single "
        f"JSON object in the protocol schema. Output JSON only."
    )
    messages = [{"role": "user", "content": base_user}]

    last_err = ""
    last_raw = ""
    for attempt in range(2):
        try:
            raw = chat(system, messages)
            last_raw = raw
            data = _extract_json(raw)
            # The engine is authoritative for WHO is speaking, their VERIFIED
            # identity, and the ROUND. The model only decides action/price/terms/
            # message. This prevents identity spoofing and stops spurious
            # fallbacks when a model omits these fields.
            data["from"] = actor_id
            data["identity"] = identity_ref
            data["round"] = round_
            return validate_message(data)
        except (KimiUnavailable, TokenRouterUnavailable) as exc:
            # Network/availability problem - no point retrying the same call.
            last_err = f"{type(exc).__name__}: {exc}"
            break
        except (ProtocolError, json.JSONDecodeError, ValueError) as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt == 0:
                messages.append(
                    {
                        "role": "user",
                        "content": "That was not valid. Respond with ONLY one JSON object in the schema.",
                    }
                )
                continue
            break
    if env("AGENTDEAL_DEBUG"):
        print(
            f"[agentdeal] fallback for {actor_id} r{round_}: {last_err} | raw={last_raw[:240]!r}",
            file=sys.stderr,
        )
    return validate_message(fallback())


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# --- main entry point -------------------------------------------------------

def negotiate(
    buyer: Buyer,
    sellers: list[Seller],
    rounds: int = A.DEFAULT_ROUNDS,
    market_reference: bool = True,
    fulfill: bool = True,
    *,
    on_event: Optional[EventCallback] = None,
    negotiation_id: Optional[str] = None,
) -> NegotiationResult:
    """Run a multi-party negotiation and return a structured result."""
    neg_id = negotiation_id or f"neg_{uuid.uuid4().hex[:10]}"

    # 1. Setup - market reference (optional, never hard-blocks) -------------
    market_ref: Optional[float] = None
    market_sources: list[str] = []
    if market_reference:
        try:
            ref = get_market_reference(buyer.need)
            market_ref, market_sources = ref.price, ref.sources
        except Exception as exc:  # market is grounding, not load-bearing
            market_sources = [f"market reference unavailable: {exc}"]

    # Anchor the whole scenario (openings, floors, ceiling) to the market
    # reference so the negotiated deal lands a realistic ~10-20% below it.
    buyer, sellers = A.scale_to_market(buyer, sellers, market_ref)

    # 1b. Identities - REQUIRED for every party. No anonymous agents. -------
    identities: dict[str, Identity] = {}
    # The buyer is the user's real procurement agent -> use the real Terminal 3
    # tenant DID. Sellers are the reference seller set -> issued reference IDs.
    identities["buyer"] = issue_identity("AgentDeal Buyer", prefer_real=True)
    for s in sellers:
        identities[s.id] = issue_identity(s.label)

    buyer_ref = identities["buyer"].ref

    # Per-agent model labels (buyer on Kimi; sellers routed via TokenRouter).
    models: dict[str, str] = {"buyer": A.display_model(buyer.provider, buyer.model)}
    for s in sellers:
        models[s.id] = A.display_model(s.provider, s.model)

    # Seed transcript with the buyer broadcast.
    transcript: list[Message] = []

    def _append(msg: Message) -> Message:
        msg.ts = time.time()
        transcript.append(msg)
        _emit(on_event, {"type": "turn", "message": msg.model_dump(by_alias=True)})
        return msg

    _emit(
        on_event,
        {
            "type": "setup",
            "id": neg_id,
            "resource": buyer.need,
            "market_reference": market_ref,
            "market_sources": market_sources,
            "rounds": rounds,
            "identities": {k: v.model_dump() for k, v in identities.items()},
            "models": models,
        },
    )

    _append(validate_message(A.buyer_broadcast(buyer, buyer_ref, market_ref)))

    # 2. Rounds ------------------------------------------------------------
    active = {s.id: s for s in sellers}
    standing: dict[str, float] = {}  # seller_id -> latest standing offer price
    accepted = False
    winner_id: Optional[str] = None
    final_price: Optional[float] = None
    final_terms: dict[str, Any] = dict(A.DEFAULT_TERMS)

    for r in range(1, rounds + 1):
        # Sellers respond in order.
        for s in list(active.values()):
            lowest_competitor = min(
                (p for sid, p in standing.items() if sid != s.id), default=None
            )
            msg = _agent_turn(
                system=A.seller_system_prompt(s, rounds, identities[s.id].ref, market_ref),
                transcript=transcript,
                actor_id=s.id,
                identity_ref=identities[s.id].ref,
                provider=s.provider,
                model=s.model,
                round_=r,
                fallback=lambda s=s, r=r, lc=lowest_competitor: A.fallback_seller(
                    s, r, rounds, identities[s.id].ref, lc, market_ref
                ),
            )
            if msg.action == "reject":
                msg = _append(msg)
                active.pop(s.id, None)
                standing.pop(s.id, None)
                continue
            if msg.price is not None:
                msg.price = round(_clamp(msg.price, s.cost_floor, float("inf")), 2)
            _append(msg)
            # offer/counter set a standing price; a seller "accept" commits to the
            # price they just agreed to (otherwise the deal closes at a stale counter).
            if msg.price is not None and msg.action in ("offer", "counter", "accept"):
                standing[s.id] = msg.price

        if not standing:
            break  # everyone walked away

        # Buyer evaluates this round's standing offers.
        cheapest_id = min(standing, key=standing.get)
        cheapest_label = active[cheapest_id].label if cheapest_id in active else cheapest_id
        buyer_msg = _agent_turn(
            system=A.buyer_system_prompt(buyer, rounds, buyer_ref, market_ref),
            transcript=transcript,
            actor_id="buyer",
            identity_ref=buyer_ref,
            provider=buyer.provider,
            model=buyer.model,
            round_=r,
            fallback=lambda r=r: A.fallback_buyer(
                buyer, r, rounds, buyer_ref, dict(standing), cheapest_label, market_ref
            ),
        )
        if buyer_msg.price is not None:
            buyer_msg.price = round(_clamp(buyer_msg.price, 0.0, buyer.max_price), 2)
        _append(buyer_msg)

        if buyer_msg.action == "accept":
            # Close on the best standing offer at or below the ceiling.
            eligible = {sid: p for sid, p in standing.items() if p <= buyer.max_price}
            pool = eligible or standing
            winner_id = min(pool, key=lambda sid: (pool[sid], _first_offer_round(transcript, sid)))
            final_price = pool[winner_id]
            final_terms = buyer_msg.terms or _last_terms(transcript, winner_id) or dict(A.DEFAULT_TERMS)
            accepted = True
            break

    # 2b. Force-close if no explicit accept happened. ----------------------
    forced = False
    if not accepted:
        eligible = {sid: p for sid, p in standing.items() if p <= buyer.max_price}
        pool = eligible or standing
        if not pool:
            raise RuntimeError("negotiation failed: no seller produced a usable offer")
        forced = True
        winner_id = min(pool, key=lambda sid: (pool[sid], _first_offer_round(transcript, sid)))
        final_price = pool[winner_id]
        final_terms = _last_terms(transcript, winner_id) or dict(A.DEFAULT_TERMS)

    assert winner_id is not None and final_price is not None

    # 3. Settlement --------------------------------------------------------
    deal = {
        "resource": buyer.need,
        "price": final_price,
        "terms": final_terms,
        "winner": winner_id,
        "negotiation_id": neg_id,
    }
    receipt = sign_settlement(deal, identities["buyer"], identities[winner_id])

    savings_pct: Optional[float] = None
    if market_ref:
        savings_pct = round((market_ref - final_price) / market_ref * 100, 1)

    _emit(
        on_event,
        {
            "type": "settlement",
            "winner": winner_id,
            "final_price": final_price,
            "final_terms": final_terms,
            "savings_pct": savings_pct,
            "receipt": receipt.model_dump(),
        },
    )

    # 4. Fulfillment -------------------------------------------------------
    fulfillment = None
    if fulfill:
        try:
            fulfillment = run_fulfillment(deal)
            _emit(on_event, {"type": "fulfillment", "fulfillment": fulfillment.model_dump()})
        except Exception as exc:  # fulfillment is the closing flourish, not load-bearing
            _emit(on_event, {"type": "fulfillment_error", "error": str(exc)})

    # 5. Persist + return --------------------------------------------------
    result = NegotiationResult(
        id=neg_id,
        resource=buyer.need,
        market_reference=market_ref,
        market_sources=market_sources,
        final_price=final_price,
        final_terms=final_terms,
        winner=winner_id,
        savings_pct=savings_pct,
        transcript=transcript,
        identities=identities,
        models=models,
        receipt=receipt,
        fulfillment=fulfillment,
        forced_close=forced,
    )
    persist_result(result)
    _emit(on_event, {"type": "done", "result": result.model_dump(by_alias=True)})
    return result


def _first_offer_round(transcript: list[Message], seller_id: str) -> int:
    for m in transcript:
        if m.from_ == seller_id and m.action in ("offer", "counter"):
            return m.round
    return 10_000


def _last_terms(transcript: list[Message], seller_id: str) -> Optional[dict[str, Any]]:
    for m in reversed(transcript):
        if m.from_ == seller_id and m.terms:
            return m.terms
    return None
