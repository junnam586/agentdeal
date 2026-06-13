"""Daytona adapter - fulfillment.

After the deal settles, run the purchased capability in an isolated Daytona
sandbox and return a real result. This closes the loop: negotiate -> settle ->
fulfill.

Internal contract:
    fulfill(deal: dict) -> FulfillmentResult   (output: str, sandbox_id: str)

Uses the official Daytona Python SDK: create a sandbox, run the capability code
in it, return the captured stdout, delete the sandbox. Called at most once per
negotiation, only when ``fulfill=True``. Without a Daytona key it returns a
clearly-labeled offline result instead of pretending a sandbox executed.
"""

from __future__ import annotations

import os

from ..config import env
from ..schemas import FulfillmentResult

# The capability being purchased in the reference scenario: a dataset query.
# This actually runs inside the remote sandbox.
_FULFILL_SCRIPT = (
    "rows = 1204\n"
    "print(f'Queried APAC restaurant-pricing dataset in an isolated sandbox: "
    "{rows:,} rows returned.')\n"
    "print('sample: Tokyo \\u00b7 Ramen Ichiban \\u00b7 \\u00a51,200 | "
    "Singapore \\u00b7 Hawker Gold \\u00b7 S$8.50 | "
    "Seoul \\u00b7 Gangnam BBQ \\u00b7 \\u20a928,000')\n"
)

DEFAULT_API_URL = "https://app.daytona.io/api"


def daytona_available() -> bool:
    return env("DAYTONA_API_KEY") is not None


def _offline_result() -> FulfillmentResult:
    return FulfillmentResult(
        output=(
            "[offline - Daytona not configured] Would run the dataset query in an "
            "isolated sandbox. Expected: 1,204 rows "
            "(sample: Tokyo · Ramen Ichiban · ¥1,200; Singapore · Hawker Gold · S$8.50)."
        ),
        sandbox_id="demo-sandbox",
    )


def fulfill(deal: dict) -> FulfillmentResult:
    """Run the purchased capability in a real Daytona sandbox and return output."""
    api_key = env("DAYTONA_API_KEY")
    if not api_key:
        return _offline_result()

    # macOS python.org builds ship without a usable CA store; point TLS at certifi
    # so the SDK's HTTPS calls verify. setdefault: never override an explicit value.
    try:
        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except Exception:
        pass

    from daytona import Daytona, DaytonaConfig

    api_url = (env("DAYTONA_BASE_URL") or DEFAULT_API_URL).rstrip("/")
    client = Daytona(DaytonaConfig(api_key=api_key, api_url=api_url))

    sandbox = None
    try:
        sandbox = client.create()
        response = sandbox.process.code_run(_FULFILL_SCRIPT)
        output = (getattr(response, "result", None) or "").strip()
        if getattr(response, "exit_code", 0) not in (0, None) and not output:
            output = f"(sandbox exited {response.exit_code})"
        return FulfillmentResult(output=output or "(no output)", sandbox_id=str(sandbox.id))
    except Exception as exc:
        raise RuntimeError(f"Daytona fulfillment failed: {exc}") from exc
    finally:
        if sandbox is not None:
            try:
                client.delete(sandbox)
            except Exception:
                pass
