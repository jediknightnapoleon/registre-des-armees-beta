import { useEffect } from "react";
import type { OptimiserMode } from "../domain/types";
import { MAX_TOTAL_UNIT_CARDS } from "../rules/rules";
import type { OptimiseSettings, OptimiseSummary } from "../state/optimiser";

const MODES: { mode: OptimiserMode; label: string; hint: string }[] = [
  {
    mode: "quantity",
    label: "Quantity",
    hint: "Keeps the price discount of very small and very large units (ladder games link it to winning), so mass units are favoured.",
  },
  {
    mode: "quality",
    label: "Quality",
    hint: "Removes the pricing model's size bias, so a unit's size alone never makes it look like a bargain.",
  },
];

/** Settings and run button for the build optimiser (state/optimiser.ts). The result is
 *  applied to the build immediately by Builder; "Undo optimise" restores the build it
 *  replaced until the next edit. */
export function OptimiseModal({
  isTow,
  settings,
  onSettings,
  filteredCount,
  filtersActive,
  busy,
  error,
  result,
  canUndo,
  onOptimise,
  onUndo,
  onClose,
}: {
  isTow: boolean;
  settings: OptimiseSettings;
  onSettings: (next: OptimiseSettings) => void;
  /** Cards that pass the roster filters (what "Only filtered units" restricts to). */
  filteredCount: number;
  filtersActive: boolean;
  busy: boolean;
  error: string | null;
  result: OptimiseSummary | null;
  canUndo: boolean;
  onOptimise: () => void;
  onUndo: () => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const set = <K extends keyof OptimiseSettings>(key: K, value: OptimiseSettings[K]) =>
    onSettings({ ...settings, [key]: value });
  const modeHint = MODES.find((m) => m.mode === settings.mode)?.hint;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal opt-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Optimise build"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <h3 style={{ color: "var(--gold-bright)" }}>Optimise build</h3>
            <div style={{ fontSize: 12, opacity: 0.85 }}>
              The most stats for 10 000 funds under the game's rules, as the game's average pricing rule values them
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn small" onClick={onClose} aria-label="Close optimiser">
            ✕
          </button>
        </div>

        <div className="modal-body">
          <label className="opt-field">
            <span className="opt-label">
              Max unit cards <b>{settings.maxCards}</b>
              <span className="opt-sub"> (staff general included; the game allows {MAX_TOTAL_UNIT_CARDS})</span>
            </span>
            <input
              type="range"
              min={2}
              max={MAX_TOTAL_UNIT_CARDS}
              step={1}
              value={settings.maxCards}
              onChange={(e) => set("maxCards", Number(e.target.value))}
            />
            <span className="opt-hint">Fewer cards are easier to micro; prices don't capture that.</span>
          </label>

          <div className="opt-field">
            <div className="tri">
              <span className="opt-label">Unit value</span>
              <span className="seg" role="group" aria-label="Unit value">
                {MODES.map((m) => (
                  <button
                    key={m.mode}
                    className={settings.mode === m.mode ? "on" : ""}
                    aria-pressed={settings.mode === m.mode}
                    onClick={() => set("mode", m.mode)}
                  >
                    {m.label}
                  </button>
                ))}
              </span>
            </div>
            <span className="opt-hint">{modeHint}</span>
          </div>

          <label className="opt-check">
            <input type="checkbox" checked={settings.remainder} onChange={(e) => set("remainder", e.target.checked)} />
            <span>
              Optimise remainder
              <span className="opt-hint">Keep the current build and fill the funds and cards left; off rebuilds the whole deck.</span>
            </span>
          </label>
          <label className="opt-check">
            <input type="checkbox" checked={settings.useFilters} onChange={(e) => set("useFilters", e.target.checked)} />
            <span>
              Only filtered units
              <span className="opt-hint">
                {filtersActive
                  ? `${filteredCount} cards pass the current filters (incl. Offered now and the corps roll).`
                  : "No filters set: every card is eligible."}
              </span>
            </span>
          </label>
          <label className="opt-check">
            <input type="checkbox" checked={settings.allowNoStaff} onChange={(e) => set("allowNoStaff", e.target.checked)} />
            <span>
              Allow no staff general
              <span className="opt-hint">Leave the staff slot empty when a unit is worth more.</span>
            </span>
          </label>
          {isTow && (
            <label className="opt-check">
              <input type="checkbox" checked={settings.singleRoll} onChange={(e) => set("singleRoll", e.target.checked)} />
              <span>
                Single roll (≤ 4 source corps)
                <span className="opt-hint">One in-game roll offers 4 corps, so the build can be fielded without changing the clock.</span>
              </span>
            </label>
          )}

          <div className="modal-actions opt-actions">
            <button className="btn" onClick={onOptimise} disabled={busy}>
              {busy ? "Optimising…" : "Optimise"}
            </button>
            {canUndo && (
              <button className="btn" onClick={onUndo} disabled={busy}>
                Undo optimise
              </button>
            )}
          </div>

          {error && (
            <div className="tow-warning" role="status">
              {error}
            </div>
          )}
          {result && !error && (
            <div className="opt-result" role="status">
              Applied: {result.cards} cards · {result.cost.toLocaleString()} gold · value {Math.round(result.value).toLocaleString()} ·
              efficiency {result.efficiency.toFixed(2)}
              {result.staffName ? ` · staff general ${result.staffName}` : " · no staff general"}
            </div>
          )}
          <div className="opt-hint opt-foot">
            Value is what the game's average pricing rule charges for a card's stats (Registre des Armées analysis),
            not battle power; generals get extra value in big, low-morale builds.
          </div>
        </div>
      </div>
    </div>
  );
}
