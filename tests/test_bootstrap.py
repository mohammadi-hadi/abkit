import math

import pytest

from abkit.bootstrap import bootstrap_ci
from abkit.stats import mean


def test_bootstrap_is_deterministic():
    data = [float(i % 7) for i in range(200)]
    first = bootstrap_ci(mean, (data,), seed=0)
    second = bootstrap_ci(mean, (data,), seed=0)
    assert first == second
    third = bootstrap_ci(mean, (data,), seed=1)
    assert third != first


def test_bootstrap_brackets_the_sample_statistic():
    data = [float(i % 11) for i in range(500)]
    point, ci = bootstrap_ci(mean, (data,))
    assert ci is not None
    assert ci[0] <= point <= ci[1]
    assert point == pytest.approx(mean(data))


def test_bootstrap_preserves_group_sizes():
    sizes = []

    def statistic(a, b):
        sizes.append((len(a), len(b)))
        return 0.0

    bootstrap_ci(statistic, ([1.0] * 30, [2.0] * 70), n_resamples=5)
    assert all(pair == (30, 70) for pair in sizes)


def test_bootstrap_withholds_ci_when_statistic_is_mostly_undefined():
    def statistic(a):
        return math.nan

    point, ci = bootstrap_ci(statistic, ([1.0, 2.0, 3.0],))
    assert math.isnan(point)
    assert ci is None
