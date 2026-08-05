"""The validity probes.

Each probe returns a :class:`~abkit.result.ProbeResult`, or a
:class:`~abkit.result.SkippedProbe` naming exactly what to log to enable it.
The innocent bands and thresholds below are opinions, stated in one place so
they are easy to disagree with.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .bootstrap import bootstrap_ci
from .result import ProbeResult, SkippedProbe
from .schema import Design, Unit
from .stats import (
    cuped_reduction,
    design_analysis,
    mean,
    normal_ppf,
    schedule_false_positive_rate,
    srm_chi2,
    standardized_mean_difference,
    variance,
    welch,
)

SRM_P_THRESHOLD = 1e-3
"""Standard practice for sample-ratio mismatch: flag below this chi-square p."""

INNOCENT_SMD = (-0.1, 0.1)
"""Standardized mean differences a randomized experiment can plausibly show."""

INNOCENT_NOVELTY = (-0.1, 0.1)
"""Early-minus-late effect gap, in pooled-SD units, compatible with a stable effect."""

FRAGILE_UNITS = 3
"""Flag a significant result that at most this many removed units would overturn."""

PEEK_FPR_FACTOR = 1.5
"""Flag a stop-on-significance schedule whose real false-positive rate exceeds
this multiple of the nominal alpha."""

CURSE_POWER = 0.5
"""Below this power, a significant estimate is more exaggeration than signal."""

FRAGILITY_CAP = 20
"""Stop searching for a flip after removing this many units."""


def _arm_values(units: Sequence[Unit], arm: str, metric: str) -> list[float]:
    return [u.metrics[metric] for u in units if u.arm == arm and metric in u.metrics]


def _arm_pre_values(units: Sequence[Unit], arm: str, key: str) -> list[float]:
    return [u.pre[key] for u in units if u.arm == arm and key in u.pre]


def sample_ratio(units: Sequence[Unit], design: Design) -> ProbeResult:
    """Chi-square test of the observed arm counts against the intended split."""
    counts = {arm: 0 for arm in design.split}
    for unit in units:
        if unit.arm in counts:
            counts[unit.arm] += 1
    stat, p = srm_chi2(counts, design.split)
    total = sum(counts.values())
    shares = ", ".join(f"{arm} {counts[arm] / total:.4f}" for arm in design.split)
    intended = ", ".join(f"{arm} {w:.4f}" for arm, w in design.normalized_split.items())
    return ProbeResult(
        name="sample ratio mismatch",
        value=p,
        unit="p",
        detail=f"observed {shares} vs intended {intended} (chi2 {stat:.2f}); "
        f"flags below p={SRM_P_THRESHOLD:g}",
        n=total,
        flagged=p < SRM_P_THRESHOLD,
    )


def contamination(units: Sequence[Unit]) -> ProbeResult:
    """Units that appear in more than one arm; any at all is an assignment bug."""
    arms_seen: dict[str, set[str]] = {}
    for unit in units:
        arms_seen.setdefault(unit.unit_id, set()).add(unit.arm)
    crossed = sorted(uid for uid, arms in arms_seen.items() if len(arms) > 1)
    example = f"; e.g. {', '.join(crossed[:3])}" if crossed else ""
    return ProbeResult(
        name="assignment contamination",
        value=float(len(crossed)),
        unit="units",
        detail=f"{len(crossed)} unit ids appear in more than one arm{example}",
        n=len(arms_seen),
        flagged=len(crossed) > 0,
    )


def covariate_balance(units: Sequence[Unit], design: Design) -> list[ProbeResult] | SkippedProbe:
    """Standardized mean difference on every pre-experiment covariate."""
    keys = sorted({key for u in units for key in u.pre})
    if not keys:
        return SkippedProbe(
            name="covariate balance",
            reason="no pre-experiment covariates; log them per unit as "
            'pre: {"metric": value} to enable this check',
        )
    results = []
    for key in keys:
        treat = _arm_pre_values(units, design.treatment, key)
        ctrl = _arm_pre_values(units, design.control, key)
        if len(treat) < 2 or len(ctrl) < 2:
            continue
        point, ci = bootstrap_ci(standardized_mean_difference, (treat, ctrl))
        results.append(
            ProbeResult(
                name=f"covariate balance ({key})",
                value=point,
                unit="SMD",
                ci=ci,
                innocent=INNOCENT_SMD,
                detail=f"pre-experiment {key}: treatment minus control in pooled-SD units",
                n=len(treat) + len(ctrl),
            )
        )
    return results


def fragility_path(
    treat: Sequence[float], ctrl: Sequence[float], steps: int = FRAGILITY_CAP
) -> list[tuple[int, float]]:
    """Greedy removal path: (units removed, primary p) at each step.

    At every step the single unit whose removal most weakens the effect — the
    top of the favored arm or the bottom of the other — is dropped.
    """
    t = sorted(treat)
    c = sorted(ctrl)
    path = [(0, welch(t, c)[3])]
    positive = mean(t) - mean(c) > 0
    for k in range(1, steps + 1):
        candidates = []
        if positive:
            if len(t) > 2:
                candidates.append((t[:-1], c))
            if len(c) > 2:
                candidates.append((t, c[1:]))
        else:
            if len(t) > 2:
                candidates.append((t[1:], c))
            if len(c) > 2:
                candidates.append((t, c[:-1]))
        if not candidates:
            break
        t, c = min(candidates, key=lambda tc: abs(welch(tc[0], tc[1])[2]))
        path.append((k, welch(t, c)[3]))
    return path


def _fragility_search(treat: Sequence[float], ctrl: Sequence[float], alpha: float) -> int | None:
    """Smallest number of removed units that lifts the primary p above alpha."""
    for k, p in fragility_path(treat, ctrl)[1:]:
        if p >= alpha:
            return k
    return None


def outlier_fragility(units: Sequence[Unit], design: Design) -> ProbeResult | SkippedProbe:
    """How many extreme units the significance of the primary result rests on."""
    treat = _arm_values(units, design.treatment, design.primary_metric)
    ctrl = _arm_values(units, design.control, design.primary_metric)
    if len(treat) < 3 or len(ctrl) < 3:
        return SkippedProbe(
            name="outlier fragility",
            reason=f"needs per-unit values of {design.primary_metric!r} in both arms",
        )
    _, _, _, p = welch(treat, ctrl)
    if p >= design.alpha:
        return ProbeResult(
            name="outlier fragility",
            value=0.0,
            unit="units",
            detail="primary result is not significant, so there is nothing to overturn",
            n=len(treat) + len(ctrl),
            flagged=False,
        )
    flip = _fragility_search(treat, ctrl, design.alpha)
    if flip is None:
        return ProbeResult(
            name="outlier fragility",
            value=float(FRAGILITY_CAP),
            unit="units",
            detail=f"removing {FRAGILITY_CAP} most extreme units does not overturn significance",
            n=len(treat) + len(ctrl),
            flagged=False,
        )
    return ProbeResult(
        name="outlier fragility",
        value=float(flip),
        unit="units",
        detail=f"removing the {flip} most extreme units lifts the primary p above "
        f"alpha; flags at {FRAGILE_UNITS} or fewer",
        n=len(treat) + len(ctrl),
        flagged=flip <= FRAGILE_UNITS,
    )


def uncorrected_winners(units: Sequence[Unit], design: Design) -> ProbeResult | SkippedProbe:
    """Metrics that are significant raw but not after Benjamini-Hochberg."""
    from .stats import benjamini_hochberg

    metric_names = design.metrics or sorted({m for u in units for m in u.metrics})
    if len(metric_names) < 2:
        return SkippedProbe(
            name="uncorrected winners",
            reason="fewer than two tested metrics; list them in design.metrics "
            "if more were tested than logged",
        )
    tested = []
    pvalues = []
    for name in metric_names:
        treat = _arm_values(units, design.treatment, name)
        ctrl = _arm_values(units, design.control, name)
        if len(treat) < 2 or len(ctrl) < 2:
            continue
        tested.append(name)
        pvalues.append(welch(treat, ctrl)[3])
    if len(tested) < 2:
        return SkippedProbe(
            name="uncorrected winners",
            reason="fewer than two metrics observed in both arms",
        )
    keep = benjamini_hochberg(pvalues, design.alpha)
    lost = [
        name
        for name, p, kept in zip(tested, pvalues, keep, strict=True)
        if p < design.alpha and not kept
    ]
    listing = f": {', '.join(lost)}" if lost else ""
    return ProbeResult(
        name="uncorrected winners",
        value=float(len(lost)),
        unit="metrics",
        detail=f"{len(lost)} of {len(tested)} tested metrics are significant raw "
        f"but not after Benjamini-Hochberg{listing}",
        n=len(tested),
        flagged=len(lost) > 0,
    )


def peeking(design: Design) -> ProbeResult | SkippedProbe:
    """The real false-positive rate of the interim-look schedule actually used."""
    if not design.looks or len(design.looks) < 2:
        return SkippedProbe(
            name="peeking",
            reason="no interim looks recorded; log each analysis as "
            "design.looks = [{n, z}, ...] to enable this check",
        )
    ns = [look.n for look in design.looks]
    fpr = schedule_false_positive_rate(ns, design.alpha)
    z_crit = normal_ppf(1.0 - design.alpha / 2.0)
    final_significant = abs(design.looks[-1].z) >= z_crit
    return ProbeResult(
        name="peeking",
        value=fpr,
        unit="FPR",
        detail=f"stopping at the first significant look across {len(ns)} looks has a "
        f"true false-positive rate of {fpr:.3f} against a nominal alpha of "
        f"{design.alpha:g}; flags when significant and FPR exceeds "
        f"{PEEK_FPR_FACTOR:g}x alpha",
        n=ns[-1],
        flagged=final_significant and fpr > PEEK_FPR_FACTOR * design.alpha,
    )


def _novelty_gap(
    early_t: Sequence[float],
    early_c: Sequence[float],
    late_t: Sequence[float],
    late_c: Sequence[float],
) -> float:
    pooled = list(early_t) + list(early_c) + list(late_t) + list(late_c)
    sd = math.sqrt(variance(pooled))
    if sd == 0.0:
        return math.nan
    gap = (mean(early_t) - mean(early_c)) - (mean(late_t) - mean(late_c))
    return gap / sd


def novelty(units: Sequence[Unit], design: Design) -> ProbeResult | SkippedProbe:
    """Early-half vs late-half effect gap; a stable effect stays near zero."""
    timed = [
        u
        for u in units
        if u.t is not None
        and u.arm in (design.treatment, design.control)
        and design.primary_metric in u.metrics
    ]
    if len(timed) < 8:
        return SkippedProbe(
            name="novelty",
            reason="no assignment times; log t per unit to enable this check",
        )
    timed.sort(key=lambda u: u.t if u.t is not None else 0.0)
    half = len(timed) // 2
    early, late = timed[:half], timed[half:]
    groups = (
        [u.metrics[design.primary_metric] for u in early if u.arm == design.treatment],
        [u.metrics[design.primary_metric] for u in early if u.arm == design.control],
        [u.metrics[design.primary_metric] for u in late if u.arm == design.treatment],
        [u.metrics[design.primary_metric] for u in late if u.arm == design.control],
    )
    if any(len(g) < 2 for g in groups):
        return SkippedProbe(
            name="novelty",
            reason="one half of the experiment lacks units in some arm",
        )
    point, ci = bootstrap_ci(_novelty_gap, groups)
    return ProbeResult(
        name="novelty",
        value=point,
        unit="SD",
        ci=ci,
        innocent=INNOCENT_NOVELTY,
        detail="first-half minus second-half effect on the primary metric, in "
        "pooled-SD units; a nonzero gap means the single reported number "
        "averages over a changing effect",
        n=len(timed),
    )


def winners_curse(units: Sequence[Unit], design: Design) -> ProbeResult | SkippedProbe:
    """Exaggeration ratio of a significant estimate, after Gelman and Carlin."""
    treat = _arm_values(units, design.treatment, design.primary_metric)
    ctrl = _arm_values(units, design.control, design.primary_metric)
    if len(treat) < 2 or len(ctrl) < 2:
        return SkippedProbe(
            name="winner's curse",
            reason=f"needs per-unit values of {design.primary_metric!r} in both arms",
        )
    effect, se, _, p = welch(treat, ctrl)
    if se == 0.0:
        return SkippedProbe(name="winner's curse", reason="zero standard error")
    if design.mde is not None:
        basis, basis_label = design.mde, f"the design MDE of {design.mde:g}"
    elif effect != 0.0:
        basis, basis_label = effect, "the observed effect (an optimistic bound)"
    else:
        return SkippedProbe(
            name="winner's curse",
            reason="observed effect is exactly zero and no design.mde is given",
        )
    power, type_s, exaggeration = design_analysis(basis, se, design.alpha)
    return ProbeResult(
        name="winner's curse",
        value=exaggeration,
        unit="x",
        detail=f"power {power:.2f} at {basis_label}; a significant estimate is "
        f"expected to overstate the true effect by {exaggeration:.1f}x "
        f"(wrong sign with probability {type_s:.3f}); flags when the result "
        f"is significant with power below {CURSE_POWER:g}",
        n=len(treat) + len(ctrl),
        flagged=p < design.alpha and power < CURSE_POWER,
    )


def variance_ratio(units: Sequence[Unit], design: Design) -> ProbeResult | SkippedProbe:
    """Treatment-to-control variance ratio on the primary metric. Descriptive."""
    treat = _arm_values(units, design.treatment, design.primary_metric)
    ctrl = _arm_values(units, design.control, design.primary_metric)
    if len(treat) < 2 or len(ctrl) < 2:
        return SkippedProbe(
            name="variance ratio",
            reason=f"needs per-unit values of {design.primary_metric!r} in both arms",
        )

    def ratio(t: Sequence[float], c: Sequence[float]) -> float:
        vc = variance(c)
        if vc == 0.0:
            return math.nan
        return variance(t) / vc

    point, ci = bootstrap_ci(ratio, (treat, ctrl))
    return ProbeResult(
        name="variance ratio",
        value=point,
        unit="ratio",
        ci=ci,
        detail="treatment variance over control variance on the primary metric; "
        "a shift here means the treatment changes the distribution, not "
        "just the mean (descriptive, never flags)",
        n=len(treat) + len(ctrl),
    )


def cuped_headroom(units: Sequence[Unit], design: Design) -> ProbeResult | SkippedProbe:
    """Variance reduction CUPED would have bought. Descriptive."""
    keys = sorted({key for u in units for key in u.pre})
    if not keys:
        return SkippedProbe(
            name="CUPED headroom",
            reason="no pre-experiment covariates logged",
        )
    best_key, best = "", 0.0
    for key in keys:
        pairs = [
            (u.metrics[design.primary_metric], u.pre[key])
            for u in units
            if design.primary_metric in u.metrics and key in u.pre
        ]
        if len(pairs) < 3:
            continue
        reduction = cuped_reduction([p[0] for p in pairs], [p[1] for p in pairs])
        if reduction > best:
            best_key, best = key, reduction
    if not best_key:
        return SkippedProbe(
            name="CUPED headroom",
            reason="no covariate observed together with the primary metric",
        )
    return ProbeResult(
        name="CUPED headroom",
        value=best,
        unit="share",
        detail=f"CUPED on pre-experiment {best_key!r} would have removed "
        f"{best:.0%} of the primary metric's variance — the confidence "
        "interval could have been that much tighter (descriptive, never flags)",
        n=len(units),
    )
