# Which builds win? A blind study of card value in NTW3 ladder games

## Summary

- **The build predicts the result, but only a little.**
  - Faction-only: test AUC 0.537.
  - Best build model (`hybsmall`): test AUC 0.592.
  - Recommended skill-controlled model (`small+elo`): test AUC 0.578, test log-loss 0.6837 against 0.6921 for faction-only.
  - In a 4v4 game, one army's build is a small part of the outcome. Player skill matters more: one standard deviation (SD) of the pre-game rating gap is worth about 0.63 logit, roughly twice the biggest build effect.
- **Paper value does not predict wins.** "Paper value" is the game's own pricing rule (stats per gold).
  - Within an army, 1 000 more gold of paper surplus is worth +0.003 logit (z 0.1) once skill is controlled.
  - The 95% interval rules out more than about ±0.05 logit per 1 000 gold.
- **What wins beyond price.** Units are logit per card, skill-controlled; multiply by 25 for percentage points (pp) near 50%.
  - **A combat general (commander card): +0.29, about +7 pp.** This is the largest and most robust effect, and it is larger for stronger players.
  - **Staff general:** +0.04 per command star.
  - **Foot artillery:** +0.12 per battery, minus 0.235 per 1 000 gold spent on artillery. Only cheap batteries help.
  - **Lancers:** +0.065 per card.
  - **Horse artillery:** about −0.10 per card at its usual 570 gold. Expensive heavy cavalry and grenadiers also earn less than their price.
  - **Light infantry** looks good, but about half of that effect is skill: strong players field more of it.
- **Recommended model: `small+elo`.** It is a logistic regression with 8 numbers: the faction term plus 7 build features, fitted with an Elo skill control. Predictions and builds use only the build and the faction.
- **Builds:** `out/builds.csv` holds an exact mixed-integer (MILP) optimum for each of the 55 armies, in both variants (`free` and `4corps`).
  - Every RULES.md rule is enforced.
  - Composition stays within what players actually field.
  - Paper value breaks ties.
  - **All 110 builds pass an independent rule checker.**

## 1. Data and protocol

| | armies | decisive | used in fits |
|---|---|---|---|
| training (played_at < 2026-09-20T15:25:11Z) | 5 690 | 5 547 | 5 511 (rated only) |
| test (played_at ≥ cut) | 2 363 | 2 168 | never |

- **Outcome.** Win = 1, loss = 0. Draws and unknown results are dropped.
- **Unrated rows.** 61 rows have no rating change: 58 wins, 3 draws and **0 losses**, often with 1–5 cards. They look like games outside the ladder.
  - They stay in every evaluation, as the protocol requires.
  - They are **excluded from every fit**; otherwise the models learn that tiny builds that leave gold unspent win.
  - 22 test armies are such rows, so rated-only test scores are also reported.
- **Faction feature F.** F is the logit of the faction's training win rate, shrunk toward the overall rate with 100 pseudo-games. The prior size was chosen on validation from 5, 20, 50 and 100.
  - For training rows it is **leave-one-match-out**: the whole match is removed, because teammates share the result.
  - Test rows use all training data.
- **Card win rates** (the `cardEB` model) are **5-fold cross-fitted, with folds grouped by match**. Test rows use all training data.
- **Model selection.**
  - Fit on training games before 2026-09-05T22:20:30Z (the 80th percentile of training game times); score on the later training games.
  - All hyper-parameters and model choices were made on that split.
  - The test set was used only once per model, for reporting.
- **Skill control (Elo).**
  - For each player and each game, the win change plus the absolute loss change is about 24, so K ≈ 24.
  - The rating change therefore reveals the pre-game expected score E: E = 1 − Δ/24 after a win, E = −Δ/24 after a loss.
  - E is the rating gap to the opponents (5–95% range: 0.375–0.625).
  - logit(E) enters the **training** fit as an unpenalised covariate (coefficient ≈ 2.0) and is fixed at its training mean when predicting.
  - So the "+elo" models predict from build and faction only, but their build coefficients are estimated net of skill.
  - A second control, a ridge "random effect" for each of the 1 760 players, is used only for understanding (section 4).

## 2. Models

All models are logistic regressions. Every build term is a sum over the build's cards of a per-card feature times the card's copies. So:
- each model gives every card a worth w_c (logit per copy);
- a build scores the faction term plus Σ copies × w_c;
- this linearity makes the best build an exact integer programme.

