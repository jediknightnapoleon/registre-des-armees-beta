"""Helpers for (segmented) linear models on log price."""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from common import TARGET


def design(df, spec):
    """spec: list of column names / (name, func(df)->Series) / ('cat', col[, levels])."""
    cols = {}
    for s in spec:
        if isinstance(s, str):
            cols[s] = df[s].astype(float)
        elif s[0] == "cat":
            col = s[1]
            levels = s[2] if len(s) > 2 else sorted(df[col].dropna().unique())
            for lv in levels[1:]:  # first level is the reference
                cols[f"{col}={lv}"] = (df[col] == lv).astype(float)
        else:
            cols[s[0]] = s[1](df).astype(float)
    return pd.DataFrame(cols, index=df.index)


class LogLinear:
    """log(price) = b0 + X b, fitted by (lightly) ridge-regularised least squares."""

    def __init__(self, spec, alpha=1e-6, min_price=1.0):
        self.spec, self.alpha, self.min_price = spec, alpha, min_price

    def fit(self, df):
        X = design(df, self.spec)
        # fix categorical levels from training data
        self.spec_fixed = []
        for s in self.spec:
            if not isinstance(s, str) and s[0] == "cat" and len(s) == 2:
                self.spec_fixed.append(("cat", s[1], sorted(df[s[1]].dropna().unique())))
            else:
                self.spec_fixed.append(s)
        X = design(df, self.spec_fixed)
        self.cols = list(X.columns)
        self.mu = X.mean()
        self.sd = X.std().replace(0, 1).fillna(1)
        Z = ((X - self.mu) / self.sd).fillna(0).values
        y = np.log(df[TARGET].clip(lower=self.min_price).values)
        self.m = Ridge(alpha=self.alpha).fit(Z, y)
        self.coef = pd.Series(self.m.coef_ / self.sd.values, index=self.cols)
        self.intercept = self.m.intercept_ - (self.coef * self.mu).sum()
        return self

    def predict_log(self, df):
        X = design(df, self.spec_fixed).reindex(columns=self.cols)
        Z = ((X - self.mu) / self.sd).fillna(0).values
        return self.m.predict(Z)

    def predict(self, df):
        return np.exp(self.predict_log(df))

    def n_params(self):
        return len(self.cols) + 1


def segmented(seg_fn, models, fallback=None):
    """Return fit_predict(tr, te) that fits models[seg] on each segment."""
    def fit_predict(tr, te):
        out = np.full(len(te), np.nan)
        str_, ste = seg_fn(tr), seg_fn(te)
        for seg, factory in models.items():
            mtr, mte = str_ == seg, ste == seg
            if mte.sum() == 0:
                continue
            m = factory().fit(tr[mtr])
            out[np.where(mte)[0]] = m.predict(te[mte])
        if np.isnan(out).any():
            raise ValueError(f"unpredicted segments: {set(ste[np.isnan(out)])}")
        return out
    return fit_predict
