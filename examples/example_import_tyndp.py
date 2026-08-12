"""
example_import_export_tyndp.py
==============================

Builds a CESDM model from TYNDP2024 CSV source files.

==============================
"""

from __future__ import annotations

import os
import re
from pathlib import Path
import sys

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

_REPO_ROOT = _repo_root()
for _path in (_REPO_ROOT, _REPO_ROOT / "tools"):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from generation_classifier import generation_asset_class, hydrogen_generation_efficiency, hydro_machine_kind

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent

from cesdm_toolbox  import build_model_from_yaml, CesdmModel
from cesdm_carriers import (
    ELECTRICITY_CARRIER_ID, ELECTRICITY_DOMAIN_ID,
    CARRIER_ID_MAP as ENERGY_CARRIER_MAP,
    CARRIER_CO2   as ENERGY_CARRIER_CO2,
    CARRIER_PRICE as ENERGY_CARRIER_PRICE,
    canonical_carrier_id,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOMAIN_ID              = "domain.electricity"
ELECTRICITY_CARRIER_ID = "carrier.electricity"

CO2_PRICE = {2030: 113.4, 2040: 147.0, 2050: 168.0}


# ---------------------------------------------------------------------------
# New structured asset hierarchy helpers
# ---------------------------------------------------------------------------

def _entity_exists(model: CesdmModel, entity_id: str) -> bool:
    """Return True if entity_id exists in any concrete class bucket."""
    return any(entity_id in ents for ents in model.entities.values())


def _entity_class(model: CesdmModel, entity_id: str) -> str | None:
    """Return the concrete class bucket containing entity_id, if present."""
    for cls, ents in model.entities.items():
        if entity_id in ents:
            return cls
    return None


def _generation_asset_class_for_type(type_name: str, type_id: str | None = None) -> str:
    """Map a TYNDP/default-library generation technology to the new asset subclass.

    The default_library remains the technology vocabulary (GeneratorType).
    The entity class describes the physical/semantic asset family only.

    Important: classify by physical conversion principle, not by substring alone.
    "Hydrogen CCGT" is a thermal generator using hydrogen fuel; it is not hydro.
    """
    slug = _slug(type_name)
    tid = type_id or TECH_HIERARCHY.get(slug, "")
    key = f"{slug} {tid}".lower()

    # Solar thermal/CSP is a generic profiled generator in TYNDP.
    # Check it before the broad thermal/fuel substring rules, otherwise
    # "Generation.Renewable.Solar.Thermal" is misclassified as thermal.
    if "solar_thermal" in key or "solar thermal" in key or "solar.thermal" in key or "csp" in key:
        return "GenerationUnit"
    if "nuclear" in key:
        return "GenerationUnit"
    # Residual/other buckets are technology-agnostic fallbacks, not thermal.
    if any(x in key for x in [
        "others_non_renewable", "other_non_renewable", "other_nonrenewable",
        "others_nonrenewable", "other_renewable", "others_renewable",
        "other.residual", "nonrenewable.residual",
    ]):
        return "GenerationUnit"
    # Hydrogen fuel cells are a hydrogen conversion fallback in CESDM until a
    # dedicated HydrogenGenerationUnit exists. Hydrogen CCGT/OCGT remain thermal.
    if "fuel_cell" in key or "fuelcell" in key or "fuel cell" in key:
        return "GenerationUnit"
    # Thermal/fuel-based technologies first so "hydrogen" cannot be caught by "hydro".
    if any(x in key for x in ["ccgt", "ocgt", "gas", "coal", "oil", "lignite", "thermal", "hydrogen turbine"]):
        return "GenerationUnit"
    # True hydro technologies only.
    if any(x in key for x in ["hydro.", "hydro_", "run_of_river", "runofriver", "reservoir", "pondage", "pumpedhydro"]):
        return "HydroGenerationUnit"
    if "wind" in key:
        return "GenerationUnit"
    if "solar" in key:
        return "GenerationUnit"
    return "GenerationUnit"


def _storage_asset_class_for_type(type_name: str, type_id: str | None = None) -> str:
    """Map a TYNDP/default-library storage technology to the correct StorageUnit subclass.

    HydraulicStorageUnit: reservoir hydro, pondage, AND all PHS types.
      PHS distinction is captured on the linked HydroGenerationUnit
      (is_reversible) and directly on the reservoir itself
      (annual_natural_inflow_energy on HydraulicStorageUnit).
    StorageUnit: batteries, generic storage, fallback.
    """
    slug = _slug(type_name)
    tid = type_id or TECH_HIERARCHY.get(slug, "")
    key = f"{slug} {tid}".lower()
    if any(x in key for x in ("reservoir", "pondage", "pump_storage",
                              "pumped", "pumpedhydro", "phs")):
        return "HydraulicStorageUnit"
    return "StorageUnit"





def _is_pumped_hydro_storage_type(type_name: str, type_id: str | None = None) -> bool:
    slug = _slug(type_name)
    tid = type_id or TECH_HIERARCHY.get(slug, "")
    key = f"{slug} {tid}".lower()
    return any(x in key for x in ["pumpedhydro", "pump_storage", "pumped", "ps open", "ps cloase", "ps close"])


def _is_reservoir_hydro_storage_type(type_name: str, type_id: str | None = None) -> bool:
    """Return True for reservoir/pondage storage that should be paired with HydroGenerationUnit."""
    slug = _slug(type_name)
    tid = type_id or TECH_HIERARCHY.get(slug, "")
    key = f"{slug} {tid}".lower()
    return "reservoir" in key or "pondage" in key


def _hydro_generator_id(storage_id: str) -> str:
    return f"gen.hydro.{storage_id}"


def _add_hydro_reservoir_composite_if_missing(model: CesdmModel, reservoir_id: str, bus_id: str | None,
                                      power_capacity: float | None = None,
                                      resource_potential: float | None = None,
                                      is_reversible: bool = False) -> str:
    """Create HydroGenerationUnit for a reservoir/PHS storage asset.

    is_reversible=True creates a PHS pump-turbine generator;
    is_reversible=False creates a pure turbine generator.
    """
    gen_id = _hydro_generator_id(reservoir_id)


    if gen_id not in model.entities.get("HydroGenerationUnit", {}):
        model.add_entity(entity_class="HydroGenerationUnit", entity_id=gen_id)
        model.add_attribute(gen_id, "name", gen_id)
        if is_reversible:
            model.add_attribute(gen_id, "turbine_type", "reversible_francis")
    hydro_tt_id = _add_hydro_generator_type_if_missing(model, is_reversible=is_reversible)
    model.add_relation(gen_id, "hasTechnology", hydro_tt_id)
    model.add_relation(gen_id, "hasInputResource", "resource.water")
    model.add_relation(gen_id, "hasOutputCarrier", ELECTRICITY_CARRIER_ID)
    model.add_relation(gen_id, "drawsFromHydraulicStorage", reservoir_id)

    if bus_id:
        model.add_relation(gen_id, "atNode", bus_id)

    # Power/efficiency held directly on the generator itself (see
    # CHANGELOG.md: the direct EAR asset model).
    model.add_attribute(gen_id, "dispatch_type", "dispatchable")
    model.add_attribute(
        gen_id,
        "hydro_machine_kind",
        hydro_machine_kind(hydro_tt_id, is_reversible=is_reversible),
    )
    if power_capacity is not None:
        model.add_attribute(gen_id, "nominal_power_capacity", power_capacity)
    if resource_potential is not None:
        model.add_attribute(gen_id, "annual_resource_potential", resource_potential)
    return gen_id




# Paths for stacked libraries (default core + TYNDP vintages + regions).
DEFAULT_LIBRARY_DIR = _REPO_ROOT / "library" / "default_library"
TYNDP_LIBRARY_DIR = _REPO_ROOT / "library" / "tyndp_library"
REGIONS_LIBRARY_DIR = _REPO_ROOT / "library" / "regions_library"


def import_tyndp_libraries(model: CesdmModel) -> None:
    """Import default + TYNDP GeneratorType libraries and regions_library."""
    model.import_library(str(DEFAULT_LIBRARY_DIR))
    model.import_library(str(TYNDP_LIBRARY_DIR))
    if REGIONS_LIBRARY_DIR.exists():
        model.import_library(str(REGIONS_LIBRARY_DIR))


def country_region_id(country_code: str) -> str:
    """Map a TYNDP/ISO country code to ``region.country.XX`` (regions_library)."""
    cc = (country_code or "").strip().upper()
    if cc.startswith("REGION.COUNTRY."):
        cc = cc.rsplit(".", 1)[-1]
    elif cc.startswith("COUNTRY."):
        cc = cc.split(".", 1)[-1].upper()
    return f"region.country.{cc}"


def ensure_country_region(
    model: CesdmModel,
    country_code: str,
    *,
    name: str | None = None,
) -> str:
    """Return ``region.country.XX``, creating a fallback entity only if missing."""
    rid = country_region_id(country_code)
    if not model.has_entity(rid):
        model.add_entity(entity_class="GeographicalRegion", entity_id=rid)
        if name:
            model.add_attribute(rid, "name", name)
    elif name and model.get_attribute_value(rid, "name") in (None, ""):
        model.add_attribute(rid, "name", name)
    return rid


# tech_slug → GeneratorType/StorageType id (default_library + tyndp_library)
TECH_HIERARCHY = {
    # Thermal — vintages Old*/Present* come from library/tyndp_library
    "nuclear":                    "Generation.Nuclear.LWR",
    "hard_coal_old_1":            "Generation.Thermal.Coal.HardCoal.Old1",
    "hard_coal_old_2":            "Generation.Thermal.Coal.HardCoal.Old2",
    "hard_coal_new":              "Generation.Thermal.Coal.HardCoal.New",
    "hard_coal_ccs":              "Generation.Thermal.Coal.HardCoal.CCS",
    "hard_coal_biofuel":          "Generation.Thermal.Coal.HardCoal.Biofuel",
    "lignite_old_1":              "Generation.Thermal.Coal.Lignite.Old1",
    "lignite_old_2":              "Generation.Thermal.Coal.Lignite.Old2",
    "lignite_new":                "Generation.Thermal.Coal.Lignite.New",
    "lignite_ccs":                "Generation.Thermal.Coal.Lignite.CCS",
    "lignite_biofuel":            "Generation.Thermal.Coal.Lignite.Biofuel",
    "gas_conventional_old_1":     "Generation.Thermal.Gas.Conventional.Old1",
    "gas_conventional_old_2":     "Generation.Thermal.Gas.Conventional.Old2",
    "gas_ccgt_old_1":             "Generation.Thermal.Gas.CCGT.Old1",
    "gas_ccgt_old_2":             "Generation.Thermal.Gas.CCGT.Old2",
    "gas_ccgt_present_1":         "Generation.Thermal.Gas.CCGT.Present1",
    "gas_ccgt_present_2":         "Generation.Thermal.Gas.CCGT.Present2",
    "gas_ccgt_new":               "Generation.Thermal.Gas.CCGT.New",
    "gas_ccgt_ccs":               "Generation.Thermal.Gas.CCGT.CCS",
    "gas_biofuel":                "Generation.Thermal.Gas.CCGT.Biofuel",
    "gas_ocgt_old":               "Generation.Thermal.Gas.OCGT.Old",
    "gas_ocgt_new":               "Generation.Thermal.Gas.OCGT.New",
    "light_oil":                  "Generation.Thermal.Oil.LightOil.Standard",
    "heavy_oil_old_1":            "Generation.Thermal.Oil.HeavyOil.Old1",
    "heavy_oil_old_2":            "Generation.Thermal.Oil.HeavyOil.Old2",
    "oil_shale_old":              "Generation.Thermal.OilShale.Standard.Old",
    "oil_shale_new":              "Generation.Thermal.OilShale.Standard.New",
    "oil_shale_biofuel":          "Generation.Thermal.OilShale.Biofuel.Standard",
    "others_non_renewable":       "Generation.Thermal.Other.NonRenewable.Residual",
    # Renewable (profiled)
    "wind_offshore":              "Generation.Renewable.Wind.Offshore",
    "wind_onshore":               "Generation.Renewable.Wind.Onshore",
    "solar_photovoltaic":         "Generation.Renewable.Solar.PV.Utility",
    "solar_photovoltaic_rooftop": "Generation.Renewable.Solar.PV.Rooftop",
    "solar_photovoltaic_utility": "Generation.Renewable.Solar.PV.Utility",
    "solar_thermal":              "Generation.Renewable.Solar.Thermal",
    "run_of_river":               "Generation.Renewable.Hydro.RunOfRiver",
    "hydro_reservoir_generation": "Generation.Renewable.Hydro.Reservoir",
    "others_renewable":           "Generation.Renewable.Other.Residual",
    # Storage
    "battery_storage":            "Storage.Electrochemical.Battery",
    "pump_storage_closed_loop":   "Storage.Hydro.PumpedHydro.ClosedLoop",
    "pump_storage_open_loop":     "Storage.Hydro.PumpedHydro.OpenLoop",
    "reservoir":                  "Storage.Hydro.Reservoir",
    "pondage":                    "Storage.Hydro.Pondage",
    # Hydrogen
    "hydrogen_fuel_cell":         "Generation.Hydrogen.FuelCell",
    "hydrogen_ccgt":              "Generation.Hydrogen.CCGT",
    # Demand response / adequacy
    "demand_side_response_explicit": "Generation.Other.DemandResponse",
    "demand_side_response_implicit": "Generation.Other.DemandResponse",
    "demand_side_response":          "Generation.Other.DemandResponse",
    "adequacy":                      "Generation.Other.Adequacy",
}

# V4 GeneratorType / StorageType techno-economic defaults
TYNDP_TECH_DATA = {
    "Generation.Nuclear.LWR":                     {"eff": 0.33, "voc": 9.0,   "disp": True,  "ramp_up": 0.05, "ramp_dn": 0.05},
    "Generation.Nuclear.SMR":                     {"eff": 0.35, "voc": 9.0,   "disp": True,  "ramp_up": 0.10, "ramp_dn": 0.10},
    "Generation.Thermal.Coal.HardCoal.Old1":      {"eff": 0.35, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.HardCoal.Old2":      {"eff": 0.40, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.HardCoal.New":       {"eff": 0.46, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.HardCoal.CCS":       {"eff": 0.38, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.HardCoal.Biofuel":   {"eff": 0.38, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.Lignite.Old1":       {"eff": 0.35, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.Lignite.Old2":       {"eff": 0.40, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.Lignite.New":        {"eff": 0.46, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.Lignite.CCS":        {"eff": 0.38, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Coal.Lignite.Biofuel":    {"eff": 0.35, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Gas.Conventional.Old1":   {"eff": 0.36, "voc": 1.1,   "disp": True},
    "Generation.Thermal.Gas.Conventional.Old2":   {"eff": 0.41, "voc": 1.1,   "disp": True},
    "Generation.Thermal.Gas.CCGT.Old1":           {"eff": 0.40, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.CCGT.Old2":           {"eff": 0.48, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.CCGT.Present1":       {"eff": 0.56, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.CCGT.Present2":       {"eff": 0.58, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.CCGT.New":            {"eff": 0.60, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.CCGT.CCS":            {"eff": 0.51, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.CCGT.Biofuel":        {"eff": 0.51, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.OCGT.Old":            {"eff": 0.35, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Gas.OCGT.New":            {"eff": 0.42, "voc": 1.6,   "disp": True},
    "Generation.Thermal.Oil.LightOil.Standard":   {"eff": 0.35, "voc": 1.1,   "disp": True},
    "Generation.Thermal.Oil.HeavyOil.Old1":       {"eff": 0.35, "voc": 3.3,   "disp": True},
    "Generation.Thermal.Oil.HeavyOil.Old2":       {"eff": 0.40, "voc": 3.3,   "disp": True},
    "Generation.Thermal.OilShale.Standard.Old":   {"eff": 0.29, "voc": 3.3,   "disp": True},
    "Generation.Thermal.OilShale.Standard.New":   {"eff": 0.39, "voc": 3.3,   "disp": True},
    "Generation.Thermal.OilShale.Biofuel.Standard":{"eff": 0.29, "voc": 3.3,  "disp": True},
    "Generation.Thermal.Other.NonRenewable.Residual":{"eff": 1.0,             "disp": True},
    "Generation.Renewable.Wind.Offshore":         {"eff": 1.0,  "voc": 0.0,   "disp": False},
    "Generation.Renewable.Wind.Onshore":          {"eff": 1.0,  "voc": 0.0,   "disp": False},
    "Generation.Renewable.Solar.PV.Rooftop":      {"eff": 1.0,  "voc": 0.0,   "disp": False},
    "Generation.Renewable.Solar.PV.Utility":      {"eff": 1.0,  "voc": 0.0,   "disp": False},
    "Generation.Renewable.Solar.Thermal":         {"eff": 1.0,  "voc": 0.0,   "disp": False},
    "Generation.Renewable.Hydro.RunOfRiver":      {"eff": 1.0,  "voc": 0.0,   "disp": False},
    "Generation.Renewable.Other.Residual":        {"eff": 1.0,  "voc": 0.0,   "disp": True},
    "Storage.Electrochemical.Battery":            {"dis_eff": 0.95, "chg_eff": 0.90},
    "Storage.Hydro.PumpedHydro.ClosedLoop":       {"dis_eff": 0.87, "chg_eff": 0.82},
    "Storage.Hydro.PumpedHydro.OpenLoop":         {"dis_eff": 0.87, "chg_eff": 0.82},
    "Storage.Hydro.Reservoir":                    {"dis_eff": 1.0,  "chg_eff": 0.0},
    "Storage.Hydro.Pondage":                      {"dis_eff": 1.0,  "chg_eff": 0.0},
    "Generation.Hydrogen.FuelCell":               {"eff": 0.55, "voc": 2.0,   "disp": True},
    "Generation.Hydrogen.CCGT":                   {"eff": 0.58, "voc": 1.6,   "disp": True},
    "Generation.Other.DemandResponse":            {"eff": 1.0,  "voc": 200.0, "disp": True},
    "Generation.Other.Adequacy":                  {"eff": 1.0,  "voc": 250.0, "disp": True},
}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or ""


def _is_storage(type_name: str) -> bool:
    t = type_name.lower()
    return any(k in t for k in ["battery", "pumped", "storage", "psh", "reservoir", "pondage"])


def _carrier_for_type(type_name: str) -> str:
    t = type_name.lower()
    if any(k in t for k in ["battery"]):              return "electricity"
    if any(k in t for k in ["pumped", "psh"]):        return "water"
    if "hydrogen" in t:                               return "hydrogen"
    if "wind"     in t:                               return "wind"
    if "solar"    in t or "pv" in t:                  return "solar"
    if any(k in t for k in ["hydro", "run", "ror", "pondage", "reservoir"]): return "water"
    if "biomass"  in t or "biogas" in t:              return "biomass"
    if "nuclear"  in t:                               return "uranium"
    if "lignite"  in t:                               return "lignite"
    if "hard coal" in t:                              return "hard_coal"
    if "oil shale" in t:                              return "oil_shale"
    if "oil"      in t:                               return "oil"
    if "gas"      in t:                               return "natural_gas"
    if "demand"   in t:                               return "electricity"
    return "electricity"


def carry_forward_year_per_group(
    df: pd.DataFrame,
    *,
    year_col: str = "Year",
    requested_year: int,
    group_cols: list[str],
) -> pd.DataFrame:
    out = df.copy()
    out[year_col] = pd.to_numeric(out[year_col], errors="coerce").astype("Int64")

    def pick_year(s: pd.Series) -> int:
        years = sorted([int(x) for x in s.dropna().unique()])
        le = [y for y in years if y <= int(requested_year)]
        return le[-1] if le else years[0]

    chosen = (
        out.groupby(group_cols, dropna=False)[year_col]
           .apply(pick_year)
           .reset_index()
           .rename(columns={year_col: "_chosen_year"})
    )
    out = out.merge(chosen, on=group_cols, how="left")
    out = out[out[year_col] == out["_chosen_year"]].drop(columns=["_chosen_year"])
    return out


# ---------------------------------------------------------------------------
# Elementary EAR creation helpers
# ---------------------------------------------------------------------------

_TYNDP_TYPE_TO_HYDRO_CATEGORY: dict[str, str] = {
    "Storage.Hydro.Reservoir":              "reservoir_hydro",
    "Storage.Hydro.Pondage":                "reservoir_hydro",
    "Storage.Hydro.PumpedHydro.ClosedLoop": "phs_closed_loop",
    "Storage.Hydro.PumpedHydro.OpenLoop":   "phs_open_loop",
}

def _add_carrier_or_resource_if_missing(model: CesdmModel, carrier_name: str) -> str:
    """Create/reuse a carrier or natural resource entity.

    ``CARRIER_ID_MAP`` now maps wind/solar/water to ``resource.*`` ids.
    These must be NaturalResource entities, not Carrier entities.
    """
    cid = ENERGY_CARRIER_MAP.get(_slug(carrier_name), f"carrier.{_slug(carrier_name)}")

    # Natural resources are not Carriers and must not be attached to
    # CarrierDomain.hasCarrier. This prevents resource.water from being created
    # as Carrier and later failing storesResource validation.
    if cid.startswith("resource."):
        if cid not in model.entities.get("NaturalResource", {}):
            model.add_entity(entity_class="NaturalResource", entity_id=cid)
            model.add_attribute(cid, "name", carrier_name)
            if "water" in cid:
                model.add_attribute(cid, "resource_group", "hydro")
                model.add_attribute(cid, "resource_type", "water_inflow")
            elif "wind" in cid:
                model.add_attribute(cid, "resource_group", "renewable")
                model.add_attribute(cid, "resource_type", "wind")
            elif "solar" in cid:
                model.add_attribute(cid, "resource_group", "renewable")
                model.add_attribute(cid, "resource_type", "solar_irradiance")
        return cid

    if cid not in model.entities.get("Carrier", {}):
        model.add_entity(entity_class="Carrier", entity_id=cid)
        model.add_attribute(cid, "name", carrier_name)
    if "electricity" in cid:
        # attach electricity carrier to the domain
        model.add_relation(DOMAIN_ID, "hasCarrier", cid)
    return cid


def _add_generator_type_if_missing(
    model: CesdmModel,
    type_name: str,
    input_carrier_id: str | None,
    output_carrier_id: str | None,
) -> str | None:
    """Create/reuse a GeneratorType technology entry.

    GeneratorType is a technology/library type. It may carry hasInputCarrier and
    hasOutputCarrier. DemandResponse is a special adequacy/flexibility
    pseudo-generation type and does not get a physical hasInputCarrier.
    """
    slug = _slug(type_name)
    if slug not in TECH_HIERARCHY:
        print(f"[WARN] '{type_name}' not in TECH_HIERARCHY — skipped")
        return None

    tt_id = TECH_HIERARCHY[slug]

    # Defensive compatibility: older extracted schemas may still have
    # GeneratorType without these relation declarations.
    gen_cls = model.classes.get("GeneratorType")
    if gen_cls is not None:
        rels = getattr(gen_cls, "relations", None)
        if isinstance(rels, dict):
            if "hasInputCarrier" not in rels:
                rels["hasInputCarrier"] = {"target": ["Carrier"], "required": False}
            if "hasInputResource" not in rels:
                rels["hasInputResource"] = {"target": ["NaturalResource"], "required": False}
            if "hasOutputCarrier" not in rels:
                rels["hasOutputCarrier"] = {"target": ["Carrier"], "required": False}

    if tt_id not in model.entities.get("GeneratorType", {}):
        model.add_entity(entity_class="GeneratorType", entity_id=tt_id)
        model.add_attribute(tt_id, "name", type_name)
    else:
        model.add_attribute(tt_id, "name", tt_id)

    # DemandResponse is not a physical carrier conversion. Natural resources
    # use hasInputResource; transported commodities use hasInputCarrier.
    if input_carrier_id and "DemandResponse" not in tt_id:
        if str(input_carrier_id).startswith("resource."):
            model.add_relation(tt_id, "hasInputResource", input_carrier_id)
        else:
            model.add_relation(tt_id, "hasInputCarrier", input_carrier_id)
    if output_carrier_id:
        model.add_relation(tt_id, "hasOutputCarrier", output_carrier_id)

    td = TYNDP_TECH_DATA.get(tt_id, {})
    if "eff" in td:
        model.add_attribute(tt_id, "energy_conversion_efficiency", td["eff"])
    if "disp" in td:
        model.add_attribute(tt_id, "dispatch_type",
                            "dispatchable" if td["disp"] else "nondispatchable")
    if "voc" in td:
        model.add_attribute(tt_id, "variable_operating_cost", td["voc"])
    if "ramp_up" in td:
        model.add_attribute(tt_id, "maximum_ramp_rate_up", td["ramp_up"])
    if "ramp_dn" in td:
        model.add_attribute(tt_id, "maximum_ramp_rate_down", td["ramp_dn"])

    return tt_id


def _add_hydro_generator_type_if_missing(model: CesdmModel,
                                            is_reversible: bool = False) -> str:
    """Ensure the GeneratorType for hydro or PHS generators exists and return its id.

    is_reversible=False → Generation.Renewable.Hydro.Reservoir (pure turbine)
    is_reversible=True  → Generation.Renewable.Hydro.PHS.ClosedLoop (pump-turbine)

    Also ensures the OpenLoop PHS type when is_reversible=True so that both
    PHS types are always available after the first PHS composite is created.

    Required even when the default library is not imported, because
    HydroGenerationUnit.hasTechnology must resolve to an existing entity.
    """
    tt_id = ("Generation.Renewable.Hydro.PHS.ClosedLoop"
             if is_reversible else "Generation.Renewable.Hydro.Reservoir")

    # Defensive compatibility: ensure GeneratorType accepts carrier relations.
    gen_cls = model.classes.get("GeneratorType")
    if gen_cls is not None:
        rels = getattr(gen_cls, "relations", None)
        if isinstance(rels, dict):
            rels.setdefault("hasInputCarrier", {"target": ["Carrier"], "required": False})
            rels.setdefault("hasInputResource", {"target": ["NaturalResource"], "required": False})
            rels.setdefault("hasOutputCarrier", {"target": ["Carrier"], "required": False})

    # Create the requested type and both PHS variants if needed
    type_ids = [tt_id]
    if is_reversible:
        type_ids = [
            "Generation.Renewable.Hydro.PHS.ClosedLoop",
            "Generation.Renewable.Hydro.PHS.OpenLoop",
        ]
    for tid in type_ids:
        if tid not in model.entities.get("GeneratorType", {}):
            model.add_entity(entity_class="GeneratorType", entity_id=tid)
            model.add_attribute(tid, "name", tid)
            model.add_relation(tid, "hasInputResource", "resource.water")
            model.add_relation(tid, "hasOutputCarrier", ELECTRICITY_CARRIER_ID)
            model.add_attribute(tid, "dispatch_type", "dispatchable")
            eff = 0.87 if "PHS" in tid else 0.90
            model.add_attribute(tid, "energy_conversion_efficiency", eff)
    return tt_id



def _add_storage_type_if_missing(
    model: CesdmModel,
    type_name: str,
    input_carrier_id: str,
    output_carrier_id: str,
) -> str | None:
    """
    Return (or create) a StorageType entity.
    If the default library was loaded the entity already exists — just return
    its id.  Only create and populate attributes when not already present.
    """
    slug = _slug(type_name)
    if slug not in TECH_HIERARCHY:
        print(f"[WARN] '{type_name}' not in TECH_HIERARCHY — skipped")
        return None

    tt_id = TECH_HIERARCHY[slug]
    if tt_id in model.entities.get("StorageType", {}):
        # Loaded from library — ensure carrier relation is set
        ent_data = getattr(model.entities["StorageType"][tt_id], "data", {})
        if "hasCarrier" not in ent_data:
            model.add_relation(tt_id, "hasCarrier", output_carrier_id)
        return tt_id

    # Not in library — create on-the-fly with techno-economic defaults.
    # Hydro/PHS classification is NOT stored on StorageType (see schema P0);
    # use GeneratorType on HydroGenerationUnit + hydro_utils instead.
    model.add_entity(entity_class="StorageType", entity_id=tt_id)
    model.add_attribute(tt_id, "name", tt_id)
    model.add_relation(tt_id, "hasCarrier", output_carrier_id)

    key = TECH_HIERARCHY.get(_slug(
        "pump_storage_open_loop"  if "pump_storage_open_loop"  in slug else
        "pump_storage_closed_loop" if "pump_storage_closed_loop" in slug else
        "battery_storage"          if "battery_storage"          in slug else
        "pondage"                  if "pondage"                  in slug else
        "reservoir"                if "reservoir"                in slug else
        type_name
    ), tt_id)

    td = TYNDP_TECH_DATA.get(key, {})
    if "dis_eff" in td:
        model.add_attribute(tt_id, "discharging_efficiency", td["dis_eff"])
    if "chg_eff" in td:
        model.add_attribute(tt_id, "charging_efficiency",    td["chg_eff"])
    if "voc" in td:
        model.add_attribute(tt_id, "variable_operating_cost", td["voc"])
    return tt_id


def _register_profile_entity(
    model: CesdmModel,
    profiles_values: dict,
    prof_id: str,
    values: np.ndarray,
    profile_type: str,
    profile_unit: str,
    ts_id: str,
) -> None:
    """
    Register a Profile entity in the model and store its numeric payload
    in profiles_values for later HDF5 export.

    Parameters
    ----------
    model          : CesdmModel
    profiles_values: accumulator dict { prof_id → np.ndarray }
    prof_id        : entity id for the Profile
    values         : numpy array of numeric values
    profile_type   : "as_SI" | "as_capacity_factor" | "as_normalized_annual_energy"
    profile_unit   : SI unit string or "pu"
    ts_id          : id of the TimestampSeries entity this profile references
    """
    if prof_id not in model.entities.get("Profile", {}):
        model.add_entity(entity_class="Profile", entity_id=prof_id)
        model.add_attribute(prof_id, "profile_type",   profile_type)
        model.add_attribute(prof_id, "profile_unit",   profile_unit)
        model.add_attribute(prof_id, "data_reference", f"/profiles/{prof_id}")
        model.add_relation(prof_id,  "hasTimestampSeries", ts_id)

    profiles_values[prof_id] = values


# ---------------------------------------------------------------------------
# CSV ingestion functions
# ---------------------------------------------------------------------------

def assign_nodes_and_countries_from_tyndp_nodes_csv(
    model: CesdmModel,
    nodes_csv_path: str,
) -> dict:
    """
    Reads TYNDP24_Nodes.csv → GeographicalRegion + ElectricalBus entities.

    V4 changes vs V1
    ----------------
    EnergyNode        → ElectricalBus
    EnergyDomain      → CarrierDomain
    isInEnergyDomain  → belongsToCarrierDomain
    isInGeographicalRegion → belongsToGeographicalRegion
    hasEnergyCarrier  → hasCarrier
    """
    df = pd.read_csv(nodes_csv_path)

    # CarrierDomain (electricity)
    if DOMAIN_ID not in model.entities.get("CarrierDomain", {}):
        model.add_entity(entity_class="CarrierDomain", entity_id=DOMAIN_ID)
        model.add_attribute(DOMAIN_ID, "name", "Electricity Domain")

    elec_id = _add_carrier_or_resource_if_missing(model, "electricity")
    model.add_relation(DOMAIN_ID, "hasCarrier", elec_id)

    created_nodes = created_countries = updated_nodes = updated_countries = 0

    for _, row in df.iterrows():
        node_code = str(row["Node"]).strip()
        cc        = str(row["Country"]).strip()
        cc_name   = str(row.get("Country_spelledOut", cc)).strip()

        rid = country_region_id(cc)
        existed = model.has_entity(rid)
        country_id = ensure_country_region(model, cc, name=cc_name)
        if existed:
            updated_countries += 1
        else:
            created_countries += 1

        bus_id = f"node.{_slug(node_code)}"

        # ElectricalBus
        if bus_id not in model.entities.get("ElectricalBus", {}):
            model.add_entity(entity_class="ElectricalBus", entity_id=bus_id)
            created_nodes += 1
        else:
            updated_nodes += 1
        model.add_attribute(bus_id, "name", node_code)
        model.add_relation(bus_id, "belongsToCarrierDomain", DOMAIN_ID)
        model.add_relation(bus_id, "belongsToGeographicalRegion", country_id)

    return {
        "countries_created": created_countries, "countries_updated": updated_countries,
        "nodes_created": created_nodes,         "nodes_updated": updated_nodes,
        "rows": int(df.shape[0]),
    }


def assign_installed_capacity_from_tyndp_csv(
    model: CesdmModel,
    installed_capacity_csv_path: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> None:
    """
    Reads TYNDP24_InstalledCapacities.csv.

    V4 changes vs V1
    ----------------
    EnergyConversionTechnology1x1 → GenerationUnit, dispatch attributes
      (nominal_power_capacity, variable_operating_cost, dispatch_type,
      efficiency) and atNode held directly on the asset itself (see
      CHANGELOG.md: the direct EAR asset model)
    EnergyStorageTechnology       → StorageUnit, same flattened pattern
      (nominal_power_capacity, maximum_charging_power, atNode)
    TechnologyType                → GeneratorType  (shared techno-economic params)
    StorageTechnologyType         → StorageType    (shared techno-economic params)
    instanceOf                    → hasTechnology
    isOutputNodeOf/isConnectedToNode → atNode
    hasInputEnergyCarrier         → GeneratorType.hasInputCarrier
    hasOutputEnergyCarrier        → GeneratorType.hasOutputCarrier
    """
    df = pd.read_csv(Path(installed_capacity_csv_path))

    if "Variable" in df.columns:
        df = df[df["Variable"].astype(str).str.contains("Installed|Charging", case=False, na=False)]
    if policy is not None and "Policy" in df.columns:
        df = df[df["Policy"] == policy]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node"])
    if climate_year is not None and "Climate Year" in df.columns:
        df = df[df["Climate Year"] == climate_year]
    if drop_zero and "Value" in df.columns:
        df = df[df["Value"].fillna(0.0) != 0.0]

    df["Type"]    = df["Type"].astype(str).str.strip()
    df["Node"]    = df["Node"].astype(str).str.strip()
    df["Country"] = df["Country"].astype(str).str.strip()

    # EnergySystemModel container
    model_id = f"TYNDP_{policy}_{year}"
    if model_id not in model.entities.get("EnergySystemModel", {}):
        model.add_entity(entity_class="EnergySystemModel", entity_id=model_id)
    if year and year in CO2_PRICE:
        model.add_attribute(model_id, "co2_price", CO2_PRICE[year])

    group_cols = [c for c in ["Type", "Node", "Country", "Policy", "Year", "Variable", "Climate Year"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)["Value"].sum()

    for _, row in df_agg.iterrows():
        type_name = str(row["Type"])
        node_code = str(row["Node"]).strip()[:4]
        load_type = _slug(str(row["Node"]).strip()[4:])
        country   = str(row.get("Country", ""))
        var       = str(row["Variable"])

        cap_mw   = float(row["Value"]) if "Installed" in var else None
        charg_mw = float(row["Value"]) if "Charging"  in var else None

        if load_type in ("ev_passenger", "sres"):
            continue
        if type_name in ("Electrolyser (load)", "CH4 Heat Pump (load)", "H2 Heat Pump (load)"):
            continue
        if _slug(type_name) not in TECH_HIERARCHY:
            print(f"[WARN] '{type_name}' not in TECH_HIERARCHY — skipped")
            continue

        bus_id = f"node.{_slug(node_code)}"
        if bus_id not in model.entities.get("ElectricalBus", {}):
            continue

        # GeographicalRegion (country level) — prefer regions_library ids
        ensure_country_region(model, country, name=node_code)
        cid = country_region_id(country)
        model.add_relation(bus_id, "belongsToGeographicalRegion", cid)

        in_carrier_id  = _add_carrier_or_resource_if_missing(model, _carrier_for_type(type_name))
        out_carrier_id = ELECTRICITY_CARRIER_ID
        is_stor        = _is_storage(type_name)
        tech_id        = f"tech.{_slug(type_name)}.{_slug(node_code)}"

        if is_stor:
            # ── StorageUnit ──────────────────────────────────────────
            tt_id = _add_storage_type_if_missing(model, type_name, in_carrier_id, out_carrier_id)
            if tt_id is None:
                continue

            storage_class  = _storage_asset_class_for_type(type_name, tt_id)
            is_hydro_res   = (storage_class == "HydraulicStorageUnit")
            is_phs_type    = _is_pumped_hydro_storage_type(type_name, tt_id)
            is_res_hydro   = _is_reservoir_hydro_storage_type(type_name, tt_id)

            if not _entity_exists(model, tech_id):
                model.add_entity(entity_class=storage_class, entity_id=tech_id)
                model.add_attribute(tech_id, "name", f"{type_name} @ {node_code}")
                if is_hydro_res:
                    # Hydro reservoirs/pondage/PHS store the natural resource water,
                    # not an energy carrier.  After the Carrier/Resource split,
                    # resource.water must therefore be linked via storesResource.
                    # No hasTechnology→StorageType: HydraulicStorageUnit is not a
                    # battery-style storage template (tech lives on the paired
                    # HydroGenerationUnit / GeneratorType).
                    model.add_relation(tech_id, "storesResource", "resource.water")
                    # No atNode here: HydraulicStorageUnit is a standalone
                    # class (not a StorageUnit subclass), with no atNode of
                    # its own at all -- a reservoir genuinely has no direct
                    # electrical role, only the paired HydroGenerationUnit
                    # (connected further below) does.
                else:
                    model.add_relation(tech_id, "hasTechnology", tt_id)
                    model.add_relation(tech_id, "storesCarrier", in_carrier_id)
                    model.add_relation(tech_id, "atNode", bus_id)

            # HydraulicStorageUnit and StorageUnit both hold their dispatch
            # attributes directly on themselves (see CHANGELOG.md).
            sdv = tech_id
            def _sgav(attr, default=0.0):
                return model.get_attribute_value(sdv, attr, default)

            # Power attrs: hydro -> held on the paired generator directly;
            # battery -> held on the storage asset itself
            _pending_cap_mw   = cap_mw    if is_hydro_res else None
            _pending_charg_mw = charg_mw  if is_hydro_res else None
            if not is_hydro_res:
                if cap_mw is not None:
                    current = _sgav("nominal_power_capacity", 0.0)
                    model.add_attribute(sdv, "nominal_power_capacity",
                                        {"value": cap_mw + current, "unit": "MW"})
                if charg_mw is not None:
                    current = _sgav("maximum_charging_power", 0.0)
                    model.add_attribute(sdv, "maximum_charging_power",
                                        {"value": charg_mw + current, "unit": "MW"})
                if _sgav("maximum_discharging_power", None) is None:
                    charging_power = _sgav("maximum_charging_power", None)
                    if charging_power is not None:
                        # TYNDP's storage rows only ever give a charging
                        # figure, never a separate discharging one --
                        # assume symmetric charge/discharge power (a
                        # common simplification for battery/PHS ratings)
                        # rather than leaving maximum_discharging_power
                        # unset entirely.
                        model.add_attribute(sdv, "maximum_discharging_power",
                                            {"value": charging_power, "unit": "MW"})

            # Reservoir hydro composite
            if is_res_hydro:
                model.add_relation(tech_id, "storesResource", "resource.water")
                _add_hydro_reservoir_composite_if_missing(
                    model,
                    reservoir_id=tech_id,
                    bus_id=bus_id,
                    power_capacity=_pending_cap_mw,
                    resource_potential=None,
                )

            if is_phs_type:
                # Create/update paired HydroGenerationUnit (reversible pump-turbine)
                gen_id = _hydro_generator_id(tech_id)
                if gen_id not in model.entities.get("HydroGenerationUnit", {}):
                    model.add_entity(entity_class="HydroGenerationUnit", entity_id=gen_id)
                    model.add_attribute(gen_id, "name", gen_id)
                model.add_attribute(gen_id, "turbine_type", "reversible_francis")
                phs_gen_tt = ("Generation.Renewable.Hydro.PHS.OpenLoop"
                              if "OpenLoop" in str(tt_id)
                              else "Generation.Renewable.Hydro.PHS.ClosedLoop")
                # Ensure GeneratorType entity exists before referencing it
                _add_hydro_generator_type_if_missing(model, is_reversible=True)
                model.add_relation(gen_id, "hasTechnology", phs_gen_tt)
                model.add_relation(gen_id, "drawsFromHydraulicStorage", tech_id)
                if bus_id:
                    model.add_relation(gen_id, "atNode", bus_id)

                # Power/efficiency attrs held directly on the generator itself.
                # Read defaults from the StorageType library entry when the TYNDP
                # input only provides power values.
                gv_phs = gen_id
                model.add_attribute(gv_phs, "dispatch_type", "dispatchable")
                model.add_attribute(gv_phs, "hydro_machine_kind", hydro_machine_kind(phs_gen_tt, is_reversible=True))
                if cap_mw is not None:
                    model.add_attribute(gv_phs, "nominal_power_capacity",
                                        {"value": cap_mw, "unit": "MW"})
                if charg_mw is not None:
                    model.add_attribute(gv_phs, "maximum_pumping_power",
                                        {"value": charg_mw, "unit": "MW"})
                turbine_eff = model.get_attr_value("StorageType", tt_id, "discharging_efficiency", None)
                pumping_eff = model.get_attr_value("StorageType", tt_id, "charging_efficiency", None)
                if turbine_eff is not None:
                    model.add_attribute(gv_phs, "turbine_efficiency", turbine_eff)
                if pumping_eff is not None:
                    model.add_attribute(gv_phs, "pumping_efficiency", pumping_eff)

        else:
            # ── GenerationUnit ───────────────────────────────────────
            tt_id = _add_generator_type_if_missing(model, type_name, in_carrier_id, out_carrier_id)
            if tt_id is None:
                continue

            generation_class = _generation_asset_class_for_type(type_name, tt_id)
            if not _entity_exists(model, tech_id):
                model.add_entity(entity_class=generation_class, entity_id=tech_id)
                model.add_attribute(tech_id, "name", f"{type_name} @ {node_code}")
                model.add_relation(tech_id, "hasTechnology", tt_id)
                model.add_relation(tech_id, "atNode", bus_id)
            gdv = tech_id
            if cap_mw is not None:
                current = model.get_attribute_value(gdv, "nominal_power_capacity", 0.0)
                model.add_attribute(gdv, "nominal_power_capacity",
                                    {"value": cap_mw + current, "unit": "MW"})

            # Materialise source-specific techno-economic values directly on
            # the asset itself. The GeneratorType/Carrier entries remain
            # reusable defaults, but export adapters must not have to infer
            # an asset's actual FlexECO values from shared library entities.
            td = TYNDP_TECH_DATA.get(tt_id, {})
            if "eff" in td:
                # HydroGenerationUnit uses turbine_efficiency rather than
                # the generic energy_conversion_efficiency attribute.
                efficiency_attribute = (
                    "turbine_efficiency"
                    if generation_class == "HydroGenerationUnit"
                    else "energy_conversion_efficiency"
                )
                model.add_attribute(gdv, efficiency_attribute, td["eff"])
            if "disp" in td:
                model.add_attribute(
                    gdv, "dispatch_type",
                    "dispatchable" if td["disp"] else "nondispatchable",
                )
            if "voc" in td:
                model.add_attribute(gdv, "variable_operating_cost", td["voc"])
            if "ramp_up" in td:
                model.add_attribute(gdv, "maximum_ramp_rate_up", td["ramp_up"])
            if "ramp_dn" in td:
                model.add_attribute(gdv, "maximum_ramp_rate_down", td["ramp_dn"])

            # Carrier prices are stored only on Carrier entities below.
            # Generation assets contain generator-specific operating costs, not fuel prices.

            if "DemandResponse" in tt_id:
                model.add_attribute(gdv, "variable_operating_cost", {"value": 300.0})

    # Carrier CO₂ intensities and prices
    for carrier, co2 in ENERGY_CARRIER_CO2.items():
        if carrier in model.entities.get("Carrier", {}):
            model.add_attribute(carrier, "co2_emission_intensity", co2)
    if year and year in ENERGY_CARRIER_PRICE:
        for carrier, price in ENERGY_CARRIER_PRICE[year].items():
            if carrier in model.entities.get("Carrier", {}):
                model.add_attribute(carrier, "energy_carrier_cost", price)


def assign_demand_from_tyndp_csv(
    model: CesdmModel,
    installed_capacity_csv_path: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> None:
    """
    Reads TYNDP24_InstalledCapacities.csv (Electrolyser / heat-pump rows).

    V4 changes vs V1
    ----------------
    EnergyDemand          → DemandUnit, dispatch attributes
      (maximum_energy_demand) and atNode held directly on the asset itself
    isConnectedToNode     → atNode
    """
    df = pd.read_csv(Path(installed_capacity_csv_path))

    if "Variable" in df.columns:
        df = df[df["Variable"].astype(str).str.contains("Installed|Charging", case=False, na=False)]
    if "Type" in df.columns:
        df = df[df["Type"].astype(str).str.contains("Electrolyser|CH4 Heat Pump", case=False, na=False)]
    if policy is not None and "Policy" in df.columns:
        df = df[df["Policy"] == policy]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node"])
    if climate_year is not None and "Climate Year" in df.columns:
        df = df[df["Climate Year"] == climate_year]
    if drop_zero and "Value" in df.columns:
        df = df[df["Value"].fillna(0.0) != 0.0]

    df["Type"]    = df["Type"].astype(str).str.strip()
    df["Node"]    = df["Node"].astype(str).str.strip()
    df["Country"] = df["Country"].astype(str).str.strip()

    group_cols = [c for c in ["Type", "Node", "Country", "Policy", "Year", "Variable", "Climate Year"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)["Value"].sum()

    for _, row in df_agg.iterrows():
        type_name = str(row["Type"])
        node_code = str(row["Node"]).strip()[:4]
        load_type = _slug(str(row["Node"]).strip()[4:])
        cap_mw    = float(row["Value"]) if "Installed" in str(row.get("Variable", "")) else None

        bus_id = f"node.{_slug(node_code)}"
        if bus_id not in model.entities.get("ElectricalBus", {}):
            continue

        if "Electrolyser" in type_name:
            subtype = "electricity.electrolyse"
        elif "CH4 Heat Pump" in type_name:
            subtype = "electricity.heatpump"
        else:
            continue

        demand_id = (f"demand.{_slug(subtype)}.{load_type}.{_slug(node_code)}"
                     if load_type else f"demand.{_slug(subtype)}.{_slug(node_code)}")

        if demand_id not in model.entities.get("DemandUnit", {}):
            model.add_entity(entity_class="DemandUnit", entity_id=demand_id)
            model.add_attribute(demand_id, "name", f"{type_name} @ {node_code}")
            model.add_relation(demand_id, "atNode", bus_id)
        # DemandUnit holds the demand capacity directly (see CHANGELOG.md).
        wdv = demand_id
        if cap_mw is not None:
            current = model.get_attribute_value(wdv, "maximum_energy_demand", 0.0)
            model.add_attribute(wdv, "maximum_energy_demand",
                                {"value": cap_mw + current, "unit": "MW"})


def assign_energy_storage_capacity_from_tyndp_csv(
    model: CesdmModel,
    storage_cap_csv_path: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> dict:
    """
    Reads TYNDP24_StorageCapacities.csv -> sets energy_storage_capacity
    directly on the storage asset itself.
    """
    df = pd.read_csv(storage_cap_csv_path)

    policy = policy or "NT"
    if "Variable" in df.columns:
        df = df[df["Variable"].astype(str).str.contains("Capacity", case=False, na=False)]
    if policy and "Policy" in df.columns:
        df = df[df["Policy"] == policy]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node"])
    if drop_zero and "Value" in df.columns:
        df = df[df["Value"].fillna(0.0) != 0.0]

    group_cols = [c for c in ["Type", "Node", "Policy", "Year"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)["Value"].sum()

    assigned, missing = 0, []

    for _, row in df_agg.iterrows():
        type_name = str(row["Type"])
        node_code = str(row["Node"])
        e_mwh     = float(row["Value"])

        slug = _slug(type_name)
        if   "pump_storage_open_loop"  in slug: slug = "pump_storage_open_loop"
        elif "pump_storage_closed_loop" in slug: slug = "pump_storage_closed_loop"
        elif "battery_storage"          in slug: slug = "battery_storage"
        elif "reservoir"                in slug: slug = "reservoir"

        storage_id = f"tech.{slug}.{_slug(node_code)}"
        if _entity_exists(model, storage_id):
            storage_cls = _entity_class(model, storage_id)
            sdv = storage_id
            model.add_attribute(sdv, "energy_storage_capacity",
                                {"value": e_mwh, "unit": "MWh"})
            assigned += 1
        else:
            missing.append(storage_id)

    return {"assigned": assigned, "missing_count": len(missing), "missing_examples": missing[:20]}


def assign_demand_from_tyndp_timeseries_csv(
    model: CesdmModel,
    profiles_values: dict,
    demand_csv_path: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    timestamp_series_id: str = "timestamp.hourly",
    drop_zero: bool = True,
) -> dict:
    """
    Reads TYNDP24_DemandProfiles.csv.

    V4 changes vs V1
    ----------------
    EnergyDemand        → DemandUnit, dispatch attributes
      (annual_energy_demand, demand_profile_reference, demand_type,
      is_demand_flexible, value_of_lost_load) and atNode held directly
      on the asset itself
    profile dict key    → Profile entity with hasTimestampSeries (new in V4)
    """
    df = pd.read_csv(demand_csv_path)

    if policy is not None and "Policy" in df.columns:
        df = df[df["Policy"].fillna(policy) == policy]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node", "Type"])
    if climate_year is not None and "Climate" in df.columns:
        df = df[df["Climate"].fillna(climate_year) == climate_year]

    ts_cols   = [c for c in df.columns if c.isdigit()]
    df[ts_cols] = df[ts_cols].apply(pd.to_numeric, errors="coerce")

    group_cols = [c for c in ["ID", "Type", "Node", "Policy", "Year", "Climate"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)[ts_cols].sum()

    created = updated = 0
    for _, row in df_agg.iterrows():
        node_code = str(row["Node"]).strip()[:4]
        load_type = _slug(str(row["Node"]).strip()[4:])
        bus_id    = f"node.{_slug(node_code)}"
        typ       = str(row.get("Type", "")).strip()

        if bus_id not in model.entities.get("ElectricalBus", {}):
            continue

        if "Demand" in typ:
            subtype = "electricity"
        elif "Electrolyser" in typ:
            subtype = "electricity.electrolyse"
        elif "CH4 Heat Pump" in typ:
            subtype = "electricity.heatpump"
        else:
            continue

        ts      = np.array([float(x) if pd.notna(x) else 0.0 for x in row[ts_cols]])
        ts      = np.concatenate([ts, ts[-24:]])        # pad to 8784
        ts      = np.abs(ts)
        annual  = float(ts.sum())
        if drop_zero and annual == 0:
            continue

        demand_id = (f"demand.{_slug(subtype)}.{load_type}.{_slug(node_code)}"
                     if load_type else f"demand.{_slug(subtype)}.{_slug(node_code)}")
        prof_id   = (f"profile.demand.{_slug(subtype)}.{load_type}.{_slug(node_code)}"
                     if load_type else f"profile.demand.{_slug(subtype)}.{_slug(node_code)}")
        demand_type = f"{_slug(subtype)}.{load_type}" if load_type else _slug(subtype)

        if demand_id not in model.entities.get("DemandUnit", {}):
            model.add_entity(entity_class="DemandUnit", entity_id=demand_id)
            model.add_attribute(demand_id, "name",
                                f"Demand {_slug(subtype)} {load_type} {node_code}")
            model.add_relation(demand_id, "atNode", bus_id)
            created += 1
        else:
            updated += 1
        # DemandUnit -- all operational attributes held directly on itself
        wdv = demand_id
        model.add_attribute(wdv, "annual_energy_demand",
                            {"value": annual, "unit": "MWh/year"})
        model.add_relation(wdv, "hasDemandProfile", prof_id)
        model.add_attribute(wdv, "demand_type",              {"value": demand_type})
        if "electrolyse" in subtype:
            model.add_attribute(wdv, "is_demand_flexible",          {"value": True})
            model.add_attribute(wdv, "flexibility_window_time_end", {"value": 8760})
            model.add_attribute(wdv, "flexibility_time_resolution", {"value": 8760})
            model.add_attribute(wdv, "value_of_lost_load",          {"value": 50.0})

        # Profile entity + numeric payload → HDF5
        _register_profile_entity(
            model, profiles_values, prof_id,
            values       = -ts / annual,
            profile_type = "as_normalized_annual_energy",
            profile_unit = "pu",
            ts_id        = timestamp_series_id,
        )

    return {"created": created, "updated": updated, "rows": int(df_agg.shape[0])}


def assign_renewable_timeseries_from_csv(
    model: CesdmModel,
    profiles_values: dict,
    renewable_csv_path: str,
    *,
    renewable_type: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    timestamp_series_id: str = "timestamp.hourly",
    drop_zero: bool = True,
) -> dict:
    """
    Reads TYNDP24_GenProfiles.csv.

    V4 changes vs V1
    ----------------
    annual_resource_potential, resource_potential_profile_reference
      → held directly on GenerationUnit itself
    profile dict key → Profile entity (V4 new)
    """
    df = pd.read_csv(renewable_csv_path)

    if renewable_type is not None and "Type" in df.columns:
        df = df[df["Type"].fillna(renewable_type) == renewable_type]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node", "Type"])
    if climate_year is not None and "Climate Year" in df.columns:
        df = df[df["Climate Year"].fillna(climate_year) == climate_year]

    ts_cols   = [c for c in df.columns if c.isdigit()]
    df[ts_cols] = df[ts_cols].apply(pd.to_numeric, errors="coerce")
    if drop_zero:
        df = df[df[ts_cols].sum(axis=1, skipna=True) != 0.0]

    group_cols = [c for c in ["ID", "Node", "Country", "Type", "Year", "Climate Year", "Unit"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)[ts_cols].sum()

    created = updated = 0
    for _, row in df_agg.iterrows():
        node_code = str(row["Node"]).strip()
        typ       = str(row.get("Type", "")).strip()

        # Map TYNDP type string → V4 tech_id slug
        if   "LFSolarPVRooftop" in typ: slug = "solar_photovoltaic_rooftop"
        elif "LFSolarPVUtility"  in typ: slug = "solar_photovoltaic_utility"
        elif "SolarPV"           in typ: slug = "solar_photovoltaic"
        elif "CSP_noStorage"     in typ: slug = "solar_thermal"
        elif "Wind_Offshore"     in typ: slug = "wind_offshore"
        elif "Wind_Onshore"      in typ: slug = "wind_onshore"
        else: continue

        tech_id = f"tech.{slug}.{_slug(node_code)}"
        prof_id = f"profile.{slug}.{_slug(node_code)}"

        asset_cls = _entity_class(model, tech_id)
        if asset_cls not in {"GenerationUnit", "HydroGenerationUnit"}:
            continue

        ts     = np.array([float(x) if pd.notna(x) else 0.0 for x in row[ts_cols]])
        annual = ts.sum()

        gdv = tech_id
        cap = model.get_attribute_value(gdv, "nominal_power_capacity", None)
        if cap is None:
            continue

        model.add_attribute(gdv, "annual_resource_potential",
                            {"value": float(annual * cap)})
        model.add_relation(gdv, "hasAvailabilityProfile", prof_id)

        # Profile entity + numeric payload → HDF5
        _register_profile_entity(
            model, profiles_values, prof_id,
            values       = ts / annual,
            profile_type = "as_normalized_annual_energy",
            profile_unit = "pu",
            ts_id        = timestamp_series_id,
        )
        created += 1

    return {"created": created, "updated": updated, "rows": int(df_agg.shape[0])}


def assign_inflow_timeseries_from_csv(
    model: CesdmModel,
    profiles_values: dict,
    inflow_csv_path: str,
    *,
    renewable_type: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    timestamp_series_id: str = "timestamp.hourly",
    drop_zero: bool = True,
) -> dict:
    """
    Reads TYNDP24_HydroInflows.csv.

    V4 changes vs V1
    ----------------
    annual_resource_potential / resource_potential_profile_reference
      → held directly on the GenerationUnit itself (run-of-river)
    annual_natural_inflow_energy / natural_inflow_profile_reference
      → held directly on the StorageUnit/HydraulicStorageUnit itself
    profile dict key → Profile entity (V4 new)
    """
    df = pd.read_csv(inflow_csv_path)

    if renewable_type is not None and "Type" in df.columns:
        df = df[df["Type"].fillna(renewable_type) == renewable_type]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node", "Type"])
    if climate_year is not None and "Climate Year" in df.columns:
        df = df[df["Climate Year"].fillna(climate_year) == climate_year]

    ts_cols   = [c for c in df.columns if c.isdigit()]
    df[ts_cols] = df[ts_cols].apply(pd.to_numeric, errors="coerce")
    if drop_zero:
        df = df[df[ts_cols].sum(axis=1, skipna=True) != 0.0]

    group_cols = [c for c in ["ID", "Node", "Country", "Type", "Year", "Climate Year", "Variable"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)[ts_cols].sum()

    created = updated = 0
    for _, row in df_agg.iterrows():
        node_code = str(row["Node"]).strip()
        typ       = str(row.get("Type", "")).strip()

        if   "Reservoir"   in typ: slug = "reservoir"
        elif "PS Open"     in typ: slug = "pump_storage_open_loop"
        elif "PS Close"    in typ or "PS Cloase" in typ: slug = "pump_storage_closed_loop"
        elif "Pondage"     in typ: slug = "pondage"
        elif "Run of River" in typ: slug = "run_of_river"
        else: continue

        tech_id = f"tech.{slug}.{_slug(node_code)}"
        prof_id = f"profile.{slug}.{_slug(node_code)}"
        ts      = np.array([float(x) if pd.notna(x) else 0.0 for x in row[ts_cols]])
        annual  = float(ts.sum())
        if annual == 0:
            continue

        asset_cls = _entity_class(model, tech_id)
        if asset_cls in {"GenerationUnit", "HydroGenerationUnit"}:
            # Resource potential on the generator; RoR inflow profile on the
            # linked HydraulicStorageUnit water body when present.
            gdv = tech_id
            model.add_attribute(gdv, "annual_resource_potential",
                                {"value": annual})
            _register_profile_entity(
                model, profiles_values, prof_id,
                values       = ts / annual,
                profile_type = "as_normalized_annual_energy",
                profile_unit = "pu",
                ts_id        = timestamp_series_id,
            )
            if asset_cls == "HydroGenerationUnit":
                res_ids = model.get_relation_targets(gdv, "drawsFromHydraulicStorage") or []
                if res_ids:
                    model.add_relation(res_ids[0], "hasNaturalInflowProfile", prof_id)
                else:
                    model.add_relation(gdv, "hasAvailabilityProfile", prof_id)
            else:
                model.add_relation(gdv, "hasAvailabilityProfile", prof_id)
            created += 1

        elif asset_cls in {"StorageUnit", "HydraulicStorageUnit"}:
            # Reservoir / pumped hydro: store inflow directly on the storage asset.
            sdv = tech_id
            model.add_attribute(sdv, "annual_natural_inflow_energy",
                                {"value": annual})
            model.add_relation(sdv, "hasNaturalInflowProfile", prof_id)
            _register_profile_entity(
                model, profiles_values, prof_id,
                values       = ts / annual,
                profile_type = "as_normalized_annual_energy",
                profile_unit = "pu",
                ts_id        = timestamp_series_id,
            )
            # If this storage asset has a generated HydroGenerationUnit component,
            # mirror the annual inflow as hydro resource potential on the paired generator.
            hydro_gen_id = _hydro_generator_id(tech_id)
            if _entity_exists(model, hydro_gen_id):
                gdv = hydro_gen_id
                model.add_attribute(gdv, "annual_resource_potential", {"value": annual})
            updated += 1

    return {"created": created, "updated": updated, "rows": int(df_agg.shape[0])}


def assign_ntc_from_tyndp_ntc_types_base_csv(
    model: CesdmModel,
    ntc_csv_path: str,
    *,
    scenario_year: int,
    base_type: str = "Base",
    real_types: tuple[str, ...] = ("Real 1", "Real 2"),
    real_years_by_scenario_year: dict[int, list[int]] | None = None,
    base_year: int | None = None,
    base_year_fallback: int = 2025,
    drop_zero: bool = True,
    add_real_only_where_base_link_exists: bool = True,
) -> dict:
    """
    Reads TYNDP24_NTC_types.csv.

    V4 changes vs V1
    ----------------
    NetTransferCapacity → Interconnector (TransmissionElement subclass),
      fromNode/toNode and power-flow attributes (maximum_power_flow_from_to,
      maximum_power_flow_to_from) all held directly on the asset itself
    isFromNodeOf → fromNode
    isToNodeOf   → toNode
    isInEnergyDomain → removed (domain context from ElectricalBus.belongsToCarrierDomain)
    """
    if real_years_by_scenario_year is None:
        real_years_by_scenario_year = {
            2030: [],
            2040: [2030, 2035],
            2050: [2030, 2035, 2040],
        }

    df = pd.read_csv(ntc_csv_path)
    for c in ("P12", "P21"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    base_year_try = base_year if base_year is not None else scenario_year
    base = df[(df["TYPE"].astype(str).str.strip() == base_type) & (df["YEAR"] == base_year_try)].copy()
    base_source_year = base_year_try
    if base.empty:
        base = df[(df["TYPE"].astype(str).str.strip() == base_type) & (df["YEAR"] == base_year_fallback)].copy()
        base_source_year = base_year_fallback

    base = base[["FROM", "TO", "P12", "P21"]].groupby(["FROM", "TO"], as_index=False).sum()

    inc_years = real_years_by_scenario_year.get(int(scenario_year), [])
    inc = df[
        (df["TYPE"].astype(str).str.strip().isin([t.strip() for t in real_types]))
        & (df["YEAR"].isin(inc_years))
    ][["FROM", "TO", "P12", "P21"]].copy()
    if not inc.empty:
        inc = inc.groupby(["FROM", "TO"], as_index=False).sum()
    else:
        inc = pd.DataFrame(columns=["FROM", "TO", "P12", "P21"])

    if add_real_only_where_base_link_exists:
        merged = base.merge(inc, on=["FROM", "TO"], how="left", suffixes=("", "_inc"))
        merged["P12"] += merged["P12_inc"].fillna(0.0)
        merged["P21"] += merged["P21_inc"].fillna(0.0)
        df_final = merged[["FROM", "TO", "P12", "P21"]]
    else:
        df_final = pd.concat([base, inc], ignore_index=True).groupby(["FROM", "TO"], as_index=False).sum()

    if drop_zero:
        df_final = df_final[(df_final["P12"].fillna(0) != 0) | (df_final["P21"].fillna(0) != 0)]

    created = updated = 0
    for _, row in df_final.iterrows():
        frm    = str(row["FROM"]).strip()
        to     = str(row["TO"]).strip()
        frm_id = f"node.{_slug(frm)}"
        to_id  = f"node.{_slug(to)}"

        if frm_id not in model.entities.get("ElectricalBus", {}): continue
        if to_id  not in model.entities.get("ElectricalBus", {}): continue

        ntc_id = f"ntc.{_slug(frm)}_{_slug(to)}"

        if not _entity_exists(model, ntc_id):
            model.add_entity(entity_class="GenericInterconnector", entity_id=ntc_id)
            model.add_attribute(ntc_id, "name", f"NTC {frm}->{to}")
            created += 1
        else:
            updated += 1
        # fromNode/toNode/power-flow attributes held directly on the
        # Interconnector itself (see CHANGELOG.md).
        model.add_relation(ntc_id, "fromNode", frm_id)
        model.add_relation(ntc_id, "toNode",   to_id)
        model.add_attribute(ntc_id, "from_switch_closed", 1)
        model.add_attribute(ntc_id, "to_switch_closed",   1)
        model.add_attribute(ntc_id, "maximum_power_flow_from_to",
                            {"value": float(row["P12"]) if pd.notna(row["P12"]) else 0.0, "unit": "MW"})
        model.add_attribute(ntc_id, "maximum_power_flow_to_from",
                            {"value": float(row["P21"]) if pd.notna(row["P21"]) else 0.0, "unit": "MW"})

    return {
        "created": created, "updated": updated, "rows": int(df_final.shape[0]),
        "scenario_year": int(scenario_year), "base_source_year": int(base_source_year),
        "real_years_added": list(inc_years),
    }


# ---------------------------------------------------------------------------
# Cleanup helpers
# ---------------------------------------------------------------------------

def _entity_data(model: CesdmModel, class_name: str, entity_id: str) -> dict:
    ent = (model.entities.get(class_name) or {}).get(entity_id)
    return getattr(ent, "data", {}) or {}


def _drop_entity_everywhere(model: CesdmModel, entity_id: str) -> None:
    """Remove an entity and dangling references to it from the in-memory model."""
    for ents in model.entities.values():
        ents.pop(entity_id, None)
    for ents in model.entities.values():
        for ent in ents.values():
            data = getattr(ent, "data", {}) or {}
            for key, value in list(data.items()):
                if value == entity_id:
                    data.pop(key, None)
                elif isinstance(value, list):
                    data[key] = [v for v in value if v != entity_id]


def prune_hydro_reservoirs_without_inflow(model: CesdmModel) -> dict:
    """Drop reservoir/pondage hydro assets that have no positive natural inflow.

    PHS/pumped-storage reservoirs are kept even without natural inflow. Reservoir
    and pondage units without an inflow profile/resource are not dispatchable in
    the TYNDP import and create spurious assets, so they are removed together with
    their paired HydroGenerationUnit entities.
    """
    removed: list[str] = []
    for reservoir_id in list((model.entities.get("HydraulicStorageUnit") or {}).keys()):
        # Classify via paired generator tech / flags (no hasTechnology on the basin).
        gen_id = _hydro_generator_id(reservoir_id)
        gen_data = _entity_data(model, "HydroGenerationUnit", gen_id) if _entity_exists(model, gen_id) else {}
        gen_tech = gen_data.get("hasTechnology")
        gen_techs = gen_tech if isinstance(gen_tech, list) else ([gen_tech] if gen_tech else [])
        key = f"{reservoir_id} {gen_id} {' '.join(map(str, gen_techs))}".lower()
        is_phs = any(x in key for x in ("pumped", "pump_storage", "phs", "pumpedhydro"))
        if not is_phs and gen_data:
            if model.get_attribute_value(gen_id, "hydro_machine_kind", None) == "reversible":
                is_phs = True
        if is_phs:
            continue
        if not any(x in key for x in ("reservoir", "pondage")):
            continue
        # HydraulicStorageUnit holds annual_natural_inflow_energy directly
        # (see CHANGELOG.md).
        inflow = model.get_attribute_value(reservoir_id, "annual_natural_inflow_energy", None)
        try:
            inflow_val = float(inflow.get("value", inflow) if isinstance(inflow, dict) else inflow)
        except Exception:
            inflow_val = 0.0
        if inflow_val > 0.0:
            continue
        for eid in (reservoir_id, gen_id):
            _drop_entity_everywhere(model, eid)
        removed.append(reservoir_id)
    return {"removed": len(removed), "removed_ids": removed[:20]}


# ---------------------------------------------------------------------------
# Top-level build function
# ---------------------------------------------------------------------------

def build_cesdm_model_from_tyndp_installed_capacities(
    schema_path: str | os.PathLike,
    data_folder: str = "../data/",
    output_folder: str | os.PathLike = "../output/",
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> None:
    """
    Full TYNDP2024 → CESDM V4 build pipeline.

    Outputs (in output_folder/SC_<policy>_SY_<year>_WY_<climate_year>/):
      cesdm/yaml/   — hierarchical + flat YAML
      cesdm/h5/     — HDF5 with TimestampSeries and all Profile numeric payloads
      cesdm/excel/  — Excel workbook (one sheet per entity class)
      flexeco/      — FlexEco export
    """
    schema_path = Path(schema_path)
    model: CesdmModel = build_model_from_yaml(schema_path)
    import_tyndp_libraries(model)

    profiles_values: dict = {}   # { prof_id → np.ndarray }  → exported to HDF5

    # ── Nodes and countries ──────────────────────────────────────────────
    assign_nodes_and_countries_from_tyndp_nodes_csv(
        model, nodes_csv_path=data_folder + "TYNDP24_Nodes.csv"
    )

    # ── Installed capacities (generators + storage) ──────────────────────
    assign_installed_capacity_from_tyndp_csv(
        model,
        installed_capacity_csv_path=data_folder + "TYNDP24_InstalledCapacities.csv",
        policy=policy, year=year, climate_year=climate_year,
    )

    # ── Demand (electrolyser / heat pump loads from capacities CSV) ───────
    assign_demand_from_tyndp_csv(
        model,
        installed_capacity_csv_path=data_folder + "TYNDP24_InstalledCapacities.csv",
        policy=policy, year=year, climate_year=climate_year,
    )

    # ── TimestampSeries entity (shared by all profiles) ───────────────────
    ts_id = "timestamp.hourly"
    model.add_entity(entity_class="TimestampSeries", entity_id=ts_id)
    model.add_attribute(ts_id, "name",           f"Hourly {climate_year or 'base'}")
    model.add_attribute(ts_id, "start_datetime", f"{climate_year or 2009}-01-01T00:00:00")
    model.add_attribute(ts_id, "resolution",     "PT1H")
    model.add_attribute(ts_id, "length",         8784)   # 8760 + 24 padding
    model.add_attribute(ts_id, "timezone",       "UTC")

    # ── Demand time series ────────────────────────────────────────────────
    assign_demand_from_tyndp_timeseries_csv(
        model, profiles_values,
        demand_csv_path=data_folder + "TYNDP24_DemandProfiles.csv",
        policy=policy, year=year, climate_year=climate_year,
        timestamp_series_id=ts_id,
    )

    # ── Renewable generation profiles ─────────────────────────────────────
    assign_renewable_timeseries_from_csv(
        model, profiles_values,
        renewable_csv_path=data_folder + "TYNDP24_GenProfiles.csv",
        year=year, climate_year=climate_year,
        timestamp_series_id=ts_id,
    )

    # ── Hydro inflows ─────────────────────────────────────────────────────
    assign_inflow_timeseries_from_csv(
        model, profiles_values,
        inflow_csv_path=data_folder + "TYNDP24_HydroInflows.csv",
        year=year, climate_year=climate_year,
        timestamp_series_id=ts_id,
    )
    prune_hydro_reservoirs_without_inflow(model)

    # ── Storage energy capacities ─────────────────────────────────────────
    assign_energy_storage_capacity_from_tyndp_csv(
        model,
        storage_cap_csv_path=data_folder + "TYNDP24_StorageCapacities.csv",
        policy=policy, year=year, drop_zero=True,
    )

    # ── Fallback: storage units with charging power but no nominal capacity
    for storage_cls in ("StorageUnit", "HydraulicStorageUnit"):
        for sid, ent in model.entities.get(storage_cls, {}).items():
            sdv = sid  # dispatch attributes held directly on the asset itself
            def _sgav(attr, default=None):
                return model.get_attribute_value(sdv, attr, default)
            def _sgav_gen(attr, default=None):
                """Read power/efficiency from the paired HydroGenerationUnit,
                which also holds its dispatch attributes directly."""
                for _gid2, _ge2 in (model.entities.get("HydroGenerationUnit") or {}).items():
                    _gd2 = getattr(_ge2, "data", {}) or {}
                    _dr2 = _gd2.get("drawsFromHydraulicStorage")
                    _dr2 = _dr2[0] if isinstance(_dr2, (list, tuple)) else _dr2
                    if _dr2 == sid:
                        v = model.get_attribute_value(_gid2, attr, None)
                        if v is not None: return v
                return default
            e_cap = _sgav("energy_storage_capacity")
            n_cap = _sgav_gen("nominal_power_capacity") or _sgav("nominal_power_capacity")
            chg   = _sgav_gen("maximum_pumping_power")  or _sgav("maximum_pumping_power") or _sgav("maximum_charging_power")
            if chg is not None and n_cap is None:
                model.add_attribute(sdv, "nominal_power_capacity",  chg)
            if chg is not None and e_cap is None:
                model.add_attribute(sdv, "energy_storage_capacity", chg)

    # ── NTC interconnectors ───────────────────────────────────────────────
    try:
        ntc_res = assign_ntc_from_tyndp_ntc_types_base_csv(
            model,
            ntc_csv_path=data_folder + "TYNDP24_NTC_types.csv",
            scenario_year=year,
        )
        print(f"NTC import: {ntc_res}")
    except FileNotFoundError:
        print("NTC CSV not found — skipping.")

    # ── Validation ────────────────────────────────────────────────────────
    errors = model.validate()
    if errors:
        print(f"Validation issues ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Model validated successfully.")

    # ── Output paths ──────────────────────────────────────────────────────
    out_root  = Path(output_folder) / f"SC_{policy}_SY_{year}_WY_{climate_year}"
    yaml_dir  = out_root / "cesdm" / "yaml"
    h5_dir    = out_root / "cesdm" / "profiles"   # profiles/ subfolder for consistency
    # excel_dir = out_root / "cesdm" / "excel"
    flex_dir  = out_root / "flexeco"
    stem      = f"tyndp_{policy}_{year}_{climate_year}".lower()

    # Create output directories
    for d in (yaml_dir, h5_dir):
        d.mkdir(parents=True, exist_ok=True)

    # # Create output directories
    # for d in (yaml_dir, h5_dir, excel_dir, flex_dir / "profiles"):
    #     d.mkdir(parents=True, exist_ok=True)

    # ── YAML exports ──────────────────────────────────────────────────────
    model.export_yaml_hierarchical(yaml_dir / f"{stem}_hierarchical.yaml")
    model.export_yaml(yaml_dir / f"{stem}_flat.yaml")

    # ── Attach profile arrays to Profile entities ──────────────────────
    # Must happen before any HDF5 export so both CESDM and FlexEco
    # exporters can find the numeric payloads.
    # _attach_profile_values(model, profiles_values)

    # ── CESDM HDF5: hierarchical format ──────────────────────────────────
    # Layout: /timestamps/<id>/  and  /profiles/<id>/values  (float64)
    # Metadata (profile_type, profile_unit, start_datetime, …) stored as
    # HDF5 group attributes alongside each dataset.
    model.export_hdf5(h5_dir / "profiles.h5", values_map=profiles_values)

    # ── CESDM Parquet: wide format ────────────────────────────────────────────────
    # Layout:
    #   profiles_profiles.parquet   columns: timestamp_index, <profile_id>…
    #   profiles_metadata.parquet   entity attributes (profile_type, profile_unit, …)
    # model.export_parquet(h5_dir / "profiles.parquet", values_map=profiles_values, wide=True)

    # # ── Excel ─────────────────────────────────────────────────────────────
    # model.export_excel(excel_dir / f"{stem}.xlsx")
    # model.export_excel_flat(excel_dir / f"{stem}_flat.xlsx")

    # # ── FlexEco .jpn + HDF5 profile file (flat-matrix format) ────────────
    # # Layout: /series_names (S64) and /values (n_timesteps × n_profiles)
    # export_to_flexeco(
    #     model,
    #     flex_dir / f"{stem}.jpn",
    #     hdf5_path=flex_dir / "profiles" / "profiles.h5",
    # )

    # ── Frictionless Data Package ─────────────────────────────────────────
    # Self-describing multi-file package with embedded Table Schema per class.
    # Layout:
    #   datapackage.json          — Frictionless descriptor
    #   resources/
    #     GenerationUnit.csv      — one CSV per entity class
    #     StorageUnit.csv
    #     Carrier.csv
    #     …
    fp_dir = out_root / "cesdm" / "frictionless"
    dp_path = model.export_frictionless(
        fp_dir,
        name        = stem.replace("_", "-"),
        title       = f"TYNDP {year} {policy} — CESDM Model",
        description = (f"CESDM energy system model derived from TYNDP 2024 "
                       f"data (policy={policy}, year={year}, "
                       f"climate_year={climate_year})."),
        version     = "1.0.0",
    )
    print(f"  Frictionless: {dp_path}")

    print(f"Outputs written to: {out_root}")
    print(f"  CESDM HDF5  : {h5_dir / 'profiles.h5'}")
    print(f"  Frictionless: {fp_dir / 'datapackage.json'}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    for sc in ["NT"]:
        for sy in [2030,2040]:
            for wy in [2009]:
                build_cesdm_model_from_tyndp_installed_capacities(
                    schema_path= str(HERE.parent) + "/schemas/cesdm",
                    data_folder= str(HERE.parent) + "/external_data/TYNDP2024/",
                    output_folder=str(HERE.parent) + "/output/TYNDP2024/",
                    policy=sc,
                    year=sy,
                    climate_year=wy,
                    drop_zero=True,
                )

    for sc in ["DE","GA"]:
        for sy in [2030,2040,2050]:
            for wy in [2009]:
                build_cesdm_model_from_tyndp_installed_capacities(
                    schema_path=str(HERE.parent) + "/schemas/cesdm",
                    data_folder=str(HERE.parent) + "/external_data/TYNDP2024/",
                    output_folder=str(HERE.parent) + "/output/TYNDP2024/",
                    policy=sc,
                    year=sy,
                    climate_year=wy,
                    drop_zero=True,
                )
