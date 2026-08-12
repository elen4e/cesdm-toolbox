"""
import_pypsa
==============

Convert a PyPSA network stored in NetCDF (*.nc) format to a CESDM V4 model,
plus optional export of time series to an HDF5 file.

V4 schema mapping (V1 → V4)
----------------------------
Entity classes:
  EnergyDomain                  → CarrierDomain
  ElectricityNode               → ElectricalBus
  EnergyConversionTechnology1x1 → GenerationUnit subclass, dispatch
                                  attributes and atNode held directly
                                  on the asset itself (see CHANGELOG.md)
  EnergyStorageTechnology       → StorageUnit subclass, same flattened pattern
  EnergyDemand                  → DemandUnit, same flattened pattern
  TransmissionLine              → TransmissionLine, fromNode/toNode and
                                  power-flow attributes (r, x, b, rating)
                                  held directly on the asset itself
  TwoWindingPowerTransformer    → Transformer, same flattened pattern
                                  (rating, voltages)

Relations:
  hasEnergyCarrier              → hasCarrier
  isInEnergyDomain              → belongsToCarrierDomain
  isInGeographicalRegion        → belongsToGeographicalRegion
  isOutputNodeOf/isConnectedToNode → atNode
  isFromNodeOf                  → fromNode
  isToNodeOf                    → toNode
  hasInputEnergyCarrier         → hasInputCarrier  (on GeneratorType)
  hasOutputEnergyCarrier        → hasOutputCarrier (on GeneratorType)

Profile references:
  demand_profile_reference      → hasDemandProfile   → Profile entity
  resource_potential_profile_reference → hasAvailabilityProfile → Profile entity
  natural_inflow_profile_reference → hasNaturalInflowProfile → Profile entity

HDF5 layout (FlexEco flat-matrix format):
  /series_names   ASCII S64, shape (n_profiles,)
  /values         float64,   shape (n_timesteps, n_profiles)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import sys

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

_REPO_ROOT = _repo_root()
for _path in (_REPO_ROOT, _REPO_ROOT / "tools"):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

import numpy as np
import h5py
import pypsa  # type: ignore

from cesdm_toolbox  import CesdmModel, build_model_from_yaml
from cesdm_carriers import (
    ELECTRICITY_CARRIER_ID, ELECTRICITY_DOMAIN_ID,
    canonical_carrier_id, canonical_domain_id,
    ensure_carrier_entities,
)
from generation_classifier import generation_asset_class, hydrogen_generation_efficiency, hydro_machine_kind



# ---------------------------------------------------------------------------
# Structured asset hierarchy helpers
# ---------------------------------------------------------------------------

def _generation_asset_class(carrier: str | None, technology: str | None) -> str:
    return generation_asset_class(carrier, technology)


def _hydrogen_generation_efficiency(carrier: str | None, technology: str | None, raw_eff) -> float:
    return hydrogen_generation_efficiency(carrier, technology, raw_eff)


def _positive_storage_unit_inflow(network, su_id, weights) -> tuple[bool, float, np.ndarray | None]:
    """Return (has_positive_inflow, annual_inflow, raw_array) for a PyPSA StorageUnit."""
    if (hasattr(network, "storage_units_t") and
            hasattr(network.storage_units_t, "inflow") and
            su_id in network.storage_units_t.inflow.columns):
        inflow = np.asarray(network.storage_units_t.inflow[su_id], dtype=float)
        annual = float((inflow * weights).sum())
        return annual > 0.0, annual, inflow
    return False, 0.0, None


def _positive_store_inflow(network, st_id, weights) -> tuple[bool, float, np.ndarray | None]:
    """Return (has_positive_inflow, annual_inflow, raw_array) for a PyPSA Store."""
    if (hasattr(network, "stores_t") and
            hasattr(network.stores_t, "e_in") and
            st_id in network.stores_t.e_in.columns):
        e_in = np.asarray(network.stores_t.e_in[st_id], dtype=float)
        annual = float((e_in * weights).sum())
        return annual > 0.0, annual, e_in
    return False, 0.0, None

def _storage_asset_class(carrier: str | None, technology: str | None = None) -> str:
    """Map PyPSA carrier/technology to the correct StorageUnit subclass.

    HydraulicStorageUnit: all hydraulic water bodies — reservoir hydro AND PHS.
      PHS distinction is captured on the linked HydroGenerationUnit
      (is_reversible, maximum_pumping_power, pumping_efficiency).
    StorageUnit: batteries, generic storage, fallback.
    """
    key = f"{carrier or ''} {technology or ''}".lower()
    if any(x in key for x in ("reservoir", "pondage", "dam", "hydro",
                               "pump", "phs", "pumped")):
        return "HydraulicStorageUnit"
    return "StorageUnit"





def _is_pumped_hydro_storage(carrier: str | None, technology: str | None = None) -> bool:
    key = f"{carrier or ''} {technology or ''}".lower()
    return any(x in key for x in ["pumpedhydro", "pumped", "pump_storage", "phs"])


def _is_reservoir_hydro_storage(carrier: str | None, technology: str | None = None) -> bool:
    """True for PyPSA storage/store entries that are hydraulic water storage.

    This includes pumped hydro storage (PHS). In CESDM, PHS is not a generic
    battery-like StorageUnit: it is represented as a HydraulicStorageUnit plus a
    linked reversible HydroGenerationUnit carrying turbine/pump parameters.
    """
    key = f"{carrier or ''} {technology or ''}".lower()
    return any(x in key for x in ("reservoir", "pondage", "dam", "hydro",
                                  "pump", "phs", "pumped"))


def _hydro_plant_id(storage_id: str) -> str:
    return f"plant.{storage_id}"


def _hydro_generator_id(storage_id: str) -> str:
    return f"generator.hydro.{storage_id}"



def _ensure_hydro_reservoir_generator_type(model: CesdmModel,
                                            is_reversible: bool = False) -> str:
    """Ensure GeneratorType for hydro/PHS generator exists and return its id.

    is_reversible=True  → PHS type (Generation.Renewable.Hydro.PHS.ClosedLoop)
    is_reversible=False → Reservoir type (Generation.Renewable.Hydro.Reservoir)
    """
    tt_id = ("Generation.Renewable.Hydro.PHS.ClosedLoop"
             if is_reversible else "Generation.Renewable.Hydro.Reservoir")

    gen_cls = model.classes.get("GeneratorType")
    if gen_cls is not None:
        rels = getattr(gen_cls, "relations", None)
        if isinstance(rels, dict):
            rels.setdefault("hasInputCarrier", {"target": ["Carrier"], "required": False})
            rels.setdefault("hasOutputCarrier", {"target": ["Carrier"], "required": False})

    if tt_id not in model.entities.get("GeneratorType", {}):
        model.add_entity(entity_class="GeneratorType", entity_id=tt_id)
        safe_set_attr(model, tt_id, "name", tt_id)
    model.add_relation(tt_id, "hasInputResource", "resource.water")
    model.add_relation(tt_id, "hasOutputCarrier", ELECTRICITY_CARRIER_ID)
    safe_set_attr(model, tt_id, "dispatch_type", "dispatchable")
    safe_set_attr(model, tt_id, "energy_conversion_efficiency", 0.87 if is_reversible else 0.90)
    return tt_id


def _ensure_hydro_reservoir_composite(
    model: CesdmModel,
    reservoir_id: str,
    bus_id: str | None,
    power_capacity: float | None = None,
    resource_potential: float | None = None,
    is_reversible: bool = False,
) -> str:
    """Create HydroGenerationUnit linked to an existing reservoir.

    Covers both reservoir-hydro (is_reversible=False) and PHS (is_reversible=True).
    The reservoir is always a HydraulicStorageUnit. The HydroGenerationUnit uses
    hydro_machine_kind to distinguish a pure turbine from a reversible pump-turbine.
    """
    gen_id   = _hydro_generator_id(reservoir_id)


    if gen_id not in model.entities.get("HydroGenerationUnit", {}):
        model.add_entity(entity_class="HydroGenerationUnit", entity_id=gen_id)
        safe_set_attr(model, gen_id, "name", gen_id)
        if is_reversible:
            safe_set_attr(model, gen_id, "turbine_type", "reversible_francis")
    hydro_tt_id = _ensure_hydro_reservoir_generator_type(model,
                                                          is_reversible=is_reversible)
    model.add_relation(gen_id, "hasTechnology", hydro_tt_id)
    model.add_relation(gen_id, "hasInputResource", "resource.water")
    model.add_relation(gen_id, "hasOutputCarrier", ELECTRICITY_CARRIER_ID)
    model.add_relation(gen_id, "drawsFromHydraulicStorage", reservoir_id)

    if bus_id:
        model.add_relation(gen_id, "atNode", bus_id)

    kind = hydro_machine_kind(hydro_tt_id, is_reversible=is_reversible, maximum_generation=power_capacity)
    hdv_id = gen_id
    safe_set_attr(model, hdv_id, "dispatch_type",             "dispatchable")
    safe_set_attr(model, hdv_id, "hydro_machine_kind",        kind)
    safe_set_attr(model, hdv_id, "nominal_power_capacity",    power_capacity)
    safe_set_attr_if_supported(model, hdv_id, "annual_resource_potential", resource_potential)
    return gen_id

# ---------------------------------------------------------------------------
# Carrier / technology classification maps
# ---------------------------------------------------------------------------

_CARRIER_ALIASES: Dict[str, str] = {
    "AC":          "electricity",
    "electricity": "electricity",
    "Electricity": "electricity",
    "gas":         "gas",
    "Gas":         "gas",
    "heat":        "heat",
    "Heat":        "heat",
    "H2":          "hydrogen",
    "hydrogen":    "hydrogen",
    "water":       "water",
    "Water":       "water",
}

# Carriers / technology keywords that are inherently non-dispatchable
# (availability is set by an external resource, not operator choice).
# Used to classify generators even when no time-varying p_max_pu profile exists.
_NON_DISPATCHABLE_CARRIERS: set[str] = {
    "wind", "onwind", "offwind", "offwind-ac", "offwind-dc",
    "solar", "solar-hsat", "solar_pv", "pv", "solar pv",
    "ror", "run_of_river", "run-of-river",
    "hydro",  # run-of-river hydro; reservoir hydro is StorageUnit not GenerationUnit
}

_TECH_TO_FUEL: Dict[str, str] = {
    "gas":         "gas",
    "gas_cc":      "gas",
    "gas_ct":      "gas",
    "OCGT":        "gas",
    "CCGT":        "gas",
    "coal":        "coal",
    "lignite":     "coal",
    "oil":         "oil",
    "nuclear":     "uranium",
    "wind":        "wind",
    "onwind":      "wind",
    "offwind":     "wind",
    "solar":       "solar",
    "solar_pv":    "solar",
    "pv":          "solar",
    "hydro":       "water",
    "ror":         "water",
    "run_of_river":"water",
    "biomass":     "biomass",
}


# Canonical PyPSA carrier/technology aliases to CESDM default-library GeneratorType ids.
# The mapping deliberately selects a single representative library technology for
# each PyPSA-Eur aggregate carrier. More detailed PyPSA labels can be added here
# without changing the importer logic.
_PYPSA_TO_DEFAULT_GENERATOR_TYPE: Dict[str, str] = {
    "nuclear": "Generation.Nuclear.LWR",
    "uranium": "Generation.Nuclear.LWR",
    "coal": "Generation.Thermal.Coal.HardCoal.New",
    "hard_coal": "Generation.Thermal.Coal.HardCoal.New",
    "lignite": "Generation.Thermal.Coal.Lignite.New",
    "ccgt": "Generation.Thermal.Gas.CCGT.Existing",
    "gas_cc": "Generation.Thermal.Gas.CCGT.Existing",
    "ocgt": "Generation.Thermal.Gas.OCGT.New",
    "gas_ct": "Generation.Thermal.Gas.OCGT.New",
    "gas": "Generation.Thermal.Gas.CCGT.Existing",
    "oil": "Generation.Thermal.Oil.LightOil.Standard",
    "biomass": "Generation.Thermal.Coal.HardCoal.Biofuel",
    "onwind": "Generation.Renewable.Wind.Onshore",
    "wind": "Generation.Renewable.Wind.Onshore",
    "offwind": "Generation.Renewable.Wind.Offshore",
    "offwind_ac": "Generation.Renewable.Wind.Offshore",
    "offwind_dc": "Generation.Renewable.Wind.Offshore",
    "solar": "Generation.Renewable.Solar.PV.Utility",
    "solar_hsat": "Generation.Renewable.Solar.PV.Utility",
    "solar_pv": "Generation.Renewable.Solar.PV.Utility",
    "pv": "Generation.Renewable.Solar.PV.Utility",
    "ror": "Generation.Renewable.Hydro.RunOfRiver",
    "run_of_river": "Generation.Renewable.Hydro.RunOfRiver",
    "hydro": "Generation.Renewable.Hydro.Reservoir",
    "phs": "Generation.Renewable.Hydro.PHS.ClosedLoop",
    "pumped_hydro": "Generation.Renewable.Hydro.PHS.ClosedLoop",
    "h2_fuel_cell": "Generation.Hydrogen.FuelCell",
    "fuel_cell": "Generation.Hydrogen.FuelCell",
    "hydrogen": "Generation.Hydrogen.FuelCell",
}

def _normalise_technology_key(value: str | None) -> str:
    if value is None:
        return ""
    key = str(value).strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return re.sub(r"_+", "_", key).strip("_")

def _default_generator_type_id(carrier: str | None, technology: str | None = None) -> Optional[str]:
    """Map a PyPSA carrier/type label to a canonical default-library GeneratorType."""
    for raw in (technology, carrier):
        key = _normalise_technology_key(raw)
        if not key:
            continue
        if key in _PYPSA_TO_DEFAULT_GENERATOR_TYPE:
            return _PYPSA_TO_DEFAULT_GENERATOR_TYPE[key]
        # PyPSA-Eur uses compound labels such as ``offwind-ac`` and
        # occasionally appends qualifiers. Prefer the most specific aliases.
        for alias in sorted(_PYPSA_TO_DEFAULT_GENERATOR_TYPE, key=len, reverse=True):
            if alias in key:
                return _PYPSA_TO_DEFAULT_GENERATOR_TYPE[alias]
    return None

def _relation_target(model: CesdmModel, entity_id: Optional[str], relation: str) -> Optional[str]:
    if not entity_id:
        return None
    cls_name = _entity_class_name(model, entity_id)
    if not cls_name:
        return None
    ent = model.entities.get(cls_name, {}).get(entity_id)
    raw = getattr(ent, "data", {}).get(relation) if ent is not None else None
    if isinstance(raw, (list, tuple)):
        return str(raw[0]) if raw else None
    return str(raw) if raw else None

# Pre-defined line-type parameters (r, x in Ω/km, b in μS/km)
_LINE_TYPE_PARAMS: Dict[str, Dict[str, float]] = {
    "Al/St 240/40 2-bundle 220.0": {"r": 0.059, "x": 0.300, "b": 3.6},
    "Al/St 240/40 3-bundle 300.0": {"r": 0.040, "x": 0.270, "b": 4.1},
    "Al/St 240/40 4-bundle 380.0": {"r": 0.030, "x": 0.260, "b": 4.2},
}

# ---------------------------------------------------------------------------
# Carrier / technology classification helpers
# ---------------------------------------------------------------------------

def canonicalize_carrier_name(name: str) -> Optional[str]:
    """Return canonical carrier name if name represents a true carrier, else None."""
    if name is None:
        return None
    s = str(name).strip()
    if not s or s.lower() == "nan":
        return None
    return _CARRIER_ALIASES.get(s) or _CARRIER_ALIASES.get(s.lower())

def classify_carrier_or_technology(name: str) -> Tuple[str, str]:
    """Return ('carrier', canonical) or ('technology', original)."""
    canonical = canonicalize_carrier_name(name)
    if canonical is not None:
        return "carrier", canonical
    return "technology", str(name)

def guess_fuel_from_technology(tech_name: str) -> Optional[str]:
    """Best-effort fuel guess from a technology name string."""
    if tech_name is None:
        return None
    canonical = canonicalize_carrier_name(tech_name)
    if canonical is not None:
        return canonical
    return _TECH_TO_FUEL.get(str(tech_name).strip())

def collect_all_carrier_strings(network: pypsa.Network) -> Set[str]:
    """Collect all distinct carrier strings from the network."""
    names: Set[str] = set()
    if hasattr(network, "carriers") and not network.carriers.empty:
        names.update(network.carriers.index.astype(str))
    for df in (getattr(network, comp, None) for comp in
               ("generators", "storage_units", "stores", "loads", "links")):
        if df is not None and not df.empty and "carrier" in df.columns:
            names.update(df.carrier.dropna().astype(str).unique())
    return names

# ---------------------------------------------------------------------------
# Entity id helpers
# ---------------------------------------------------------------------------

def _slugify(s: str) -> str:
    """Convert any string to a lowercase slug safe for use in entity ids."""
    s = str(s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"

def _make_id(prefix: str, name: str) -> str:
    """Sanitize name to a valid entity id (kept for backward compatibility)."""
    return f"{prefix}{_slugify(name)}"

def _node_suffix(bus_to_node: dict, bus_id: str) -> str:
    """
    Return the node id stripped of the 'node.' prefix for use in
    compound asset ids like 'load.itf33.1316' or 'line.fr0.de0.line_42'.
    """
    nid = bus_to_node.get(str(bus_id), f"node.{_slugify(str(bus_id))}")
    return nid[5:] if nid.startswith("node.") else nid

def _profile_id(entity_id: str, role: str) -> str:
    """Construct a Profile entity id from the owning entity id and its role."""
    return f"profile.{role}.{entity_id.lower()}"

# ---------------------------------------------------------------------------
# Safe attribute / relation setters
# ---------------------------------------------------------------------------

def safe_set_attr(model: CesdmModel, entity_id: str, attr: str, value) -> None:
    """Set attribute only if value is not None."""
    if value is None:
        return
    model.add_attribute(entity_id, attr, value)

def safe_add_rel(model: CesdmModel, entity_id: str, rel_name: str,
                 target_id: Optional[str]) -> None:
    """Add relation only if target_id is not empty."""
    if not target_id:
        return
    model.add_relation(entity_id, rel_name, target_id)

def _entity_class_name(model: CesdmModel, entity_id: str) -> Optional[str]:
    """Return the concrete class name for an entity id, if present."""
    for cls_name, entities in getattr(model, "entities", {}).items():
        if entity_id in entities:
            return cls_name
    return None

def _supports_attribute(model: CesdmModel, entity_id: str, attr: str) -> bool:
    """True if the entity's schema declares the attribute."""
    cls_name = _entity_class_name(model, entity_id)
    cdef = getattr(model, "classes", {}).get(cls_name) if cls_name else None
    attrs = getattr(cdef, "attributes", {}) or {}
    return attr in attrs

