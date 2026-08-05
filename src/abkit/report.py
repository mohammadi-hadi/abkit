"""Report and figure writers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .probes import fragility_path
from .result import AuditResult
from .schema import Design, Look, Unit
from .stats import design_analysis, normal_ppf

ACCENT = "#0f766e"
ALERT = "#b91c1c"
NEUTRAL = "#6b7280"

_BAND_TEXT = {
    "sample ratio mismatch": "p >= 0.001",
    "assignment contamination": "0 units",
    "outlier fragility": "> 3 units to overturn",
    "uncorrected winners": "0 metrics",
    "peeking": "FPR <= 1.5x alpha",
    "winner's curse": "power >= 0.5",
    "variance ratio": "descriptive",
    "CUPED headroom": "descriptive",
}


def _style(ax: plt.Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.set_axisbelow(True)


def peeking_figure(looks: Sequence[Look], alpha: float, path: Path) -> None:
    """The z statistic at every interim look against the fixed-horizon bound."""
    z_crit = normal_ppf(1.0 - alpha / 2.0)
    ns = [look.n for look in looks]
    zs = [look.z for look in looks]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.axhline(z_crit, color=NEUTRAL, linestyle="--", linewidth=1)
    ax.axhline(-z_crit, color=NEUTRAL, linestyle="--", linewidth=1)
    ax.axhline(0, color="#d1d5db", linewidth=0.8)
    ax.plot(ns, zs, color=ACCENT, linewidth=1.8, marker="o", markersize=4)
    top = max(max(zs), z_crit)
    ax.set_ylim(min(min(zs), -z_crit) - 0.5, top + 0.7)
    crossed = [(n, z) for n, z in zip(ns, zs, strict=True) if abs(z) >= z_crit]
    if crossed:
        n_x, z_x = crossed[0]
        ax.plot([n_x], [z_x], marker="o", markersize=9, color=ALERT, zorder=5)
        ax.annotate(
            f"stopped here, z = {z_x:.2f}",
            (n_x, z_x),
            textcoords="offset points",
            xytext=(-14, -4),
            ha="right",
            va="center",
            fontsize=9,
            color=ALERT,
        )
    ax.text(ns[0], z_crit, f"z = {z_crit:.2f}", va="bottom", ha="left", fontsize=9, color=NEUTRAL)
    ax.set_xlabel("units observed")
    ax.set_ylabel("z statistic")
    ax.set_title("A null experiment, analyzed after every batch", fontsize=11)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fragility_figure(
    treat: Sequence[float], ctrl: Sequence[float], alpha: float, path: Path
) -> None:
    """Primary p-value as the most extreme units are removed one by one."""
    removal = fragility_path(treat, ctrl)
    ks = [k for k, _ in removal]
    ps = [max(p, 1e-6) for _, p in removal]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.axhline(alpha, color=NEUTRAL, linestyle="--", linewidth=1)
    ax.text(
        ks[-1], alpha, f"  alpha = {alpha:g}", va="bottom", ha="right", fontsize=9, color=NEUTRAL
    )
    ax.plot(ks, ps, color=ACCENT, linewidth=1.8, marker="o", markersize=4)
    flipped = [(k, p) for k, p in zip(ks, ps, strict=True) if p >= alpha]
    if flipped:
        k_x, p_x = flipped[0]
        ax.plot([k_x], [p_x], marker="o", markersize=9, color=ALERT, zorder=5)
        noun = "removal" if k_x == 1 else "removals"
        ax.annotate(
            f"significance gone after {k_x} {noun}",
            (k_x, p_x),
            textcoords="offset points",
            xytext=(6, -14),
            fontsize=9,
            color=ALERT,
        )
    ax.set_yscale("log")
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.set_xlabel("most extreme units removed")
    ax.set_ylabel("primary p-value (log scale)")
    ax.set_title("How many units the significant result rests on", fontsize=11)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def exaggeration_figure(
    marks: Sequence[tuple[str, float, float]], alpha: float, path: Path
) -> None:
    """Type-M exaggeration ratio against power, with experiments marked."""
    powers = []
    ratios = []
    mu = 0.6
    while mu <= 6.0:
        power, _, ratio = design_analysis(mu, 1.0, alpha)
        powers.append(power)
        ratios.append(ratio)
        mu += 0.02
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot(powers, ratios, color=ACCENT, linewidth=1.8)
    ax.axhline(1.0, color="#d1d5db", linewidth=0.8)
    ax.set_ylim(0.0, max(ratios) + 0.6)
    stagger = 0
    for label, power, ratio in marks:
        color = ALERT if power < 0.5 else NEUTRAL
        ax.plot([power], [ratio], marker="o", markersize=7, color=color, zorder=5)
        near_right = power > 0.6
        if near_right:
            offset = (-8, 8 if stagger % 2 == 0 else -16)
            stagger += 1
        else:
            offset = (8, 4)
        ax.annotate(
            f"{label} ({ratio:.1f}x)",
            (power, ratio),
            textcoords="offset points",
            xytext=offset,
            ha="right" if near_right else "left",
            fontsize=9,
            color=color,
        )
    ax.set_xlabel("power at the true effect")
    ax.set_ylabel("expected exaggeration of\na significant estimate")
    ax.set_title("The winner's curse is a function of power", fontsize=11)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _format_value(value: float, unit: str) -> str:
    if unit == "p":
        return f"{value:.2g}"
    if unit in ("units", "metrics"):
        return f"{value:.0f}"
    if unit == "share":
        return f"{value:.0%}"
    return f"{value:.2f}"


def render_report(audit: AuditResult) -> str:
    lines = [f"# abkit audit: {audit.experiment}", ""]
    if audit.summary:
        s = audit.summary
        effect = float(s["effect"])  # type: ignore[arg-type]
        se = float(s["se"])  # type: ignore[arg-type]
        lines += [
            "## Primary readout",
            "",
            "| metric | effect | 95% CI | z | p | n (treatment/control) |",
            "|---|---|---|---|---|---|",
            f"| {s['primary_metric']} | {effect:.4f} "
            f"| [{effect - 1.96 * se:.4f}, {effect + 1.96 * se:.4f}] "
            f"| {float(s['z']):.2f} | {float(s['p']):.2g} "  # type: ignore[arg-type]
            f"| {s['n_treatment']}/{s['n_control']} |",
            "",
        ]
    lines += [
        "## Probes",
        "",
        "| probe | value | 95% CI | innocent | flag |",
        "|---|---|---|---|---|",
    ]
    for probe in audit.probes:
        value = _format_value(probe.value, probe.unit)
        if probe.unit and probe.unit not in ("p", "share"):
            value = f"{value} {probe.unit}"
        ci = f"[{probe.ci[0]:.2f}, {probe.ci[1]:.2f}]" if probe.ci else "-"
        if probe.innocent is not None:
            band = f"[{probe.innocent[0]:g}, {probe.innocent[1]:g}]"
        else:
            band = _BAND_TEXT.get(probe.name.split(" (")[0], "-")
        flag = "**FLAG**" if probe.triggered else "-"
        lines.append(f"| {probe.name} | {value} | {ci} | {band} | {flag} |")
    lines.append("")
    lines.append("### Details")
    lines.append("")
    for probe in audit.probes:
        lines.append(f"- **{probe.name}** (n={probe.n}): {probe.detail}")
    if audit.skipped:
        lines += ["", "## Skipped checks", ""]
        for skip in audit.skipped:
            lines.append(f"- **{skip.name}**: {skip.reason}")
    flags = audit.flags
    lines += ["", "## Verdict", ""]
    if flags:
        lines.append(f"{len(flags)} flag(s):")
        lines.append("")
        for probe in flags:
            lines.append(f"- **{probe.name}**: {probe.detail}")
    else:
        lines.append("No probe left its innocent range.")
    lines.append("")
    return "\n".join(lines)


def write_report(
    audit: AuditResult,
    out_dir: str | Path,
    design: Design | None = None,
    units: Sequence[Unit] | None = None,
) -> Path:
    out = Path(out_dir)
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(render_report(audit), encoding="utf-8")
    (out / "report.json").write_text(json.dumps(audit.to_dict(), indent=2) + "\n", encoding="utf-8")
    if design is not None and design.looks and len(design.looks) >= 2:
        peeking_figure(design.looks, design.alpha, figures / "peeking.png")
    if design is not None and units is not None and audit.summary:
        p = float(audit.summary["p"])  # type: ignore[arg-type]
        if p < design.alpha:
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
            fragility_figure(treat, ctrl, design.alpha, figures / "fragility.png")
    return out / "report.md"


def inject_readme(readme_path: str | Path, table: str) -> None:
    """Replace the fenced demo table in a README with the freshly built one."""
    start = "<!-- abkit:demo -->"
    end = "<!-- /abkit:demo -->"
    text = Path(readme_path).read_text(encoding="utf-8")
    if start not in text or end not in text:
        raise ValueError(f"README markers {start} / {end} not found")
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    Path(readme_path).write_text(
        head + start + "\n" + table.rstrip() + "\n" + end + tail, encoding="utf-8"
    )
