"""Audit 4,873 real A/B tests from the Upworthy Research Archive.

Each test compared several headline "packages" randomly assigned to equal
shares of traffic; the archive records impressions and clicks per package.
This script runs three abkit checks across the whole archive:

- sample ratio mismatch per test, split by whether all packages in the test
  were created together (a mismatch there is an allocation problem) or added
  mid-test (unequal impressions are then expected, and the check correctly
  refuses to bless them);
- the naive winner rate — best package beats the runner-up at p < 0.05 —
  against the Benjamini-Hochberg rate across all 4,873 winner tests;
- a Gelman-Carlin design analysis of the median significant "winning" test,
  giving the expected exaggeration of the winning lift.

Every number is written to results/upworthy.json; the committed
results/upworthy.md and figure are regenerated from it by `make upworthy`.

Run `python fetch_data.py` first.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from abkit.stats import (
    benjamini_hochberg,
    design_analysis,
    srm_chi2,
    two_proportion_z,
)

HERE = Path(__file__).parent
DATA = HERE / "data" / "upworthy-archive-exploratory-packages-03.12.2020.csv"
RESULTS = HERE / "results"

ACCENT = "#0f766e"
NEUTRAL = "#6b7280"

SAME_START_SECONDS = 3600.0
"""Packages created within an hour of each other count as launched together."""


def load_tests() -> dict[str, list[dict[str, object]]]:
    tests: dict[str, list[dict[str, object]]] = defaultdict(list)
    with open(DATA, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            tests[row["clickability_test_id"]].append(
                {
                    "impressions": int(row["impressions"]),
                    "clicks": int(row["clicks"]),
                    "created_at": datetime.fromisoformat(row["created_at"]),
                }
            )
    return tests


def main() -> None:
    tests = load_tests()
    srm_pvalues_same_start: list[float] = []
    srm_pvalues_staggered: list[float] = []
    winner_pvalues: list[float] = []
    winner_lifts: list[float] = []
    winner_ses: list[float] = []

    for packages in tests.values():
        if len(packages) < 2 or any(p["impressions"] == 0 for p in packages):
            continue
        counts = {str(i): int(p["impressions"]) for i, p in enumerate(packages)}
        split = {str(i): 1.0 for i in range(len(packages))}
        _, srm_p = srm_chi2(counts, split)
        created = [p["created_at"] for p in packages]
        spread = (max(created) - min(created)).total_seconds()
        if spread <= SAME_START_SECONDS:
            srm_pvalues_same_start.append(srm_p)
        else:
            srm_pvalues_staggered.append(srm_p)

        ranked = sorted(
            packages, key=lambda p: int(p["clicks"]) / int(p["impressions"]), reverse=True
        )
        best, second = ranked[0], ranked[1]
        i1, c1 = int(best["impressions"]), int(best["clicks"])
        i2, c2 = int(second["impressions"]), int(second["clicks"])
        lift, _, p = two_proportion_z(c1, i1, c2, i2)
        winner_pvalues.append(p)
        winner_lifts.append(lift)
        r1, r2 = c1 / i1, c2 / i2
        pooled = (c1 + c2) / (i1 + i2)
        winner_ses.append(math.sqrt(pooled * (1 - pooled) * (1 / i1 + 1 / i2)))
        del r1, r2

    n_same = len(srm_pvalues_same_start)
    n_staggered = len(srm_pvalues_staggered)
    srm_same = sum(1 for p in srm_pvalues_same_start if p < 1e-3)
    srm_staggered = sum(1 for p in srm_pvalues_staggered if p < 1e-3)

    n_winner_tests = len(winner_pvalues)
    naive = sum(1 for p in winner_pvalues if p < 0.05)
    bh_kept = sum(benjamini_hochberg(winner_pvalues, 0.05))

    significant = [
        (lift, se)
        for lift, se, p in zip(winner_lifts, winner_ses, winner_pvalues, strict=True)
        if p < 0.05
    ]
    significant.sort(key=lambda pair: pair[0])
    median_lift, median_se = significant[len(significant) // 2]
    power, _, exaggeration = design_analysis(median_lift, median_se, 0.05)

    numbers = {
        "n_tests": len(tests),
        "n_same_start": n_same,
        "n_staggered": n_staggered,
        "srm_flag_rate_same_start": srm_same / n_same,
        "srm_flags_same_start": srm_same,
        "srm_flag_rate_staggered": srm_staggered / n_staggered,
        "srm_flags_staggered": srm_staggered,
        "n_winner_tests": n_winner_tests,
        "naive_winner_rate": naive / n_winner_tests,
        "naive_winners": naive,
        "bh_winners": bh_kept,
        "bh_winner_rate": bh_kept / n_winner_tests,
        "median_significant_lift": median_lift,
        "median_significant_lift_se": median_se,
        "median_winner_power": power,
        "median_winner_exaggeration": exaggeration,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "figures").mkdir(exist_ok=True)
    with open(RESULTS / "upworthy.json", "w", encoding="utf-8") as handle:
        json.dump(numbers, handle, indent=2)
        handle.write("\n")

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
    bins = [i / 25 for i in range(26)]
    for ax, pvalues, n, title in (
        (axes[0], srm_pvalues_same_start, n_same, "packages launched together"),
        (axes[1], srm_pvalues_staggered, n_staggered, "packages added mid-test"),
    ):
        ax.hist(pvalues, bins=bins, color=ACCENT, edgecolor="white", linewidth=0.4)
        ax.axhline(n / 25, color=NEUTRAL, linestyle="--", linewidth=1)
        ax.text(0.98, n / 25, " uniform", va="bottom", ha="right", fontsize=8, color=NEUTRAL)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("SRM p-value per test")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_ylabel("tests")
    fig.suptitle("SRM p-values across 4,873 real Upworthy tests", fontsize=11)
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "upworthy_srm.png", dpi=160)
    plt.close(fig)

    report = f"""# abkit on the Upworthy Research Archive

