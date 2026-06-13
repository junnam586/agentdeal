import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { SettlementPanelProps } from "../lib/types";
import { IdentityBadge } from "./IdentityBadge";

// THE STRUCK DEAL - the front-page payoff. The market reference falls to the
// settled number under a stamped emerald seal; the receipt below is signed by
// two accountable parties. The emerald seal is spent here and at the gauge only.

const fmt = (n: number): string =>
  `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const TWEEN_MS = 1000;

export function SettlementPanel({ settlement, marketReference }: SettlementPanelProps) {
  if (!settlement) return null;
  const reduce = useReducedMotion();

  const finalPrice = settlement.final_price;
  const start = marketReference != null && marketReference > finalPrice ? marketReference : finalPrice * 1.3;
  const [shown, setShown] = useState(reduce ? finalPrice : start);

  useEffect(() => {
    if (reduce) {
      setShown(finalPrice);
      return;
    }
    let raf = 0;
    const begin = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - begin) / TWEEN_MS);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(start + (finalPrice - start) * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [finalPrice, start, reduce]);

  const { receipt } = settlement;

  return (
    <section className="relative mt-6 overflow-hidden border-y-[3px] border-double border-ink bg-paper2 px-6 py-7">
      {/* emerald 'settled' stamp */}
      <motion.div
        className="pointer-events-none absolute right-4 top-4 hidden select-none sm:block"
        initial={reduce ? false : { opacity: 0, scale: 1.5, rotate: 4 }}
        animate={{ opacity: 1, scale: 1, rotate: -9 }}
        transition={reduce ? { duration: 0.2 } : { type: "spring", stiffness: 200, damping: 12, delay: 0.5 }}
      >
        <div className="flex h-24 w-24 flex-col items-center justify-center rounded-full border-2 border-seal text-seal" style={{ boxShadow: "inset 0 0 0 1px rgba(19,106,74,0.4)" }}>
          <span className="font-mono text-[9px] uppercase tracking-[0.3em]">Settled</span>
          <span className="font-display text-2xl font-black leading-none">{fmt(finalPrice).replace(".00", "")}</span>
          <span className="font-mono text-[8px] uppercase tracking-widest">Terminal 3</span>
        </div>
      </motion.div>

      <span className="kicker">From the floor</span>
      <h2 className="mt-1 font-display text-headline font-black tracking-tight text-ink">
        Deal struck.
      </h2>

      {/* hero: market -> final */}
      <div className="mt-5 flex flex-wrap items-baseline gap-x-6 gap-y-2">
        {marketReference != null && (
          <span className="font-mono tabular text-2xl text-muted line-through decoration-seller/50 decoration-2">
            {fmt(marketReference)}
          </span>
        )}
        <span className="font-display text-settle-price font-semibold leading-none text-seal">
          {fmt(shown)}
        </span>
        {settlement.savings_pct != null && (
          <span className="font-body text-xl italic text-inksoft">
            down <span className="font-display font-bold not-italic text-seal">{settlement.savings_pct}%</span> from market
          </span>
        )}
      </div>

      {/* awarded to */}
      <div className="rule-t mt-6 flex flex-wrap items-center gap-3 pt-4">
        <span className="kicker">Awarded to</span>
        <span className="font-display text-xl font-semibold text-ink">{receipt.seller.label}</span>
        <IdentityBadge identity={receipt.seller} />
      </div>

      {/* receipt */}
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="kicker">Receipt signed</span>
        <IdentityBadge identity={receipt.buyer} />
        <span aria-hidden className="font-body text-muted">⟷</span>
        <IdentityBadge identity={receipt.seller} />
        <span className="min-w-0 max-w-full truncate font-mono text-[11px] text-muted">
          {receipt.signed_ref}
        </span>
      </div>
    </section>
  );
}
