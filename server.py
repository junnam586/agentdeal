"""AgentDeal HTTP server (FastAPI).

Endpoints
---------
POST /negotiate?stream=true|false[&delay=<sec>]
    Run a negotiation. ``stream=true`` returns Server-Sent Events — one event per
    engine turn — for live mode. ``stream=false`` returns the full
    ``NegotiationResult`` JSON. Persists either way.
GET  /negotiations/{id}
    Return a saved ``NegotiationResult`` for replay mode.
GET  /negotiations
    List saved negotiation ids + summaries (for a picker).

Event contract (identical for live SSE and reconstructed by replay):
    setup -> ordered turn events -> settlement -> optional fulfillment -> done
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agentdeal import Buyer, Seller, default_sellers, negotiate
from agentdeal.storage import list_results, load_result

app = FastAPI(title="AgentDeal", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # open for local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


class SellerSpec(BaseModel):
    id: str
    label: str
    cost_floor: float
    opening_price: float
    pitch: str = ""


class NegotiateRequest(BaseModel):
    resource: Optional[str] = None
    max_price: Optional[float] = None
    rounds: int = 3
    market_reference: bool = True
    fulfill: bool = True
    sellers: Optional[list[SellerSpec]] = None


def _build_inputs(body: NegotiateRequest):
    buyer = Buyer(
        **{
            k: v
            for k, v in {"need": body.resource, "max_price": body.max_price}.items()
            if v is not None
        }
    )
    if body.sellers:
        sellers = [Seller(**s.model_dump()) for s in body.sellers]
    else:
        sellers = default_sellers()
    return buyer, sellers


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "AgentDeal",
        "version": "0.1.0",
        "endpoints": ["POST /negotiate", "GET /negotiations", "GET /negotiations/{id}"],
    }


@app.post("/negotiate")
async def post_negotiate(
    body: NegotiateRequest = NegotiateRequest(),
    stream: bool = False,
    delay: float = 0.0,
):
    buyer, sellers = _build_inputs(body)

    if not stream:
        result = await asyncio.to_thread(
            negotiate,
            buyer,
            sellers,
            body.rounds,
            body.market_reference,
            body.fulfill,
        )
        return JSONResponse(result.model_dump(by_alias=True))

    return EventSourceResponse(_event_stream(buyer, sellers, body, delay))


async def _event_stream(buyer: Buyer, sellers: list[Seller], body: NegotiateRequest, delay: float):
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    END = {"type": "__end__"}

    def on_event(ev: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ev)

    def run() -> None:
        try:
            negotiate(
                buyer,
                sellers,
                body.rounds,
                body.market_reference,
                body.fulfill,
                on_event=on_event,
            )
        except Exception as exc:  # surface engine errors to the client
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(exc)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, END)

    worker = loop.run_in_executor(None, run)

    while True:
        ev = await queue.get()
        if ev.get("type") == "__end__":
            break
        yield {"event": ev["type"], "data": json.dumps(ev)}
        # Pace live mode (helps when the engine runs instantly offline).
        if delay > 0 and ev.get("type") == "turn":
            await asyncio.sleep(delay)

    await worker


@app.get("/negotiations")
def get_negotiations() -> dict[str, Any]:
    return {"negotiations": list_results()}


@app.get("/negotiations/{negotiation_id}")
def get_negotiation(negotiation_id: str):
    try:
        result = load_result(negotiation_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"no negotiation {negotiation_id!r}")
    return JSONResponse(result.model_dump(by_alias=True))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
