# Conversion Units example

Swiss district energy hub demonstrating the compact `ConversionUnit` leaves.

```bash
python examples/example_conversion_units.py
```

| Asset | Class | Role |
|-------|-------|------|
| `conv.hub.heat_pump` | `HeatPumpUnit` | electricity → heat |
| `conv.hub.electrolyser` | `ElectrolyserUnit` | electricity → hydrogen |
| `conv.hub.boiler` | `BoilerUnit` | gas → heat |
| `conv.hub.fuel_cell` | `FuelCellUnit` | hydrogen → electricity (+ heat) |
| `conv.hub.chp` | `CHPUnit` | gas → electricity + heat |

Step-by-step walkthrough: [Conversion Units tutorial](../docs/tutorials/conversion-units/overview.md).
