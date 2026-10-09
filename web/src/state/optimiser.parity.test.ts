// Parity with the Python optimiser (analysis/cost_effective_builds.py): for three armies
// — [1806] 10. Preußen and [1815] 6. Napoli (the two calibration anchors of the general
// correction) and the Custom army HRE — the app's optimiser must reach the same optimum
// as Python's "max value" build (no roll limit) and "four corps" build (Single roll), at
// 31 cards, in both value versions. The fixture holds the cards exactly as the app's
// faction JSON has them plus Python's results; regenerate it with
// `py -3.13 analysis/export_optimiser_values.py --fixture` after tools/build_web_data.py.

import fixture from "./__fixtures__/optimiser-parity.json";
import type { FactionRoster, OptimiserMode, UnitCard } from "../domain/types";
import { normalizeCard, normalizeOptimiserParams } from "../data/load";
import { emptyBuild, indexRoster, summarize } from "./build";
import { DEFAULT_OPTIMISE_SETTINGS, optimiseBuild } from "./optimiser";
import { nodeSolver } from "../test/highs";

interface PythonBuild { objective: number; cost: number; staff: string; units: [string, number][] }
interface FixtureArmy { optimiser: unknown; cards: Record<string, unknown>[]; python: Record<string, PythonBuild> }

const armies = (fixture as unknown as { armies: Record<string, FixtureArmy> }).armies;

function rosterOf(factionKey: string, army: FixtureArmy): FactionRoster {
  const cards = army.cards.map(normalizeCard).filter((c): c is UnitCard => c !== null);
  return { schemaVersion: 2, factionKey, armyCorpsName: factionKey, cards, optimiser: normalizeOptimiserParams(army.optimiser) };
}

const cases = Object.entries(armies).flatMap(([factionKey, army]) =>
  Object.entries(army.python).map(([key, python]) => ({ factionKey, army, key, python })));

describe("optimiser parity with analysis/cost_effective_builds.py", () => {
  it.each(cases)("$factionKey $key", async ({ factionKey, army, key, python }) => {
    const [mode, variant] = key.split("/") as [OptimiserMode, string];
    const roster = rosterOf(factionKey, army);
    const index = indexRoster(roster);
    const settings = { ...DEFAULT_OPTIMISE_SETTINGS, mode, useFilters: false, singleRoll: variant === "four corps" };
    const outcome = await optimiseBuild(roster, index, emptyBuild(), roster.cards, settings, await nodeSolver());
    if (!outcome.ok) throw new Error(outcome.error);
    // Same optimum (values in the fixture are rounded to 1e-6 gold, hence the tolerance).
    expect(outcome.summary.value).toBeCloseTo(python.objective, 3);
    expect(outcome.summary.cost).toBeLessThanOrEqual(10_000);
    expect(outcome.build.staffSlotUnitKey).toBe(python.staff);
    expect(summarize(index, outcome.build).limits.violations).toEqual([]);
  });
});
