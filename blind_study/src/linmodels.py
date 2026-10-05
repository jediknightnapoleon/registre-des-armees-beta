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

    def __init__(self, spec, alpha=1e-6, min_price=1.0, clip=True):
        self.spec, self.alpha, self.min_price, self.clip = spec, alpha, min_price, clip

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
        self.lo, self.hi = X.min(), X.max()
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
        if self.clip:
            X = X.clip(self.lo, self.hi, axis=1)
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


def ridge_solve(X, y, pen, w=None):
    """Weighted least squares with a per-column ridge penalty vector (0 = unpenalised)."""
    X = np.asarray(X, float)
    w = np.ones(len(y)) if w is None else np.asarray(w, float)
    Xw = X * w[:, None]
    A = X.T @ Xw + np.diag(pen)
    b = Xw.T @ y
    return np.linalg.solve(A + 1e-9 * np.eye(len(pen)), b)


class JointLogLinear:
    """log(price) = seg-specific linear terms + shared faction offset.

    seg_fn(df) -> array of segment labels; specs[seg] -> feature spec for that segment
    (an intercept per segment is always included). Faction offset:
    -log(corps_n/10) (fixed, if use_n) + per-faction deviation (ridge penalty lam_f;
    lam_f=None disables the deviations). Rows where rule_fn(df) is not NaN are priced
    by the rule and not used in fitting.
    """

    def __init__(self, seg_fn, specs, use_n=True, lam_f=1.0, lam=1e-4, rule_fn=None,
                 faction_col="faction_key", clip=True, weight="none", irls=0):
        self.seg_fn, self.specs, self.use_n, self.lam_f, self.lam = seg_fn, specs, use_n, lam_f, lam
        self.clip, self.weight, self.irls = clip, weight, irls
        self.rule_fn, self.faction_col = rule_fn, faction_col

    def _blocks(self, df, fit):
        seg = np.asarray(self.seg_fn(df))
        mats = []
        if fit:
            self.segs = sorted(self.specs)
            self.fixed = {}
        for s in self.segs:
            spec = self.specs[s]
            if fit:
                sub = df[seg == s]
                fx = []
                for t in spec:
                    if not isinstance(t, str) and t[0] == "cat" and len(t) == 2:
                        fx.append(("cat", t[1], sorted(sub[t[1]].dropna().unique())))
                    else:
                        fx.append(t)
                self.fixed[s] = fx
            X = design(df, self.fixed[s]).fillna(0)
            X.insert(0, "const", 1.0)
            X = X.mul((seg == s).astype(float), axis=0)
            X.columns = [f"{s}:{c}" for c in X.columns]
            mats.append(X)
        if self.lam_f is not None:
            if fit:
                self.factions = sorted(df[self.faction_col].dropna().unique())
            F = pd.DataFrame({f"fac:{f}": (df[self.faction_col] == f).astype(float)
                              for f in self.factions}, index=df.index)
            mats.append(F)
        return pd.concat(mats, axis=1), seg

    def _offset(self, df):
        return -np.log(df["corps_n"].fillna(10).clip(lower=1) / 10.0) if self.use_n else 0.0

    def fit(self, df):
        if self.rule_fn is not None:
            df = df[np.isnan(self.rule_fn(df))]
        X, seg = self._blocks(df, fit=True)
        self.cols = list(X.columns)
        # per-column range over the rows of that column's segment (used to clamp at predict)
        self.lo = pd.Series(0.0, index=self.cols); self.hi = pd.Series(0.0, index=self.cols)
        for c in self.cols:
            if c.startswith("fac:") or c.endswith(":const"):
                continue
            m = seg == c.split(":")[0]
            self.lo[c], self.hi[c] = X.loc[m, c].min(), X.loc[m, c].max()
        y = np.log(df[TARGET].clip(lower=1).values) - self._offset(df)
        # standardise non-constant, non-faction columns within their segment
        Xv = X.values.copy()
        self.mu = np.zeros(Xv.shape[1]); self.sd = np.ones(Xv.shape[1])
        for j, c in enumerate(self.cols):
            if c.endswith(":const") or c.startswith("fac:"):
                continue
            s = c.split(":")[0]
            m = seg == s
            mu, sd = Xv[m, j].mean(), Xv[m, j].std()
            sd = sd if sd > 0 else 1.0
            self.mu[j], self.sd[j] = mu, sd
            Xv[m, j] = (Xv[m, j] - mu) / sd
        pen = np.array([0.0 if c.endswith(":const") else
                        (self.lam_f if c.startswith("fac:") else self.lam) for c in self.cols])
        pen = pen * len(df)
        if self.weight == "price":
            w0 = df[TARGET].clip(lower=1).values.astype(float)
        elif self.weight == "sqrtprice":
            w0 = np.sqrt(df[TARGET].clip(lower=1).values.astype(float))
        else:
            w0 = np.ones(len(df))
        w0 = w0 / w0.mean()
        beta = ridge_solve(Xv, y, pen, w0)
        for _ in range(self.irls):  # IRLS towards weighted least absolute deviation
            r = np.abs(y - Xv @ beta)
            beta = ridge_solve(Xv, y, pen, w0 / np.maximum(r, 0.01) * np.mean(np.maximum(r, 0.01)))
        # convert back to raw-scale coefficients
        self.coef = pd.Series(beta / self.sd, index=self.cols)
        for s in self.segs:
            idx = [j for j, c in enumerate(self.cols) if c.startswith(s + ":") and not c.endswith(":const")]
            self.coef[f"{s}:const"] -= np.sum(beta[idx] * self.mu[idx] / self.sd[idx])
        return self

    def predict_log(self, df):
        X, seg = self._blocks(df, fit=False)
        X = X.reindex(columns=self.cols, fill_value=0.0)
        if self.clip:
            for s in self.segs:
                m = seg == s
                if not m.any():
                    continue
                cs = [c for c in self.cols if c.startswith(s + ":") and not c.endswith(":const")]
                X.loc[m, cs] = X.loc[m, cs].clip(self.lo[cs], self.hi[cs], axis=1)
        return X.values @ self.coef.values + self._offset(df)

    def predict(self, df):
        p = np.exp(self.predict_log(df))
        if self.rule_fn is not None:
            r = self.rule_fn(df)
            p = np.where(np.isnan(r), p, r)
        return p

    def n_params_by_seg(self):
        out = {s: sum(1 for c in self.cols if c.startswith(s + ":")) for s in self.segs}
        out["faction"] = sum(1 for c in self.cols if c.startswith("fac:"))
        return out
