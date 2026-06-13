"""The reference set of seller agents AgentDeal ships with - and how to add your own.

The seller side is a *reference implementation*, not a live external network.
Anyone can define a new ``Seller`` that speaks the AgentDeal protocol and drop it
into ``negotiate(...)``; that is what "make your agent negotiable" means in the
README. An open seller network is future work.

Run this file to negotiate against a custom three-seller field::

    python examples/reference_sellers.py
"""

from __future__ import annotations

from agentdeal import Buyer, Seller, negotiate

# The two reference sellers from the tuned scenario, plus a third you might add.
REFERENCE_SELLERS = [
    Seller(id="seller_a", label="DataNorth", cost_floor=32.0, opening_price=48.0,
           pitch="freshest APAC coverage, daily updates"),
    Seller(id="seller_b", label="GridSource", cost_floor=36.0, opening_price=52.0,
           pitch="widest historical depth, 5-year archive"),
]

# To make YOUR agent negotiable, implement a Seller with a cost floor and an
# opening price. It will speak the protocol via the same engine + prompts.
MY_SELLER = Seller(
    id="seller_c",
    label="EdgeFeeds",
    cost_floor=34.0,
    opening_price=50.0,
    pitch="lowest-latency streaming updates",
)


def main() -> None:
    result = negotiate(
        buyer=Buyer(need="access to a curated APAC restaurant-pricing dataset", max_price=45.0),
        sellers=[*REFERENCE_SELLERS, MY_SELLER],
        rounds=3,
        market_reference=True,
        fulfill=False,
    )
    print(f"winner={result.winner}  final=${result.final_price:.2f}  saved={result.savings_pct}%")
    for m in result.transcript:
        price = "" if m.price is None else f"${m.price:.2f}"
        print(f"  r{m.round} {m.from_:<9} {m.action:<9} {price:>8}  {m.message}")


if __name__ == "__main__":
    main()
