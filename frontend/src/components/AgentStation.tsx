import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import type { AgentStationProps, Action } from "../lib/types";
import { IdentityBadge } from "./IdentityBadge";

// THE BYLINE - each negotiator printed as a columnist, not a card. The buyer is
// the lead editor (centered, larger); the sellers file their bids from the left.
// The standing price is the heartbeat: it ticks up/down on every change, set in
// tabular mono and tinted by role (petrol buyer, oxblood seller).

const fmt = (p: number): string => "$" + (Number.isInteger(p) ? p.toString() : p.toFixed(2));

// past-tense dateline tag for the latest move
const ACTION_LABEL: Record<Action, string> = {
  broadcast: "Opened",
  offer: "Offered",
  counter: "Countered",
  accept: "Accepted",
  reject: "Withdrew",
};

export function AgentStation({ agent, primary = false }: AgentStationProps) {
  const reduce = useReducedMotion();
  if (!agent) return null;

  const isSeller = agent.role === "seller";
  const priceTint = isSeller ? "text-seller" : "text-buyer";
  const actionTint = isSeller ? "text-seller/80" : "text-buyer/80";
  const roleLine = isSeller ? "Seller - Bid" : "Procurement Editor";
  const inactive = agent.active === false;

  const priceSize = primary ? "text-3xl" : "text-2xl";

  return (
    <article className={`flex flex-col items-start text-left ${inactive ? "opacity-60" : ""}`}>
      {/* byline */}
      <h3
        className={`font-display font-semibold leading-tight text-ink ${
          primary ? "text-2xl" : "text-lg"
        }`}
      >
        {agent.label}
      </h3>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span className="kicker">{roleLine}</span>
        {agent.model && (
          <span className="border border-rule px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-inksoft">
            {isSeller ? "via " : ""}
            {agent.model}
          </span>
        )}
        {agent.identity && <IdentityBadge identity={agent.identity} />}
      </div>

      {/* standing price - the heartbeat */}
      <div className="rule-t mt-3 flex w-full flex-col items-start pt-3">
        <span className="kicker mb-1 text-muted">Standing price</span>

        {agent.price == null ? (
          <span className={`font-mono tabular font-semibold leading-none text-muted ${priceSize}`}>
            -
          </span>
        ) : reduce ? (
          <span className={`font-mono tabular font-semibold leading-none ${priceTint} ${priceSize}`}>
            {fmt(agent.price)}
          </span>
        ) : (
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={agent.price}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
              className={`inline-block font-mono tabular font-semibold leading-none ${priceTint} ${priceSize}`}
            >
              {fmt(agent.price)}
            </motion.span>
          </AnimatePresence>
        )}

        {agent.lastAction && (
          <span className={`kicker mt-2 ${actionTint}`}>{ACTION_LABEL[agent.lastAction]}</span>
        )}
      </div>

      {/* latest dispatch, the column's body */}
      {agent.lastMessage && (
        <p
          className={`mt-3 font-body italic leading-relaxed text-inksoft ${
            primary ? "line-clamp-4 text-[15px]" : "line-clamp-3 text-sm"
          }`}
        >
          “{agent.lastMessage}”
        </p>
      )}

      {/* withdrawal note */}
      {inactive && <p className="mt-2 font-body italic text-muted">withdrew from bidding</p>}
    </article>
  );
}
