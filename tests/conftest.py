"""Force tests to run in deterministic offline mode.

Once real sponsor keys live in ``.env``, the SDK would otherwise make live,
non-deterministic calls during the test run. These tests assert the tuned
offline scenario (Seller A wins $38, 24% saved), so we blank the sponsor keys
for every test. ``config.env()`` treats an empty string as unset.
"""

import pytest

_SPONSOR_KEYS = [
    "KIMI_API_KEY",
    "TERMINAL3_API_KEY",
    "BRIGHTDATA_API_KEY",
    "DAYTONA_API_KEY",
    "TOKENROUTER_API_KEY",
]


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    for key in _SPONSOR_KEYS:
        monkeypatch.setenv(key, "")
    yield
