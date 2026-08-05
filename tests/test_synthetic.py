import pytest

from abkit.stats import mean, standardized_mean_difference, welch
from abkit.synthetic import simulate, simulate_peeking


def test_effect_dial_moves_the_primary_metric():
    units, design = simulate(n=20000, effect=0.25, seed=5)
    treat = [u.metrics["outcome"] for u in units if u.arm == "treatment"]
    ctrl = [u.metrics["outcome"] for u in units if u.arm == "control"]
    assert welch(treat, ctrl)[0] == pytest.approx(0.25, abs=0.05)


def test_srm_dial_moves_the_assignment_share():
    units, _ = simulate(n=20000, srm=0.05, seed=6)
    share = sum(1 for u in units if u.arm == "treatment") / len(units)
    assert share == pytest.approx(0.55, abs=0.01)


def test_imbalance_dial_moves_the_pre_covariate():
    units, _ = simulate(n=20000, imbalance=0.4, seed=7)
    treat = [u.pre["pre_outcome"] for u in units if u.arm == "treatment"]
    ctrl = [u.pre["pre_outcome"] for u in units if u.arm == "control"]
    assert standardized_mean_difference(treat, ctrl) == pytest.approx(0.4, abs=0.04)


def test_novelty_dial_creates_the_early_late_gap():
    units, _ = simulate(n=20000, effect=0.2, novelty=0.4, seed=8)
    units.sort(key=lambda u: u.t or 0.0)
    half = len(units) // 2

    def arm_effect(chunk):
        treat = [u.metrics["outcome"] for u in chunk if u.arm == "treatment"]
        ctrl = [u.metrics["outcome"] for u in chunk if u.arm == "control"]
        return mean(treat) - mean(ctrl)

    gap = arm_effect(units[:half]) - arm_effect(units[half:])
    assert gap == pytest.approx(0.4, abs=0.06)


def test_whales_and_contamination_are_implanted_as_declared():
    units, _ = simulate(n=1000, whales=4, whale_value=9.0, contaminated=10, seed=9)
    whales = [u for u in units if u.unit_id.startswith("whale")]
    assert len(whales) == 4
    assert all(u.arm == "treatment" and u.metrics["outcome"] == 9.0 for u in whales)
    by_id: dict[str, set[str]] = {}
    for u in units:
        by_id.setdefault(u.unit_id, set()).add(u.arm)
    assert sum(1 for arms in by_id.values() if len(arms) > 1) == 10


def test_extra_metrics_are_present_and_null():
    units, _ = simulate(n=5000, extra_metrics=3, seed=10)
    treat = [u.metrics["m2"] for u in units if u.arm == "treatment"]
    ctrl = [u.metrics["m2"] for u in units if u.arm == "control"]
    assert abs(welch(treat, ctrl)[0]) < 0.1


def test_peeking_simulation_stops_at_the_first_crossing():
    for seed in range(200):
        units, design = simulate_peeking(n_max=4000, look_every=200, seed=seed)
        looks = design.looks or []
        assert looks, "at least one look is always recorded"
        assert [lk.n for lk in looks] == sorted({lk.n for lk in looks})
        if looks[-1].n < 4000:
            assert abs(looks[-1].z) >= 1.96
            assert all(abs(lk.z) < 1.96 for lk in looks[:-1])
            assert len(units) == looks[-1].n
            return
    raise AssertionError("no early stop in 200 seeds")
