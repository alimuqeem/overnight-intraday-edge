"""
OLS with Newey-West (HAC) standard errors, implemented directly on numpy
so the offline analysis pipeline needs nothing beyond numpy/scipy.

Daily equity returns are autocorrelated and volatility-clustered, so a
naive t-test (std/sqrt(n)) understates the true standard error and
overstates significance -- this is what a plain scipy.stats.ttest_1samp
does. Newey-West corrects for that by adding weighted autocovariance
terms up to a chosen lag before taking the square root.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def newey_west_lags(n: int) -> int:
    """Newey & West (1994) automatic lag-selection rule."""
    return max(1, int(np.floor(4 * (n / 100) ** (2 / 9))))


def hac_ols(y: np.ndarray, X: np.ndarray, lags: int | None = None):
    """OLS of y on X (X must include a column of ones for an intercept)
    with Newey-West HAC standard errors.

    Returns dict with coefs, se, t_stat, p_value (each length = X.shape[1]),
    plus n, lags_used, r_squared.
    """
    n, k = X.shape
    if lags is None:
        lags = newey_west_lags(n)

    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta

    # Newey-West HAC covariance of the moment conditions
    scores = X * resid[:, None]  # n x k
    S = scores.T @ scores  # lag 0
    for lag in range(1, lags + 1):
        weight = 1 - lag / (lags + 1)
        Gamma = scores[lag:].T @ scores[:-lag]
        S += weight * (Gamma + Gamma.T)

    cov_beta = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(cov_beta))
    t_stat = beta / se
    p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), df=n - k))

    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return {
        "coefs": beta,
        "se": se,
        "t_stat": t_stat,
        "p_value": p_value,
        "n": n,
        "lags_used": lags,
        "r_squared": r_squared,
    }


def hac_mean_test(returns: np.ndarray, lags: int | None = None):
    """HAC-robust one-sample test of whether the mean of `returns` is
    zero -- the autocorrelation-robust replacement for
    scipy.stats.ttest_1samp on daily return series."""
    X = np.ones((len(returns), 1))
    out = hac_ols(np.asarray(returns), X, lags=lags)
    return {
        "mean": out["coefs"][0],
        "se": out["se"][0],
        "t_stat": out["t_stat"][0],
        "p_value": out["p_value"][0],
        "n": out["n"],
        "lags_used": out["lags_used"],
    }
