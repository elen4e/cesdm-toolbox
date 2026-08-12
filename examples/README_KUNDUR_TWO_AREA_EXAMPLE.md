# `example_kundur_two_area.py` — Step by Step

## Why this example matters

This is the only example reaching past steady-state dispatch and power
flow into dynamic/stability modelling — machine models, voltage
regulators (AVR), turbine governors (GOV), and power system stabilizers
(PSS). It reproduces a genuinely well-known benchmark (Kundur's
four-machine, two-area system, *Power System Stability and Control*,
1994, Ch. 12), so every number in it is independently checkable
against a real textbook, not invented for the demo.

---

## One generator, a linked machine model, three linked controllers

```python
model.add_entity("GenerationUnit", gen_id)
model.add_relation(gen_id, "atNode", bus_id)
gen = model.get_entity(gen_id)

# Power flow -- all in MW / MVAr / pu / deg
pf = gen.power_flow
for attr, val in _GEN_PF[gen_id].items():
    setattr(pf, attr, val)

# Dynamic machine model: a reusable DynamicMachineModelType.Synchronous
# ids are already underscore-separated).
dyn_id = f"dyn.machine.{gen_id}"
model.add_entity("DynamicMachineModelType.Synchronous", dynamic_model_type_id)
for attr, val in mach.items():
    model.add_attribute(dyn_id, attr, val)
gen.rated_apparent_power = 900.0
gen.rated_voltage = 20.0
gen.usesDynamicModelType = dynamic_model_type_id

# Automatic Voltage Regulator (SEXS model) -- a separate entity, linked
# via controlsGenerationUnit
avr_id = f"dyn.avr.{gen_id}"
model.add_entity("Controller.AVR.SEXS", avr_id)
model.add_relation(avr_id, "controlsGenerationUnit", gen_id)
for attr, val in _AVR.items():
    model.add_attribute(avr_id, attr, val)
gen.hasAutomaticVoltageRegulator = avr_id

# Power System Stabilizer (STAB1 model) and turbine governor (IEEEG1
# model) follow the identical pattern -- Controller.PSS.STAB1 /
# Controller.GOV.IEEEG1, linked via controlsGenerationUnit, then wired
# back onto the generator via hasPowerSystemStabilizer /
# hasTurbineGovernor.
```

The machine model's own parameters (`d_axis_synchronous_reactance`, `inertia_constant`, ...)
live on the reusable `DynamicMachineModelType.Synchronous` entity, not on
`GenerationUnit` itself — the dynamic-model family is an independent
dimension from generation technology (a wind or solar generator has no
synchronous machine at all, so there is nothing to flatten onto it).
Their real IEEE-typical defaults resolve lazily on read if never set
(`dyn.dynamics.d_axis_synchronous_reactance`, or flat `dyn.d_axis_synchronous_reactance` — same storage
either way). AVR/GOV/PSS controllers follow the identical standalone-
entity pattern for a related reason: a generator can have at most one
of each, but three mutually exclusive AVR types (and similarly
governor/PSS) each carry their own distinct attribute set, so
flattening all of them onto `GenerationUnit` would mean carrying
every variant's attributes simultaneously. See
[`docs/architecture/proxy_api.md`](../docs/architecture/proxy_api.md).

---

## Power-flow parameters: transformers and lines

```python
model.add_entity("Transformer", tfr_id)
model.add_attribute(tfr_id, "name", tfr_id.upper())
tfr = model.get_entity(tfr_id)
tfr.connect(from_bus, to_bus)
tfr.power_flow.short_circuit_voltage_in_percentage = scc_pct
tfr.power_flow.thermal_capacity_rating = rated_mva

model.add_entity("TransmissionLine", line_id)
model.add_relation(line_id, "fromNode", from_bus)
model.add_relation(line_id, "toNode", to_bus)
line = model.get_entity(line_id)
line.power_flow.line_length = length_km
line.power_flow.series_resistance_per_km = pu_to_ohm(r_pu, Z_base_sys) / length_km
line.power_flow.series_reactance_per_km = pu_to_ohm(x_pu, Z_base_sys) / length_km
line.power_flow.shunt_susceptance_per_km = pu_to_siemens(b_pu, Z_base_sys) / length_km
```

The source data (Kundur's own textbook table) gives *total* impedances in
per-unit on the system base — `pu_to_ohm`/`pu_to_siemens` convert them
to physical units, then divide by `line_length` so CESDM stores true
per-km quantities.

The example also runs `validate_for_analysis("power_flow")` and
`validate_for_analysis("dynamics")` after schema validation, so the
machine/AVR/GOV/PSS parameters and line lengths are checked against the
study profiles in `analysis_profiles/`.

---

## Result

```
Network nodes  : 11 buses
Generators     : 4 units
Transformers   : 4 units
Lines          : 7 circuits
Loads          : 2 units

Generator machine parameters (converted to physical units)
             Xd [Ω]    X'd [Ω]  X'' d [Ω]  H [s]  Pset [MW]
gen.g1       1.8000     0.3000     0.2500    6.5      700.0
gen.g2       1.8000     0.3000     0.2500    6.5      700.0
gen.g3       1.8000     0.3000     0.2500    6.5      719.0
gen.g4       1.8000     0.3000     0.2500    6.5      700.0
```

Every value printed here is recomputed from what's actually stored in
the model (converted back from physical units for display) — not
copy-pasted from the source table — so it also serves as an implicit
round-trip check.

---

## Run it yourself

```bash
python examples/example_kundur_two_area.py
```
