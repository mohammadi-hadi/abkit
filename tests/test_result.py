import json

from abkit.result import AuditResult, ProbeResult, SkippedProbe


def _probe(**overrides):
    base = dict(name="probe", value=0.5, detail="d", n=100)
    base.update(overrides)
    return ProbeResult(**base)


def test_band_probe_triggers_only_when_ci_leaves_the_band():
    inside = _probe(ci=(0.02, 0.08), innocent=(-0.1, 0.1))
    straddling = _probe(ci=(0.05, 0.15), innocent=(-0.1, 0.1))
    outside = _probe(ci=(0.12, 0.20), innocent=(-0.1, 0.1))
    below = _probe(ci=(-0.3, -0.15), innocent=(-0.1, 0.1))
    assert not inside.triggered
    assert not straddling.triggered
    assert outside.triggered
    assert below.triggered


def test_flagged_overrides_band_logic():
    assert _probe(flagged=True).triggered
    assert not _probe(flagged=False, ci=(0.5, 0.9), innocent=(-0.1, 0.1)).triggered


def test_descriptive_probe_never_triggers():
    assert not _probe(ci=(5.0, 9.0)).triggered
    assert not _probe(value=99.0).triggered


def test_missing_ci_on_a_band_probe_does_not_trigger():
    assert not _probe(ci=None, innocent=(-0.1, 0.1), value=3.0).triggered


def test_audit_result_serializes_to_json():
    audit = AuditResult(
        experiment="exp",
        summary={"effect": 0.1, "p": 0.03},
        probes=[_probe(flagged=True), _probe(name="other")],
        skipped=[SkippedProbe(name="novelty", reason="no timestamps")],
    )
    payload = json.loads(json.dumps(audit.to_dict()))
    assert payload["flags"] == ["probe"]
    assert payload["probes"][0]["triggered"] is True
    assert payload["skipped"][0]["reason"] == "no timestamps"
