import json
import tomllib
from pathlib import Path

import pytest

import abkit
from abkit.cli import main
from abkit.io import dump_design, dump_units
from abkit.synthetic import simulate


def _write_experiment(tmp_path, **dials):
    units, design = simulate(**dials)
    units_path = tmp_path / "units.jsonl"
    design_path = tmp_path / "design.json"
    dump_units(units, units_path)
    dump_design(design, design_path)
    return units_path, design_path


def test_report_command_writes_report_and_json(tmp_path, capsys):
    units_path, design_path = _write_experiment(tmp_path, n=2000, effect=0.2, seed=1)
    out = tmp_path / "audit"
    code = main(["report", str(units_path), "--design", str(design_path), "--out", str(out)])
    assert code == 0
    text = (out / "report.md").read_text()
    assert "sample ratio mismatch" in text
    payload = json.loads((out / "report.json").read_text())
    assert payload["experiment"] == "units"
    assert any(p["name"] == "sample ratio mismatch" for p in payload["probes"])


def test_report_fail_on_flags_exits_nonzero(tmp_path, capsys):
    units_path, design_path = _write_experiment(tmp_path, n=8000, effect=0.2, srm=0.04, seed=2)
    out = tmp_path / "audit"
    code = main(
        [
            "report",
            str(units_path),
            "--design",
            str(design_path),
            "--out",
            str(out),
            "--fail-on-flags",
        ]
    )
    assert code == 2
    assert "FLAG sample ratio mismatch" in capsys.readouterr().out


def test_demo_and_inject_readme(tmp_path, capsys):
    results = tmp_path / "results"
    assert main(["demo", "--out", str(results)]) == 0
    assert (results / "report.md").exists()
    assert (results / "table.md").exists()
    assert (results / "figures" / "peeking.png").exists()
    assert (results / "figures" / "fragility.png").exists()
    assert (results / "figures" / "exaggeration.png").exists()

    readme = tmp_path / "README.md"
    readme.write_text("intro\n<!-- abkit:demo -->\nstale\n<!-- /abkit:demo -->\n")
    assert main(["inject-readme", str(readme), "--results", str(results)]) == 0
    updated = readme.read_text()
    assert "| experiment | implanted defect |" in updated
    assert "stale" not in updated


def test_demo_flags_land_on_the_diagonal(tmp_path):
    """Every implanted defect is flagged on its own row and nowhere else."""
    from abkit.audit import run_audit
    from abkit.demo import build_experiments

    expected = {
        "clean": set(),
        "traffic-leak": {"sample ratio mismatch"},
        "double-dipper": {"assignment contamination"},
        "whale-driven": {"outlier fragility"},
        "peeker": {"peeking"},
        "fading-novelty": {"novelty"},
        "metric-fisher": {"uncorrected winners"},
        "underpowered-winner": {"winner's curse"},
    }
    for name, units, design in build_experiments():
        audit = run_audit(units, design, name=name)
        assert {p.name for p in audit.flags} == expected[name], name


def test_version_flag_prints_the_package_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert abkit.__version__ in capsys.readouterr().out


def test_version_matches_pyproject():
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == abkit.__version__
