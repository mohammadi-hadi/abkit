"""Synthetic experiments with defect dials.

Every failure mode abkit probes for can be implanted here at a chosen
severity, which is how the probes are validated: each must recover its own
dial, stay monotone in it, and stay silent on the clean experiment.
"""

from __future__ import annotations

import math

import numpy as np

from .schema import Design, Look, Unit
from .stats import normal_ppf

PRE_CORRELATION = 0.6
"""Correlation between the pre-experiment covariate and the outcome."""


def simulate(
    n: int = 8000,
    effect: float = 0.2,
    seed: int = 0,
    srm: float = 0.0,
    imbalance: float = 0.0,
    whales: int = 0,
    whale_value: float = 15.0,
    novelty: float = 0.0,
    contaminated: int = 0,
    extra_metrics: int = 0,
    mde: float | None = None,
) -> tuple[list[Unit], Design]:
    """Simulate a two-arm experiment on a unit outcome with SD 1.

    Dials, all zero-off:

    - ``srm``: extra assignment share diverted to treatment (0.03 gives 53/47).
    - ``imbalance``: SMD implanted on the pre-experiment covariate in treatment.
    - ``whales``: units appended to treatment with outcome ``whale_value``.
    - ``novelty``: early-minus-late effect gap in SD units; the effect decays
      linearly from ``effect + novelty`` to ``effect - novelty``, so the
      first-half mean effect exceeds the second-half mean effect by exactly
      ``novelty``.
    - ``contaminated``: unit ids duplicated into the other arm.
    - ``extra_metrics``: independent null secondary metrics per unit.
    """
    rng = np.random.Generator(np.random.PCG64(seed))
    units: list[Unit] = []
    load = math.sqrt(1.0 - PRE_CORRELATION**2)
    for i in range(n):
        in_treatment = rng.random() < 0.5 + srm
        arm = "treatment" if in_treatment else "control"
        pre = float(rng.standard_normal())
        if in_treatment:
            pre += imbalance
        noise = float(rng.standard_normal())
        outcome = PRE_CORRELATION * pre + load * noise
        if in_treatment:
            outcome += effect + novelty * (1.0 - 2.0 * i / n)
        metrics = {"outcome": outcome}
        for j in range(extra_metrics):
            metrics[f"m{j + 1}"] = float(rng.standard_normal())
        units.append(
            Unit(unit_id=f"u{i}", arm=arm, metrics=metrics, pre={"pre_outcome": pre}, t=float(i))
        )
    for w in range(whales):
        units.append(
            Unit(
                unit_id=f"whale{w}",
                arm="treatment",
                metrics={"outcome": whale_value},
                pre={"pre_outcome": float(rng.standard_normal())},
                t=float(rng.integers(0, n)),
            )
        )
    for c, unit in enumerate(units[:contaminated]):
        other = "control" if unit.arm == "treatment" else "treatment"
        units.append(
            Unit(
                unit_id=unit.unit_id,
                arm=other,
                metrics=dict(unit.metrics),
                pre=dict(unit.pre),
                t=float(n + whales + c),
            )
        )
    design = Design(
        split={"control": 0.5, "treatment": 0.5},
        control="control",
        treatment="treatment",
        primary_metric="outcome",
        mde=mde,
    )
    return units, design


def simulate_peeking(
    n_max: int = 5000,
    look_every: int = 250,
    effect: float = 0.0,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[list[Unit], Design]:
    """A sequential experiment stopped at the first significant interim look.

    Returns the units accrued up to the stop together with a design whose
    ``looks`` record every interim analysis performed — exactly what a peeking
    analyst would have shipped.
    """
    rng = np.random.Generator(np.random.PCG64(seed))
    z_crit = normal_ppf(1.0 - alpha / 2.0)
    units: list[Unit] = []
    looks: list[Look] = []
    sum_t = sum_c = sumsq_t = sumsq_c = 0.0
    n_t = n_c = 0
    for i in range(n_max):
        in_treatment = bool(rng.random() < 0.5)
        value = float(rng.standard_normal()) + (effect if in_treatment else 0.0)
        arm = "treatment" if in_treatment else "control"
        units.append(Unit(unit_id=f"u{i}", arm=arm, metrics={"outcome": value}, t=float(i)))
        if in_treatment:
            n_t, sum_t, sumsq_t = n_t + 1, sum_t + value, sumsq_t + value * value
        else:
            n_c, sum_c, sumsq_c = n_c + 1, sum_c + value, sumsq_c + value * value
        if (i + 1) % look_every == 0 and n_t > 1 and n_c > 1:
            mean_t, mean_c = sum_t / n_t, sum_c / n_c
            var_t = (sumsq_t - n_t * mean_t**2) / (n_t - 1)
            var_c = (sumsq_c - n_c * mean_c**2) / (n_c - 1)
            se = math.sqrt(var_t / n_t + var_c / n_c)
            z = (mean_t - mean_c) / se if se > 0 else 0.0
            looks.append(Look(n=i + 1, z=z))
            if abs(z) >= z_crit:
                break
    design = Design(
        split={"control": 0.5, "treatment": 0.5},
        control="control",
        treatment="treatment",
        primary_metric="outcome",
        alpha=alpha,
        planned_n=n_max,
        looks=looks,
    )
    return units, design
