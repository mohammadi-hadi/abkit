"""Eight experiments, seven implanted defects, one table.

Each demo experiment implants exactly one failure mode at a severity chosen to
be decisive, then runs the full audit. The table is regenerated from fixed
seeds; CI diffs it against the committed copy.

Two experiments deliberately search over seeds: the peeker keeps trying null
experiments until one stops early at an interim look, and the underpowered
winner keeps trying until a true effect of 0.1 comes out significant. That
selection is not a trick — it is the defect. Peeking and publishing only
winners are selection processes, and the demo reproduces the selection.
"""

from __future__ import annotations

from pathlib import Path

from .audit import run_audit
from .probes import uncorrected_winners
from .report import (
    exaggeration_figure,
    fragility_figure,
    peeking_figure,
    render_report,
)
from .result import AuditResult, SkippedProbe
from .schema import Design, Unit
from .stats import design_analysis, welch
from .synthetic import simulate, simulate_peeking

DEFECTS = {
    "clean": "nothing",
    "traffic-leak": "3% of traffic diverted to treatment",
    "double-dipper": "25 units assigned to both arms",
    "whale-driven": "3 extreme units carry the significance",
    "peeker": "null effect, stopped at the first significant look",
    "fading-novelty": "early-half effect 0.30, late-half effect 0.00",
    "metric-fisher": "null effect, 40 secondary metrics tested",
    "underpowered-winner": "true effect 0.1, powered for 0.14 of that chance",
}


def _confirm(
    units: list[Unit], design: Design, name: str, target: set[str]
) -> tuple[list[Unit], Design] | None:
    audit = run_audit(units, design, name=name)
    if {probe.name for probe in audit.flags} == target:
        return units, design
    return None


def _find_peeker() -> tuple[list[Unit], Design]:
    for seed in range(500):
        units, design = simulate_peeking(n_max=5000, look_every=250, effect=0.0, seed=seed)
        looks = design.looks or []
        if not looks or looks[-1].n < 1500 or looks[-1].n > 3500 or abs(looks[-1].z) < 2.2:
            continue
        found = _confirm(units, design, "peeker", {"peeking"})
        if found:
            return found
    raise RuntimeError("no early-stopping null experiment found in 500 seeds")


def _find_underpowered() -> tuple[list[Unit], Design]:
    for seed in range(500):
        units, design = simulate(n=300, effect=0.1, mde=0.1, seed=seed)
        treat = [u.metrics["outcome"] for u in units if u.arm == "treatment"]
        ctrl = [u.metrics["outcome"] for u in units if u.arm == "control"]
        effect, _, _, p = welch(treat, ctrl)
        if p >= design.alpha or effect <= 0:
            continue
        found = _confirm(units, design, "underpowered-winner", {"winner's curse"})
        if found:
            return found
    raise RuntimeError("no significant underpowered experiment found in 500 seeds")


def _find_metric_fisher() -> tuple[list[Unit], Design]:
    for seed in range(500):
        units, design = simulate(n=2000, effect=0.0, extra_metrics=40, seed=seed)
        probe = uncorrected_winners(units, design)
        if isinstance(probe, SkippedProbe) or not probe.triggered:
            continue
        found = _confirm(units, design, "metric-fisher", {"uncorrected winners"})
        if found:
            return found
    raise RuntimeError("no experiment with uncorrected winners found in 500 seeds")


def build_experiments() -> list[tuple[str, list[Unit], Design]]:
    return [
        ("clean", *simulate(n=8000, effect=0.2, mde=0.2, seed=11)),
        ("traffic-leak", *simulate(n=8000, effect=0.2, srm=0.03, mde=0.2, seed=12)),
        ("double-dipper", *simulate(n=4000, effect=0.2, contaminated=25, mde=0.2, seed=13)),
        (
            "whale-driven",
            *simulate(n=1000, effect=0.12, whales=3, whale_value=15.0, mde=0.2, seed=2),
        ),
        ("peeker", *_find_peeker()),
        ("fading-novelty", *simulate(n=6000, effect=0.15, novelty=0.3, mde=0.15, seed=16)),
        ("metric-fisher", *_find_metric_fisher()),
        ("underpowered-winner", *_find_underpowered()),
    ]


def _cell(audit: AuditResult, probe_name: str, fmt: str) -> str:
    for probe in audit.probes:
        if probe.name == probe_name:
            text = format(probe.value, fmt)
            return f"**{text}**" if probe.triggered else text
    return "-"


def demo_table(audits: list[AuditResult]) -> str:
    lines = [
        "| experiment | implanted defect | SRM p | contam. | fragility "
        "| look FPR | novelty gap | uncorrected | exagg. | flags |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    curse = "winner's curse"
    for audit in audits:
        flags = ", ".join(p.name for p in audit.flags) or "none"
        lines.append(
            f"| {audit.experiment} | {DEFECTS[audit.experiment]} "
            f"| {_cell(audit, 'sample ratio mismatch', '.2g')} "
            f"| {_cell(audit, 'assignment contamination', '.0f')} "
            f"| {_cell(audit, 'outlier fragility', '.0f')} "
            f"| {_cell(audit, 'peeking', '.2f')} "
            f"| {_cell(audit, 'novelty', '.2f')} "
            f"| {_cell(audit, 'uncorrected winners', '.0f')} "
            f"| {_cell(audit, curse, '.1f')} "
            f"| {flags} |"
        )
    return "\n".join(lines)


def run_demo(out_dir: str | Path) -> list[AuditResult]:
    out = Path(out_dir)
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    experiments = build_experiments()
    audits = []
    sections = []
    marks = []
    for name, units, design in experiments:
        audit = run_audit(units, design, name=name)
        audits.append(audit)
        sections.append(render_report(audit).replace("# abkit audit:", "## "))
        if (
            name in ("clean", "whale-driven", "underpowered-winner")
            and audit.summary
            and design.mde is not None
        ):
            se = float(audit.summary["se"])  # type: ignore[arg-type]
            power, _, ratio = design_analysis(design.mde, se, design.alpha)
            if float(audit.summary["p"]) < design.alpha:  # type: ignore[arg-type]
                marks.append((name, power, ratio))
        if name == "peeker" and design.looks:
            peeking_figure(design.looks, design.alpha, figures / "peeking.png")
        if name == "whale-driven":
            treat = [u.metrics["outcome"] for u in units if u.arm == "treatment"]
            ctrl = [u.metrics["outcome"] for u in units if u.arm == "control"]
            fragility_figure(treat, ctrl, design.alpha, figures / "fragility.png")
    exaggeration_figure(marks, 0.05, figures / "exaggeration.png")

    table = demo_table(audits)
    (out / "table.md").write_text(table + "\n", encoding="utf-8")
    header = (
        "# abkit demo\n\n"
        "Eight synthetic experiments, seven implanted defects. Bold values are\n"
        "flags; each lands on the row where its defect was implanted.\n\n"
    )
    (out / "report.md").write_text(header + table + "\n\n" + "\n".join(sections), encoding="utf-8")
    return audits


__all__ = ["build_experiments", "demo_table", "run_demo", "DEFECTS"]
