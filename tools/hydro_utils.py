"""Shared hydro modelling helpers for CESDM importers and examples.

The functions in this module derive hydro modelling choices from the explicit
CESDM technology identifier used in the ``hasTechnology`` relation.  This keeps
HydroGenerationUnit / HydraulicStorageUnit handling consistent across PyPSA,
TYNDP, FlexECO and examples.
"""
from __future__ import annotations

from typing import Any


def normalize_hydro_technology(technology: Any) -> str:
    """Return a robust lower-case token string for a hydro technology id/label."""
    return str(technology or "").strip().lower().replace("-", "_").replace(".", "_").replace("/", "_")


def is_pumped_storage(technology: Any) -> bool:
    key = normalize_hydro_technology(technology)
    return any(token in key for token in (
        "phs", "pumped", "pumped_storage", "pump_storage", "pumpstorage",
        "pump_hydro", "pumped_hydro", "open_loop", "closed_loop",
    ))


def is_run_of_river(technology: Any) -> bool:
    key = normalize_hydro_technology(technology)
    return "run_of_river" in key or "runofriver" in key or key.endswith("ror") or "_ror" in key


def is_pondage(technology: Any) -> bool:
    return "pondage" in normalize_hydro_technology(technology)


def is_reservoir(technology: Any) -> bool:
    key = normalize_hydro_technology(technology)
    return "reservoir" in key or "dam" in key or is_pondage(key) or is_pumped_storage(key)


def has_reservoir(technology: Any) -> bool:
    """True when the hydro technology should be represented with HydraulicStorageUnit."""
    return is_reservoir(technology) and not is_run_of_river(technology)


def has_natural_inflow(technology: Any) -> bool:
    """True when the reservoir normally has natural inflow.

    Closed-loop PHS is modelled without natural inflow by default. Open-loop PHS
    can have natural inflow, but source data decides whether a profile/value is attached.
    """
    key = normalize_hydro_technology(technology)
    if "closed_loop" in key or "closedloop" in key:
        return False
    return is_run_of_river(key) or "reservoir" in key or "pondage" in key or "open_loop" in key or "openloop" in key


def hydro_storage_kind(technology: Any) -> str:
    """Return one of: run_of_river, pondage, reservoir, phs_open_loop, phs_closed_loop, hydro."""
    key = normalize_hydro_technology(technology)
    if is_run_of_river(key):
        return "run_of_river"
    if "closed_loop" in key or "closedloop" in key:
        return "phs_closed_loop"
    if "open_loop" in key or "openloop" in key:
        return "phs_open_loop"
    if is_pumped_storage(key):
        return "phs_closed_loop"
    if is_pondage(key):
        return "pondage"
    if "reservoir" in key or "dam" in key:
        return "reservoir"
    return "hydro"


def hydro_machine_kind(technology: Any = None, **legacy_hints: Any) -> str:
    """Return HydroGenerationUnit.DispatchView.hydro_machine_kind.

    Preferred input is the CESDM technology identifier from ``hasTechnology``.
    Legacy keyword hints are accepted only for backwards compatibility during
    migrations; technology-based classification always takes precedence.
    """
    key = normalize_hydro_technology(technology)
    if is_pumped_storage(key) or "reversible" in key or "reversible_francis" in key:
        return "reversible"
    if "pump_only" in key or key.endswith("_pump") or key == "pump":
        return "pump"

    # Compatibility fallback for older examples/importers that have not passed
    # a technology id yet. Keep this centralized, not duplicated at call sites.
    if bool(legacy_hints.get("is_reversible")):
        return "reversible"
    try:
        pump = float(legacy_hints.get("maximum_pumping_power") or 0.0)
        gen = float(legacy_hints.get("maximum_generation") or 0.0)
    except Exception:
        pump, gen = 0.0, 0.0
    if pump > 0.0 and gen <= 0.0:
        return "pump"
    if pump > 0.0 and gen > 0.0:
        return "reversible"
    return "turbine"
