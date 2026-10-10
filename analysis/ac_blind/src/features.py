"""Feature construction and a generalised ridge solver (per-group penalties).

Design matrices are built as a list of named blocks; each block has a penalty
group so that e.g. army offsets can be shrunk harder than unit stats.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from common import Data

STATS = ["accuracy", "reload_skill", "ammo", "morale", "melee_attack", "melee_defense", "charge_bonus"]
BOOLS = ["can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
         "has_guerrilla_deployment", "can_place_stakes", "can_place_mines", "scares_enemies",
         "can_build_barricades", "skirmish", "guard_mode", "can_snipe", "pike_square"]
TRAIN_LEVELS = ["mob", "poorly_trained", "trained", "well_trained", "elite"]


@dataclass
class Design:
    names: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    cols: list[np.ndarray] = field(default_factory=list)

    def add(self, name: str, col: np.ndarray, group: str = "main") -> None:
        self.names.append(name)
        self.groups.append(group)
        self.cols.append(np.asarray(col, dtype=float))

    def add_onehot(self, prefix: str, values: np.ndarray, group: str = "main",
                   levels: list[str] | None = None, drop: str | None = None) -> None:
        levels = levels if levels is not None else sorted(set(values.tolist()))
        for lv in levels:
            if lv == drop:
                continue
            self.add(f"{prefix}={lv}", (values == lv).astype(float), group)

    def matrix(self) -> np.ndarray:
        return np.column_stack(self.cols) if self.cols else np.zeros((0, 0))


def gridge_fit(X: np.ndarray, y: np.ndarray, pen: np.ndarray, w: np.ndarray | None = None) -> tuple[float, np.ndarray]:
    """min sum w (y - a - Xb)^2 + sum pen_j b_j^2 ; intercept a unpenalised."""
    n = len(y)
    if w is None:
        w = np.ones(n)
    sw = w.sum()
    xm = (w[:, None] * X).sum(0) / sw
    ym = (w * y).sum() / sw
    Xc = X - xm
    yc = y - ym
    A = Xc.T @ (w[:, None] * Xc) + np.diag(pen)
    b = np.linalg.solve(A + 1e-9 * np.eye(len(pen)), Xc.T @ (w * yc))
    a = ym - xm @ b
    return a, b


def onehot_levels(values: np.ndarray) -> list[str]:
    return sorted(set(values.tolist()))
