// In-app build optimiser for Theatre-of-War and Custom armies.
//
// Finds the build with the most *normative value* — what the game's average pricing
// rule would charge for the cards' stats — under the game's build rules and the
// user's settings. It is the integer programme of analysis/cost_effective_builds.py
// `solve()` (the analysis's "max value" build, and with Single roll its "four corps"
// build), re-implemented here so the app can run it; the parity test
// (optimiser.parity.test.ts) checks it reproduces the Python optimum.
//
// Values are data, not computed here (the app cannot run the pricing models): each
// card's `optimiserValue` comes from analysis/export_optimiser_values.py through
// tools/build_web_data.py, in two versions —
//   - "quality":  full size harmonisation. The pricing model overprices small and very
//                 large units; that size bias is removed, so size alone never looks
//                 like a bargain;
//   - "quantity": noise-only harmonisation. Only the model's excess noise at extreme
//                 sizes is removed and each size's systematic discount is kept,
//                 because the replays link that discount to winning.
// Staff generals are valued here: the global staff price rule T3 = b·stars^q (1 gold
// without stars) plus the analysis's hand-set command correction — stars are worth
// λ·stars·D more, D = Σ models·(mRef − morale)₊ over the build's units (a big,
// shaky army needs command), ×(1 + σ) for a C-class (cavalry-speed) general, plus a
// priced bonus for a fighting bodyguard. D depends on the build, so each staff option
// carries an auxiliary w ≤ D, w ≤ D_max·z (exact because w is maximised).
//
// Rules, as the app enforces them (rules/rules.ts checkKnownLimits): at most 31 cards
// including the staff slot (the user may cap lower), 10 000 funds, no discounts
// outside Army Corps, one staff general, the corps' combat-general cap (1 for ToW and
// Custom), each cap group's cap shared with its combat-general versions and at most
// one combat general per group, foot artillery ≤ 2, horse artillery ≤ 1 (2 for a
// cavalry-only corps), heavy cavalry ≤ 10, counted by cappedClassOf. With Single roll,
// a ToW build draws on at most 4 source corps, staff general included — all one roll
// offers (state/towRoll.ts LEGACY_TOW_MAX_SOURCE_CORPS; NTW3AC.ToWFarmycorps).

import type { FactionRoster, OptimiserMode, OptimiserParams, UnitCard } from "../domain/types";
import { isTowFactionKey } from "../domain/tow";
import {
  MAX_BUILD_COST,
  MAX_FOOT_ARTILLERY,
  MAX_HEAVY_CAVALRY,
  MAX_TOTAL_UNIT_CARDS,
  cappedClassOf,
  generalCaps,
  horseArtilleryMax,
} from "../rules/rules";
import {
  type BuildState,
  type RosterIndex,
  combatGeneralsAgainstCap,
  expandBuild,
  makeInstanceId,
} from "./build";
import type { LpSolver } from "./solveLp";
import { LEGACY_TOW_MAX_SOURCE_CORPS } from "./towRoll";

export interface OptimiseSettings {
  /** Cards including the staff slot, 2 … 31 (the game's limit). Fewer = less micro. */
  maxCards: number;
  /** Which value version: "quality" (size bias removed) or "quantity" (size discount kept). */
  mode: OptimiserMode;
  /** Keep the current build and fill the remaining funds and cards, instead of rebuilding. */
  remainder: boolean;
  /** Only pick cards that pass the roster filters (the caller passes the candidate list). */
  useFilters: boolean;
  /** Let the optimiser leave the staff slot empty when a unit is worth more. */
  allowNoStaff: boolean;
  /** ToW only: at most 4 source corps, so one roll offers the whole build. */
  singleRoll: boolean;
}

export const DEFAULT_OPTIMISE_SETTINGS: OptimiseSettings = {
  maxCards: MAX_TOTAL_UNIT_CARDS,
  mode: "quantity",
  remainder: false,
  useFilters: true,
  allowNoStaff: false,
  singleRoll: true,
};

/** Tie-break weight: among equal-value builds prefer the cheaper (as the Python optimiser). */
const COST_TIE_BREAK = 1e-6;

