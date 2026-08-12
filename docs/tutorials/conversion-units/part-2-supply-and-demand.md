# Part 2: Supply and Demand

!!! info "Checkpoint"
    After Part 2 you should have local wind generation, a gas import slack, and three demand units (electricity, heat, hydrogen).

Continue from the model built in [Part 1](part-1-system-and-carriers.md).

## 5. Add renewable electricity and gas import

```python
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
```

Wind supplies the electricity domain (and later the electrolyser / heat pump). Gas import is the exogenous fuel boundary for the boiler and CHP.

---

## 6. Add end-use demands

```python
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
```

Capacities in this demo illustrate coupling, not a full adequacy study. Annual demand figures are district-scale placeholders.

---

## Navigation

← [Part 1](part-1-system-and-carriers.md) · Next: [Part 3 — Conversion Units](part-3-conversion-units.md)
