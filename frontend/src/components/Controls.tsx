import type { ControlsProps } from "../lib/types";

// PRESS CONTROLS, pinned as a persistent footer bar so the tempo and run
// controls stay reachable while you scroll the edition. Ink-on-paper buttons
// (no solid black fills), a quiet reset, and a segmented mono tempo dial.

const SPEEDS = [0.5, 1, 1.5, 2] as const;
const speedLabel = (v: number): string => `${v}×`;

export function Controls({
  status,
  speed,
  running,
  canReplay,
  onRunLive,
  onReplay,
  onReset,
  onSpeedChange,
}: ControlsProps) {
  const replayDisabled = running || !canReplay;

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-ink bg-paper/95 backdrop-blur-sm shadow-lift">
      <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-x-6 gap-y-3 px-5 py-3 sm:px-8">
        {/* left cluster, the press run */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onReplay}
            disabled={replayDisabled}
            className={
              "border border-ink bg-ink/[0.06] px-4 py-2 font-mono text-xs font-medium uppercase tracking-wide text-ink transition-colors" +
              (replayDisabled ? " cursor-not-allowed opacity-40" : " hover:bg-ink/[0.12]")
            }
          >
            Replay edition
          </button>

          <button
            type="button"
            onClick={onRunLive}
            disabled={running}
            className={
              "border border-ink bg-transparent px-4 py-2 font-mono text-xs uppercase tracking-wide text-ink transition-colors" +
              (running ? " cursor-not-allowed opacity-40" : " hover:bg-ink/[0.06]")
            }
          >
            Run live
          </button>

          {status !== "idle" && (
            <button
              type="button"
              onClick={onReset}
              className="font-body italic text-muted underline underline-offset-2 transition-colors hover:text-ink"
            >
              Reset
            </button>
          )}
        </div>

        {/* right cluster, the tempo dial */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="kicker">Speed</span>
          <div className="flex items-center" role="group" aria-label="Replay speed">
            {SPEEDS.map((v, i) => {
              const active = speed === v;
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => onSpeedChange(v)}
                  aria-pressed={active}
                  className={
                    "border border-ink px-2.5 py-1 font-mono text-xs tabular transition-colors" +
                    (i > 0 ? " -ml-px" : "") +
                    (active ? " bg-ink/[0.12] font-medium text-ink" : " bg-transparent text-inksoft hover:bg-ink/[0.05]")
                  }
                >
                  {speedLabel(v)}
                </button>
              );
            })}
          </div>
          <span className="kicker hidden lg:inline">Replay is the clean path for recording.</span>
        </div>
      </div>
    </div>
  );
}
