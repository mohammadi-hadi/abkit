"""abkit: sample-ratio, peeking, multiple-testing and winner's-curse checks."""

from .audit import run_audit
from .io import dump_design, dump_units, load_design, load_units
from .result import AuditResult, ProbeResult, SkippedProbe
from .schema import Design, Look, Unit

__version__ = "0.1.1"

__all__ = [
    "AuditResult",
    "Design",
    "Look",
    "ProbeResult",
    "SkippedProbe",
    "Unit",
    "__version__",
    "dump_design",
    "dump_units",
    "load_design",
    "load_units",
    "run_audit",
]
