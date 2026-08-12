# `example_cesdm_to_pandapower_and_matpower.py` — Step by Step

## Why this example matters

CESDM isn't a dead end for data — this example proves the round trip
to two established power-flow tools actually works, not just that the
export code runs without crashing. The exported pandapower network is
verified structurally *and* an actual AC load flow is run against it,
with convergence checked explicitly.

---

## Step 1: A minimal two-bus power-flow case

```python
model.import_library("library/default_library")
model.import_library("library/regions_library")

model.add_entity("ElectricalBus", "bus.1")
model.add_attribute("bus.1", "nominal_voltage", 110.0)
model.add_relation("bus.1", "belongsToGeographicalRegion", "region.country.CH")
model.add_relation("bus.1", "belongsToCarrierDomain", "domain.electricity")
model.add_attribute("bus.1", "voltage_magnitude_setpoint", 1.02)
bus_1 = model.get_entity("bus.1")
# bus.2 follows the identical pattern, voltage_magnitude_setpoint=1.00

model.add_entity("GenerationUnit", "gen.1")
model.add_relation("gen.1", "atNode", "bus.1")
gen_1 = model.get_entity("gen.1")
gen_1.power_flow.powerflow_bus_type = "slack"
gen_1.power_flow.active_power_setpoint = 50.0
gen_1.power_flow.voltage_magnitude_setpoint = 1.02
gen_1.dispatch.nominal_power_capacity = 100.0

model.add_entity("DemandUnit", "load.1")
model.add_relation("load.1", "atNode", "bus.2")
load_1 = model.get_entity("load.1")
load_1.power_flow.active_power_demand = 50.0
load_1.power_flow.reactive_power_demand = 20.0

model.add_entity("TransmissionLine", "line.1_2")
model.add_relation("line.1_2", "fromNode", "bus.1")
model.add_relation("line.1_2", "toNode", "bus.2")
line = model.get_entity("line.1_2")
line.power_flow.series_resistance_per_km = 0.12
line.power_flow.series_reactance_per_km = 0.40
line.power_flow.thermal_capacity_rating = 100.0
```

Slack generator on bus 1, a load on bus 2, one line between them —
the smallest network that's still a genuine load-flow case. Note the
bus id convention: `bus.1`/`bus.2` (ending in `.1`/`.2`, never `.0`)
so the MATPOWER exporter, which is 1-indexed, writes `bus_i = 1` and
`2` directly.

Physical, not per-unit, line parameters: `series_resistance_per_km` in
Ω/km, `shunt_susceptance_per_km` in µS/km — CESDM stores physical
quantities; per-unit conversion is the exporter's job, not the model's.

---

## Step 2: Export to MATPOWER, verify structurally

```python
matpower_case = export_matpower_case(model, base_mva=100.0)
matpower_result = verify_matpower_export(
    matpower_case, expected_buses=2, expected_branches=1, min_generators=1,
)
if not matpower_result["ok"]:
    raise SystemExit("MATPOWER verification failed:\n" + "\n".join(matpower_result["errors"]))

write_matpower_case(matpower_case, output_dir / "two_bus_from_cesdm.m", function_name="two_bus_from_cesdm")
```

`verify_matpower_export` checks the exported case actually has the bus/
branch/generator counts you expect — a structural sanity check before
trusting the `.m` file.

---

## Step 3: Export to pandapower, run an actual AC load flow

```python
pp_net = export_pandapower_net(model, name="Two-bus CESDM example", base_mva=100.0)
pp_result = verify_pandapower_export(
    pp_net, expected_buses=2, expected_lines=1, min_generators=1, min_loads=1, min_ext_grids=1,
)

import pandapower as pp
pp.runpp(pp_net, init="flat", calculate_voltage_angles=True)
if not bool(getattr(pp_net, "converged", False)):
    raise RuntimeError("pandapower load flow did not converge.")
pp.to_json(pp_net, str(output_dir / "two_bus_from_cesdm_pandapower.json"))
```

This is the step that goes beyond "the file was written" — an actual
AC power flow is solved on the exported network, and convergence is
checked explicitly rather than assumed. `export_pandapower_net`/
`verify_pandapower_export` degrade gracefully behind a `try/except
ImportError` if the optional `pandapower` dependency isn't installed
— the MATPOWER export above doesn't need it at all.

---

## Result

```
DemandUnit                1
GenerationUnit            1
TransmissionElement       1

✓ Two-bus CESDM model created
✓ CESDM model validated
✓ MATPOWER case exported and verified
✓ pandapower network exported and verified
✓ pandapower network exported, verified, saved, and AC load flow converged   (with pandapower installed)
```

---

## Run it yourself

```bash
pip install -e ".[pandapower,matpower]"
python examples/example_cesdm_to_pandapower_and_matpower.py
```
