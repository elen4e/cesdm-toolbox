"""Shared generation classification helpers for CESDM importers.

Importer-side classification (this module) is intentionally narrower than
the full set of schema subclasses: it only distinguishes hydro (kept as
``HydroGenerationUnit`` because of its reservoir and reversible-machine
relations) from everything else, mapping wind/solar/thermal technologies
to the plain ``GenerationUnit`` class rather than the more specific
``WindGenerationUnit``/``SolarGenerationUnit``/``ThermalGenerationUnit``
schema subclasses. Technology itself is represented by ``GeneratorType``
entities via ``hasTechnology``, independently of which entity class was
chosen at import time.
"""
from __future__ import annotations

import math
from typing import Any


def _norm(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
    )


def _key(carrier: Any = None, technology: Any = None) -> str:
    return f"{_norm(carrier)} {_norm(technology)}".strip()


def generation_asset_class(carrier: Any = None, technology: Any = None) -> str:
    """Return the canonical CESDM generation entity class.

    Only true hydro technologies map to ``HydroGenerationUnit``. Hydrogen is
    checked first because the word contains the substring ``hydro``. All other
    technologies map to the flattened ``GenerationUnit`` class.
    """
    slug = _key(carrier, technology).replace(" ", "_")

    # Hydrogen technologies are not hydro assets.
    if "hydrogen" in slug or "h2" in slug:
        return "GenerationUnit"

    hydro_tokens = (
        "run_of_river",
        "runofriver",
        "reservoir",
        "pondage",
        "pumped_storage",
        "pump_storage",
        "pumpedhydro",
        "phs",
    )
    if any(token in slug for token in hydro_tokens):
        return "HydroGenerationUnit"
    if "hydro" in slug:
        return "HydroGenerationUnit"

    return "GenerationUnit"


def hydrogen_generation_efficiency(
    carrier: Any = None,
    technology: Any = None,
    raw_eff: Any = None,
) -> float:
    """Normalize efficiency and provide defaults for hydrogen technologies."""
    key = _key(carrier, technology).replace(" ", "_")
    try:
        efficiency = float(raw_eff)
    except (TypeError, ValueError):
        efficiency = 1.0

    if not math.isfinite(efficiency) or efficiency <= 0.0:
        efficiency = 1.0

    if ("hydrogen" in key or "h2" in key) and abs(efficiency - 1.0) < 1e-12:
        if "fuel_cell" in key or "fuelcell" in key:
            return 0.55
        if "ccgt" in key or "combined_cycle" in key:
            return 0.58

    return efficiency


def classify_generation_unit(*args: Any, **kwargs: Any) -> str:
    """Alias for callers using the newer helper name."""
    return generation_asset_class(*args, **kwargs)


def classify_generator(*args: Any, **kwargs: Any) -> str:
    """Alias for callers using the older generic helper name."""
    return generation_asset_class(*args, **kwargs)


# Hydro helpers live in tools.hydro_utils; re-export for existing import paths.
try:
    from hydro_utils import hydro_machine_kind
except ImportError:  # pragma: no cover - package import path
    from .hydro_utils import hydro_machine_kind  # type: ignore


__all__ = [
    "generation_asset_class",
    "hydrogen_generation_efficiency",
    "hydro_machine_kind",
    "classify_generation_unit",
    "classify_generator",
]
