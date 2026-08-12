#!/usr/bin/env python3
"""
explore_cesdm_model.py
======================

Iterate over a CESDM model (e.g. one imported from a PyPSA nodal network)
and print capacity-by-country, generation mix, renewable potentials,
reservoir inflows, demand, storage, and network summary statistics.

Works on any CESDM hierarchical YAML (for example from ``import_pypsa.py``).

Prerequisites
-------------
    pip install pyyaml numpy

Run
---
    python tools/explore_cesdm_model.py --yaml output/pypsa_cesdm.yaml

Schema default is ``schemas/cesdm`` (relative to the repository root).
Override with ``--schemas`` only when needed.

The functions can also be called individually from a Jupyter notebook after
loading the model with build_model_from_yaml + import_yaml_hierarchical.

─────────────────────────────────────────────────────────────────────────────
Attribute location reference
─────────────────────────────────────────────────────────────────────────────

  Every attribute below lives directly on the asset entity itself,
  tagged `belongsToGroup`.

  GenerationUnit (+ HydroGenerationUnit, WindGenerationUnit,
  SolarGenerationUnit, ThermalGenerationUnit) carries nominal_power_capacity,
  dispatch_type, generator_technology_type, hasAvailabilityProfile, etc.
  directly on the shared base class -- only technology-specific physical/
  design attributes (hub_height, tilt_angle, reactor_type, ...) live on
  the respective subclass.

  StorageUnit (+ HydraulicStorageUnit) carries charging/discharging
  power and efficiencies directly; HydraulicStorageUnit additionally
  carries the reservoir energy/inflow state.

  DemandUnit carries annual_energy_demand, demand_type, etc. directly.

  ElectricalBus                          nominal_voltage, latitude, longitude
                                        → belongsToGeographicalRegion → GeographicalRegion

  atNode                                  single-port topology (Generation/
                                           Storage/DemandUnit/...), belongsToGroup: [topology]
  fromNode / toNode                       two-port topology (TransmissionLine/
                                           HVDCLink/Interconnector/Transformer)

  TransmissionLine/Transformer            thermal_capacity_rating, line_length, …
  Interconnector                          maximum_power_flow_from_to/_to_from
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


_REPO_ROOT = _repo_root()
_DEFAULT_SCHEMAS = _REPO_ROOT / "schemas" / "cesdm"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools"))

from cesdm_toolbox import build_model_from_yaml, CesdmModel  # noqa: E402
from generation_classifier import (  # noqa: E402
    generation_asset_class,
    hydrogen_generation_efficiency,
)


GENERATION_ASSET_CLASSES = [
    "GenerationUnit", "HydroGenerationUnit",
    "WindGenerationUnit", "SolarGenerationUnit", "ThermalGenerationUnit",
]

STORAGE_ASSET_CLASSES = [
    "StorageUnit",
    "HydraulicStorageUnit",
]


# ─────────────────────────────────────────────────────────────────────────────
# Low-level entity accessors
#
# The toolbox stores each entity as an object whose .data dict contains
# attribute values and relation targets, keyed by attribute/relation id.
#
# Attributes are stored as:
#   {"value": 250.0, "unit": "MW"}   ← dict with value + optional unit
#   or plain scalar when no unit is defined
#
# Relations are stored as:
#   "nuts3.ch051"        ← string (single target)
#   ["nuts3.ch051", …]   ← list   (multiple targets)
#
# The three helpers below normalise these into simple Python values.
# ─────────────────────────────────────────────────────────────────────────────

def _av(ent: Any, attr: str, default=None) -> Any:
    """
    Read one attribute value from a toolbox entity object.

    Handles both plain scalar storage and {"value": ..., "unit": ...} dict.
    Returns `default` if the attribute is absent.
    """
    raw = getattr(ent, "data", {}) or {}
    v = raw.get(attr)
    if v is None:
        return default
    if isinstance(v, dict):       # {"value": 380.0, "unit": "kV"}
        return v.get("value", default)
    return v


def _af(ent: Any, attr: str) -> Optional[float]:
    """Read one attribute as float, return None if absent or non-numeric."""
    v = _av(ent, attr)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _target_id(value: Any) -> Optional[str]:
    """Return an entity id from a relation target representation.

    Handles strings, Entity objects, and YAML-style dictionaries.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "id"):
        return str(value.id)
    if isinstance(value, dict):
        if "id" in value:
            return str(value["id"])
        if "target_entity_id" in value:
            return str(value["target_entity_id"])
    return str(value)


_RELATION_ALIASES = {
    "locatedIn": "belongsToGeographicalRegion",
}


def _rels(ent: Any, rel_id: str) -> List[str]:
    """Return all target entity ids for a named relation.

    Accepts legacy relation ids stored in older model dumps (e.g.
    ``locatedIn`` alongside canonical ``belongsToGeographicalRegion``).
    """
    raw = getattr(ent, "data", {}) or {}
    keys = [rel_id]
    canon = _RELATION_ALIASES.get(rel_id)
    if canon:
        keys.append(canon)
    for legacy, c in _RELATION_ALIASES.items():
        if c == rel_id:
            keys.append(legacy)
    for key in keys:
        v = raw.get(key)
        if v is None:
            continue
        if isinstance(v, list):
            return [x for x in (_target_id(t) for t in v) if x]
        x = _target_id(v)
        return [x] if x else []
    return []


def _rel(ent: Any, rel_id: str) -> Optional[str]:
    """Return the first target entity id for a named relation, or None."""
    xs = _rels(ent, rel_id)
    return xs[0] if xs else None


