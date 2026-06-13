import { motion, useReducedMotion } from "framer-motion";
import type { StatusBarProps } from "../lib/types";

// THE DATELINE, the folio line under the masthead: commission, market reference
// (with the Bright Data sources it came from, clickable), round, and edition.
// No boxes; hairlines and whitespace separate the segments.

const fmt = (n: number): string =>
  `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const isUrl = (s: string): boolean => /^https?:\/\//i.test(s);

const host = (u: string): string => {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return u;
  }
};

export function StatusBar({
  resource,
  marketReference,
  marketSources,
  round,
  rounds,
  mode,
  status,
}: StatusBarProps) {
  const reduce = useReducedMotion();
  const settled = status === "settled" || status === "fulfilled";

  const links = (marketSources ?? []).filter(isUrl).slice(0, 4);
  const note = (marketSources ?? []).find((s) => !isUrl(s));

  return (
    <div className="rule-b py-4">
      <div className="flex flex-wrap items-center justify-between gap-x-10 gap-y-3">
        {/* the commission */}
        <div className="flex min-w-0 items-baseline gap-3">
          <span className="kicker shrink-0">Commission</span>
          <span className="min-w-0 truncate font-body italic text-ink">{resource}</span>
        </div>

        {/* the market reference */}
        <div className="flex items-baseline gap-3">
          <span className="kicker shrink-0">Market ref · Bright Data</span>
          <span className="font-mono tabular text-base text-ink">
            {marketReference != null ? fmt(marketReference) : "n/a"}
          </span>
        </div>

        {/* round + edition */}
        <div className="flex items-center gap-5">
          <span className="font-mono tabular text-inksoft">
            Round {round > 0 ? round : 0} / {rounds}
          </span>
          {settled ? (
            <span className="kicker text-seal">Final edition</span>
          ) : mode === "live" ? (
            <span className="kicker flex items-center gap-2 text-ink">
              {reduce ? (
                <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-seller" />
              ) : (
                <motion.span
                  aria-hidden
                  className="h-1.5 w-1.5 shrink-0 rounded-full bg-seller"
                  animate={{ opacity: [1, 0.25, 1] }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                />
              )}
              Live edition
            </span>
          ) : mode === "replay" ? (
            <span className="kicker text-trust">Replay edition</span>
          ) : (
            <span className="kicker text-muted">Draft</span>
          )}
        </div>
      </div>

      {/* Bright Data provenance, clickable */}
      {(links.length > 0 || note) && (
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
          <span className="kicker shrink-0">Sourced via Bright Data</span>
          {links.length > 0
            ? links.map((u) => (
                <a
                  key={u}
                  href={u}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-[11px] text-trust underline decoration-trust/40 underline-offset-2 transition-colors hover:decoration-trust"
                >
                  {host(u)}
                </a>
              ))
            : note && <span className="font-mono text-[11px] text-muted">{note}</span>}
        </div>
      )}
    </div>
  );
}
