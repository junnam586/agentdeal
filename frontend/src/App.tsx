import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchNegotiation,
  replayNegotiation,
  resultToEvents,
  streamNegotiation,
} from "./lib/api";
import type {
  AgentView,
  NegotiationEvent,
  NegotiationState,
  SellerOffer,
} from "./lib/types";

import { StatusBar } from "./components/StatusBar";
import { AgentStation } from "./components/AgentStation";
import { ConvergenceMeter } from "./components/ConvergenceMeter";
import { NegotiationStream } from "./components/NegotiationStream";
import { SettlementPanel } from "./components/SettlementPanel";
import { FulfillmentPanel } from "./components/FulfillmentPanel";
import { Controls } from "./components/Controls";

const INITIAL: NegotiationState = {
  status: "idle",
  mode: null,
  resource: "",
  marketReference: null,
  marketSources: [],
  rounds: 3,
  round: 0,
  agents: {},
  buyerId: "buyer",
  sellerIds: [],
  messages: [],
};

// One reducer; both live SSE and replay feed through it so the two paths render
// identically. (Visual layer changed in the redesign; this logic is unchanged.)
function reduce(state: NegotiationState, ev: NegotiationEvent): NegotiationState {
  switch (ev.type) {
    case "setup": {
      const ids = Object.keys(ev.identities);
      const buyerId = ids.find((i) => i === "buyer") ?? ids[0] ?? "buyer";
      const sellerIds = ids.filter((i) => i !== buyerId);
      const agents: Record<string, AgentView> = {};
      for (const id of ids) {
        const idn = ev.identities[id];
        agents[id] = {
          id,
          label: idn.label,
          role: id === buyerId ? "buyer" : "seller",
          identity: idn,
          price: null,
          model: ev.models?.[id],
          active: true,
        };
      }
      return {
        ...state,
        status: "running",
        id: ev.id,
        resource: ev.resource,
        marketReference: ev.market_reference,
        marketSources: ev.market_sources,
        rounds: ev.rounds,
        round: 1,
        agents,
        buyerId,
        sellerIds,
        messages: [],
        settlement: undefined,
        fulfillment: undefined,
        error: undefined,
      };
    }
    case "turn": {
      const m = ev.message;
      const agents = { ...state.agents };
      const a = agents[m.from];
      if (a) {
        const next = { ...a, lastAction: m.action, lastMessage: m.message || a.lastMessage };
        if (m.action === "reject") next.active = false;
        else if (
          m.price != null &&
          (m.action === "offer" || m.action === "counter" || m.action === "accept")
        ) {
          next.price = m.price;
        }
        agents[m.from] = next;
      }
      return {
        ...state,
        messages: [...state.messages, m],
        round: Math.max(state.round, m.round),
        agents,
      };
    }
    case "settlement": {
      const agents = { ...state.agents };
      if (agents[ev.winner]) agents[ev.winner] = { ...agents[ev.winner], price: ev.final_price };
      if (agents[state.buyerId])
        agents[state.buyerId] = { ...agents[state.buyerId], price: ev.final_price };
      return { ...state, status: "settled", settlement: ev, agents };
    }
    case "fulfillment":
      return { ...state, status: "fulfilled", fulfillment: ev.fulfillment };
    case "done":
      return state;
    case "error":
      return { ...state, status: "error", error: ev.error };
    case "fulfillment_error":
      return { ...state, error: ev.error };
    default:
      return state;
  }
}