# ─────────────────────────────────────────────────────────────────────────────
# Index builders
#
# These translate the many-to-one structure of a CESDM model into fast lookup
# dicts. Each is built once and reused across statistics functions. Every
# attribute/relation lives directly on the asset's own entity, so these are
# thin, direct lookups by real class name -- no indirection needed.
# ─────────────────────────────────────────────────────────────────────────────

def build_asset_to_node(model: CesdmModel) -> Dict[str, str]:
    """
    Map each asset entity id → connected ElectricalBus id.

    `atNode` lives directly on single-port assets (GenerationUnit,
    StorageUnit, DemandUnit, ExternalSupply, ShuntUnit, ...).
    """
    a2n: Dict[str, str] = {}
    for _cls, entities in model.entities.items():
        for aid, ent in entities.items():
            node = _rel(ent, "atNode")
            if node:
                a2n[aid] = node
    return a2n


def build_node_to_country(model: CesdmModel) -> Dict[str, str]:
    """
    Map each ElectricalBus id → 2-letter ISO country code.

    In library-aligned models the bus carries e.g.:
        belongsToGeographicalRegion → "region.nuts3.DE111"
        or "region.country.DE"
    Legacy PyPSA dumps may still use "nuts3.de111" / "country.de".

    Falls back to parsing the bus entity id  node.<nuts3>.<kv>.
    """
    n2c: Dict[str, str] = {}
    for bus_id, bus_ent in (model.entities.get("ElectricalBus") or {}).items():
        loc = _rel(bus_ent, "belongsToGeographicalRegion")
        country = _country_code_from_region_id(loc) if loc else None
        if country:
            n2c[bus_id] = country
        else:
            parts = bus_id.split(".")
            if len(parts) >= 3 and parts[0] == "node":
                n2c[bus_id] = parts[1][:2].upper()
    return n2c


def _country_code_from_region_id(region_id: str) -> Optional[str]:
    low = region_id.lower()
    if low.startswith("region.country."):
        return region_id.rsplit(".", 1)[-1].upper()
    if low.startswith("country."):
        return region_id.split(".", 1)[1].upper()
    if low.startswith("region.nuts"):
        return region_id.split(".")[-1][:2].upper()
    if low.startswith("nuts"):
        return region_id.split(".", 1)[-1][:2].upper()
    return None


def build_dispatch_index(model: CesdmModel, asset_class: str) -> Dict[str, Any]:
    """Build a reverse map: asset_id → entity, for one asset class."""
    return dict(model.entities.get(asset_class) or {})


def build_multi_dispatch_index(model: CesdmModel, asset_classes: List[str]) -> Dict[str, Tuple[str, Any]]:
    """Build asset_id → (asset_class, entity) across several asset classes,
    using each entity's own real class as the label."""
    index: Dict[str, Tuple[str, Any]] = {}
    for asset_class in asset_classes:
        for aid, ent in (model.entities.get(asset_class) or {}).items():
            index[aid] = (asset_class, ent)
    return index


def iter_entities_by_classes(model: CesdmModel, classes: List[str]):
    """Yield (class_name, entity_id, entity) for all populated classes in order."""
    seen = set()
    for cls in classes:
        for eid, ent in (model.entities.get(cls) or {}).items():
            if eid in seen:
                continue
            seen.add(eid)
            yield cls, eid, ent


def generation_technology_label(asset_cls: str, dv_cls: Optional[str], dv: Any, asset_id: str) -> str:
    """Return a readable generation technology label."""
    tech = _av(dv, "generator_technology_type") if dv is not None else None
    if tech:
        return str(tech)
    if dv_cls:
        return dv_cls
    return asset_cls or asset_id.split(".")[0]


def build_generation_dispatch_index(model: CesdmModel) -> Dict[str, Tuple[str, Any]]:
    """Generation dispatch index over GenerationUnit and HydroGenerationUnit."""
    return build_multi_dispatch_index(model, GENERATION_ASSET_CLASSES)


def build_storage_dispatch_index(model: CesdmModel) -> Dict[str, Tuple[str, Any]]:
    """Storage dispatch index covering both StorageUnit and HydraulicStorageUnit."""
    return build_multi_dispatch_index(model, STORAGE_ASSET_CLASSES)


