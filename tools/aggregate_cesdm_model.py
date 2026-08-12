#!/usr/bin/env python3
"""
CESDM nodal-model aggregation — nuts3 / nuts2 / nuts1 / country levels.

Reads a CESDM hierarchical YAML produced by the PyPSA→CESDM importer and
aggregates nodes (ElectricalBus) and their attached assets spatially by
NUTS region code.  Profile arrays are aggregated from a companion HDF5 file
and written to a new HDF5 using the CESDM Profile / TimestampSeries structure.

This tool reads and writes real, current schema classes directly
(GenerationUnit and its subclasses, DemandUnit, StorageUnit,
HydraulicStorageUnit, TransmissionLine, Interconnector, HVDCLink,
Transformer, ...) — every dispatch/topology/power-flow attribute and
relation lives on the one real asset entity, with no separate view/section
layer and no "reportsOn" indirection.

Profile / time-series structure
────────────────────────────────────────────────────────────────────────────
CESDM entities —  TimestampSeries  +  Profile
     Profile has relation hasTimestampSeries → TimestampSeries
     and attribute data_reference = "profiles.h5:/profiles/<profile_id>/values"
     HDF5 layout: /profiles/<profile_id>/values  (float32 array, shape (T,))
                  /timestamps/<ts_id>/  (attrs: start_datetime, resolution, …)
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import copy
import fnmatch
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repo_root()))
sys.path.insert(0, str(_repo_root() / "tools"))


import h5py

from cesdm_toolbox import build_model_from_yaml, CesdmModel
import numpy as np
import yaml


# ── Default values (overridden by CLI arguments) ──────────────────────────────

_DEFAULT_YAML  = "pypsa_cesdm.yaml"
_DEFAULT_H5    = "pypsa_cesdm_profiles.h5"
_DEFAULT_OUTDIR = "aggregated_output"

# HDF5 dtype for read and write
H5_READ_DTYPE  = np.float32
H5_WRITE_DTYPE = np.float32

# Shared electricity carrier / domain ids (CESDM canonical)
CARRIER_ELECTRICITY_ID = "carrier.electricity"
DOMAIN_ELECTRICITY_ID  = "domain.electricity"

# TimestampSeries entity id written into the output YAML
TIMESTAMP_SERIES_ID = "ts.hourly"


# ── CESDM section keys (real schema classes -- no synthetic view layer) ───────
# The tool used to route every asset through an internal ".DispatchView"/
# ".PowerFlowView" pseudo-class with a "reportsOn" relation back to
# the real entity -- a leftover from the pre-flattening CESDM architecture.
# Those classes and that relation no longer exist in the schema at all; the
# real, current model already carries every dispatch/topology/power-flow
# attribute directly on the one real asset entity. This tool now reads and
# writes those real classes directly, with no translation layer in between.

# Non-hydro generation subclasses are intentionally grouped as one bucket:
# they share the same dispatch attribute shape, and merging Wind/Solar/
# Thermal/generic GenerationUnit under one aggregated "GenerationUnit"
# output class (rather than trying to keep each subclass separate through
# aggregation) matches this tool's original, long-standing behaviour. Only
# Hydro needs its own bucket, because of its reservoir-pairing logic.
GENERATION_NONHYDRO_CLASSES = [
    "GenerationUnit", "WindGenerationUnit", "SolarGenerationUnit", "ThermalGenerationUnit",
]
GENERATION_HYDRO_CLASS = "HydroGenerationUnit"
GENERATION_ASSET_CLASSES = GENERATION_NONHYDRO_CLASSES + [GENERATION_HYDRO_CLASS]

# Aggregation "bucket" keys used internally to group generation members
# before producing one aggregated output entity per bucket -- "nonhydro"
# writes out as plain GenerationUnit, "hydro" as HydroGenerationUnit.
GENERATION_BUCKET_OUTPUT_CLASS = {
    "nonhydro": "GenerationUnit",
    "hydro": "HydroGenerationUnit",
}

def generation_bucket_for_class(asset_class: str) -> str:
    return "hydro" if asset_class == GENERATION_HYDRO_CLASS else "nonhydro"

# HydraulicStorageUnit is a standalone class (not a StorageUnit subclass --
# see schemas/cesdm/.../HydraulicStorageUnit.yaml), so the two need separate
# aggregation buckets: a reservoir's storage attributes and aggregation id
# scheme differ from a battery-style StorageUnit's, and reservoirs are kept
# as their own output class rather than collapsed into StorageUnit.
STORAGE_NONRESERVOIR_CLASS = "StorageUnit"
STORAGE_RESERVOIR_CLASS = "HydraulicStorageUnit"
STORAGE_ASSET_CLASSES = [STORAGE_NONRESERVOIR_CLASS, STORAGE_RESERVOIR_CLASS]

BRANCH_ASSET_CLASSES = ["TransmissionLine", "GenericInterconnector", "HVDCLink", "Transformer"]

SECTIONS = {
    "Carrier", "NaturalResource",
    "CarrierDomain",
    "GeographicalRegion",
    "ElectricalBus",
    *GENERATION_ASSET_CLASSES,
    "DemandUnit",
    *STORAGE_ASSET_CLASSES,
    *BRANCH_ASSET_CLASSES,
    "Profile",
    "TimestampSeries",
}


# ── Path helpers ──────────────────────────────────────────────────────────────


# ── NUTS code helpers ─────────────────────────────────────────────────────────

def normalize_code(code: str) -> str:
    code = code.strip().lower()
    if "." in code:
        code = code.split(".", 1)[1]
    return code


def nuts3_to_level(code: str, level: str) -> str:
    """Truncate a NUTS3 code to the requested spatial level.

    ``disaggregated`` is not handled here — callers keep the original bus
    id instead of deriving a region key (see ``aggregate_subset``).
    ``nuts3`` returns the full code (merge all buses that share that NUTS3).
    """
    code = code.lower()
    if level == "nuts3":
        return code
    if level == "disaggregated":
        # Legacy alias: treated like nuts3 only if a caller still asks for a
        # region key. Prefer identity bus mapping in aggregate_subset.
        return code
    if level == "nuts2":
        return code[:-1] if len(code) >= 3 else code
    if level == "nuts1":
        return code[:-2] if len(code) >= 4 else code[:2]
    if level == "country":
        return code[:2]
    raise ValueError(level)


def country_of_nuts3(code: str) -> str:
    """ISO-2 country prefix of a NUTS3 code, e.g. 'ch021' -> 'ch'."""
    return code.lower()[:2]


def parse_kv_overrides(pairs: List[str], *, value_type=str, what: str = "override") -> Dict[str, Any]:
    """Parse ``["CH=nuts3", "de=country"]`` into ``{"ch": "nuts3", "de": "country"}``,
    keyed by lowercased ISO-2 country code. Used for spatial
    ``--level-by-country`` overrides.
    """
    result: Dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(
                f"Invalid --*-by-country {what} {pair!r}: expected COUNTRY=VALUE "
                f"(e.g. CH=nuts3 or DE=country)."
            )
        key, _, raw_value = pair.partition("=")
        key = normalize_code(key)[:2]
        try:
            result[key] = value_type(raw_value)
        except ValueError:
            raise SystemExit(
                f"Invalid value in --*-by-country {what} {pair!r}: "
                f"{raw_value!r} is not a valid {value_type.__name__}."
            )
    return result


def resolve_level_for_country(
    country: str, level_by_country: Dict[str, str], default_level: str,
) -> str:
    """The spatial aggregation level to use for a bus in this country --
    its explicit per-country override if one was given, the global
    ``--level`` default otherwise."""
    return level_by_country.get(country, default_level)


def normalize_tech_groups(patterns: Optional[List[str]]) -> List[str]:
    """Normalize ``--tech-group`` patterns and sort longest-first so more
    specific groups win over broader ones when several match."""
    out: List[str] = []
    for raw in patterns or []:
        pattern = str(raw or "").strip()
        if not pattern:
            continue
        out.append(pattern)
    # Longer literal stems first: Generation.Thermal.Gas.* before Generation.Thermal.*
    out.sort(key=lambda p: (-len(tech_group_key(p)), -len(p)))
    return out


def tech_group_key(pattern: str) -> str:
    """Canonical group id written onto merged assets (pattern without glob)."""
    p = pattern.strip()
    if p.endswith(".*"):
        return p[:-2]
    if p.endswith("*"):
        return p[:-1].rstrip(".")
    return p


def technology_matches_group(tech_id: str, pattern: str) -> bool:
    """True if ``tech_id`` belongs to the ``--tech-group`` pattern.

    Supports shell globs (``Generation.Thermal.Gas.*``) and bare prefixes
    (``Generation.Thermal.Gas`` matches that id and every
    ``Generation.Thermal.Gas.<subtype>``). Matching is case-insensitive so
    library ids and already-normalised tags both work.
    """
    if not tech_id or not pattern:
        return False
    tid = tech_id.lower()
    pat = pattern.lower()
    if "*" in pattern or "?" in pattern or "[" in pattern:
        return fnmatch.fnmatchcase(tid, pat)
    return tid == pat or tid.startswith(pat + ".")


def technology_tag_for_groups(tech_id: str, tech_groups: Optional[List[str]]) -> str:
    """Map a technology id onto its matching ``--tech-group`` key, or leave
    it unchanged when no pattern matches (no technology aggregation)."""
    if not tech_id:
        return tech_id
    for pattern in tech_groups or []:
        if technology_matches_group(tech_id, pattern):
            return tech_group_key(pattern)
    return tech_id


def is_phs_paired_generator(data: Dict[str, Any], gen_asset_id: str) -> bool:
    """True if this HydroGenerationUnit is a reversible pump-turbine
    (PHS), false for a plain (non-reversible) hydro turbine.

    Used to keep PHS-paired and plain-hydro-paired generators in
    separate aggregation groups even when a --tech-group pattern would
    otherwise put them in the same tag -- merging them would make it
    impossible for downstream
    consumers (tools/import_flexeco.py's PN_StorageDam vs. PN_StoragePump*
    classification, which determines PHS-ness from the generator a
    reservoir is paired with) to recover which of the aggregated
    generator's original members were actually reversible.

    Checks the same signals import_flexeco.py itself uses for PHS
    detection, so the two stay consistent: the asset's own
    legacy is_reversible attribute, its own hydro_machine_kind/
    maximum_pumping_power, and its paired reservoir's
    storage_technology_type / hasTechnology.
    """
    gen_ent = section_items(data, "HydroGenerationUnit").get(gen_asset_id, {})
    if bool(attr_value(gen_ent, "is_reversible")):
        return True
    kind = str(
        attr_value(gen_ent, "hydro_machine_kind")
        or attr_value(gen_ent, "machine_role")
        or ""
    ).lower()
    if kind == "reversible":
        return True
    if attr_value(gen_ent, "maximum_pumping_power") is not None:
        return True

    res_id = first_rel(gen_ent, "drawsFromHydraulicStorage")
    if res_id:
        res_ent = section_items(data, "HydraulicStorageUnit").get(res_id, {})
        tech = str(attr_value(res_ent, "storage_technology_type") or "").lower()
        if "phs" in tech or "pumped" in tech:
            return True
        hastech = str(first_rel(res_ent, "hasTechnology") or "").lower()
        if "phs" in hastech or "pumped" in hastech:
            return True

    return False


def is_phs_reservoir(data: Dict[str, Any], reservoir_id: str) -> bool:
    """True if this HydraulicStorageUnit is fed by at least one
    reversible (PHS) HydroGenerationUnit, false if every generator
    drawing from it is a plain (non-reversible) turbine.

    A reservoir has no PHS-ness of its own -- it's purely a function
    of which kind of generator draws from it (see
    is_phs_paired_generator). Without this, two reservoirs at the same
    bus that happen to share the same (or no) storage_technology_type
    -- one feeding a plain turbine, the other feeding a reversible
    pump-turbine -- would be merged into one aggregated reservoir by
    the storage-aggregation grouping key, even though the two
    generators drawing from them are correctly kept in separate
    aggregation groups: both aggregated generators' drawsFromHydraulicStorage
    would then point at the same merged reservoir, silently combining
    two physically different water bodies.
    """
    for gen_id, gen_ent in section_items(data, "HydroGenerationUnit").items():
        if first_rel(gen_ent, "drawsFromHydraulicStorage") == reservoir_id:
            if is_phs_paired_generator(data, gen_id):
                return True
    return False


def geo_region_id(level: str, code: str) -> str:
    prefix = "nuts3" if level in ("disaggregated", "nuts3") else level
    return f"{prefix}.{code}"


def build_outdir_name(level: str, selectors: List[str]) -> str:
    if not selectors:
        return f"aggregated_{level}"
    tag = "_".join(normalize_code(x) for x in selectors if normalize_code(x))
    return f"aggregated_{level}_{tag}"


# ── Scalar helpers ────────────────────────────────────────────────────────────

def safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except Exception:
        return None


def wavg(
    values: List[Optional[float]], weights: List[Optional[float]]
) -> Optional[float]:
    num = den = 0.0
    for v, w in zip(values, weights):
        if v is None or w is None or w == 0:
            continue
        num += v * w
        den += w
    return None if den == 0.0 else num / den


def normalize_sum_pos1(a: np.ndarray) -> np.ndarray:
    s = float(a.sum())
    return a if s == 0.0 else a / s


def normalize_sum_neg1(a: np.ndarray) -> np.ndarray:
    s = float(a.sum())
    return a if s == 0.0 else a / abs(s)


# ── CESDM entity accessors ────────────────────────────────────────────────────
# The YAML uses the flat EAR structure:
#   { "attributes": [{"id": ..., "value": ..., "unit": ...}, ...],
#     "relations":  [{"id": ..., "target_entity_ids": [...]}, ...] }

def get_attrs(entity: Dict[str, Any]) -> Dict[str, Tuple[Any, Optional[str]]]:
    out: Dict[str, Tuple[Any, Optional[str]]] = {}
    for a in entity.get("attributes", []) or []:
        if isinstance(a, dict):
            aid = a.get("id")
            if isinstance(aid, str):
                out[aid] = (a.get("value"), a.get("unit"))
    return out


_RELATION_ALIASES = {
    "locatedIn": "belongsToGeographicalRegion",
}


def get_rels(entity: Dict[str, Any]) -> Dict[str, List[str]]:
    """Return relation-id → targets, remapping legacy ids (e.g. locatedIn)."""
    out: Dict[str, List[str]] = {}
    for r in entity.get("relations", []) or []:
        if isinstance(r, dict):
            rid = r.get("id")
            targets = list(r.get("target_entity_ids", []) or [])
            if isinstance(rid, str):
                rid = _RELATION_ALIASES.get(rid, rid)
                existing = out.setdefault(rid, [])
                for t in targets:
                    if t not in existing:
                        existing.append(t)
    return out


def make_attr(aid: str, value: Any, unit: Optional[str] = None) -> Dict[str, Any]:
    d: Dict[str, Any] = {"id": aid, "value": value}
    if unit is not None:
        d["unit"] = unit
    return d


def make_rel(rid: str, targets: List[str]) -> Dict[str, Any]:
    return {"id": rid, "target_entity_ids": targets}


def id_tag(value: Any, fallback: str = "unknown") -> str:
    txt = str(value or fallback).strip().lower()
    txt = re.sub(r"[^a-z0-9]+", ".", txt).strip(".")
    return txt or fallback


def agg_asset_region_key(
    agg_bus: str,
    split_voltage: bool,
    *,
    identity: bool = False,
) -> Tuple[str, str]:
    """Return ``(region_token, voltage_suffix)`` for aggregated asset ids.

    Spatially aggregated buses are ``node.<rc>`` or ``node.<rc>.<kv>``.
    Disaggregated (identity) buses keep the original id, e.g.
    ``node.ch021.7205``. Using only ``parts[1]`` (``ch021``) for those
    would make every asset on every bus in the same NUTS3 share one id
    and silently overwrite each other -- so identity buses use the full
    trailing token ``ch021.7205`` instead.
    """
    parts = agg_bus.split(".")
    if identity:
        if len(parts) >= 2 and parts[0] == "node":
            return ".".join(parts[1:]), ""
        return id_tag(agg_bus), ""
    rc = parts[1] if len(parts) >= 2 else id_tag(agg_bus)
    sfx = f".{parts[2]}" if split_voltage and len(parts) >= 3 else ""
    return rc, sfx


def asset_technology_id(data: Dict[str, Any], asset_class: str, asset_id: str, fallback: str) -> str:
    """Raw hasTechnology / instanceOfType id (or fallback), before id_tag."""
    ent = section_items(data, asset_class).get(asset_id, {})
    tech = first_rel(ent, "hasTechnology") or first_rel(ent, "instanceOfType")
    return str(tech or fallback)


def asset_technology_tag(data: Dict[str, Any], asset_class: str, asset_id: str, fallback: str) -> str:
    return id_tag(asset_technology_id(data, asset_class, asset_id, fallback))

def aggregated_storage_id_for_asset(
    data: Dict[str, Any],
    asset_id: str,
    node_to_agg: Dict[str, str],
    a2n: Dict[str, str],
    sto_by_class: Dict[str, Dict[str, Dict[str, Any]]],
    split_voltage: bool,
    bus_country: Optional[Dict[str, str]] = None,
    tech_groups: Optional[List[str]] = None,
    reservoir_bus: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Return the aggregated storage/reservoir id for an original storage asset.

    This mirrors the storage aggregation naming logic (including the same
    ``--tech-group`` mapping and reservoir-via-generator bus fallback) and
    is used to preserve HydroGenerationUnit.drawsFromHydraulicStorage links
    after aggregation -- it must produce exactly the same id the main
    storage-aggregation loop does, or those links would point at an id
    that was never created.
    """
    bus_country = bus_country or {}
    tech_groups = tech_groups or []
    reservoir_bus = reservoir_bus or {}
    bus_id = a2n.get(asset_id) or reservoir_bus.get(asset_id)
    agg_bus = node_to_agg.get(bus_id or "")
    if not agg_bus:
        return None
    for asset_class, members in sto_by_class.items():
        ent = members.get(asset_id)
        if ent is None:
            continue
        tech = (
            attr_value(ent, "storage_technology_type")
            or asset_technology_id(data, asset_class, asset_id, asset_class)
        )
        tech = technology_tag_for_groups(str(tech), tech_groups)
        tag = id_tag(tech)
        if asset_class == STORAGE_RESERVOIR_CLASS:
            tag = id_tag(f"{tag}.{'phs' if is_phs_reservoir(data, asset_id) else 'nonphs'}")
        # Identity mapping (disaggregated country): bus_id == agg_bus.
        rc, sfx = agg_asset_region_key(
            agg_bus, split_voltage, identity=(bus_id == agg_bus),
        )
        return f"storage.{tag}.agg.{rc}{sfx}"
    return None