def _supports_relation(model: CesdmModel, entity_id: str, rel_name: str) -> bool:
    """True if the entity's schema declares the relation."""
    cls_name = _entity_class_name(model, entity_id)
    cdef = getattr(model, "classes", {}).get(cls_name) if cls_name else None
    relations = getattr(cdef, "relations", {}) or {}
    return rel_name in relations

def safe_set_attr_if_supported(model: CesdmModel, entity_id: str, attr: str, value) -> None:
    """Set an attribute only when the asset's own class supports it."""
    if value is None or not _supports_attribute(model, entity_id, attr):
        return
    model.add_attribute(entity_id, attr, value)


def _entity_attribute(model: CesdmModel, entity_id: Optional[str], attr: str, default=None):
    """Read an attribute from an entity without assuming its concrete class.

    Relations in CESDM point to ids, while the model stores entities grouped by
    schema class.  PyPSA import needs this helper to materialise carrier-level
    values (notably energy_carrier_cost) on the concrete asset.
    """
    if not entity_id:
        return default
    cls_name = _entity_class_name(model, str(entity_id))
    if not cls_name:
        return default
    ent = getattr(model, "entities", {}).get(cls_name, {}).get(str(entity_id))
    if ent is None:
        return default
    value = getattr(ent, "data", {}).get(attr, default)
    if isinstance(value, dict) and "value" in value:
        value = value.get("value", default)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else default
        if isinstance(value, dict) and "value" in value:
            value = value.get("value", default)
    return value

def safe_add_rel_if_supported(model: CesdmModel, entity_id: str, rel_name: str,
                              target_id: Optional[str]) -> None:
    """Add a relation when the concrete entity supports it.

    Some schema loader versions expose class relations as objects/lists rather
    than the dict shape used by _supports_relation().  Relying only on that
    pre-check caused supported relations such as Wind/Solar.hasAvailabilityProfile
    to be skipped, which in turn made PyPSA non-dispatchable generators vanish
    from the FlexECO export.  The schema validator remains the source of truth:
    try the relation and ignore only genuine unsupported-relation KeyErrors.
    """
    if not target_id:
        return
    try:
        model.add_relation(entity_id, rel_name, target_id)
    except KeyError:
        return

