"""Run a full AgentDeal negotiation in the terminal.

    python examples/run_demo.py

With a ``KIMI_API_KEY`` configured, every turn is produced by real Kimi
reasoning. Without one, the demo runs in offline mode using the deterministic
fallback so you still see a clean, converging 3-round negotiation out of the box.
"""

from __future__ import annotations

from agentdeal import Buyer, default_sellers, negotiate
from agentdeal.agents import display_model
from agentdeal.integrations import (
    brightdata_available,
    daytona_available,
    kimi_available,
    terminal3_available,
    tokenrouter_available,
)

LINE = "─" * 68


def status(name: str, ok: bool) -> str:
    return f"  {name:<12} {'live ✓' if ok else 'offline (no key)'}"


def main() -> None:
    print(LINE)
    print("AgentDeal - trusted agent-to-agent negotiation")
    print(LINE)
    print("Integrations:")
    print(status("Kimi", kimi_available()))
    print(status("TokenRouter", tokenrouter_available()))
    print(status("Terminal 3", terminal3_available()))
    print(status("Bright Data", brightdata_available()))
    print(status("Daytona", daytona_available()))
    print(LINE)

    buyer = Buyer()
    sellers = default_sellers()
    print("Model routing:")
    print(f"  buyer        {display_model(buyer.provider, buyer.model)}")
    for s in sellers:
        print(f"  {s.label:<12} {display_model(s.provider, s.model)}  (via {s.provider})")
    print(LINE)

    result = negotiate(
        buyer=buyer,  # default APAC dataset scenario
        sellers=sellers,
        rounds=3,
        market_reference=True,
        fulfill=True,
    )

    print(f"Resource     : {result.resource}")
    if result.market_reference is not None:
        src = result.market_sources[0] if result.market_sources else ""
        print(f"Market ref   : ${result.market_reference:.2f}  ({src})")
    print(LINE)
    print("Negotiation transcript")
    print(LINE)
    for m in result.transcript:
        price = "       " if m.price is None else f"${m.price:>6.2f}"
        verified = "⬡" if result.identities.get(m.from_, None) and result.identities[m.from_].verified else "·"
        print(f"  r{m.round} {verified} {m.from_:<9} {m.action:<9} {price}  {m.message}")

    print(LINE)
    win = result.identities.get(result.winner)
    win_label = win.label if win else result.winner
    print(f"WINNER       : {win_label} ({result.winner})")
    print(f"FINAL PRICE  : ${result.final_price:.2f}")
    if result.savings_pct is not None:
        print(f"SAVED        : {result.savings_pct:.1f}%  vs ${result.market_reference:.2f} market ref")
    print(LINE)
    print("Settlement receipt (Terminal 3)")
    print(f"  buyer      : {result.receipt.buyer.label}  {result.receipt.buyer.ref}")
    print(f"  seller     : {result.receipt.seller.label}  {result.receipt.seller.ref}")
    print(f"  signed_ref : {result.receipt.signed_ref}")
    if result.fulfillment is not None:
        print(LINE)
        print("Fulfillment (Daytona)")
        print(f"  sandbox    : {result.fulfillment.sandbox_id}")
        print(f"  output     : {result.fulfillment.output}")
    print(LINE)
    print(f"Saved to saved/{result.id}.json")
    print(LINE)


if __name__ == "__main__":
    main()
