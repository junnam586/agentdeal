import { motion, useReducedMotion } from "framer-motion";
import type { OfferCardProps } from "../lib/types";

// A WIRE DISPATCH - a single negotiation message set as a newspaper brief, not a
// chat bubble. A left rule in the speaker's role color, a serif byline + smallcaps
// action tag, the standing price in mono, and the message itself as an italic
// pull-quote that must read well across several sentences.

const fmt = (p: number): string => "$" + (Number.isInteger(p) ? p.toString() : p.toFixed(2));

export function OfferCard({ message, agentLabel, role }: OfferCardProps) {
  const reduce = useReducedMotion();
  if (message == null) return null;

  const action = message.action;
  const isAccept = action === "accept";
  const isReject = action === "reject";

  // Left rule: accept -> seal, reject -> muted, else by role.
  const ruleColor = isAccept
    ? "border-seal"
    : isReject
    ? "border-muted"
    : role === "seller"
    ? "border-seller"
    : "border-buyer";

  // Price tint: accept -> seal, else by role.
  const priceColor = isAccept
    ? "text-seal"
    : role === "seller"
    ? "text-seller"
    : "text-buyer";

  // Enter motion: buyer slides from the left, sellers from the right, accept
  // scales 0.97 -> 1; all fade in. Reduced motion -> fade only.
  const initial = reduce
    ? { opacity: 0 }
    : isAccept
    ? { opacity: 0, scale: 0.97 }
    : { opacity: 0, x: role === "seller" ? 14 : -14 };

  const animate = reduce ? { opacity: 1 } : { opacity: 1, x: 0, scale: 1 };

  return (
    <motion.div
      initial={initial}
      animate={animate}
      transition={
        reduce
          ? { duration: 0.2 }
          : { type: "spring", stiffness: 260, damping: 26, mass: 0.8 }
      }
      className={`rule-b border-l-2 ${ruleColor} py-4 pl-5`}
    >
      {/* byline + action tag, price + round */}
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-2.5">
          <span className="truncate font-display font-semibold text-ink">{agentLabel}</span>
          <span className="kicker shrink-0">{action}</span>
        </div>
        <div className="flex shrink-0 items-baseline gap-2.5">
          {message.price != null && (
            <span className={`font-mono tabular text-[15px] ${priceColor}`}>
              {fmt(message.price)}
            </span>
          )}
          <span className="kicker text-muted">{`R${message.round}`}</span>
        </div>
      </div>

      {/* the dispatch, an italic serif pull-quote with room to breathe */}
      <p className="mt-2 max-w-prose font-body text-[15px] italic leading-relaxed text-ink">
        {message.message}
      </p>
    </motion.div>
  );
}
