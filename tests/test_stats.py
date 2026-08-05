"""Every statistic is cross-checked against scipy or statsmodels.

The library itself depends on neither; these tests are why its hand-rolled
implementations can be trusted.
"""

import math

import numpy as np
import pytest
import scipy.integrate
import scipy.stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest

from abkit.stats import (
    benjamini_hochberg,
    chi2_sf,
    cuped_reduction,
    design_analysis,
    normal_cdf,
    normal_pdf,
    normal_ppf,
    pearson,
    schedule_false_positive_rate,
    srm_chi2,
    standardized_mean_difference,
    two_proportion_z,
    welch,
)


def test_normal_functions_match_scipy():
    for x in (-3.7, -1.0, -0.2, 0.0, 0.5, 1.96, 4.2):
        assert normal_cdf(x) == pytest.approx(scipy.stats.norm.cdf(x), abs=1e-12)
        assert normal_pdf(x) == pytest.approx(scipy.stats.norm.pdf(x), abs=1e-12)
    for q in (0.001, 0.025, 0.5, 0.975, 0.999):
        assert normal_ppf(q) == pytest.approx(scipy.stats.norm.ppf(q), abs=1e-9)


def test_chi2_sf_matches_scipy_across_df():
    for df in range(1, 11):
        for x in (0.01, 0.5, 1.0, 2.7, 5.0, 10.0, 25.0, 60.0):
            assert chi2_sf(x, df) == pytest.approx(scipy.stats.chi2.sf(x, df), rel=1e-10, abs=1e-14)


def test_srm_chi2_matches_scipy_chisquare():
    counts = {"control": 5150, "treatment": 4850}
    stat, p = srm_chi2(counts, {"control": 0.5, "treatment": 0.5})
    ref = scipy.stats.chisquare([5150, 4850], f_exp=[5000, 5000])
    assert stat == pytest.approx(ref.statistic, rel=1e-12)
    assert p == pytest.approx(ref.pvalue, rel=1e-10)

    counts3 = {"a": 3400, "b": 3300, "c": 3300}
    stat3, p3 = srm_chi2(counts3, {"a": 1, "b": 1, "c": 1})
    ref3 = scipy.stats.chisquare([3400, 3300, 3300])
    assert stat3 == pytest.approx(ref3.statistic, rel=1e-12)
    assert p3 == pytest.approx(ref3.pvalue, rel=1e-10)


def test_welch_matches_scipy_ttest_statistic():
    rng = np.random.Generator(np.random.PCG64(0))
    a = rng.standard_normal(2000) + 0.1
    b = rng.standard_normal(1900)
    effect, se, z, p = welch(a.tolist(), b.tolist())
    ref = scipy.stats.ttest_ind(a, b, equal_var=False)
    assert z == pytest.approx(ref.statistic, rel=1e-10)
    assert effect == pytest.approx(a.mean() - b.mean(), rel=1e-10)
    assert p == pytest.approx(2 * scipy.stats.norm.sf(abs(z)), rel=1e-10)
    assert p == pytest.approx(ref.pvalue, abs=2e-3)


def test_two_proportion_z_matches_statsmodels():
    diff, z, p = two_proportion_z(430, 5000, 380, 5000)
    stat, ref_p = proportions_ztest([430, 380], [5000, 5000])
    assert z == pytest.approx(stat, rel=1e-10)
    assert p == pytest.approx(ref_p, rel=1e-10)
    assert diff == pytest.approx(430 / 5000 - 380 / 5000, rel=1e-12)


def test_benjamini_hochberg_matches_statsmodels():
    rng = np.random.Generator(np.random.PCG64(1))
    for _ in range(20):
        pvalues = rng.random(15).tolist()
        pvalues[0] = 1e-5
        ours = benjamini_hochberg(pvalues, 0.05)
        theirs = multipletests(pvalues, alpha=0.05, method="fdr_bh")[0].tolist()
        assert ours == theirs


