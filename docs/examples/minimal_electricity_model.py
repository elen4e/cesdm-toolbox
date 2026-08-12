#!/usr/bin/env python3
"""
minimal_electricity_model.py

Smallest useful CESDM study model for documentation and first-time modellers:
one electricity carrier domain, one bus, wind + PV + reservoir hydro, one
demand unit, and synthetic hourly profiles (demand, availability, inflow).

Uses Core EAR API for the system container and carrier domain, then Proxy API
for network assets. Run from the cesdm-toolbox repository root:

    python docs/examples/minimal_electricity_model.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


def repository_root() -> Path:
    here = Path(__file__).resolve()
    candidates = list(here.parents) + [Path.cwd(), *Path.cwd().parents]
    for candidate in candidates:
        if (candidate / "schemas" / "cesdm").exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate cesdm-toolbox. Run this script from the repository root "
        "or from docs/examples/."
    )


_REPO_ROOT = repository_root()
sys.path.insert(0, str(_REPO_ROOT))

from cesdm_toolbox import build_model_from_yaml
from cesdm.default_library import CarrierDomains, GeneratorTypes, NaturalResources

HOURS = 8760
TS_ID = "ts.hourly.2030"


def _hour_of_year() -> np.ndarray:
    return np.arange(HOURS, dtype=np.float64)


def synthetic_demand_pu(hours: np.ndarray) -> np.ndarray:
    """Normalized annual demand shape (sums to 1.0)."""
    hod = hours % 24.0
    dow = (hours // 24.0) % 7.0
    daily = 0.75 + 0.25 * np.sin((hod - 8.0) * 2.0 * np.pi / 24.0)
    weekly = 1.0 - 0.08 * ((dow >= 5).astype(np.float64))  # weekend dip
    seasonal = 1.0 + 0.12 * np.sin((hours - 2000.0) * 2.0 * np.pi / HOURS)
    raw = np.clip(daily * weekly * seasonal, 0.05, None)
    return raw / raw.sum()


def synthetic_wind_cf(hours: np.ndarray) -> np.ndarray:
    """Onshore wind capacity factor (rough synthetic)."""
    seasonal = 0.35 + 0.15 * np.sin((hours + 1000.0) * 2.0 * np.pi / HOURS)
    weather = 0.15 * np.sin(hours * 2.0 * np.pi / 72.0)
    noise = 0.05 * np.sin(hours * 2.0 * np.pi / 11.0)
    return np.clip(seasonal + weather + noise, 0.0, 1.0)


def synthetic_pv_cf(hours: np.ndarray) -> np.ndarray:
    """Utility PV capacity factor — daytime envelope + seasonality."""
    hod = hours % 24.0
    # Rough solar elevation proxy (zero at night)
    elev = np.sin((hod - 6.0) * np.pi / 12.0)
    elev = np.clip(elev, 0.0, None)
    seasonal = 0.55 + 0.35 * np.sin((hours - 1720.0) * 2.0 * np.pi / HOURS)
    return np.clip(elev * seasonal, 0.0, 1.0)


def synthetic_inflow_pu(hours: np.ndarray) -> np.ndarray:
    """Normalized natural inflow (spring peak; sums to 1.0)."""
    # Peak around May (hour ~3000)
    seasonal = 0.55 + 0.45 * np.sin((hours - 2200.0) * 2.0 * np.pi / HOURS)
    pulse = 0.15 * np.exp(-0.5 * ((hours % 168.0) - 84.0) ** 2 / 40.0**2)
    raw = np.clip(seasonal + pulse, 0.02, None)
    return raw / raw.sum()


def _add_profile(
    model,
    profile_id: str,
    *,
    profile_type: str,
    profile_unit: str,
    values: np.ndarray,
    values_map: dict[str, np.ndarray],
):
    profile = model.add_entity("Profile", profile_id)
    profile.profile_type = profile_type
    profile.profile_unit = profile_unit
    profile.data_reference = f"profiles.h5:/profiles/{profile_id}"
    profile.hasTimestampSeries = TS_ID
    values_map[profile_id] = np.asarray(values, dtype=np.float64)
    return profile


def main() -> None:
    repo = _REPO_ROOT
    output_dir = repo / "output" / "minimal_electricity_model"
    values_map: dict[str, np.ndarray] = {}

    model = build_model_from_yaml(str(repo / "schemas" / "cesdm"))
    model.import_library(str(repo / "library" / "default_library"))
    model.import_library(str(repo / "library" / "regions_library"))

    # --- Core EAR API: system boundary and electricity domain ---
    model.add_entity(entity_class="EnergySystemModel", entity_id="DEMO_2030")
    model.add_attribute(
        entity_id="DEMO_2030",
        attribute_id="long_name",
        value="Minimal electricity demo",
        unit=None,
        provenance_ref=None,
    )

    # domain.electricity comes from the default library
    electricity = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)
    region_ch = model.get_entity("region.country.CH")

    # --- Shared time axis ---
    ts = model.add_entity("TimestampSeries", TS_ID)
    ts.name = "Hourly, 2030"
    ts.start_datetime = "2030-01-01T00:00:00"
    ts.resolution = "PT1H"
    ts.length = HOURS
    ts.timezone = "UTC"

    hours = _hour_of_year()

    # --- Proxy API: network and assets ---
    bus = model.add_entity("ElectricalBus", "bus.demo")
    bus.name = "Demo bus 380 kV"
    bus.nominal_voltage = (380, "kV")
    bus.belongsToCarrierDomain = electricity
    bus.belongsToGeographicalRegion = region_ch

    # Wind
    gen_wind = model.add_entity("GenerationUnit", "gen.demo.wind")
    gen_wind.name = "Demo wind farm"
    gen_wind.nominal_power_capacity = (500, "MW")
    gen_wind.hasTechnology = GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE
    gen_wind.hasInputResource = NaturalResources.RESOURCE_RENEWABLE_WIND
    gen_wind.atNode = bus
    wind_prof = _add_profile(
        model,
        "profile.gen.demo.wind.capacity_factor",
        profile_type="as_capacity_factor",
        profile_unit="pu",
        values=synthetic_wind_cf(hours),
        values_map=values_map,
    )
    gen_wind.hasAvailabilityProfile = wind_prof

    # Solar PV (utility)
    gen_pv = model.add_entity("GenerationUnit", "gen.demo.pv")
    gen_pv.name = "Demo utility PV"
    gen_pv.nominal_power_capacity = (300, "MW")
    gen_pv.hasTechnology = GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY
    gen_pv.hasInputResource = NaturalResources.RESOURCE_RENEWABLE_SOLAR
    gen_pv.atNode = bus
    pv_prof = _add_profile(
        model,
        "profile.gen.demo.pv.capacity_factor",
        profile_type="as_capacity_factor",
        profile_unit="pu",
        values=synthetic_pv_cf(hours),
        values_map=values_map,
    )
    gen_pv.hasAvailabilityProfile = pv_prof

    # Reservoir hydro + natural inflow
    model.ensure_resource(
        NaturalResources.RESOURCE_WATER,
        name="Water",
        resource_type="water",
    )
    reservoir = model.add_entity("HydraulicStorageUnit", "storage.demo.reservoir")
    reservoir.name = "Demo seasonal reservoir"
    reservoir.energy_storage_capacity = (50_000, "MWh")
    reservoir.annual_natural_inflow_energy = (200_000, "MWh/year")
    reservoir.storesResource = NaturalResources.RESOURCE_WATER
    inflow_prof = _add_profile(
        model,
        "profile.storage.demo.reservoir.inflow",
        profile_type="as_normalized_annual_energy",
        profile_unit="pu",
        values=synthetic_inflow_pu(hours),
        values_map=values_map,
    )
    reservoir.hasNaturalInflowProfile = inflow_prof

    hydro = model.add_entity("HydroGenerationUnit", "gen.demo.hydro")
    hydro.name = "Demo reservoir turbines"
    hydro.hydro_machine_kind = "turbine"
    hydro.nominal_power_capacity = (200, "MW")
    hydro.turbine_efficiency = 0.90
    hydro.hasTechnology = GeneratorTypes.GENERATION_RENEWABLE_HYDRO_RESERVOIR
    hydro.hasInputResource = NaturalResources.RESOURCE_WATER
    hydro.atNode = bus
    hydro.drawsFromHydraulicStorage = reservoir

    # Demand
    demand = model.add_entity("DemandUnit", "dem.demo")
    demand.name = "Demo electricity demand"
    demand.annual_energy_demand = (2_000_000, "MWh/year")  # 2 TWh/year
    demand.atNode = bus
    dem_prof = _add_profile(
        model,
        "profile.dem.demo.demand",
        profile_type="as_normalized_annual_energy",
        profile_unit="pu",
        values=synthetic_demand_pu(hours),
        values_map=values_map,
    )
    demand.hasDemandProfile = dem_prof

    errors = model.validate()
    if errors:
        print(f"{len(errors)} validation issue(s):")
        for error in errors[:20]:
            print(" -", error)
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    model.export_yaml_hierarchical(output_dir / "demo_2030.yaml")
    model.export_frictionless(
        output_dir / "frictionless",
        name="minimal-electricity-demo",
        title="Minimal electricity demo model",
    )
    model.export_hdf5(output_dir / "profiles.h5", values_map=values_map)

    print(
        f"Validated model and exported to {output_dir}\n"
        f"  profiles: demand, wind CF, PV CF, hydro inflow "
        f"({HOURS} h → profiles.h5)"
    )


if __name__ == "__main__":
    main()
