"""Read and write experiment data.

Units are one JSON object per line; the design is a single JSON document.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Design, Unit


def load_units(path: str | Path) -> list[Unit]:
    units = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                units.append(Unit.model_validate_json(line))
    return units


def dump_units(units: list[Unit], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for unit in units:
            handle.write(unit.model_dump_json(exclude_defaults=True) + "\n")


def load_design(path: str | Path) -> Design:
    return Design.model_validate_json(Path(path).read_text(encoding="utf-8"))


def dump_design(design: Design, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(design.model_dump(exclude_none=True), indent=2) + "\n",
        encoding="utf-8",
    )
