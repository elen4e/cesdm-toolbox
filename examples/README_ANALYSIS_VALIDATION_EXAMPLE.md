# `example_analysis_validation.py` — Step by Step

## Why this example matters

`model.validate()` passing does **not** mean a model is ready for the
analysis you actually want to run. The schema doesn't require
`variable_operating_cost` on a generator — plenty of valid CESDM
models (a pure topology study, say) never need it — but an
optimal-dispatch study can't run without it. This example shows the
separate check that catches that gap, and — just as importantly —
what happens when you feed the model a genuinely invalid value, since
that behaviour is easy to get wrong assumptions about.

Full design: [`docs/guide/10_analysis_validation.md`](../docs/guide/10_analysis_validation.md).

---

## Step 1: Build a model with one deliberate gap

```python
from cesdm_toolbox import build_model_from_yaml

model = build_model_from_yaml("schemas/cesdm")
model.import_library("library/default_library")

model.add_entity("ElectricalBus", "bus.1")
model.add_attribute("bus.1", "nominal_voltage", 380)
bus1 = model.get_entity("bus.1")
model.add_entity("ElectricalBus", "bus.2")
model.add_attribute("bus.2", "nominal_voltage", 380)

# A fully specified generator -- everything an optimal-dispatch
# study needs is set.
model.add_entity("GenerationUnit", "gas.1")
model.add_relation("gas.1", "hasTechnology", "Generation.Thermal.Gas.CCGT.New")
model.add_relation("gas.1", "atNode", "bus.1")
gas = model.get_entity("gas.1")
gas.name = "Gas plant"
gas.dispatch.nominal_power_capacity = 400
gas.dispatch.variable_operating_cost = 32.0

# Schema-valid, but NOT ready for that same study --
# variable_operating_cost is never set below (on purpose).
model.add_entity("GenerationUnit", "wind.1")
model.add_relation("wind.1", "hasTechnology", "Generation.Renewable.Wind.Onshore")
model.add_relation("wind.1", "atNode", "bus.1")
wind = model.get_entity("wind.1")
wind.name = "Wind farm"
wind.dispatch.nominal_power_capacity = 150

model.add_entity("TransmissionLine", "line.1")
model.add_relation("line.1", "fromNode", "bus.1")
model.add_relation("line.1", "toNode", "bus.2")
line = model.get_entity("line.1")
line.power_flow.thermal_capacity_rating = 500
```

Two generators, one line — `wind` is missing `variable_operating_cost`
on purpose, to demonstrate what the next two steps catch (and don't
catch).

---

## Step 2: Schema validation passes — but that's not the whole story

```python
schema_errors = model.validate()
print(f"model.validate(): {len(schema_errors)} error(s)")
# -> model.validate(): 0 error(s)
```

Every attribute set above is well-formed CESDM: correct types,
in-range values, valid relations. `validate()` has nothing to
complain about — it only checks structural completeness against the
*schema*, and the schema never required `variable_operating_cost` in
the first place.

---

## Step 3: Analysis validation catches what the schema doesn't require

```python
dispatch_errors = model.validate_for_analysis("optimal_dispatch")
print(f"validate_for_analysis('optimal_dispatch'): {len(dispatch_errors)} error(s)")
for e in dispatch_errors:
    print(" -", e)
```

```
validate_for_analysis('optimal_dispatch'): 1 error(s)
 - [optimal_dispatch] [GenerationUnit:wind.1] missing required 'variable_operating_cost (view: dispatch)'
```

`"optimal_dispatch"` is a YAML profile
([`analysis_profiles/optimal_dispatch.yaml`](../analysis_profiles/optimal_dispatch.yaml))
declaring exactly this requirement — a check like this can be written
for *any* analysis, independent of what the schema itself enforces.

Fixing it is exactly what you'd expect:

```python
wind.dispatch.variable_operating_cost = 0.0
dispatch_errors = model.validate_for_analysis("optimal_dispatch")
# -> 0 error(s): the model is now ready for this specific analysis
```

---

## Step 4: What an actual constraint violation looks like

This is the part worth paying close attention to. Setting an invalid
enum value:

```python
gas.dispatch.dispatch_type = "steerable"  # not one of the allowed values
```

prints this **immediately**:

```
[GenerationUnit:gas.1] Value 'steerable' is not allowed for 'dispatch_type'. Allowed: ['dispatchable', 'nondispatchable', 'must_run']
```

— but it does **not** raise an exception, and does **not** block the
assignment. The invalid value is set regardless. If your script isn't
watching stdout (a batch job, a notebook with output scrolled away), a
genuinely broken value can sit in the model unnoticed.

`model.validate()` is the authoritative, structured way to catch this
— a list you can check in code, not a message you have to notice:

```python
schema_errors = model.validate()
print(f"model.validate() now reports {len(schema_errors)} error(s):")
for e in schema_errors:
    print(" -", e)
```

```
model.validate() now reports 1 error(s):
 - [GenerationUnit:gas.1] Attribute 'dispatch_type' not in enum ['dispatchable', 'nondispatchable', 'must_run']: steerable
```

**Takeaway**: never treat "no warning printed while building" as proof
a model is correct. Always call `model.validate()` (and
`model.validate_for_analysis(...)`, if relevant) before trusting a
model — both return plain lists your code can check, rather than
relying on console output.

---

## Step 5: Fix it and confirm the model is fully ready

```python
gas.dispatch.dispatch_type = "dispatchable"
schema_errors = model.validate()
dispatch_errors = model.validate_for_analysis("optimal_dispatch")
print(f"validate()={len(schema_errors)} errors, "
      f"validate_for_analysis()={len(dispatch_errors)} errors -- model is fully ready.")
# -> validate()=0 errors, validate_for_analysis()=0 errors -- model is fully ready.
```

## Step 6: Export

```python
model.export_yaml_hierarchical(out_dir / "model.yaml")
```

---

## Run it yourself

```bash
python examples/example_analysis_validation.py
```