// Staggered "typeset" reveal wrapper.
function Slot({ delay = 0, children }: { delay?: number; children: React.ReactNode }) {
  return (
    <div className="animate-ink-in" style={{ animationDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

export default function App() {
  const [state, setState] = useState<NegotiationState>(INITIAL);
  const [speed, setSpeed] = useState(1);
  const abortRef = useRef<AbortController | null>(null);

  const onEvent = useCallback((ev: NegotiationEvent) => {
    setState((s) => reduce(s, ev));
  }, []);

  // Dev/recording: ?snapshot=<id> instantly applies a saved negotiation.
  useEffect(() => {
    const snap = new URLSearchParams(window.location.search).get("snapshot");
    if (snap == null) return;
    const id = snap === "" || snap === "true" ? "sample" : snap;
    fetchNegotiation(id)
      .then((res) => {
        setState({ ...INITIAL, mode: "replay" });
        for (const ev of resultToEvents(res)) setState((s) => reduce(s, ev));
      })
      .catch(() => {});
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL);
  }, []);

  const runLive = useCallback(async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setState({ ...INITIAL, status: "running", mode: "live" });
    try {
      await streamNegotiation({ rounds: 3, market_reference: true, fulfill: true }, onEvent, ac.signal);
    } catch (e) {
      if (!(e instanceof DOMException)) setState((s) => ({ ...s, status: "error", error: String(e) }));
    }
  }, [onEvent]);

  const runReplay = useCallback(async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setState({ ...INITIAL, status: "running", mode: "replay" });
    try {
      await replayNegotiation("sample", speed, onEvent, ac.signal);
    } catch (e) {
      if (!(e instanceof DOMException)) setState((s) => ({ ...s, status: "error", error: String(e) }));
    }
  }, [onEvent, speed]);

  // The landing page IS the replay: auto-play the saved negotiation on mount
  // (unless a ?snapshot= is driving an instant settled view).
  const autostarted = useRef(false);
  useEffect(() => {
    if (autostarted.current) return;
    if (new URLSearchParams(window.location.search).get("snapshot") != null) return;
    autostarted.current = true;
    runReplay();
  }, [runReplay]);

  const sellerOffers: SellerOffer[] = useMemo(
    () =>
      state.sellerIds
        .map((id) => state.agents[id])
        .filter((a): a is AgentView => !!a && a.price != null)
        .map((a) => ({ id: a.id, label: a.label, price: a.price as number })),
    [state.sellerIds, state.agents],
  );
  const buyerTarget = state.agents[state.buyerId]?.price ?? null;
  const settledPrice = state.settlement?.final_price ?? null;
  const locked = state.status === "settled" || state.status === "fulfilled";
  const idle = state.status === "idle";
  const running = state.status === "running";

  const leftSellers = state.sellerIds.filter((_, i) => i % 2 === 0);
  const rightSellers = state.sellerIds.filter((_, i) => i % 2 === 1);

  return (
    <div className="mx-auto max-w-[1180px] px-5 pb-28 pt-8 sm:px-8">
      {/* ===== MASTHEAD ===== */}
      <header>
        <div className="flex items-end justify-between pb-1">
          <span className="kicker">Vol. I - No. 1</span>
          <span className="kicker">Settlement Edition</span>
        </div>
        <div className="rule-t pt-3">
          <h1 className="text-center font-display text-masthead font-black tracking-tight">
            AgentDeal
          </h1>
          <p className="kicker mt-2 text-center" style={{ letterSpacing: "0.34em" }}>
            The Daily Settlement · Trusted Agent-to-Agent Negotiation
          </p>
        </div>
        <div className="double-rule mt-3" />
      </header>

      {/* ===== DATELINE ===== */}
      <Slot delay={40}>
        <StatusBar
          resource={state.resource || "Awaiting commission"}
          marketReference={state.marketReference}
          marketSources={state.marketSources}
          round={state.round}
          rounds={state.rounds}
          mode={state.mode}
          status={state.status}
        />
      </Slot>

      {idle ? (
        <Slot delay={120}>
          <div className="rule-b border-rule py-24 text-center">
            <p className="font-display text-headline text-ink">An empty page.</p>
            <p className="mx-auto mt-4 max-w-md font-body text-lg italic text-inksoft">
              Commission a negotiation and watch two verified strangers argue a price down to a
              number they'll both sign.
            </p>
          </div>
        </Slot>
      ) : (
        <>
          {/* THE FLOOR: the buyer (left) works the spread against both sellers (right) */}
          <Slot delay={120}>
            <section className="grid grid-cols-1 gap-y-10 pt-6 md:grid-cols-[1fr_300px_1fr] md:gap-y-0">
              {/* buyer, left */}
              <div className="md:border-r md:border-rule md:pr-8">
                {state.agents[state.buyerId] && (
                  <AgentStation agent={state.agents[state.buyerId]} primary />
                )}
              </div>

              {/* the spread, center */}
              <div className="md:px-6">
                <ConvergenceMeter
                  marketReference={state.marketReference}
                  buyerTarget={buyerTarget}
                  sellerOffers={sellerOffers}
                  settledPrice={settledPrice}
                  locked={locked}
                  winnerId={state.settlement?.winner}
                />
              </div>

              {/* sellers, right (stacked) */}
              <div className="flex flex-col gap-6 md:border-l md:border-rule md:pl-8">
                {state.sellerIds.map((id, i) => (
                  <div key={id} className={i > 0 ? "rule-t pt-6" : ""}>
                    <AgentStation agent={state.agents[id]} />
                  </div>
                ))}
              </div>
            </section>
          </Slot>

          {/* THE WIRE */}
          <Slot delay={220}>
            <div className="mt-12">
              <NegotiationStream messages={state.messages} agents={state.agents} />
            </div>
          </Slot>

          {/* ===== SETTLEMENT + FULFILLMENT ===== */}
          {state.settlement && (
            <Slot delay={60}>
              <SettlementPanel settlement={state.settlement} marketReference={state.marketReference} />
            </Slot>
          )}
          {state.fulfillment && (
            <Slot delay={60}>
              <FulfillmentPanel fulfillment={state.fulfillment} />
            </Slot>
          )}
        </>
      )}

      {state.error && (
        <div className="rule-t mt-4 border-seller/40 pt-3 font-body text-sm text-seller">
          Dispatch failed: {state.error}
        </div>
      )}

      {/* ===== PRESS CONTROLS (fixed footer bar) ===== */}
      <Controls
        status={state.status}
        mode={state.mode}
        speed={speed}
        running={running}
        canReplay={!running}
        onRunLive={runLive}
        onReplay={runReplay}
        onReset={reset}
        onSpeedChange={setSpeed}
      />

      <footer className="double-rule mt-10 pt-4 text-center">
        <span className="kicker">
          Kimi reasoning · Terminal 3 identity · Bright Data market · Daytona fulfillment
        </span>
      </footer>
    </div>
  );
}
