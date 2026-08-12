# `example_schema_extension.py` — Step by Step

## Why this example matters

Sooner or later, every real deployment needs an asset type CESDM
doesn't ship out of the box. The whole point of a schema-driven design
is that this shouldn't require touching the core schema or writing
new Python — this example proves it, adding
`ElectricVehicleChargingStation` end to end: write the schema files,
load them, build a model with the new class connected to a standard
`ElectricalBus`, validate, export. Zero core-schema edits, zero
Python-side class definitions.

Design background: [`docs/getting-started/schemas-in-depth.md`](../docs/getting-started/schemas-in-depth.md).

---

## Step 1: Write the extension's manifest

```python
core_schemas_rel = os.path.relpath(REPO_ROOT / "schemas" / "cesdm", extension_dir)

(extension_dir / "SCHEMA_MANIFEST.yaml").write_text(f"""\
version: "0.1.0"
description: >
  Example schema extension adding ElectricVehicleChargingStation as a
  new CESDM asset type, without modifying the core schema at all.
changelog: none
extends:
  - {core_schemas_rel}
stability:
  assets: experimental
  attributes: experimental
  relations: experimental
""")
```

`extends:` is the same mechanism `schemas/agentbased/` uses to build
on the core schema — resolved relative to the manifest's own
directory, so it's computed here with `os.path.relpath` rather than
hardcoded, and works no matter where the extension directory ends up.

---

## Step 2: Check before defining a new attribute

```python
(extension_dir / "attributes" / "attributes.yaml").write_text("""\
attributes:
  number_of_charging_points:
    label: Number of Charging Points
    description: Count of individual EV charging points at the station.
    value:
      type: integer
      constraints:
        minimum: 1
""")
```

Only **one** new attribute is defined here —
`number_of_charging_points`. The obvious second candidate,
`maximum_charging_power`, turned out to already exist in the core
schema (registered originally for a different asset) — it's reused
directly in Step 3 rather than redefined. Always check
`model.global_attributes` for an existing match before adding a new
one; a duplicate definition with a different meaning is exactly the
kind of drift `docs/guides/schema-governance.md` warns about.

---

## Step 3: Define the new entity class, dispatch attributes flattened directly onto it

```python
(extension_dir / "assets" / "ElectricVehicleChargingStation.yaml").write_text("""\
name: ElectricVehicleChargingStation
parents:
  - EnergyAssetInstance
description: >
  A public or private electric-vehicle charging installation, modelled
  as a controllable electricity demand asset. Dispatch attributes are
  declared directly here (belongsToGroup: [dispatch]) rather than on a
  separate view class -- see CHANGELOG.md.
attributes:
  - id: number_of_charging_points
    required: true
  - id: maximum_charging_power
    required: true
    belongsToGroup: [dispatch]
  - id: annual_energy_demand
    required: false
    belongsToGroup: [dispatch]
relations:
  - id: atNode
    required: false
    belongsToGroup: [topology]
""")
```

Two things worth noticing:

- `parents: [EnergyAssetInstance]` — inheriting from the same base
  every core CESDM asset class does gives it `name`/`long_name`/
  `description` for free.
- `belongsToGroup: [dispatch]`/`[topology]` on the new attributes/
  relation — this is what makes `.dispatch` and `.connect(...)` on the
  proxy API resolve to them automatically for this asset class, the
  exact same schema-driven mechanism every built-in asset class uses
  (see [`docs/guides/proxy-api.md`](../docs/guides/proxy-api.md)).
  There's no separate view entity to define at all — everything lives
  directly on the new class itself.

---

## Step 4: Load it and build a model

```python
model = build_model_from_yaml(extension_dir)
print("ElectricVehicleChargingStation registered:",
      "ElectricVehicleChargingStation" in model.classes)
# -> ElectricVehicleChargingStation registered: True

carrier = model.ensure_entity("Carrier", "carrier.electricity", name="Electricity")
electricity = model.ensure_entity("CarrierDomain", "domain.electricity")
electricity.hasCarrier = carrier
bus = model.ensure_entity("ElectricalBus", "bus.1")
bus.nominal_voltage = 20
bus.belongsToCarrierDomain = electricity

# No add_entity()-wrapping constructor exists specifically for this new
# class -- there are no per-class constructors at all, so it's built
# with the exact same add_entity()/ensure_entity() calls every entity,
# built-in or not, uses.
station = model.ensure_entity(
    "ElectricVehicleChargingStation", "ev.station.1",
    name="Highway rest-stop charger",
)
station.number_of_charging_points = 8
station.dispatch.maximum_charging_power = 2.0
station.dispatch.annual_energy_demand = 3500

# atNode is declared with belongsToGroup: [topology] directly on the
# new class above, so connect() (the same proxy method every other
# asset uses) works on it exactly as-is.
station.connect("bus.1")
```

`build_model_from_yaml(extension_dir)` loads *both* the new class and
every core CESDM class in one call.

---

## Step 5: Validate and export exactly like any other model

```python
errors = model.validate()
print(f"model.validate(): {len(errors)} error(s)")
# -> model.validate(): 0 error(s)

model.export_yaml_hierarchical(out_dir / "ev_charging_model.yaml")
```

The new class round-trips through the same export/import machinery
as every built-in one — nothing about it is special-cased.

---

## Run it yourself

```bash
python examples/example_schema_extension.py
```