def generation_profile_relation_for_bucket(bucket: str) -> str:
    return "hasNaturalInflowProfile" if bucket == "hydro" else "hasAvailabilityProfile"

def allowed_agg_attrs_for_generation(bucket: str) -> set[str]:
    base = {"name", "nominal_power_capacity", "minimum_generation", "maximum_generation", "variable_operating_cost"}
    if bucket == "nonhydro":
        return base | {"generator_technology_type", "energy_conversion_efficiency", "annual_resource_potential", "dispatch_type", "maximum_ramp_rate_up", "maximum_ramp_rate_down"}
    if bucket == "hydro":
        return base | {"annual_resource_potential", "dispatch_type", "hydro_machine_kind", "turbine_efficiency", "maximum_pumping_power", "pumping_efficiency"}
    return base


def attr_float(entity: Dict[str, Any], aid: str) -> Optional[float]:
    v = get_attrs(entity).get(aid, (None, None))[0]
    return safe_float(v)


def attr_value(entity: Dict[str, Any], aid: str) -> Any:
    return get_attrs(entity).get(aid, (None, None))[0]


def attr_unit(entity: Dict[str, Any], aid: str) -> Optional[str]:
    return get_attrs(entity).get(aid, (None, None))[1]


def first_rel(entity: Dict[str, Any], rid: str) -> Optional[str]:
    xs = get_rels(entity).get(rid, [])
    return xs[0] if xs else None


# ── Node NUTS3 resolution ─────────────────────────────────────────────────────
# Spatial info lives on the ElectricalBus entity itself:
#   - attribute  latitude / longitude
#   - relation   belongsToGeographicalRegion → GeographicalRegion
#     (library: region.nuts3.DE111; legacy: nuts3.de111)
# Fallback: parse the entity id (pattern: node.<nuts3>.<kv>)

def _nuts3_code_from_region_id(region_id: str) -> Optional[str]:
    low = region_id.lower()
    if low.startswith("region.nuts3."):
        return region_id.split(".", 2)[2].lower()
    if low.startswith("nuts3."):
        return region_id.split(".", 1)[1].lower()
    return None


def node_nuts3_code(node_id: str, node_entity: Dict[str, Any]) -> Optional[str]:
    # Primary: belongsToGeographicalRegion pointing at a NUTS3 region
    for t in get_rels(node_entity).get("belongsToGeographicalRegion", []):
        if isinstance(t, str):
            code = _nuts3_code_from_region_id(t)
            if code:
                return code
    # Fallback: node id structure  node.<nuts3>.<kv>
    parts = node_id.split(".")
    if len(parts) >= 3 and parts[0] == "node":
        return parts[1].lower()
    return None


# ── Bus / topology helpers ─────────────────────────────────────────────────
# Every asset carries its own topology relations (atNode for single-port
# assets, fromNode/toNode for two-port ones) directly -- no separate
# TopologyView entity or reportsOn indirection exists in the current
# schema, so these read straight off the real asset entity.

def build_asset_to_node(
    data: Dict[str, Any], asset_classes: List[str],
) -> Dict[str, str]:
    """Return {asset_entity_id: bus_entity_id} for every single-port asset
    of the given classes, read directly from each asset's own atNode
    relation."""
    mapping: Dict[str, str] = {}
    for cls in asset_classes:
        for asset_id, ent in section_items(data, cls).items():
            node = first_rel(ent, "atNode")
            if node:
                mapping[asset_id] = node
    return mapping


def build_reservoir_bus_via_generator(
    data: Dict[str, Any], a2n: Dict[str, str],
) -> Dict[str, str]:
    """Return {reservoir_entity_id: bus_entity_id}.

    A reservoir (HydraulicStorageUnit) is never itself electrically
    connected -- only its paired HydroGenerationUnit is, via
    drawsFromHydraulicStorage. Without this, the storage-aggregation loop's
    plain ``a2n.get(reservoir_id)`` always returns None for every
    reservoir (it has no atNode of its own), and every reservoir/PHS
    storage asset is silently excluded from aggregation entirely --
    this reconstructs the bus a reservoir should be grouped by, via
    the generator that draws from it.
    """
    mapping: Dict[str, str] = {}
    for gen_id, gen_ent in section_items(data, "HydroGenerationUnit").items():
        res_id = first_rel(gen_ent, "drawsFromHydraulicStorage")
        bus_id = a2n.get(gen_id)
        if res_id and bus_id:
            mapping[res_id] = bus_id
    return mapping


def build_branch_endpoints(
    data: Dict[str, Any], asset_classes: List[str],
) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """Return {asset_entity_id: (from_bus_id, to_bus_id)} for every
    two-port asset of the given classes, read directly from each
    asset's own fromNode/toNode relations."""
    mapping: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    for cls in asset_classes:
        for asset_id, ent in section_items(data, cls).items():
            frm = first_rel(ent, "fromNode")
            to = first_rel(ent, "toNode")
            mapping[asset_id] = (frm, to)
    return mapping


# ── Profile relation helpers ──────────────────────────────────────────────────
# Relations: hasDemandProfile, hasAvailabilityProfile, hasNaturalInflowProfile → Profile id

def dispatch_profile_rel(view_entity: Dict[str, Any]) -> Optional[str]:
    """Return the Profile entity id linked from a dispatch view, if any."""
    rels = get_rels(view_entity)
    for rel_id in ("hasAvailabilityProfile", "hasDemandProfile", "hasNaturalInflowProfile", "hasNaturalInflowProfile"):
        t = rels.get(rel_id, [])
        if t:
            return t[0]
    return None


def profile_data_ref(
    profile_id: str, profiles_sec: Dict[str, Dict[str, Any]]
) -> Optional[str]:
    """Return the data_reference attribute of a Profile entity."""
    ent = profiles_sec.get(profile_id)
    if ent is None:
        return None
    return attr_value(ent, "data_reference")


# ── NUTS selector helpers ─────────────────────────────────────────────────────

def selector_matches_nuts3(nuts3_code: str, selectors: List[str]) -> bool:
    if not selectors:
        return True
    c = nuts3_code.lower()
    for s in selectors:
        s = normalize_code(s)
        if not s:
            continue
        if c[:2] == s if len(s) == 2 else c.startswith(s):
            return True
    return False


def collect_all_nuts3_codes(buses: Dict[str, Dict[str, Any]]) -> List[str]:
    return sorted({
        c for nid, ent in buses.items()
        if (c := node_nuts3_code(nid, ent))
    })


def validate_selectors(
    selectors: List[str], valid_nuts3: List[str]
) -> Tuple[List[str], List[str]]:
    valid, invalid = [], []
    for s in selectors:
        ss = normalize_code(s)
        found = any(
            (code[:2] == ss if len(ss) == 2 else code.startswith(ss))
            for code in valid_nuts3
        )
        (valid if found else invalid).append(ss)
    return valid, invalid


