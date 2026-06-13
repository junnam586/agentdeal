# AgentDeal

**An open negotiation protocol and SDK for trusted agent-to-agent deals.**

Fixed-price agent commerce is solved - x402 and friends have moved 75M+ transactions. But every one of those is *take-it-or-leave-it at a posted price*. **Negotiated** commerce between agents that don't trust each other is not solved. AgentDeal is that layer.

```python
from agentdeal import negotiate, Buyer, Seller

result = negotiate(
    # the buyer reasons on Kimi
    buyer=Buyer(need="a curated APAC restaurant-pricing dataset"),
    # each seller reasons on a DIFFERENT model, routed through TokenRouter
    sellers=[
        Seller(id="seller_a", label="DataNorth",  cost_floor=32.0, opening_price=48.0,
               pitch="freshest APAC coverage, daily updates",
               provider="tokenrouter", model="openai/gpt-5.4"),
        Seller(id="seller_b", label="GridSource", cost_floor=36.0, opening_price=52.0,
               pitch="widest historical depth, 5-year archive",
               provider="tokenrouter", model="anthropic/claude-sonnet-4.6"),
    ],
    rounds=3,
)
print(result.winner)        # "seller_a"
print(result.final_price)   # ~10-20% below the live market reference
print(result.savings_pct)   # e.g. 15.0  - vs the real Bright Data market price
print(result.models)        # {"buyer": "kimi-k2.6", "seller_a": "openai/gpt-5.4", ...}
```

> **Cross-model by design.** The buyer runs on Kimi while the two sellers run on
> *different* models via TokenRouter, so this is a genuine cross-model
> negotiation. The opening/floor prices above are anchors: at runtime the whole
> scenario is **scaled to the live Bright Data market reference**, so the deal
> always lands a realistic ~10-20% below the real going rate (not at a hardcoded
> number).

---

## Why negotiate instead of picking the cheapest listed price?

Negotiation extracts value a sort-by-price comparison cannot. **Competitive pressure** drives sellers *below* their public price to win a specific deal, and **dynamic terms** (volume, delivery speed, bundling) can't be expressed as a single static number. AgentDeal demonstrates this directly: the deal closes *below every seller's posted price*.

Negotiation between strangers has always been gated by one thing - the cost of establishing trust. AgentDeal removes that gate with **verifiable agent identity**, so two agents that have never met can safely haggle and settle.

---

## Quickstart

```bash
pip install git+https://github.com/agentdeal/agentdeal.git
cp .env.example .env      # optional: add sponsor keys to go live
python examples/run_demo.py
```

Expected output (abridged; live numbers track the market reference):

```
Model routing:
  buyer        kimi-k2.6
  DataNorth    openai/gpt-5.4                (via tokenrouter)
  GridSource   anthropic/claude-sonnet-4.6  (via tokenrouter)
Market ref   : $27.00  (Bright Data: globaldata.com, datarade.ai, ...)

  r1  DataNorth   offer    $26   "We open at $26, materially below the $27 market reference, and the daily refresh is what keeps a live forecast from drifting ..."
  r1  GridSource  offer    $28   "GridSource opens at $28; our 5-year archive is what anchors your model against APAC seasonality ..."
  r1  buyer       counter  $24   "DataNorth is the sharper bid; against the $27 reference I'm at $24, and the keener seller takes it ..."
  ...
  r3  buyer       accept   $24   "Decided, DataNorth at $24, about 11% under the market reference. Deal."
WINNER : DataNorth (seller_a)   FINAL PRICE : $24.00   SAVED : 11.1% vs $27.00
```

> **Runs out of the box.** With no API keys, AgentDeal runs in **offline mode** using a deterministic concession fallback so you see a clean, converging negotiation immediately (the offline market reference is ~$50). Add keys to `.env` and every turn is real model reasoning, the buyer and each seller run on **different models** (Kimi + two TokenRouter models), the market reference is a real Bright Data price, identities are real verified credentials, and fulfillment runs in a real Daytona sandbox.

---

## The AgentDeal Protocol

A single message type is exchanged by every party. This is the reusable artifact.