def build_reservoir_hydro_power_index(model: CesdmModel, a2n: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, float]]:
    """
    Aggregate turbine/pump power from HydroGenerationUnit per reservoir.

    HydraulicStorageUnit only describes the water/energy state. The power
    interfaces are represented by HydroGenerationUnit assets:
        HydroGenerationUnit.drawsFromHydraulicStorage -> HydraulicStorageUnit
        HydroGenerationUnit.nominal_power_capacity / maximum_generation
        HydroGenerationUnit.maximum_pumping_power

    For storage summaries, discharge/charge power for a reservoir is therefore
    derived from connected HydroGenerationUnits, not from the reservoir itself.
    """
    hydro_dv = build_dispatch_index(model, "HydroGenerationUnit")
    result: Dict[str, Dict[str, float]] = defaultdict(lambda: {"power_mw": 0.0, "charge_mw": 0.0})

    unassigned_hydro: List[Tuple[str, float, float]] = []

    for hydro_id, hydro_ent in (model.entities.get("HydroGenerationUnit") or {}).items():
        dv = hydro_dv.get(hydro_id)
        if dv is None:
            continue

        discharge = (
            _af(dv, "nominal_power_capacity")
            or _af(dv, "maximum_generation")
            or _af(dv, "maximum_generation_power")
            or 0.0
        )
        charge = _af(dv, "maximum_pumping_power") or 0.0

        reservoir_ids = _rels(hydro_ent, "drawsFromHydraulicStorage") or _rels(dv, "drawsFromHydraulicStorage")
        if reservoir_ids:
            for reservoir_id in reservoir_ids:
                result[reservoir_id]["power_mw"] += discharge
                result[reservoir_id]["charge_mw"] += charge
        else:
            unassigned_hydro.append((hydro_id, discharge, charge))

    # Aggregated CESDM subsets may contain country/region-level hydro units and
    # reservoirs without explicit drawsFromHydraulicStorage links.  For display only,
    # use a conservative same-node fallback so reservoir duration is not shown
    # as 0 h simply because the aggregation removed the link.
    if a2n and unassigned_hydro:
        reservoirs_by_node: Dict[str, List[str]] = defaultdict(list)
        for res_id in (model.entities.get("HydraulicStorageUnit") or {}).keys():
            node = a2n.get(res_id)
            if node:
                reservoirs_by_node[node].append(res_id)
        for hydro_id, discharge, charge in unassigned_hydro:
            node = a2n.get(hydro_id)
            candidates = reservoirs_by_node.get(node or "", [])
            if len(candidates) == 1:
                result[candidates[0]]["power_mw"] += discharge
                result[candidates[0]]["charge_mw"] += charge

    return dict(result)


def build_pf_index(model: CesdmModel, asset_class: str) -> Dict[str, Any]:
    """
    Build a reverse map: asset_id → entity, for one power-flow-bearing
    asset class (e.g. "TransmissionLine", "Transformer", "GenericInterconnector").
    """
    return dict(model.entities.get(asset_class) or {})


def build_branch_index(model: CesdmModel) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """
    Map each branch asset id → (from_bus_id, to_bus_id).

    `fromNode`/`toNode` live directly on two-port assets
    (TransmissionLine, HVDCLink, Interconnector, Transformer).
    """
    index: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    for _cls, entities in model.entities.items():
        for aid, ent in entities.items():
            frm = _rel(ent, "fromNode")
            to = _rel(ent, "toNode")
            if frm or to:
                index[aid] = (frm, to)
    return index


# ─────────────────────────────────────────────────────────────────────────────
# Statistics functions
# ─────────────────────────────────────────────────────────────────────────────

def model_entity_counts(model: CesdmModel) -> Dict[str, int]:
    """
    Count entities per class — quick overview of model size.

    model.entities is { class_name: { entity_id: entity_object } }.
    """
    return {
        cls: len(entities)
        for cls, entities in model.entities.items()
        if entities
    }


def bus_voltage_distribution(model: CesdmModel) -> Dict[int, int]:
    """
    Count ElectricalBuses by nominal voltage level [kV].

    nominal_voltage is on the ElectricalBus entity itself — it is a
    nameplate property that does not change between modelling contexts.
    """
    dist: Dict[int, int] = defaultdict(int)
    for _bus_id, bus_ent in (model.entities.get("ElectricalBus") or {}).items():
        kv = _af(bus_ent, "nominal_voltage")
        if kv is not None:
            dist[int(round(kv))] += 1
    return dict(sorted(dist.items()))


def generation_capacity_by_country_and_type(
    model: CesdmModel,
    a2n: Dict[str, str],
    n2c: Dict[str, str],
) -> Dict[str, Dict[str, float]]:
    """
    Total nominal_power_capacity [MW] by (country, technology label).

    This function is compatible with the current dispatch-view split:
    GenerationUnit, GenerationUnit, GenerationUnit,
    HydroGenerationUnit, Wind, Solar and Variable views are all considered.
    """
    gen_dv = build_generation_dispatch_index(model)

    result: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for asset_cls, gen_id, _gen_ent in iter_entities_by_classes(model, GENERATION_ASSET_CLASSES):
        dv_cls, dv = gen_dv.get(gen_id, (None, None))
        if dv is None:
            continue

        cap = _af(dv, "nominal_power_capacity")
        if cap is None:
            # Some variable-renewable imports may only store maximum_generation.
            cap = _af(dv, "maximum_generation")
        if cap is None:
            continue

        tech = generation_technology_label(asset_cls, dv_cls, dv, gen_id)
        node = a2n.get(gen_id)
        country = n2c.get(node, "??") if node else "??"
        result[country][tech] += cap

    return {c: dict(techs) for c, techs in result.items()}


def generation_capacity_by_asset_class(
    model: CesdmModel,
    a2n: Dict[str, str],
    n2c: Dict[str, str],
) -> Dict[str, Dict[str, float]]:
    """Total nominal_power_capacity [MW] by country and CESDM asset class."""
    gen_dv = build_generation_dispatch_index(model)
    result: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for asset_cls, gen_id, _gen_ent in iter_entities_by_classes(model, GENERATION_ASSET_CLASSES):
        _dv_cls, dv = gen_dv.get(gen_id, (None, None))
        if dv is None:
            continue
        cap = _af(dv, "nominal_power_capacity") or _af(dv, "maximum_generation")
        if cap is None:
            continue
        node = a2n.get(gen_id)
        country = n2c.get(node, "??") if node else "??"
        result[country][asset_cls] += cap
    return {c: dict(classes) for c, classes in result.items()}



