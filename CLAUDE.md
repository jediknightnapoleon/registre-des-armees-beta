# CLAUDE.md — blind pricing study branch

This branch exists for one self-contained modelling study. **All work happens inside
`blind_study/`.** Read `blind_study/TASK.md` first: it defines the goal, scope, allowed
model families, evaluation protocol and deliverable. Column meanings are in
`blind_study/DATA_DICTIONARY.md`.

- **Rules:**
  - Do not modify anything outside `blind_study/`. The rest of the repository is an
    unrelated web app.
  - Use `blind_study/data/ntw3_units_analysis.csv` as the data.
  - All paths in `TASK.md` (`data/`, `src/`, `out/`, `RESULTS.md`, `NOTES.md`) are relative
    to `blind_study/`.
- **Resume protocol** (this session may be a continuation):
  1. Read `blind_study/NOTES.md` and `blind_study/RESULTS.md` before doing anything else.
  2. Check `git log` for the last pushed state.
  3. Continue from the next step in `NOTES.md`. Never redo finished experiments, and never
     re-split the holdout: `blind_study/data/holdout_ids.csv`, once created, is fixed.
- **Checkpoint protocol:**
  - Append to `RESULTS.md` after **every** experiment, and update `NOTES.md` every few
    experiments.
  - **Commit and push** after every experiment, or at least every 15 minutes, with short
    messages such as `exp 07: piecewise model per unit class`.
  - Scripts live in `blind_study/src/`, are deterministic (fixed seeds), and write outputs
    under `blind_study/out/`.
- **Environment:**
  - Python 3 with `numpy`, `pandas` and `scikit-learn`; run
    `pip install -r blind_study/requirements.txt` if they're missing.
  - Cloud command limits: at most about 2–10 minutes in the foreground and about
    30 minutes in the background. Split long searches into chunks that each finish well
    within that limit and append to `RESULTS.md`.