| model | formula (logit P(win) =) | parameters | intuition |
|---|---|---|---|
| **faction** (baseline) | a + b·F | 2 | Some armies win more. |
| **paper** | a + b·F + c·S, with S = Σ(value_adj − cost)/1000 | 3 | More stats per gold should win. value_adj values units above 240 models as if they had 240. |
| **comp** | a + b·F + Σ_k c_k·X_k (ridge) | 27 | What the build is made of (feature list below). |
| **small** | a + b·F + 7 terms | 9 | comp reduced to the 7 clearest features. |
| **cardEB** | a + b·F + c·R, with R = Σ copies·r_c and r_c = Σ copies(y − p0)/(Σ copies + k) | 3 + k | Each card's shrunk excess win rate over the faction-only prediction p0 (empirical Bayes, cross-fitted). |
| **hybrid** | comp + Σ copies·u_c, u_c ~ ridge(λ_card) | 27 + one u per card | comp plus a card-specific bonus. Counts are centred within the army, so u_c only describes how a build differs from that army's usual build. |
| **hybsmall** | small + Σ copies·u_c | 9 + one u per card | as hybrid |

The comp features (X_k) are army-level sums of:
- paper surplus;
- gold spent on infantry, cavalry and artillery;
- the number of cards in each of the 13 unit classes;
- commander cards;
- staff general stars;
- the digit of each speed tag, by tag letter;
- models.

Each model is fitted twice: without control and as "+elo".

Hyper-parameters chosen on validation:
- faction prior: 100;
- comp and small: λ = 0.1 on standardised features, so effectively unpenalised;
- cardEB: k = 20 (5 for +elo);
- hybrid: λ = 1, λ_card = 300;
- hybsmall: λ_card = 300 (100 for +elo).

### Recommended model: `small+elo`

logit P(win) = −0.407 + 0.139·F + the terms below. The Elo coefficient (2.00) is used only in fitting; it is set to its mean when predicting.

| build term (army sum) | coef | z | meaning |
|---|---|---|---|
| commander card present (0/1) | **+0.291** | 4.5 | A named combat general: about +7 pp. |
| staff general stars | **+0.042** per star | 3.1 | Napoleon (9 stars) instead of a 3-star general: about +6 pp. |
| foot artillery batteries | **+0.122** each | 2.7 | Worth taking … |
| gold spent on artillery | **−0.235** per 1 000 | −3.8 | … if cheap. Break-even is about 520 gold per foot battery. |
| horse artillery batteries | +0.034 each | 0.5 | Net about −0.10 at 570 gold. |
| lancer cards | **+0.065** each | 3.5 | About +1.6 pp per card. |
| light infantry cards | +0.012 each | 1.4 | Was 0.030 (z 3.4) before the skill control. |

**Card worth w_c** is the sum of the terms the card switches on. Examples:
- a commander-led line battalion: +0.29;
- a 100-gold howitzer: +0.10;
- a lancer regiment: +0.065;
- a plain line battalion: 0.

**Build score:** add up w_c over the build and add the faction term. Between two builds of the same army, the difference divided by 4 is roughly the difference in win probability.

Per-card numbers for all 12 514 cards are in `out/card_scores.csv`: price, paper value, usage, worth under `small+elo` (`w_small`), worth under `comp+elo` (`w_comp`), and the card bonus (`bonus`).

## 3. Evaluation

Test: 2 168 decisive armies (2 146 rated). Validation: 1 114. The 95% intervals resample matches.