def test_pearson_matches_numpy():
    rng = np.random.Generator(np.random.PCG64(2))
    x = rng.standard_normal(500)
    y = 0.6 * x + 0.8 * rng.standard_normal(500)
    assert pearson(x.tolist(), y.tolist()) == pytest.approx(np.corrcoef(x, y)[0, 1], rel=1e-12)
    assert math.isnan(pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]))


def test_cuped_reduction_is_rho_squared():
    rng = np.random.Generator(np.random.PCG64(3))
    pre = rng.standard_normal(4000)
    post = 0.6 * pre + 0.8 * rng.standard_normal(4000)
    rho = np.corrcoef(pre, post)[0, 1]
    assert cuped_reduction(post.tolist(), pre.tolist()) == pytest.approx(rho**2, rel=1e-10)


def test_standardized_mean_difference_recovers_implanted_shift():
    rng = np.random.Generator(np.random.PCG64(4))
    control = rng.standard_normal(20000)
    treatment = rng.standard_normal(20000) + 0.3
    smd = standardized_mean_difference(treatment.tolist(), control.tolist())
    assert smd == pytest.approx(0.3, abs=0.03)


def _numeric_design(mu: float, se: float, alpha: float):
    crit = scipy.stats.norm.ppf(1 - alpha / 2) * se
    power = scipy.stats.norm.sf(crit, mu, se) + scipy.stats.norm.cdf(-crit, mu, se)
    upper = scipy.integrate.quad(
        lambda x: abs(x) * scipy.stats.norm.pdf(x, mu, se), crit, mu + 20 * se
    )[0]
    lower = scipy.integrate.quad(
        lambda x: abs(x) * scipy.stats.norm.pdf(x, mu, se), mu - 20 * se, -crit
    )[0]
    exaggeration = (upper + lower) / power / abs(mu)
    type_s = scipy.stats.norm.cdf(-crit, mu, se) / power
    return power, type_s, exaggeration


def test_design_analysis_matches_numeric_integration():
    for mu, se in ((0.5, 1.0), (1.0, 0.7), (2.8, 1.0), (0.2, 0.5)):
        power, type_s, exaggeration = design_analysis(mu, se, 0.05)
        ref_power, ref_type_s, ref_exaggeration = _numeric_design(mu, se, 0.05)
        assert power == pytest.approx(ref_power, abs=1e-8)
        assert type_s == pytest.approx(ref_type_s, abs=1e-8)
        assert exaggeration == pytest.approx(ref_exaggeration, abs=1e-6)


def test_design_analysis_known_shape():
    power, type_s, exaggeration = design_analysis(0.5, 1.0, 0.05)
    assert power == pytest.approx(0.079, abs=0.002)
    assert exaggeration > 3.0
    high_power, _, low_exaggeration = design_analysis(4.0, 1.0, 0.05)
    assert high_power > 0.97
    assert low_exaggeration == pytest.approx(1.0, abs=0.02)
    with pytest.raises(ValueError):
        design_analysis(0.0, 1.0, 0.05)


def test_schedule_fpr_matches_group_sequential_tables():
    """Armitage/Pocock repeated-significance rates for equally spaced looks."""
    horizon = 10000
    cases = ((1, 0.05, 0.006), (2, 0.083, 0.01), (5, 0.142, 0.012), (10, 0.193, 0.015))
    for k, expected, tol in cases:
        ns = [horizon * (i + 1) // k for i in range(k)]
        fpr = schedule_false_positive_rate(ns, 0.05, seed=0)
        assert fpr == pytest.approx(expected, abs=tol)


def test_schedule_fpr_is_deterministic_and_validates():
    ns = [100, 200, 300]
    assert schedule_false_positive_rate(ns, 0.05) == schedule_false_positive_rate(ns, 0.05)
    with pytest.raises(ValueError):
        schedule_false_positive_rate([100, 100], 0.05)