def summarize_kept_by_country(
    node_ids: List[str], buses: Dict[str, Dict[str, Any]]
) -> Counter:
    c: Counter = Counter()
    for nid in node_ids:
        n3 = node_nuts3_code(nid, buses.get(nid, {}))
        if n3:
            c[n3[:2].upper()] += 1
    return c


# ── YAML load ────────────────────────────────────────────────────────────────

def load_cesdm_model(schemas_dir: Path, yaml_path: Path) -> "CesdmModel":
    """Load schema and import model YAML via the CESDM toolbox."""
    model = build_model_from_yaml(str(schemas_dir))
    model.import_yaml_hierarchical(str(yaml_path))
    return model


def model_to_data(model: "CesdmModel") -> Dict[str, Any]:
    """
    Convert a CesdmModel into the flat EAR dict structure used internally
    by the aggregation logic:
        { class_name: { entity_id: {"attributes": [...], "relations": [...]} } }

    Every attribute and relation (dispatch, topology, power_flow, spatial,
    ...) lives directly on the one real asset entity in the current
    schema -- there is no separate view/section layer to reconstruct, and
    no "reportsOn" indirection to resolve. This is a direct,
    faithful copy of the model's own data.

    Relations are stored in entity.data as plain scalars (single target) or
    lists (multiple targets) keyed by relation name — not as dicts.
    We distinguish them from attributes by consulting the class schema.
    """
    data: Dict[str, Any] = {}
    for cls_name, entities in model.entities.items():
        # Build the set of relation names for this class (including inherited)
        cdef = model.classes.get(cls_name)
        _, rel_defs = model._collect_inherited_fields(cdef) if cdef else ({}, {})
        rel_names = set(rel_defs.keys())

        sec: Dict[str, Dict[str, Any]] = {}
        for eid, ent in entities.items():
            raw = getattr(ent, "data", {}) or {}
            attrs = []
            rels = []
            for key, val in raw.items():
                if key in rel_names:
                    # Relations: stored as a string or list of strings
                    if isinstance(val, list):
                        targets = [str(t) for t in val if t is not None]
                    elif val is not None:
                        targets = [str(val)]
                    else:
                        targets = []
                    if targets:
                        rels.append({"id": key, "target_entity_ids": targets})
                elif isinstance(val, dict) and "value" in val:
                    a = {"id": key, "value": val["value"]}
                    if "unit" in val:
                        a["unit"] = val["unit"]
                    attrs.append(a)
                elif val is not None:
                    attrs.append({"id": key, "value": val})
            sec[eid] = {"attributes": attrs, "relations": rels}
        data[cls_name] = sec
    for sec_name in SECTIONS:
        data.setdefault(sec_name, {})
    return data


def section_items(data: Dict[str, Any], sec: str) -> Dict[str, Dict[str, Any]]:
    x = data.get(sec, {})
    return x if isinstance(x, dict) else {}


def section_items_union(data: Dict[str, Any], classes: List[str]) -> Dict[str, Dict[str, Any]]:
    """Return the union of section_items() over several real classes,
    e.g. every concrete GenerationUnit subclass together -- used where
    the aggregation logic intentionally treats several subclasses as
    one input pool (see GENERATION_NONHYDRO_CLASSES)."""
    merged: Dict[str, Dict[str, Any]] = {}
    for cls in classes:
        merged.update(section_items(data, cls))
    return merged


def data_to_model(schemas_dir: Path, data: Dict[str, Any]) -> "CesdmModel":
    """
    Populate a fresh CesdmModel from the flat EAR aggregated-output dict,
    using only add_entity / add_attribute / add_relation (the three primitives).

    Every section in ``data`` is a real, current schema class -- the
    aggregation functions that build ``data`` write directly onto each
    real asset entity, with no separate view/section layer and no
    "reportsOn" indirection to resolve first.
    """
    model = build_model_from_yaml(str(schemas_dir))

    for cls_name, entities in data.items():
        if not isinstance(entities, dict):
            continue
        for eid, ent in entities.items():
            if not isinstance(ent, dict):
                continue
            try:
                model.add_entity(entity_class=cls_name, entity_id=eid)
            except Exception:
                continue  # unknown class in this schema version — skip
            for a in ent.get("attributes", []) or []:
                if not isinstance(a, dict):
                    continue
                aid = a.get("id")
                val = a.get("value")
                unit = a.get("unit")
                if aid is None or val is None:
                    continue
                try:
                    model.add_attribute(eid, aid, val, unit=unit)
                except Exception:
                    pass  # unknown attribute — skip silently
            for r in ent.get("relations", []) or []:
                if not isinstance(r, dict):
                    continue
                rid = r.get("id")
                targets = r.get("target_entity_ids", []) or []
                if not rid or not targets:
                    continue
                try:
                    # add_relation() validates the relation/target and sets
                    # the first one exactly as before.
                    model.add_relation(eid, rid, targets[0])
                except Exception:
                    continue  # unknown relation or target — skip silently
                if len(targets) > 1:
                    # add_relation() has no append semantics -- calling it
                    # again per additional target would silently overwrite
                    # (it always *sets*, and even stringifies a list rather
                    # than storing it), which is why a single aggregated
                    # generator drawing from more than one aggregated
                    # reservoir (after merging different reservoir-side
                    # technology groups together on the generator side --
                    # see CHANGELOG) used to lose every target but the
                    # last. Build the real list directly on the entity's
                    # own data instead, once the relation/first target is
                    # already known-valid from the call above.
                    entity_obj = model.entities.get(cls_name, {}).get(eid)
                    if entity_obj is not None and hasattr(entity_obj, "data"):
                        entity_obj.data[rid] = list(targets)

    return model


# ── HDF5 profile I/O ─────────────────────────────────────────────────────────
# Old format: /values (T×N matrix), /series_names (N strings)
# New format: /profiles/<profile_id>/values  (T-length float32)
#             /timestamps/<ts_id>/  (group attrs)

class ProfileMatrix:
    """
    Reads profile stores from HDF5 (legacy flat or CESDM) or Parquet (CESDM wide).

    Formats detected automatically:

    HDF5 — legacy flat (old PyPSA→CESDM exporter):
        /values          float matrix (T × N)
        /series_names    N byte-strings

    HDF5 — CESDM format (write_profiles_h5_cesdm / CesdmModel.export_hdf5):
        /profiles/<profile_id>/values    float array (T,)
        /timestamps/<ts_id>/             group

    Parquet — CESDM wide format (CesdmModel.export_parquet(wide=True)):
        <stem>_profiles.parquet          columns: timestamp_index, <profile_id>…
    """

    def __init__(self, path: Path):
        path = Path(path)
        if path.suffix.lower() == ".parquet" or "_profiles" in path.stem:
            self._fmt = "parquet"
            self._init_parquet(path)
        else:
            self.f = h5py.File(path, "r")
            self._fmt = self._detect_format()
            if self._fmt == "flat":
                self._init_flat()
            else:
                self._init_cesdm()

    def _init_parquet(self, path: Path) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError(
                "pyarrow is required to read Parquet profiles. "
                "Install with: pip install pyarrow"
            )
        # Accept both <stem>_profiles.parquet and bare <stem>.parquet
        if not path.exists():
            # try _profiles suffix
            alt = path.parent / (path.stem + "_profiles.parquet")
            if alt.exists():
                path = alt
        tbl = pq.read_table(str(path)).to_pydict()
        self._parquet_data: Dict[str, "np.ndarray"] = {}
        T = 0
        for col, arr in tbl.items():
            if col == "timestamp_index":
                T = len(arr)
                continue
            self._parquet_data[col] = np.asarray(arr, dtype=H5_READ_DTYPE)
            T = len(arr)
        self.T = T
        self.name_to_idx = {k: k for k in self._parquet_data}
        self.values = None

    def _detect_format(self) -> str:
        if "/values" in self.f and "/series_names" in self.f:
            return "flat"
        if "/profiles" in self.f:
            return "cesdm"
        raise ValueError(
            f"Unrecognised HDF5 layout — expected either "
            f"'/values' + '/series_names' (flat) or '/profiles/*' (CESDM). "
            f"Top-level keys: {list(self.f.keys())}"
        )

    def _init_flat(self) -> None:
        self.values = self.f["/values"]
        raw = self.f["/series_names"][:]
        names = [
            x.decode("utf-8", errors="replace") if isinstance(x, (bytes, bytearray))
            else str(x)
            for x in raw
        ]
        self.name_to_idx = {n: i for i, n in enumerate(names)}
        self.T = int(self.values.shape[0])

    def _init_cesdm(self) -> None:
        self.values = None  # not used in CESDM mode
        profiles_grp = self.f["/profiles"]
        # Determine T from the first available dataset
        T = 0
        for pid in profiles_grp:
            ds = profiles_grp[pid].get("values")
            if ds is not None:
                T = int(ds.shape[0])
                break
        self.T = T
        self.name_to_idx = {pid: pid for pid in profiles_grp}

    def col(self, name: str) -> Optional[np.ndarray]:
        if self._fmt == "parquet":
            return self._parquet_data.get(name)
        if self._fmt == "flat":
            idx = self.name_to_idx.get(name)
            if idx is None:
                return None
            return np.array(self.f["/values"][:, idx], dtype=H5_READ_DTYPE)
        # cesdm hdf5
        grp = self.f["/profiles"].get(name)
        if grp is None:
            return None
        ds = grp.get("values")
        if ds is None:
            return None
        return np.array(ds[:], dtype=H5_READ_DTYPE)

    def close(self) -> None:
        if self._fmt != "parquet":
            self.f.close()


