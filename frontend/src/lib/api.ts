// API client for the AgentDeal backend.
//
// Live mode streams Server-Sent Events from POST /negotiate?stream=true.
// Replay mode fetches a saved NegotiationResult and *re-emits* it as timed
// events client-side, so both paths render through the identical pipeline
// (App.applyEvent) - which is what makes a clean, repeatable recording possible.

import type {
  NegotiationEvent,
  NegotiationResult,
  SetupEvent,
  SettlementEvent,
  TurnEvent,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export interface NegotiateBody {
  resource?: string;
  max_price?: number;
  rounds?: number;
  market_reference?: boolean;
  fulfill?: boolean;
}

export interface NegotiationSummary {
  id: string;
  resource: string;
  final_price: number | null;
  savings_pct: number | null;
  winner: string | null;
  market_reference: number | null;
}

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("aborted", "AbortError"));
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(t);
        reject(new DOMException("aborted", "AbortError"));
      },
      { once: true },
    );
  });

// --- Live: stream SSE from a POST -----------------------------------------

export async function streamNegotiation(
  body: NegotiateBody,
  onEvent: (ev: NegotiationEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/negotiate?stream=true`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`negotiate stream failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const dataLine = frame
        .split("\n")
        .find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const json = dataLine.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as NegotiationEvent);
      } catch {
        // ignore non-JSON keepalive frames
      }
    }
  }
}

// --- Replay: fetch a saved result and re-emit it as timed events ----------

export async function fetchNegotiation(id: string): Promise<NegotiationResult> {
  const res = await fetch(`${API_BASE}/negotiations/${id}`);
  if (!res.ok) throw new Error(`fetch negotiation ${id} failed: ${res.status}`);
  return (await res.json()) as NegotiationResult;
}

export async function listNegotiations(): Promise<NegotiationSummary[]> {
  const res = await fetch(`${API_BASE}/negotiations`);
  if (!res.ok) throw new Error(`list negotiations failed: ${res.status}`);
  const data = (await res.json()) as { negotiations: NegotiationSummary[] };
  return data.negotiations;
}

export function resultToEvents(result: NegotiationResult): NegotiationEvent[] {
  const events: NegotiationEvent[] = [];
  const setup: SetupEvent = {
    type: "setup",
    id: result.id,
    resource: result.resource,
    market_reference: result.market_reference,
    market_sources: result.market_sources,
    rounds: Math.max(1, ...result.transcript.map((m) => m.round)),
    identities: result.identities,
    models: result.models,
  };
  events.push(setup);
  for (const message of result.transcript) {
    events.push({ type: "turn", message } as TurnEvent);
  }
  const settlement: SettlementEvent = {
    type: "settlement",
    winner: result.winner,
    final_price: result.final_price,
    final_terms: result.final_terms,
    savings_pct: result.savings_pct,
    receipt: result.receipt,
  };
  events.push(settlement);
  if (result.fulfillment) {
    events.push({ type: "fulfillment", fulfillment: result.fulfillment });
  }
  events.push({ type: "done", result });
  return events;
}

// Emit a saved result through the same pipeline with controlled pacing.
export async function replayNegotiation(
  id: string,
  speed: number,
  onEvent: (ev: NegotiationEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const result = await fetchNegotiation(id);
  const events = resultToEvents(result);
  const base = 950; // ms per turn at 1x

  for (const ev of events) {
    onEvent(ev);
    let beat = 0;
    if (ev.type === "turn") beat = ev.message.action === "accept" ? base * 1.4 : base;
    else if (ev.type === "setup") beat = 650;
    else if (ev.type === "settlement") beat = 900;
    else if (ev.type === "fulfillment") beat = 500;
    if (beat > 0) await sleep(beat / Math.max(0.25, speed), signal);
  }
}