def _generation_category(asset_cls: str, asset_id: str, ent: Any) -> Optional[str]:
    """Classify generation assets for annual renewable-energy reporting."""
    values = [asset_cls, asset_id, _av(ent, "generator_technology_type", ""), _rel(ent, "hasTechnology") or ""]
    label = " ".join(str(v).lower() for v in values if v)
    if "runofriver" in label or "run_of_river" in label or "run-of-river" in label or ".ror" in label or " ror" in label:
        return "run_of_river"
    if "offwind" in label or "offshore" in label:
        return "wind_offshore"
    if "onwind" in label or "onshore" in label or asset_cls == "WindGenerationUnit" or "wind" in label:
        return "wind_onshore"
    if asset_cls == "SolarGenerationUnit" or "solar" in label or "photovoltaic" in label or ".pv" in label or " pv" in label:
        return "solar_pv"
    return None


def annual_renewable_energy_by_country(model: CesdmModel, a2n: Dict[str, str], n2c: Dict[str, str]) -> Dict[str, Dict[str, float]]:
    """Sum wind, PV, run-of-river annual energy and reservoir inflow [MWh/year]."""
    result: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for asset_cls, asset_id, ent in iter_entities_by_classes(model, GENERATION_ASSET_CLASSES):
        category = _generation_category(asset_cls, asset_id, ent)
        if category is None:
            continue
        annual_mwh = _af(ent, "annual_resource_potential")
        if annual_mwh is None:
            continue
        node = a2n.get(asset_id)
        country = n2c.get(node, "??") if node else "??"
        result[country][category] += annual_mwh

    reservoir_to_node: Dict[str, str] = {}
    for hydro_id, hydro_ent in (model.entities.get("HydroGenerationUnit") or {}).items():
        node = a2n.get(hydro_id)
        if not node:
            continue
        for reservoir_id in _rels(hydro_ent, "drawsFromHydraulicStorage"):
            reservoir_to_node.setdefault(reservoir_id, node)

    for reservoir_id, reservoir in (model.entities.get("HydraulicStorageUnit") or {}).items():
        annual_inflow = _af(reservoir, "annual_natural_inflow_energy")
        if annual_inflow is None:
            continue
        node = a2n.get(reservoir_id) or reservoir_to_node.get(reservoir_id)
        country = n2c.get(node, "??") if node else "??"
        result[country]["reservoir_natural_inflow"] += annual_inflow

    return {country: dict(categories) for country, categories in result.items()}