def _is_non_dispatchable(carrier_str: str | None, tech_str: str | None) -> bool:
    """
    Return True if this generator is non-dispatchable based on its carrier
    or technology string — regardless of whether a time-varying profile exists.

    Wind and solar are always non-dispatchable; thermal and hydro reservoir
    units are always dispatchable.
    """
    for s in (carrier_str, tech_str):
        if s is None:
            continue
        slug = str(s).strip().lower().replace(" ", "_").replace("-", "_")
        if slug in _NON_DISPATCHABLE_CARRIERS:
            return True
        # Partial match for compound names like "offwind-dc", "solar-hsat"
        for kw in ("wind", "solar", "pv", "ror", "run_of_river"):
            if kw in slug:
                return True
    return False

# ---------------------------------------------------------------------------
# Direct EAR entity/attribute/relation mapping helpers
# ---------------------------------------------------------------------------

def _connect_branch(model: CesdmModel, asset_id: str,
                    from_bus: str | None, to_bus: str | None) -> str:
    """Attach a two-terminal asset directly through EAR relations."""
    if from_bus:
        model.add_relation(asset_id, "fromNode", from_bus)
    if to_bus:
        model.add_relation(asset_id, "toNode", to_bus)
    return asset_id

_CARRIER_TO_HYDRO_CATEGORY = {
    "hydro":        "reservoir_hydro",
    "reservoir":    "reservoir_hydro",
    "pondage":      "reservoir_hydro",
    "phs":          "phs_closed_loop",
    "pumped_hydro": "phs_closed_loop",
    "pumped":       "phs_closed_loop",
    "hydro_open":   "phs_open_loop",
    "pump_open":    "phs_open_loop",
}

def _ensure_stor_dispatch(model: CesdmModel, asset_id: str,
                          is_hydro_reservoir: bool = False) -> str:
    return asset_id

def _ensure_dem_dispatch(model: CesdmModel, asset_id: str) -> str:
    return asset_id

def _register_profile(
    model: CesdmModel,
    profiles_values: dict,
    prof_id: str,
    values: np.ndarray,
    profile_type: str,
    profile_unit: str,
    ts_id: str,
) -> None:
    """
    Register a Profile entity in the model and store its numeric array.

    Parameters
    ----------
    model           : CesdmModel
    profiles_values : accumulator {prof_id → np.ndarray} for HDF5 export
    prof_id         : Profile entity id
    values          : float64 array (length = number of snapshots)
    profile_type    : "as_SI" | "as_capacity_factor" | "as_normalized_annual_energy"
    profile_unit    : SI unit string or "pu"
    ts_id           : TimestampSeries entity id
    """
    if prof_id not in model.entities.get("Profile", {}):
        model.add_entity(entity_class="Profile", entity_id=prof_id)
        model.add_attribute(prof_id, "profile_type",   profile_type)
        model.add_attribute(prof_id, "profile_unit",   profile_unit)
        model.add_attribute(prof_id, "data_reference", f"/profiles/{prof_id}")
        model.add_relation(prof_id,  "hasTimestampSeries", ts_id)
    profiles_values[prof_id] = np.asarray(values, dtype=np.float64)

# ---------------------------------------------------------------------------
# Snapshot weights
# ---------------------------------------------------------------------------

def _snapshot_weights(network: pypsa.Network) -> np.ndarray:
    n_ts = len(network.snapshots)
    if hasattr(network, "snapshot_weightings"):
        sw = network.snapshot_weightings
        for field in ("generators", "objective"):
            if hasattr(sw, field):
                arr = np.asarray(getattr(sw, field), dtype=float)
                if arr.size == n_ts:
                    return arr
    return np.ones(n_ts, dtype=float)

# ---------------------------------------------------------------------------
# HDF5 time series export (FlexEco flat-matrix format)
# ---------------------------------------------------------------------------

def save_timeseries_to_hdf5(
    filename: str,
    timestamps,
    data_dict: Dict[str, np.ndarray],
) -> None:
    """
    Save time series to HDF5 in the FlexEco flat-matrix layout.

    Layout
    ------
    /series_names   ASCII S64, shape (n_profiles,)
    /values         float64,   shape (n_timesteps, n_profiles)

    Parameters
    ----------
    filename  : output .h5 path (parent directories created if absent)
    timestamps: iterable of snapshot labels (used only for length check)
    data_dict : { series_name → 1D np.ndarray of length n_timesteps }
    """
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    series_names = list(data_dict.keys())
    if not series_names:
        return

    n_timesteps = len(timestamps) if timestamps is not None else len(
        next(iter(data_dict.values()))
    )
    cols = []
    for name in series_names:
        arr = np.asarray(data_dict[name], dtype=np.float64).ravel()
        if len(arr) != n_timesteps:
            col = np.zeros(n_timesteps, dtype=np.float64)
            col[:min(len(arr), n_timesteps)] = arr[:n_timesteps]
            cols.append(col)
        else:
            cols.append(arr)

    data_matrix = np.column_stack(cols).astype(np.float64)  # (n_ts, n_profiles)

    with h5py.File(filename, "w") as f:
        f.create_dataset("series_names",
                         data=np.array(series_names, dtype="S64"))
        f.create_dataset("values", data=data_matrix, dtype=np.float64)

def collect_timeseries_from_pypsa(
    network: pypsa.Network,
) -> Tuple[List, Dict[str, np.ndarray]]:
    """
    Extract time series from a PyPSA network.

    Returns
    -------
    timestamps : list of snapshot labels
    data_dict  : { series_name → 1D array }
        Series names use the V4 Profile entity id convention:
          profile.demand.<LOAD_eid>       — normalised, NEGATIVE (withdrawal)
          profile.availability.<GEN_eid>  — capacity factor [0,1], positive
          profile.inflow.<STORU_eid>      — normalised annual, positive
          profile.inflow.<STORS_eid>      — normalised annual, positive
    """
    timestamps = list(network.snapshots)
    n_ts = len(timestamps)
    data_dict: Dict[str, np.ndarray] = {}

    def _get(df, col, default=0.0):
        if df is None or col not in getattr(df, "columns", []):
            return np.full(n_ts, default, dtype=float)
        try:
            return np.asarray(df[col], dtype=float)
        except Exception:
            return np.full(n_ts, default, dtype=float)

    # Loads → demand profiles (negated: withdrawal = negative injection)
    if hasattr(network, "loads_t") and hasattr(network.loads_t, "p_set"):
        for load_id in network.loads.index:
            l_bus   = str(network.loads.at[load_id, "bus"]) if "bus" in network.loads.columns else str(load_id)
            l_sfx   = bus_to_node.get(l_bus, f"node.{_slugify(l_bus)}")[5:]
            prof_id = f"profile.demand.{l_sfx}"
            data_dict[prof_id] = -_get(network.loads_t.p_set, load_id, 0.0)

    # Generators → availability profiles
    if hasattr(network, "generators_t") and hasattr(network.generators_t, "p_max_pu"):
        for gen_id in network.generators.index:
            g_bus    = str(network.generators.at[gen_id, "bus"]) if "bus" in network.generators.columns else str(gen_id)
            g_sfx    = bus_to_node.get(g_bus, f"node.{_slugify(g_bus)}")[5:]
            g_carrier= _slugify(str(network.generators.at[gen_id, "carrier"]) if "carrier" in network.generators.columns else "gen")
            prof_id  = f"profile.{g_carrier}.{g_sfx}"
            data_dict[prof_id] = _get(network.generators_t.p_max_pu, gen_id, 1.0)

    # Storage units → inflow profiles
    if hasattr(network, "storage_units_t") and hasattr(network.storage_units_t, "inflow"):
        for su_id in network.storage_units.index:
            su_bus  = str(network.storage_units.at[su_id, "bus"]) if "bus" in network.storage_units.columns else str(su_id)
            su_car  = _slugify(str(network.storage_units.at[su_id, "carrier"]) if "carrier" in network.storage_units.columns else "storage")
            su_sfx  = bus_to_node.get(su_bus, f"node.{_slugify(su_bus)}")[5:]
            prof_id = f"profile.inflow.{su_car}.{su_sfx}"
            data_dict[prof_id] = _get(network.storage_units_t.inflow, su_id, 0.0)

    # Stores → inflow profiles
    if hasattr(network, "stores_t") and hasattr(network.stores_t, "e_in"):
        for st_id in network.stores.index:
            st_bus  = str(network.stores.at[st_id, "bus"]) if "bus" in network.stores.columns else str(st_id)
            st_car  = _slugify(str(network.stores.at[st_id, "carrier"]) if "carrier" in network.stores.columns else "store")
            st_sfx  = bus_to_node.get(st_bus, f"node.{_slugify(st_bus)}")[5:]
            prof_id = f"profile.inflow.{st_car}.{st_sfx}"
            data_dict[prof_id] = _get(network.stores_t.e_in, st_id, 0.0)

    # Links with time-varying p_max_pu → availability profiles
    # (e.g. HVDC links with varying capacity, or demand-response links)
    if (hasattr(network, "links_t") and
            hasattr(network.links_t, "p_max_pu") and
            not network.links_t.p_max_pu.empty):
        for link_id in network.links_t.p_max_pu.columns:
            lk_bus  = str(network.links.at[link_id, "bus0"]) if (hasattr(network, "links") and "bus0" in network.links.columns and link_id in network.links.index) else str(link_id)
            lk_sfx  = bus_to_node.get(lk_bus, f"node.{_slugify(lk_bus)}")[5:]
            prof_id = f"profile.availability.link.{lk_sfx}"
            data_dict[prof_id] = _get(network.links_t.p_max_pu, link_id, 1.0)

    return timestamps, data_dict

# ---------------------------------------------------------------------------
# NUTS3 location helpers (used when nuts_shapefile is provided)
# ---------------------------------------------------------------------------

_NUTS_COUNTRY_REMAP: Dict[str, str] = {
    "EL": "GR",   # Greece: NUTS uses EL, ISO uses GR
    "UK": "GB",   # United Kingdom: NUTS uses UK, ISO uses GB
}

def _country_region_id(ccode: str) -> str:
    """Map an ISO/NUTS country code to ``region.country.XX``."""
    cc = (ccode or "").strip().upper()
    if cc.startswith("REGION.COUNTRY."):
        cc = cc.rsplit(".", 1)[-1]
    cc = _NUTS_COUNTRY_REMAP.get(cc, cc)
    return f"region.country.{cc}"


