"""Statistics used by the probes.

Everything here is closed-form or an explicit seeded simulation, implemented
on top of the standard library and elementwise numpy — no scipy at runtime and
no BLAS in any statistic's path, so the same data gives the same digits on any
machine. The test suite cross-checks each function against scipy or
statsmodels.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from statistics import NormalDist

import numpy as np

_STANDARD_NORMAL = NormalDist()


def normal_cdf(x: float) -> float:
    return _STANDARD_NORMAL.cdf(x)


def normal_pdf(x: float) -> float:
    return _STANDARD_NORMAL.pdf(x)


def normal_ppf(q: float) -> float:
    return _STANDARD_NORMAL.inv_cdf(q)


def _lower_gamma_series(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) by series, for x < a + 1."""
    term = 1.0 / a
    total = term
    denom = a
    for _ in range(1000):
        denom += 1.0
        term *= x / denom
        total += term
        if abs(term) < abs(total) * 1e-16:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _upper_gamma_cf(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) by continued fraction."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b if b != 0 else 1.0 / tiny
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_sf(x: float, df: float) -> float:
    """Survival function of the chi-square distribution."""
    if x <= 0:
        return 1.0
    a = df / 2.0
    half = x / 2.0
    if half < a + 1.0:
        p = 1.0 - _lower_gamma_series(a, half)
    else:
        p = _upper_gamma_cf(a, half)
    return min(1.0, max(0.0, p))


def srm_chi2(counts: Mapping[str, int], split: Mapping[str, float]) -> tuple[float, float]:
    """Chi-square statistic and p-value for observed arm counts vs the intended split."""
    total = sum(counts.get(arm, 0) for arm in split)
    weight_total = sum(split.values())
    stat = 0.0
    for arm, weight in split.items():
        expected = total * weight / weight_total
        observed = counts.get(arm, 0)
        stat += (observed - expected) ** 2 / expected
    return stat, chi2_sf(stat, len(split) - 1)


def mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values))


def variance(values: Sequence[float]) -> float:
    """Unbiased sample variance."""
    m = mean(values)
    return float(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def welch(
    treatment: Sequence[float], control: Sequence[float]
) -> tuple[float, float, float, float]:
    """Difference in means with its standard error, z statistic and two-sided p.

    Uses the normal approximation, which is what experimentation platforms
    report at the sample sizes where an audit matters.
    """
    effect = mean(treatment) - mean(control)
    se = math.sqrt(variance(treatment) / len(treatment) + variance(control) / len(control))
    if se == 0.0:
        return effect, 0.0, math.inf if effect else 0.0, 0.0 if effect else 1.0
    z = effect / se
    p = 2.0 * (1.0 - normal_cdf(abs(z)))
    return effect, se, z, p


def two_proportion_z(
    successes_a: int, n_a: int, successes_b: int, n_b: int
) -> tuple[float, float, float]:
    """Difference in proportions, pooled z statistic and two-sided p."""
    p_a = successes_a / n_a
    p_b = successes_b / n_b
    pooled = (successes_a + successes_b) / (n_a + n_b)
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n_a + 1.0 / n_b))
    if se == 0.0:
        return p_a - p_b, 0.0, 1.0
    z = (p_a - p_b) / se
    return p_a - p_b, z, 2.0 * (1.0 - normal_cdf(abs(z)))


def standardized_mean_difference(treatment: Sequence[float], control: Sequence[float]) -> float:
    """Cohen-style SMD with the pooled (average-variance) denominator."""
    sd = math.sqrt((variance(treatment) + variance(control)) / 2.0)
    if sd == 0.0:
        return 0.0
    return (mean(treatment) - mean(control)) / sd


def benjamini_hochberg(pvalues: Sequence[float], alpha: float) -> list[bool]:
    """Step-up FDR control; returns a rejection flag per input p-value."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    threshold_rank = 0
    for rank, idx in enumerate(order, start=1):
        if pvalues[idx] <= rank * alpha / m:
            threshold_rank = rank
    rejected = [False] * m
    for rank, idx in enumerate(order, start=1):
        if rank <= threshold_rank:
            rejected[idx] = True
    return rejected


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0.0 or syy == 0.0:
        return math.nan
    return sxy / math.sqrt(sxx * syy)


def cuped_reduction(post: Sequence[float], pre: Sequence[float]) -> float:
    """Share of metric variance CUPED would have removed, rho squared."""
    rho = pearson(post, pre)
    if math.isnan(rho):
        return 0.0
    return rho * rho


def design_analysis(true_effect: float, se: float, alpha: float) -> tuple[float, float, float]:
    """Power, Type-S rate and Type-M exaggeration ratio (Gelman and Carlin).

    For an estimator distributed N(true_effect, se) and a two-sided test at
    ``alpha``: the probability of significance, the probability a significant
    result has the wrong sign, and the expected |estimate| among significant
    results divided by |true_effect|.
    """
    if true_effect == 0.0 or se <= 0.0:
        raise ValueError("design_analysis needs a nonzero effect and positive se")
    crit = normal_ppf(1.0 - alpha / 2.0) * se
    mu = abs(true_effect)
    hi = (crit - mu) / se
    lo = (-crit - mu) / se
    p_hi = 1.0 - normal_cdf(hi)
    p_lo = normal_cdf(lo)
    power = p_hi + p_lo
    upper_mass = mu * p_hi + se * normal_pdf(hi)
    lower_mass = mu * p_lo - se * normal_pdf(lo)
    exaggeration = (upper_mass - lower_mass) / power / mu
    type_s = p_lo / power
    return power, type_s, exaggeration


def schedule_false_positive_rate(
    look_ns: Sequence[int], alpha: float, seed: int = 0, n_sim: int = 20_000
) -> float:
    """False-positive rate of "stop when any look is significant" under H0.

    Simulates the z-statistic path at the given cumulative sample sizes as a
    Brownian motion observed at those information fractions, and counts null
    experiments in which any look crosses the fixed-horizon critical value.
    Seeded PCG64, elementwise numpy only.
    """
    if any(b <= a for a, b in zip(look_ns, look_ns[1:], strict=False)):
        raise ValueError("look sample sizes must be strictly increasing")
    z_crit = normal_ppf(1.0 - alpha / 2.0)
    fractions = np.asarray(look_ns, dtype=np.float64) / float(look_ns[-1])
    dt = np.diff(np.concatenate([np.zeros(1), fractions]))
    rng = np.random.Generator(np.random.PCG64(seed))
    increments = rng.standard_normal((n_sim, len(look_ns))) * np.sqrt(dt)
    paths = np.cumsum(increments, axis=1)
    z_paths = paths / np.sqrt(fractions)
    crossed = (np.abs(z_paths) >= z_crit).any(axis=1)
    return float(crossed.sum()) / float(n_sim)
