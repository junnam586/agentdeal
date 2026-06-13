"""Protocol validation tests — the trust field and message rules."""

import pytest

from agentdeal.protocol import ProtocolError, validate_message


def _base(**over):
    msg = {
        "from": "buyer",
        "identity": "did:agentdeal:demo:abc",
        "action": "counter",
        "price": 40.0,
        "round": 1,
        "message": "hi",
    }
    msg.update(over)
    return msg


def test_valid_message_round_trips():
    m = validate_message(_base())
    assert m.from_ == "buyer"
    assert m.action == "counter"
    assert m.price == 40.0


def test_missing_identity_is_rejected():
    raw = _base()
    del raw["identity"]
    with pytest.raises(ProtocolError):
        validate_message(raw)


def test_empty_identity_is_rejected():
    with pytest.raises(ProtocolError):
        validate_message(_base(identity="  "))


def test_offer_requires_price():
    with pytest.raises(ProtocolError):
        validate_message(_base(action="offer", price=None))


def test_broadcast_allows_null_price():
    m = validate_message(_base(action="broadcast", price=None))
    assert m.price is None


def test_unknown_action_rejected():
    with pytest.raises(ProtocolError):
        validate_message(_base(action="haggle"))


def test_round_must_be_positive():
    with pytest.raises(ProtocolError):
        validate_message(_base(round=0))
