import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import type { NegotiationStreamProps, Role } from "../lib/types";
import { OfferCard } from "./OfferCard";

// THE WIRE - the running transcript set as a newspaper section. Dispatches
// arrive in order, grouped under ruled round datelines; the column scrolls to
// the freshest dispatch as the negotiation breathes. Hairlines, not cards.

export function NegotiationStream({ messages, agents }: NegotiationStreamProps) {
  const reduce = useReducedMotion();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Run to the foot of the column whenever a new dispatch lands.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (reduce) {
      el.scrollTop = el.scrollHeight;
      return;
    }
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages.length, reduce]);

  return (
    <section>
      {/* masthead */}
      <div className="rule-t">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 pb-3 pt-4">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            The Wire
          </h2>
          <span className="kicker">Round-by-round dispatches</span>
        </div>
      </div>
      <div className="rule-b" aria-hidden />

      {messages.length === 0 ? (
        <p className="py-6 font-body italic text-muted">The wire is quiet.</p>
      ) : (
        <div
          ref={scrollRef}
          className="scroll-thin max-h-[460px] overflow-y-auto pr-1"
        >
          {messages.map((message, index) => {
            const prev = index > 0 ? messages[index - 1] : undefined;
            const newRound = prev === undefined || message.round !== prev.round;

            const agentLabel = agents[message.from]?.label ?? message.from;
            const role: Role =
              agents[message.from]?.role ??
              (message.from === "buyer" ? "buyer" : "seller");

            return (
              <div key={`${message.from}-${message.round}-${index}`}>
                {newRound && (
                  <div className="flex items-center gap-3 pb-3 pt-6 first:pt-2">
                    <span className="kicker shrink-0">Round {message.round}</span>
                    <span aria-hidden className="hair h-px flex-1" />
                  </div>
                )}
                <div className="pb-3">
                  <OfferCard
                    message={message}
                    agentLabel={agentLabel}
                    role={role}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