type Column =
  | { name: string; kind: "unit"; card: UnitCard }
  | { name: string; kind: "staff"; card: UnitCard }
  | { name: string; kind: "corps"; corps: string }
  | { name: string; kind: "command"; staff: string };

export interface OptimiseProblem {
  lp: string;
  columns: Column[];
  /** The part of the current build that is kept (empty unless remainder mode). */
  fixed: BuildState;
  settings: OptimiseSettings;
  params: OptimiserParams;
}

export interface OptimiseSummary {
  cards: number;
  cost: number;
  value: number;
  efficiency: number;
  staffName: string | null;
}

export type OptimiseOutcome =
  | { ok: true; build: BuildState; summary: OptimiseSummary; status: string }
  | { ok: false; error: string };

// --- valuation -----------------------------------------------------------------

/** Morale deficit a card adds to D: models × morale points below mRef. */
export function moraleDeficit(card: UnitCard, params: OptimiserParams): number {
  const models = (card.menRaw ?? 0) / 2;
  const morale = card.stats.morale ?? params.mRef;
  return models * Math.max(0, params.mRef - morale);
}

function staffTerms(card: UnitCard, params: OptimiserParams, mode: OptimiserMode): { constant: number; slope: number } {
  const stars = card.commandStars ?? 0;
  const speed = 1 + params.speedBonus * (card.speedCode?.startsWith("C") ? 1 : 0);
  const t3 = stars > 0 ? params.t3B * stars ** params.t3Q : 1;
  const melee = (card.stats.meleeAttack ?? 0) > params.standardGeneralMelee ? params.meleeBonus : 0;
  return { constant: t3 * speed + melee, slope: params.lambda[mode] * stars * speed };
}

/** A staff general's value in a build whose units have morale deficit `deficit`. */
export function staffGeneralValue(card: UnitCard, params: OptimiserParams, mode: OptimiserMode, deficit: number): number {
  const { constant, slope } = staffTerms(card, params, mode);
  return constant + slope * deficit;
}

/** Totals of a whole build as the optimiser values it (cards include the staff slot). */
export function buildValue(index: RosterIndex, build: BuildState, params: OptimiserParams,
                           mode: OptimiserMode): OptimiseSummary {
  const line = build.instances.map((i) => index.byKey.get(i.unitKey)).filter((c): c is UnitCard => !!c);
  const slot = build.staffSlotUnitKey ? index.byKey.get(build.staffSlotUnitKey) ?? null : null;
  const deficit = line.reduce((d, c) => d + moraleDeficit(c, params), 0);
  let value = line.reduce((v, c) => v + (c.optimiserValue?.[mode] ?? 0), 0);
  if (slot) {
    value += slot.generalKind === "staff" ? staffGeneralValue(slot, params, mode, deficit) : slot.optimiserValue?.[mode] ?? 0;
  }
  const cost = line.reduce((s, c) => s + c.cost, 0) + (slot?.cost ?? 0);
  return { cards: line.length + (slot ? 1 : 0), cost, value, efficiency: cost > 0 ? value / cost : 0,
           staffName: slot?.generalKind === "staff" ? slot.name : null };
}

// --- LP text -------------------------------------------------------------------

function num(x: number): string {
  return Number.isInteger(x) ? String(x) : x.toFixed(9).replace(/0+$/, "").replace(/\.$/, "");
}

/** `coef name` terms, one per line (LP format allows continuation lines). Every row the
 *  optimiser writes has at least one column; a zero coefficient is kept as `+ 0 name`
 *  so the column still exists. */
function terms(entries: [number, string][]): string {
  return entries.map(([c, n]) => `${c < 0 ? "-" : "+"} ${num(Math.abs(c))} ${n}`).join("\n   ");
}

// --- problem -------------------------------------------------------------------

/** Build the integer programme, or explain why no build can be made. `candidates` are
 *  the cards the optimiser may add (the filtered list, or the whole roster). */
