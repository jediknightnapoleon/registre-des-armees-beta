"""Is a staff general's command worth more in large, low-morale armies? Evidence from the replays.

Proposed correction (the user's idea) to a staff general's normative value:

    value = T3(stars) + λ · stars · D(build),   D = Σ_units models · (m_ref − morale)₊

D, the build's morale deficit, grows with the number of models and with how far
units sit below a reference morale m_ref. This script tests whether ladder games
support it and, if so, what λ is in gold.

Per army (Redcoatz ladder, ToW/Custom armies, decisive games):
  S   staff general's command stars
  D   morale deficit of its units (commander cards included), per 1 000
  V   total normative value of its units (analysis/build_blind/data/cards.csv), per 1 000 gold
  controls: the faction's and the player's win rates in *other* games (cross-fitted by
  match, 5 folds; player rate shrunk to 0.5 with 10 pseudo-games), as logits.

Logistic regression  win ~ faction + player + V + S + D + S·D.  Uncertainty: 300
bootstrap resamples of whole matches. m_ref is chosen from a grid by likelihood. The
time split of the two-compartment test checks that S·D also helps on later games.
λ (gold per star per unit of deficit) = β(S·D) ÷ β(V): the gold of normative value
that buys the same change in win odds.

Output: analysis/output/general_command_report.md and general_command_effect.json
(λ and m_ref, for cost_effective_builds.py when the effect is supported).

    python analysis/general_command_effect.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402

OUT = up.ROOT / "analysis" / "output"
BLIND_DATA = up.ROOT / "analysis" / "build_blind" / "data"
M_REF_GRID = (6, 8, 10, 12, 14, 16)
FOLDS, BOOT, SEED = 5, 300, 0
FEATURES = ["faction", "player", "V", "S", "D", "S×D"]


def load():
    stats = {}
    with up.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            stats[(r["faction_key"], r["unit_key"])] = (up.num(r["morale"]), up.num(r["men_raw"]) / 2,
                                                        int(up.num(r["command_stars"])))
    value = {}
    with open(BLIND_DATA / "cards.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            value[(r["faction_key"], r["card_key"])] = float(r["normative_value"])
    with open(OUT / "replay_army_builds.csv", encoding="utf-8") as fh:
        armies = [a for a in csv.DictReader(fh) if a["result"] in ("win", "loss") and a["staff_key"]]
    cut = json.loads((BLIND_DATA / "split.json").read_text(encoding="utf-8"))["cut_played_at"]
    return stats, value, armies, cut


def cross_fitted_rates(armies: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Faction and player win rates from the *other* folds' games (folds by match), as logits."""
    matches = sorted({a["match_id"] for a in armies})
    fold = {m: i % FOLDS for i, m in enumerate(np.random.default_rng(SEED).permutation(matches))}
    fac_l, ply_l = np.zeros(len(armies)), np.zeros(len(armies))
    for k in range(FOLDS):
        fw, pw = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
        for a in armies:
            if fold[a["match_id"]] != k:
                i = 0 if a["result"] == "win" else 1
                fw[a["faction_key"]][i] += 1
                pw[a["player"]][i] += 1
        for j, a in enumerate(armies):
            if fold[a["match_id"]] == k:
                w, l = fw[a["faction_key"]]
                p = (w + 1) / (w + l + 2)
                fac_l[j] = np.log(p / (1 - p))
                w, l = pw[a["player"]]
                p = (w + 5) / (w + l + 10)
                ply_l[j] = np.log(p / (1 - p))
    return fac_l, ply_l


def design(armies, stats, value, m_ref, fac_l, ply_l) -> np.ndarray:
    rows = []
    for j, a in enumerate(armies):
        f = a["faction_key"]
        units = a["unit_keys"].split()
        deficit = sum(stats[(f, k)][1] * max(0.0, m_ref - stats[(f, k)][0]) for k in units if (f, k) in stats) / 1000
        v = sum(value.get((f, k), 0.0) for k in units) / 1000
        s = stats.get((f, a["staff_key"]), (0, 0, 0))[2]
        rows.append([fac_l[j], ply_l[j], v, s, deficit, s * deficit])
    return np.array(rows)


def fit(X: np.ndarray, y: np.ndarray) -> LogisticRegression:
    return LogisticRegression(C=1e6, max_iter=5000).fit(X, y)


