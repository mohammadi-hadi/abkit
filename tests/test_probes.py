"""Validation by implantation: each probe must recover its own dial, stay
monotone in it, and stay silent on the clean experiment."""

import pytest

from abkit.probes import (
    FRAGILITY_CAP,
    contamination,
    covariate_balance,
    cuped_headroom,
    novelty,
    outlier_fragility,
    peeking,
    sample_ratio,
    uncorrected_winners,
    variance_ratio,
    winners_curse,
)
from abkit.result import ProbeResult, SkippedProbe
from abkit.schema import Design, Look, Unit
from abkit.stats import srm_chi2, welch
from abkit.synthetic import PRE_CORRELATION, simulate, simulate_peeking

CLEAN_UNITS, CLEAN_DESIGN = simulate(n=8000, effect=0.2, mde=0.2, seed=11)


def test_clean_experiment_carries_no_flags():
    checks = [
        sample_ratio(CLEAN_UNITS, CLEAN_DESIGN),
        contamination(CLEAN_UNITS),
        outlier_fragility(CLEAN_UNITS, CLEAN_DESIGN),
        novelty(CLEAN_UNITS, CLEAN_DESIGN),
        winners_curse(CLEAN_UNITS, CLEAN_DESIGN),
        variance_ratio(CLEAN_UNITS, CLEAN_DESIGN),
        cuped_headroom(CLEAN_UNITS, CLEAN_DESIGN),
    ]
    balance = covariate_balance(CLEAN_UNITS, CLEAN_DESIGN)
    assert isinstance(balance, list)
    checks.extend(balance)
    for check in checks:
        assert isinstance(check, ProbeResult)
        assert not check.triggered, check.name


def test_sample_ratio_flags_implanted_leak():
    units, design = simulate(n=8000, effect=0.2, srm=0.03, seed=12)
    probe = sample_ratio(units, design)
    assert probe.triggered
    assert probe.value < 1e-3


def test_srm_statistic_is_monotone_in_the_leak():
    mild = srm_chi2({"control": 4800, "treatment": 5200}, {"control": 1, "treatment": 1})
    severe = srm_chi2({"control": 4500, "treatment": 5500}, {"control": 1, "treatment": 1})
    assert severe[0] > mild[0]
    assert severe[1] < mild[1]


def test_contamination_counts_implanted_double_assignments():
    units, _ = simulate(n=4000, effect=0.2, contaminated=25, seed=13)
    probe = contamination(units)
    assert probe.triggered
    assert probe.value == 25


def test_covariate_balance_recovers_the_implanted_shift():
    units, design = simulate(n=4000, effect=0.2, imbalance=0.3, seed=21)
    results = covariate_balance(units, design)
    assert isinstance(results, list)
    probe = results[0]
    assert probe.value == pytest.approx(0.3, abs=0.08)
    assert probe.triggered


def test_covariate_balance_is_monotone_in_the_shift():
    def implanted(imbalance: float) -> float:
        units, design = simulate(n=4000, effect=0.2, imbalance=imbalance, seed=22)
        results = covariate_balance(units, design)
        assert isinstance(results, list)
        return abs(results[0].value)

    assert implanted(0.5) > implanted(0.25) > implanted(0.0)


def test_covariate_balance_skips_without_pre_metrics():
    units, design = simulate(n=100, seed=1)
    stripped = [u.model_copy(update={"pre": {}}) for u in units]
    assert isinstance(covariate_balance(stripped, design), SkippedProbe)


def test_fragility_attributes_a_deterministic_whale_push():
    """Base effect just below significance, three whales push it over: the
    probe must attribute the significance to at most three units."""
    treat = [0.106 + (1.0 if i % 2 else -1.0) for i in range(400)] + [12.0] * 3
    ctrl = [(1.0 if i % 2 else -1.0) for i in range(400)]
    units = [
        Unit(unit_id=f"t{i}", arm="treatment", metrics={"outcome": v}) for i, v in enumerate(treat)
    ] + [Unit(unit_id=f"c{i}", arm="control", metrics={"outcome": v}) for i, v in enumerate(ctrl)]
    design = Design(
        split={"control": 0.5, "treatment": 0.5},
        control="control",
        treatment="treatment",
        primary_metric="outcome",
    )
    probe = outlier_fragility(units, design)
    assert isinstance(probe, ProbeResult)
    assert probe.triggered
    assert probe.value <= 3


def test_fragility_flags_exactly_the_whale_decisive_seeds():
    """Whenever the whales are what makes the result significant — significant
    with them, not without them — the probe must trigger with value <= 3."""
    found = 0
    for seed in range(60):
        units, design = simulate(n=1000, effect=0.12, whales=3, whale_value=15.0, seed=seed)
        treat = [u.metrics["outcome"] for u in units if u.arm == "treatment"]
        sans_whales = [
            u.metrics["outcome"]
            for u in units
            if u.arm == "treatment" and not u.unit_id.startswith("whale")
        ]
        ctrl = [u.metrics["outcome"] for u in units if u.arm == "control"]
        decisive = welch(treat, ctrl)[3] < 0.05 and welch(sans_whales, ctrl)[3] >= 0.05
        if not decisive:
            continue
        probe = outlier_fragility(units, design)
        assert isinstance(probe, ProbeResult)
        assert probe.triggered, f"seed {seed}"
        assert probe.value <= 3
        found += 1
    assert found >= 5


