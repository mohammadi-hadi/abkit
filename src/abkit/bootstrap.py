"""Stratified bootstrap confidence intervals.

Units are resampled within their arm (or other stratum), never across, so the
group sizes that determine a statistic's sampling distribution are preserved.
Percentile intervals, seeded PCG64, no BLAS.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np

MAX_UNDEFINED_SHARE = 0.1
"""If more than this share of resamples yields nan, the CI is not reported."""


def bootstrap_ci(
    statistic: Callable[..., float],
    groups: Sequence[Sequence[float]],
    n_resamples: int = 1000,
    seed: int = 0,
) -> tuple[float, tuple[float, float] | None]:
    """Point estimate and 95% percentile CI, resampling within each group."""
    point = statistic(*groups)
    rng = np.random.Generator(np.random.PCG64(seed))
    arrays = [list(group) for group in groups]
    values: list[float] = []
    undefined = 0
    for _ in range(n_resamples):
        resampled = []
        for group in arrays:
            indices = rng.integers(0, len(group), size=len(group)).tolist()
            resampled.append([group[i] for i in indices])
        value = statistic(*resampled)
        if math.isnan(value):
            undefined += 1
        else:
            values.append(value)
    if undefined > MAX_UNDEFINED_SHARE * n_resamples or not values:
        return point, None
    values.sort()
    lo = values[int(0.025 * len(values))]
    hi = values[min(len(values) - 1, int(0.975 * len(values)))]
    return point, (lo, hi)
