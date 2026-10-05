"""Two-stage model: (1) log-linear model of regular units + staff generals (JointLogLinear);
(2) commander variants priced additively from the regular-unit prediction:
    price_cv = max(1, a_g * p_reg + b_{g,stars} / d),   d = N/10,
where p_reg is stage 1's price for the commander's own row (as if it were a regular unit of
its type), and g is a commander group (global / base type / unit type)."""
import numpy as np
import pandas as pd

from common import TARGET
from linmodels import JointLogLinear, ridge_solve


def _cv_design(df, p_reg, star_levels):
    d = (df["corps_n"].fillna(10).clip(lower=1) / 10.0).values
    cols = {"a": p_reg}
    s = df["stars"].clip(upper=star_levels[-1]).values
    for lv in star_levels:
        cols[f"b{lv}"] = (s == lv).astype(float) / d
    return pd.DataFrame(cols, index=df.index)


class TwoStage:
    def __init__(self, reg_seg_fn, reg_specs, army_col, lam_f=1e-4, rule_fn=None,
                 cv_group_fn=None, lowcut=50, star_levels=(0, 1, 2, 3, 4, 5),
                 cv_loss="l2", reg_lam=1e-4):
        self.reg_seg_fn, self.reg_specs, self.army_col = reg_seg_fn, reg_specs, army_col
        self.lam_f, self.rule_fn, self.lowcut = lam_f, rule_fn, lowcut
        self.cv_group_fn = cv_group_fn or (lambda d: np.full(len(d), "all", dtype=object))
        self.star_levels = list(star_levels)
        self.cv_loss, self.reg_lam = cv_loss, reg_lam

    def fit(self, df):
        reg = df[df["is_commander_variant"] == 0]
        reg = reg[(reg[TARGET] >= self.lowcut) | (reg["staff_general"] == 1)]
        self.stage1 = JointLogLinear(self.reg_seg_fn, self.reg_specs, use_n=True,
                                     lam_f=self.lam_f, rule_fn=self.rule_fn,
                                     faction_col=self.army_col, lam=self.reg_lam).fit(reg)
        cv = df[df["is_commander_variant"] == 1]
        p_reg = self.stage1.predict(cv)
        X = _cv_design(cv, p_reg, self.star_levels)
        y = cv[TARGET].values.astype(float)
        g = np.asarray(self.cv_group_fn(cv))
        self.cv_coef = {}
        for grp in sorted(set(g)):
            m = g == grp
            Xg, yg = X.values[m], y[m]
            pen = np.full(Xg.shape[1], 1e-6)
            w = np.ones(m.sum())
            for _ in range(30 if self.cv_loss == "l1" else 1):  # IRLS for least absolute dev.
                beta = ridge_solve(Xg, yg, pen, w)
                if self.cv_loss == "l1":
                    w = 1.0 / np.maximum(np.abs(yg - Xg @ beta), 1.0)
            self.cv_coef[grp] = pd.Series(beta, index=X.columns)
        return self

    def predict(self, df):
        out = np.asarray(self.stage1.predict(df), float).copy()
        cvm = (df["is_commander_variant"] == 1).values
        if cvm.any():
            cv = df[cvm]
            p_reg = out[cvm]
            X = _cv_design(cv, p_reg, self.star_levels)
            g = np.asarray(self.cv_group_fn(cv))
            p = np.empty(len(cv))
            for grp in set(g):
                m = g == grp
                coef = self.cv_coef.get(grp, self.cv_coef.get("all"))
                p[m] = X.values[m] @ coef.values
            out[cvm] = np.maximum(p, 1.0)
        return out