def write_profiles_parquet(
    out_parquet_path: Path,
    series_dict: Dict[str, np.ndarray],
    T: int,
    ts_id: str = TIMESTAMP_SERIES_ID,
) -> None:
    """
    Write aggregated profiles in the CESDM Parquet wide format:
        <stem>_profiles.parquet    columns: timestamp_index, <profile_id>…
        <stem>_metadata.parquet   one row per entity attribute (TimestampSeries only)
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required to write Parquet profiles. "
            "Install with: pip install pyarrow"
        )
    out_parquet_path = Path(out_parquet_path)
    out_parquet_path.parent.mkdir(parents=True, exist_ok=True)

    stem = str(out_parquet_path.with_suffix(""))
    profiles_path = Path(stem + "_profiles.parquet")
    metadata_path = Path(stem + "_metadata.parquet")

    # Profiles wide table
    cols: Dict[str, Any] = {
        "timestamp_index": pa.array(np.arange(T, dtype=np.int64))
    }
    for pid, arr in series_dict.items():
        cols[pid] = pa.array(arr.astype(np.float64))
    pq.write_table(pa.table(cols), str(profiles_path), compression="snappy")

    # Minimal metadata table (just the TimestampSeries id)
    pq.write_table(
        pa.table({
            "entity_class": pa.array(["TimestampSeries"], pa.string()),
            "entity_id":    pa.array([ts_id],            pa.string()),
            "attribute":    pa.array(["resolution"],     pa.string()),
            "value":        pa.array(["PT1H"],           pa.string()),
        }),
        str(metadata_path),
        compression="snappy",
    )


def write_profiles_h5_cesdm(
    out_h5_path: Path,
    series_dict: Dict[str, np.ndarray],
    T: int,
    ts_id: str = TIMESTAMP_SERIES_ID,
) -> None:
    """
    Write profiles in the CESDM HDF5 layout:
      /timestamps/<ts_id>/   (empty group; metadata is in the YAML Profile entity)
      /profiles/<profile_id>/values   (float32 array, shape (T,))
    """
    out_h5_path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_h5_path, "w") as f:
        f.create_group(f"timestamps/{ts_id}")
        for profile_id, arr in series_dict.items():
            grp = f.require_group(f"profiles/{profile_id}")
            grp.create_dataset(
                "values",
                data=arr.astype(H5_WRITE_DTYPE),
                compression="gzip",
                compression_opts=4,
            )


# ── CESDM entity builders ─────────────────────────────────────────────────────

def make_profile_entity(
    profile_id: str,
    profile_type: str,
    profile_unit: str,
    h5_path_relative: str,
    ts_id: str = TIMESTAMP_SERIES_ID,
) -> Dict[str, Any]:
    """Build a CESDM Profile entity dict."""
    return {
        "attributes": [
            make_attr("name", profile_id),
            make_attr("profile_type", profile_type),
            make_attr("profile_unit", profile_unit),
            make_attr("data_reference", f"{h5_path_relative}:/profiles/{profile_id}/values"),
        ],
        "relations": [make_rel("hasTimestampSeries", [ts_id])],
    }


def make_electrical_bus(
    bus_id: str,
    name: str,
    lat: Optional[float],
    lon: Optional[float],
    kv: Optional[float],
    region_id: str,
    domain_id: str = DOMAIN_ELECTRICITY_ID,
) -> Dict[str, Any]:
    """Return the ElectricalBus entity dict, coordinates included directly
    -- ElectricalBus (a NetworkNode) carries latitude/longitude itself in
    the current schema (its own "spatial" group), so there is no separate
    location entity to build or link."""
    attrs = [make_attr("name", name)]
    if kv is not None:
        attrs.append(make_attr("nominal_voltage", kv, "kV"))
    if lat is not None:
        attrs.append(make_attr("latitude", lat, "decimal degrees"))
    if lon is not None:
        attrs.append(make_attr("longitude", lon, "decimal degrees"))
    return {
        "attributes": attrs,
        "relations": [
            make_rel("belongsToGeographicalRegion",              [region_id]),
            make_rel("belongsToCarrierDomain", [domain_id]),
        ],
    }


# ── Disaggregated subset (no aggregation, just filtering) ────────────────────

def build_subset_disaggregated(
    data: Dict[str, Any],
    kept_buses: Dict[str, Dict[str, Any]],
    pm: Optional[ProfileMatrix],
    log,
) -> Tuple[Dict[str, Any], Dict[str, int]]:

    kept_bus_ids = set(kept_buses.keys())
    drop = Counter()

    a2n = build_asset_to_node(data, GENERATION_ASSET_CLASSES + ["DemandUnit"] + STORAGE_ASSET_CLASSES)
    a2br = build_branch_endpoints(data, BRANCH_ASSET_CLASSES)

    def _keep_asset(asset_id: str) -> bool:
        n = a2n.get(asset_id)
        return n in kept_bus_ids if n else False

    def _keep_branch(asset_id: str) -> bool:
        frm, to = a2br.get(asset_id, (None, None))
        return frm in kept_bus_ids and to in kept_bus_ids

    out_gen_assets_by_class = {
        cls: {aid: e for aid, e in section_items(data, cls).items() if _keep_asset(aid)}
        for cls in GENERATION_ASSET_CLASSES
    }
    out_gens = section_items_union(out_gen_assets_by_class, list(out_gen_assets_by_class))
    out_dem = {aid: e for aid, e in section_items(data, "DemandUnit").items()
               if _keep_asset(aid) or (drop.__setitem__("dem_outside", drop.get("dem_outside", 0)+1) and False)}

    # Reservoirs have no atNode of their own -- only their paired
    # HydroGenerationUnit does -- so a reservoir is kept whenever the
    # generator that draws from it is kept.
    kept_gen_ids = {aid for sec in out_gen_assets_by_class.values() for aid in sec}
    kept_reservoir_ids = {
        first_rel(section_items(data, "HydroGenerationUnit")[gid], "drawsFromHydraulicStorage")
        for gid in out_gen_assets_by_class.get("HydroGenerationUnit", {})
    } - {None}

    def _keep_storage(cls: str, aid: str) -> bool:
        if cls == "HydraulicStorageUnit":
            return aid in kept_reservoir_ids
        return _keep_asset(aid)

    out_sto_assets_by_class = {
        cls: {aid: e for aid, e in section_items(data, cls).items() if _keep_storage(cls, aid)}
        for cls in STORAGE_ASSET_CLASSES
    }
    out_sto = section_items_union(out_sto_assets_by_class, list(out_sto_assets_by_class))
    out_txl = {aid: e for aid, e in section_items(data, "TransmissionLine").items()
               if _keep_branch(aid) or (drop.__setitem__("line_outside", drop.get("line_outside", 0)+1) and False)}
    out_ico = {aid: e for aid, e in section_items(data, "GenericInterconnector").items()
               if _keep_branch(aid) or (drop.__setitem__("ico_outside", drop.get("ico_outside", 0)+1) and False)}
    out_hvdc = {aid: e for aid, e in section_items(data, "HVDCLink").items()
                if _keep_branch(aid) or (drop.__setitem__("hvdc_outside", drop.get("hvdc_outside", 0)+1) and False)}
    out_trf = {aid: e for aid, e in section_items(data, "Transformer").items()
               if _keep_branch(aid) or (drop.__setitem__("trf_outside", drop.get("trf_outside", 0)+1) and False)}

    # Geographic regions referenced by kept buses
    geo_ids = {
        t for ent in kept_buses.values()
        for t in get_rels(ent).get("belongsToGeographicalRegion", [])
    }
    out_geo = {}
    geo_sec = section_items(data, "GeographicalRegion")
    for gid in sorted(geo_ids):
        out_geo[gid] = geo_sec.get(gid) or {"attributes": [make_attr("name", gid)], "relations": []}

    # Copy Profile entities for kept assets
    profiles_sec = section_items(data, "Profile")
    all_kept_with_profiles = {**out_gens, **out_dem, **out_sto}
    kept_profile_ids = {
        pid
        for ent in all_kept_with_profiles.values()
        if (pid := dispatch_profile_rel(ent))
    }
    out_profiles = {pid: profiles_sec[pid] for pid in kept_profile_ids if pid in profiles_sec}

    # Copy HDF5 profiles
    series_dict: Dict[str, np.ndarray] = {}
    if pm is not None:
        for pid, pent in out_profiles.items():
            dref = attr_value(pent, "data_reference")
            if isinstance(dref, str):
                # data_reference format: "file.h5:/profiles/<id>/values"
                # resolve the series name from the old h5 index
                col = pm.col(pid) or pm.col(dref.split(":")[-1].lstrip("/"))
                if col is not None:
                    series_dict[pid] = col.astype(H5_WRITE_DTYPE)
                else:
                    log(f"[WARN] missing profile in source h5: {pid}")

    for k, v in drop.items():
        log(f"dropped {k}={v}")

    out_obj: Dict[str, Any] = {
        "Carrier":              section_items(data, "Carrier"),
        "NaturalResource":            section_items(data, "NaturalResource"),
        "CarrierDomain":              section_items(data, "CarrierDomain"),
        "GeographicalRegion":         out_geo,
        "TimestampSeries":            section_items(data, "TimestampSeries"),
        "Profile":                    out_profiles,
        "ElectricalBus":              kept_buses,
        **out_gen_assets_by_class,
        "DemandUnit":                 out_dem,
        **out_sto_assets_by_class,
        "TransmissionLine":           out_txl,
        "GenericInterconnector":             out_ico,
        "HVDCLink":                   out_hvdc,
        "Transformer":                out_trf,
    }

    stats = {
        "buses":  len(kept_buses),
        "gens":   len(out_gens),
        "loads":  len(out_dem),
        "stors":  len(out_sto),
        "lines":  len(out_txl),
        "icos":   len(out_ico),
        "trafos": len(out_trf),
    }
    return out_obj, series_dict, stats


# ── Aggregation ───────────────────────────────────────────────────────────────

# ── Per-country sanity check: disaggregated vs. aggregated totals ────────────
# Aggregation should conserve totals -- summing capacities/energies across
# many small assets and summing them across few large ones must agree,
# country by country. This is a real correctness safety net: several of the
# aggregation bugs found and fixed in this tool (a duplicated-string
# exclusion that silently dropped availability-profile relations, two
# reservoirs merging into one because nothing distinguished PHS-paired from
# turbine-paired) would all have shown up immediately here, as a totals
# mismatch, rather than needing to be found downstream by inspection.

def _bus_country_for_asset(
    asset_id: str,
    asset_class: str,
    data: Dict[str, Any],
    bus_to_country: Dict[str, str],
    a2n: Dict[str, str],
    reservoir_bus: Dict[str, str],
) -> Optional[str]:
    if asset_class == STORAGE_RESERVOIR_CLASS:
        bus_id = a2n.get(asset_id) or reservoir_bus.get(asset_id)
    else:
        bus_id = a2n.get(asset_id)
    return bus_to_country.get(bus_id or "")


def summarize_by_country(
    data: Dict[str, Any],
    bus_to_country: Dict[str, str],
    a2n: Dict[str, str],
    reservoir_bus: Dict[str, str],
) -> Dict[str, Dict[str, Any]]:
    """Return, per country, the conserved totals this tool's aggregation
    must not change: dispatchable generation capacity by technology,
    non-dispatchable generation capacity and annual_resource_potential
    by technology, hydro turbine vs. reversible (PHS) discharge/charge
    capacity, battery-style StorageUnit energy/charge/discharge capacity
    by technology, reservoir capacity and natural inflow, and demand.

    Works identically on the raw, disaggregated ``data`` and on
    ``aggregate_subset()``'s own aggregated ``out_obj`` -- both use the
    same real-class shape, so the same function produces directly
    comparable totals for both.
    """
    def _country_totals() -> Dict[str, Any]:
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

    totals: Dict[str, Dict[str, Any]] = defaultdict(_country_totals)

    for asset_class in GENERATION_ASSET_CLASSES:
        for asset_id, ent in section_items(data, asset_class).items():
            country = _bus_country_for_asset(asset_id, asset_class, data, bus_to_country, a2n, reservoir_bus)
            if not country:
                continue
            cap = attr_float(ent, "nominal_power_capacity") or 0.0
            tech = id_tag(attr_value(ent, "generator_technology_type") or asset_technology_tag(data, asset_class, asset_id, asset_class))
            dispatch_type = str(attr_value(ent, "dispatch_type") or "").lower()

            if asset_class == GENERATION_HYDRO_CLASS:
                if is_phs_paired_generator(data, asset_id):
                    totals[country]["hydro_reversible_discharge_capacity_mw"] += cap
                    totals[country]["hydro_reversible_charge_capacity_mw"] += attr_float(ent, "maximum_pumping_power") or 0.0
                else:
                    totals[country]["hydro_turbine_discharge_capacity_mw"] += cap
                # Hydro's own resource potential (run-of-river inflow
                # expressed as an energy potential) still belongs in the
                # non-dispatchable resource-potential total below.
                if dispatch_type != "dispatchable":
                    totals[country]["nondispatchable_annual_resource_potential_mwh"][tech] += attr_float(ent, "annual_resource_potential") or 0.0
                continue

            if dispatch_type == "nondispatchable":
                totals[country]["nondispatchable_capacity_mw"][tech] += cap
                totals[country]["nondispatchable_annual_resource_potential_mwh"][tech] += attr_float(ent, "annual_resource_potential") or 0.0
            else:
                totals[country]["dispatchable_capacity_mw"][tech] += cap

    for asset_id, ent in section_items(data, STORAGE_NONRESERVOIR_CLASS).items():
        country = _bus_country_for_asset(
            asset_id, STORAGE_NONRESERVOIR_CLASS, data, bus_to_country, a2n, reservoir_bus,
        )
        if not country:
            continue
        tech = id_tag(
            attr_value(ent, "storage_technology_type")
            or asset_technology_tag(data, STORAGE_NONRESERVOIR_CLASS, asset_id, STORAGE_NONRESERVOIR_CLASS)
        )
        totals[country]["storage_energy_capacity_mwh"][tech] += (
            attr_float(ent, "energy_storage_capacity") or 0.0
        )
        totals[country]["storage_discharge_capacity_mw"][tech] += (
            attr_float(ent, "nominal_power_capacity") or 0.0
        )
        totals[country]["storage_charge_capacity_mw"][tech] += (
            attr_float(ent, "maximum_charging_power") or 0.0
        )

    for asset_id, ent in section_items(data, STORAGE_RESERVOIR_CLASS).items():
        country = _bus_country_for_asset(asset_id, STORAGE_RESERVOIR_CLASS, data, bus_to_country, a2n, reservoir_bus)
        if not country:
            continue
        totals[country]["reservoir_capacity_mwh"] += attr_float(ent, "energy_storage_capacity") or 0.0
        totals[country]["reservoir_inflow_mwh"] += attr_float(ent, "annual_natural_inflow_energy") or 0.0

    for asset_id, ent in section_items(data, "DemandUnit").items():
        country = _bus_country_for_asset(asset_id, "DemandUnit", data, bus_to_country, a2n, reservoir_bus)
        if not country:
            continue
        totals[country]["demand_annual_energy_mwh"] += attr_float(ent, "annual_energy_demand") or 0.0

    return {c: dict(t) for c, t in totals.items()}


def write_sanity_check_report(
    outdir: Path,
    disagg_totals: Dict[str, Dict[str, Any]],
    agg_totals: Dict[str, Dict[str, Any]],
    log,
    rel_tol: float = 1e-6,
) -> None:
    """Write outdir/sanity_check_by_country.txt comparing pre- and
    post-aggregation totals, and log a [WARN] for any category where
    they disagree beyond floating-point rounding -- aggregation must
    conserve every one of these totals exactly; a mismatch here is a
    real aggregation bug, not a rounding artefact."""
    lines: List[str] = [
        "Per-country sanity check: disaggregated vs. aggregated totals.",
        "Aggregation must conserve every value below (summing many small",
        "assets vs. summing few large ones must agree) -- a mismatch",
        "beyond floating-point rounding indicates a real aggregation bug.",
        "",
    ]
    scalar_keys = [
        "hydro_turbine_discharge_capacity_mw",
        "hydro_reversible_discharge_capacity_mw",
        "hydro_reversible_charge_capacity_mw",
        "reservoir_capacity_mwh",
        "reservoir_inflow_mwh",
        "demand_annual_energy_mwh",
    ]
    dict_keys = [
        "dispatchable_capacity_mw",
        "nondispatchable_capacity_mw",
        "nondispatchable_annual_resource_potential_mwh",
        "storage_energy_capacity_mwh",
        "storage_discharge_capacity_mw",
        "storage_charge_capacity_mw",
    ]

    all_countries = sorted(set(disagg_totals) | set(agg_totals))
    any_mismatch = False

    for country in all_countries:
        d = disagg_totals.get(country, {})
        a = agg_totals.get(country, {})
        lines.append(f"=== {country.upper()} ===")

        for key in scalar_keys:
            dv, av = float(d.get(key, 0.0)), float(a.get(key, 0.0))
            ok = math.isclose(dv, av, rel_tol=rel_tol, abs_tol=1e-6)
            marker = "OK" if ok else "MISMATCH"
            lines.append(f"  {key:48s} disagg={dv:>14,.2f}  agg={av:>14,.2f}  [{marker}]")
            if not ok:
                any_mismatch = True
                log(f"[WARN] sanity check mismatch: {country} {key} "
                    f"disaggregated={dv:.4f} vs. aggregated={av:.4f}")

        for key in dict_keys:
            d_by_tech: Dict[str, float] = d.get(key, {})
            a_by_tech: Dict[str, float] = a.get(key, {})
            all_techs = sorted(set(d_by_tech) | set(a_by_tech))
            if not all_techs:
                continue
            lines.append(f"  {key}:")
            for tech in all_techs:
                dv, av = float(d_by_tech.get(tech, 0.0)), float(a_by_tech.get(tech, 0.0))
                ok = math.isclose(dv, av, rel_tol=rel_tol, abs_tol=1e-6)
                marker = "OK" if ok else "MISMATCH"
                lines.append(f"    {tech:44s} disagg={dv:>14,.2f}  agg={av:>14,.2f}  [{marker}]")
                if not ok:
                    any_mismatch = True
                    log(f"[WARN] sanity check mismatch: {country} {key}[{tech}] "
                        f"disaggregated={dv:.4f} vs. aggregated={av:.4f}")
        lines.append("")

    lines.append("All totals conserved." if not any_mismatch else "MISMATCHES FOUND -- see [WARN] lines above / in the run log.")
    (outdir / "sanity_check_by_country.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote sanity check={outdir / 'sanity_check_by_country.txt'}"
        f" ({'all totals conserved' if not any_mismatch else 'MISMATCHES FOUND'})")


def aggregate_subset(
    data: Dict[str, Any],
    kept_buses: Dict[str, Dict[str, Any]],
    level: str,
    split_voltage: bool,
    pm: Optional[ProfileMatrix],
    log,
    h5_path_relative: str = "profiles/profiles.h5",
    round_kv: int = 1,
    level_by_country: Optional[Dict[str, str]] = None,
    tech_groups: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], Dict[str, np.ndarray], Dict[str, int]]:

    level_by_country = level_by_country or {}
    tech_groups = normalize_tech_groups(tech_groups)

    kept_bus_ids = set(kept_buses.keys())

    profiles_sec = section_items(data, "Profile")

    a2n = build_asset_to_node(
        data, GENERATION_ASSET_CLASSES + ["DemandUnit", STORAGE_NONRESERVOIR_CLASS],
    )
    reservoir_bus = build_reservoir_bus_via_generator(data, a2n)
    a2br = build_branch_endpoints(data, BRANCH_ASSET_CLASSES)

    # ── Map each kept bus to its aggregated bus id ─────────────────────────────
    # Countries at level ``disaggregated`` keep each original bus id (no spatial
    # merge). Other levels merge buses that share the truncated region key.
    node_to_agg: Dict[str, str] = {}
    agg_members: Dict[str, List[str]] = defaultdict(list)
    agg_id_level: Dict[str, str] = {}   # agg_id -> the spatial level actually used to produce it
    region_codes: set = set()
    region_code_level: Dict[str, str] = {}   # region code -> the level that produced it
    bus_country: Dict[str, str] = {}   # original bus id -> country, for per-country tech depth below
    disagg_geo_ids: set = set()        # GeographicalRegion ids to copy for disaggregated buses

    for bid, ent in kept_buses.items():
        n3 = node_nuts3_code(bid, ent)
        if not n3:
            continue
        country = country_of_nuts3(n3)
        bus_country[bid] = country
        effective_level = resolve_level_for_country(country, level_by_country, level)
        if effective_level == "disaggregated":
            # True passthrough: one output bus per input bus (not nuts3 merge).
            agg_id = bid
            for gid in get_rels(ent).get("belongsToGeographicalRegion", []) or []:
                if isinstance(gid, str) and gid:
                    disagg_geo_ids.add(gid)
        else:
            rc = nuts3_to_level(n3, effective_level)
            region_codes.add(rc)
            region_code_level[rc] = effective_level
            kv = attr_float(ent, "nominal_voltage")
            if split_voltage and kv is not None:
                kvn = int(round(kv, round_kv))
                agg_id = f"node.{rc}.{kvn}"
            else:
                agg_id = f"node.{rc}"
        node_to_agg[bid] = agg_id
        agg_members[agg_id].append(bid)
        agg_id_level[agg_id] = effective_level

    series_dict:      Dict[str, np.ndarray] = {}
    out_profiles:     Dict[str, Dict[str, Any]] = {}
    out_buses:        Dict[str, Dict[str, Any]] = {}
    out_gens:         Dict[str, Dict[str, Any]] = {}
    out_dem:          Dict[str, Dict[str, Any]] = {}
    out_sto:          Dict[str, Dict[str, Any]] = {}
    out_lines:        Dict[str, Dict[str, Any]] = {}
    out_icos:         Dict[str, Dict[str, Any]] = {}
    out_hvdcs:        Dict[str, Dict[str, Any]] = {}
    out_trafos:       Dict[str, Dict[str, Any]] = {}

    def _is_disagg_bus(bus_id: Optional[str]) -> bool:
        if not bus_id:
            return False
        return agg_id_level.get(node_to_agg.get(bus_id, ""), "") == "disaggregated"

    def _carry_profile_entity(ent: Dict[str, Any]) -> None:
        """Copy a Profile entity (+ HDF5 column) for a passthrough asset."""
        pid = dispatch_profile_rel(ent)
        if not pid or pid in out_profiles:
            return
        if pid not in profiles_sec:
            return
        out_profiles[pid] = copy.deepcopy(profiles_sec[pid])
        if pm is not None:
            col = pm.col(pid)
            if col is not None:
                series_dict[pid] = col.astype(H5_WRITE_DTYPE)

    # ── Aggregated ElectricalBus entities ─────────────────────────────────────
    # Coordinates are read directly off each member bus -- ElectricalBus
    # carries latitude/longitude itself, no separate location entity.
    for agg_id, members in agg_members.items():
        if agg_id_level.get(agg_id) == "disaggregated":
            # Identity mapping: preserve the original bus entity verbatim.
            src = kept_buses[members[0]]
            out_buses[agg_id] = copy.deepcopy(src)
            continue

        parts = agg_id.split(".")
        rc = parts[1]
        kv_out = float(parts[2]) if split_voltage and len(parts) >= 3 else None

        lats = [attr_float(kept_buses[m], "latitude") for m in members]
        lons = [attr_float(kept_buses[m], "longitude") for m in members]
        kvs  = [attr_float(kept_buses[m], "nominal_voltage") for m in members]

        lat_vals = [x for x in lats if x is not None]
        lon_vals = [x for x in lons if x is not None]

        out_buses[agg_id] = make_electrical_bus(
            bus_id    = agg_id,
            name      = agg_id,
            lat       = float(sum(lat_vals) / len(lat_vals)) if lat_vals else None,
            lon       = float(sum(lon_vals) / len(lon_vals)) if lon_vals else None,
            kv        = kv_out if kv_out is not None
                        else (max(x for x in kvs if x is not None) if any(x is not None for x in kvs) else None),
            region_id = geo_region_id(agg_id_level.get(agg_id, level), rc),
        )

    # ── Helper: load profile array from the source h5 via an asset's own
    # profile-referencing relation (hasAvailabilityProfile, hasDemandProfile,
    # hasNaturalInflowProfile, hasNaturalInflowProfile -- whichever it has) ──
    def load_profile(ent: Dict[str, Any]) -> Optional[np.ndarray]:
        pid = dispatch_profile_rel(ent)
        if pid is None or pm is None:
            return None
        col = pm.col(pid)
        return col.astype(np.float64) if col is not None else None

    # ── Aggregated DemandUnit ──────────────────────────────────────────────────
    load_groups: Dict[str, List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)
    for asset_id, ent in section_items(data, "DemandUnit").items():
        bus_id = a2n.get(asset_id)
        if bus_id not in node_to_agg:
            continue
        if _is_disagg_bus(bus_id):
            out_dem[asset_id] = copy.deepcopy(ent)
            _carry_profile_entity(ent)
            continue
        load_groups[node_to_agg[bus_id]].append((asset_id, ent))

    for agg_bus, members in load_groups.items():
        rc, sfx = agg_asset_region_key(agg_bus, split_voltage, identity=False)
        lid = f"demand.agg.{rc}{sfx}"

        ann_sum = sum((attr_float(e, "annual_energy_demand") or 0.0) for _, e in members)
        profs = [
            (arr, attr_float(e, "annual_energy_demand") or 0.0)
            for _, e in members
            if (arr := load_profile(e)) is not None
        ]

        dem_attrs = [
            make_attr("name", lid),
            make_attr("annual_energy_demand", float(ann_sum), "MWh/year"),
        ]
        dem_rels = [make_rel("atNode", [agg_bus])]

        if profs:
            arrays, weights = zip(*profs)
            W = np.array(weights, dtype=np.float64)
            if W.sum() > 0:
                raw = (np.vstack(arrays).T * W).T.sum(axis=0)
                agg_arr = normalize_sum_neg1(raw).astype(H5_WRITE_DTYPE)
                new_pid = f"profile.demand.{rc}{sfx}"
                series_dict[new_pid] = agg_arr
                out_profiles[new_pid] = make_profile_entity(
                    new_pid, "as_normalized_annual_energy", "pu",
                    h5_path_relative,
                )
                dem_rels.append(make_rel("hasDemandProfile", [new_pid]))

        out_dem[lid] = {"attributes": dem_attrs, "relations": dem_rels}

    # ── Aggregated generation ──────────────────────────────────────────────────
    # Non-hydro generation subclasses (GenerationUnit, WindGenerationUnit,
    # SolarGenerationUnit, ThermalGenerationUnit) are intentionally grouped
    # under one shared "nonhydro" bucket, writing out as plain GenerationUnit
    # -- they share the same dispatch attribute shape, and this tool has
    # always merged them this way. Hydro gets its own bucket, because of its
    # reservoir-pairing logic below.
    out_gen_assets_by_class: Dict[str, Dict[str, Dict[str, Any]]] = {
        cls: {} for cls in GENERATION_BUCKET_OUTPUT_CLASS.values()
    }

    # Reservoir-coupled hydro generators whose "no profile of its own"
    # status can't be judged yet -- see the deferred check after the
    # storage/reservoir aggregation loop below.
    pending_reservoir_coupled_hydro_checks: List[Tuple[str, List[str], int, List[str]]] = []

    gen_groups: Dict[Tuple[str, str, str], List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)
    for asset_class in GENERATION_ASSET_CLASSES:
        bucket = generation_bucket_for_class(asset_class)
        output_class = GENERATION_BUCKET_OUTPUT_CLASS[bucket]
        for asset_id, ent in section_items(data, asset_class).items():
            bus_id = a2n.get(asset_id)
            if bus_id not in node_to_agg:
                continue
            if _is_disagg_bus(bus_id):
                tech_raw = (
                    attr_value(ent, "generator_technology_type")
                    or asset_technology_id(data, asset_class, asset_id, asset_class)
                )
                # Passthrough unless a --tech-group pattern actually matches:
                # technology merge is orthogonal to spatial level, but assets
                # that are not being tech-merged must keep their original ids
                # (and must not share a colliding gen.*.agg.<nuts3> id with
                # every other bus in the same NUTS3).
                if not any(
                    technology_matches_group(str(tech_raw), p) for p in (tech_groups or [])
                ):
                    out_gen_assets_by_class[output_class][asset_id] = copy.deepcopy(ent)
                    _carry_profile_entity(ent)
                    continue
            tech = (
                attr_value(ent, "generator_technology_type")
                or asset_technology_id(data, asset_class, asset_id, asset_class)
            )
            tech = technology_tag_for_groups(str(tech), tech_groups)
            tag = id_tag(tech)
            if bucket == "hydro":
                # PHS-paired and plain-hydro-paired generators must never
                # merge, even when a --tech-group pattern would put them
                # in the same tag: they draw from structurally different
                # reservoirs (reversible pump-turbine vs. simple turbine),
                # and downstream tools (tools/import_flexeco.py's
                # PN_StorageDam/PN_StoragePump classification) determine
                # PHS-ness from the generator a reservoir is paired with
                # -- merge them and that distinction can no longer be
                # recovered afterward.
                tag = id_tag(f"{tag}.{'phs' if is_phs_paired_generator(data, asset_id) else 'nonphs'}")
            gen_groups[(bucket, node_to_agg[bus_id], tag)].append((asset_id, ent))

    for (bucket, agg_bus, tech), members in gen_groups.items():
        output_class = GENERATION_BUCKET_OUTPUT_CLASS[bucket]
        rc, sfx = agg_asset_region_key(
            agg_bus, split_voltage,
            identity=(agg_id_level.get(agg_bus) == "disaggregated"),
        )
        gid = f"gen.{tech}.agg.{rc}{sfx}"

        caps = [attr_float(e, "nominal_power_capacity") for _, e in members]
        anns = [attr_float(e, "annual_resource_potential") for _, e in members]
        effs = [attr_float(e, "energy_conversion_efficiency") for _, e in members]
        vops = [attr_float(e, "variable_operating_cost") for _, e in members]
        max_pump = [attr_float(e, "maximum_pumping_power") for _, e in members]
        pump_effs = [attr_float(e, "pumping_efficiency") for _, e in members]
        turb_effs = [attr_float(e, "turbine_efficiency") for _, e in members]

        cap_sum = sum(x or 0.0 for x in caps)
        ann_sum = sum(x or 0.0 for x in anns)
        eff_avg = wavg(effs, caps)
        vop_avg = wavg(vops, caps)
        pump_sum = sum(x or 0.0 for x in max_pump)
        pump_eff_avg = wavg(pump_effs, max_pump if any(max_pump) else caps)
        turb_eff_avg = wavg(turb_effs, caps)
        energy_shape = ann_sum > 0
        allowed = allowed_agg_attrs_for_generation(bucket)

        gen_attrs = [make_attr("name", gid)]
        if "generator_technology_type" in allowed:
            gen_attrs.append(make_attr("generator_technology_type", tech))
        if "nominal_power_capacity" in allowed:
            gen_attrs.append(make_attr("nominal_power_capacity", float(cap_sum), "MW"))
        if eff_avg is not None and "energy_conversion_efficiency" in allowed:
            gen_attrs.append(make_attr("energy_conversion_efficiency", float(eff_avg)))
        if vop_avg is not None and "variable_operating_cost" in allowed:
            gen_attrs.append(make_attr("variable_operating_cost", float(vop_avg), "MU/MWh"))
        if ann_sum > 0 and "annual_resource_potential" in allowed:
            gen_attrs.append(make_attr("annual_resource_potential", float(ann_sum), "MWh/year"))
        if pump_sum > 0 and "maximum_pumping_power" in allowed:
            gen_attrs.append(make_attr("maximum_pumping_power", float(pump_sum), "MW"))
        if pump_eff_avg is not None and "pumping_efficiency" in allowed:
            gen_attrs.append(make_attr("pumping_efficiency", float(pump_eff_avg)))
        if turb_eff_avg is not None and "turbine_efficiency" in allowed:
            gen_attrs.append(make_attr("turbine_efficiency", float(turb_eff_avg)))
        # For hydro, preserve the dominant/non-default machine role when present.
        if "hydro_machine_kind" in allowed:
            roles = [attr_value(e, "hydro_machine_kind") for _, e in members if attr_value(e, "hydro_machine_kind")]
            if roles:
                gen_attrs.append(make_attr("hydro_machine_kind", Counter(roles).most_common(1)[0][0]))
        # dispatch_type distinguishes dispatchable from non-dispatchable
        # generation downstream (tools/import_flexeco.py's PN_GenDispatchable
        # vs. PN_GenNonDispatchable classification) -- preserve the
        # dominant value among merged members, the same way hydro_machine_kind is.
        if "dispatch_type" in allowed:
            dtypes = [attr_value(e, "dispatch_type") for _, e in members if attr_value(e, "dispatch_type")]
            if dtypes:
                gen_attrs.append(make_attr("dispatch_type", Counter(dtypes).most_common(1)[0][0]))

        gen_rels = [make_rel("atNode", [agg_bus])]

        profs = []
        weights = []
        for _, e in members:
            arr = load_profile(e)
            if arr is None:
                continue
            w = float((attr_float(e, "annual_resource_potential") if energy_shape else attr_float(e, "nominal_power_capacity")) or 0.0)
            if w > 0:
                profs.append(arr)
                weights.append(w)

        if profs and sum(weights) > 0:
            W = np.array(weights, dtype=np.float64)
            raw = (np.vstack(profs).T * W).T.sum(axis=0)
            agg_arr = (normalize_sum_pos1(raw) if energy_shape else (raw / W.sum())).astype(H5_WRITE_DTYPE)
            new_pid = f"profile.gen.{tech}.{rc}{sfx}"
            series_dict[new_pid] = agg_arr
            out_profiles[new_pid] = make_profile_entity(
                new_pid,
                "as_normalized_annual_energy" if energy_shape else "as_capacity_factor",
                "pu", h5_path_relative,
            )
            gen_rels.append(make_rel(generation_profile_relation_for_bucket(bucket), [new_pid]))
            has_own_profile = True
        else:
            has_own_profile = False

        if bucket == "hydro":
            mapped_reservoirs: List[str] = []
            for original_asset_id, _e in members:
                original_asset = section_items(data, GENERATION_HYDRO_CLASS).get(original_asset_id, {})
                res_id = first_rel(original_asset, "drawsFromHydraulicStorage")
                if not res_id:
                    continue
                agg_res_id = aggregated_storage_id_for_asset(
                    data, res_id, node_to_agg, a2n,
                    {cls: section_items(data, cls) for cls in STORAGE_ASSET_CLASSES},
                    split_voltage,
                    bus_country=bus_country,
                    tech_groups=tech_groups,
                    reservoir_bus=reservoir_bus,
                )
                if agg_res_id and agg_res_id not in mapped_reservoirs:
                    mapped_reservoirs.append(agg_res_id)
            if mapped_reservoirs:
                gen_rels.append(make_rel("drawsFromHydraulicStorage", mapped_reservoirs))
        else:
            mapped_reservoirs = []

        if not has_own_profile:
            # The aggregated generator entity below gets written either
            # way -- that's correct for a dispatchable generator
            # (thermal, nuclear, ...), which genuinely has no
            # availability profile to lose. It's a real, actionable
            # data gap for anything non-dispatchable (wind, solar,
            # run-of-river hydro): downstream tools that need
            # hasAvailabilityProfile/hasNaturalInflowProfile (e.g.
            # tools/import_flexeco.py's PN_GenNonDispatchable handling)
            # will silently skip the generator, several steps and a
            # different tool away from here -- surface it now, at the
            # point where the cause is still visible, instead.
            dtypes_seen = [attr_value(e, "dispatch_type") for _, e in members if attr_value(e, "dispatch_type")]
            # PHS (reversible pump-turbine) units are dispatchable --
            # operated from stored reservoir water on demand, not
            # constrained by a natural inflow -- so they genuinely have
            # no hasNaturalInflowProfile to lose. Only a plain
            # (non-reversible) turbine's output is constrained by
            # natural river flow and needs one; "tech" already carries
            # the ".phs"/".nonphs" suffix this same loop's own grouping
            # key applies (see the reservoir/generator PHS-vs-turbine
            # split above), so reuse it here instead of re-deriving it.
            is_phs_group = bucket == "hydro" and tech.split(".")[-1] == "phs"
            is_nondispatchable = (
                (dtypes_seen and Counter(dtypes_seen).most_common(1)[0][0] == "nondispatchable")
                or (bucket == "hydro" and not is_phs_group)
            )
            if is_nondispatchable:
                if bucket == "hydro" and mapped_reservoirs:
                    # Reservoir-coupled (schema's own words: "Reservoir-
                    # level parameters (inflow, volume) are declared
                    # directly on the linked HydraulicStorageUnit entity
                    # itself") -- this generator correctly has no
                    # hasNaturalInflowProfile of its own; the real
                    # question is whether its paired reservoir has
                    # hasNaturalInflowProfile, which isn't known yet at
                    # this point (the storage/reservoir aggregation loop
                    # hasn't run). Deferred and checked after that loop,
                    # below -- warning here unconditionally would flag
                    # every reservoir-coupled turbine as a false positive,
                    # even when its reservoir's inflow is entirely correct.
                    pending_reservoir_coupled_hydro_checks.append((gid, mapped_reservoirs, len(members), [m_id for m_id, _ in members]))
                else:
                    reason = "no member had a usable profile array" if not profs else "combined weight was zero (missing/zero nominal_power_capacity or annual_resource_potential)"
                    log(f"[WARN] '{gid}' aggregated with no availability/run-of-river profile -- {reason}. "
                        f"{len(members)} member(s): {[m_id for m_id, _ in members]}")

        out_gen_assets_by_class[output_class][gid] = {"attributes": gen_attrs, "relations": gen_rels}

    out_gens = section_items_union(out_gen_assets_by_class, list(out_gen_assets_by_class))

    # ── Aggregated storage ─────────────────────────────────────────────────────
    # Non-reservoir StorageUnit and HydraulicStorageUnit are kept as
    # separate output classes (HydraulicStorageUnit is a standalone
    # class, not a StorageUnit subclass), so the Frictionless subset
    # doesn't lose specialised CSVs by collapsing them together.
    out_sto_assets_by_class: Dict[str, Dict[str, Dict[str, Any]]] = {
        cls: {} for cls in STORAGE_ASSET_CLASSES
    }

    sto_by_class = {cls: section_items(data, cls) for cls in STORAGE_ASSET_CLASSES}

    sto_groups: Dict[Tuple[str, str, str], List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)
    for asset_class, members_by_id in sto_by_class.items():
        for asset_id, ent in members_by_id.items():
            # Reservoirs have no atNode of their own -- only their paired
            # HydroGenerationUnit does -- so fall back to the bus
            # reachable via drawsFromHydraulicStorage.
            bus_id = a2n.get(asset_id) or reservoir_bus.get(asset_id)
            if bus_id not in node_to_agg:
                continue
            if _is_disagg_bus(bus_id):
                tech_raw = (
                    attr_value(ent, "storage_technology_type")
                    or asset_technology_id(data, asset_class, asset_id, asset_class)
                )
                if not any(
                    technology_matches_group(str(tech_raw), p) for p in (tech_groups or [])
                ):
                    out_sto_assets_by_class[asset_class][asset_id] = copy.deepcopy(ent)
                    _carry_profile_entity(ent)
                    continue
            tech = (
                attr_value(ent, "storage_technology_type")
                or asset_technology_id(data, asset_class, asset_id, asset_class)
            )
            tech = technology_tag_for_groups(str(tech), tech_groups)
            tag = id_tag(tech)
            if asset_class == STORAGE_RESERVOIR_CLASS:
                # A reservoir feeding a reversible (PHS) generator and
                # one feeding a plain turbine must never merge, for
                # the same reason their generators don't (see
                # is_phs_reservoir): they are structurally different
                # water bodies, and merging them would make the
                # aggregated turbine's and the aggregated PHS unit's
                # drawsFromHydraulicStorage both point at one, physically
                # meaningless, combined reservoir.
                tag = id_tag(f"{tag}.{'phs' if is_phs_reservoir(data, asset_id) else 'nonphs'}")
            sto_groups[(asset_class, node_to_agg[bus_id], tag)].append((asset_id, ent))

    for (asset_class, agg_bus, tech), members in sto_groups.items():
        rc, sfx = agg_asset_region_key(
            agg_bus, split_voltage,
            identity=(agg_id_level.get(agg_bus) == "disaggregated"),
        )
        sid = f"storage.{tech}.agg.{rc}{sfx}"

        pcaps   = [attr_float(e, "nominal_power_capacity")         for _, e in members]
        ecaps   = [attr_float(e, "energy_storage_capacity")        for _, e in members]
        pch     = [attr_float(e, "maximum_charging_power")         for _, e in members]
        eff_ch  = [attr_float(e, "charging_efficiency")            for _, e in members]
        eff_dis = [attr_float(e, "discharging_efficiency")         for _, e in members]
        vop     = [attr_float(e, "variable_operating_cost")        for _, e in members]
        vop_ch  = [attr_float(e, "charging_variable_operating_cost") for _, e in members]
        inflows = [attr_float(e, "annual_natural_inflow_energy")   for _, e in members]

        pc_sum     = sum(x or 0.0 for x in pcaps)
        ec_sum     = sum(x or 0.0 for x in ecaps)
        pch_sum    = sum(x or 0.0 for x in pch)
        inflow_sum = sum(x or 0.0 for x in inflows)

        sto_attrs = [make_attr("name", sid), make_attr("energy_storage_capacity", float(ec_sum), "MWh")]
        sto_rels: List[Dict[str, Any]] = []
        if asset_class == STORAGE_NONRESERVOIR_CLASS:
            sto_attrs.append(make_attr("storage_technology_type", tech))
            if pc_sum > 0:
                sto_attrs.append(make_attr("nominal_power_capacity", float(pc_sum), "MW"))
            if pch_sum > 0:
                sto_attrs.append(make_attr("maximum_charging_power", float(pch_sum), "MW"))
            for aid, vals, weights, unit in [
                ("charging_efficiency", eff_ch, pch, None),
                ("discharging_efficiency", eff_dis, pcaps, None),
                ("variable_operating_cost", vop, pcaps, "MU/MWh"),
                ("charging_variable_operating_cost", vop_ch, pch, "MU/MWh"),
            ]:
                val = wavg(vals, weights)
                if val is not None:
                    sto_attrs.append(make_attr(aid, float(val), unit))
            # A plain StorageUnit is electrically connected in its own
            # right (unlike a HydraulicStorageUnit).
            sto_rels.append(make_rel("atNode", [agg_bus]))
        else:
            if inflow_sum > 0:
                sto_attrs.append(make_attr("annual_natural_inflow_energy", float(inflow_sum), "MWh/year"))

        if inflow_sum > 0:
            profs = []
            weights = []
            for _, e in members:
                arr = load_profile(e)
                if arr is None:
                    continue
                w = float(attr_float(e, "annual_natural_inflow_energy") or 0.0)
                if w > 0:
                    profs.append(arr)
                    weights.append(w)
            if profs:
                W = np.array(weights, dtype=np.float64)
                raw = (np.vstack(profs).T * W).T.sum(axis=0)
                agg_arr = normalize_sum_pos1(raw).astype(H5_WRITE_DTYPE)
                new_pid = f"profile.inflow.{tech}.{rc}{sfx}"
                series_dict[new_pid] = agg_arr
                out_profiles[new_pid] = make_profile_entity(
                    new_pid, "as_normalized_annual_energy", "pu", h5_path_relative,
                )
                if asset_class == STORAGE_RESERVOIR_CLASS:
                    sto_rels.append(make_rel("hasNaturalInflowProfile", [new_pid]))

        out_sto_assets_by_class[asset_class][sid] = {"attributes": sto_attrs, "relations": sto_rels}

    out_sto = section_items_union(out_sto_assets_by_class, list(out_sto_assets_by_class))

    # ── Deferred check: reservoir-coupled hydro turbines without their
    # own profile ────────────────────────────────────────────────────
    # A reservoir-coupled HydroGenerationUnit correctly has no
    # hasNaturalInflowProfile of its own -- the schema's own words:
    # "Reservoir-level parameters (inflow, volume) are declared
    # directly on the linked HydraulicStorageUnit entity itself." Only
    # warn if *none* of its aggregated reservoir(s) ended up with
    # hasNaturalInflowProfile either -- that's the genuine gap; a
    # turbine correctly deferring to a reservoir that does have inflow
    # data is not.
    reservoirs_out = out_sto_assets_by_class.get(STORAGE_RESERVOIR_CLASS, {})
    for gid, mapped_reservoirs, n_members, member_ids in pending_reservoir_coupled_hydro_checks:
        any_reservoir_has_inflow = any(
            any(r["id"] == "hasNaturalInflowProfile" for r in reservoirs_out.get(res_id, {}).get("relations", []))
            for res_id in mapped_reservoirs
        )
        if not any_reservoir_has_inflow:
            log(f"[WARN] '{gid}' aggregated with no availability/run-of-river profile -- "
                f"reservoir-coupled, but none of its aggregated reservoir(s) "
                f"{mapped_reservoirs} has a natural inflow profile either. "
                f"{n_members} member(s): {member_ids}")

    # ── Diagnostic: every aggregated HydraulicStorageUnit should have at
    # least one aggregated HydroGenerationUnit's drawsFromHydraulicStorage
    # pointing to it. If not, this is either a genuine pre-existing gap
    # in the source data (some reservoirs were never paired with a
    # generator to begin with) or a real aggregation bug -- surfaced
    # here explicitly, with the original pre-aggregation reservoir ids
    # that fed into it, rather than silently producing an orphaned
    # reservoir with no way to trace it back.
    reservoir_class_ids = set(out_sto_assets_by_class.get(STORAGE_RESERVOIR_CLASS, {}).keys())
    if reservoir_class_ids:
        linked_reservoir_ids: set = set()
        for gen_ent in out_gens.values():
            for rel in gen_ent.get("relations", []):
                if rel["id"] == "drawsFromHydraulicStorage":
                    linked_reservoir_ids.update(rel["target_entity_ids"])
        orphaned = reservoir_class_ids - linked_reservoir_ids
        for orphan_id in sorted(orphaned):
            original_ids = [
                orig_id for (_cls, _bus, _tech), members in sto_groups.items()
                if _tech in orphan_id  # the aggregated id embeds this group's tech tag
                for orig_id, _e in members
            ]
            log(
                f"[WARN] Aggregated reservoir '{orphan_id}' has no aggregated "
                f"HydroGenerationUnit linked via drawsFromHydraulicStorage -- check "
                f"whether its pre-aggregation source reservoir(s) "
                f"{original_ids or '(could not trace)'} were ever paired with a "
                f"generator in the input data at all."
            )
            # Trace each pre-aggregation source reservoir individually: did it
            # have a paired generator before aggregation, and if so, what id
            # does aggregated_storage_id_for_asset() compute for it right now?
            # A generator that WAS paired pre-aggregation, but whose computed
            # id doesn't match orphan_id, is a real aggregation bug -- a
            # mismatch, not a source-data gap. A reservoir with no paired
            # generator at all pre-aggregation is a genuine source-data gap.
            all_hydro_gens = section_items(data, "HydroGenerationUnit")
            for orig_res_id in original_ids:
                paired_gens = [
                    gen_id for gen_id, gen_ent in all_hydro_gens.items()
                    if first_rel(gen_ent, "drawsFromHydraulicStorage") == orig_res_id
                ]
                if not paired_gens:
                    log(f"  - source reservoir '{orig_res_id}': no HydroGenerationUnit "
                        f"draws from it in the input data (genuine source-data gap).")
                    continue
                for gen_id in paired_gens:
                    recomputed = aggregated_storage_id_for_asset(
                        data, orig_res_id, node_to_agg, a2n, sto_by_class, split_voltage,
                        bus_country=bus_country,
                        tech_groups=tech_groups,
                        reservoir_bus=reservoir_bus,
                    )
                    gen_bus = a2n.get(gen_id)
                    gen_agg_bus = node_to_agg.get(gen_bus or "")
                    match = "MATCHES orphan_id" if recomputed == orphan_id else "MISMATCH -- this is the bug"
                    log(f"  - source reservoir '{orig_res_id}' <- generator '{gen_id}' "
                        f"(bus={gen_bus}, agg_bus={gen_agg_bus}): "
                        f"aggregated_storage_id_for_asset() computes '{recomputed}' ({match})")

    # ── Branch assets ──────────────────────────────────────────────────────────
    # Keep every branch (TransmissionLine, GenericInterconnector, HVDCLink,
    # Transformer) as-is: same entity id, same attributes. Only remap
    # fromNode/toNode onto the aggregated buses. No parallel-corridor merge
    # and no blended electrical / transfer parameters.
    dropped_cross = dropped_switch = dropped_internal = 0

    def _branch_agg_endpoints(
        asset_id: str, asset_ent: Dict[str, Any],
    ) -> Optional[Tuple[str, str]]:
        """Return (agg_from, agg_to) or None if the branch is dropped."""
        nonlocal dropped_cross, dropped_switch, dropped_internal
        frm0, to0 = a2br.get(asset_id, (None, None))
        if frm0 not in node_to_agg or to0 not in node_to_agg:
            dropped_cross += 1
            return None
        sf = attr_float(asset_ent, "from_switch_closed")
        st = attr_float(asset_ent, "to_switch_closed")
        if (sf is not None and sf == 0) or (st is not None and st == 0):
            dropped_switch += 1
            return None
        a = node_to_agg[frm0]
        b = node_to_agg[to0]
        if a == b:
            dropped_internal += 1
            return None
        return a, b

    def _copy_branch_on_agg_buses(
        ent: Dict[str, Any], agg_from: str, agg_to: str,
    ) -> Dict[str, Any]:
        copied = copy.deepcopy(ent)
        rels = []
        saw_from = saw_to = False
        for rel in copied.get("relations", []) or []:
            if not isinstance(rel, dict):
                continue
            rid = rel.get("id")
            if rid == "fromNode":
                rels.append(make_rel("fromNode", [agg_from]))
                saw_from = True
            elif rid == "toNode":
                rels.append(make_rel("toNode", [agg_to]))
                saw_to = True
            else:
                rels.append(copy.deepcopy(rel))
        if not saw_from:
            rels.append(make_rel("fromNode", [agg_from]))
        if not saw_to:
            rels.append(make_rel("toNode", [agg_to]))
        copied["relations"] = rels
        return copied

    out_branches_by_class = {
        "TransmissionLine": out_lines,
        "GenericInterconnector": out_icos,
        "HVDCLink": out_hvdcs,
        "Transformer": out_trafos,
    }
    for branch_class, out_bucket in out_branches_by_class.items():
        for aid, ent in section_items(data, branch_class).items():
            endpoints = _branch_agg_endpoints(aid, ent)
            if endpoints is None:
                continue
            out_bucket[aid] = _copy_branch_on_agg_buses(ent, endpoints[0], endpoints[1])

    log(f"dropped_links_outside_subset={dropped_cross}")
    log(f"dropped_links_switch_off={dropped_switch}")
    log(f"dropped_links_internal_after_agg={dropped_internal}")

    # ── Geographic regions ─────────────────────────────────────────────────────
    out_geo: Dict[str, Dict[str, Any]] = {}
    geo_sec = section_items(data, "GeographicalRegion")
    for gid in sorted(disagg_geo_ids):
        out_geo[gid] = copy.deepcopy(geo_sec[gid]) if gid in geo_sec else {
            "attributes": [make_attr("name", gid)], "relations": [],
        }
    for rc in sorted(region_codes):
        gid = geo_region_id(region_code_level.get(rc, level), rc)
        if gid not in out_geo:
            out_geo[gid] = {"attributes": [make_attr("name", gid)], "relations": []}

    # ── TimestampSeries entity (carry through or create placeholder) ───────────
    ts_sec = section_items(data, "TimestampSeries")
    out_ts: Dict[str, Dict[str, Any]] = {}
    if ts_sec:
        out_ts = ts_sec  # carry through existing
    else:
        out_ts[TIMESTAMP_SERIES_ID] = {
            "attributes": [
                make_attr("name",       TIMESTAMP_SERIES_ID),
                make_attr("resolution", "PT1H"),
            ],
            "relations": [],
        }

    out_obj: Dict[str, Any] = {
        "Carrier":                   section_items(data, "Carrier"),
        "NaturalResource":                 section_items(data, "NaturalResource"),
        "CarrierDomain":                   section_items(data, "CarrierDomain"),
        "GeographicalRegion":              out_geo,
        "TimestampSeries":                 out_ts,
        "Profile":                         out_profiles,
        "ElectricalBus":                   out_buses,
        **out_gen_assets_by_class,
        "DemandUnit":                      out_dem,
        **out_sto_assets_by_class,
        "TransmissionLine":                out_lines,
        "GenericInterconnector":                  out_icos,
        "HVDCLink":                        out_hvdcs,
        "Transformer":                     out_trafos,
    }

    stats = {
        "buses":  len(out_buses),
        "gens":   len(out_gens),
        "loads":  len(out_dem),
        "stors":  len(out_sto),
        "lines":  len(out_lines),
        "icos":   len(out_icos),
        "trafos": len(out_trafos),
    }

    # ── Per-country sanity check: disaggregated vs. aggregated totals ─────────
    # bus_country already only has entries for kept_buses, so summing the raw
    # (unfiltered) input data against it naturally scopes the "disaggregated"
    # side to exactly the same subset the aggregation itself operated on --
    # the same fairness a before/after comparison needs.
    disagg_totals = summarize_by_country(data, bus_country, a2n, reservoir_bus)
    agg_bus_country: Dict[str, str] = {}
    for agg_id in out_buses:
        if agg_id_level.get(agg_id) == "disaggregated":
            agg_bus_country[agg_id] = bus_country.get(agg_id, "")
        else:
            parts = agg_id.split(".")
            agg_bus_country[agg_id] = country_of_nuts3(parts[1]) if len(parts) >= 2 else ""
    agg_bus_country = {k: v for k, v in agg_bus_country.items() if v}
    agg_a2n = build_asset_to_node(
        out_obj, GENERATION_ASSET_CLASSES + ["DemandUnit", STORAGE_NONRESERVOIR_CLASS],
    )
    agg_reservoir_bus = build_reservoir_bus_via_generator(out_obj, agg_a2n)
    agg_totals = summarize_by_country(out_obj, agg_bus_country, agg_a2n, agg_reservoir_bus)
    stats["_sanity_disaggregated_by_country"] = disagg_totals
    stats["_sanity_aggregated_by_country"] = agg_totals

    return out_obj, series_dict, stats


def write_summary(
    outdir: Path,
    level: str,
    split_voltage: bool,
    selectors: List[str],
    invalid_selectors: List[str],
    kept_buses: Dict[str, Dict[str, Any]],
    original_data: Dict[str, Any],
    result_stats: Dict[str, int],
    log_lines: List[str],
) -> None:
    country_counts = summarize_kept_by_country(
        list(kept_buses.keys()), section_items(original_data, "ElectricalBus")
    )
    lines = [
        f"LEVEL={level}",
        f"SPLIT_VOLTAGE={split_voltage}",
        f"KEEP_CODES={selectors}",
        f"INVALID_KEEP_CODES={invalid_selectors}",
        "",
        "Kept buses by country:",
        *(f"  {k}: {v}" for k, v in sorted(country_counts.items())),
        "",
        "Output entity counts:",
        *(f"  {k}: {result_stats.get(k, 0)}"
          for k in ["buses", "gens", "loads", "stors", "lines", "icos", "trafos"]),
        "",
        "Run log:",
        *log_lines,
    ]
    (outdir / "subset_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="CESDM nodal-model aggregation — nuts3 / nuts2 / nuts1 / country.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ── I/O ──────────────────────────────────────────────────────────────────
    p.add_argument(
        "--schemas", metavar="DIR", default="schemas/cesdm",
        help="CESDM schema directory (passed to build_model_from_yaml).",
    )
    p.add_argument(
        "--yaml", metavar="FILE", default=_DEFAULT_YAML,
        help="Input CESDM hierarchical YAML file.",
    )
    p.add_argument(
        "--h5", metavar="FILE", default=_DEFAULT_H5,
        help="Input profile HDF5 file (legacy flat format). "
             "Required unless --no-profiles is set.",
    )
    p.add_argument(
        "--outdir", metavar="DIR", default=None,
        help="Output directory. Defaults to '<cwd>/aggregated_<level>[_<codes>]'.",
    )

    # ── Aggregation control ───────────────────────────────────────────────────
    p.add_argument(
        "--level", metavar="LEVEL",
        choices=["disaggregated", "nuts3", "nuts2", "nuts1", "country"],
        default="disaggregated",
        help="Default spatial aggregation level, used for every country "
             "not given its own override in --level-by-country.",
    )
    p.add_argument(
        "--level-by-country", metavar="COUNTRY=LEVEL", nargs="*", default=[],
        help="Per-country spatial aggregation level overrides, e.g. "
             "--level-by-country CH=disaggregated DE=country -- keeps "
             "every original Swiss bus (no spatial merge) while aggregating "
             "Germany to one node per country. CH=nuts3 merges Swiss buses "
             "that share a NUTS3 region. Countries not listed use --level.",
    )
    p.add_argument(
        "--tech-group", metavar="PATTERN", action="append", default=None,
        help="Technology aggregation group pattern (repeatable), e.g. "
             "--tech-group 'Generation.Thermal.Gas.*' "
             "--tech-group 'Generation.Renewable.Wind.*'. Matching "
             "hasTechnology ids merge into one asset per aggregated bus; "
             "unmatched technologies stay separate. Bare prefixes "
             "(Generation.Thermal.Gas) also match subtypes. Longest "
             "matching pattern wins. Omit for no technology aggregation.",
    )
    p.add_argument(
        "--keep", metavar="CODE", nargs="*", default=["CH"],
        help="ISO-2 or NUTS prefix codes to include (e.g. CH DE fr042). "
             "Pass no arguments to keep everything.",
    )
    p.add_argument(
        "--split-voltage", action=argparse.BooleanOptionalAction, default=True,
        help="Maintain separate aggregated nodes per voltage level.",
    )
    p.add_argument(
        "--round-kv", metavar="N", type=int, default=1,
        help="Decimal rounding precision for voltage grouping.",
    )

    # ── Output switches ───────────────────────────────────────────────────────
    p.add_argument(
        "--no-yaml", dest="export_yaml", action="store_false", default=True,
        help="Skip writing the output YAML file.",
    )
    p.add_argument(
        "--no-profiles", dest="export_profiles", action="store_false", default=True,
        help="Skip reading / writing profile HDF5 files.",
    )
    p.add_argument(
        "--no-log", dest="write_log", action="store_false", default=True,
        help="Skip writing the aggregation_log.txt file.",
    )

    return p.parse_args()


def main():
    args = parse_args()

    schemas_dir = Path(args.schemas).expanduser().resolve()
    yaml_path   = Path(args.yaml).expanduser().resolve()
    h5_path     = Path(args.h5).expanduser().resolve()

    keep_codes: List[str] = args.keep or []
    level         = args.level
    level_by_country = parse_kv_overrides(args.level_by_country, value_type=str, what="level")
    invalid_levels = {c: lv for c, lv in level_by_country.items()
                       if lv not in ("disaggregated", "nuts3", "nuts2", "nuts1", "country")}
    if invalid_levels:
        raise SystemExit(
            f"Invalid --level-by-country value(s) {invalid_levels} -- must be one "
            f"of disaggregated/nuts3/nuts2/nuts1/country."
        )
    tech_groups = normalize_tech_groups(args.tech_group)
    split_voltage = args.split_voltage
    export_yaml    = args.export_yaml
    export_profiles = args.export_profiles
    write_log_txt  = args.write_log

    if args.outdir:
        outdir = Path(args.outdir).expanduser().resolve()
    else:
        outdir = Path.cwd() / build_outdir_name(level, keep_codes)
    outdir.mkdir(parents=True, exist_ok=True)

    log_lines: List[str] = []

    def log(msg: str) -> None:
        print(msg)
        log_lines.append(msg)

    log(f"input yaml={yaml_path}")
    log(f"input h5={h5_path}")
    log(f"outdir={outdir}")
    log(f"level={level}  split_voltage={split_voltage}  keep={keep_codes}")
    if level_by_country:
        log(f"level_by_country={level_by_country}")
    log(f"tech_groups={tech_groups or None}")

    if not schemas_dir.exists():
        raise SystemExit(f"Schema directory not found: {schemas_dir}")
    if not yaml_path.exists():
        raise SystemExit(f"YAML not found: {yaml_path}")
    if export_profiles and not h5_path.exists():
        raise SystemExit(f"HDF5 not found: {h5_path}")

    log(f"loading schema from {schemas_dir} …")
    input_model = load_cesdm_model(schemas_dir, yaml_path)
    data = model_to_data(input_model)
    log(f"schema + model loaded via cesdm_toolbox")

    buses_sec = section_items(data, "ElectricalBus")
    log(
        f"parsed buses={len(buses_sec)} "
        f"gens={len(section_items(data, 'GenerationUnit'))} "
        f"loads={len(section_items(data, 'DemandUnit'))} "
        f"stors={len(section_items(data, 'StorageUnit'))} "
        f"lines={len(section_items(data, 'TransmissionLine'))} "
        f"icos={len(section_items(data, 'GenericInterconnector'))} "
        f"trafos={len(section_items(data, 'Transformer'))}"
    )

    # Resolve profile input: Parquet takes priority over HDF5
    _profiles_parquet = getattr(args, "profiles_parquet", None)
    _out_format       = getattr(args, "out_format", "hdf5")
    if export_profiles and _profiles_parquet:
        pm = ProfileMatrix(Path(_profiles_parquet).expanduser().resolve())
    elif export_profiles:
        pm = ProfileMatrix(h5_path)
    else:
        pm = None
    if pm is not None:
        log(f"h5 T={pm.T} profiles={len(pm.name_to_idx)}")

    all_nuts3   = collect_all_nuts3_codes(buses_sec)
    selectors_r = [normalize_code(x) for x in keep_codes if normalize_code(x)]
    selectors, invalid_selectors = validate_selectors(selectors_r, all_nuts3)

    if invalid_selectors:
        log(f"[WARN] invalid selectors={invalid_selectors}")
    log(f"subset selectors={selectors}")

    kept_buses: Dict[str, Dict[str, Any]] = {
        bid: ent for bid, ent in buses_sec.items()
        if (n3 := node_nuts3_code(bid, ent)) and selector_matches_nuts3(n3, selectors)
    }

    log(f"kept_buses={len(kept_buses)} dropped={len(buses_sec) - len(kept_buses)}")
    if not kept_buses:
        raise SystemExit(f"No buses remain after applying --keep {keep_codes}")

    # Relative path for data_reference attributes in Profile entities
    h5_out_path = outdir / "cesdm" / "profiles" / "profiles.h5"
    h5_relative = str(h5_out_path.relative_to(outdir))

    uses_pure_disaggregated = (
        level == "disaggregated" and not level_by_country and not tech_groups
    )

    if uses_pure_disaggregated:
        out_obj, series_dict, stats = build_subset_disaggregated(
            data, kept_buses, pm, log
        )
        log(
            f"mode=disaggregated buses={stats['buses']} gens={stats['gens']} "
            f"loads={stats['loads']} stors={stats['stors']} "
            f"lines={stats['lines']} icos={stats['icos']} trafos={stats['trafos']}"
        )
    else:
        out_obj, series_dict, stats = aggregate_subset(
            data, kept_buses, level, split_voltage, pm, log, h5_relative,
            round_kv=args.round_kv,
            level_by_country=level_by_country,
            tech_groups=tech_groups,
        )
        log(
            f"mode={level} buses={stats['buses']} gens={stats['gens']} "
            f"loads={stats['loads']} stors={stats['stors']} "
            f"lines={stats['lines']} icos={stats['icos']} trafos={stats['trafos']}"
        )
        disagg_sanity = stats.pop("_sanity_disaggregated_by_country", None)
        agg_sanity = stats.pop("_sanity_aggregated_by_country", None)
        if disagg_sanity is not None and agg_sanity is not None:
            write_sanity_check_report(outdir, disagg_sanity, agg_sanity, log)

    if export_profiles and series_dict:
        T = pm.T if pm is not None else 8760
        if _out_format == "parquet":
            pq_out = outdir / "cesdm" / "profiles" / "profiles.parquet"
            write_profiles_parquet(pq_out, series_dict, T)
            log(f"wrote profiles (parquet)={pq_out} n_series={len(series_dict)}")
        else:
            write_profiles_h5_cesdm(h5_out_path, series_dict, T)
            log(f"wrote profiles (hdf5)={h5_out_path} n_series={len(series_dict)}")

    if export_yaml:
        out_yaml = outdir / "cesdm" / "yaml" / f"aggregated_cesdm_{level}.yaml"
        out_model = data_to_model(schemas_dir, out_obj)
        out_model.export_yaml_hierarchical(str(out_yaml))
        log(f"wrote yaml={out_yaml} (via cesdm_toolbox export_yaml_hierarchical)")

        # Frictionless Data Package — self-describing, one CSV per class
        out_model.export_frictionless(
            outdir / "cesdm" / "frictionless",
            name  = f"pypsa data in {level} resolution",
            title = f"pypsa {level}-level model",
        )

    write_summary(outdir, level, split_voltage, selectors, invalid_selectors, kept_buses, data, stats, log_lines)

    if write_log_txt:
        (outdir / "aggregation_log.txt").write_text(
            "\n".join(log_lines) + "\n", encoding="utf-8"
        )

    if pm is not None:
        pm.close()


if __name__ == "__main__":
    main()