```jsonc
{
  "from": "buyer" | "<seller_id>",   // who is speaking
  "identity": "<identity_ref>",       // verified credential reference - REQUIRED, the trust field
  "action": "broadcast" | "offer" | "counter" | "accept" | "reject",
  "price": 38.0,                      // number; null for a pure broadcast
  "terms": {                          // optional dynamic terms - what fixed-price can't express
    "quantity": 1,
    "delivery": "standard" | "express"
  },
  "message": "I can beat that - $38 for express.",  // human-readable, shown in the UI
  "round": 1
}
```

### Action semantics

| Action      | Meaning |
|-------------|---------|
| `broadcast` | Buyer announces the need + budget intent (`price` may be null or a target). |
| `offer`     | A seller proposes a price/terms. |
| `counter`   | Buyer or seller responds with a revised price/terms. |
| `accept`    | Closes the deal at the most recent offer's price/terms. |
| `reject`    | Declines to continue (e.g. a seller hitting its floor). |

### Validation rules (enforced in [`protocol.py`](agentdeal/protocol.py))

- **`identity` must be present and non-empty on every message.** A message without identity is invalid and rejected by the engine. *This is the protocol's whole point: untrusted agents cannot transact anonymously.*
- `price` is required for `offer` / `counter` / `accept`.
- `action` must be in the allowed set; `round` must be a positive integer.
- The engine additionally **clamps** any agent price to that agent's known floor/ceiling as a safety net only - agents respect their own constraints via prompt; clamping just prevents a malformed turn from breaking convergence.

---

## Make your agent negotiable

Implement a `Seller` with a cost floor and an opening price, and drop it into `negotiate(...)`. It will speak the protocol through the same engine and prompts - no extra glue.

```python
from agentdeal import Buyer, Seller, negotiate

my_seller = Seller(
    id="seller_c", label="EdgeFeeds",
    cost_floor=34.0, opening_price=50.0,
    pitch="lowest-latency streaming updates",
    provider="tokenrouter", model="x-ai/grok-4.3",   # reason on any TokenRouter model
)

result = negotiate(buyer=Buyer(), sellers=[my_seller, ...], rounds=3)
```

See [`examples/reference_sellers.py`](examples/reference_sellers.py) for a runnable three-seller field.

---

## Cross-model routing & market-scaled pricing