def _nuts_region_id(level: str, code: str) -> str:
    """Map a NUTS code to ``region.nuts{1,2,3}.CODE`` (regions_library)."""
    return f"region.{level}.{str(code).strip().upper()}"


def _ensure_geo_region(model: "CesdmModel", region_id: str, name: Optional[str] = None) -> str:
    """Use existing GeographicalRegion (e.g. from regions_library) or create fallback."""
    if region_id not in (model.entities.get("GeographicalRegion") or {}):
        model.add_entity(entity_class="GeographicalRegion", entity_id=region_id)
        if name:
            safe_set_attr(model, region_id, "name", name)
    return region_id

def _nuts_to_iso(nuts_code: str) -> str:
    """Remap NUTS country prefix to ISO 3166-1 alpha-2."""
    prefix = nuts_code[:2]
    return _NUTS_COUNTRY_REMAP.get(prefix, prefix) + nuts_code[2:]

def _lookup_nuts3(
    nuts3_gdf,
    lon: float,
    lat: float,
    max_nearest_km: float = 10.0,
) -> Optional[Dict[str, str]]:
    """
    Spatially look up the NUTS3 region containing (lon, lat).

    Returns a dict with keys 'country', 'nuts2', 'nuts3', 'name',
    or None if no region is found within max_nearest_km.
    """
    import numpy as _np
    try:
        from shapely.geometry import Point as _Point
    except ImportError:
        return None

    point = _Point(lon, lat)

    # Fast spatial index query
    nuts_col = next(
        (c for c in ("NUTS_ID", "NUTS_CODE", "NUTS") if c in nuts3_gdf.columns),
        None)
    name_col = next(
        (c for c in ("NAME_LATN", "NUTS_NAME", "NAME_ENGL", "NAME")
         if c in nuts3_gdf.columns), None)
    if nuts_col is None:
        return None

    cand_idx = list(nuts3_gdf.sindex.intersection(point.bounds))
    candidates = nuts3_gdf.iloc[cand_idx] if cand_idx else nuts3_gdf

    hit = candidates[candidates.geometry.contains(point)]
    if hit.empty:
        hit = candidates[candidates.geometry.intersects(point.buffer(0.02))]

    if hit.empty:
        # Nearest-neighbour fallback within max_nearest_km
        try:
            nuts_m = nuts3_gdf.to_crs(3857)
            import geopandas as _gpd
            pt_m   = _gpd.GeoSeries([point], crs=4326).to_crs(3857).iloc[0]
            radius = max_nearest_km * 1000.0
            bb     = pt_m.buffer(radius).bounds
            cands  = list(nuts_m.sindex.intersection(bb))
            if not cands:
                return None
            dists  = nuts_m.iloc[cands].geometry.distance(pt_m)
            nearest = dists.idxmin()
            if float(dists.loc[nearest]) / 1000.0 > max_nearest_km:
                return None
            row = nuts3_gdf.loc[nearest]
        except Exception:
            return None
    else:
        row = hit.iloc[0]

    nuts3_code = str(row[nuts_col])
    nuts2_code = nuts3_code[:4]
    iso3 = _nuts_to_iso(nuts3_code)
    iso2 = _nuts_to_iso(nuts2_code)

    name = None
    if name_col and name_col in row.index:
        v = row[name_col]
        name = str(v.iloc[0] if hasattr(v, "iloc") else v)

    return {
        "country": iso3[:2].lower(),
        "nuts2":   iso2.lower(),
        "nuts3":   iso3.lower(),
        "name":    name,
    }

# ---------------------------------------------------------------------------
# Carrier / domain entity creation
# ---------------------------------------------------------------------------

def build_carrier_domain_entities(
    network: pypsa.Network,
    model: CesdmModel,
    *,
    year: int | None = None,
) -> Tuple[Dict[str, str], Dict[str, str], str, str]:
    """
    Create Carrier and CarrierDomain entities for all carriers in the
    PyPSA network using the same canonical CESDM naming as the TYNDP importer.

    carrier.electricity, carrier.fuel.fossil.gas.natural_gas,
    carrier.fuel.nuclear.uranium, resource.renewable.wind, …

    CO₂ intensities and fuel costs are taken from cesdm_carriers.py —
    the same values as in example_import_export_tyndp.py.

    Returns
    -------
    carrier_to_ec : { pypsa_carrier_string → Carrier entity id }
    carrier_to_cd : { pypsa_carrier_string → CarrierDomain entity id }
    default_ec    : fallback Carrier id (electricity)
    default_cd    : fallback CarrierDomain id (electricity domain)
    """
    carrier_strings = collect_all_carrier_strings(network)
    energy_carriers: Set[str] = set()

    for name in carrier_strings:
        kind, val = classify_carrier_or_technology(name)
        if kind == "carrier":
            energy_carriers.add(val)
    for name in carrier_strings:
        kind, _ = classify_carrier_or_technology(name)
        if kind == "technology":
            fuel = guess_fuel_from_technology(name)
            if fuel:
                energy_carriers.add(fuel)
    energy_carriers.add("electricity")

    carrier_to_ec: Dict[str, str] = {}
    carrier_to_cd: Dict[str, str] = {}

    for c in sorted(energy_carriers):
        cid = canonical_carrier_id(c)   # e.g. "carrier.fuel.nuclear.uranium"
        did = canonical_domain_id(cid)  # e.g. "domain.nuclear"
        ensure_carrier_entities(model, cid, year=year)
        carrier_to_ec[c] = cid
        carrier_to_cd[c] = did

    default_ec = carrier_to_ec.get("electricity", ELECTRICITY_CARRIER_ID)
    default_cd = carrier_to_cd.get("electricity", ELECTRICITY_DOMAIN_ID)
    return carrier_to_ec, carrier_to_cd, default_ec, default_cd

# ---------------------------------------------------------------------------
# Main builder: PyPSA NC → CESDM Model
# ---------------------------------------------------------------------------

