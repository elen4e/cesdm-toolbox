"""
example_import_tyndp_proxy_api.py
==================================

A second TYNDP importer, built with core EAR calls (`add_entity`/
`add_attribute`/`add_relation`) for entity construction, plus the
object-oriented proxy layer (`cesdm.proxy`) for convenient attribute/
relation reading and writing afterward (`gen.dispatch.x = y`,
`gen.connect(bus)`, ...) -- no CESDM builder-function calls
(`add_<EntityClass>`/`create_<xxxxxx>`) anywhere, per direct request.

Scope
-----
This is **not** a byte-for-byte behavioral port of the full,
1800+-line original. To stay faithful to the real TYNDP business
rules (technology classification, hydro-reservoir/PHS compositing,
carrier mapping, techno-economic defaults), it *reuses that file's
own classification functions and constants directly* — TECH_HIERARCHY,
TYNDP_TECH_DATA, _generation_asset_class_for_type,
_storage_asset_class_for_type, _is_pumped_hydro_storage_type,
_is_reservoir_hydro_storage_type, _add_carrier_or_resource_if_missing,
_add_generator_type_if_missing, _add_storage_type_if_missing — rather than
re-deriving or guessing at them. What's reimplemented here is the
core asset-construction pipeline: buses/regions, generation units
(including hydro reservoir and pumped-hydro composites), storage
units, and demand -- each entity created directly with `add_entity`/
`add_relation`, then read and updated through the proxy layer.

Defensive edge-case handling for real-world CSV variants that the
original accumulated over time is not all replicated. If you need
that, use example_import_tyndp.py -- this file exists to demonstrate
and exercise the proxy layer's read/write convenience against
realistic complexity, not to replace the original.

See docs/architecture/proxy_api.md and CHANGELOG.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPO_ROOT, _REPO_ROOT / "tools", _REPO_ROOT / "examples"):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

import os

import numpy as np
import pandas as pd

from cesdm_toolbox import build_model_from_yaml, CesdmModel
from cesdm.generated_proxies import (
    GenerationUnitProxy, HydroGenerationUnitProxy, DemandUnitProxy,
    StorageUnitProxy, HydraulicStorageUnitProxy, GenericInterconnectorProxy,
)

# Reused, unmodified, from the original importer -- this file already
# demonstrated the proxy-API approach for TYNDP import before the rest of
# the pre-proxy-API examples were retired, so it wasn't re-converted;
# pure classification logic and TYNDP-specific data, not entity-
# construction style, so there is no proxy-API angle to rewriting these;
# importing them keeps this file's business rules identical to (not
# drifted from) the original's.
from example_import_tyndp import (  # type: ignore[import]  # noqa: E402 -- resolved via sys.path.insert above, not statically visible to Pyright
    TECH_HIERARCHY,
    TYNDP_TECH_DATA,
    CO2_PRICE,
    ENERGY_CARRIER_CO2,
    ENERGY_CARRIER_PRICE,
    ELECTRICITY_CARRIER_ID,
    DOMAIN_ID,
    import_tyndp_libraries,
    country_region_id,
    ensure_country_region,
    _slug,
    _carrier_for_type as _carrier_for_type_legacy,
    _is_storage,
    _hydro_generator_id,
    carry_forward_year_per_group,
    _generation_asset_class_for_type,
    _storage_asset_class_for_type,
    _is_pumped_hydro_storage_type,
    _is_reservoir_hydro_storage_type,
    _add_carrier_or_resource_if_missing,
    _add_generator_type_if_missing,
    _add_storage_type_if_missing,
    _register_profile_entity,
    _drop_entity_everywhere,
)


def _carrier_for_type(type_name: str) -> str:
    """Wraps the legacy _carrier_for_type() with one real bug fix: the
    legacy classifier's "hydro"-keyword check (`if any(k in t for k in
    ["hydro", "run", "ror", "pondage", "reservoir"]): return "water"`)
    incorrectly matches "hydrogen" too, since "hydrogen" contains
    "hydro" as a substring, and there is no dedicated hydrogen check
    anywhere in the function to catch it first -- even though
    CARRIER_ID_MAP (tools/cesdm_carriers.py) already correctly maps
    "hydrogen" -> "carrier.hydrogen". Confirmed concretely: found
    `hydrogen_ccgt` (a hydrogen-fuelled gas turbine) classified as a
    *water resource* input, which would have produced
    `hasInputResource: resource.water` on the generator -- wrong for a
    combustion turbine, not a hydro turbine. This is a real,
    independent bug from the "carrier.natural_gas" hardcoded-default
    one (see _assign_generation_row) and would presumably also affect
    the legacy pipeline's own GeneratorType-level hasInputCarrier, not
    just this proxy-API rewrite. Left as a local wrapper rather than
    editing example_import_tyndp.py itself, to keep that file exactly
    as extracted/backed-up. See CHANGELOG.md.
    """
    if "hydrogen" in type_name.lower():
        return "hydrogen"
    return _carrier_for_type_legacy(type_name)


# ---------------------------------------------------------------------------
# Generation rows -- proxy API
# ---------------------------------------------------------------------------

def _assign_generation_row(model: CesdmModel, tech_id: str, type_name: str,
                           node_code: str, bus_id: str, in_carrier_id: str, out_carrier_id: str,
                           cap_mw: float | None) -> None:
    tt_id = _add_generator_type_if_missing(model, type_name, in_carrier_id, out_carrier_id)
    if tt_id is None:
        return

    generation_class = _generation_asset_class_for_type(type_name, tt_id)

    if model.has_entity(tech_id):
        # asset() rather than get_entity_as() here: generation_class (just above)
        # is one of two possible classes depending on the technology, so
        # there's no single correct get_entity_as() argument -- the low-level,
        # dynamically-resolved EntityProxy is the right tool for this case.
        gen = model.get_entity(entity_id=tech_id)
    else:
        model.add_entity(entity_class=generation_class, entity_id=tech_id)
        model.add_relation(tech_id, "hasTechnology", tt_id)
        model.add_relation(tech_id, "atNode", bus_id)
        gen = model.get_entity(entity_id=tech_id)
        gen.name = f"{type_name} @ {node_code}"
        if generation_class == "HydroGenerationUnit":
            # Plain hydro (not PHS -- pumped-hydro storage rows are
            # handled entirely separately in _assign_storage_row), so
            # hydro_machine_kind is always "turbine" here.
            gen.dispatch.hydro_machine_kind = "turbine"

        # hasInputCarrier/hasInputResource/hasOutputCarrier: set
        # directly here rather than via a family-specific builder that
        # would apply its own hardcoded default and then need
        # correcting -- e.g. a generic "thermal-family" default of
        # "carrier.natural_gas" would be simply wrong for coal/oil/
        # lignite generators, and even for gas ones is the
        # non-canonical spelling (the correct id, already computed
        # above via _add_carrier_or_resource_if_missing/_carrier_for_type, is
        # "carrier.fuel.fossil.gas.natural_gas"). strict=True
        # deliberately: the real pipeline
        # (assign_installed_capacity_from_tyndp_csv_proxy_api) always
        # creates in_carrier_id/out_carrier_id via _add_carrier_or_resource_if_missing
        # before calling this function, so the target should always
        # exist -- if that invariant is ever broken by a future change,
        # this should fail loudly rather than silently doing nothing.
        # See CHANGELOG.md.
        if in_carrier_id:
            is_resource = str(in_carrier_id).startswith("resource.")
            rel = "hasInputResource" if is_resource else "hasInputCarrier"
            model.add_relation_if_allowed(gen, rel, in_carrier_id, strict=True)
        if out_carrier_id:
            model.add_relation_if_allowed(gen, "hasOutputCarrier", out_carrier_id, strict=True)

    if cap_mw is not None:
        current = gen.dispatch.nominal_power_capacity or 0.0
        gen.dispatch.nominal_power_capacity = cap_mw + current

    td = TYNDP_TECH_DATA.get(tt_id, {})
    if "eff" in td:
        eff_attr = ("turbine_efficiency" if generation_class == "HydroGenerationUnit"
                    else "energy_conversion_efficiency")
        setattr(gen.dispatch, eff_attr, td["eff"])
    if "disp" in td:
        gen.dispatch.dispatch_type = "dispatchable" if td["disp"] else "nondispatchable"
    if "voc" in td:
        gen.dispatch.variable_operating_cost = td["voc"]
    if "ramp_up" in td:
        gen.dispatch.maximum_ramp_rate_up = td["ramp_up"]
    if "ramp_dn" in td:
        gen.dispatch.maximum_ramp_rate_down = td["ramp_dn"]
    if "DemandResponse" in tt_id:
        gen.dispatch.variable_operating_cost = 300.0


# ---------------------------------------------------------------------------
# Storage rows -- proxy API, including hydro reservoir / PHS composites
# ---------------------------------------------------------------------------

def _assign_storage_row(model: CesdmModel, tech_id: str, type_name: str,
                        node_code: str, bus_id: str, in_carrier_id: str, out_carrier_id: str,
                        cap_mw: float | None, charg_mw: float | None) -> None:
    tt_id = _add_storage_type_if_missing(model, type_name, in_carrier_id, out_carrier_id)
    if tt_id is None:
        return

    storage_class = _storage_asset_class_for_type(type_name, tt_id)
    is_hydro_res = (storage_class == "HydraulicStorageUnit")
    is_phs_type = _is_pumped_hydro_storage_type(type_name, tt_id)
    is_res_hydro = _is_reservoir_hydro_storage_type(type_name, tt_id)

    if model.has_entity(tech_id):
        # Same reasoning as _assign_generation_row above: reservoir is one
        # of two possible classes (StorageUnit or HydraulicStorageUnit)
        # depending on is_hydro_res, so this stays on plain asset().
        reservoir = model.get_entity(entity_id=tech_id)
    elif is_hydro_res:
        model.add_entity(entity_class="HydraulicStorageUnit", entity_id=tech_id)
        model.ensure_resource("resource.water", name="Water", resource_type="water")
        model.add_relation_if_allowed(tech_id, "storesResource", "resource.water")
        # No hasTechnology→StorageType on water bodies (schema P0).
        reservoir = model.get_entity(entity_id=tech_id)
        reservoir.name = f"{type_name} @ {node_code}"
        # The original importer connected the reservoir itself to the bus
        # too, separately from the paired generator's own bus connection
        # below -- removed: HydraulicStorageUnit is a standalone class now
        # (not a StorageUnit subclass), with no atNode of its own at all,
        # matching the fact that a reservoir genuinely has no direct
        # electrical role (the paired HydroGenerationUnit's own atNode,
        # set further below, is the real connection point).
    else:
        model.add_entity(entity_class="StorageUnit", entity_id=tech_id)
        model.set_technology(tech_id, tt_id, technology_class="StorageType")
        if in_carrier_id:
            model.ensure_carrier(in_carrier_id)
            model.add_relation_if_allowed(tech_id, "storesCarrier", in_carrier_id)
        reservoir = model.get_entity(entity_id=tech_id)
        reservoir.connect(bus_id)
        reservoir.name = f"{type_name} @ {node_code}"

    # Power/energy attrs: hydro reservoirs carry capacity on the paired
    # HydroGenerationUnit.DispatchView (handled below), not here.
    if not is_hydro_res:
        if cap_mw is not None:
            current = reservoir.dispatch.nominal_power_capacity or 0.0
            reservoir.dispatch.nominal_power_capacity = cap_mw + current
        if charg_mw is not None:
            current = reservoir.dispatch.maximum_charging_power or 0.0
            reservoir.dispatch.maximum_charging_power = charg_mw + current
        if (reservoir.dispatch.maximum_discharging_power is None
                and reservoir.dispatch.maximum_charging_power is not None):
            # TYNDP's storage rows only ever give a charging figure, never
            # a separate discharging one -- assume symmetric charge/
            # discharge power (a common simplification for battery/PHS
            # ratings) rather than leaving maximum_discharging_power unset
            # entirely.
            reservoir.dispatch.maximum_discharging_power = reservoir.dispatch.maximum_charging_power
        return

    if is_phs_type:
        gen_id = f"gen.hydro.{tech_id}"
        phs_tech = ("Generation.Renewable.Hydro.PHS.OpenLoop" if "OpenLoop" in str(tt_id)
                    else "Generation.Renewable.Hydro.PHS.ClosedLoop")
        if model.has_entity(gen_id):
            gen = model.get_entity_as(gen_id, HydroGenerationUnitProxy)
        else:
            model.add_entity(entity_class="HydroGenerationUnit", entity_id=gen_id)
            model.ensure_resource("resource.water", name="Water", resource_type="water")
            model.set_technology(gen_id, phs_tech, technology_class="GeneratorType")
            model.add_relation(gen_id, "hasInputResource", "resource.water")
            model.add_relation(gen_id, "atNode", bus_id)
            model.add_relation(gen_id, "drawsFromHydraulicStorage", tech_id)
            gen = model.get_entity(entity_id=gen_id)
            gen.name = gen_id
            gen.dispatch.hydro_machine_kind = "reversible"

        if cap_mw is not None:
            current = gen.dispatch.nominal_power_capacity or 0.0
            gen.dispatch.nominal_power_capacity = cap_mw + current
        if charg_mw is not None:
            current = gen.dispatch.maximum_pumping_power or 0.0
            gen.dispatch.maximum_pumping_power = charg_mw + current
        turbine_eff = model.get_attribute_value(tt_id, "discharging_efficiency")
        pumping_eff = model.get_attribute_value(tt_id, "charging_efficiency")
        if turbine_eff is not None:
            gen.dispatch.turbine_efficiency = turbine_eff
        if pumping_eff is not None:
            gen.dispatch.pumping_efficiency = pumping_eff

    elif is_res_hydro:
        gen_id = f"gen.hydro.{tech_id}"
        if model.has_entity(gen_id):
            gen = model.get_entity_as(gen_id, HydroGenerationUnitProxy)
        else:
            model.add_entity(entity_class="HydroGenerationUnit", entity_id=gen_id)
            model.ensure_resource("resource.water", name="Water", resource_type="water")
            model.set_technology(gen_id, "Generation.Renewable.Hydro.Reservoir", technology_class="GeneratorType")
            model.add_relation(gen_id, "hasInputResource", "resource.water")
            model.add_relation(gen_id, "atNode", bus_id)
            model.add_relation(gen_id, "drawsFromHydraulicStorage", tech_id)
            gen = model.get_entity(entity_id=gen_id)
            gen.dispatch.hydro_machine_kind = "turbine"
            gen.name = gen_id
        if cap_mw is not None:
            current = gen.dispatch.nominal_power_capacity or 0.0
            gen.dispatch.nominal_power_capacity = cap_mw + current


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def assign_installed_capacity_from_tyndp_csv_proxy_api(
    model: CesdmModel,
    installed_capacity_csv_path: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> None:
    """Same CSV shape and pipeline as
    example_import_tyndp.assign_installed_capacity_from_tyndp_csv(), but
    every entity/view created below goes through the EntityProxy/
    ViewProxy API instead of raw add_entity/add_relation/add_attribute.
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

    df["Type"] = df["Type"].astype(str).str.strip()
    df["Node"] = df["Node"].astype(str).str.strip()
    df["Country"] = df["Country"].astype(str).str.strip()

    model_id = f"TYNDP_{policy}_{year}"
    if not model.has_entity(model_id):
        model.add_entity(entity_class="EnergySystemModel", entity_id=model_id)
    if year and year in CO2_PRICE:
        model.set_attribute_if_allowed(model_id, "co2_price", CO2_PRICE[year])

    group_cols = [c for c in ["Type", "Node", "Country", "Policy", "Year", "Variable", "Climate Year"]
                  if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)["Value"].sum()

    for _, row in df_agg.iterrows():
        type_name = str(row["Type"])
        node_code = str(row["Node"]).strip()[:4]
        load_type = _slug(str(row["Node"]).strip()[4:])
        country = str(row.get("Country", ""))
        var = str(row["Variable"])

        cap_mw = float(row["Value"]) if "Installed" in var else None
        charg_mw = float(row["Value"]) if "Charging" in var else None

        if load_type in ("ev_passenger", "sres"):
            continue
        if type_name in ("Electrolyser (load)", "CH4 Heat Pump (load)", "H2 Heat Pump (load)"):
            continue
        if _slug(type_name) not in TECH_HIERARCHY:
            continue

        bus_id = f"node.{_slug(node_code)}"
        if not model.has_entity(bus_id):
            continue

        # GeographicalRegion (country level) — regions_library id
        cid = ensure_country_region(model, country, name=node_code)
        model.add_relation_if_allowed(bus_id, "belongsToGeographicalRegion", cid)

        in_carrier_id = _add_carrier_or_resource_if_missing(model, _carrier_for_type(type_name))
        out_carrier_id = ELECTRICITY_CARRIER_ID
        tech_id = f"tech.{_slug(type_name)}.{_slug(node_code)}"

        if _is_storage(type_name):
            _assign_storage_row(model, tech_id, type_name, node_code, bus_id,
                                in_carrier_id, out_carrier_id, cap_mw, charg_mw)
        else:
            _assign_generation_row(model, tech_id, type_name, node_code, bus_id,
                                   in_carrier_id, out_carrier_id, cap_mw)

    for carrier, co2 in ENERGY_CARRIER_CO2.items():
        if model.has_entity(carrier):
            model.set_attribute_if_allowed(carrier, "co2_emission_intensity", co2)
    if year and year in ENERGY_CARRIER_PRICE:
        for carrier, price in ENERGY_CARRIER_PRICE[year].items():
            if model.has_entity(carrier):
                model.set_attribute_if_allowed(carrier, "energy_carrier_cost", price)

    # add_generator() -> add_thermal_generator() has its own hardcoded,
    # non-canonical fuel_carrier_id default ("carrier.natural_gas",
    # rather than the canonical "carrier.fuel.fossil.gas.natural_gas"
    # used everywhere else -- see CARRIER_ID_MAP in tools/
    # cesdm_carriers.py). _assign_generation_row above always
    # explicitly overwrites the resulting hasInputCarrier relation
    # with the correct id, but the wrong entity can still be created as
    # a side effect before that override runs, leaving it orphaned
    # (zero incoming relations) if nothing else references it. Cleaned
    # up here rather than in add_thermal_generator itself, since that
    # builder's default is also relied on by tools/import_pandapower.py,
    # tools/import_matpower.py, and an existing test -- fixing it at
    # the source is a broader, separate change than "correct the TYNDP
    # import". See CHANGELOG.md.
    stray_id = "carrier.natural_gas"
    if model.has_entity(stray_id):
        referenced = any(
            stray_id in (model.get_relation_targets(gid, rel) or [])
            for gid in model.entities.get("GenerationUnit", {})
            for rel in ("hasInputCarrier", "hasOutputCarrier")
        )
        if not referenced:
            _drop_entity_everywhere(model, stray_id)


def assign_nodes_and_countries_from_tyndp_nodes_csv(
    model: CesdmModel,
    nodes_csv_path: str,
) -> dict:
    """Reads TYNDP24_Nodes.csv -> GeographicalRegion + ElectricalBus entities,
    using add_bus() (proxy-returning) instead of raw add_entity/add_relation.
    """
    df = pd.read_csv(nodes_csv_path)

    if not model.has_entity(DOMAIN_ID):
        model.add_entity(entity_class="CarrierDomain", entity_id=DOMAIN_ID)
        model.set_attribute_if_allowed(DOMAIN_ID, "name", "Electricity Domain")
    elec_id = _add_carrier_or_resource_if_missing(model, "electricity")
    model.add_relation_if_allowed(DOMAIN_ID, "hasCarrier", elec_id)

    created_nodes = created_countries = updated_nodes = updated_countries = 0

    for _, row in df.iterrows():
        node_code = str(row["Node"]).strip()
        cc        = str(row["Country"]).strip()
        cc_name   = str(row.get("Country_spelledOut", cc)).strip()

        country_id = country_region_id(cc)
        bus_id     = f"node.{_slug(node_code)}"
        existed = model.has_entity(country_id)
        ensure_country_region(model, cc, name=cc_name)
        if existed:
            updated_countries += 1
        else:
            created_countries += 1

        if not model.has_entity(bus_id):
            model.add_entity(entity_class="ElectricalBus", entity_id=bus_id)
            model.add_relation_if_allowed(bus_id, "belongsToGeographicalRegion", country_id)
            model.add_relation_if_allowed(bus_id, "belongsToCarrierDomain", DOMAIN_ID)
            model.set_attribute_if_allowed(bus_id, "name", node_code)
            created_nodes += 1
        else:
            model.set_attribute_if_allowed(bus_id, "name", node_code)
            model.add_relation_if_allowed(bus_id, "belongsToCarrierDomain", DOMAIN_ID)
            model.add_relation_if_allowed(bus_id, "belongsToGeographicalRegion", country_id)
            updated_nodes += 1

    return {
        "countries_created": created_countries, "countries_updated": updated_countries,
        "nodes_created": created_nodes,         "nodes_updated": updated_nodes,
        "rows": int(df.shape[0]),
    }


def assign_demand_from_tyndp_csv(
    model: CesdmModel,
    installed_capacity_csv_path: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> None:
    """Reads TYNDP24_InstalledCapacities.csv (Electrolyser / heat-pump rows)
    using create_demand_unit() (proxy-returning) + .dispatch instead of raw
    add_entity/add_attribute.
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

    df["Type"] = df["Type"].astype(str).str.strip()
    df["Node"] = df["Node"].astype(str).str.strip()
    df["Country"] = df["Country"].astype(str).str.strip()

    group_cols = [c for c in ["Type", "Node", "Country", "Policy", "Year", "Variable", "Climate Year"]
                  if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)["Value"].sum()

    for _, row in df_agg.iterrows():
        type_name = str(row["Type"])
        node_code = str(row["Node"]).strip()[:4]
        load_type = _slug(str(row["Node"]).strip()[4:])
        cap_mw = float(row["Value"]) if "Installed" in str(row.get("Variable", "")) else None

        bus_id = f"node.{_slug(node_code)}"
        if not model.has_entity(bus_id):
            continue

        if "Electrolyser" in type_name:
            subtype = "electricity.electrolyse"
        elif "CH4 Heat Pump" in type_name:
            subtype = "electricity.heatpump"
        else:
            continue

        demand_id = (f"demand.{_slug(subtype)}.{load_type}.{_slug(node_code)}"
                     if load_type else f"demand.{_slug(subtype)}.{_slug(node_code)}")

        if model.has_entity(demand_id):
            load = model.get_entity_as(demand_id, DemandUnitProxy)
        else:
            model.add_entity(entity_class="DemandUnit", entity_id=demand_id)
            model.add_relation(demand_id, "atNode", bus_id)
            load = model.get_entity(entity_id=demand_id)
            load.name = f"{type_name} @ {node_code}"

        if cap_mw is not None:
            current = load.dispatch.maximum_energy_demand or 0.0
            load.dispatch.maximum_energy_demand = cap_mw + current


def assign_energy_storage_capacity_from_tyndp_csv(
    model: CesdmModel,
    storage_cap_csv_path: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> dict:
    """Reads TYNDP24_StorageCapacities.csv -> sets energy_storage_capacity
    via .dispatch, resolved through the proxy API's schema-driven
    view_family lookup rather than reconstructing the view id by hand
    (the legacy _ensure_storage_dispatch_view() hardcodes
    f"storage_dispatch_view.{asset_id}" for *every* storage class, which
    does not actually match the real id convention for
    HydraulicStorageUnit specifically -- reservoir_storage_dispatch_view.*,
    not storage_dispatch_view.* -- a real, silent mismatch this rewrite
    avoids entirely by never reconstructing view ids by hand).
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
        e_mwh = float(row["Value"])

        slug = _slug(type_name)
        if "pump_storage_open_loop" in slug: slug = "pump_storage_open_loop"
        elif "pump_storage_closed_loop" in slug: slug = "pump_storage_closed_loop"
        elif "battery_storage" in slug: slug = "battery_storage"
        elif "reservoir" in slug: slug = "reservoir"

        storage_id = f"tech.{slug}.{_slug(node_code)}"
        if model.has_entity(storage_id):
            # Genuinely either StorageUnit or HydraulicStorageUnit depending
            # on the CSV row's Type column -- get_entity_as() with a tuple of
            # both still gets .dispatch to type-check (against whichever
            # of the two actually declares it), unlike plain asset().
            storage = model.get_entity_as(storage_id, (StorageUnitProxy, HydraulicStorageUnitProxy))
            storage.dispatch.energy_storage_capacity = e_mwh
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
    """Reads TYNDP24_DemandProfiles.csv using create_demand_unit()
    (proxy-returning) + .dispatch instead of raw add_entity/add_attribute.
    The numeric time-series handling (pandas/numpy) is unchanged from the
    original -- there's no proxy-API angle to array processing itself.
    """
    df = pd.read_csv(demand_csv_path)

    if policy is not None and "Policy" in df.columns:
        df = df[df["Policy"].fillna(policy) == policy]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node", "Type"])
    if climate_year is not None and "Climate" in df.columns:
        df = df[df["Climate"].fillna(climate_year) == climate_year]

    ts_cols = [c for c in df.columns if c.isdigit()]
    df[ts_cols] = df[ts_cols].apply(pd.to_numeric, errors="coerce")

    group_cols = [c for c in ["ID", "Type", "Node", "Policy", "Year", "Climate"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)[ts_cols].sum()

    created = updated = 0
    for _, row in df_agg.iterrows():
        node_code = str(row["Node"]).strip()[:4]
        load_type = _slug(str(row["Node"]).strip()[4:])
        bus_id = f"node.{_slug(node_code)}"
        typ = str(row.get("Type", "")).strip()

        if not model.has_entity(bus_id):
            continue

        if "Demand" in typ:
            subtype = "electricity"
        elif "Electrolyser" in typ:
            subtype = "electricity.electrolyse"
        elif "CH4 Heat Pump" in typ:
            subtype = "electricity.heatpump"
        else:
            continue

        ts = np.array([float(x) if pd.notna(x) else 0.0 for x in row[ts_cols]])
        ts = np.concatenate([ts, ts[-24:]])  # pad to 8784
        ts = np.abs(ts)
        annual = float(ts.sum())
        if drop_zero and annual == 0:
            continue

        demand_id = (f"demand.{_slug(subtype)}.{load_type}.{_slug(node_code)}"
                     if load_type else f"demand.{_slug(subtype)}.{_slug(node_code)}")
        prof_id = (f"profile.demand.{_slug(subtype)}.{load_type}.{_slug(node_code)}"
                   if load_type else f"profile.demand.{_slug(subtype)}.{_slug(node_code)}")
        demand_type = f"{_slug(subtype)}.{load_type}" if load_type else _slug(subtype)

        if model.has_entity(demand_id):
            load = model.get_entity_as(demand_id, DemandUnitProxy)
            updated += 1
        else:
            model.add_entity(entity_class="DemandUnit", entity_id=demand_id)
            model.add_relation(demand_id, "atNode", bus_id)
            load = model.get_entity(entity_id=demand_id)
            load.name = f"Demand {_slug(subtype)} {load_type} {node_code}"
            created += 1

        dv = load.dispatch
        dv.annual_energy_demand = annual
        # Profile entity must exist before the relation to it can be
        # added -- add_relation_if_allowed() silently returns False
        # (no error, since strict=True isn't passed) when the target
        # doesn't exist yet, so this order matters.
        _register_profile_entity(
            model, profiles_values, prof_id,
            values=-ts / annual, profile_type="as_normalized_annual_energy",
            profile_unit="pu", ts_id=timestamp_series_id,
        )
        model.add_relation_if_allowed(dv.id, "hasDemandProfile", prof_id)
        dv.demand_type = demand_type
        if "electrolyse" in subtype:
            dv.is_demand_flexible = True
            dv.flexibility_window_time_end = 8760
            dv.flexibility_time_resolution = 8760
            dv.value_of_lost_load = 50.0

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
    """Reads TYNDP24_GenProfiles.csv, updating existing GenerationUnit/
    HydroGenerationUnit assets via .dispatch -- resolved through the
    proxy API's schema-driven view_family lookup, so there's no need for
    the legacy _dispatch_view_class()/_ensure_generation_dispatch_view()
    asset-class-to-view-class mapping at all: .dispatch always resolves
    to the correct concrete view for whatever the asset's real class is.
    """
    df = pd.read_csv(renewable_csv_path)

    if renewable_type is not None and "Type" in df.columns:
        df = df[df["Type"].fillna(renewable_type) == renewable_type]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node", "Type"])
    if climate_year is not None and "Climate Year" in df.columns:
        df = df[df["Climate Year"].fillna(climate_year) == climate_year]

    ts_cols = [c for c in df.columns if c.isdigit()]
    df[ts_cols] = df[ts_cols].apply(pd.to_numeric, errors="coerce")
    if drop_zero:
        df = df[df[ts_cols].sum(axis=1, skipna=True) != 0.0]

    group_cols = [c for c in ["ID", "Node", "Country", "Type", "Year", "Climate Year", "Unit"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)[ts_cols].sum()

    created = updated = 0
    for _, row in df_agg.iterrows():
        node_code = str(row["Node"]).strip()
        typ = str(row.get("Type", "")).strip()

        if "LFSolarPVRooftop" in typ: slug = "solar_photovoltaic_rooftop"
        elif "LFSolarPVUtility" in typ: slug = "solar_photovoltaic_utility"
        elif "SolarPV" in typ: slug = "solar_photovoltaic"
        elif "CSP_noStorage" in typ: slug = "solar_thermal"
        elif "Wind_Offshore" in typ: slug = "wind_offshore"
        elif "Wind_Onshore" in typ: slug = "wind_onshore"
        else: continue

        tech_id = f"tech.{slug}.{_slug(node_code)}"
        prof_id = f"profile.{slug}.{_slug(node_code)}"

        if not model.has_entity(tech_id):
            continue
        # Genuinely either class -- see the isinstance-style tuple form of
        # get_entity_as() a few functions below for the same pattern applied.
        gen = model.get_entity_as(tech_id, (GenerationUnitProxy, HydroGenerationUnitProxy))
        if gen.entity_class not in ("GenerationUnit", "HydroGenerationUnit"):
            continue

        ts = np.array([float(x) if pd.notna(x) else 0.0 for x in row[ts_cols]])
        annual = ts.sum()

        cap = gen.dispatch.nominal_power_capacity
        if cap is None:
            continue

        gen.dispatch.annual_resource_potential = float(annual * cap)
        # Same ordering fix as assign_demand_from_tyndp_timeseries_csv above.
        _register_profile_entity(
            model, profiles_values, prof_id,
            values=ts / annual, profile_type="as_normalized_annual_energy",
            profile_unit="pu", ts_id=timestamp_series_id,
        )
        model.add_relation_if_allowed(gen.dispatch.id, "hasAvailabilityProfile", prof_id)
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
    """Reads TYNDP24_HydroInflows.csv, updating existing run-of-river
    GenerationUnits or reservoir/pondage StorageUnits via .dispatch --
    same reasoning as assign_renewable_timeseries_from_csv above: no
    asset-class-to-view-class mapping needed, .dispatch resolves it.
    """
    df = pd.read_csv(inflow_csv_path)

    if renewable_type is not None and "Type" in df.columns:
        df = df[df["Type"].fillna(renewable_type) == renewable_type]
    if year is not None and "Year" in df.columns:
        df = carry_forward_year_per_group(df, year_col="Year", requested_year=int(year), group_cols=["Node", "Type"])
    if climate_year is not None and "Climate Year" in df.columns:
        df = df[df["Climate Year"].fillna(climate_year) == climate_year]

    ts_cols = [c for c in df.columns if c.isdigit()]
    df[ts_cols] = df[ts_cols].apply(pd.to_numeric, errors="coerce")
    if drop_zero:
        df = df[df[ts_cols].sum(axis=1, skipna=True) != 0.0]

    group_cols = [c for c in ["ID", "Node", "Country", "Type", "Year", "Climate Year", "Variable"] if c in df.columns]
    df_agg = df.groupby(group_cols, dropna=False, as_index=False)[ts_cols].sum()

    created = updated = 0
    for _, row in df_agg.iterrows():
        node_code = str(row["Node"]).strip()
        typ = str(row.get("Type", "")).strip()

        if "Reservoir" in typ: slug = "reservoir"
        elif "PS Open" in typ: slug = "pump_storage_open_loop"
        elif "PS Close" in typ or "PS Cloase" in typ: slug = "pump_storage_closed_loop"
        elif "Pondage" in typ: slug = "pondage"
        elif "Run of River" in typ: slug = "run_of_river"
        else: continue

        tech_id = f"tech.{slug}.{_slug(node_code)}"
        prof_id = f"profile.{slug}.{_slug(node_code)}"
        ts = np.array([float(x) if pd.notna(x) else 0.0 for x in row[ts_cols]])
        annual = float(ts.sum())
        if annual == 0:
            continue

        if not model.has_entity(tech_id):
            continue
        # Any of four classes depending on the CSV row -- get_entity_as() with
        # all four still gets .dispatch to type-check against whichever
        # one actually applies.
        asset = model.get_entity_as(tech_id, (GenerationUnitProxy, HydroGenerationUnitProxy,
                                         StorageUnitProxy, HydraulicStorageUnitProxy))

        if asset.entity_class in ("GenerationUnit", "HydroGenerationUnit"):
            asset.dispatch.annual_resource_potential = annual
            # Same ordering fix as the two functions above: register the
            # Profile entity before adding the relation to it.
            _register_profile_entity(
                model, profiles_values, prof_id,
                values=ts / annual, profile_type="as_normalized_annual_energy",
                profile_unit="pu", ts_id=timestamp_series_id,
            )
            if asset.entity_class == "HydroGenerationUnit":
                res_ids = model.get_relation_targets(str(asset), "drawsFromHydraulicStorage") or []
                if res_ids:
                    model.add_relation_if_allowed(
                        res_ids[0], "hasNaturalInflowProfile", prof_id
                    )
                else:
                    model.add_relation_if_allowed(
                        asset.dispatch.id, "hasAvailabilityProfile", prof_id
                    )
            else:
                model.add_relation_if_allowed(
                    asset.dispatch.id, "hasAvailabilityProfile", prof_id
                )
            created += 1

        elif asset.entity_class in ("StorageUnit", "HydraulicStorageUnit"):
            asset.dispatch.annual_natural_inflow_energy = annual
            _register_profile_entity(
                model, profiles_values, prof_id,
                values=ts / annual, profile_type="as_normalized_annual_energy",
                profile_unit="pu", ts_id=timestamp_series_id,
            )
            model.add_relation_if_allowed(asset.dispatch.id, "hasNaturalInflowProfile", prof_id)
            hydro_gen_id = _hydro_generator_id(tech_id)
            if model.has_entity(hydro_gen_id):
                model.get_entity_as(hydro_gen_id, HydroGenerationUnitProxy).dispatch.annual_resource_potential = annual
            updated += 1

    return {"created": created, "updated": updated, "rows": int(df_agg.shape[0])}


def assign_ntc_from_tyndp_ntc_types_base_csv(
    model: CesdmModel,
    ntc_csv_path: str,
    *,
    scenario_year: int,
    base_type: str = "Base",
    real_types: tuple = ("Real 1", "Real 2"),
    real_years_by_scenario_year: dict | None = None,
    base_year: int | None = None,
    base_year_fallback: int = 2025,
    drop_zero: bool = True,
    add_real_only_where_base_link_exists: bool = True,
) -> dict:
    """Reads TYNDP24_NTC_types.csv, using ensure_entity() for creation +
    get_entity_as(ntc_id, GenericInterconnectorProxy) for a statically-typed reference
    + .connect() + .power_flow -- no dedicated builder exists yet for
    Interconnector specifically (create_transmission_line() targets
    TransmissionLine), same reasoning as the reference model /
    tutorial_ch_neighbours.py's interconnector sections.
    """
    if real_years_by_scenario_year is None:
        real_years_by_scenario_year = {2030: [], 2040: [2030, 2035], 2050: [2030, 2035, 2040]}

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
        frm = str(row["FROM"]).strip()
        to = str(row["TO"]).strip()
        frm_id = f"node.{_slug(frm)}"
        to_id = f"node.{_slug(to)}"

        if not model.has_entity(frm_id) or not model.has_entity(to_id):
            continue

        ntc_id = f"ntc.{_slug(frm)}_{_slug(to)}"
        was_new = not model.has_entity(ntc_id)
        model.ensure_entity(class_name="GenericInterconnector", entity_id=ntc_id, name=f"NTC {frm}->{to}")
        ico = model.get_entity_as(ntc_id, GenericInterconnectorProxy)
        created += int(was_new)
        updated += int(not was_new)

        ico.connect(frm_id, to_id)
        pf = ico.power_flow
        pf.maximum_power_flow_from_to = float(row["P12"]) if pd.notna(row["P12"]) else 0.0
        pf.maximum_power_flow_to_from = float(row["P21"]) if pd.notna(row["P21"]) else 0.0

    return {
        "created": created, "updated": updated, "rows": int(df_final.shape[0]),
        "scenario_year": int(scenario_year), "base_source_year": int(base_source_year),
        "real_years_added": list(inc_years),
    }


def prune_hydro_reservoirs_without_inflow(model: CesdmModel) -> dict:
    """Drop reservoir/pondage hydro assets that have no positive natural
    inflow, using .dispatch (proxy API) to read the current value instead
    of reconstructing f"storage_dispatch_view.{id}" by hand -- the exact
    id-mismatch class of bug documented on
    assign_energy_storage_capacity_from_tyndp_csv above; this function is
    a second, independent place the legacy code had the same bug.
    PHS/pumped-storage reservoirs are kept even without natural inflow.
    """
    removed: list[str] = []
    for reservoir_id in list((model.entities.get("HydraulicStorageUnit") or {}).keys()):
        # PHS / hydro kind: prefer paired generator technology + machine flags
        # (HydraulicStorageUnit no longer has hasTechnology→StorageType).
        gen_id = _hydro_generator_id(reservoir_id)
        gen_tech = " ".join(model.get_relation_targets(gen_id, "hasTechnology")) if model.has_entity(gen_id) else ""
        key = f"{reservoir_id} {gen_id} {gen_tech}".lower()
        is_phs = any(x in key for x in ("pumped", "pump_storage", "phs", "pumpedhydro"))
        if not is_phs and model.has_entity(gen_id):
            try:
                gen = model.get_entity(gen_id)
                if getattr(getattr(gen, "dispatch", None), "hydro_machine_kind", None) == "reversible":
                    is_phs = True
            except Exception:
                pass
        if is_phs:
            continue
        if not any(x in key for x in ("reservoir", "pondage")):
            continue

        reservoir = model.get_entity_as(reservoir_id, HydraulicStorageUnitProxy)
        inflow = reservoir.dispatch.annual_natural_inflow_energy
        try:
            inflow_val = float(inflow) if inflow is not None else 0.0
        except (TypeError, ValueError):
            inflow_val = 0.0
        if inflow_val > 0.0:
            continue

        for eid in (reservoir_id, gen_id):
            if model.has_entity(eid):
                for view_id in list(model.views_for_asset(eid).values()):
                    _drop_entity_everywhere(model, view_id)
                _drop_entity_everywhere(model, eid)
        removed.append(reservoir_id)
    return {"removed": len(removed), "removed_ids": removed[:20]}


def build_cesdm_model_from_tyndp_installed_capacities_proxy_api(
    schema_path: str,
    data_folder: str,
    output_folder: str,
    *,
    policy: str | None = None,
    year: int | None = None,
    climate_year: int | None = None,
    drop_zero: bool = True,
) -> CesdmModel:
    """Full TYNDP2024 -> CESDM V4 build pipeline, entirely on the proxy
    API. Same stages, same order, as
    example_import_tyndp.build_cesdm_model_from_tyndp_installed_capacities()
    -- see each stage function's docstring above for what changed and why.
    """
    model = build_model_from_yaml(str(schema_path))
    import_tyndp_libraries(model)
    profiles_values: dict = {}

    assign_nodes_and_countries_from_tyndp_nodes_csv(
        model, nodes_csv_path=data_folder + "TYNDP24_Nodes.csv")

    assign_installed_capacity_from_tyndp_csv_proxy_api(
        model, installed_capacity_csv_path=data_folder + "TYNDP24_InstalledCapacities.csv",
        policy=policy, year=year, climate_year=climate_year, drop_zero=drop_zero)

    assign_demand_from_tyndp_csv(
        model, installed_capacity_csv_path=data_folder + "TYNDP24_InstalledCapacities.csv",
        policy=policy, year=year, climate_year=climate_year, drop_zero=drop_zero)

    ts_id = "timestamp.hourly"
    model.add_entity(entity_class="TimestampSeries", entity_id=ts_id)
    model.set_attribute_if_allowed(ts_id, "name", f"Hourly {climate_year or 'base'}")
    model.set_attribute_if_allowed(ts_id, "start_datetime", f"{climate_year or 2009}-01-01T00:00:00")
    model.set_attribute_if_allowed(ts_id, "resolution", "PT1H")
    model.set_attribute_if_allowed(ts_id, "length", 8784)
    model.set_attribute_if_allowed(ts_id, "timezone", "UTC")

    try:
        assign_demand_from_tyndp_timeseries_csv(
            model, profiles_values, demand_csv_path=data_folder + "TYNDP24_DemandProfiles.csv",
            policy=policy, year=year, climate_year=climate_year, timestamp_series_id=ts_id)
    except FileNotFoundError:
        print("Demand profiles CSV not found -- skipping.")

    try:
        assign_renewable_timeseries_from_csv(
            model, profiles_values, renewable_csv_path=data_folder + "TYNDP24_GenProfiles.csv",
            year=year, climate_year=climate_year, timestamp_series_id=ts_id)
    except FileNotFoundError:
        print("Generation profiles CSV not found -- skipping.")

    try:
        assign_inflow_timeseries_from_csv(
            model, profiles_values, inflow_csv_path=data_folder + "TYNDP24_HydroInflows.csv",
            year=year, climate_year=climate_year, timestamp_series_id=ts_id)
        prune_hydro_reservoirs_without_inflow(model)
    except FileNotFoundError:
        print("Hydro inflows CSV not found -- skipping.")

    try:
        assign_energy_storage_capacity_from_tyndp_csv(
            model, storage_cap_csv_path=data_folder + "TYNDP24_StorageCapacities.csv",
            policy=policy, year=year, drop_zero=True)
    except FileNotFoundError:
        print("Storage capacities CSV not found -- skipping.")

    try:
        ntc_res = assign_ntc_from_tyndp_ntc_types_base_csv(
            model, ntc_csv_path=data_folder + "TYNDP24_NTC_types.csv", scenario_year=year)
        print(f"NTC import: {ntc_res}")
    except FileNotFoundError:
        print("NTC CSV not found -- skipping.")

    errors = model.validate()
    if errors:
        print(f"Validation issues ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Model validated successfully.")

    out_root = Path(output_folder) / f"SC_{policy}_SY_{year}_WY_{climate_year}"
    yaml_dir = out_root / "cesdm" / "yaml"
    h5_dir = out_root / "cesdm" / "profiles"
    yaml_dir.mkdir(parents=True, exist_ok=True)
    h5_dir.mkdir(parents=True, exist_ok=True)
    stem = f"tyndp_{policy}_{year}_{climate_year}".lower()

    model.export_yaml_hierarchical(yaml_dir / f"{stem}_hierarchical.yaml")
    model.export_yaml(yaml_dir / f"{stem}_flat.yaml")
    if hasattr(model, "export_hdf5"):
        try:
            model.export_hdf5(h5_dir / "profiles.h5", values_map=profiles_values)
        except Exception as exc:
            print(f"HDF5 export skipped: {exc}")

    fp_dir = out_root / "cesdm" / "frictionless"
    dp_path = model.export_frictionless(
        fp_dir, name=stem.replace("_", "-"),
        title=f"TYNDP {year} {policy} — CESDM Model",
        description=(f"CESDM energy system model derived from TYNDP 2024 data "
                     f"(policy={policy}, year={year}, climate_year={climate_year})."),
        version="1.0.0",
    )
    print(f"Outputs written to: {out_root}")
    print(f"  Frictionless: {dp_path}")
    return model


def _build_minimal_buses_for_demo(model: CesdmModel, node_codes: list) -> None:
    """Minimal bus setup for the single-CSV demo mode only (`main()`
    below) -- just enough to connect assets to when no real
    TYNDP24_Nodes.csv is available. The full pipeline
    (`build_cesdm_model_from_tyndp_installed_capacities_proxy_api`)
    uses `assign_nodes_and_countries_from_tyndp_nodes_csv` instead,
    which links buses to ``region.country.XX`` from regions_library
    (creating a fallback GeographicalRegion only if missing).
    """
    if not model.has_entity(DOMAIN_ID):
        model.add_entity(entity_class="CarrierDomain", entity_id=DOMAIN_ID)
        model.set_attribute_if_allowed(DOMAIN_ID, "name", "Electricity Domain")
    for code in node_codes:
        bus_id = f"node.{_slug(code)}"
        model.add_entity(entity_class="ElectricalBus", entity_id=bus_id)
        model.add_attribute(bus_id, "nominal_voltage", 380)
        model.add_relation_if_allowed(bus_id, "belongsToCarrierDomain", DOMAIN_ID)


def main(installed_capacity_csv_path: str, *, policy: str, year: int,
         climate_year: int | None = None,
         storage_capacity_csv_path: str | None = None) -> CesdmModel:
    """Minimal single-CSV demo mode. Note: TYNDP splits storage data
    across two files -- installed_capacity_csv_path only carries power
    (MW) and charging power; energy (MWh) capacity
    (energy_storage_capacity) lives in a separate TYNDP24_
    StorageCapacities.csv-shaped file and is NOT populated unless
    storage_capacity_csv_path is also given here. Without it, every
    StorageUnit/HydraulicStorageUnit in the output will correctly have
    nominal_power_capacity but no energy_storage_capacity -- this is
    not a bug, it reflects what's actually in the single CSV this mode
    reads. Use the full pipeline
    (`build_cesdm_model_from_tyndp_installed_capacities_proxy_api`,
    `--data-folder` on the CLI) for the complete picture without
    needing to pass every file path individually.
    """
    model = build_model_from_yaml(str(_REPO_ROOT / "schemas/cesdm"))
    df = pd.read_csv(installed_capacity_csv_path)
    node_codes = sorted({str(n).strip()[:4] for n in df["Node"].dropna().unique()})
    _build_minimal_buses_for_demo(model, node_codes)
    assign_installed_capacity_from_tyndp_csv_proxy_api(
        model, installed_capacity_csv_path, policy=policy, year=year, climate_year=climate_year,
    )
    if storage_capacity_csv_path:
        result = assign_energy_storage_capacity_from_tyndp_csv(
            model, storage_capacity_csv_path, policy=policy, year=year, climate_year=climate_year,
        )
        print(f"Storage capacity: {result}")
    return model


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    # Minimal single-CSV mode (unchanged from before) -- run against just
    # the synthetic examples/sample_data fixture.
    parser.add_argument("csv_path", nargs="?", help="Path to a TYNDP24_InstalledCapacities.csv-shaped file")
    parser.add_argument("--policy", default=None)
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--climate-year", type=int, default=None)
    parser.add_argument("--output", default="tyndp_proxy_api_model.yaml")
    parser.add_argument("--storage-capacity-csv", default=None,
                        help="Optional path to a TYNDP24_StorageCapacities.csv-shaped "
                             "file (minimal single-CSV mode only). Without it, "
                             "energy_storage_capacity (MWh) is not populated for any "
                             "storage asset -- installed_capacity_csv_path alone only "
                             "carries power (MW), never energy (MWh) capacity, since "
                             "that's genuinely how TYNDP splits the data across files.")

    # Full pipeline mode -- matches
    # example_import_tyndp.build_cesdm_model_from_tyndp_installed_capacities()'s
    # signature.
    parser.add_argument("--data-folder", default=None,
                        help="If given, runs the FULL pipeline (nodes, demand, "
                             "storage, NTC, timeseries) against a TYNDP data folder "
                             "instead of the minimal single-CSV mode.")
    parser.add_argument("--output-folder", default="output/TYNDP2024/")
    args = parser.parse_args()

    if not args.data_folder and not args.csv_path:
        parser.error(
            "Provide either a csv_path (minimal single-CSV mode) or "
            "--data-folder (full pipeline mode). Examples:\n"
            "  Minimal:      python examples/example_import_tyndp_proxy_api.py "
            "examples/sample_data/tyndp_sample_installed_capacities.csv --year 2030\n"
            "  Full pipeline: python examples/example_import_tyndp_proxy_api.py "
            "--data-folder path/to/tyndp/csvs/ --year 2030 --policy \"National Trends\""
        )
    if args.data_folder and args.csv_path:
        parser.error("Provide either csv_path or --data-folder, not both.")
    if args.year is None:
        parser.error("--year is required in both modes.")

    if args.data_folder:
        build_cesdm_model_from_tyndp_installed_capacities_proxy_api(
            schema_path=str(_REPO_ROOT / "schemas/cesdm"),
            data_folder=args.data_folder,
            output_folder=args.output_folder,
            policy=args.policy, year=args.year, climate_year=args.climate_year,
        )
    else:
        m = main(args.csv_path, policy=args.policy, year=args.year, climate_year=args.climate_year,
                storage_capacity_csv_path=args.storage_capacity_csv)
        m.validate_or_raise()
        m.export_yaml_hierarchical(args.output)
        print(f"Wrote {args.output}")