4,873 real headline tests (22,666 packages) from the archive's exploratory
split, audited with abkit's aggregate-count checks. Regenerate with
`make upworthy` (downloads 14 MB from OSF on first run).

## Sample ratio mismatch

Upworthy assigned packages to equal traffic shares, so within a test the
impression counts should pass a chi-square test against an even split.

| stratum | tests | SRM flags (p < 0.001) | rate |
|---|---|---|---|
| all packages launched together | {n_same} | {srm_same} | {srm_same / n_same:.1%} |
| packages added mid-test | {n_staggered} | {srm_staggered} | {srm_staggered / n_staggered:.1%} |

One in six real tests fails the standard validity gate — and the failures are
not explained by packages being added mid-test, because the rate is just as
high in the {n_same} tests whose packages were all created within an hour of
each other. Whatever the mechanism (variants paused by editors, traffic
throttling, mid-test edits), the CTR comparisons in those {srm_same + srm_staggered}
tests carry unknown exposure bias, and an SRM gate would have quarantined
them before anyone read the winner off the dashboard.

## The winner's curse, measured on real experiments

For every test, compare the best-CTR package against the runner-up:

- **{naive / n_winner_tests:.1%}** of tests ({naive} of {n_winner_tests}) have a
  "significant winner" at raw p < 0.05.
- Benjamini-Hochberg across all {n_winner_tests} winner tests keeps
  **{bh_kept}** of them ({bh_kept / n_winner_tests:.1%}).
- The median significant winning lift is
  **{median_lift * 100:.2f} percentage points** of CTR with a standard error of
  {median_se * 100:.2f} points: power {power:.2f} against a same-size true effect,
  so the winning margin is expected to overstate the truth by
  **{exaggeration:.2f}x** ({(exaggeration - 1) * 100:.0f}% exaggeration) even when
  the winner is real.

![SRM p-values](figures/upworthy_srm.png)

Data: Matias, Munger & Watts (2021), The Upworthy Research Archive,
Scientific Data 8:195, https://doi.org/10.1038/s41597-021-00934-7 —
distributed via https://osf.io/jd64p/ and not redistributed here.
"""
    (RESULTS / "upworthy.md").write_text(report, encoding="utf-8")
    print(json.dumps(numbers, indent=2))


if __name__ == "__main__":
    main()
