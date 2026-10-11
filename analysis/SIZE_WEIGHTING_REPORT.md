# Size-frequency weighting in the pricing fits

*October 2026. Plan and log: `analysis/SIZE_WEIGHTING_PLAN.md`.*

**The question.** The pricing models are fitted mostly to the common unit sizes. Among AC infantry, 2 005
units have 100–140 models and only 13 have 240+. So mid sizes fit well and the extremes poorly. If each
unit's error is weighted by how rare its size is, so the size distribution is "regressed out" of the
training, do the extremes fit better? And do the values make better builds, in particular more mid-sized
units?

**The answer: no.** Weighting buys little on the rare sizes, costs accuracy on the common ones, and leaves
the optimiser's picks almost unchanged. Quality (full size harmonisation) and the size-band model already
do what the weighting was meant to do, and far more strongly.

Numbers come from these output files, all regenerable from checkpoints:
- `analysis/output/size_weighting_diagnostics.md`;
- `analysis/output/size_weighting_report.md`;
- `analysis/output/size_weighting_builds.md`.

## Summary

1. **The current loss already leans on small units.** The models minimise the error in price per model,
   which weights a unit's total-price error by 1/size². The result:
   - one-gun AC batteries are 4% of units but 24% of the fitted loss;
   - 0–40-model AC cavalry are 1% of units but 9% of the loss.
   So the size problem is not only about how common each size is.
2. **Weighting barely moves the size curves.** Even uncapped, each class's fitted size power stays within
   0.05 of its unweighted value. The exception is skirmishers, at 0.75–0.80 → 0.60.
3. **It trades the core for the edges.** For example, AC infantry V4 with uncapped weights:
   - 0–40 bias goes from −8.2% to −4.9%, and 180–240 from +10.9% to +4.4%;
   - but the 100–140 core, 44% of all units, goes from −1.8% to −3.2%, with MAPE from 3.8% to 5.5%.
4. **Overall accuracy suffers.** Infantry gets 2–6 gold worse and artillery 3–9 gold worse; cavalry is
   unchanged. The error averaged over size bands improves a little:
   - AC infantry: 13.0% → 11.5% (uncapped);
   - ToW cavalry: 6.9% → 5.9%;
   - ToW infantry: unchanged.
5. **The 240+ militia masses stay overpriced** by +20–33% under every weighting. That is a problem of the
   model's form (how price grows with size for militia), not of how much those units count.
6. **Values move by only 1–4%.**
   - The smallest infantry and cavalry gain about 2–4.5%.
   - Mid sizes lose 1–3%.
   - The biggest units lose most: 240+ infantry 2–11%, 140+ cavalry 1–7%.
7. **The optimiser picks almost the same sizes.** Look at the ToW infantry 100–140 band, the most common
   size: raw values give it 8.2% of infantry picks, the weighted values 8.6–10.1%, but Quality 22.1% and
   the size bands 21.6%.
8. **The ladder replays don't favour it.** The part of value the weighting removes leans toward predicting
   wins, as full harmonisation's did, but not significantly: β +0.34 … +0.79, z 1.4–1.6. So there is no
   sign the weighted values are closer to battlefield worth.

**Recommendation:** don't ship a weighted value version. For "more mid-sized units in optimal builds", use
Quality (ToW/Custom) or Quality = size bands (AC), which the app already offers. If the size problem is
worth more work, the lead is the shape of the size curve for militia masses.

## Method

**Weights.** Within each arm, in the size bands of the AC study (models 40/60/80/100/140/180/240; guns
2/3/4/5), a unit's squared error is multiplied by w = (median band count / its band count)^α. Three
variants, by the user's choice:

| Variant | α | Cap | Small bands |
|---|---|---|---|
| `a0.5c10` | 0.5 | 10× | bands under 20 units merged toward the middle |
| `a1c10` | 1 | 10× | merged as above |
| `a1` | 1 | none | none merged; e.g. the 2 cavalry units of 180–240 get ×101 |

- Weights multiply the existing per-size loss and are normalised to mean 1 on each training set.
- Counts come from the whole data slice (sizes are inputs, so there is no leakage).
- Effective sample sizes (Kish), uncapped: AC cavalry 82 of 1 715, ToW infantry 732 of 4 370.

**Models.** The two the app uses, refitted on the same 5 folds as the cached unweighted fits, which serve
as the baseline:
- **V4**, the per-class model behind ToW/Custom values and AC Quantity. It was run with the size power per
  class held fixed (a quick screen) and searched again under the weights (nested).
- **The size-band model (F6)** behind AC Quality. Its free per-band multipliers already absorb band bias,
  so weighting can only move its shared parameters.

