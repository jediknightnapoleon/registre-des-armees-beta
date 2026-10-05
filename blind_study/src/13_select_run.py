"""Exp 13 (selection step): nested per-segment feature selection for stage 1.

For each unit-type segment and each outer fold k (and 'all' for the final model), select
terms on the dev folds != k only (inner CV over those folds): backward-prune RICH, then
forward-add from a pool of extra terms (squares, men interactions, stat products, speed /
training / drill dummies, formation geometry). Results are cached in
out/sel/<seg>_<k>.json so the run can resume. Usage: python 13_select_run.py [n_workers]
"""
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT  # noqa
from explore_families import FAM, e10, get_dev  # noqa
from segsel import select_segment, name_of  # noqa

POOL_TERMS = [t for f in FAM.values() for t in f]
REGISTRY = {name_of(t): t for t in e10.RICH + POOL_TERMS}
SELDIR = os.path.join(OUT, "sel")
FOLDS = [0, 1, 2, 3, 4]


def job(args):
    seg, k = args
    path = os.path.join(SELDIR, f"{seg}_{k}.json")
    if os.path.exists(path):
        return path
    d = get_dev()
    d = d.assign(army_seg=d.faction_key + "|" + d.seg)
    s = d[(d.seg == seg) & (d.is_commander_variant == 0)]
    folds = [f for f in FOLDS if f != k] if k != "all" else FOLDS
    sel, mae = select_segment(s, e10.RICH, POOL_TERMS, folds)
    with open(path, "w") as f:
        json.dump({"seg": seg, "outer": k, "terms": [name_of(t) for t in sel],
                   "inner_mae": mae}, f, indent=1)
    print("done", seg, k, round(mae, 2), flush=True)
    return path


def load_spec(seg, k):
    with open(os.path.join(SELDIR, f"{seg}_{k}.json")) as f:
        return [REGISTRY[n] for n in json.load(f)["terms"]]


if __name__ == "__main__":
    os.makedirs(SELDIR, exist_ok=True)
    d = get_dev()
    segs = sorted(set(d.seg) - {"staff"})
    # biggest segments first so they don't straggle
    size = d[d.is_commander_variant == 0].seg.value_counts()
    segs.sort(key=lambda s: -size[s])
    jobs = [(s, k) for s in segs for k in FOLDS + ["all"]]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    with Pool(n) as p:
        for _ in p.imap_unordered(job, jobs):
            pass