export function buildOptimiseProblem(
  roster: FactionRoster,
  index: RosterIndex,
  current: BuildState,
  candidates: readonly UnitCard[],
  settings: OptimiseSettings,
): { problem: OptimiseProblem } | { error: string } {
  const params = roster.optimiser;
  if (!params) return { error: "No optimiser data for this army (Army Corps armies are not covered)." };
  const mode = settings.mode;
  const maxCards = Math.max(2, Math.min(MAX_TOTAL_UNIT_CARDS, Math.round(settings.maxCards)));
  const fixed: BuildState = settings.remainder ? current : { instances: [], staffSlotUnitKey: null };
  const fixedCards = expandBuild(index, fixed).cards;
  const fixedLine = fixed.instances.map((i) => index.byKey.get(i.unitKey)).filter((c): c is UnitCard => !!c);
  const fixedSlot = fixed.staffSlotUnitKey ? index.byKey.get(fixed.staffSlotUnitKey) ?? null : null;

  const funds = MAX_BUILD_COST - fixedCards.reduce((s, c) => s + c.cost, 0);
  const slots = maxCards - fixedCards.length;
  if (funds <= 0) return { error: "The current build already uses all 10 000 funds." };
  if (slots <= 0) return { error: `The current build already has ${fixedCards.length} cards (cap ${maxCards}).` };

  // What the kept part already uses of every limit.
  const groupUsed = new Map<string, number>();
  const groupGeneralUsed = new Map<string, number>();
  const classUsed = new Map<string, number>();
  for (const c of fixedCards) {
    groupUsed.set(c.capGroupKey, (groupUsed.get(c.capGroupKey) ?? 0) + 1);
    if (c.generalKind === "combat") groupGeneralUsed.set(c.capGroupKey, (groupGeneralUsed.get(c.capGroupKey) ?? 0) + 1);
    const cls = cappedClassOf(c);
    classUsed.set(cls, (classUsed.get(cls) ?? 0) + 1);
  }
  const combatLeft = generalCaps(roster.factionKey).combat - combatGeneralsAgainstCap(index, fixed);
  const staffInBuild = fixedCards.some((c) => c.generalKind === "staff");
  const fixedDeficit = fixedLine.reduce((d, c) => d + moraleDeficit(c, params), 0);
  // A kept staff general's command still grows with the units added: slope × their deficit.
  const keptSlope = fixedSlot?.generalKind === "staff" ? staffTerms(fixedSlot, params, mode).slope : 0;

  // Unit columns: valued, non-staff candidates with room left in their group.
  const candidateSet = new Set(candidates.map((c) => c.unitKey));
  const columns: Column[] = [];
  const units: { col: string; card: UnitCard; ub: number }[] = [];
  for (const card of roster.cards) {
    if (!candidateSet.has(card.unitKey) || card.generalKind === "staff" || !card.optimiserValue) continue;
    const groupRoom = card.groupCap > 0 ? card.groupCap - (groupUsed.get(card.capGroupKey) ?? 0) : slots;
    const isCombat = card.generalKind === "combat";
    if (isCombat && (combatLeft <= 0 || (groupGeneralUsed.get(card.capGroupKey) ?? 0) > 0)) continue;
    const ub = Math.min(isCombat ? 1 : slots, groupRoom, slots);
    if (ub <= 0) continue;
    const col = `x${units.length}`;
    units.push({ col, card, ub });
    columns.push({ name: col, kind: "unit", card });
  }

  // Staff options: only when the slot is free and no staff general is kept in the line.
  const needStaff = !fixedSlot && !staffInBuild;
  const staffCards = needStaff
    ? roster.cards.filter((c) => c.generalKind === "staff" && candidateSet.has(c.unitKey) && c.cost <= funds)
    : [];
  if (needStaff && !settings.allowNoStaff && staffCards.length === 0) {
    return { error: "No staff general passes the filters (or fits the funds): allow a build without one, or widen the filters." };
  }
  const staff = staffCards.map((card, i) => ({ col: `z${i}`, w: `w${i}`, card, ...staffTerms(card, params, mode) }));
  for (const s of staff) columns.push({ name: s.col, kind: "staff", card: s.card });
  if (!units.length && !staff.length) return { error: "No card passes the filters with room left in the build." };

  const rows: string[] = [];
  let r = 0;
  const row = (entries: [number, string][], sense: "<=" | ">=" | "=", rhs: number) =>
    rows.push(` c${r++}: ${terms(entries)} ${sense} ${num(rhs)}`);

  row([...units.map((u): [number, string] => [u.card.cost, u.col]), ...staff.map((s): [number, string] => [s.card.cost, s.col])],
      "<=", funds);
  row([...units.map((u): [number, string] => [1, u.col]), ...staff.map((s): [number, string] => [1, s.col])], "<=", slots);
  if (staff.length) row(staff.map((s): [number, string] => [1, s.col]), settings.allowNoStaff ? "<=" : "=", 1);
  const combat = units.filter((u) => u.card.generalKind === "combat");
  if (combat.length) row(combat.map((u): [number, string] => [1, u.col]), "<=", Math.max(0, combatLeft));

  const byGroup = new Map<string, typeof units>();
  for (const u of units) byGroup.set(u.card.capGroupKey, [...(byGroup.get(u.card.capGroupKey) ?? []), u]);
  for (const [group, members] of byGroup) {
    const cap = members[0].card.groupCap;
    if (cap > 0 && members.length > 1) {
      row(members.map((u): [number, string] => [1, u.col]), "<=", Math.max(0, cap - (groupUsed.get(group) ?? 0)));
    }
    const generals = members.filter((u) => u.card.generalKind === "combat");
    if (generals.length > 1) row(generals.map((u): [number, string] => [1, u.col]), "<=", 1);
  }

  const classCaps: [string, number][] = [
    ["artillery_foot", MAX_FOOT_ARTILLERY],
    ["artillery_horse", horseArtilleryMax(roster.cards, roster.factionKey)],
    ["cavalry_heavy", MAX_HEAVY_CAVALRY],
  ];
  for (const [cls, cap] of classCaps) {
    const members = units.filter((u) => cappedClassOf(u.card) === cls);
    if (members.length) row(members.map((u): [number, string] => [1, u.col]), "<=", Math.max(0, cap - (classUsed.get(cls) ?? 0)));
  }

  // Single roll: binary per source corps, at most 4, every card from an open corps.
  const corpsBounds: string[] = [];
  const corpsCols: string[] = [];
  if (settings.singleRoll && isTowFactionKey(roster.factionKey)) {
    const fixedCorps = new Set(fixedCards.map((c) => c.towSourceCorpsId).filter((v): v is string => !!v));
    if (fixedCorps.size > LEGACY_TOW_MAX_SOURCE_CORPS) {
      return { error: `The current build already draws on ${fixedCorps.size} source corps (one roll offers ${LEGACY_TOW_MAX_SOURCE_CORPS}).` };
    }
    const all = new Set([...fixedCorps, ...units.map((u) => u.card.towSourceCorpsId), ...staff.map((s) => s.card.towSourceCorpsId)]
      .filter((v): v is string => !!v));
    const colOf = new Map<string, string>();
    [...all].sort().forEach((corps, i) => {
      const col = `y${i}`;
      colOf.set(corps, col);
      corpsCols.push(col);
      columns.push({ name: col, kind: "corps", corps });
      corpsBounds.push(` ${fixedCorps.has(corps) ? 1 : 0} <= ${col} <= 1`);
    });
    row(corpsCols.map((c): [number, string] => [1, c]), "<=", LEGACY_TOW_MAX_SOURCE_CORPS);
    for (const u of units) {
      const y = u.card.towSourceCorpsId && colOf.get(u.card.towSourceCorpsId);
      if (y) row([[1, u.col], [-u.ub, y]], "<=", 0);
    }
    for (const s of staff) {
      const y = s.card.towSourceCorpsId && colOf.get(s.card.towSourceCorpsId);
      if (y) row([[1, s.col], [-1, y]], "<=", 0);
    }
  }

  // Command correction: w ≤ D (= fixed + Σ d·x) and w ≤ D_max·z for each staff option.
  const deficits = units.map((u) => moraleDeficit(u.card, params));
  const dMax = fixedDeficit + deficits.map((d, i) => d * units[i].ub).sort((a, b) => b - a).slice(0, slots)
    .reduce((s, d) => s + d, 0);
  const commandBounds: string[] = [];
  for (const s of staff) {
    if (s.slope === 0) continue;
    columns.push({ name: s.w, kind: "command", staff: s.card.unitKey });
    commandBounds.push(` 0 <= ${s.w} <= ${num(dMax)}`);
    row([[1, s.w], ...units.map((u, i): [number, string] => [-deficits[i], u.col])], "<=", fixedDeficit);
    row([[1, s.w], [-dMax, s.col]], "<=", 0);
  }

  const objective: [number, string][] = [
    ...units.map((u, i): [number, string] =>
      [u.card.optimiserValue![mode] + keptSlope * deficits[i] - COST_TIE_BREAK * u.card.cost, u.col]),
    ...staff.map((s): [number, string] => [s.constant - COST_TIE_BREAK * s.card.cost, s.col]),
    ...staff.filter((s) => s.slope !== 0).map((s): [number, string] => [s.slope, s.w]),
  ];

  const integers = [...units.map((u) => u.col), ...staff.map((s) => s.col), ...corpsCols];
  const lp = [
    "Maximize",
    ` obj: ${terms(objective)}`,
    "Subject To",
    ...rows,
    "Bounds",
    ...units.map((u) => ` 0 <= ${u.col} <= ${u.ub}`),
    ...staff.map((s) => ` 0 <= ${s.col} <= 1`),
    ...corpsBounds,
    ...commandBounds,
    "Generals",
    ...integers.map((c) => ` ${c}`),
    "End",
    "",
  ].join("\n");
  return { problem: { lp, columns, fixed, settings: { ...settings, maxCards }, params } };
}