def storage_capacity_by_country(
    model: CesdmModel,
    a2n: Dict[str, str],
    n2c: Dict[str, str],
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Total storage/reservoir capacity by (country, technology/asset class).

    Non-hydro storage (StorageUnit) carries charge/discharge power
    directly. Hydro reservoirs (HydraulicStorageUnit) carry
    energy/SoC only; their discharge and charge power is aggregated from the
    connected HydroGenerationUnit objects via drawsFromHydraulicStorage.
    """
    sto_dv = build_storage_dispatch_index(model)
    reservoir_power = build_reservoir_hydro_power_index(model, a2n)

    result: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"power_mw": 0.0, "charge_mw": 0.0, "energy_mwh": 0.0})
    )

    for sto_cls, sto_id, _sto_ent in iter_entities_by_classes(model, STORAGE_ASSET_CLASSES):
        dv_cls, dv = sto_dv.get(sto_id, (None, None))
        if dv is None:
            continue

        if dv_cls == "HydraulicStorageUnit":
            hydro_power = reservoir_power.get(sto_id, {})
            power = hydro_power.get("power_mw", 0.0)
            charge = hydro_power.get("charge_mw", 0.0)
        else:
            power = _af(dv, "nominal_power_capacity") or _af(dv, "maximum_discharging_power") or 0.0
            charge = _af(dv, "maximum_charging_power") or 0.0

        energy = _af(dv, "energy_storage_capacity")
        tech = str(_av(dv, "storage_technology_type", None) or dv_cls or sto_cls)

        node = a2n.get(sto_id)
        if not node and dv_cls == "HydraulicStorageUnit":
            # HydraulicStorageUnit may not have its own topology port. Use the
            # first connected hydro unit's node as country fallback.
            for hydro_id, hydro_ent in (model.entities.get("HydroGenerationUnit") or {}).items():
                if _rel(hydro_ent, "drawsFromHydraulicStorage") == sto_id:
                    node = a2n.get(hydro_id)
                    if node:
                        break
        country = n2c.get(node, "??") if node else "??"

        result[country][tech]["power_mw"] += (power or 0.0)
        result[country][tech]["charge_mw"] += (charge or 0.0)
        result[country][tech]["energy_mwh"] += (energy or 0.0)

    return {c: dict(techs) for c, techs in result.items()}


def demand_by_country(
    model: CesdmModel,
    a2n: Dict[str, str],
    n2c: Dict[str, str],
) -> Dict[str, float]:
    """
    Total annual_energy_demand [MWh/year] per country.

    Data source
    -----------
    annual_energy_demand → DemandUnit
    """
    dem_dv = build_dispatch_index(model, "DemandUnit")

    result: Dict[str, float] = defaultdict(float)

    for dem_id in (model.entities.get("DemandUnit") or {}):
        dv     = dem_dv.get(dem_id)
        demand = _af(dv, "annual_energy_demand") if dv else None
        if demand is None:
            continue

        node    = a2n.get(dem_id)
        country = n2c.get(node, "??") if node else "??"
        result[country] += demand

    return dict(result)


def _is_phs_hydro(model: CesdmModel, gen_ent: Any) -> bool:
    """True if this HydroGenerationUnit is a reversible pump-turbine (PHS)."""
    if bool(_av(gen_ent, "is_reversible")):
        return True
    kind = str(_av(gen_ent, "hydro_machine_kind") or _av(gen_ent, "machine_role") or "").lower()
    if kind == "reversible":
        return True
    if _av(gen_ent, "maximum_pumping_power") is not None:
        return True
    for res_id in _rels(gen_ent, "drawsFromHydraulicStorage"):
        res = (model.entities.get("HydraulicStorageUnit") or {}).get(res_id)
        if res is None:
            continue
        tech = str(_av(res, "storage_technology_type") or "").lower()
        hastech = str(_rel(res, "hasTechnology") or "").lower()
        if "phs" in tech or "pumped" in tech or "phs" in hastech or "pumped" in hastech:
            return True
    return False


def _country_for_asset(
    model: CesdmModel,
    asset_id: str,
    a2n: Dict[str, str],
    n2c: Dict[str, str],
    *,
    via_hydro_reservoir: bool = False,
) -> str:
    """Resolve ISO country for an asset; reservoirs fall back via paired hydro."""
    node = a2n.get(asset_id)
    if not node and via_hydro_reservoir:
        for hydro_id, hydro_ent in (model.entities.get("HydroGenerationUnit") or {}).items():
            if asset_id in _rels(hydro_ent, "drawsFromHydraulicStorage"):
                node = a2n.get(hydro_id)
                if node:
                    break
    return n2c.get(node, "??") if node else "??"


def _tech_label(ent: Any, *attr_ids: str, fallback: str = "unknown") -> str:
    for aid in attr_ids:
        val = _av(ent, aid)
        if val:
            return str(val)
    tech = _rel(ent, "hasTechnology")
    if tech:
        return str(tech)
    return fallback


def summarize_totals_by_country(
    model: CesdmModel,
    a2n: Dict[str, str],
    n2c: Dict[str, str],
) -> Dict[str, Dict[str, Any]]:
    """Per-country totals aligned with ``aggregate_cesdm_model``'s sanity check.

    Categories (same meaning as ``sanity_check_by_country.txt``):

    - dispatchable / nondispatchable generation capacity by technology [MW]
    - nondispatchable annual_resource_potential by technology [MWh/year]
    - hydro turbine vs. reversible (PHS) discharge/charge [MW]
    - battery StorageUnit energy / discharge / charge by technology
    - reservoir energy capacity and natural inflow
    - demand annual energy
    """
    def _empty() -> Dict[str, Any]:
        return {
            "dispatchable_capacity_mw": defaultdict(float),
            "nondispatchable_capacity_mw": defaultdict(float),
            "nondispatchable_annual_resource_potential_mwh": defaultdict(float),
            "hydro_turbine_discharge_capacity_mw": 0.0,
            "hydro_reversible_discharge_capacity_mw": 0.0,
            "hydro_reversible_charge_capacity_mw": 0.0,
            "storage_energy_capacity_mwh": defaultdict(float),
            "storage_discharge_capacity_mw": defaultdict(float),
            "storage_charge_capacity_mw": defaultdict(float),
            "reservoir_capacity_mwh": 0.0,
            "reservoir_inflow_mwh": 0.0,
            "demand_annual_energy_mwh": 0.0,
        }

    totals: Dict[str, Dict[str, Any]] = defaultdict(_empty)

    for asset_cls, asset_id, ent in iter_entities_by_classes(model, GENERATION_ASSET_CLASSES):
        country = _country_for_asset(model, asset_id, a2n, n2c)
        cap = _af(ent, "nominal_power_capacity") or _af(ent, "maximum_generation") or 0.0
        tech = _tech_label(ent, "generator_technology_type", fallback=asset_cls)
        dispatch_type = str(_av(ent, "dispatch_type") or "").lower()

        if asset_cls == "HydroGenerationUnit":
            if _is_phs_hydro(model, ent):
                totals[country]["hydro_reversible_discharge_capacity_mw"] += cap
                totals[country]["hydro_reversible_charge_capacity_mw"] += (
                    _af(ent, "maximum_pumping_power") or 0.0
                )
            else:
                totals[country]["hydro_turbine_discharge_capacity_mw"] += cap
            if dispatch_type != "dispatchable":
                pot = _af(ent, "annual_resource_potential") or 0.0
                if pot:
                    totals[country]["nondispatchable_annual_resource_potential_mwh"][tech] += pot
            continue

        if dispatch_type == "nondispatchable":
            totals[country]["nondispatchable_capacity_mw"][tech] += cap
            pot = _af(ent, "annual_resource_potential") or 0.0
            if pot:
                totals[country]["nondispatchable_annual_resource_potential_mwh"][tech] += pot
        else:
            totals[country]["dispatchable_capacity_mw"][tech] += cap

    for sto_id, ent in (model.entities.get("StorageUnit") or {}).items():
        country = _country_for_asset(model, sto_id, a2n, n2c)
        tech = _tech_label(ent, "storage_technology_type", fallback="StorageUnit")
        totals[country]["storage_energy_capacity_mwh"][tech] += (
            _af(ent, "energy_storage_capacity") or 0.0
        )
        totals[country]["storage_discharge_capacity_mw"][tech] += (
            _af(ent, "nominal_power_capacity") or _af(ent, "maximum_discharging_power") or 0.0
        )
        totals[country]["storage_charge_capacity_mw"][tech] += (
            _af(ent, "maximum_charging_power") or 0.0
        )

    for res_id, ent in (model.entities.get("HydraulicStorageUnit") or {}).items():
        country = _country_for_asset(
            model, res_id, a2n, n2c, via_hydro_reservoir=True,
        )
        totals[country]["reservoir_capacity_mwh"] += (
            _af(ent, "energy_storage_capacity") or 0.0
        )
        totals[country]["reservoir_inflow_mwh"] += (
            _af(ent, "annual_natural_inflow_energy") or 0.0
        )

    for dem_id, ent in (model.entities.get("DemandUnit") or {}).items():
        country = _country_for_asset(model, dem_id, a2n, n2c)
        totals[country]["demand_annual_energy_mwh"] += (
            _af(ent, "annual_energy_demand") or 0.0
        )

    return {c: dict(t) for c, t in totals.items()}


def transmission_lines_summary(model: CesdmModel) -> Dict[str, Any]:
    """
    Summarise TransmissionLine assets — total circuit km and thermal capacity.

    Data sources
    ------------
    thermal_capacity_rating → TransmissionLine  [MVA]
    line_length             → TransmissionLine  [km]
    parallel_circuit_count  → TransmissionLine

    fromNode/toNode give the from/to bus for counting cross-border lines.
    """
    pf_idx = build_pf_index(model, "TransmissionLine")

    total_km    = 0.0
    total_mva   = 0.0
    line_count  = 0

    for line_id in (model.entities.get("TransmissionLine") or {}):
        pf      = pf_idx.get(line_id)
        length  = _af(pf, "line_length")          if pf else None
        cap     = _af(pf, "thermal_capacity_rating") if pf else None
        n_par   = _af(pf, "parallel_circuit_count")  if pf else 1.0
        n_par   = n_par or 1.0

        line_count += 1
        if length is not None:
            total_km  += length * n_par
        if cap is not None:
            total_mva += cap

    return {
        "count":      line_count,
        "total_km":   total_km,
        "total_mva":  total_mva,
    }


def transformer_summary(model: CesdmModel) -> Dict[str, float]:
    """
    Total installed transformer capacity [MVA].

    Data source: thermal_capacity_rating → Transformer
    """
    pf_idx = build_pf_index(model, "Transformer")
    total_mva   = 0.0
    count = 0
    for trf_id in (model.entities.get("Transformer") or {}):
        pf  = pf_idx.get(trf_id)
        cap = _af(pf, "thermal_capacity_rating") if pf else None
        count += 1
        if cap is not None:
            total_mva += cap
    return {"count": count, "total_mva": total_mva}


def interconnector_flows(
    model: CesdmModel,
    n2c: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    List all interconnectors with flow limits and connected countries.

    Data sources
    ------------
    maximum_power_flow_from_to → Interconnector  [MW]
    maximum_power_flow_to_from → Interconnector  [MW]
    fromNode / toNode         → declared directly on the asset
    """
    pf_idx  = build_pf_index(model, "GenericInterconnector")
    br_idx  = build_branch_index(model)

    rows = []
    for ico_id in (model.entities.get("GenericInterconnector") or {}):
        pf        = pf_idx.get(ico_id)
        frm, to   = br_idx.get(ico_id, (None, None))
        from_c    = n2c.get(frm, "??") if frm else "??"
        to_c      = n2c.get(to,  "??") if to  else "??"

        rows.append({
            "id":       ico_id,
            "from_bus": frm,
            "to_bus":   to,
            "from_country": from_c,
            "to_country":   to_c,
            "p_max_12": _af(pf, "maximum_power_flow_from_to") if pf else None,
            "p_max_21": _af(pf, "maximum_power_flow_to_from") if pf else None,
        })
    return rows


def cross_border_capacity_summary(
    rows: List[Dict[str, Any]]
) -> Dict[Tuple[str, str], Dict[str, float]]:
    """
    Aggregate interconnector capacities by country pair.

    Groups all interconnectors between the same pair of countries
    and sums their flow limits in both directions.

    Returns { (country_A, country_B): {"fwd_mw": float, "bwd_mw": float} }
    where country_A < country_B alphabetically.
    """
    result: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
        lambda: {"fwd_mw": 0.0, "bwd_mw": 0.0}
    )
    for r in rows:
        fc, tc = r["from_country"], r["to_country"]
        if fc == tc:
            continue   # intra-country — skip
        key = (min(fc, tc), max(fc, tc))
        if (r["p_max_12"] or 0) > 0:
            result[key]["fwd_mw"] += r["p_max_12"] or 0.0
        if (r["p_max_21"] or 0) > 0:
            result[key]["bwd_mw"] += r["p_max_21"] or 0.0
    return dict(result)