def build_cesdm_from_pypsa(
    nc_path: str,
    schema_dir: str,
    region_name: str = "DefaultRegion",
    nuts_shapefile: str | None = None,
    default_library_path: str | None = None,
) -> Tuple[CesdmModel, dict]:
    """
    Build a CESDM V4 Model from a PyPSA NetCDF file.

    Parameters
    ----------
    nc_path       : path to the PyPSA *.nc file
    schema_dir    : path to CESDM V4 schema directory
    region_name   : default region name when the network has no country info
    nuts_shapefile: optional path to a NUTS shapefile (EPSG:4326) for
                    sub-national NUTS2/NUTS3 region assignment. Requires
                    geopandas. Example: "data/NUTS_RG_20M_2021_4326.shp"
    default_library_path: optional path to ``default_library.yaml``. When
                    omitted, the repository default library is loaded.

    Returns
    -------
    model          : populated CesdmModel instance
    profiles_values: { Profile entity id → np.ndarray } for HDF5 export
    """
    network = pypsa.Network(nc_path)
    model: CesdmModel = build_model_from_yaml(schema_dir)
    profiles_values: dict = {}

    # PyPSA carrier labels are aggregate technology categories. Load the
    # canonical CESDM library and map each generator to a GeneratorType so
    # shared VOM, efficiency, ramp and carrier-cost data come from one source.
    library_path = Path(default_library_path) if default_library_path else (_REPO_ROOT / "library" / "default_library")
    if library_path.exists():
        model.import_library(str(library_path))
    else:
        print(f"[WARN] CESDM default library not found: {library_path}")
    regions_path = library_path.parent / "regions_library" if library_path.name == "default_library" else (_REPO_ROOT / "library" / "regions_library")
    if regions_path.exists():
        model.import_library(str(regions_path))
    else:
        print(f"[WARN] CESDM regions library not found: {regions_path}")

    # Load NUTS3 shapefile if provided (optional geopandas dependency)
    _nuts3_gdf = None
    if nuts_shapefile is not None:
        try:
            import geopandas as gpd
            _nuts3_gdf = gpd.read_file(nuts_shapefile)
            if _nuts3_gdf.crs is None:
                _nuts3_gdf = _nuts3_gdf.set_crs("EPSG:4326")
            elif str(_nuts3_gdf.crs).lower() not in ("epsg:4326", "crs84"):
                _nuts3_gdf = _nuts3_gdf.to_crs("EPSG:4326")
            level_col = next(
                (c for c in ("LEVL_CODE","LEVEL","STAT_LEVL_","LEVL")
                 if c in _nuts3_gdf.columns), None)
            if level_col:
                _nuts3_gdf = _nuts3_gdf[
                    _nuts3_gdf[level_col].astype(int) == 3].copy()
            _ = _nuts3_gdf.sindex  # build spatial index
            print(f"Loaded {len(_nuts3_gdf)} NUTS3 regions.")
        except ImportError:
            print("[WARN] geopandas not installed — NUTS3 lookup disabled.")
        except Exception as exc:
            print(f"[WARN] Could not load NUTS shapefile: {exc}")

    weights = _snapshot_weights(network)
    n_ts    = len(network.snapshots)

    # ── TimestampSeries ───────────────────────────────────────────────────
    ts_id = "timestamp.pypsa"
    model.add_entity(entity_class="TimestampSeries", entity_id=ts_id)
    safe_set_attr(model, ts_id, "name",   "PyPSA snapshots")
    safe_set_attr(model, ts_id, "length", n_ts)
    if n_ts > 0:
        safe_set_attr(model, ts_id, "start_datetime",
                      str(network.snapshots[0]))
        # Infer resolution from first two snapshots if possible
        try:
            import pandas as pd
            delta = pd.Timestamp(network.snapshots[1]) - \
                    pd.Timestamp(network.snapshots[0])
            total_secs = int(delta.total_seconds())
            h, m = divmod(total_secs // 60, 60)
            safe_set_attr(model, ts_id, "resolution",
                          f"PT{h}H" if m == 0 else f"PT{total_secs}S")
        except Exception:
            safe_set_attr(model, ts_id, "resolution", "PT1H")
    safe_set_attr(model, ts_id, "timezone", "UTC")

    # ── Pre-compute bus voltage from connected lines ─────────────────────
    # PyPSA-Eur aggregated networks sometimes set buses_v_nom = 1.0 (per-unit)
    # or leave it masked. First try to infer real kV from connected lines;
    # any bus still at ≤ 1.0 after the line scan defaults to 380 kV (same
    # convention as the old netcdf2cesdm.py: np.ma.masked → 380).
    _bus_kv: Dict[str, float] = {}
    if not network.buses.empty and "v_nom" in network.buses.columns:
        for bid, bus in network.buses.iterrows():
            v = float(getattr(bus, "v_nom", 0.0) or 0.0)
            _bus_kv[str(bid)] = v

    if not network.lines.empty:
        for _, line in network.lines.iterrows():
            b0, b1 = str(line.bus0), str(line.bus1)
            # v_nom on the line takes precedence over per-unit bus v_nom
            line_v = None
            if "v_nom" in network.lines.columns:
                lv = getattr(line, "v_nom", None)
                if lv is not None and float(lv) > 1.0:
                    line_v = float(lv)
            # Fall back to line type lookup
            if line_v is None and hasattr(network, "line_types"):
                lt = getattr(line, "type", None)
                if lt and lt in network.line_types.index:
                    for col in ("v_nom", "V_nom", "voltage"):
                        if col in network.line_types.columns:
                            v = float(network.line_types.at[lt, col])
                            if v > 1.0:
                                line_v = v
                                break
            if line_v is not None:
                for bid in (b0, b1):
                    if _bus_kv.get(bid, 0.0) <= 1.0:
                        _bus_kv[bid] = line_v

    # ── EnergySystemModel ─────────────────────────────────────────────────
    esm_id = "PyPSA_Model"
    model.add_entity(entity_class="EnergySystemModel", entity_id=esm_id)
    safe_set_attr(model, esm_id, "long_name",
                  f"PyPSA import from {os.path.basename(nc_path)}")
    safe_set_attr(model, esm_id, "co2_price", 0.0)

    # ── CarrierDomain + Carrier ─────────────────────────────────────
    carrier_to_ec, carrier_to_cd, default_ec, default_cd = \
        build_carrier_domain_entities(network, model)

    # ── GeographicalRegion ────────────────────────────────────────────────
    region_by_code: Dict[str, str] = {}
    bus_country_col = next(
        (c for c in ("bus_country", "country") if c in network.buses.columns),
        None,
    )
    default_region_id: Optional[str] = None
    if bus_country_col is None:
        # Prefer a library country id when region_name looks like an ISO code;
        # otherwise create an ad-hoc fallback region.
        if len(region_name.strip()) == 2 and region_name.strip().isalpha():
            default_region_id = _ensure_geo_region(
                model, _country_region_id(region_name), name=region_name.strip().upper()
            )
        else:
            default_region_id = _make_id("GR_", region_name)
            _ensure_geo_region(model, default_region_id, name=region_name)

    # ── ElectricalBus (buses) ─────────────────────────────────────────────────
    bus_to_node: Dict[str, str] = {}
    bus_to_cd:   Dict[str, str] = {}
    bus_to_carrier: Dict[str, str] = {}

    for bus_id, bus in network.buses.iterrows():
        # Id: "node.{bus_name}" — enriched to "node.{nuts3}.{bus_name}" later
        # if NUTS3 lookup succeeds. Use the raw bus_id (PyPSA name) as the
        # human-readable suffix, matching the old netcdf2cesdm.py convention.
        node_id = f"node.{_slugify(str(bus_id))}"
        bus_to_node[bus_id] = node_id

        model.add_entity(entity_class="ElectricalBus", entity_id=node_id)
        # name will be (re-)set after NUTS3 enrichment below
        v_kv = _bus_kv.get(str(bus_id), 0.0)
        if v_kv <= 1.0:
            # Per-unit placeholder (1.0) or missing (0.0) — fall back to 380 kV
            # matching the old netcdf2cesdm.py behaviour (np.ma.masked → 380).
            v_kv = 380.0
        safe_set_attr(model, node_id, "nominal_voltage", v_kv)

        # Determine bus carrier → CarrierDomain
        bus_canonical = "electricity"
        if "carrier" in network.buses.columns:
            bc = getattr(bus, "carrier", None)
            if bc is not None and str(bc).lower() != "nan":
                kind, val = classify_carrier_or_technology(str(bc))
                if kind == "carrier":
                    bus_canonical = val
                else:
                    guessed = guess_fuel_from_technology(bc)
                    if guessed:
                        bus_canonical = guessed

        bus_to_carrier[bus_id] = bus_canonical
        cd_id = carrier_to_cd.get(bus_canonical, default_cd)
        bus_to_cd[bus_id] = cd_id
        safe_add_rel(model, node_id, "belongsToCarrierDomain", cd_id)

        # GeographicalRegion
        # When NUTS3 shapefile is provided the belongsToGeographicalRegion relation is set
        # inside the NUTS3 block below (NUTS3 region only, no country level).
        # Without shapefile, fall back to country-level region from regions_library.
        if _nuts3_gdf is None:
            if bus_country_col is not None:
                ccode = str(getattr(bus, bus_country_col, "") or "")
                if ccode and ccode.lower() != "nan":
                    if ccode not in region_by_code:
                        gr_id = _country_region_id(ccode)
                        region_by_code[ccode] = _ensure_geo_region(model, gr_id, name=ccode.strip().upper())
                    safe_add_rel(model, node_id, "belongsToGeographicalRegion",
                                 region_by_code[ccode])
                else:
                    if default_region_id is None:
                        default_region_id = _make_id("GR_", region_name)
                        _ensure_geo_region(model, default_region_id, name=region_name)
                    safe_add_rel(model, node_id, "belongsToGeographicalRegion", default_region_id)
            else:
                safe_add_rel(model, node_id, "belongsToGeographicalRegion", default_region_id)

        # Read coordinates before the optional NUTS3-based node rename; assign them
        # directly to the final ElectricalBus entity afterwards.
        lon_val = lat_val = None
        if "x" in network.buses.columns:
            v = getattr(bus, "x", None)
            if v is not None and str(v) != "nan":
                try: lon_val = float(v)
                except (TypeError, ValueError): pass
        if "y" in network.buses.columns:
            v = getattr(bus, "y", None)
            if v is not None and str(v) != "nan":
                try: lat_val = float(v)
                except (TypeError, ValueError): pass

        # NUTS3 sub-region (optional — requires geopandas + shapefile)
        if _nuts3_gdf is not None and lon_val is not None and lat_val is not None:
            nuts_info = _lookup_nuts3(_nuts3_gdf, lon_val, lat_val)
            if nuts_info:
                nuts3_id = _nuts_region_id("nuts3", nuts_info["nuts3"])
                nuts2_id = _nuts_region_id("nuts2", nuts_info["nuts2"])
                for rid, rname in [(nuts3_id, nuts_info.get("name", nuts3_id)),
                                   (nuts2_id, nuts_info["nuts2"])]:
                    _ensure_geo_region(model, rid, name=rname)
                # Library entities already carry isSubRegionOf; only add when missing.
                if not model.get_relation_targets(nuts3_id, "isSubRegionOf"):
                    safe_add_rel(model, nuts3_id, "isSubRegionOf", nuts2_id)
                # Bus located in NUTS3 region (matching old netcdf2cesdm.py)
                model.add_relation(node_id, "belongsToGeographicalRegion", nuts3_id)
                # Rebuild node_id to include nuts3 code: "node.{nuts3}.{bus_name}"
                # This matches the old netcdf2cesdm.py convention.
                old_node_id = node_id
                node_id = f"node.{str(nuts_info['nuts3']).lower()}.{_slugify(str(bus_id))}"
                if node_id != old_node_id:
                    # Re-register under the enriched id; keep old id as alias
                    # Rename the node key in ElectricalBus (and any other NetworkNode subclass
                    # dict that may hold this id). The deprecated "Bus" dict is also patched
                    # for backwards compatibility with old serialised models.
                    for _cls in ("ElectricalBus", "GasBus", "HeatBus", "HydrogenBus", "Bus"):
                        if _cls in model.entities and old_node_id in model.entities[_cls]:
                            ent = model.entities[_cls].pop(old_node_id)
                            model.entities[_cls][node_id] = ent
                    bus_to_node[bus_id] = node_id

        # Store coordinates directly on the ElectricalBus through EAR attributes.
        if lon_val is not None:
            safe_set_attr(model, node_id, "longitude", lon_val)
        if lat_val is not None:
            safe_set_attr(model, node_id, "latitude", lat_val)

        # Set name to the final (NUTS3-enriched or plain) entity id
        safe_set_attr(model, node_id, "name", node_id)

    # ── TransmissionElement — AC lines ────────────────────────────────────
    for line_id, line in network.lines.iterrows():
        n_par = getattr(line, "num_parallel", 1) or 1
        # Don't skip n_par < 1 here — extendable lines (not yet built) have
        # num_parallel=0 but should still appear with side_on=0 (switch open).
        if n_par < 0:
            continue

        frm_sfx = _node_suffix(bus_to_node, str(line.bus0))
        to_sfx  = _node_suffix(bus_to_node, str(line.bus1))
        eid     = f"line.{frm_sfx}.{to_sfx}.{_slugify(str(line_id))}"
        frm_id = bus_to_node.get(str(line.bus0))
        to_id  = bus_to_node.get(str(line.bus1))
        model.add_entity(entity_class="TransmissionLine", entity_id=eid)
        safe_set_attr(model, eid, "name", eid)
        tv = _connect_branch(model, eid, frm_id, to_id)

        # ── Electrical parameters, held directly on the asset itself ────
        #
        # The old netcdf2cesdm.py used hardcoded voltage-level defaults for
        # r, x, b and Smax — the elec.nc does not store per-km impedance
        # values directly. Only v_nom, length, num_parallel, s_nom are used.
        #
        # x [Ω/km]: 220kV=0.301, 300kV=0.2735, 380kV=0.246
        # r [Ω/km]: 0.0  (old code hardcoded)
        # b [S/km]: 0.0  (old code hardcoded)
        # Smax [MVA]: 380kV=1698.1, 300kV=1005.5, 220kV=491.6 × num_parallel

        def _fv(attr):
            v = getattr(line, attr, None)
            return float(v) if v is not None and str(v) != "nan" else None

        length_km  = _fv("length") or 1.0
        v_bus0     = _bus_kv.get(str(line.bus0), 380.0)
        v_nom_line = _fv("v_nom") or v_bus0

        _X_DEFAULT = {220: 0.301, 300: 0.2735, 380: 0.246}
        _S_DEFAULT = {220: 491.556019188047,
                      300: 1005.45549379373,
                      380: 1698.10261174053}
        v_std    = min(_X_DEFAULT.keys(), key=lambda v: abs(v - v_nom_line))
        r_per_km = 0.0
        x_per_km = _X_DEFAULT.get(v_std, 0.246)
        b_per_km = 0.0

        s_nom_pypsa  = _fv("s_nom") or 0.0
        s_nom_opt    = _fv("s_nom_opt")
        s_extendable = bool(getattr(line, "s_nom_extendable", False))
        if s_extendable and s_nom_opt is not None and s_nom_opt > s_nom_pypsa:
            s_nom_pypsa = s_nom_opt
        s_default = _S_DEFAULT.get(v_std, 1698.10261174053)
        # Smax = per-circuit voltage-level default (matching old netcdf2cesdm.py which
        # always overrides lines_s_nom with the hardcoded voltage-level value).
        # For extendable lines with no capacity yet, keep 0 so side_on=0 is set.
        s_total = s_default if not (s_extendable and s_nom_pypsa == 0.0) else 0.0

        under_construction = bool(getattr(line, "under_construction", False))
        switch = 0 if (under_construction or (s_extendable and s_nom_pypsa == 0.0)) else 1
        model.add_attribute(tv, "from_switch_closed", switch)
        model.add_attribute(tv, "to_switch_closed",   switch)

        pv = eid
        model.add_attribute(pv, "series_resistance_per_km", r_per_km, unit="Ohm/km")
        model.add_attribute(pv, "series_reactance_per_km", x_per_km, unit="Ohm/km")
        model.add_attribute(pv, "shunt_susceptance_per_km", b_per_km, unit="microS/km")
        safe_set_attr(model, pv, "line_length",            length_km)
        safe_set_attr(model, pv, "thermal_capacity_rating", s_total)
        safe_set_attr(model, pv, "parallel_circuit_count", int(n_par))
    # ── TransmissionElement — transformers ───────────────────────────────
    for trafo_id, trafo in network.transformers.iterrows():
        bus0 = str(trafo.bus0)
        bus1 = str(trafo.bus1)
        tr_frm_sfx = _node_suffix(bus_to_node, bus0)
        tr_to_sfx  = _node_suffix(bus_to_node, bus1)
        eid        = f"transformer.{tr_frm_sfx}.{tr_to_sfx}.{_slugify(str(trafo_id))}"
        model.add_entity(entity_class="Transformer", entity_id=eid)
        safe_set_attr(model, eid, "name", eid)
        _connect_branch(model, eid,
                            bus_to_node.get(bus0),
                            bus_to_node.get(bus1))
        pv     = eid
        s_nom  = getattr(trafo, "s_nom", None)
        safe_set_attr(model, pv, "thermal_capacity_rating",
                      float(s_nom) if s_nom is not None else None)

        v0 = _bus_kv.get(bus0, 0.0)
        v1 = _bus_kv.get(bus1, 0.0)
        safe_set_attr(model, pv, "rated_primary_voltage",   v0)
        safe_set_attr(model, pv, "rated_secondary_voltage", v1)

        x_pu = getattr(trafo, "x_pu", None)
        r_pu = getattr(trafo, "r_pu", None)
        if x_pu is not None or r_pu is not None:
            z = ((float(x_pu or 0.0))**2 + (float(r_pu or 0.0))**2) ** 0.5
            safe_set_attr(model, pv, "thermal_capacity_rating",
                          float(s_nom) if s_nom else None)
            usc = 100.0 * z
            if usc > 0.0:   # only store when meaningful; 0.0 → export uses default 10%
                safe_set_attr(model, pv, "short_circuit_voltage_in_percentage", usc)
        # When x_pu/r_pu absent: short_circuit_voltage_in_percentage left unset → export default 10.0

    # ── DemandUnit (loads) ────────────────────────────────────────────────
    for load_id, load in network.loads.iterrows():
        bus    = str(load.bus)
        bus_id = bus_to_node.get(bus)
        eid    = f"load.{_node_suffix(bus_to_node, bus)}"

        model.add_entity(entity_class="DemandUnit", entity_id=eid)
        safe_set_attr(model, eid, "name", eid)
        model.add_relation(eid, "atNode", bus_id)
        # Annual energy, held directly on the DemandUnit itself
        annual = 0.0
        if (hasattr(network, "loads_t") and
                hasattr(network.loads_t, "p_set") and
                load_id in network.loads_t.p_set.columns):
            try:
                annual = float(
                    (np.asarray(network.loads_t.p_set[load_id], dtype=float)
                     * weights).sum()
                )
            except Exception:
                pass
        if annual == 0.0:
            p_set = getattr(load, "p_set", None)
            if p_set is not None and n_ts > 0:
                annual = float(p_set) * float(n_ts)

        dv = eid
        safe_set_attr(model, dv, "annual_energy_demand", annual)

        # Profile entity
        prof_id = f"profile.demand.{_node_suffix(bus_to_node, bus)}"
        if (hasattr(network, "loads_t") and
                hasattr(network.loads_t, "p_set") and
                load_id in network.loads_t.p_set.columns):
            arr = np.asarray(network.loads_t.p_set[load_id], dtype=float)
            # Normalise to annual shape; negate because demand is a
            # withdrawal from the bus (negative injection convention used
            # by FlexEco and consistent with CESDM withdrawal semantics).
            arr_norm = arr / arr.sum() if arr.sum() > 0 else arr
            _register_profile(model, profiles_values, prof_id, -arr_norm,
                               "as_normalized_annual_energy", "pu", ts_id)
            model.add_relation(dv, "hasDemandProfile", prof_id)

    # ── GenerationUnit (generators) ───────────────────────────────────────
    _gen_counter: Dict[str, int] = {}   # {carrier.node_suffix → count}
    for gen_id, gen in network.generators.iterrows():
        bus    = str(gen.bus)
        bus_id = bus_to_node.get(bus)

        # Carrier / technology (resolved first so eid can include carrier slug)
        carrier_str = getattr(gen, "carrier", None)
        tech_str    = None
        fuel_carrier = None

        if carrier_str is not None and str(carrier_str).lower() != "nan":
            kind, val = classify_carrier_or_technology(str(carrier_str))
            if kind == "carrier":
                fuel_carrier = val
                tech_str = getattr(gen, "type", None) or str(carrier_str)
            else:
                tech_str     = str(carrier_str)
                fuel_carrier = guess_fuel_from_technology(carrier_str)
        else:
            tech_str = getattr(gen, "type", None)

        # Resolve the PyPSA aggregate technology to a canonical library type.
        technology_type_id = _default_generator_type_id(carrier_str, tech_str)

        # Output carrier from bus. Input carrier/resource is preferably read
        # from the mapped GeneratorType, with the old heuristic as fallback.
        bus_carrier = bus_to_carrier.get(bus, "electricity")
        out_ec = carrier_to_ec.get(bus_carrier, default_ec)
        type_input_carrier = _relation_target(model, technology_type_id, "hasInputCarrier")
        type_input_resource = _relation_target(model, technology_type_id, "hasInputResource")
        # The mapped default-library technology is authoritative for its
        # physical input.  PyPSA carrier heuristics are only a fallback when
        # no canonical GeneratorType relation is available.
        in_carrier = fuel_carrier or bus_carrier
        in_ec = (
            type_input_resource
            or type_input_carrier
            or carrier_to_ec.get(in_carrier, out_ec)
        )

        non_disp = _is_non_dispatchable(carrier_str, tech_str)

        # Wind/Solar/RoR (and any other carrier _is_non_dispatchable()
        # classifies this way) with no genuine availability data at all,
        # or with zero installed capacity, are skipped entirely, rather
        # than imported as a generator that can structurally never
        # produce power: a flat-zero profile or a zero nominal capacity
        # would still pass CESDM's own schema validation (nothing in the
        # schema requires a positive value), so it would silently sit in
        # the model -- annual_resource_potential permanently 0 regardless
        # of the profile's own shape, since it's the product of the
        # profile and the capacity -- only to be quietly dropped much
        # later -- by tools/aggregate_cesdm_model.py's own "no
        # availability/run-of-river profile" check, or by a downstream
        # dispatch tool that simply never dispatches it -- with no
        # obvious link back to this importer as the actual cause. Skipping
        # here, at the one point where the source PyPSA data is directly
        # visible, keeps that cause immediately traceable.
        if non_disp:
            gen_id_str = str(gen_id)
            p_nom_for_check = getattr(gen, "p_nom", None)
            try:
                has_capacity = p_nom_for_check is not None and float(p_nom_for_check) > 0
            except (TypeError, ValueError):
                has_capacity = False

            ts_profile_for_check = None
            if (
                hasattr(network, "generators_t") and
                hasattr(network.generators_t, "p_max_pu") and
                gen_id_str in network.generators_t.p_max_pu.columns
            ):
                ts_profile_for_check = np.asarray(
                    network.generators_t.p_max_pu[gen_id_str], dtype=float)

            if ts_profile_for_check is not None:
                # A genuine time-varying profile exists -- but if every
                # value in it is zero (or negative/NaN), it can never
                # contribute anything either.
                has_positive_profile = bool(np.any(np.nan_to_num(ts_profile_for_check) > 0))
            else:
                # No time-varying profile at all: fall back to whatever
                # scalar p_max_pu PyPSA reports (its own component default
                # is 1.0 -- a flat "always available" assumption, which is
                # a real, if simplified, modelling choice and is kept; only
                # an explicit non-positive scalar is treated as "no
                # profile").
                scalar_p_max_pu = getattr(gen, "p_max_pu", 1.0)
                try:
                    has_positive_profile = float(scalar_p_max_pu) > 0
                except (TypeError, ValueError):
                    has_positive_profile = True

            if not has_capacity or not has_positive_profile:
                reason = (
                    "zero/missing nominal_power_capacity" if not has_capacity
                    else "no profile or an all-zero/non-positive profile"
                )
                print(
                    f"[SKIP] generator '{gen_id_str}' (carrier={carrier_str!r}) -- "
                    f"non-dispatchable with {reason}; not imported."
                )
                continue

        # id: "generator.{carrier_slug}.{counter:02d}.{node_suffix}"
        carrier_slug = _slugify(str(carrier_str or tech_str or "gen"))
        node_sfx     = _node_suffix(bus_to_node, bus)
        counter_key  = f"{carrier_slug}.{node_sfx}"
        _gen_counter[counter_key] = _gen_counter.get(counter_key, 0) + 1
        eid = f"generator.{carrier_slug}.{_gen_counter[counter_key]:02d}.{node_sfx}"

        gen_cls = _generation_asset_class(carrier_str, tech_str)
        # Use the domain helper when available.  It creates the specialized
        # generation asset with dispatch attributes and atNode held directly
        # on it. Keep the local gen_cls variable for existing downstream
        # technology-specific profile logic.
        model.add_entity(entity_class=gen_cls, entity_id=eid)
        safe_set_attr(model, eid, "name", eid)
        model.add_relation(eid, "atNode", bus_id)
        safe_set_attr(model, eid, "name", eid)
        if technology_type_id and technology_type_id in model.entities.get("GeneratorType", {}):
            safe_add_rel(model, eid, "hasTechnology", technology_type_id)
        gv = eid
        # Non-dispatchable (wind/solar/RoR): resource is exogenous and
        # availability is bounded by a profile.
        # Dispatchable (thermal/hydro reservoir): operator decides output.
        safe_set_attr_if_supported(model, gv, "dispatch_type",
                                   "nondispatchable" if non_disp else "dispatchable")
        if tech_str:
            safe_set_attr_if_supported(model, gv, "generator_technology_type", str(tech_str))

        # Instance capacity comes from PyPSA. Shared techno-economic values
        # come from the mapped default-library GeneratorType. PyPSA values are
        # used only when no matching library type/value exists.
        library_eff = _entity_attribute(model, technology_type_id, "energy_conversion_efficiency")
        raw_eff = getattr(gen, "efficiency", 1.0)
        eff = library_eff if library_eff is not None else _hydrogen_generation_efficiency(carrier_str, tech_str, raw_eff)
        safe_set_attr_if_supported(model, gv, "energy_conversion_efficiency", float(eff))

        p_nom = getattr(gen, "p_nom", None)
        safe_set_attr_if_supported(model, gv, "nominal_power_capacity",
                                   float(p_nom) if p_nom is not None else None)

        library_vom = _entity_attribute(model, technology_type_id, "variable_operating_cost")
        pypsa_mc = getattr(gen, "marginal_cost", None)
        vom = library_vom if library_vom is not None else pypsa_mc
        safe_set_attr_if_supported(model, gv, "variable_operating_cost",
                                   float(vom) if vom is not None else None)

        for attr in ("minimum_generation", "maximum_ramp_rate_up", "maximum_ramp_rate_down",
                     "dispatch_type"):
            safe_set_attr_if_supported(model, gv, attr, _entity_attribute(model, technology_type_id, attr))

        # Carrier cost is canonical data of the related Carrier.
        # Do not duplicate it on the generator asset.

        # Carrier/resource relations on GenerationUnit directly; mapped GeneratorType
        # provides the canonical library defaults and carrier/resource semantics.
        # Wind/solar/hydro natural inputs are NaturalResource instances and must
        # use hasInputResource; transported commodities such as gas/H2/uranium
        # remain Carrier instances and use hasInputCarrier.
        # Carrier/resource relations are created by CesdmModel.create_generation_unit.
        # Keep a fallback for older Model implementations.
        if in_ec:
            in_ec_str = str(in_ec)
            if in_ec_str.startswith("resource."):
                safe_add_rel(model, eid, "hasInputResource", in_ec_str)
            else:
                safe_add_rel(model, eid, "hasInputCarrier", in_ec_str)
        safe_add_rel(model, eid, "hasOutputCarrier", out_ec)

        # Resource potential and availability profile
        p_nom_val = float(p_nom) if p_nom is not None else 0.0

        has_ts_profile = (
            hasattr(network, "generators_t") and
            hasattr(network.generators_t, "p_max_pu") and
            gen_id in network.generators_t.p_max_pu.columns
        )

        if has_ts_profile:
            # Time-varying capacity factor profile (wind/solar/RoR)
            p_max_pu = np.asarray(
                network.generators_t.p_max_pu[gen_id], dtype=float)
            annual_res = float((p_max_pu * p_nom_val * weights).sum())
            prof_id = f"profile.{carrier_slug}.{_node_suffix(bus_to_node, bus)}"
            _register_profile(model, profiles_values, prof_id, p_max_pu,
                               "as_capacity_factor", "pu", ts_id)
            # annual_resource_potential on the asset; RoR inflow profile on the
            # linked HydraulicStorageUnit (water body), else availability on gen.
            safe_set_attr_if_supported(model, gv, "annual_resource_potential", annual_res)
            if gen_cls == "HydroGenerationUnit":
                res_ids = model.get_relation_targets(gv, "drawsFromHydraulicStorage") or []
                if res_ids:
                    safe_add_rel_if_supported(
                        model, res_ids[0], "hasNaturalInflowProfile", prof_id
                    )
                else:
                    safe_add_rel_if_supported(model, gv, "hasAvailabilityProfile", prof_id)
            else:
                safe_add_rel_if_supported(model, gv, "hasAvailabilityProfile", prof_id)

        elif non_disp:
            # Non-dispatchable generator with flat (scalar) p_max_pu.
            # Create a constant profile so FlexEco receives a PN_GenNonDispatchable
            # with a flat capacity factor rather than a spurious PN_GenDispatchable.
            p_max_pu_scalar = float(getattr(gen, "p_max_pu", 1.0) or 1.0)
            annual_res = p_nom_val * p_max_pu_scalar * n_ts
            flat_profile = np.full(n_ts, p_max_pu_scalar, dtype=np.float64)
            prof_id = f"profile.{carrier_slug}.{_node_suffix(bus_to_node, bus)}"
            _register_profile(model, profiles_values, prof_id, flat_profile,
                               "as_capacity_factor", "pu", ts_id)
            safe_set_attr_if_supported(model, gv, "annual_resource_potential", annual_res)
            if gen_cls == "HydroGenerationUnit":
                res_ids = model.get_relation_targets(gv, "drawsFromHydraulicStorage") or []
                if res_ids:
                    safe_add_rel_if_supported(
                        model, res_ids[0], "hasNaturalInflowProfile", prof_id
                    )
                else:
                    safe_add_rel_if_supported(model, gv, "hasAvailabilityProfile", prof_id)
            else:
                safe_add_rel_if_supported(model, gv, "hasAvailabilityProfile", prof_id)

    # ── StorageUnit (storage_units) ───────────────────────────────────────
    _stor_counter: Dict[str, int] = {}   # {carrier.node_suffix → count}
    for su_id, su in network.storage_units.iterrows():
        bus    = str(su.bus)
        bus_id = bus_to_node.get(bus)

        # id: "storage.{carrier_slug}.{counter:02d}.{node_suffix}"
        su_carrier_str = str(getattr(su, "carrier", "") or "storage")
        su_carrier_slug = _slugify(su_carrier_str)
        su_node_sfx    = _node_suffix(bus_to_node, bus)
        su_counter_key = f"{su_carrier_slug}.{su_node_sfx}"
        _stor_counter[su_counter_key] = _stor_counter.get(su_counter_key, 0) + 1
        eid = f"storage.{su_carrier_slug}.{_stor_counter[su_counter_key]:02d}.{su_node_sfx}"

        su_is_hydro_res = _is_reservoir_hydro_storage(su_carrier_str)
        su_is_phs = _is_pumped_hydro_storage(su_carrier_str)
        su_has_inflow, su_annual_inflow, su_inflow = _positive_storage_unit_inflow(network, su_id, weights)
        # Reservoir/pondage hydro without natural inflow cannot be represented
        # as inflow-driven hydro dispatch. PHS is kept even without natural
        # inflow because it can operate as pumped storage.
        if su_is_hydro_res and not su_is_phs and not su_has_inflow:
            continue

        model.add_entity(entity_class=_storage_asset_class(su_carrier_str), entity_id=eid)
        safe_set_attr(model, eid, "name", eid)
        # A hydro/PHS reservoir is never itself electrically connected --
        # only its paired HydroGenerationUnit is (via drawsFromHydraulicStorage),
        # attached below through _ensure_hydro_reservoir_composite(). Setting
        # atNode on the reservoir itself here too would be both redundant
        # and semantically wrong (two entities connected to the same bus
        # for what CESDM models as one physical asset), and confuses
        # anything that assumes a HydraulicStorageUnit has no direct
        # electrical connection of its own (e.g. downstream aggregation).
        if not su_is_hydro_res:
            safe_add_rel(model, eid, "atNode", bus_to_node.get(str(su.bus)))
        p_nom     = getattr(su, "p_nom",       None)
        max_hours = getattr(su, "max_hours",   None)
        e_nom     = getattr(su, "energy_nom",  None)
        if e_nom is None and p_nom is not None and max_hours is not None:
            e_nom = float(p_nom) * float(max_hours)

        is_hydro_res = su_is_hydro_res
        sv = eid
        # Store the PyPSA carrier string (hydro/PHS/battery) on the asset
        # so the FlexEco exporter can determine Dam vs Pump correctly.
        # StorageUnit and HydraulicStorageUnit intentionally have different
        # schemas. Write PyPSA storage attributes only when the concrete
        # asset class supports them; reservoir/PHS power and pump parameters
        # are carried directly on the linked HydroGenerationUnit below.
        safe_set_attr_if_supported(model, sv, "storage_technology_type", su_carrier_str)
        safe_set_attr_if_supported(model, sv, "nominal_power_capacity",
                                   float(p_nom) if p_nom is not None else None)
        safe_set_attr_if_supported(model, sv, "maximum_charging_power",
                                   float(p_nom) if p_nom is not None else None)
        safe_set_attr_if_supported(model, sv, "energy_storage_capacity",
                                   float(e_nom) if e_nom is not None else None)
        # charging_efficiency = efficiency_store × 0.95 auxiliary loss factor
        # (matches old netcdf2cesdm.py: eta_load = efficiency_store * 0.95)
        safe_set_attr_if_supported(model, sv, "charging_efficiency",
                                   float(getattr(su, "efficiency_store",    1.0) or 1.0) * 0.95)
        safe_set_attr_if_supported(model, sv, "discharging_efficiency",
                                   float(getattr(su, "efficiency_dispatch", 1.0) or 1.0))

        bus_carrier = bus_to_carrier.get(bus, "electricity")
        ec_id = carrier_to_ec.get(bus_carrier, default_ec)
        if _is_reservoir_hydro_storage(su_carrier_str):
            safe_add_rel(model, eid, "storesResource", "resource.water")
            gen_id = _ensure_hydro_reservoir_composite(
                model,
                reservoir_id=eid,
                bus_id=bus_to_node.get(str(su.bus)),
                power_capacity=float(p_nom) if p_nom is not None else None,
                resource_potential=None,
                is_reversible=_is_pumped_hydro_storage(su_carrier_str),
            )
            hdv = gen_id
            safe_set_attr(model, hdv, "turbine_efficiency",
                          float(getattr(su, "efficiency_dispatch", 1.0) or 1.0))
            if su_is_phs:
                safe_set_attr(model, hdv, "maximum_pumping_power",
                              float(p_nom) if p_nom is not None else None)
                safe_set_attr(model, hdv, "pumping_efficiency",
                              float(getattr(su, "efficiency_store", 1.0) or 1.0) * 0.95)
        else:
            safe_add_rel(model, eid, "storesCarrier", ec_id)
        if _is_pumped_hydro_storage(su_carrier_str):
            safe_set_attr_if_supported(model, sv, "has_active_charging", True)

        # Inflow profile
        if su_inflow is not None:
            inflow = su_inflow
            annual_inflow = su_annual_inflow
            if annual_inflow > 0.0:
                safe_set_attr_if_supported(model, sv, "annual_natural_inflow_energy",
                                           annual_inflow)
            total = inflow.sum()
            arr_norm = inflow / total if total > 0 else inflow
            prof_id  = f"profile.inflow.{su_carrier_slug}.{su_node_sfx}"
            _register_profile(model, profiles_values, prof_id, arr_norm,
                               "as_normalized_annual_energy", "pu", ts_id)
            safe_add_rel_if_supported(model, sv, "hasNaturalInflowProfile", prof_id)

    # ── StorageUnit (stores) ──────────────────────────────────────────────
    _store_counter: Dict[str, int] = {}
    for st_id, st in network.stores.iterrows():
        bus    = str(st.bus)
        bus_id = bus_to_node.get(bus)

        st_carrier_str  = str(getattr(st, "carrier", "") or "store")
        st_carrier_slug = _slugify(st_carrier_str)
        st_node_sfx     = _node_suffix(bus_to_node, bus)
        st_counter_key  = f"{st_carrier_slug}.{st_node_sfx}"
        _store_counter[st_counter_key] = _store_counter.get(st_counter_key, 0) + 1
        eid = f"store.{st_carrier_slug}.{_store_counter[st_counter_key]:02d}.{st_node_sfx}"

        st_is_hydro_res = _is_reservoir_hydro_storage(st_carrier_str)
        st_is_phs = _is_pumped_hydro_storage(st_carrier_str)
        st_has_inflow, st_annual_inflow, st_inflow = _positive_store_inflow(network, st_id, weights)
        # Reservoir/pondage stores without inflow are skipped; PHS is kept.
        if st_is_hydro_res and not st_is_phs and not st_has_inflow:
            continue

        model.add_entity(entity_class=_storage_asset_class(st_carrier_str), entity_id=eid)
        safe_set_attr(model, eid, "name", eid)
        # Same reasoning as the storage_units loop above: a hydro/PHS
        # reservoir gets its electrical connection exclusively through its
        # paired HydroGenerationUnit, not directly.
        if not st_is_hydro_res:
            safe_add_rel(model, eid, "atNode", bus_to_node.get(str(st.bus)))
        is_hydro_res_st = st_is_hydro_res
        sv = eid
        e_nom = getattr(st, "e_nom", None)
        safe_set_attr_if_supported(model, sv, "energy_storage_capacity",
                                   float(e_nom) if e_nom is not None else None)

        bus_carrier = bus_to_carrier.get(bus, "electricity")
        ec_id = carrier_to_ec.get(bus_carrier, default_ec)
        if is_hydro_res_st:
            safe_add_rel(model, eid, "storesResource", "resource.water")
            _ensure_hydro_reservoir_composite(
                model,
                reservoir_id=eid,
                bus_id=bus_to_node.get(str(st.bus)),
                power_capacity=None,
                resource_potential=None,
                is_reversible=_is_pumped_hydro_storage(st_carrier_str),
            )
        else:
            safe_add_rel(model, eid, "storesCarrier", ec_id)
        if _is_pumped_hydro_storage(st_carrier_str):
            safe_set_attr_if_supported(model, sv, "has_active_charging", True)

        # Inflow profile from stores_t.e_in
        if st_inflow is not None:
            e_in = st_inflow
            annual_inflow = st_annual_inflow
            if annual_inflow > 0.0:
                safe_set_attr_if_supported(model, sv, "annual_natural_inflow_energy",
                                           annual_inflow)
            total    = e_in.sum()
            arr_norm = e_in / total if total > 0 else e_in
            prof_id  = _profile_id(eid, "inflow")
            _register_profile(model, profiles_values, prof_id, arr_norm,
                               "as_normalized_annual_energy", "pu", ts_id)
            safe_add_rel_if_supported(model, sv, "hasNaturalInflowProfile", prof_id)

    # ── Links ─────────────────────────────────────────────────────────────
    # PyPSA links represent directed connections between buses. They split
    # into two asset classes based on whether they cross carrier domains:
    #
    #   Same carrier (or no carrier difference):
    #     → HVDCLink, fromNode/toNode and power-flow attributes held
    #       directly on the asset itself
    #     Examples: HVDC cable, DC link, lossless NTC-style link
    #
    #   Different carriers (or explicit cross-domain conversion):
    #     → ConversionUnit + ConversionPort entities
    #     Examples: electrolyser (electricity → hydrogen),
    #               heat pump (electricity → heat),
    #               gas turbine modelled as link (gas → electricity)
    #
    # Multi-port links (bus2, bus3) generate additional ConversionPort
    # entities for each extra output port.
    # ─────────────────────────────────────────────────────────────────────

    if not network.links.empty:
        for link_id, link in network.links.iterrows():
            bus0   = str(link.bus0)
            bus1   = str(link.bus1)
            bus0_id = bus_to_node.get(bus0)
            bus1_id = bus_to_node.get(bus1)

            if bus0_id is None or bus1_id is None:
                print(f"[WARN] Link '{link_id}' references unknown bus "
                      f"(bus0={bus0!r}, bus1={bus1!r}) — skipped")
                continue

            carrier0 = bus_to_carrier.get(bus0, "electricity")
            carrier1 = bus_to_carrier.get(bus1, "electricity")
            p_nom    = getattr(link, "p_nom", None)
            eff      = float(getattr(link, "efficiency", 1.0) or 1.0)
            link_carrier = str(getattr(link, "carrier", "") or "")
            mc       = getattr(link, "marginal_cost", None)

            same_carrier = (carrier0 == carrier1)

            lnk_frm_sfx = _node_suffix(bus_to_node, bus0)
            lnk_to_sfx  = _node_suffix(bus_to_node, bus1)

            if same_carrier:
                eid = f"hvdc.{lnk_frm_sfx}.{lnk_to_sfx}.{_slugify(str(link_id))}"
                # ── HVDCLink ───────────────────────────────────────────
                # All DC links are represented as the base HVDCLink class.
                # Dispatch/power-flow attributes are flattened directly
                # onto the asset (see CHANGELOG.md).
                model.add_entity(entity_class="HVDCLink", entity_id=eid)
                safe_set_attr(model, eid, "name", eid)
                _connect_branch(model, eid, bus0_id, bus1_id)

                dv = eid

                if p_nom is not None:
                    p_max_pu = float(getattr(link, "p_max_pu", 1.0) or 1.0)
                    safe_set_attr(model, dv, "max_flow",
                                  float(p_nom) * p_max_pu)

                if mc is not None:
                    safe_set_attr(model, dv, "variable_operating_cost",
                                  float(mc))

            else:
                # ── ConversionUnit ──────────────────────────────────────
                in_ec  = carrier_to_ec.get(carrier0, default_ec)
                out_ec = carrier_to_ec.get(carrier1, default_ec)
                lnk_carrier_slug = _slugify(str(link_carrier) or carrier1)
                eid = f"converter.{lnk_carrier_slug}.{lnk_frm_sfx}.{lnk_to_sfx}.{_slugify(str(link_id))}"

                model.add_entity(entity_class="GenericConversionUnit", entity_id=eid)
                safe_set_attr(model, eid, "name", eid)

                # Conversion topology is represented with explicit ports.
                in_port = f"port.{eid}.input"
                out_port = f"port.{eid}.output1"
                model.add_entity(entity_class="ConversionPort", entity_id=in_port)
                safe_set_attr(model, in_port, "port_direction", "input")
                safe_set_attr(model, in_port, "flow_coefficient", -1.0)
                model.add_relation(in_port, "belongsToUnit", eid)
                model.add_relation(in_port, "atNode", bus0_id)
                model.add_relation(in_port, "hasCarrier", in_ec)

                model.add_entity(entity_class="ConversionPort", entity_id=out_port)
                safe_set_attr(model, out_port, "port_direction", "output")
                safe_set_attr(model, out_port, "flow_coefficient", eff)
                model.add_relation(out_port, "belongsToUnit", eid)
                model.add_relation(out_port, "atNode", bus1_id)
                model.add_relation(out_port, "hasCarrier", out_ec)

                cv = eid
                model.add_relation(cv, "referencePort", in_port)
                if mc is not None:
                    safe_set_attr(model, cv, "variable_operating_cost", float(mc))
                if p_nom is not None:
                    safe_set_attr(model, cv, "nominal_power_capacity", float(p_nom))

                # Additional output ports: bus2, bus3 (multi-port links)
                for port, bus_attr, eff_attr in [
                    ("2", "bus2", "efficiency2"),
                    ("3", "bus3", "efficiency3"),
                ]:
                    extra_bus = str(getattr(link, bus_attr, "") or "")
                    if not extra_bus or extra_bus.lower() == "nan":
                        continue
                    extra_bus_id = bus_to_node.get(extra_bus)
                    if extra_bus_id is None:
                        continue

                    extra_carrier = bus_to_carrier.get(extra_bus, carrier0)
                    extra_ec      = carrier_to_ec.get(extra_carrier, default_ec)
                    extra_eff     = float(getattr(link, eff_attr, 0.0) or 0.0)

                    extra_port = f"port.{eid}.output{port}"
                    model.add_entity(entity_class="ConversionPort", entity_id=extra_port)
                    safe_set_attr(model, extra_port, "port_direction", "output")
                    safe_set_attr(model, extra_port, "flow_coefficient", extra_eff)
                    model.add_relation(extra_port, "belongsToUnit", eid)
                    model.add_relation(extra_port, "atNode", extra_bus_id)
                    model.add_relation(extra_port, "hasCarrier", extra_ec)

    return model, profiles_values
