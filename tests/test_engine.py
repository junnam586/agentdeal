"""Engine tests — convergence, identity, and settlement invariants.

These run in offline mode (no sponsor keys), exercising the deterministic
fallback. They assert the acceptance-checklist guarantees hold.
"""

from agentdeal import Buyer, default_sellers, negotiate


def _run():
    return negotiate(
        buyer=Buyer(),
        sellers=default_sellers(),
        rounds=3,
        market_reference=True,
        fulfill=True,
        negotiation_id="test_run",
    )


def test_converges_to_realistic_discount():
    r = _run()
    m = r.market_reference  # 50.0 offline
    assert r.winner == "seller_a"
    assert r.final_price <= m * 0.90 + 0.5  # within the market-scaled buyer budget
    # The deal lands a realistic ~10-20% below the market reference.
    assert m * 0.78 <= r.final_price <= m * 0.92


def test_every_message_carries_identity():
    r = _run()
    assert r.transcript, "transcript should not be empty"
    for m in r.transcript:
        assert m.identity and m.identity.strip()


def test_market_reference_and_savings():
    r = _run()
    assert r.market_reference == 50.0
    assert r.savings_pct is not None and 8.0 <= r.savings_pct <= 22.0


def test_receipt_references_both_identities():
    r = _run()
    assert r.receipt.buyer.ref == r.identities["buyer"].ref
    assert r.receipt.seller.ref == r.identities[r.winner].ref
    assert r.receipt.signed_ref


def test_fulfillment_present_when_requested():
    r = _run()
    assert r.fulfillment is not None
    assert r.fulfillment.sandbox_id


def test_rounds_capped():
    r = _run()
    assert max(m.round for m in r.transcript) <= 3