| model | test AUC | test log-loss | test AUC (rated) | test LL (rated) | ΔAUC vs faction, 95% | Δlog-loss vs faction, 95% | val AUC | val LL |
|---|---|---|---|---|---|---|---|---|
| **faction (baseline)** | **0.5373** | **0.69207** | 0.5393 | 0.69194 | – | – | 0.5420 | 0.69292 |
| faction+elo | 0.5373 | 0.69237 | 0.5393 | 0.69239 | [0, 0] | [−0.0004, +0.0010] | 0.4583 | 0.69328 |
| paper | 0.5317 | 0.69208 | 0.5348 | 0.69190 | [−0.022, +0.012] | [−0.0005, +0.0005] | 0.5526 | 0.69285 |
| paper+elo | 0.5391 | 0.69237 | 0.5415 | 0.69237 | [−0.001, +0.005] | [−0.0004, +0.0010] | 0.4500 | 0.69372 |
| comp | 0.5712 | 0.68682 | 0.5752 | 0.68578 | [−0.009, +0.077] | [−0.0126, +0.0022] | 0.6180 | 0.67363 |
| comp+elo | 0.5673 | 0.68803 | 0.5703 | 0.68749 | [−0.011, +0.073] | [−0.0106, +0.0031] | 0.6043 | 0.67792 |
| cardEB | 0.5610 | 0.68943 | 0.5631 | 0.68931 | [+0.000, +0.048] | [−0.0039, −0.0014] | 0.5523 | 0.69036 |
| cardEB+elo | 0.5397 | 0.69232 | 0.5417 | 0.69233 | [−0.000, +0.005] | [−0.0004, +0.0009] | 0.5147 | 0.69294 |
| hybrid | 0.5799 | 0.68517 | 0.5845 | 0.68403 | [+0.001, +0.085] | [−0.0142, +0.0008] | **0.6219** | **0.67239** |
| hybrid+elo | 0.5733 | 0.68742 | 0.5768 | 0.68678 | [−0.006, +0.079] | [−0.0113, +0.0029] | 0.6090 | 0.67632 |
| small | 0.5829 | 0.68211 | 0.5838 | 0.68203 | [+0.003, +0.087] | [−0.0151, −0.0048] | 0.6155 | 0.67685 |
| **small+elo (recommended)** | **0.5782** | **0.68368** | 0.5782 | 0.68391 | [−0.002, +0.084] | **[−0.0132, −0.0038]** | 0.6070 | 0.67915 |
| hybsmall | **0.5921** | **0.68028** | 0.5936 | 0.68003 | [+0.014, +0.097] | [−0.0173, −0.0066] | 0.6214 | 0.67473 |
| hybsmall+elo | 0.5782 | 0.68515 | 0.5789 | 0.68515 | [−0.002, +0.086] | [−0.0132, −0.0008] | 0.6061 | 0.67702 |

- **Faction alone is weak.** Once skill is controlled, its coefficient drops from 0.40 to 0.23: part of an army's win rate reflects who plays it.
- **Paper value adds nothing** over faction-only.
- **Composition adds about +0.04 AUC and −0.008 log-loss.** The log-loss gain is significant on test for `small`, `small+elo` and `hybsmall`.
- **cardEB** (card win rates) adds little, and almost nothing with the skill control.
- **"+elo" models score a little lower,** because they stop crediting cards for the skill of the players who pick them. That is the cost of a recommendation that does not depend on the player.
- **Validation scores beat test for every model:** the meta drifts.
- **Why `small+elo`:**
  - On validation, the uncontrolled `hybrid` is best, and every simpler model is within 1–2 bootstrap standard errors (SE): comp +0.0013 (SE 0.0012), hybsmall +0.0023 (0.0025), small +0.0045 (0.0030), small+elo +0.0068 (0.0031).
  - Among the skill-controlled models, `small+elo` has the best test log-loss and the joint-best test AUC.
  - It has only 8 coefficients.
  - Its builds keep their advantage on independent data (section 5).

## 4. What the evidence says about cards

### 4.1 Kinds of cards that beat their price

Source: `out/class_effects.csv`, under `comp+elo`. "Excess over price" is worth minus 0.056 logit per 1 000 gold of cost, where 0.056 is the average worth per gold of all fielded cards.

| kind of card | training copies | mean cost | paper value/cost | worth (logit/card) | excess over price |
|---|---|---|---|---|---|
| commander cards (non-artillery classes) | 11–1 394 | 236–1 328 | 0.97–1.58 | +0.27 to +0.36 | **+0.22 to +0.34** |
| foot artillery commander | 219 | 853 | 1.20 | +0.20 | +0.15 |
| lancers | 4 310 | 573 | 1.20 | +0.076 | **+0.044** |
| irregular infantry | 387 | 350 | 1.18 | +0.068 | +0.048 |
| light cavalry | 9 011 | 552 | 1.14 | +0.046 | +0.015 |
| militia / skirmishers | 4 240 / 8 113 | 209 / 236 | 1.17 / 1.27 | +0.026 / +0.022 | +0.015 / +0.009 |
| standard cavalry / light infantry | 6 994 / 14 134 | 633 / 423 | 1.16 / 1.24 | +0.034 / +0.022 | ≈ 0 |
| line infantry | 55 537 | 336 | 1.24 | +0.007 | −0.012 |
| foot artillery (unit) | 5 875 | 501 | 1.16 | −0.012 | −0.040 |
| grenadiers | 4 956 | 549 | 1.25 | −0.009 | −0.040 |
| heavy cavalry | 2 646 | 1 213 | 1.23 | +0.005 | **−0.063** |
| horse artillery | 2 215 | 572 | 1.17 | −0.083 | **−0.115** |

