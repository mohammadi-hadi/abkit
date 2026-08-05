"""Probe results and the audit container."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProbeResult:
    """One measured check.

    A probe triggers in one of two ways: band probes carry an ``innocent``
    interval and trigger when the whole 95% CI lies outside it; exact
    procedures (a chi-square threshold, a count that must be zero) set
    ``flagged`` directly and ``innocent`` stays None. Descriptive probes set
    neither and can never trigger.
    """

    name: str
    value: float
    detail: str
    n: int
    unit: str = ""
    ci: tuple[float, float] | None = None
    innocent: tuple[float, float] | None = None
    flagged: bool | None = None

    @property
    def triggered(self) -> bool:
        if self.flagged is not None:
            return self.flagged
        if self.innocent is None or self.ci is None:
            return False
        lo, hi = self.ci
        band_lo, band_hi = self.innocent
        return hi < band_lo or lo > band_hi

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "ci": list(self.ci) if self.ci is not None else None,
            "innocent": list(self.innocent) if self.innocent is not None else None,
            "triggered": self.triggered,
            "detail": self.detail,
            "n": self.n,
        }


@dataclass(frozen=True)
class SkippedProbe:
    """A check that could not run, and exactly what to log to enable it."""

    name: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "skipped": True, "reason": self.reason}


@dataclass
class AuditResult:
    """Everything the audit measured for one experiment readout."""

    experiment: str
    summary: dict[str, float | str | None] = field(default_factory=dict)
    probes: list[ProbeResult] = field(default_factory=list)
    skipped: list[SkippedProbe] = field(default_factory=list)

    @property
    def flags(self) -> list[ProbeResult]:
        return [probe for probe in self.probes if probe.triggered]

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment": self.experiment,
            "summary": self.summary,
            "probes": [probe.to_dict() for probe in self.probes],
            "skipped": [skip.to_dict() for skip in self.skipped],
            "flags": [probe.name for probe in self.flags],
        }