def test_fragility_stays_silent_on_a_broad_based_effect():
    probe = outlier_fragility(CLEAN_UNITS, CLEAN_DESIGN)
    assert isinstance(probe, ProbeResult)
    assert not probe.triggered
    assert probe.value == FRAGILITY_CAP


def test_fragility_reports_nothing_to_overturn_when_not_significant():
    units, design = simulate(n=400, effect=0.0, seed=3)
    probe = outlier_fragility(units, design)
    assert isinstance(probe, ProbeResult)
    assert not probe.triggered
    assert "not significant" in probe.detail


def test_uncorrected_winners_flags_metric_fishing():
    for seed in range(200):
        units, design = simulate(n=2000, effect=0.0, extra_metrics=40, seed=seed)
        probe = uncorrected_winners(units, design)
        assert isinstance(probe, ProbeResult)
        if probe.triggered:
            assert probe.value >= 1
            return
    raise AssertionError("40 null metrics never produced an uncorrected winner")


def test_uncorrected_winners_keeps_a_real_effect():
    units, design = simulate(n=8000, effect=0.3, extra_metrics=2, seed=30)
    probe = uncorrected_winners(units, design)
    assert isinstance(probe, ProbeResult)
    assert not probe.triggered


def test_uncorrected_winners_skips_with_one_metric():
    units, design = simulate(n=200, seed=1)
    assert isinstance(uncorrected_winners(units, design), SkippedProbe)


def test_peeking_flags_an_early_stopped_null():
    for seed in range(500):
        units, design = simulate_peeking(n_max=5000, look_every=250, effect=0.0, seed=seed)
        looks = design.looks or []
        if looks and looks[-1].n < 5000 and abs(looks[-1].z) >= 1.96:
            probe = peeking(design)
            assert isinstance(probe, ProbeResult)
            assert probe.triggered
            assert probe.value > 1.5 * design.alpha
            return
    raise AssertionError("no early-stopping null experiment found")


def test_peeking_accepts_a_single_final_look():
    design = Design(
        split={"control": 0.5, "treatment": 0.5},
        control="control",
        treatment="treatment",
        primary_metric="outcome",
        looks=[Look(n=5000, z=2.5)],
    )
    assert isinstance(peeking(design), SkippedProbe)


def test_peeking_does_not_flag_an_insignificant_final_look():
    design = Design(
        split={"control": 0.5, "treatment": 0.5},
        control="control",
        treatment="treatment",
        primary_metric="outcome",
        looks=[Look(n=1000, z=0.4), Look(n=2000, z=0.8), Look(n=3000, z=0.5)],
    )
    probe = peeking(design)
    assert isinstance(probe, ProbeResult)
    assert not probe.triggered
    assert probe.value > 0.05


def test_novelty_recovers_the_implanted_decay():
    units, design = simulate(n=6000, effect=0.15, novelty=0.3, seed=16)
    probe = novelty(units, design)
    assert isinstance(probe, ProbeResult)
    assert probe.value == pytest.approx(0.3, abs=0.1)
    assert probe.triggered


def test_novelty_is_monotone_in_the_decay():
    def implanted(dial: float) -> float:
        units, design = simulate(n=6000, effect=0.15, novelty=dial, seed=17)
        probe = novelty(units, design)
        assert isinstance(probe, ProbeResult)
        return probe.value

    assert implanted(0.5) > implanted(0.25)


def test_novelty_skips_without_timestamps():
    units, design = simulate(n=200, seed=1)
    stripped = [u.model_copy(update={"t": None}) for u in units]
    assert isinstance(novelty(stripped, design), SkippedProbe)


def test_winners_curse_flags_an_underpowered_significant_result():
    for seed in range(500):
        units, design = simulate(n=300, effect=0.1, mde=0.1, seed=seed)
        probe = winners_curse(units, design)
        assert isinstance(probe, ProbeResult)
        if probe.triggered:
            assert probe.value > 1.5
            return
    raise AssertionError("no significant underpowered experiment found")


def test_winners_curse_stays_silent_when_well_powered():
    probe = winners_curse(CLEAN_UNITS, CLEAN_DESIGN)
    assert isinstance(probe, ProbeResult)
    assert not probe.triggered
    assert probe.value == pytest.approx(1.0, abs=0.1)


def test_descriptive_probes_never_trigger():
    units, design = simulate(n=1000, effect=0.12, whales=5, whale_value=20.0, seed=18)
    ratio = variance_ratio(units, design)
    assert isinstance(ratio, ProbeResult)
    assert ratio.value > 1.5
    assert not ratio.triggered

    headroom = cuped_headroom(CLEAN_UNITS, CLEAN_DESIGN)
    assert isinstance(headroom, ProbeResult)
    assert headroom.value == pytest.approx(PRE_CORRELATION**2, abs=0.05)
    assert not headroom.triggered
