# Blind study: which builds win?

## Background

NTW3 (Napoleonic: Total War III) is a mod for *Napoleon: Total War*. Before a
multiplayer battle, each player buys an army (a "build") from a fixed list of
unit cards for their chosen army (faction), within a budget and a set of rules
(`RULES.md`).

You have two kinds of evidence:

1. **What each card is worth on paper.** `data/cards.csv` lists every card of
   every army with its price (`cost`) and a `normative_value`: what the game's
   own average pricing rule would charge for that card's stats in a reference
   army, in the same gold units as `cost`. A card whose value is above its cost
   gives more stats per gold than the game's average rule. Normative values of
   very large units (`models` above 240) are probably overstated.
2. **What players actually brought, and whether they won.** `data/armies.csv`
   has 8 053 armies from 2 300+ ladder games. Each row is one army in one game:
   its faction, every card it fielded, its team, the result, and the player's
   rating change for that game.

## Goal

Propose one or more **readable** models that combine both kinds of evidence to
answer two questions:

- **How good is a card, or a whole build?**
- **What is the best legal build for each army?**

The models should make sense to a player who knows the game. Explain what each
part does and why.

## Required evaluation

This protocol is fixed so that models can be compared with each other and with
other work.

- **Time split.** `data/split.json` gives a cut date. *Training*: armies with
  `played_at` < cut. *Test*: armies with `played_at` ≥ cut. Fit everything on
  training data only.
- **Test question.** For each test army in a decisive game (`result` win or
  loss), predict the probability that it won from its build (its cards) and
  its faction.
- **Metrics.** AUC and log-loss on the test armies. Compare with a
  **faction-only** model, i.e. the faction's training win rate in a logistic
  regression.
- **No leakage.** A training army's own game result must not feed into the
  features it is scored with: card win rates computed on training data must be
  cross-fitted or computed leave-one-out. Test features use training data only.
- **Player skill.** Player skill is a confounder. You may use rating changes
  or player identity as controls for *understanding* card effects. But the
  final build recommendation must not depend on who the player is.

## Rules

- **Inputs:** use only the files in this folder. Do not read anything else in
  the repository, especially not `analysis/output/` or any other `analysis/*.py`
  or `analysis/*.md`. This is a blind study.
- **Models:** readable ones only.
  - Allowed: linear or regularised-linear models, small lookup tables,
    shrinkage or empirical-Bayes estimates, simple trees or rule lists
    (depth ≤ 4), and explicit optimisation.
  - Not allowed: ensembles, boosting, kNN or neural networks.
- **Builds must be legal under `RULES.md`.** A build optimiser has to enforce
  every rule there.
- **Work location:** work in this folder only. Scripts go in `src/` and
  outputs in `out/`. Keep a running log in `RESULTS.md`, one row per
  experiment. Use fixed seeds.
- **Environment:** Python 3.13 with numpy, scipy (including
  `scipy.optimize.milp`) and scikit-learn. pandas is **not** installed. Windows;
  run Python with `PYTHONIOENCODING=utf-8`.

## Deliverable

`REPORT.md` containing:

1. each model you propose: its formula or rule, its parameters, and the
   intuition behind it;
2. the evaluation table: test AUC and log-loss for every model and for the
   faction-only baseline;
3. what the evidence says about cards: which kinds of cards win more than
   their price suggests, and how strong the effect is once player skill is
   considered;
4. your recommended model's best legal build for **every** army, written to
   `out/builds.csv` with columns `faction_key, variant, card_key, copies`.
   The variants are `free` (no corps limit) and `4corps` (≤ 4 source corps),
   and each build includes its staff general;
5. limitations.
