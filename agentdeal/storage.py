"""Filesystem persistence for negotiations (no database).

A completed negotiation is written to ``saved/<id>.json`` at the repo root.
Replay reads from there. ``Message.from_`` is serialized as ``"from"`` via
``by_alias=True`` so saved files match the wire protocol exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import NegotiationResult

SAVED_DIR = Path(__file__).resolve().parent.parent / "saved"


def _ensure_dir() -> None:
    SAVED_DIR.mkdir(parents=True, exist_ok=True)


def persist_result(result: NegotiationResult) -> Path:
    _ensure_dir()
    path = SAVED_DIR / f"{result.id}.json"
    path.write_text(
        json.dumps(result.model_dump(by_alias=True), indent=2),
        encoding="utf-8",
    )
    return path


def load_result(negotiation_id: str) -> NegotiationResult:
    path = SAVED_DIR / f"{negotiation_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"no saved negotiation with id {negotiation_id!r}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return NegotiationResult.model_validate(data)


def list_results() -> list[dict]:
    """Return lightweight summaries of saved negotiations, newest first."""
    _ensure_dir()
    summaries: list[dict] = []
    for path in SAVED_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        summaries.append(
            {
                "id": data.get("id", path.stem),
                "resource": data.get("resource", ""),
                "final_price": data.get("final_price"),
                "savings_pct": data.get("savings_pct"),
                "winner": data.get("winner"),
                "market_reference": data.get("market_reference"),
            }
        )
    summaries.sort(key=lambda s: str(s.get("id", "")), reverse=True)
    return summaries
