import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import type { ConvergenceMeterProps } from "../lib/types";

// THE SPREAD - the signature instrument, drawn as a printed market gauge.
// A ruled vertical price axis: sellers hold high (oxblood, right), the buyer
// pulls low (petrol, left), and the markers SLIDE toward each other each round
// until they strike a single number under an emerald seal. (Marker up/down
// motion preserved by request.)

const fmt = (p: number): string => "$" + (Number.isInteger(p) ? p.toString() : p.toFixed(2));

export function ConvergenceMeter({
  marketReference,
  buyerTarget,
  sellerOffers,
  settledPrice,
  locked,
  winnerId,
}: ConvergenceMeterProps) {
  const reduce = useReducedMotion();
  if (sellerOffers == null) return null;

  const Frame = (children: React.ReactNode) => (
    <figure className="m-0 flex h-full flex-col">
      <figcaption className="kicker mb-2 text-center" style={{ letterSpacing: "0.28em" }}>
        The&nbsp;Spread
      </figcaption>
      {children}
    </figure>
  );

  const values = [marketReference, buyerTarget, settledPrice, ...sellerOffers.map((o) => o.price)].filter(
    (v): v is number => v != null,
  );
  if (values.length === 0) {
    return Frame(
      <div className="flex flex-1 items-center justify-center border-y border-rule py-16">
        <span className="font-body italic text-muted">Awaiting the first bid…</span>
      </div>,
    );
  }

  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 10;
  // Top of the scale is ~1.5x the market reference, so the market line sits in
  // the upper-middle (a real negotiation range) rather than at the very top; and
  // there's clear room below the strike.
  const ref = marketReference ?? max;
  const domainMax = Math.max(ref * 1.5, max * 1.05);
  const domainMin = Math.min(ref * 0.5, min - span * 0.2);
  const yPct = (p: number) => ((domainMax - p) / (domainMax - domainMin)) * 100;

  const sellerLow = sellerOffers.length ? Math.min(...sellerOffers.map((o) => o.price)) : null;
  const resolved = locked && settledPrice != null;
  const settleY = resolved ? yPct(settledPrice as number) : 0;

  let spread: { top: number; height: number; size: number } | null = null;
  if (!resolved && sellerLow != null && buyerTarget != null) {
    const a = yPct(sellerLow);
    const b = yPct(buyerTarget);
    spread = { top: Math.min(a, b), height: Math.abs(a - b), size: Math.abs(sellerLow - buyerTarget) };
  }

  // three reference ticks for the printed-scale feel
  const ticks = [domainMax - span * 0.14, (domainMax + domainMin) / 2, domainMin + span * 0.14];

  const slide = reduce
    ? { duration: 0 }
    : { type: "spring" as const, stiffness: 110, damping: 20, mass: 0.7 };

  return Frame(
    <div className="relative flex-1 border-y border-rule py-4">
      <div className="relative mx-auto h-[270px]">
        {/* scale ticks + labels */}
        {ticks.map((t, i) => (
          <div
            key={i}
            className="pointer-events-none absolute left-0 right-0 flex items-center"
            style={{ top: yPct(t) + "%", transform: "translateY(-50%)" }}
          >
            <span className="w-10 font-mono tabular text-[10px] text-muted">{fmt(Math.round(t))}</span>
            <div className="h-px flex-1" style={{ background: "var(--rule)" }} />
          </div>
        ))}

        {/* the axis (the gauge spine) */}
        <div className="absolute bottom-0 left-1/2 top-0 w-px -translate-x-1/2" style={{ background: "var(--ink)" }} />

        {/* market reference rule */}
        {marketReference != null && (
          <motion.div
            className="pointer-events-none absolute left-0 right-0 flex items-center"
            initial={false}
            animate={{ top: yPct(marketReference) + "%" }}
            transition={slide}
            style={{ transform: "translateY(-50%)" }}
          >
            <div className="ml-10 flex-1 border-t border-dashed border-muted/60" />
            <span className="ml-2 whitespace-nowrap font-mono tabular text-[10px] uppercase tracking-wide text-muted">
              {fmt(marketReference)} market
            </span>
          </motion.div>
        )}

        {/* spread bracket on the axis (value is called out in the footer) */}
        <AnimatePresence>
          {spread != null && spread.height > 1 && (
            <motion.div
              key="spread"
              className="absolute left-1/2 w-2 -translate-x-1/2"
              initial={false}
              animate={{ top: spread.top + "%", height: spread.height + "%" }}
              exit={{ opacity: 0 }}
              transition={slide}
              style={{
                borderTop: "2px solid var(--ink)",
                borderBottom: "2px solid var(--ink)",
                borderLeft: "1px solid var(--ink)",
              }}
            />
          )}
        </AnimatePresence>

        {/* buyer marker - left, petrol */}
        {buyerTarget != null && (
          <motion.div
            className="absolute right-1/2 mr-2.5 flex -translate-y-1/2 items-center gap-1.5 text-buyer"
            initial={false}
            animate={{ top: (resolved ? settleY : yPct(buyerTarget)) + "%" }}
            transition={slide}
          >
            <div className="flex flex-col items-end leading-tight">
              <span className="font-mono tabular text-[15px] font-semibold">{fmt(buyerTarget)}</span>
              <span className="font-mono text-[10px] uppercase tracking-wider text-buyer/80">buyer</span>
            </div>
            <span aria-hidden style={{ borderTop: "5px solid transparent", borderBottom: "5px solid transparent", borderLeft: "7px solid var(--buyer)" }} />
          </motion.div>
        )}

        {/* seller markers - right, oxblood */}
        {sellerOffers.map((o) => {
          const isWinner = winnerId != null && o.id === winnerId;
          return (
            <motion.div
              key={o.id}
              className="absolute left-1/2 ml-2.5 flex -translate-y-1/2 items-center gap-1.5 text-seller"
              initial={false}
              animate={{ top: (resolved ? settleY : yPct(o.price)) + "%", opacity: resolved && !isWinner ? 0.3 : 1 }}
              transition={slide}
            >
              <span aria-hidden className="h-2 w-2" style={{ background: "var(--seller)" }} />
              <div className="flex flex-col items-start leading-tight">
                <span className="font-mono tabular text-[15px] font-semibold">{fmt(o.price)}</span>
                <span className="whitespace-nowrap font-mono text-[10px] uppercase tracking-wider text-seller/80">
                  {o.label}
                </span>
              </div>
            </motion.div>
          );
        })}

        {/* the strike - emerald seal line + one-time stamp */}
        <AnimatePresence>
          {resolved && (
            <motion.div
              key="strike"
              className="pointer-events-none absolute left-0 right-0 flex items-center"
              style={{ top: settleY + "%", transform: "translateY(-50%)" }}
              initial={reduce ? { opacity: 0 } : { opacity: 0, scaleX: 0.4 }}
              animate={{ opacity: 1, scaleX: 1 }}
              transition={reduce ? { duration: 0.3 } : { duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
            >
              <div className="ml-10 h-[2px] flex-1" style={{ background: "var(--seal)" }} />
              <span className="ml-2 whitespace-nowrap font-mono tabular text-[11px] font-semibold uppercase tracking-wide text-seal">
                struck {fmt(settledPrice as number)}
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* footer caption: the live spread, or the close */}
      <div className="mt-4 text-center">
        {resolved ? (
          <p className="font-body text-xs text-seal">
            Closed the spread, struck at{" "}
            <span className="font-mono tabular">{fmt(settledPrice as number)}</span>
          </p>
        ) : (
          <p className="font-body text-xs text-muted">
            {spread != null && (
              <>
                Spread <span className="font-mono tabular text-inksoft">{fmt(spread.size)}</span>.{" "}
              </>
            )}
            Sellers hold high, buyer pulls low.
          </p>
        )}
      </div>
    </div>,
  );
}
