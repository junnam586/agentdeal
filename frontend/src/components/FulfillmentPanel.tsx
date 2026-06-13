import { motion, useReducedMotion } from "framer-motion";
import type { FulfillmentPanelProps } from "../lib/types";

// THE DELIVERY - a classified notice filed beneath the struck deal. Once a
// price is sealed the agreed work is run in an isolated Daytona sandbox; this
// is the printed receipt of that execution, stamped delivered and filed by id.

export function FulfillmentPanel({ fulfillment }: FulfillmentPanelProps) {
  const reduce = useReducedMotion();
  if (!fulfillment) return null;

  return (
    <motion.section
      className="mt-4 border border-rule bg-paper2 px-5 py-4"
      initial={reduce ? { opacity: 0 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reduce ? { duration: 0.25 } : { duration: 0.4, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {/* dateline + delivered stamp */}
      <div className="flex items-start justify-between gap-3">
        <span className="kicker">Fulfillment · Daytona</span>
        <motion.span
          className="select-none border border-seal px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.28em] text-seal"
          initial={reduce ? false : { opacity: 0, scale: 1.35, rotate: 6 }}
          animate={{ opacity: 1, scale: 1, rotate: -4 }}
          transition={reduce ? { duration: 0.2 } : { type: "spring", stiffness: 220, damping: 13, delay: 0.25 }}
          style={{ boxShadow: "inset 0 0 0 1px rgba(19,106,74,0.35)" }}
        >
          Delivered
        </motion.span>
      </div>

      {/* dispatch line */}
      <p className="mt-2 font-body italic text-inksoft">
        Executed in an isolated sandbox.
      </p>

      {/* the output, verbatim */}
      <pre className="scroll-thin mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words bg-paper3 px-3 py-2 font-mono text-[13px] text-ink">
        {fulfillment.output}
      </pre>

      {/* filed under */}
      <div className="rule-t mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 pt-2">
        <span className="kicker">Sandbox</span>
        <span className="min-w-0 max-w-full truncate font-mono tabular text-[11px] text-muted">
          {fulfillment.sandbox_id}
        </span>
      </div>
    </motion.section>
  );
}
