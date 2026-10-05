# Blind pricing study

A self-contained, "blind" modelling study: find the most accurate *readable* model of NTW3
unit prices for Theatre-of-War and Custom armies, validated by cross-validation. The brief
is `TASK.md`, the column meanings are in `DATA_DICTIONARY.md`, and the session rules are in
the repository-root `CLAUDE.md` of branch `blind-pricing-study`.

## Running it in a Claude Code cloud session

1. Branch `blind-pricing-study` is pushed to `jediknightnapoleon/registre-des-armees-beta`.
2. **Open claude.ai/code** and connect GitHub. If the fork is private, install the Claude
   GitHub App on it.
3. **Environment.** Keep network access on **Trusted** (allows PyPI). Optionally add the
   setup script:

   ```
   pip install -r blind_study/requirements.txt
   ```

4. **Pick the repository and branch `blind-pricing-study`**, and start with:

   > Read CLAUDE.md and blind_study/TASK.md, then start the study (or resume it from
   > blind_study/NOTES.md and blind_study/RESULTS.md if they already contain progress).
   > Follow the checkpoint protocol: append to RESULTS.md after every experiment and commit
   > and push regularly.

5. **Close the browser whenever you like.** The session keeps running in the cloud.

## Resuming

- **If the session stops,** reopen it at claude.ai/code (conversation and branch are kept)
  and say "resume from blind_study/NOTES.md".
- **For a fresh session,** pick the branch the last session pushed to.
- **To pull a cloud session into your terminal:** `claude --teleport <session-id>`.