Every agent can reason on a **different model**, so a negotiation is genuinely
cross-model. By default the **buyer runs on Kimi** (`kimi-k2.6`) and each
**seller routes through [TokenRouter](https://tokenrouter.com)** to a different
provider — `openai/gpt-5.4` for DataNorth, `anthropic/claude-sonnet-4.6` for
GridSource. Set `provider="tokenrouter"` + `model="<provider/model>"` on any
agent (or `provider="kimi"` to use Kimi directly). The model each agent used is
returned in `result.models` and shown next to its byline in the UI.

Prices are **anchored to the live market**: once Bright Data returns the going
rate, `scale_to_market()` sizes every opening price, cost floor, and the buyer's
ceiling around it, so the negotiated deal lands a realistic **~10-20% below the
real market reference** for any resource — rather than converging on a hardcoded
number. The agents are told the market reference in their prompts and cite it as
they haggle.

---

## Identity & trust

Identity is a **first-class, required field** of every protocol message, not metadata bolted on.

- Every message carries its sender's `identity` reference, and the engine rejects any message that lacks one. The engine is also **authoritative** for who is speaking and their identity - the model never self-asserts identity - which prevents spoofing.
- The **buyer** authenticates to **Terminal 3** via the ADK (`@terminal3/t3n-sdk` - SIWE auth + an encrypted TEE session) and uses its real `did:t3n` tenant DID. Because that SDK is Node-only, this runs through a small Node sidecar (`agentdeal/integrations/terminal3_node/`) that the Python adapter shells out to once and caches.
- The **sellers** are the reference seller set AgentDeal ships, with issued reference identities (`did:agentdeal:ref:…`).
- At settlement, the receipt is signed **EIP-191** by the DID's authenticator key (recoverable to the authenticator address) and references *both* parties' identity refs - an attributable, verifiable record.

This is what lets two strangers transact: each is accountable, and the settlement is non-repudiable.

**Production signing path (next step):** issuing a full on-chain SD-JWT Verifiable Credential goes through a deployed Terminal 3 ADK WASM contract (the `sign-sd-jwt-vc` host interface) invoked via the t3n-sdk. The EIP-191 attestation above is the authenticator-key signature; the contract path is the on-chain VC. Without a Terminal 3 key, identities are labeled reference DIDs and the receipt is a local attestation hash.

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              Frontend (React)             │
                    │  StatusBar · AgentStations · Stream ·     │
                    │  ConvergenceMeter · Settlement · Fulfill  │
                    └──────────────┬────────────────────────────┘
                                   │  HTTP / SSE
                    ┌──────────────▼────────────────────────────┐
                    │           server.py (FastAPI)             │
                    │  POST /negotiate (run + stream + persist) │
                    │  GET  /negotiations/{id} (replay)         │
                    └──────────────┬────────────────────────────┘
                                   │  calls
                    ┌──────────────▼────────────────────────────┐
                    │            agentdeal (SDK)                │
                    │  negotiate() · engine · protocol · agents │
                    └──────────────┬────────────────────────────┘
                                   │  adapters
   ┌───────────┬───────────┬─────────┴─┬───────────┬───────────┐
   ▼           ▼           ▼           ▼           ▼
 Kimi      TokenRouter  Terminal 3  Bright Data   Daytona
(buyer      (seller      (identity   (market       (sandbox
 reasoning)  models)     + receipt)   price)        fulfillment)
```

| Layer | Tech |
|-------|------|
| Engine + SDK | Python 3.11+, Pydantic, httpx |
| Server | FastAPI, SSE (`sse-starlette`), uvicorn |
| Frontend | Vite + React + TypeScript + Tailwind + Framer Motion |
| Persistence | `saved/<id>.json` files (no database) |

**Sponsor integrations**, each doing genuine, load-bearing work at a specific point:

| Sponsor | Role | Where |
|---------|------|-------|
| **Kimi** (`kimi-k2.6`) | Reasoning for the **buyer** agent | every buyer turn |
| **TokenRouter** | Routes each **seller** to a different model (e.g. GPT-5.4, Claude Sonnet 4.6) | every seller turn |
| **Terminal 3** | Verified identity + attributable EIP-191 receipt | agent init; settlement |
| **Bright Data** | Real market reference price (the deal is scaled to ~10-20% below it) | once, before negotiation |
| **Daytona** | Sandboxed fulfillment of the purchased capability | once, after settlement |

Each is implemented as an adapter behind a fixed internal contract in [`agentdeal/integrations/`](agentdeal/integrations/). Credentials live in `.env`. Where a sponsor's exact request shape needs confirmation against its console docs, the call site is marked `# TODO(sponsor-docs)`; the contract holds regardless, so the system never hard-blocks on a single integration.

---

## Run the web interface

```bash
# 1. backend
pip install -e ".[server]"
python server.py                       # serves on :8000

# 2. frontend
cd frontend
npm install
npm run dev                            # serves on :5173, proxies the API

# 3. (only with a Terminal 3 key) install the Node identity sidecar
cd agentdeal/integrations/terminal3_node && npm install
```

The interface visualizes a live negotiation: verified identities, offers streaming round by round, the **convergence meter** closing the spread, and the settlement locking in. It supports **live mode** (consume SSE from `/negotiate?stream=true`) and **replay mode** (re-emit a saved negotiation through the identical event pipeline) - replay is the clean path for recording.

---

## Status & roadmap

AgentDeal ships with a **reference set of seller agents**, not a live external network. It is a working SDK + reference implementation, not a deployed marketplace.

- ✅ Open protocol with identity as a first-class, required field
- ✅ Multi-party turn-based negotiation engine
- ✅ Cross-model agents: Kimi buyer + a different model per seller via TokenRouter
- ✅ Market-scaled pricing: the deal lands ~10-20% below the live Bright Data reference
- ✅ Verified identity + EIP-191 receipts (Terminal 3), sandboxed fulfillment (Daytona)
- ✅ FastAPI server with SSE streaming + replay; React "Broadsheet" visualization
- ⏳ **An open seller network is future work** - today you bring your own sellers.

---

## License

[MIT](LICENSE).