1. **Always field a combat general.** About 25% of training builds have none, and that costs about 0.29 logit (7 pp).
   - The effect survives every control: 0.37 with none, 0.28 with Elo, 0.31 with player effects, 0.27 with both.
   - It is not about the unit's stats: commander cards are on average cheaper than their regular version and no better on paper.
2. **Staff stars matter.** The effect grows under the skill control (0.037 → 0.053 in comp).
3. **Take two cheap foot batteries and no horse artillery.** Horse artillery is the clearest "worse than its price" card.
4. **Lancers beat their price** (+0.065 to +0.076 per card, z ≈ 3.5). Heavy cavalry and grenadiers give the least per gold.
5. **Stats per gold are irrelevant to winning.**
   - Paper surplus: 0.021 (z 0.9) without control, 0.003 (z 0.1) with Elo.
   - Across cards, paper surplus correlates with model worth at r = 0.08, and with the card bonus at r = 0.01.
   - Extra gold on infantry or cavalry, at fixed counts and classes, has no detectable effect: −0.001 and +0.014 per 1 000 gold.
   - The levers are which kinds of cards and the generals, not buying the statistically better version of a unit.
6. **Individual card bonuses** range from about −0.10 to +0.11 per copy (`out/card_scores.csv`, column `bonus`).
   - Top: Kroatische Grenzer-Schützen (HRE), Voltigeurs de la ligne (a08_x8_047), New York militia (c10_x8_025).
   - Bottom: 95th Rifles (b12_x8_012), Strelki (b11_x8_013), French chasseurs à pied (a03_x8_032).
   - They do not replicate across halves of the data (section 5), so treat them as hints.

### 4.2 Player skill

Source: `out/skill_controls.csv`, which compares four controls: none, Elo, a player ridge effect (λ = 5), and both.

- **Skill dominates.** The Elo coefficient is 2.0. One SD of the rating gap (0.32 logit) is worth 0.63 logit, more than twice a combat general.
- **Some apparent card effects are skill.**
  - Light infantry drops from 0.036 to 0.015 per card, and the faction effect from 0.40 to 0.23.
  - The commander effect drops about 25% (0.37 → 0.27–0.31) but stays large.
  - Skilled players use more light infantry (r = 0.13 with skill) and more commanders (r = 0.10).
- **Some effects get stronger with the control:** staff stars; artillery (gold −0.21 → −0.24 per 1 000; battery +0.10 → +0.13); lancers. Weaker players lean on these.
- **By skill level** (`out/skill_groups.csv`). Skill is the player's mean logit(E) over their *other* matches; `small+elo` was refitted for each group.

  | term | weaker half (n 2 365, win rate 40%) | stronger half (n 2 364, win rate 64%) | unknown (n 782) |
  |---|---|---|---|
  | combat general | +0.19 (z 1.9) | **+0.39 (z 3.7)** | +0.14 |
  | stars | **+0.055 (z 2.7)** | +0.017 | +0.051 |
  | artillery gold per 1 000 | **−0.31 (z −3.0)** | −0.16 | −0.28 |
  | foot battery | +0.14 | +0.12 | +0.12 |
  | lancers | +0.073 (z 2.4) | +0.037 | +0.108 |

  - Strong players get twice as much from a combat general.
  - Weaker players gain more from stars, cheap artillery and lancers.
  - The recommended model uses the pooled, skill-controlled average.

## 5. Best legal build per army (`out/builds.csv`)

### Method (`src/optimise.py`)

- **Solver.** One exact MILP per army and variant (`scipy.optimize.milp`). Each solves in under 1 s, and all 110 were proven optimal.
- **Objective.** Σ w_c·x_c under `small+elo`, where x_c is the number of copies. Faction, intercept and skill terms are constant within an army, so the result does not depend on the player.
- **Two stages:**
  1. Maximise W = Σ w_c·x_c.
  2. Among builds with W ≥ W* − 0.02 logit (about 0.5 pp), maximise total adjusted paper value. The data picks the levers; paper value decides what the data cannot separate.
