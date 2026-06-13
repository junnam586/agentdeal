"""Terminal 3 adapter - the trust layer.

The whole thesis: two agents that have never met can transact because each
carries a *verified identity*, and the settlement is an *attributable record*
referencing both.

Terminal 3's ADK is a **Node-only SDK** (SIWE auth + an encrypted TEE session +
a WASM crypto component) - there is no REST API. So real identity goes through a
small Node sidecar (``terminal3_node/auth.mjs``) that authenticates with the
developer key and reads the real tenant DID off the session. The Python side
shells out to it once and caches the result.

Internal contract (unchanged):
    issue_identity(agent_label: str, prefer_real: bool = False) -> Identity
    sign_settlement(deal: dict, buyer: Identity, seller: Identity) -> Receipt

Notes / honest boundaries:
- We have one developer key, so one real tenant DID. The **buyer** (the user's
  procurement agent) uses that real verified DID. The **sellers** are the
  reference seller set AgentDeal ships, with issued reference identities.
- The settlement receipt is signed with the DID's **authenticator key**
  (EIP-191 / personal_sign, recoverable to the authenticator address). Terminal
  3 doc: the sign-in wallet credential "is just an authenticator on that DID",
  so this is a verifiable attestation by the DID controller. Issuing a full
  on-chain SD-JWT Verifiable Credential is the production path and requires a
  deployed ADK WASM contract (``sign-sd-jwt-vc`` host interface) invoked via the
  t3n-sdk - see README "Identity & trust" for that next step.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from ..config import env
from ..schemas import Identity, Receipt

_NODE_DIR = Path(__file__).resolve().parent / "terminal3_node"
_AUTH_SCRIPT = _NODE_DIR / "auth.mjs"

# Cache the authenticated (address, did) for the process - the tenant DID is
# stable, and auth is a multi-second network round trip we don't want per agent.
_auth_cache: dict[str, tuple[str, str]] = {}


def _demo_ref(label: str) -> str:
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:16]
    return f"did:agentdeal:ref:{digest}"


def terminal3_available() -> bool:
    return env("TERMINAL3_API_KEY") is not None


def _terminal3_authenticate() -> Optional[tuple[str, str]]:
    """Authenticate via the Node sidecar; return (address, did) or None.

    Cached for the process. Any failure (no node, network, SDK error) returns
    None so the caller can fall back rather than killing the negotiation.
    """
    key = env("TERMINAL3_API_KEY")
    if not key:
        return None
    if "result" in _auth_cache:
        return _auth_cache["result"]
    try:
        proc = subprocess.run(
            ["node", str(_AUTH_SCRIPT)],
            cwd=str(_NODE_DIR),
            env={**os.environ, "T3N_API_KEY": key, "T3N_ENV": env("TERMINAL3_ENV") or "testnet"},
            capture_output=True,
            text=True,
            timeout=120,
        )
        lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
        if not lines:
            return None
        data = json.loads(lines[-1])
        if data.get("ok") and data.get("did"):
            result = (str(data.get("address", "")), str(data["did"]))
            _auth_cache["result"] = result
            return result
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None


def issue_identity(agent_label: str, prefer_real: bool = False) -> Identity:
    """Issue (or fetch) a verified identity for an agent.

    ``prefer_real=True`` (the buyer) authenticates to Terminal 3 and uses the
    real tenant DID. Sellers use issued reference identities.
    """
    if prefer_real and env("TERMINAL3_API_KEY"):
        auth = _terminal3_authenticate()
        if auth is not None:
            _, did = auth
            return Identity(label=agent_label, ref=did, verified=True)

    # Reference identity (reference seller set, or offline / auth-unavailable).
    return Identity(label=agent_label, ref=_demo_ref(agent_label), verified=False)


def sign_settlement(deal: dict, buyer: Identity, seller: Identity) -> Receipt:
    """Produce an attributable settlement record referencing both identities.

    When a Terminal 3 key is present, the record is signed (EIP-191) by the DID's
    authenticator key and is verifiable by recovering the signer address. Without
    a key, it falls back to a labeled local attestation hash.
    """
    now = time.time()
    price = float(deal["price"])
    terms = dict(deal.get("terms") or {})

    payload = json.dumps(
        {
            "buyer": buyer.ref,
            "seller": seller.ref,
            "price": price,
            "terms": terms,
            "resource": deal.get("resource"),
            "ts": now,
        },
        sort_keys=True,
    )

    key = env("TERMINAL3_API_KEY")
    if key:
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct

            signed = Account.sign_message(encode_defunct(text=payload), key)
            addr = Account.from_key(key).address
            # signed_ref is verifiable: recover_message(encode_defunct(text=payload),
            # signature=<sig>) == addr, the DID's authenticator.
            signed_ref = f"eip191:{addr}:{signed.signature.hex()}"
            return Receipt(buyer=buyer, seller=seller, price=price, terms=terms, signed_ref=signed_ref, ts=now)
        except Exception:
            pass  # fall through to local attestation

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
    return Receipt(buyer=buyer, seller=seller, price=price, terms=terms, signed_ref=f"t3:local:{digest}", ts=now)
