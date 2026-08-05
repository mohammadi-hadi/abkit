"""Data model for an experiment readout.

The schema accepts the data as it was logged, including the problems an audit
exists to find: duplicated unit ids, units present in several arms, or arms
that never appear in the intended split all pass validation and are reported
by the probes instead of rejected here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Unit(BaseModel):
    """One randomized unit (user, session, cluster) and what it produced."""

    model_config = ConfigDict(extra="forbid")

    unit_id: str
    arm: str
    metrics: dict[str, float] = Field(default_factory=dict)
    pre: dict[str, float] = Field(default_factory=dict)
    t: float | None = None
    """Assignment order or timestamp; any monotone unit works."""


class Look(BaseModel):
    """One interim analysis: cumulative sample size and the z statistic seen."""

    model_config = ConfigDict(extra="forbid")

    n: int = Field(gt=0)
    z: float


class Design(BaseModel):
    """What the experiment intended, against which the data is audited."""

    model_config = ConfigDict(extra="forbid")

    split: dict[str, float]
    control: str
    treatment: str
    primary_metric: str
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0)
    metrics: list[str] | None = None
    """Metrics that were tested; defaults to every metric observed."""
    mde: float | None = None
    """Absolute effect the experiment was designed to detect."""
    planned_n: int | None = None
    looks: list[Look] | None = None
    """Interim analyses actually performed, in order, final look last."""

    @field_validator("split")
    @classmethod
    def _positive_weights(cls, value: dict[str, float]) -> dict[str, float]:
        if len(value) < 2:
            raise ValueError("split needs at least two arms")
        if any(weight <= 0 for weight in value.values()):
            raise ValueError("split weights must be positive")
        return value

    def model_post_init(self, __context: object) -> None:
        for arm in (self.control, self.treatment):
            if arm not in self.split:
                raise ValueError(f"arm {arm!r} is not in the intended split")

    @property
    def normalized_split(self) -> dict[str, float]:
        total = sum(self.split.values())
        return {arm: weight / total for arm, weight in self.split.items()}