**Builds.** Every ToW/Custom army (55) and AC corps (223, formation discounts included) was rebuilt with
each value set: raw, Quantity, Quality, size bands, and the three weighted sets. The picked cards were
counted by the size band of their base unit.

## Results

### Accuracy, nested V4 (gold; Δ ± paired SE over folds against unweighted)

| | Unweighted MAE | `a0.5c10` | `a1c10` | `a1` | Balanced MAPE, unweighted → `a1` |
|---|---|---|---|---|---|
| AC infantry | 28.10 | +2.04 ± 0.22 | +4.64 ± 0.27 | +4.90 ± 0.34 | 13.03 → 11.46 |
| AC cavalry | 42.37 | −0.20 ± 0.31 | −0.04 ± 0.68 | +0.05 ± 0.68 | 7.82 → 7.81 |
| AC artillery | 51.78 | +4.15 ± 0.64 | +7.88 ± 1.43 | +7.88 ± 1.43 | 16.23 → 17.01 |
| ToW infantry | 24.92 | +2.12 ± 0.20 | +5.25 ± 0.38 | +6.00 ± 0.45 | 15.41 → 15.27 |
| ToW cavalry | 32.77 | −0.57 ± 0.31 | −0.23 ± 0.47 | −0.00 ± 0.50 | 6.86 → 5.86 |
| ToW artillery | 27.15 | +3.16 ± 0.46 | +9.08 ± 0.51 | +9.08 ± 0.51 | 12.91 → 13.92 |

For artillery, `a1c10` equals `a1`, because no artillery band reaches the cap.

The size-band model barely changes. Balanced MAPE improves by 0.2–0.6 points for artillery and cavalry,
while infantry MAE rises by 1.4–5.1 gold.

### AC infantry V4 by size band (bias % / MAPE %)

| Models | Units | Unweighted | `a0.5c10` | `a1c10` | `a1` |
|---|---|---|---|---|---|
| 0–40 | 93 | −8.2 / 11.5 | −6.9 / 10.3 | −4.9 / 9.1 | −4.9 / 9.1 |
| 40–60 | 214 | +5.7 / 12.5 | +5.0 / 12.4 | +4.8 / 11.8 | +4.9 / 11.8 |
| 60–80 | 230 | +5.0 / 12.6 | +3.8 / 12.3 | +2.8 / 12.2 | +2.8 / 12.3 |
| 80–100 | 719 | −0.5 / 6.0 | −1.3 / 6.5 | −2.1 / 7.1 | −2.1 / 7.2 |
| 100–140 | 2 005 | −1.8 / 3.8 | −2.3 / 4.5 | −3.2 / 5.4 | −3.2 / 5.5 |
| 140–180 | 1 042 | +1.3 / 5.0 | +0.9 / 5.3 | −0.1 / 5.7 | −0.2 / 5.8 |
| 180–240 | 221 | +10.9 / 17.4 | +8.1 / 16.6 | +6.0 / 16.1 | +4.4 / 16.2 |
| 240+ | 13 | +33.0 / 48.8 | +24.2 / 44.0 | +22.0 / 41.0 | +20.1 / 33.4 |

### Which sizes the optimiser picks (share of each arm's picked cards)

| Infantry, 100–140 models | Raw | Quantity | Quality | Size bands | Weighted (3 variants) |
|---|---|---|---|---|---|
| ToW / Custom | 8.2% | 7.9% | 22.1% | 21.6% | 8.6–10.1% |
| AC | 37.0% | 36.6% | 41.3% | 43.1% | 36.5–36.6% |

Cavalry and artillery picks under weighting stay within a few points of raw. Quality moves ToW cavalry from
40–60 toward 60–80 models.

### Why weighting does so little

A residual is partly the model's error and partly the unit's real over- or under-pricing; the user's
point. Either way, weighting shifts values by only 1–4%, mostly by the same amount for every mid-sized
band. Harmonisation and the size bands instead remove each band's whole systematic bias, and that is what
reorders the build rankings. Weighting gives a band more say in the shared curve. It doesn't give the band
its own level, so one curve still has to fit all sizes.

## Reproducing

```bash
py -3.13 analysis/size_weighting.py diagnostics
py -3.13 analysis/size_weighting.py run --model both --mode fixed --variant a1        # per variant; seconds
py -3.13 analysis/size_weighting.py run --model V4 --mode nested --variant a1 --workers 5   # ~1–2 h per variant
py -3.13 analysis/size_weighting.py report
py -3.13 analysis/size_weighting_builds.py                                          # ~11 min
```

- Checkpoints are in `analysis/.cache/size_weighting/` and runs resume from them.
- The weighting lives in `unit_pricing.SIZE_WEIGHTING`. It is off by default, which leaves every existing
  fit unchanged (checked against the cached results).
