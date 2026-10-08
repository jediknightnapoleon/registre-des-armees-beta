"""Two-compartment build model (the user's baseline): normative value + replay evidence.

Every card of a Theatre-of-War / Custom army — units, commander cards and staff
generals — gets two scores on the same scale:

  A, normative   efficiency = normative value ÷ actual cost. Units: the per-class
                 model V4 at corps 8 with no army × class adjustment; commander
                 cards: the commander model on that value; staff generals: the
                 global general price rule T3 (76.55·stars^1.39, 1 gold without
                 stars, no army modifier). Units above 240 models take part; their
                 value is probably overstated (the models overprice them) — A being
                 a rank caps the effect at the top rank.
  B, empirical   shrunk win rate when the card is brought in Redcoatz ladder games:
                 (wins + k·p₀) ÷ (wins + losses + k), k = 20 pseudo-games, p₀ = the
                 army's own win rate in decisive games; a card never brought gets p₀.

Each compartment becomes a percentile rank within the army (0–1, ties at their
average rank); a card's total score = A + B (0–2), equal weights.

Builds maximise   mean(total score of the build's cards) × (2 · spent ÷ 10 000)
— the staff general counts as one of the cards; money is scaled to the score's
0–2 range (the constant factor does not change the optimum). The objective is a
product, so it is solved exactly on a grid: for every card count n = 2…31 and
spend floor F = 5 000, 5 250, …, 10 000, an integer programme maximises Σ score
with exactly n cards and spend ≥ F under the build rules (cost_effective_builds.solve),
and the best true objective wins. Two builds per army: no corps limit, and at most
4 source corps (one roll).

Out-of-sample test: games are split in time at the 70th percentile of dates. The
empirical scores are recomputed from pre-cut games only; for every post-cut army
the mean total score of its actual cards (and the baseline objective) is used to
predict whether it won, beyond its faction's pre-cut win rate (logistic
regression fitted on pre-cut armies). AUC and log-loss against a faction-only model.

Also exports the inputs of the build blind study (analysis/build_blind/data/).

Outputs: analysis/output/unit_scores.csv, two_compartment_builds.md / .csv,
two_compartment_evaluation.md, app_builds_two_compartment/ (importable app files).

    python analysis/two_compartment.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402
from cost_effective_builds import (BIG_UNIT_MODELS, BUDGET, MAX_ROLL_CORPS, MAX_UNITS,  # noqa: E402
                                   load_cards, solve)

OUT = up.ROOT / "analysis" / "output"
BLIND = up.ROOT / "analysis" / "build_blind"
REPLAYS = up.ROOT / "replays" / "redcoatz"
K_SHRINK = 20.0
CUT_QUANTILE = 0.70
CROSS_FOLDS = 5                                          # cross-fitting of the training armies' empirical scores
CARD_COUNTS = range(2, MAX_UNITS + 2)                    # 2 … 31 cards including the staff general
SPEND_FLOORS = range(5_000, BUDGET + 1, 250)
SAVE_FORMAT_VERSION = 2


# --- Empirical evidence ------------------------------------------------------------------

def read_armies() -> list[dict]:
    with open(OUT / "replay_army_builds.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["cards"] = r["unit_keys"].split() + ([r["staff_key"]] if r["staff_key"] else [])
    return rows


def usage(armies: list[dict]) -> tuple[dict, dict]:
    """(faction → (wins, losses)), ((faction, card) → (wins, losses) when brought) — decisive games only;
    each army counts once per card it brings."""
    fac, card = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for a in armies:
        if a["result"] not in ("win", "loss"):
            continue
        i = 0 if a["result"] == "win" else 1
        fac[a["faction_key"]][i] += 1
        for k in set(a["cards"]):
            card[(a["faction_key"], k)][i] += 1
    return fac, card


def shrunk(w: int, l: int, p0: float) -> float:
    return (w + K_SHRINK * p0) / (w + l + K_SHRINK)


# --- Scores ------------------------------------------------------------------------------

def score_cards(by_faction: dict, staff_of: dict, fac: dict, card: dict) -> dict[str, list[dict]]:
    """Per army: every card (units, commanders, staff generals) with A/B raw values, ranks and total."""
    out = {}
    for f in by_faction:
        w, l = fac.get(f, (0, 0))
        p0 = w / (w + l) if w + l else 0.5
        cards = [dict(c) for c in by_faction[f]] + [dict(g, kind="staff", cls="general", arm="staff", base=g["key"],
                                                         models=8.0, men=16.0, cap=1) for g in staff_of.get(f, [])]
        for c in cards:
            cw, cl = card.get((f, c["key"]), (0, 0))
            c["a_raw"] = c["value"] / c["cost"] if c["cost"] else 0.0
            c["b_raw"] = shrunk(cw, cl, p0)
            c["wins"], c["losses"], c["p0"] = cw, cl, p0
        n = len(cards)
        for raw, rank in (("a_raw", "a"), ("b_raw", "b")):
            r = rankdata([c[raw] for c in cards], method="average")
            for c, x in zip(cards, r):
                c[rank] = (x - 1) / (n - 1) if n > 1 else 0.5
        for c in cards:
            c["score"] = c["a"] + c["b"]
        out[f] = cards
    return out


# --- Optimiser ---------------------------------------------------------------------------

def optimise(cards: list[dict], max_corps: int | None) -> dict | None:
    """Grid search over card count and spend floor; best mean score × 2·spent/10 000."""
    units = [c for c in cards if c["kind"] != "staff"]
    staff = [c for c in cards if c["kind"] == "staff"]
    cavalry_only = not any(c["arm"] == "infantry" for c in units)
    best = None
    for n in CARD_COUNTS:
        last_spent = None
        for floor in SPEND_FLOORS:
            if last_spent is not None and last_spent >= floor:
                continue                     # the previous solution already satisfies this floor
            sol = solve(units, staff, cavalry_only, "max value", max_corps=max_corps, score_key="score",
                        score_staff=True, n_cards=n, min_spend=float(floor))
            if sol is None:
                break                        # higher floors are infeasible too
            chosen, general = sol
            total = sum(c["score"] * k for c, k in chosen) + general["score"]
            spent = sum(c["cost"] * k for c, k in chosen) + general["cost"]
            objective = total / n * (2 * spent / BUDGET)
            last_spent = spent
            if best is None or objective > best["objective"] + 1e-12:
                best = {"chosen": chosen, "general": general, "n": n, "spent": spent, "mean": total / n,
                        "objective": objective}
    return best


def optimise_job(faction: str, cards: list[dict]) -> tuple[str, dict | None, dict | None]:
    return faction, optimise(cards, None), optimise(cards, MAX_ROLL_CORPS)


# --- Out-of-sample test ------------------------------------------------------------------

def evaluate(armies: list[dict], by_faction: dict, staff_of: dict, cost_of: dict) -> list[str]:
    dated = sorted({(a["played_at"], a["match_id"]) for a in armies})
    cut = dated[int(len(dated) * CUT_QUANTILE)][0]
    pre = [a for a in armies if a["played_at"] < cut]
    post = [a for a in armies if a["played_at"] >= cut]
    assert not ({a["match_id"] for a in pre} & {a["match_id"] for a in post}), "a match on both sides of the cut"
    # Empirical evidence from pre-cut games only. Test armies use all of it; each pre-cut (training)
    # army uses only the other folds' games (cross-fitting by match), so its B — like a test army's —
    # never includes its own game, and the fitted coefficients are not inflated by in-sample B.
    fac, card = usage(pre)
    test_lookup = {(f, c["key"]): c for f, cs in score_cards(by_faction, staff_of, fac, card).items() for c in cs}
    match_ids = sorted({a["match_id"] for a in pre})
    fold_of = {m: i % CROSS_FOLDS for i, m in enumerate(np.random.default_rng(0).permutation(match_ids))}
    fold_lookup, fold_fac = {}, {}
    for k in range(CROSS_FOLDS):
        f_k, c_k = usage([a for a in pre if fold_of[a["match_id"]] != k])
        fold_fac[k] = f_k
        fold_lookup[k] = {(f, c["key"]): c for f, cs in score_cards(by_faction, staff_of, f_k, c_k).items() for c in cs}

    def features(a: dict) -> dict[str, float] | None:
        k = fold_of.get(a["match_id"])
        lookup, fac_used = (test_lookup, fac) if k is None else (fold_lookup[k], fold_fac[k])
        cs = [lookup.get((a["faction_key"], key)) for key in a["cards"]]
        cs = [c for c in cs if c is not None]
        if not cs:
            return None
        w, l = fac_used.get(a["faction_key"], (0, 0))
        p0 = (w + 1) / (w + l + 2)
        spent = sum(cost_of.get((a["faction_key"], k), 0) for k in a["cards"])
        mean = float(np.mean([c["score"] for c in cs]))
        return {"faction": np.log(p0 / (1 - p0)), "A": float(np.mean([c["a"] for c in cs])),
                "B": float(np.mean([c["b"] for c in cs])), "total": mean,
                "objective": mean * 2 * min(spent, BUDGET) / BUDGET}

    def dataset(rows: list[dict]):
        X, y = [], []
        for a in rows:
            if a["result"] not in ("win", "loss"):
                continue
            f = features(a)
            if f is not None:
                X.append(f)
                y.append(1 if a["result"] == "win" else 0)
        return X, np.array(y)

    Xtr, ytr = dataset(pre)
    Xte, yte = dataset(post)
    models = [("faction only", ["faction"]), ("faction + A (normative)", ["faction", "A"]),
              ("faction + B (empirical)", ["faction", "B"]), ("faction + total score (A + B)", ["faction", "total"]),
              ("faction + baseline objective", ["faction", "objective"])]
    rows = []
    for name, cols in models:
        mat = lambda X: np.array([[x[c] for c in cols] for x in X])  # noqa: E731
        lr = LogisticRegression(C=1e6, max_iter=1000).fit(mat(Xtr), ytr)
        p = lr.predict_proba(mat(Xte))[:, 1]
        coef = ", ".join(f"{c} {b:+.3f}" for c, b in zip(cols, lr.coef_[0]))
        rows.append([name, f"{roc_auc_score(yte, p):.3f}", f"{log_loss(yte, p):.4f}", coef])
    L = ["# Two-compartment model: out-of-sample test", "",
         "Generated by `analysis/two_compartment.py`. Does an army's build score predict whether it wins, beyond "
         "its faction's win rate?", "",
         f"- **Temporal split** at {cut[:10]} (70th percentile of game dates): {len(pre)} armies before, "
         f"{len(post)} after; no match on both sides.",
         "- **Empirical scores (B) are recomputed from pre-cut games only;** the normative scores (A) use no game data.",
         f"- **Cross-fitted training features.** Each pre-cut army's B (and faction win rate) comes from the pre-cut "
         f"games in the *other* {CROSS_FOLDS} folds (folds by match), so, like a test army's, it never includes its "
         "own game.",
         f"- **Models** are logistic regressions fitted on the {len(ytr)} decisive pre-cut armies and evaluated on the "
         f"{len(yte)} decisive post-cut armies. An army's A / B / total = the mean over its actual cards (staff "
         "general included); *objective* = mean total × 2·spent/10 000, the baseline's build objective.", ""]
    L += up.table(["model", "AUC (post-cut)", "log-loss (post-cut)", "coefficients"], rows)
    L += ["", "AUC 0.5 = no better than chance; lower log-loss is better.", "",
          "**Caveats:**",
          "- **Player skill confounds this.** Strong players pick certain units and win more, so a card's win rate "
          "partly measures who brings it.",
          "- **Games share players,** so armies are not independent.",
          "- **Faction effects are partly mixed with players:** a few strong players can carry an army's win rate.", ""]
    return L, cut


# --- Blind-study inputs ------------------------------------------------------------------

def export_blind(scores: dict, armies: list[dict], cut: str) -> None:
    (BLIND / "data").mkdir(parents=True, exist_ok=True)
    with open(BLIND / "data" / "cards.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "card_key", "kind", "base_unit_key", "name", "unit_class", "arm", "cost",
                    "unit_cap", "source_corps", "models", "men", "command_stars", "normative_value"])
        for f, cs in sorted(scores.items()):
            for c in cs:
                w.writerow([f, c["key"], c["kind"], c["base"], c["name"], c["cls"], c["arm"], f"{c['cost']:.0f}",
                            c["cap"], c.get("corps") or "", f"{c['models']:g}", f"{c['men']:g}", c.get("stars", ""),
                            f"{c.get('value_raw', c['value']):.2f}"])   # the blind study's frozen input: unharmonised
    deltas = {}
    with (REPLAYS / "matches.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            deltas[m["id"]] = m.get("rating_delta") or {}
    with open(BLIND / "data" / "armies.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["match_id", "played_at", "map", "faction_key", "army_corps_name", "player", "team", "result",
                    "player_rating_change", "staff_key", "unit_keys"])
        for a in armies:
            d = deltas.get(a["match_id"], {}).get(a["player"])
            w.writerow([a["match_id"], a["played_at"], a["map"], a["faction_key"], a["army_corps_name"], a["player"],
                        a["team"], a["result"], "" if d is None else d, a["staff_key"], a["unit_keys"]])
    (BLIND / "data" / "split.json").write_text(json.dumps({"cut_played_at": cut, "rule": "train: played_at < cut; "
                                                           "test: played_at >= cut"}, indent=2), encoding="utf-8")


# --- Main --------------------------------------------------------------------------------

def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main() -> int:
    started = time.time()
    by_faction, staff_of, _, army_of = load_cards(started)
    armies = read_armies()
    fac, card = usage(armies)
    scores = score_cards(by_faction, staff_of, fac, card)
    cost_of = {(f, c["key"]): c["cost"] for f, cs in scores.items() for c in cs}
    up.log(f"scores: {sum(len(c) for c in scores.values())} cards in {len(scores)} armies", started)

    with open(OUT / "unit_scores.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "army_corps_name", "card_key", "kind", "name", "unit_class", "cost", "normative_value",
                    "efficiency", "wins_when_brought", "losses_when_brought", "faction_winrate", "shrunk_winrate",
                    "A_rank", "B_rank", "total_score", "over_240_models"])
        for f, cs in sorted(scores.items()):
            for c in sorted(cs, key=lambda c: -c["score"]):
                w.writerow([f, army_of[f][0], c["key"], c["kind"], c["name"], c["cls"], f"{c['cost']:.0f}",
                            f"{c['value']:.1f}", f"{c['a_raw']:.4f}", c["wins"], c["losses"], f"{c['p0']:.4f}",
                            f"{c['b_raw']:.4f}", f"{c['a']:.4f}", f"{c['b']:.4f}", f"{c['score']:.4f}",
                            int(c["models"] > BIG_UNIT_MODELS)])

    jobs = [(f, scores[f]) for f in sorted(scores)]
    results = {f: (free, four) for f, free, four in up.parallel_map(optimise_job, jobs)}
    up.log("builds optimised", started)

    eval_lines, cut = evaluate(armies, by_faction, staff_of, cost_of)
    (OUT / "two_compartment_evaluation.md").write_text("\n".join(eval_lines), encoding="utf-8")
    export_blind(scores, armies, cut)
    up.log(f"evaluation written; blind-study data → {BLIND.relative_to(up.ROOT)}/data", started)

    # Reports and app files.
    folder = OUT / "app_builds_two_compartment"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.json"):
        old.unlink()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    order = {"artillery": 0, "cavalry": 1, "infantry": 2}
    ranked = sorted(results, key=lambda f: -(results[f][0]["objective"] if results[f][0] else 0))
    md = ["# Two-compartment builds (baseline)", "",
          "Generated by `analysis/two_compartment.py`. Every card is scored on two compartments with equal weight: "
          "**A** = its efficiency (normative value ÷ cost) and **B** = its shrunk win rate in ladder games, each as a "
          "percentile rank within the army; total = A + B (0–2). A build maximises mean total score × 2·spent/10 000, "
          "the staff general counting as a card. Rules as in `cost_effective_builds.md`. † = over "
          f"{BIG_UNIT_MODELS} models (normative value probably overstated).", ""]
    summary, csv_rows, sections = [], [], []
    for rank, f in enumerate(ranked, 1):
        corps_used = {}
        for tag, res in (("free", results[f][0]), ("4corps", results[f][1])):
            if res is None:
                continue
            g = res["general"]
            corps_used[tag] = sorted({c["corps"] for c, _ in res["chosen"] if c.get("corps")} | ({g.get("corps")} - {None}))
            for c, k in res["chosen"]:
                csv_rows.append([army_of[f][0], f, tag, c["name"], c["key"], c["kind"], k, f"{c['cost']:.0f}",
                                 f"{c['a']:.3f}", f"{c['b']:.3f}", f"{c['score']:.3f}"])
            csv_rows.append([army_of[f][0], f, tag, g["name"], g["key"], "staff", 1, f"{g['cost']:.0f}",
                             f"{g['a']:.3f}", f"{g['b']:.3f}", f"{g['score']:.3f}"])
            instances = [c["key"] for c, k in sorted(res["chosen"], key=lambda t: (order.get(t[0]["arm"], 3), -t[0]["score"]))
                         for _ in range(k)]
            label = "no corps limit" if tag == "free" else "≤ 4 source corps (one roll)"
            name = (f"{army_of[f][0]} — two-compartment, {label}: objective {res['objective']:.3f} "
                    f"(mean score {res['mean']:.2f}, {res['spent']:,.0f} gold)")
            (folder / f"{rank:02d}_{slug(army_of[f][0])}_{tag}.json").write_text(json.dumps({
                "saveFormatVersion": SAVE_FORMAT_VERSION, "id": f"b_tc_{rank:02d}_{tag}", "name": name,
                "createdAt": now, "updatedAt": now, "factionKey": f, "armyCorpsName": army_of[f][0],
                "instances": instances, "staffSlotUnitKey": g["key"],
                "config": {"density": "comfortable", "showCombatGenerals": True}}, indent=2, ensure_ascii=False),
                encoding="utf-8")
        free, four = results[f]
        if free is None:
            continue
        arms = Counter()
        for c, k in free["chosen"]:
            arms[c["arm"]] += k
        summary.append([army_of[f][0], f"{free['objective']:.3f}", f"{free['mean']:.3f}", f"{free['spent']:,.0f}",
                        free["n"], f"{arms['infantry']}/{arms['cavalry']}/{arms['artillery']}",
                        f"{four['objective']:.3f}" if four else "—"])
        g = free["general"]
        sections += [f"### {army_of[f][0]} — objective {free['objective']:.3f}, mean score {free['mean']:.3f}, "
                     f"{free['spent']:,.0f} gold, {free['n']} cards", "",
                     f"Staff general: {g['name']} ({g['cost']:.0f} gold, {g.get('stars', 0)}★; A {g['a']:.2f}, "
                     f"B {g['b']:.2f}).", ""]
        sections += [f"- {c['name']} ×{k} ({c['cost']:.0f} gold; A {c['a']:.2f}, B {c['b']:.2f}, total {c['score']:.2f})"
                     + (" — combat general" if c["kind"] == "commander" else "")
                     + (" †" if c["models"] > BIG_UNIT_MODELS else "") for c, k in free["chosen"]]
        if four:
            same = sorted((c["key"], k) for c, k in four["chosen"]) == sorted((c["key"], k) for c, k in free["chosen"])
            sections += ["", f"*≤ 4 source corps:* objective {four['objective']:.3f}"
                         + (" — the same build" if same and four["general"]["key"] == g["key"]
                            else f", corps {' '.join(corps_used.get('4corps', [])) or '—'}") + "."]
        sections += [""]
    md += ["## All armies (no corps limit)", ""] + up.table(
        ["army", "objective", "mean score", "spent", "cards", "inf/cav/art", "objective ≤ 4 corps"], summary)
    md += ["", "## Builds (no corps limit)", ""] + sections
    md += [f"*Runtime {time.time() - started:.0f} s.*", ""]
    (OUT / "two_compartment_builds.md").write_text("\n".join(md), encoding="utf-8")
    with open(OUT / "two_compartment_builds.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["army_corps_name", "faction_key", "variant", "card", "card_key", "kind", "copies", "cost_each",
                    "A_rank", "B_rank", "total_score"])
        w.writerows(csv_rows)
    up.log("done → unit_scores.csv, two_compartment_builds.md/.csv, two_compartment_evaluation.md, "
           "app_builds_two_compartment/", started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
