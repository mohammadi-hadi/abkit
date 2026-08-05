"""Run every applicable probe against one experiment readout."""

from __future__ import annotations

from collections.abc import Sequence

from . import probes
from .result import AuditResult, ProbeResult, SkippedProbe
from .schema import Design, Unit
from .stats import welch


def run_audit(units: Sequence[Unit], design: Design, name: str = "experiment") -> AuditResult:
    result = AuditResult(experiment=name)

    treat = [
        u.metrics[design.primary_metric]
        for u in units
        if u.arm == design.treatment and design.primary_metric in u.metrics
    ]
    ctrl = [
        u.metrics[design.primary_metric]
        for u in units
        if u.arm == design.control and design.primary_metric in u.metrics
    ]
    if len(treat) >= 2 and len(ctrl) >= 2:
        effect, se, z, p = welch(treat, ctrl)
        result.summary = {
            "primary_metric": design.primary_metric,
            "effect": effect,
            "se": se,
            "z": z,
            "p": p,
            "n_treatment": len(treat),
            "n_control": len(ctrl),
            "alpha": design.alpha,
        }

    outcomes: list[ProbeResult | SkippedProbe | list[ProbeResult]] = [
        probes.sample_ratio(units, design),
        probes.contamination(units),
        probes.covariate_balance(units, design),
        probes.outlier_fragility(units, design),
        probes.uncorrected_winners(units, design),
        probes.peeking(design),
        probes.novelty(units, design),
        probes.winners_curse(units, design),
        probes.variance_ratio(units, design),
        probes.cuped_headroom(units, design),
    ]
    for outcome in outcomes:
        if isinstance(outcome, SkippedProbe):
            result.skipped.append(outcome)
        elif isinstance(outcome, list):
            result.probes.extend(outcome)
        else:
            result.probes.append(outcome)
    return result
