"""Nonlinear fitting helper: robust (soft-L1, ~MAE) least squares with scipy."""
from __future__ import annotations
import numpy as np
from scipy.optimize import least_squares
from harness import Y


def fit_nl(fun, theta0, tr, f_scale=3.0):
    """fun(theta, mask) -> predictions for rows in mask."""
    res = least_squares(lambda th: fun(th, tr) - Y[tr], theta0, loss="soft_l1", f_scale=f_scale,
                        max_nfev=4000, x_scale="jac")
    return res.x


def nl_fit_fn(fun, theta0, f_scale=3.0):
    def fit_fn(tr):
        th = fit_nl(fun, theta0, tr, f_scale)
        return (lambda m: fun(th, m)), {"theta": th}
    return fit_fn
