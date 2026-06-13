import { motion, useReducedMotion } from "framer-motion";
import type { IdentityBadgeProps } from "../lib/types";

// THE NOTARY MARK - a printed verification stamp in trust indigo. Square-cornered,
// hairline-ruled, struck inline beside an accountable party. A tiny concentric
// seal (filled when verified), the smallcaps status, and the signed reference
// truncated to its tail. Indigo belongs to the identity layer alone.

export function IdentityBadge({ identity, size = "md", className = "" }: IdentityBadgeProps) {
  if (!identity) return null;
  const reduce = useReducedMotion();

  const dim = size === "sm" ? 12 : 15;
  const ref = identity.ref ?? "";
  const tail = "…" + ref.slice(-6);

  return (
    <motion.span
      initial={reduce ? false : { opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={reduce ? { duration: 0.2 } : { type: "spring", stiffness: 320, damping: 22 }}
      className={
        "inline-flex items-center gap-1 border border-trust/45 bg-trust/10 px-1.5 py-0.5 text-trust " +
        className
      }
    >
      <Seal size={dim} filled={identity.verified} />
      <span className="kicker leading-none">{identity.verified ? "Verified" : "Reference"}</span>
      <span className="font-mono tabular text-[10px] leading-none text-trust/80">{tail}</span>
    </motion.span>
  );
}

function Seal({ size, filled }: { size: number; filled: boolean }) {
  return (
    <svg
      aria-hidden
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      className="shrink-0"
    >
      {filled && (
        <circle cx="8" cy="8" r="7" fill="currentColor" fillOpacity={0.16} stroke="none" />
      )}
      <circle cx="8" cy="8" r="6.5" strokeWidth={1.2} />
      <circle
        cx="8"
        cy="8"
        r="3.4"
        strokeWidth={1.2}
        fill={filled ? "currentColor" : "none"}
        fillOpacity={filled ? 0.55 : 0}
      />
    </svg>
  );
}
