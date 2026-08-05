import pytest
from pydantic import ValidationError

from abkit.io import dump_design, dump_units, load_design, load_units
from abkit.schema import Design, Unit
from abkit.synthetic import simulate


def _design(**overrides):
    base = dict(
        split={"control": 0.5, "treatment": 0.5},
        control="control",
        treatment="treatment",
        primary_metric="outcome",
    )
    base.update(overrides)
    return Design(**base)


def test_design_rejects_bad_splits():
    with pytest.raises(ValidationError):
        _design(split={"control": 1.0})
    with pytest.raises(ValidationError):
        _design(split={"control": 0.5, "treatment": -0.5})
    with pytest.raises(ValidationError):
        _design(control="holdout")
    with pytest.raises(ValidationError):
        _design(alpha=0.0)


def test_normalized_split_sums_to_one():
    design = _design(split={"control": 2.0, "treatment": 1.0, "variant_b": 1.0})
    normalized = design.normalized_split
    assert sum(normalized.values()) == pytest.approx(1.0)
    assert normalized["control"] == pytest.approx(0.5)


def test_unit_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        Unit(unit_id="u1", arm="control", extra="nope")


def test_dirty_data_is_accepted_not_rejected():
    """Contaminated assignments are the audit's job to find, not the schema's."""
    units = [
        Unit(unit_id="u1", arm="control", metrics={"outcome": 1.0}),
        Unit(unit_id="u1", arm="treatment", metrics={"outcome": 2.0}),
    ]
    assert len(units) == 2


def test_units_and_design_round_trip(tmp_path):
    units, design = simulate(n=50, extra_metrics=1, seed=1)
    units_path = tmp_path / "units.jsonl"
    design_path = tmp_path / "design.json"
    dump_units(units, units_path)
    dump_design(design, design_path)
    assert load_units(units_path) == units
    assert load_design(design_path) == design