// --- solution ------------------------------------------------------------------

const ARM_ORDER: Record<string, number> = { artillery: 0, cavalry: 1, infantry: 2 };

/** Turn the solver's column values into a build: the kept part, then the new cards
 *  (artillery, cavalry, infantry; most valuable first), the chosen staff general in the slot. */
export function decodeOptimiseSolution(problem: OptimiseProblem, primal: Record<string, number>,
                                       index: RosterIndex): { build: BuildState; summary: OptimiseSummary } {
  const mode = problem.settings.mode;
  const picks: { card: UnitCard; copies: number }[] = [];
  let staffKey: string | null = null;
  for (const col of problem.columns) {
    const v = Math.round(primal[col.name] ?? 0);
    if (v <= 0) continue;
    if (col.kind === "unit") picks.push({ card: col.card, copies: v });
    else if (col.kind === "staff") staffKey = col.card.unitKey;
  }
  const armRank = (c: UnitCard) => ARM_ORDER[c.underlyingUnitClass.split("_")[0]] ?? 3;
  picks.sort((a, b) => armRank(a.card) - armRank(b.card)
    || (b.card.optimiserValue?.[mode] ?? 0) - (a.card.optimiserValue?.[mode] ?? 0)
    || a.card.unitKey.localeCompare(b.card.unitKey));
  const added = picks.flatMap(({ card, copies }) =>
    Array.from({ length: copies }, () => ({ id: makeInstanceId(), unitKey: card.unitKey })));
  const build: BuildState = {
    instances: [...problem.fixed.instances, ...added],
    staffSlotUnitKey: problem.fixed.staffSlotUnitKey ?? staffKey,
  };
  return { build, summary: buildValue(index, build, problem.params, mode) };
}

const STATUS_MESSAGES: Record<string, string> = {
  Infeasible: "No legal build fits these settings.",
  "Primal infeasible or unbounded": "No legal build fits these settings.",
};

/** Build the programme, solve it with `solver`, and decode the result. */
export async function optimiseBuild(
  roster: FactionRoster,
  index: RosterIndex,
  current: BuildState,
  candidates: readonly UnitCard[],
  settings: OptimiseSettings,
  solver: LpSolver,
): Promise<OptimiseOutcome> {
  const made = buildOptimiseProblem(roster, index, current, candidates, settings);
  if ("error" in made) return { ok: false, error: made.error };
  const solution = await solver(made.problem.lp);
  const usable = solution.status === "Optimal"
    || (solution.status === "Time limit reached" && Object.keys(solution.columns).length > 0);
  if (!usable) {
    return { ok: false, error: STATUS_MESSAGES[solution.status] ?? `The solver stopped: ${solution.status}.` };
  }
  const { build, summary } = decodeOptimiseSolution(made.problem, solution.columns, index);
  return { ok: true, build, summary, status: solution.status };
}
