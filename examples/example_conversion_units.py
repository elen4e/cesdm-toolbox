#!/usr/bin/env python3
"""
example_conversion_units.py

Plausible Swiss district energy hub demonstrating the compact ConversionUnit
leaves (CHP, heat pump, electrolyser, boiler, fuel cell).

Domains: electricity, gas, heat, hydrogen
Region:  region.country.CH (library/regions_library)

Run from the repository root:

    python examples/example_conversion_units.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cesdm_toolbox import build_model_from_yaml, CesdmModel
from cesdm.default_library import CarrierDomains, Carriers, GeneratorTypes


def build_conversion_units_demo(schema_dir: Path | None = None) -> CesdmModel:
    """Build a validated multi-carrier conversion demo centred on CH."""
    schema = schema_dir or (REPO_ROOT / "schemas" / "cesdm")
    model = build_model_from_yaml(str(schema))
    model.import_library(str(REPO_ROOT / "library" / "default_library"))
    model.import_library(str(REPO_ROOT / "library" / "regions_library"))

    # ------------------------------------------------------------------
    # System + geography
    # ------------------------------------------------------------------
    system = model.add_entity("EnergySystemModel", "DISTRICT_HUB_CH_2030")
    system.long_name = "Swiss district energy hub — conversion units demo, 2030"
    system.co2_price = 120.0

    region = model.get_entity("region.country.CH")
    elec_domain = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)
    gas_domain = model.get_entity(CarrierDomains.DOMAIN_GAS)
    heat_domain = model.get_entity(CarrierDomains.DOMAIN_HEAT)
    h2_domain = model.get_entity(CarrierDomains.DOMAIN_HYDROGEN)

    # ------------------------------------------------------------------
    # Buses (one typed balance point per carrier domain)
    # ------------------------------------------------------------------
    bus_elec = model.add_entity("ElectricalBus", "bus.hub.elec")
    bus_elec.name = "District electricity bus"
    bus_elec.nominal_voltage = (20.0, "kV")
    bus_elec.belongsToCarrierDomain = elec_domain
    bus_elec.belongsToGeographicalRegion = region

    bus_gas = model.add_entity("GasBus", "bus.hub.gas")
    bus_gas.name = "District gas bus"
    bus_gas.belongsToCarrierDomain = gas_domain
    bus_gas.belongsToGeographicalRegion = region

    bus_heat = model.add_entity("HeatBus", "bus.hub.heat")
    bus_heat.name = "District heat bus"
    bus_heat.belongsToCarrierDomain = heat_domain
    bus_heat.belongsToGeographicalRegion = region

    bus_h2 = model.add_entity("HydrogenBus", "bus.hub.h2")
    bus_h2.name = "District hydrogen bus"
    bus_h2.belongsToCarrierDomain = h2_domain
    bus_h2.belongsToGeographicalRegion = region

    # ------------------------------------------------------------------
    # Boundary: renewable electricity + gas import
    # ------------------------------------------------------------------
    wind = model.add_entity("GenerationUnit", "gen.hub.wind")
    wind.name = "Local wind park"
    wind.nominal_power_capacity = (80.0, "MW")
    wind.hasTechnology = GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE
    wind.hasOutputCarrier = Carriers.CARRIER_ELECTRICITY
    wind.atNode = bus_elec

    gas_supply = model.add_entity("ExternalSupply", "supply.hub.gas")
    gas_supply.name = "Gas grid import"
    gas_supply.supply_capacity = (200.0, "MW")
    gas_supply.is_slack = True
    gas_supply.hasOutputCarrier = Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
    gas_supply.atNode = bus_gas

    # ------------------------------------------------------------------
    # Compact ConversionUnit leaves
    # ------------------------------------------------------------------
    # Electricity → heat
    heat_pump = model.add_entity("HeatPumpUnit", "conv.hub.heat_pump")
    heat_pump.name = "District heat pump"
    heat_pump.coefficient_of_performance = 3.5
    heat_pump.nominal_thermal_power_capacity = (25.0, "MW")
    heat_pump.nominal_electrical_power_capacity = (25.0 / 3.5, "MW")
    heat_pump.hasInputCarrier = Carriers.CARRIER_ELECTRICITY
    heat_pump.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
    heat_pump.atElectricityNode = bus_elec
    heat_pump.atHeatNode = bus_heat

    # Electricity → hydrogen
    electrolyser = model.add_entity("ElectrolyserUnit", "conv.hub.electrolyser")
    electrolyser.name = "PEM electrolyser"
    electrolyser.energy_conversion_efficiency = 0.68
    electrolyser.nominal_electrical_power_capacity = (40.0, "MW")
    electrolyser.hasInputCarrier = Carriers.CARRIER_ELECTRICITY
    electrolyser.hasHydrogenOutputCarrier = Carriers.CARRIER_HYDROGEN
    electrolyser.atElectricityNode = bus_elec
    electrolyser.atHydrogenNode = bus_h2

    # Fuel → heat
    boiler = model.add_entity("BoilerUnit", "conv.hub.boiler")
    boiler.name = "Peak gas boiler"
    boiler.thermal_efficiency = 0.92
    boiler.nominal_thermal_power_capacity = (30.0, "MW")
    boiler.hasInputCarrier = Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
    boiler.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
    boiler.atFuelNode = bus_gas
    boiler.atHeatNode = bus_heat

    # Hydrogen → electricity (+ optional heat)
    fuel_cell = model.add_entity("FuelCellUnit", "conv.hub.fuel_cell")
    fuel_cell.name = "Stationary fuel cell"
    fuel_cell.electrical_efficiency = 0.55
    fuel_cell.thermal_efficiency = 0.25
    fuel_cell.nominal_electrical_power_capacity = (20.0, "MW")
    fuel_cell.nominal_thermal_power_capacity = (10.0, "MW")
    fuel_cell.power_to_heat_ratio = 2.0
    fuel_cell.hasInputCarrier = Carriers.CARRIER_HYDROGEN
    fuel_cell.hasElectricityOutputCarrier = Carriers.CARRIER_ELECTRICITY
    fuel_cell.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
    fuel_cell.atHydrogenNode = bus_h2
    fuel_cell.atElectricityNode = bus_elec
    fuel_cell.atHeatNode = bus_heat

    # Fuel → electricity + heat (classic CHP)
    chp = model.add_entity("CHPUnit", "conv.hub.chp")
    chp.name = "Gas CHP"
    chp.nominal_electrical_power_capacity = (15.0, "MW")
    chp.nominal_thermal_power_capacity = (20.0, "MW")
    chp.electrical_efficiency = 0.38
    chp.thermal_efficiency = 0.42
    chp.total_efficiency = 0.80
    chp.power_to_heat_ratio = 15.0 / 20.0
    chp.hasInputCarrier = Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
    chp.hasElectricityOutputCarrier = Carriers.CARRIER_ELECTRICITY
    chp.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
    chp.atFuelNode = bus_gas
    chp.atElectricityNode = bus_elec
    chp.atHeatNode = bus_heat

    # ------------------------------------------------------------------
    # Demands
    # ------------------------------------------------------------------
    dem_elec = model.add_entity("DemandUnit", "dem.hub.elec")
    dem_elec.name = "District electricity demand"
    dem_elec.annual_energy_demand = (180_000.0, "MWh/year")
    dem_elec.atNode = bus_elec

    dem_heat = model.add_entity("DemandUnit", "dem.hub.heat")
    dem_heat.name = "District heat demand"
    dem_heat.annual_energy_demand = (220_000.0, "MWh/year")
    dem_heat.atNode = bus_heat

    dem_h2 = model.add_entity("DemandUnit", "dem.hub.h2")
    dem_h2.name = "Hydrogen offtake (mobility / industry)"
    dem_h2.annual_energy_demand = (50_000.0, "MWh/year")
    dem_h2.atNode = bus_h2

    return model


def main() -> None:
    out_dir = REPO_ROOT / "output" / "conversion_units_demo"
    out_dir.mkdir(parents=True, exist_ok=True)

    model = build_conversion_units_demo()
    print(model.summary())
    print()

    errors = model.validate()
    if errors:
        print(f"Validation: {len(errors)} issue(s)")
        for err in errors[:20]:
            print(f"  - {err}")
        raise SystemExit(1)
    print("Validation: OK")

    model.export_yaml_hierarchical(out_dir / "conversion_units_hierarchical.yaml")
    model.export_frictionless(
        out_dir / "frictionless",
        name="cesdm-conversion-units-demo",
        title="CESDM Conversion Units Demo",
    )
    print(f"Wrote outputs under {out_dir}")


if __name__ == "__main__":
    main()