# ─────────────────────────────────────────────────────────────────────────────
# Printing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sep(title: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {title}")
    print(f"{'─' * 62}")


def print_entity_counts(counts: Dict[str, int]) -> None:
    _sep("Model entity counts")
    for cls in sorted(counts, key=lambda c: -counts[c]):
        print(f"  {cls:<44s}  {counts[cls]:>6,}")


def print_country_totals_summary(totals: Dict[str, Dict[str, Any]]) -> None:
    """Print the sanity-check-style per-country capacity / energy summary."""
    _sep("Per-country totals (sanity-check categories)")
    scalar_keys = [
        ("hydro_turbine_discharge_capacity_mw", "MW"),
        ("hydro_reversible_discharge_capacity_mw", "MW"),
        ("hydro_reversible_charge_capacity_mw", "MW"),
        ("reservoir_capacity_mwh", "MWh"),
        ("reservoir_inflow_mwh", "MWh/year"),
        ("demand_annual_energy_mwh", "MWh/year"),
    ]
    dict_keys = [
        ("dispatchable_capacity_mw", "MW"),
        ("nondispatchable_capacity_mw", "MW"),
        ("nondispatchable_annual_resource_potential_mwh", "MWh/year"),
        ("storage_energy_capacity_mwh", "MWh"),
        ("storage_discharge_capacity_mw", "MW"),
        ("storage_charge_capacity_mw", "MW"),
    ]

    if not totals:
        print("  (no country-attributable assets found)")
        return

    for country in sorted(totals):
        t = totals[country]
        print(f"\n  === {country} ===")
        for key, unit in scalar_keys:
            val = float(t.get(key, 0.0) or 0.0)
            if val == 0.0:
                continue
            print(f"  {key:48s} {val:>14,.2f}  {unit}")
        for key, unit in dict_keys:
            by_tech = t.get(key) or {}
            if not by_tech:
                continue
            print(f"  {key} [{unit}]:")
            for tech in sorted(by_tech, key=lambda k: -float(by_tech[k] or 0.0)):
                val = float(by_tech[tech] or 0.0)
                if val == 0.0:
                    continue
                print(f"    {tech:46s} {val:>14,.2f}")
            subtotal = sum(float(v or 0.0) for v in by_tech.values())
            print(f"    {'(total)':46s} {subtotal:>14,.2f}")


