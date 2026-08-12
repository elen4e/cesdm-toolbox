# Part 3: Compact Conversion Units

!!! info "Checkpoint"
    After Part 3 you should have five compact conversion leaves linking the four buses.

Each leaf uses **typed node relations** — no `ConversionPort` entities. Prefer `GenericConversionUnit` only when the topology is truly MxN.

## 7. Heat pump — electricity → heat

```python
heat_pump = model.add_entity("HeatPumpUnit", "conv.hub.heat_pump")
heat_pump.name = "District heat pump"
heat_pump.coefficient_of_performance = 3.5
heat_pump.nominal_thermal_power_capacity = (25.0, "MW")
heat_pump.nominal_electrical_power_capacity = (25.0 / 3.5, "MW")
heat_pump.hasInputCarrier = Carriers.CARRIER_ELECTRICITY
heat_pump.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
heat_pump.atElectricityNode = bus_elec
heat_pump.atHeatNode = bus_heat
```

`coefficient_of_performance` may be greater than 1 (unlike efficiency fractions).

---

## 8. Electrolyser — electricity → hydrogen

```python
electrolyser = model.add_entity("ElectrolyserUnit", "conv.hub.electrolyser")
electrolyser.name = "PEM electrolyser"
electrolyser.energy_conversion_efficiency = 0.68
electrolyser.nominal_electrical_power_capacity = (40.0, "MW")
electrolyser.hasInputCarrier = Carriers.CARRIER_ELECTRICITY
electrolyser.hasHydrogenOutputCarrier = Carriers.CARRIER_HYDROGEN
electrolyser.atElectricityNode = bus_elec
electrolyser.atHydrogenNode = bus_h2
```

---

## 9. Boiler — gas → heat

```python
boiler = model.add_entity("BoilerUnit", "conv.hub.boiler")
boiler.name = "Peak gas boiler"
boiler.thermal_efficiency = 0.92
boiler.nominal_thermal_power_capacity = (30.0, "MW")
boiler.hasInputCarrier = Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
boiler.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
boiler.atFuelNode = bus_gas
boiler.atHeatNode = bus_heat
```

---

## 10. Fuel cell — hydrogen → electricity (+ heat)

```python
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
```

Attach the fuel side with `atHydrogenNode` (hydrogen network) or `atFuelNode` (other fuel bus). Heat output is optional.

!!! tip "FuelCellUnit vs GenerationUnit"
    Use `FuelCellUnit` when hydrogen topology is explicit. `GenerationUnit` + a FuelCell `GeneratorType` remains valid when fuel is only a technology template on an electricity-domain plant.

---

## 11. CHP — gas → electricity + heat

```python
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
```

---

## When to use `GenericConversionUnit`

| Situation | Prefer |
|-----------|--------|
| Clear 1→1 or 1→2 carrier pattern | Compact leaf (`HeatPumpUnit`, …) |
| Arbitrary MxN ports / unusual P2X | `GenericConversionUnit` + `ConversionPort` + `referencePort` |

See `examples/example_multienergy.py` for a port-based CHP.

---

## Navigation

← [Part 2](part-2-supply-and-demand.md) · Next: [Part 4 — Validate and Export](part-4-validate-and-export.md)