def main() -> int:
    stats, value, armies, cut = load()
    y = np.array([1 if a["result"] == "win" else 0 for a in armies])
    fac_l, ply_l = cross_fitted_rates(armies)
    # m_ref by likelihood of the full model
    profile = []
    for m_ref in M_REF_GRID:
        X = design(armies, stats, value, m_ref, fac_l, ply_l)
        model = fit(X, y)
        profile.append((log_loss(y, model.predict_proba(X)[:, 1]) * len(y), m_ref))
    m_ref = min(profile)[1]
    X = design(armies, stats, value, m_ref, fac_l, ply_l)
    full = fit(X, y)
    # Bootstrap by match
    rng = np.random.default_rng(SEED)
    by_match = defaultdict(list)
    for j, a in enumerate(armies):
        by_match[a["match_id"]].append(j)
    ids = list(by_match)
    boots = []
    for _ in range(BOOT):
        pick = rng.choice(len(ids), len(ids), replace=True)
        rows = [j for i in pick for j in by_match[ids[i]]]
        b = fit(X[rows], y[rows]).coef_[0]
        boots.append(b)
    boots = np.array(boots)
    lam = boots[:, 5] / boots[:, 2]
    # Out of sample: same features, fitted before the cut, tested after it
    pre = np.array([a["played_at"] < cut for a in armies])
    oos = []
    for name, cols in (("without S×D", [0, 1, 2, 3, 4]), ("with S×D", [0, 1, 2, 3, 4, 5])):
        m = fit(X[pre][:, cols], y[pre])
        p = m.predict_proba(X[~pre][:, cols])[:, 1]
        oos.append([name, f"{roc_auc_score(y[~pre], p):.4f}", f"{log_loss(y[~pre], p):.5f}"])

    coef, lo, hi = full.coef_[0], np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)
    supported = lo[5] > 0 and lo[2] > 0
    lam_hat, lam_lo, lam_hi = float(np.median(lam)), float(np.percentile(lam, 2.5)), float(np.percentile(lam, 97.5))
    L = ["# Is a staff general's command worth more in large, low-morale armies?", "",
         "Generated by `analysis/general_command_effect.py` from the Redcoatz ladder replays: ToW/Custom armies in "
         f"decisive games ({len(y)} armies). The correction being tested is "
         "value = T3(stars) + λ · stars · D, with D = Σ models · (m_ref − morale)₊ over the army's units (per 1 000).",
         "",
         f"**m_ref** chosen by likelihood from {list(M_REF_GRID)}: **{m_ref}** (deviance by m_ref: "
         + ", ".join(f"{m}: {d:.1f}" for d, m in sorted(profile, key=lambda t: t[1])) + ").", "",
         "## Logistic regression of winning (all decisive games)", "",
         "Controls are cross-fitted, so an army's own game never feeds its faction or player rate. "
         f"The 95% intervals come from {BOOT} bootstrap resamples of whole matches.", ""]
    L += up.table(["term", "coefficient", "95% interval", "meaning"],
                  [[FEATURES[i], f"{coef[i]:+.4f}", f"{lo[i]:+.4f} … {hi[i]:+.4f}", meaning]
                   for i, meaning in enumerate([
                       "faction's win rate in other games (logit)", "player's win rate in other games (logit)",
                       "army's total normative value, per 1 000 gold", "staff general's stars",
                       "morale deficit D, per 1 000", "stars × D: the proposed correction"])])
    L += ["", "## The same features on later games (time split)", "",
          f"Fitted on games before {cut[:10]}, tested on games after it:", ""]
    L += up.table(["model", "test AUC", "test log-loss"], oos)
    L += ["", "## Verdict", ""]
    if supported:
        L += [f"**Supported.** Stars × deficit raises win odds (interval above 0), and so does normative value, so the "
              "effect has a price in gold:",
              "",
              f"- **λ = {lam_hat:.3f} gold per star per unit of deficit** (95% interval {lam_lo:.3f} … {lam_hi:.3f});",
              f"- with m_ref = {m_ref};",
              "- D counts models × morale points below the reference, before the ÷ 1 000 scaling.",
              "",
              f"Example: a build of 3 000 models averaging 2 morale below {m_ref} (D = 6 000) makes each star worth "
              f"{lam_hat * 6000:.0f} gold more than its price-rule value."]
    else:
        L += ["**Not supported.** The interval for stars × deficit, or for normative value (needed to price it in "
              "gold), includes 0. The data do not show that a general's stars are worth more in large, low-morale "
              "armies, so the general's value stays the price rule T3.",
              "",
              f"Point estimate for reference: λ ≈ {lam_hat:.3f} gold per star per deficit unit (95% interval "
              f"{lam_lo:.3f} … {lam_hi:.3f})."]
    L += ["", "**Caveats:**",
          "- **Observational data.** Players choose generals and builds together, so the controls reduce but don't "
          "remove confounding.",
          "- **Games share players.**",
          "- **D is computed from the units' listed morale;** the game's morale mechanics are richer.", ""]
    (OUT / "general_command_report.md").write_text("\n".join(L), encoding="utf-8")
    (OUT / "general_command_effect.json").write_text(json.dumps({
        "supported": bool(supported), "lambda_gold_per_star_per_deficit": lam_hat, "lambda_95": [lam_lo, lam_hi],
        "m_ref": m_ref, "coefficients": dict(zip(FEATURES, map(float, coef)))}, indent=2), encoding="utf-8")
    print("\n".join(l for l in L if l.startswith("|") or l.startswith("**")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