- **Rules enforced as constraints:**
  - exactly 1 staff general;
  - ≤ 31 cards;
  - cost ≤ 10 000;
  - ≤ 1 commander;
  - per base_unit_key: copies ≤ unit_cap and ≤ 1 commander version;
  - commander and staff cards at most 1 copy each;
  - foot artillery ≤ 2; horse artillery ≤ 1 (2 if the army has no infantry); heavy cavalry ≤ 10;
  - for `4corps`: ≤ 4 distinct source corps, staff included, using binary corps switches.
- **Two modelling restrictions** (not game rules):
  1. **Composition guardrails.** Infantry and cavalry counts, per-class counts and copies of any single card stay within the middle 95% of the army's own rated training builds.
     - This applies to the 38 of 55 armies with at least 40 such builds.
     - Other armies use the pooled range, widened to cover everything that army was actually seen to field.
     - Without guardrails, the optimiser builds 31-card stacks of one type with no cavalry.
     - The unguarded optimum is in `out/builds_noguard.csv`; it is also legal.
  2. **Token cards excluded.** These are 110 cards worth less than half their price on paper: one-model "commanders", depleted batteries, and negative-value units. They are almost never fielded, but the count terms would otherwise use them as cheap filler.

### Result

- All builds have 15–31 cards (median 26) and cost 9 989–10 000.
- **All 110 builds pass `src/check_builds.py`.** It re-reads cards.csv independently. Each deliberate mutation was caught: extra staff, extra commander, a card over its cap, 5 corps in a `4corps` build, a 3rd foot battery, a missing army.
- **The typical build:**
  - the highest-star staff general;
  - one combat general;
  - two cheap foot batteries, often one led by an artillery commander (22 of 55 armies), which fills two needs with one card;
  - no horse artillery unless it is very cheap;
  - as many lancers as the army usually fields;
  - the rest filled with the best stats-per-gold infantry and cavalry.
- **`4corps`.** In 42 of 55 armies the free build already uses ≤ 4 corps. For the other 13, the corps limit costs at most 0.008 logit.
- **Predicted gain** over the army's average observed build: median +0.49 logit (in-sample). This is optimistic.
  - In a split-half check (`src/optimism.py`), small+elo builds keep about two thirds of their gain on the other half (0.585 → 0.39).
  - Realistically, expect about +0.3 logit (about +7 pp), mostly from the commander, staff general and artillery.
  - Card bonuses (hybsmall+elo) fall from 0.24 to 0.02, which is why they are not used for building.
  - comp+elo keeps more of its gain (0.58) and is a reasonable alternative optimiser, but it has 27 coefficients and a worse test log-loss.

Per-army builds are listed in `out/builds_summary.csv` (columns: army, train games, cards, inf / cav / art, lancers, light infantry, staff general and stars, combat general and class, cost, in-sample gain in logit, and whether the 4-corps variant differs). "Gain" is the in-sample logit advantage over the army's average rated training build: divide by about 4 for win-probability points, then take about 2/3.

## 6. Limitations

1. **Observational data and small effects.**
   - Possible confounders: skill, teammates, the opponents' armies (Army Corps and AI armies are absent from the data), map and meta.
   - The Elo control removes the rating gap, not everything.
   - Rating partly reflects a player's usual builds, so controlling for it may *under*-state true build effects.
2. **One army is about a quarter of a team.** That caps the achievable AUC, and teammates' and opponents' builds are ignored.
3. **Linear and additive.**
   - There are no interactions. For example, an artillery commander gets both the commander and the battery effect, while comp+elo rates artillery commanders lower (+0.20 vs +0.29).
   - There are no diminishing returns beyond the guardrails.
   - The guardrails and the token filter are modelling choices, not rules.
4. **Slightly optimistic validation score for `small`.** Its 7 features were chosen from z-scores on the full training set. The test set was never used for choices.
5. **Paper value is taken as given.** The correction for units above 240 models is a simple assumption and affects 32 cards.
6. **Never-fielded cards.** 3 375 of 12 514 cards were never fielded. They are rated only through their class, the general terms and paper value, and several builds include such cards (mostly untried commander versions).
7. **Price drift.** Builds from before September 2024 often exceed 10 000 gold at today's prices. They make up about 3% of training and are kept at current prices.
8. **Time drift.** Test scores are below validation scores for every model. The effects should be refreshed with new games.
9. **Predicted gains are in-sample.** Discount them by about one third.
