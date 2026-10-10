"""Shared data loading and metric helpers for the blind AC pricing study.

Everything reads only ``data/ac_units.csv`` inside this folder. No pandas: the
CSV is parsed into a dict of numpy arrays (strings kept as object arrays,
numeric columns converted on demand).
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "ac_units.csv")
OUT = os.path.join(ROOT, "out")

ARM_OF_CLASS = {
    "infantry_line": "infantry", "infantry_light": "infantry",
    "infantry_grenadiers": "infantry", "infantry_skirmishers": "infantry",
    "infantry_militia": "infantry", "infantry_irregulars": "infantry",
    "cavalry_light": "cavalry", "cavalry_standard": "cavalry",
    "cavalry_lancers": "cavalry", "cavalry_heavy": "cavalry",
    "cavalry_missile": "cavalry",
    "artillery_foot": "artillery", "artillery_horse": "artillery",
    "artillery_fixed": "artillery", "general": "general",
}


def load_raw() -> dict[str, np.ndarray]:
    with open(DATA, encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        rows = list(rd)
    cols = {h: np.array([r[i] for r in rows], dtype=object) for i, h in enumerate(header)}
    return cols


def num(col: np.ndarray, fill: float = np.nan) -> np.ndarray:
    out = np.full(len(col), fill, dtype=float)
    for i, v in enumerate(col):
        if v != "":
            out[i] = float(v)
    return out


def boolc(col: np.ndarray) -> np.ndarray:
    return np.array([v == "true" for v in col], dtype=bool)


@dataclass
class Data:
    raw: dict[str, np.ndarray]
    idx: np.ndarray  # indices into raw of the selected rows

    def s(self, name: str) -> np.ndarray:
        return self.raw[name][self.idx]

    def f(self, name: str, fill: float = np.nan) -> np.ndarray:
        return num(self.raw[name][self.idx], fill)

    def b(self, name: str) -> np.ndarray:
        return boolc(self.raw[name][self.idx])

    def __len__(self) -> int:
        return len(self.idx)


def regular_units(raw: dict[str, np.ndarray] | None = None) -> Data:
    """Regular units in scope: not general, not fixed artillery."""
    raw = raw if raw is not None else load_raw()
    isg = boolc(raw["is_general"])
    cls = raw["unit_class"]
    sel = np.where(~isg & (cls != "artillery_fixed"))[0]
    return Data(raw, sel)


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    err = p - y
    mae = float(np.mean(np.abs(err)))
    mape = float(np.mean(np.abs(err) / np.abs(y))) * 100
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"mae": mae, "mape": mape, "r2": r2, "n": int(len(y))}


def fold_metrics(y: np.ndarray, p: np.ndarray, fold: np.ndarray, mask: np.ndarray | None = None) -> dict[str, tuple[float, float]]:
    """mean +- sd over folds 1..5 of MAE, MAPE, R2 (only rows with fold>0 and mask)."""
    if mask is None:
        mask = np.ones(len(y), dtype=bool)
    res = {"mae": [], "mape": [], "r2": []}
    for k in range(1, 6):
        m = mask & (fold == k) & np.isfinite(p)
        if m.sum() < 2:
            continue
        mm = metrics(y[m], p[m])
        for key in res:
            res[key].append(mm[key])
    return {k: (float(np.mean(v)), float(np.std(v))) for k, v in res.items()}


def fmt_fm(fm: dict[str, tuple[float, float]]) -> str:
    return (f"MAE {fm['mae'][0]:.1f} ± {fm['mae'][1]:.1f} | MAPE {fm['mape'][0]:.2f}% | "
            f"R² {fm['r2'][0]:.4f}")


def append_results(row: list[str]) -> None:
    """Append a row to RESULTS.md (create header if missing)."""
    path = os.path.join(ROOT, "RESULTS.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# Experiment log\n\n")
            fh.write("| id | model / features | segment | CV MAE ± sd | MAPE % | R² | params | note |\n")
            fh.write("|---|---|---|---|---|---|---|---|\n")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(row) + " |\n")
