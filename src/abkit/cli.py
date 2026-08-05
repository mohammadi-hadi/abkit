"""Command line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .audit import run_audit
from .demo import run_demo
from .io import load_design, load_units
from .report import inject_readme, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="abkit", description="Audit an A/B-test readout before you ship the decision."
    )
    parser.add_argument("--version", action="version", version=f"abkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    report_cmd = sub.add_parser("report", help="audit a units JSONL against a design JSON")
    report_cmd.add_argument("units", help="JSONL file, one unit per line")
    report_cmd.add_argument("--design", required=True, help="design JSON file")
    report_cmd.add_argument("--out", default="audit", help="output directory")
    report_cmd.add_argument("--name", default=None, help="experiment name in the report")
    report_cmd.add_argument(
        "--fail-on-flags", action="store_true", help="exit 2 if any probe triggers"
    )

    demo_cmd = sub.add_parser("demo", help="rebuild the implanted-defect demo")
    demo_cmd.add_argument("--out", default="results", help="output directory")

    inject_cmd = sub.add_parser(
        "inject-readme", help="refresh the demo table between README markers"
    )
    inject_cmd.add_argument("readme")
    inject_cmd.add_argument("--results", default="results", help="demo output directory")

    args = parser.parse_args(argv)

    if args.command == "report":
        units = load_units(args.units)
        design = load_design(args.design)
        name = args.name or Path(args.units).stem
        audit = run_audit(units, design, name=name)
        report_path = write_report(audit, args.out, design=design, units=units)
        print(f"wrote {report_path}")
        for probe in audit.flags:
            print(f"FLAG {probe.name} -- {probe.detail}")
        if args.fail_on_flags and audit.flags:
            return 2
        return 0

    if args.command == "demo":
        audits = run_demo(args.out)
        flagged = sum(1 for audit in audits if audit.flags)
        print(f"wrote {args.out}/report.md ({flagged}/{len(audits)} experiments flagged)")
        return 0

    if args.command == "inject-readme":
        table = (Path(args.results) / "table.md").read_text(encoding="utf-8")
        inject_readme(args.readme, table)
        print(f"updated {args.readme}")
        return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
