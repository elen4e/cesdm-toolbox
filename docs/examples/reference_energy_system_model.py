#!/usr/bin/env python3
"""
reference_energy_system_model.py

Build the CESDM reference / second-step tutorial model using the three
core EAR operations for model construction:

    model.add_entity(...)
    model.add_attribute(...)
    model.add_relation(...)

Also synthesises hourly Profile arrays (country demand, wind/PV capacity
factors, hydro inflow) and writes them to ``profiles.h5`` via
``export_hdf5``.

After export, prints an illustrative annual electricity energy balance:
dispatchable (P×8760) + non-dispatchable (resource potential) + hydro
natural inflows vs electricity demand.

Schema loading, library import, validation, and export are separate workflow
operations and are intentionally retained.

Each major section also contains commented Proxy API equivalents. These
comments are educational only and are not executed.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HOURS = 8760
TS_ID = "ts.hourly.2030"


def _hour_of_year() -> np.ndarray:
    return np.arange(HOURS, dtype=np.float64)


def synthetic_demand_pu(hours: np.ndarray, *, phase_hours: float = 0.0) -> np.ndarray:
    """Normalized annual demand shape (sums to 1.0)."""
    hod = (hours + phase_hours) % 24.0
    dow = (hours // 24.0) % 7.0
    daily = 0.75 + 0.25 * np.sin((hod - 8.0) * 2.0 * np.pi / 24.0)
    weekly = 1.0 - 0.08 * ((dow >= 5).astype(np.float64))
    seasonal = 1.0 + 0.12 * np.sin((hours - 2000.0) * 2.0 * np.pi / HOURS)
    raw = np.clip(daily * weekly * seasonal, 0.05, None)
    return raw / raw.sum()


def synthetic_wind_cf(hours: np.ndarray, *, phase_hours: float = 0.0) -> np.ndarray:
    """Onshore wind capacity factor (rough synthetic)."""
    t = hours + phase_hours
    seasonal = 0.35 + 0.15 * np.sin((t + 1000.0) * 2.0 * np.pi / HOURS)
    weather = 0.15 * np.sin(t * 2.0 * np.pi / 72.0)
    noise = 0.05 * np.sin(t * 2.0 * np.pi / 11.0)
    return np.clip(seasonal + weather + noise, 0.0, 1.0)


def synthetic_pv_cf(hours: np.ndarray, *, phase_hours: float = 0.0) -> np.ndarray:
    """Utility PV capacity factor — daytime envelope + seasonality."""
    hod = (hours + phase_hours) % 24.0
    elev = np.clip(np.sin((hod - 6.0) * np.pi / 12.0), 0.0, None)
    seasonal = 0.55 + 0.35 * np.sin((hours - 1720.0) * 2.0 * np.pi / HOURS)
    return np.clip(elev * seasonal, 0.0, 1.0)


def synthetic_inflow_pu(hours: np.ndarray) -> np.ndarray:
    """Normalized natural inflow (spring peak; sums to 1.0)."""
    seasonal = 0.55 + 0.45 * np.sin((hours - 2200.0) * 2.0 * np.pi / HOURS)
    pulse = 0.15 * np.exp(-0.5 * ((hours % 168.0) - 84.0) ** 2 / 40.0**2)
    raw = np.clip(seasonal + pulse, 0.02, None)
    return raw / raw.sum()


def _country_from_bus(bus_id: str) -> str:
    return bus_id.rsplit(".", 1)[-1].upper()


def print_annual_energy_balance(
    *,
    demands: list,
    generators: list,
    reservoirs: list,
    values_map: dict[str, np.ndarray],
    turbine_efficiency: float = 0.90,
) -> None:
    """Compare annual supply potential vs electricity demand (TWh).

    Not a dispatch solve — only annual energy aggregates:

    * **Dispatchable** (thermal/coal/nuclear): ``P_MW × 8760`` (full-year technical max).
    * **Non-dispatchable** (wind/solar): ``annual_resource_potential``; also
      report profile energy ``P × Σ CF`` when a CF series exists.
    * **Hydro**: ``annual_natural_inflow_energy`` only (not ``P × 8760``).
      Electrical upper bound after turbine efficiency is shown separately.
    * **Demand**: ``annual_energy_demand`` (electricity DemandUnits only).
    """
    countries = sorted(
        {
            *(_country_from_bus(b) for *_, b, _ in demands),
            *(_country_from_bus(b) for *_, b, _, _ in generators),
            *(_country_from_bus(b) for *_, b, _, _ in reservoirs),
        }
    )

    demand_mwh = {cc: 0.0 for cc in countries}
    disp_mwh = {cc: 0.0 for cc in countries}
    nondisp_pot_mwh = {cc: 0.0 for cc in countries}
    nondisp_cf_mwh = {cc: 0.0 for cc in countries}
    hydro_inflow_mwh = {cc: 0.0 for cc in countries}

    for _did, _name, annual_gwh, bus_id, _phase in demands:
        demand_mwh[_country_from_bus(bus_id)] += float(annual_gwh) * 1_000.0

    for generator_id, _name, _tech, capacity_mw, bus_id, family, annual_mwh in generators:
        cc = _country_from_bus(bus_id)
        if family in ("thermal", "coal", "nuclear"):
            disp_mwh[cc] += float(capacity_mw) * float(HOURS)
        elif family in ("wind", "solar"):
            if annual_mwh is not None:
                nondisp_pot_mwh[cc] += float(annual_mwh)
            profile_id = f"profile.{generator_id}.capacity_factor"
            cf = values_map.get(profile_id)
            if cf is not None:
                nondisp_cf_mwh[cc] += float(capacity_mw) * float(np.sum(cf))

    for _rid, _rn, _hid, _hn, _p, bus_id, _e, inflow_mwh in reservoirs:
        hydro_inflow_mwh[_country_from_bus(bus_id)] += float(inflow_mwh)

    def _twh(mwh: float) -> float:
        return mwh / 1_000_000.0

    print()
    print("Annual electricity energy balance (illustrative aggregates, not a solve)")
    print(
        "  Dispatchable     = P_MW × 8760 h  (thermal/coal/nuclear technical max)"
    )
    print(
        "  Non-dispatchable = annual_resource_potential  (wind/solar; "
        "CF-based P×ΣCF shown for cross-check)"
    )
    print(
        "  Hydro            = annual_natural_inflow_energy only "
        f"(electrical @ η={turbine_efficiency:.0%} = inflow × η)"
    )
    print("  Demand           = annual_energy_demand (electricity)")
    print(
        f"{'CC':<4} {'Demand':>8} {'Disp':>8} {'NonDisp':>8} "
        f"{'Hydro':>8} {'Supply':>8} {'Balance':>9}  {'NonDisp_CF':>10} {'Hydro_el':>8}"
    )
    print(
        f"{'':4} {'TWh':>8} {'TWh':>8} {'TWh':>8} "
        f"{'TWh':>8} {'TWh':>8} {'TWh':>9}  {'TWh':>10} {'TWh':>8}"
    )

    tot = {k: 0.0 for k in (
        "demand", "disp", "nondisp", "hydro", "supply", "balance", "nondisp_cf", "hydro_el"
    )}
    for cc in countries:
        d = demand_mwh[cc]
        disp = disp_mwh[cc]
        nond = nondisp_pot_mwh[cc]
        hydro = hydro_inflow_mwh[cc]
        supply = disp + nond + hydro
        balance = supply - d
        nond_cf = nondisp_cf_mwh[cc]
        hydro_el = hydro * turbine_efficiency
        tot["demand"] += d
        tot["disp"] += disp
        tot["nondisp"] += nond
        tot["hydro"] += hydro
        tot["supply"] += supply
        tot["balance"] += balance
        tot["nondisp_cf"] += nond_cf
        tot["hydro_el"] += hydro_el
        print(
            f"{cc:<4} {_twh(d):8.1f} {_twh(disp):8.1f} {_twh(nond):8.1f} "
            f"{_twh(hydro):8.1f} {_twh(supply):8.1f} {_twh(balance):+9.1f}  "
            f"{_twh(nond_cf):10.1f} {_twh(hydro_el):8.1f}"
        )

    print(
        f"{'ALL':<4} {_twh(tot['demand']):8.1f} {_twh(tot['disp']):8.1f} "
        f"{_twh(tot['nondisp']):8.1f} {_twh(tot['hydro']):8.1f} "
        f"{_twh(tot['supply']):8.1f} {_twh(tot['balance']):+9.1f}  "
        f"{_twh(tot['nondisp_cf']):10.1f} {_twh(tot['hydro_el']):8.1f}"
    )
    # Supply with hydro as electricity after η (still using declared RE potential)
    supply_el = tot["disp"] + tot["nondisp"] + tot["hydro_el"]
    print(
        f"  → with hydro as electricity (inflow×η): "
        f"supply={_twh(supply_el):.1f} TWh, "
        f"balance={_twh(supply_el - tot['demand']):+.1f} TWh"
    )
    print()


def repository_root() -> Path:
    """Locate the repository from examples/, docs/examples/, or the working directory."""
    here = Path(__file__).resolve()
    candidates = list(here.parents) + [Path.cwd(), *Path.cwd().parents]
    for candidate in candidates:
        if (candidate / "schemas" / "cesdm").exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate the repository. Run this script from the CESDM "
        "repository or place it under examples/ or docs/examples/."
    )


_REPO_ROOT = repository_root()
sys.path.insert(0, str(_REPO_ROOT))

from cesdm_toolbox import build_model_from_yaml
from cesdm.default_library import CarrierDomains, GeneratorTypes, Carriers


def main() -> None:
    repo = _REPO_ROOT
    schema_dir = repo / "schemas" / "cesdm"
    library_dir = repo / "library" / "default_library"
    output_dir = repo / "output" / "reference_energy_system_model"

    regions_dir = repo / "library" / "regions_library"
    model = build_model_from_yaml(str(schema_dir))
    model.import_library(str(library_dir))
    model.import_library(str(regions_dir))
    values_map: dict[str, np.ndarray] = {}
    hours = _hour_of_year()

    # ------------------------------------------------------------------
    # 1. System container and electricity Carrier Domain
# Proxy API equivalent:
# system = model.add_entity("EnergySystemModel", "CH_NEIGHBOURS_2030")
# system.long_name = "CH + neighbours multi-domain energy system, 2030"
# system.co2_price = 80.0
#
# electricity_domain = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)
    # ------------------------------------------------------------------
    model.add_entity(
        entity_class='EnergySystemModel',
        entity_id='CH_NEIGHBOURS_2030',
    )
    model.add_attribute(
        entity_id='CH_NEIGHBOURS_2030',
        attribute_id='long_name',
        value='CH + neighbours multi-domain energy system, 2030',
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id='CH_NEIGHBOURS_2030',
        attribute_id='co2_price',
        value=80.0,
        unit=None,
        provenance_ref=None,
    )

    # domain.electricity comes from the default library
    # Countries / NUTS / MarketZones come from library/regions_library
    # (e.g. region.country.CH, market_zone.CH).

    # ------------------------------------------------------------------
    # 2. Geographic regions (from regions_library)
# Proxy API equivalent:
# region_ch = model.get_entity("region.country.CH")
    # ------------------------------------------------------------------
    countries = [
        "region.country.CH",
        "region.country.DE",
        "region.country.FR",
        "region.country.IT",
        "region.country.AT",
    ]
    for region_id in countries:
        if model.entity_class(region_id) is None:
            raise RuntimeError(
                f"Missing {region_id} — import library/regions_library after default_library"
            )

    # ------------------------------------------------------------------
    # 3. Electricity buses
    # Proxy API equivalent:
    # bus = model.add_entity("ElectricalBus", bus_id)
    # bus.name = name
    # bus.nominal_voltage = voltage_kv
    # bus.spatial.latitude = latitude
    # bus.spatial.longitude = longitude
    # bus.spatial.belongsToGeographicalRegion = region
    # bus.belongsToCarrierDomain = electricity_domain
    # ------------------------------------------------------------------
    buses = [
        ("bus.ch", "region.country.CH", "Switzerland 380kV", 380.0, 47.0, 8.0),
        ("bus.de", "region.country.DE", "Germany 380kV", 380.0, 51.0, 10.0),
        ("bus.fr", "region.country.FR", "France 400kV", 400.0, 46.0, 2.0),
        ("bus.it", "region.country.IT", "Italy 380kV", 380.0, 42.0, 12.0),
        ("bus.at", "region.country.AT", "Austria 380kV", 380.0, 47.5, 14.0),
    ]
    for bus_id, region_id, name, voltage_kv, latitude, longitude in buses:
        model.add_entity(
            entity_class='ElectricalBus',
            entity_id=bus_id,
        )
        model.add_attribute(
            entity_id=bus_id,
            attribute_id='name',
            value=name,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=bus_id,
            attribute_id='nominal_voltage',
            value=voltage_kv,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=bus_id,
            attribute_id='latitude',
            value=latitude,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=bus_id,
            attribute_id='longitude',
            value=longitude,
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=bus_id,
            relation_id='belongsToGeographicalRegion',
            target_entity_id=region_id,
        )
        model.add_relation(
            entity_id=bus_id,
            relation_id='belongsToCarrierDomain',
            target_entity_id='domain.electricity',
        )

    # ------------------------------------------------------------------
    # 4. Shared time axis (needed before Profile relations)
    # Proxy API equivalent:
    # timestamps = model.add_entity("TimestampSeries", "ts.hourly.2030")
    # timestamps.name = "Hourly, 2030"
    # timestamps.start_datetime = "2030-01-01T00:00:00"
    # timestamps.resolution = "PT1H"
    # timestamps.length = 8760
    # timestamps.timezone = "Europe/Zurich"
    #
    # Wind, solar, and water resources are already reusable entities in
    # the imported Default Library. The project model references them
    # directly and does not recreate them.
    # ------------------------------------------------------------------
    model.add_entity(
        entity_class='TimestampSeries',
        entity_id=TS_ID,
    )
    model.add_attribute(
        entity_id=TS_ID,
        attribute_id='name',
        value='Hourly, 2030',
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id=TS_ID,
        attribute_id='start_datetime',
        value='2030-01-01T00:00:00',
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id=TS_ID,
        attribute_id='resolution',
        value='PT1H',
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id=TS_ID,
        attribute_id='length',
        value=HOURS,
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id=TS_ID,
        attribute_id='timezone',
        value='Europe/Zurich',
        unit=None,
        provenance_ref=None,
    )

    # ------------------------------------------------------------------
    # 5. Electricity demand (+ synthetic hourly demand Profiles)
    # Proxy API equivalent:
    # demand = model.add_entity("DemandUnit", demand_id)
    # demand.name = name
    # demand.dispatch.annual_energy_demand = annual_gwh * 1_000
    # demand.topology.atNode = bus
    # demand.hasDemandProfile = profile  # arrays → export_hdf5(values_map)
    # ------------------------------------------------------------------
    # phase_hours: small country offsets so shapes are not identical
    demands = [
        ("dem.ch", "CH electricity demand", 60_000, "bus.ch", 0.0),
        ("dem.de", "DE electricity demand", 500_000, "bus.de", 1.0),
        ("dem.fr", "FR electricity demand", 450_000, "bus.fr", -1.0),
        ("dem.it", "IT electricity demand", 300_000, "bus.it", 0.5),
        ("dem.at", "AT electricity demand", 70_000, "bus.at", 0.25),
    ]
    for demand_id, name, annual_gwh, bus_id, phase_hours in demands:
        model.add_entity(
            entity_class='DemandUnit',
            entity_id=demand_id,
        )
        model.add_attribute(
            entity_id=demand_id,
            attribute_id='name',
            value=name,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=demand_id,
            attribute_id='annual_energy_demand',
            value=annual_gwh * 1000,
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=demand_id,
            relation_id='atNode',
            target_entity_id=bus_id,
        )

        profile_id = f"profile.{demand_id}.demand"
        model.add_entity(
            entity_class='Profile',
            entity_id=profile_id,
        )
        model.add_attribute(
            entity_id=profile_id,
            attribute_id='profile_type',
            value='as_normalized_annual_energy',
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=profile_id,
            attribute_id='profile_unit',
            value='pu',
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=profile_id,
            attribute_id='data_reference',
            value=f'profiles.h5:/profiles/{profile_id}',
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=profile_id,
            relation_id='hasTimestampSeries',
            target_entity_id=TS_ID,
        )
        model.add_relation(
            entity_id=demand_id,
            relation_id='hasDemandProfile',
            target_entity_id=profile_id,
        )
        values_map[profile_id] = synthetic_demand_pu(hours, phase_hours=phase_hours)

    # ------------------------------------------------------------------
    # 6. Generation fleet and explicit availability Profiles
    # Proxy API equivalent:
    # generator = model.add_entity("GenerationUnit", generator_id)
    # generator.name = name
    # generator.dispatch.nominal_power_capacity = capacity_mw
    # generator.hasTechnology = technology_id
    # generator.topology.atNode = bus
    #
    # if family == "thermal":
    #     generator.hasInputCarrier = (
    #         Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
    #     )
    # elif family == "wind":
    #     generator.hasInputResource = "resource.renewable.wind"
    # elif family == "solar":
    #     generator.hasInputResource = "resource.renewable.solar"
    #
    # profile = model.add_entity("Profile", profile_id)
    # profile.profile_type = "as_capacity_factor"
    # profile.profile_unit = "pu"
    # profile.data_reference = f"profiles.h5:/profiles/{profile_id}"
    # profile.hasTimestampSeries = timestamps
    # generator.dispatch.hasAvailabilityProfile = profile
    # numeric arrays collected in values_map → export_hdf5(...)
    # ------------------------------------------------------------------
    # Illustrative 2030 capacities (MW) and renewable annual potentials (MWh).
    # Same country set as examples/reference_energy_system_model.py.
    # Thermal capacities: annual energy surplus plus firm headroom for peak
    # residual load (demand − wind/PV) so a dispatch solve has ~0 ENS.
    generators = [
        ("gen.ch.gas", "CH Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 3_000, "bus.ch", "thermal", None),
        ("gen.ch.nuc", "CH Nuclear", GeneratorTypes.GENERATION_NUCLEAR_LWR, 2_000, "bus.ch", "nuclear", None),
        ("gen.ch.wind", "CH Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 500, "bus.ch", "wind", 900_000),
        ("gen.ch.solar", "CH Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 2_000, "bus.ch", "solar", 2_000_000),
        ("gen.de.gas", "DE Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 40_000, "bus.de", "thermal", None),
        ("gen.de.coal", "DE Hard Coal", GeneratorTypes.GENERATION_THERMAL_COAL_HARDCOAL_EXISTING, 25_000, "bus.de", "coal", None),
        ("gen.de.wind", "DE Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 30_000, "bus.de", "wind", 65_000_000),
        ("gen.de.solar", "DE Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 60_000, "bus.de", "solar", 60_000_000),
        ("gen.fr.nuc", "FR Nuclear", GeneratorTypes.GENERATION_NUCLEAR_LWR, 56_000, "bus.fr", "nuclear", None),
        ("gen.fr.gas", "FR Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 8_000, "bus.fr", "thermal", None),
        ("gen.fr.solar", "FR Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 25_000, "bus.fr", "solar", 30_000_000),
        ("gen.it.gas", "IT Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 40_000, "bus.it", "thermal", None),
        ("gen.it.solar", "IT Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 20_000, "bus.it", "solar", 25_000_000),
        ("gen.it.wind", "IT Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 8_000, "bus.it", "wind", 18_000_000),
        ("gen.at.gas", "AT Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 9_000, "bus.at", "thermal", None),
        ("gen.at.wind", "AT Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 4_000, "bus.at", "wind", 8_000_000),
        ("gen.at.solar", "AT Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 5_000, "bus.at", "solar", 6_000_000),
    ]
    country_phase_h = {"ch": 0.0, "de": 1.5, "fr": -1.0, "it": 0.75, "at": 0.5}

    for (
        generator_id,
        name,
        technology_id,
        capacity_mw,
        bus_id,
        family,
        annual_mwh,
    ) in generators:
        model.add_entity(
            entity_class='GenerationUnit',
            entity_id=generator_id,
        )
        model.add_attribute(
            entity_id=generator_id,
            attribute_id='name',
            value=name,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=generator_id,
            attribute_id='nominal_power_capacity',
            value=capacity_mw,
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=generator_id,
            relation_id='hasTechnology',
            target_entity_id=technology_id,
        )
        model.add_relation(
            entity_id=generator_id,
            relation_id='atNode',
            target_entity_id=bus_id,
        )

        if family == "thermal":
            model.add_relation(
                entity_id=generator_id,
                relation_id='hasInputCarrier',
                target_entity_id=Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS,
            )
        elif family == "coal":
            model.add_relation(
                entity_id=generator_id,
                relation_id='hasInputCarrier',
                target_entity_id=Carriers.CARRIER_FUEL_FOSSIL_COAL_HARD_COAL,
            )
        elif family == "wind":
            model.add_relation(
                entity_id=generator_id,
                relation_id='hasInputResource',
                target_entity_id='resource.renewable.wind',
            )
        elif family == "solar":
            model.add_relation(
                entity_id=generator_id,
                relation_id='hasInputResource',
                target_entity_id='resource.renewable.solar',
            )

        if annual_mwh is not None:
            model.add_attribute(
                entity_id=generator_id,
                attribute_id='annual_resource_potential',
                value=annual_mwh,
                unit=None,
                provenance_ref=None,
            )

            profile_id = f"profile.{generator_id}.capacity_factor"
            model.add_entity(
                entity_class='Profile',
                entity_id=profile_id,
            )
            model.add_attribute(
                entity_id=profile_id,
                attribute_id='profile_type',
                value='as_capacity_factor',
                unit=None,
                provenance_ref=None,
            )
            model.add_attribute(
                entity_id=profile_id,
                attribute_id='profile_unit',
                value='pu',
                unit=None,
                provenance_ref=None,
            )
            model.add_attribute(
                entity_id=profile_id,
                attribute_id='data_reference',
                value=f'profiles.h5:/profiles/{profile_id}',
                unit=None,
                provenance_ref=None,
            )
            model.add_relation(
                entity_id=profile_id,
                relation_id='hasTimestampSeries',
                target_entity_id=TS_ID,
            )
            model.add_relation(
                entity_id=generator_id,
                relation_id='hasAvailabilityProfile',
                target_entity_id=profile_id,
            )
            cc = bus_id.rsplit(".", 1)[-1]
            phase = country_phase_h.get(cc, 0.0)
            if family == "wind":
                values_map[profile_id] = synthetic_wind_cf(hours, phase_hours=phase)
            elif family == "solar":
                values_map[profile_id] = synthetic_pv_cf(hours, phase_hours=phase)
            else:
                values_map[profile_id] = np.ones(HOURS, dtype=np.float64)

    # ------------------------------------------------------------------
    # 7. Reservoir hydro per country (capacity, energy, inflow, efficiency)
    # Proxy API equivalent (one country):
    # reservoir = model.add_entity("HydraulicStorageUnit", reservoir_id)
    # reservoir.energy_storage_capacity = (...)
    # reservoir.annual_natural_inflow_energy = (...)
    # hydro = model.add_entity("HydroGenerationUnit", hydro_id)
    # hydro.nominal_power_capacity = (...); hydro.turbine_efficiency = 0.90
    # hydro.drawsFromHydraulicStorage = reservoir
    # reservoir.hasNaturalInflowProfile = inflow_profile
    # ------------------------------------------------------------------
    # res_id, res_name, hydro_id, hydro_name, P_MW, bus, E_MWh, inflow_MWh/y
    reservoirs = [
        ("storage.ch.hydro.reservoir", "CH Alpine seasonal reservoir",
         "gen.ch.hydro.reservoir", "CH Reservoir hydro turbines",
         8_000, "bus.ch", 8_800_000, 20_000_000),
        ("storage.de.hydro.reservoir", "DE storage hydro reservoir",
         "gen.de.hydro.reservoir", "DE Reservoir hydro turbines",
         2_500, "bus.de", 2_000_000, 5_000_000),
        ("storage.fr.hydro.reservoir", "FR reservoir hydro",
         "gen.fr.hydro.reservoir", "FR Reservoir hydro turbines",
         10_000, "bus.fr", 5_000_000, 15_000_000),
        ("storage.it.hydro.reservoir", "IT Alpine reservoir",
         "gen.it.hydro.reservoir", "IT Reservoir hydro turbines",
         5_000, "bus.it", 4_000_000, 10_000_000),
        ("storage.at.hydro.reservoir", "AT Alpine reservoir",
         "gen.at.hydro.reservoir", "AT Reservoir hydro turbines",
         3_000, "bus.at", 3_000_000, 18_000_000),
    ]
    for (
        reservoir_id,
        res_name,
        hydro_id,
        hydro_name,
        capacity_mw,
        bus_id,
        energy_mwh,
        inflow_mwh,
    ) in reservoirs:
        inflow_profile_id = f"profile.{reservoir_id}.inflow"

        model.add_entity(
            entity_class='HydraulicStorageUnit',
            entity_id=reservoir_id,
        )
        model.add_attribute(
            entity_id=reservoir_id,
            attribute_id='name',
            value=res_name,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=reservoir_id,
            attribute_id='energy_storage_capacity',
            value=energy_mwh,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=reservoir_id,
            attribute_id='annual_natural_inflow_energy',
            value=inflow_mwh,
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=reservoir_id,
            relation_id='storesResource',
            target_entity_id='resource.water',
        )

        model.add_entity(
            entity_class='HydroGenerationUnit',
            entity_id=hydro_id,
        )
        model.add_attribute(
            entity_id=hydro_id,
            attribute_id='name',
            value=hydro_name,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=hydro_id,
            attribute_id='hydro_machine_kind',
            value='turbine',
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=hydro_id,
            attribute_id='nominal_power_capacity',
            value=capacity_mw,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=hydro_id,
            attribute_id='turbine_efficiency',
            value=0.90,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=hydro_id,
            attribute_id='annual_resource_potential',
            value=inflow_mwh,
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=hydro_id,
            relation_id='hasTechnology',
            target_entity_id='Generation.Renewable.Hydro.Reservoir',
        )
        model.add_relation(
            entity_id=hydro_id,
            relation_id='hasInputResource',
            target_entity_id='resource.water',
        )
        model.add_relation(
            entity_id=hydro_id,
            relation_id='atNode',
            target_entity_id=bus_id,
        )
        model.add_relation(
            entity_id=hydro_id,
            relation_id='drawsFromHydraulicStorage',
            target_entity_id=reservoir_id,
        )

        model.add_entity(
            entity_class='Profile',
            entity_id=inflow_profile_id,
        )
        model.add_attribute(
            entity_id=inflow_profile_id,
            attribute_id='profile_type',
            value='as_normalized_annual_energy',
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=inflow_profile_id,
            attribute_id='profile_unit',
            value='pu',
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=inflow_profile_id,
            attribute_id='data_reference',
            value=f'profiles.h5:/profiles/{inflow_profile_id}',
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=inflow_profile_id,
            relation_id='hasTimestampSeries',
            target_entity_id=TS_ID,
        )
        model.add_relation(
            entity_id=reservoir_id,
            relation_id='hasNaturalInflowProfile',
            target_entity_id=inflow_profile_id,
        )
        cc = bus_id.rsplit(".", 1)[-1]
        values_map[inflow_profile_id] = synthetic_inflow_pu(
            hours + country_phase_h.get(cc, 0.0) * 24.0
        )

    # ------------------------------------------------------------------
    # 8. Cross-border interconnectors
# Proxy API equivalent:
# interconnector = model.add_entity("GenericInterconnector", interconnector_id)
# interconnector.name = name
# interconnector.power_flow.maximum_power_flow_from_to = capacity_from_to
# interconnector.power_flow.maximum_power_flow_to_from = capacity_to_from
# interconnector.topology.fromNode = from_bus
# interconnector.topology.toNode = to_bus
    # ------------------------------------------------------------------
    # Same NTC set as examples/reference_energy_system_model.py (MW A→B / B→A).
    interconnectors = [
        ("ntc.ch.de", "CH-DE NTC", "bus.ch", "bus.de", 6_000, 5_500),
        ("ntc.ch.fr", "CH-FR NTC", "bus.ch", "bus.fr", 4_000, 3_500),
        ("ntc.ch.it", "CH-IT NTC", "bus.ch", "bus.it", 5_000, 4_500),
        ("ntc.ch.at", "CH-AT NTC", "bus.ch", "bus.at", 2_000, 2_000),
        ("ntc.de.fr", "DE-FR NTC", "bus.de", "bus.fr", 3_500, 3_500),
        ("ntc.de.at", "DE-AT NTC", "bus.de", "bus.at", 4_000, 4_000),
        ("ntc.fr.it", "FR-IT NTC", "bus.fr", "bus.it", 3_000, 3_000),
        ("ntc.at.it", "AT-IT NTC", "bus.at", "bus.it", 2_500, 2_500),
    ]
    for (
        interconnector_id,
        name,
        from_bus,
        to_bus,
        capacity_from_to,
        capacity_to_from,
    ) in interconnectors:
        model.add_entity(
            entity_class='GenericInterconnector',
            entity_id=interconnector_id,
        )
        model.add_attribute(
            entity_id=interconnector_id,
            attribute_id='name',
            value=name,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=interconnector_id,
            attribute_id='maximum_power_flow_from_to',
            value=capacity_from_to,
            unit=None,
            provenance_ref=None,
        )
        model.add_attribute(
            entity_id=interconnector_id,
            attribute_id='maximum_power_flow_to_from',
            value=capacity_to_from,
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=interconnector_id,
            relation_id='fromNode',
            target_entity_id=from_bus,
        )
        model.add_relation(
            entity_id=interconnector_id,
            relation_id='toNode',
            target_entity_id=to_bus,
        )

    # ------------------------------------------------------------------
    # 9. Gas and heat buses (domains/carriers from default library)
    # Proxy API equivalent:
    # gas_bus = model.add_entity("GasBus", "bus.ch.gas")
    # gas_bus.name = "Swiss gas bus"
    # gas_bus.belongsToGeographicalRegion = region_ch
    # gas_bus.belongsToCarrierDomain = CarrierDomains.DOMAIN_GAS
    #
    # heat_bus = model.add_entity("HeatBus", "bus.ch.heat")
    # heat_bus.name = "Swiss heat bus"
    # heat_bus.belongsToGeographicalRegion = region_ch
    # heat_bus.belongsToCarrierDomain = CarrierDomains.DOMAIN_HEAT
    # ------------------------------------------------------------------
    nodes = [
        (
            "GasBus",
            "bus.ch.gas",
            "Swiss gas bus",
            "domain.gas",
        ),
        (
            "HeatBus",
            "bus.ch.heat",
            "Swiss heat bus",
            "domain.heat",
        ),
    ]
    for entity_class, node_id, name, domain_id in nodes:
        model.add_entity(
            entity_class=entity_class,
            entity_id=node_id,
        )
        model.add_attribute(
            entity_id=node_id,
            attribute_id='name',
            value=name,
            unit=None,
            provenance_ref=None,
        )
        model.add_relation(
            entity_id=node_id,
            relation_id='belongsToGeographicalRegion',
            target_entity_id='region.country.CH',
        )
        model.add_relation(
            entity_id=node_id,
            relation_id='belongsToCarrierDomain',
            target_entity_id=domain_id,
        )

    # ------------------------------------------------------------------
    # 10. Gas supply, CHP conversion, and heat demand
    # Proxy API equivalent:
    # gas_supply = model.add_entity("ExternalSupply", "supply.ch.gas")
    # gas_supply.name = "Swiss gas import"
    # gas_supply.dispatch.supply_capacity = 10_000.0
    # gas_supply.dispatch.is_slack = True
    # gas_supply.hasOutputCarrier = natural_gas
    # gas_supply.topology.atNode = gas_bus
    #
    # chp = model.add_entity("CHPUnit", "chp.ch")
    # chp.name = "Swiss CHP plant"
    # chp.dispatch.nominal_electrical_power_capacity = 350.0
    # chp.dispatch.nominal_thermal_power_capacity = 450.0
    # chp.dispatch.electrical_efficiency = 0.35
    # chp.dispatch.thermal_efficiency = 0.45
    # chp.technical.total_efficiency = 0.80
    # chp.technical.power_to_heat_ratio = 350.0 / 450.0
    # chp.hasInputCarrier = natural_gas
    # chp.hasElectricityOutputCarrier = electricity
    # chp.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
    # chp.topology.atFuelNode = gas_bus
    # chp.topology.atElectricityNode = electricity_bus
    # chp.topology.atHeatNode = heat_bus
    # ------------------------------------------------------------------
    model.add_entity(
        entity_class='ExternalSupply',
        entity_id='supply.ch.gas',
    )
    model.add_attribute(
        entity_id='supply.ch.gas',
        attribute_id='name',
        value='Swiss gas import',
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id='supply.ch.gas',
        attribute_id='supply_capacity',
        value=10000.0,
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id='supply.ch.gas',
        attribute_id='is_slack',
        value=True,
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id='supply.ch.gas',
        relation_id='hasOutputCarrier',
        target_entity_id=Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS,
    )
    model.add_relation(
        entity_id='supply.ch.gas',
        relation_id='atNode',
        target_entity_id='bus.ch.gas',
    )

    model.add_entity(
        entity_class='CHPUnit',
        entity_id='chp.ch',
    )
    chp_attributes = {
        "name": "Swiss CHP plant",
        "nominal_electrical_power_capacity": 350.0,
        "nominal_thermal_power_capacity": 450.0,
        "electrical_efficiency": 0.35,
        "thermal_efficiency": 0.45,
        "total_efficiency": 0.80,
        "power_to_heat_ratio": 350.0 / 450.0,
    }
    for attribute_id, value in chp_attributes.items():
        model.add_attribute(
            entity_id='chp.ch',
            attribute_id=attribute_id,
            value=value,
            unit=None,
            provenance_ref=None,
        )

    chp_relations = {
        "hasInputCarrier": (
            Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
        ),
        "hasElectricityOutputCarrier": Carriers.CARRIER_ELECTRICITY,
        "hasHeatOutputCarrier": Carriers.CARRIER_HEAT,
        "atFuelNode": "bus.ch.gas",
        "atElectricityNode": "bus.ch",
        "atHeatNode": "bus.ch.heat",
    }
    for relation_id, target_id in chp_relations.items():
        model.add_relation(
            entity_id='chp.ch',
            relation_id=relation_id,
            target_entity_id=target_id,
        )

    model.add_entity(
        entity_class='DemandUnit',
        entity_id='dem.ch.heat',
    )
    model.add_attribute(
        entity_id='dem.ch.heat',
        attribute_id='name',
        value='Swiss heat demand',
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id='dem.ch.heat',
        attribute_id='annual_energy_demand',
        value=20000000.0,
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id='dem.ch.heat',
        relation_id='atNode',
        target_entity_id='bus.ch.heat',
    )

    # ------------------------------------------------------------------
    # 11. Validate and export (YAML + Frictionless + HDF5 profile arrays)
    # ------------------------------------------------------------------
    errors = model.validate()
    if errors:
        print(f"{len(errors)} validation issue(s):")
        for error in errors[:20]:
            print(" -", error)
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    model.export_yaml_hierarchical(
        output_dir / "ch_neighbours_2030.yaml",
    )
    model.export_frictionless(
        output_dir / "frictionless",
        name="ch-neighbours-2030",
        title="CH + Neighbours 2030 — CESDM tutorial model",
    )
    model.export_hdf5(output_dir / "profiles.h5", values_map=values_map)

    print("Model validated and exported successfully.")
    n_cf = sum(1 for k in values_map if k.endswith(".capacity_factor"))
    n_inflow = sum(1 for k in values_map if k.endswith(".inflow"))
    print(
        f"  profiles.h5: {len(values_map)} series "
        f"(demand ×{len(demands)}, CF ×{n_cf}, inflow ×{n_inflow}; {HOURS} h)"
    )
    print(
        f"  fleet: {len(generators)} GenerationUnit + "
        f"{len(reservoirs)} reservoir hydro composites (CH/DE/FR/IT/AT)"
    )
    print(
        f"  NTCs: {len(interconnectors)} interconnectors "
        f"(CH–neighbours + DE–FR, DE–AT, FR–IT, AT–IT)"
    )
    print(model.summary())
    print_annual_energy_balance(
        demands=demands,
        generators=generators,
        reservoirs=reservoirs,
        values_map=values_map,
        turbine_efficiency=0.90,
    )


if __name__ == "__main__":
    main()