def print_voltage_distribution(dist: Dict[int, int]) -> None:
    _sep("ElectricalBus count by voltage level [kV]")
    for kv, n in sorted(dist.items()):
        bar = "█" * min(n, 50)
        print(f"  {kv:>6} kV   {n:>5,}   {bar}")


def print_generation_capacity(cap: Dict[str, Dict[str, float]]) -> None:
    _sep("Generation capacity by country and technology [MW]")
    grand_total = sum(sum(t.values()) for t in cap.values())
    for country in sorted(cap):
        country_total = sum(cap[country].values())
        share = country_total / grand_total * 100 if grand_total else 0
        print(f"\n  {country}   {country_total:,.0f} MW  ({share:.1f} % of total)")
        for tech in sorted(cap[country], key=lambda t: -cap[country][t]):
            mw  = cap[country][tech]
            bar = "█" * max(1, int(mw / country_total * 28))
            print(f"    {tech:<22s}  {mw:>9,.0f} MW   {bar}")
    print(f"\n  {'GRAND TOTAL':<22s}  {grand_total:>9,.0f} MW")


def print_generation_capacity_by_class(cap: Dict[str, Dict[str, float]]) -> None:
    _sep("Generation capacity by country and CESDM asset class [MW]")
    for country in sorted(cap):
        country_total = sum(cap[country].values())
        print(f"\n  {country}   {country_total:,.0f} MW")
        for cls in sorted(cap[country], key=lambda c: -cap[country][c]):
            mw = cap[country][cls]
            bar = "█" * max(1, int(mw / country_total * 28)) if country_total else ""
            print(f"    {cls:<32s}  {mw:>9,.0f} MW   {bar}")



def print_annual_renewable_energy(energy: Dict[str, Dict[str, float]]) -> None:
    """Print annual renewable potentials and reservoir inflows [TWh/year]."""
    _sep("Annual renewable energy and hydro inflow by country [TWh/year]")
    labels = {
        "wind_onshore": "Wind onshore",
        "wind_offshore": "Wind offshore",
        "solar_pv": "Solar PV",
        "run_of_river": "Run-of-river",
        "reservoir_natural_inflow": "Reservoir natural inflow",
    }
    order = ["wind_onshore", "wind_offshore", "solar_pv", "run_of_river", "reservoir_natural_inflow"]
    totals: Dict[str, float] = defaultdict(float)
    for country in sorted(energy):
        country_total = sum(energy[country].values())
        print(f"\n  {country}   total {country_total / 1e6:,.2f} TWh/year")
        for category in order:
            mwh = energy[country].get(category, 0.0)
            if not mwh:
                continue
            totals[category] += mwh
            print(f"    {labels[category]:<27s}{mwh / 1e6:>10,.2f} TWh/year")
    if energy:
        print("\n  Totals across all countries")
        for category in order:
            mwh = totals.get(category, 0.0)
            if mwh:
                print(f"    {labels[category]:<27s}{mwh / 1e6:>10,.2f} TWh/year")

def print_storage_capacity(sto: Dict[str, Dict[str, Dict[str, float]]]) -> None:
    _sep("Storage capacity by country and technology")
    for country in sorted(sto):
        print(f"\n  {country}")
        for tech in sorted(sto[country]):
            p   = sto[country][tech]["power_mw"]
            pc  = sto[country][tech]["charge_mw"]
            e   = sto[country][tech]["energy_mwh"]
            dur = e / p if p > 0 else 0.0
            print(f"    {tech:<22s}  discharge {p:>8,.0f} MW  "
                  f"charge {pc:>8,.0f} MW  "
                  f"energy {e:>10,.0f} MWh  "
                  f"(≈ {dur:.1f} h)")


def print_demand(dem: Dict[str, float]) -> None:
    _sep("Annual electricity demand by country [TWh/year]")
    total = sum(dem.values())
    for country in sorted(dem, key=lambda c: -dem[c]):
        twh   = dem[country] / 1e6
        share = dem[country] / total * 100 if total else 0
        bar   = "█" * max(1, int(share / 2))
        print(f"  {country}   {twh:>8.1f} TWh  ({share:4.1f} %)  {bar}")
    print(f"  {'TOTAL'}   {total/1e6:>8.1f} TWh")


def print_transmission_summary(
    lines: Dict[str, Any],
    trafos: Dict[str, float],
) -> None:
    _sep("Network infrastructure summary")
    print(f"  TransmissionLine:  {lines['count']:>6,} circuits  "
          f"{lines['total_km']:>9,.0f} circuit-km  "
          f"{lines['total_mva']:>9,.0f} MVA thermal")
    print(f"  Transformer:       {trafos['count']:>6,} units     "
          f"{'':>9}           "
          f"{trafos['total_mva']:>9,.0f} MVA installed")


def print_cross_border_capacity(
    summary: Dict[Tuple[str, str], Dict[str, float]],
    top_n: int = 20,
) -> None:
    _sep(f"Cross-border interconnector capacity (top {top_n}) [MW]")
    rows = sorted(summary.items(), key=lambda kv: -(kv[1]["fwd_mw"] + kv[1]["bwd_mw"]))
    print(f"  {'Border':<8s}   {'→ [MW]':>10}   {'← [MW]':>10}")
    for (ca, cb), v in rows[:top_n]:
        print(f"  {ca}↔{cb}   {v['fwd_mw']:>10,.0f}   {v['bwd_mw']:>10,.0f}")


def print_generation_classifier_smoke_test() -> None:
    """Show the shared classifier outcomes relevant for PyPSA fallback categories."""
    samples = [
        ("CCGT", None),
        ("OCGT", None),
        ("biomass", None),
        ("others_non_renewable", None),
        ("solar_thermal", None),
        ("hydrogen", "CCGT"),
        ("hydrogen", "FuelCell"),
        ("phs", None),
        ("wind", None),
        ("solar", None),
    ]
    _sep("Shared PyPSA generation classifier smoke test")
    for carrier, tech in samples:
        cls = generation_asset_class(carrier, tech)
        eff = hydrogen_generation_efficiency(carrier, tech, 1.0)
        suffix = f", default_eff={eff:g}" if "hydrogen" in str(carrier).lower() else ""
        label = carrier if tech is None else f"{carrier}/{tech}"
        print(f"  {label:<28s} → {cls}{suffix}")


# ─────────────────────────────────────────────────────────────────────────────
# Main exploration routine
# ─────────────────────────────────────────────────────────────────────────────

def explore(model: CesdmModel) -> None:
    """Run all statistics functions and print a full report."""

    # ── Build indexes once ────────────────────────────────────────────────────
    # These are plain dicts built by scanning one entity class each.
    # They make all subsequent lookups O(1) instead of O(n).

    # asset_id → bus_id    (atNode)
    a2n = build_asset_to_node(model)

    # bus_id → "DE" / "CH" / "FR" …   (from ElectricalBus.belongsToGeographicalRegion)
    n2c = build_node_to_country(model)

    # ── Run and print all statistics ──────────────────────────────────────────
    print_entity_counts(model_entity_counts(model))
    print_country_totals_summary(summarize_totals_by_country(model, a2n, n2c))
    print_voltage_distribution(bus_voltage_distribution(model))
    print_generation_capacity(
        generation_capacity_by_country_and_type(model, a2n, n2c)
    )
    print_generation_capacity_by_class(
        generation_capacity_by_asset_class(model, a2n, n2c)
    )
    print_annual_renewable_energy(
        annual_renewable_energy_by_country(model, a2n, n2c)
    )
    print_storage_capacity(storage_capacity_by_country(model, a2n, n2c))
    print_generation_classifier_smoke_test()
    print_demand(demand_by_country(model, a2n, n2c))
    print_transmission_summary(
        transmission_lines_summary(model),
        transformer_summary(model),
    )

    ico_rows = interconnector_flows(model, n2c)
    print_cross_border_capacity(cross_border_capacity_summary(ico_rows))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Explore a CESDM model and print summary statistics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "--schemas",
        default=str(_DEFAULT_SCHEMAS),
        help="Path to the CESDM schemas directory (default: schemas/cesdm).",
    )
    ap.add_argument(
        "--yaml",
        required=True,
        help="Path to the CESDM hierarchical YAML file.",
    )
    args = ap.parse_args()

    schemas_dir = Path(args.schemas).expanduser().resolve()
    yaml_path = Path(args.yaml).expanduser().resolve()

    if not schemas_dir.exists():
        raise SystemExit(f"Schemas directory not found: {schemas_dir}")
    if not yaml_path.exists():
        raise SystemExit(f"YAML file not found: {yaml_path}")

    print(f"Loading schemas from  {schemas_dir}")
    print(f"Loading model from    {yaml_path}")

    # ── Load the model ────────────────────────────────────────────────────────
    # build_model_from_yaml:  reads all schema YAML files, registers entity
    #     classes, attribute definitions, and relation rules.  Returns an
    #     empty CesdmModel (no entities yet).
    model = build_model_from_yaml(str(schemas_dir))

    # import_yaml_hierarchical:  reads the YAML produced by import_pypsa_nc.py
    #     and populates model.entities — a nested dict:
    #     { class_name: { entity_id: entity_object } }
    model.import_yaml_hierarchical(str(yaml_path))

    n_ent = sum(len(e) for e in model.entities.values())
    n_cls = sum(1 for e in model.entities.values() if e)
    print(f"Loaded: {n_ent:,} entities across {n_cls} classes\n")

    explore(model)


if __name__ == "__main__":
    main()
