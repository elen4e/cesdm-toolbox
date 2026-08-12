# `example_hydro_reservoir_plant.py` — Step by Step

## Why this example matters

A hydro plant is never one entity — it's a reservoir (storage) linked
to a turbine (generation), connected by `drawsFromHydraulicStorage`/
`suppliesResourceTo` relations. There's no `HydroPowerPlant` wrapper
class hiding this; both entities plus the relation pairing between
them are created directly with core EAR calls. This is the general
pattern for any physical system made of multiple linked assets, not
just hydro.

Two variants are shown: simple reservoir hydro, and closed-loop
pumped storage (PHS) — the same structural pattern, with a reversible
turbine and a second, lower reservoir.

---

## Reservoir hydro: two linked entities, wired directly

```python
m.add_entity("HydraulicStorageUnit", "reservoir.alpine")
m.add_entity("HydroGenerationUnit", "gen.hydro.alpine")
m.add_relation("gen.hydro.alpine", "drawsFromHydraulicStorage", "reservoir.alpine")
m.add_relation("reservoir.alpine", "suppliesResourceTo", "gen.hydro.alpine")
reservoir = m.get_entity("reservoir.alpine")
gen = m.get_entity("gen.hydro.alpine")

gen.dispatch.nominal_power_capacity = 500.0
reservoir.dispatch.energy_storage_capacity = 2500.0

m.set_attribute_if_allowed(reservoir, "name", "Alpine reservoir")
m.add_relation_if_allowed(reservoir, "storesResource", "resource.water")
reservoir.dispatch.annual_natural_inflow_energy = 900_000.0

m.set_attribute_if_allowed(gen, "name", "Alpine hydro turbine")
m.set_attribute_if_allowed(gen, "hydro_machine_kind", "turbine")
m.add_relation_if_allowed(gen, "hasInputResource", "resource.water")
m.add_relation_if_allowed(gen, "hasOutputCarrier", "carrier.electricity")
gen.connect(bus)

gen.dispatch.dispatch_type = "dispatchable"
gen.dispatch.hydro_machine_kind = "turbine"
gen.dispatch.turbine_efficiency = 0.90
```

The `HydraulicStorageUnit` and the `HydroGenerationUnit` are two
separate entities, linked by the `drawsFromHydraulicStorage`/
`suppliesResourceTo` relation pair set explicitly in both directions.
`set_attribute_if_allowed()`/`add_relation_if_allowed()` set a field
only if the entity's class actually declares it (returning `False`
rather than raising if not) — used here for fields shared with other
asset types, so the same helper works regardless of the exact class.

`dischargesToHydraulicStorage` (where the turbine's outflow goes — a
downstream cascade stage) is deliberately left unset here: the
outflow reaches the river directly in this example, with no modelled
downstream reservoir.

---

## Pumped hydro storage (PHS): the same pattern, reversible, three entities

```python
m.add_entity("HydraulicStorageUnit", "reservoir.grimsel.upper")
m.add_entity("HydraulicStorageUnit", "reservoir.grimsel.lower")
m.add_entity("HydroGenerationUnit", "gen.phs.grimsel")
m.add_relation("gen.phs.grimsel", "drawsFromHydraulicStorage", "reservoir.grimsel.upper")
m.add_relation("gen.phs.grimsel", "dischargesToHydraulicStorage", "reservoir.grimsel.lower")
m.add_relation("reservoir.grimsel.upper", "suppliesResourceTo", "gen.phs.grimsel")
upper = m.get_entity("reservoir.grimsel.upper")
lower = m.get_entity("reservoir.grimsel.lower")
gen = m.get_entity("gen.phs.grimsel")

gen.dispatch.nominal_power_capacity = 420.0
gen.dispatch.maximum_pumping_power = 420.0
gen.dispatch.pumping_efficiency = 0.82
gen.dispatch.turbine_efficiency = 0.87
gen.dispatch.hydro_machine_kind = "reversible"

m.set_attribute_if_allowed(gen, "hydro_machine_kind", "reversible")
m.set_attribute_if_allowed(gen, "turbine_type", "reversible_francis")
gen.connect(bus)
```

Three linked entities this time — the upper reservoir, the lower
reservoir, and the reversible turbine — with `drawsFromHydraulicStorage`/
`suppliesResourceTo`/`dischargesToHydraulicStorage` all wired between them
explicitly. The turbine can both generate (upper → lower, producing
electricity) and pump (lower → upper, consuming it) — that's what
`hydro_machine_kind="reversible"` and `maximum_pumping_power` describe.

---

## Result

```
=== Reservoir-Hydro example ===
GenerationUnit       1
StorageUnit          1
Validation errors: 0

=== PHS closed-loop example ===
StorageUnit          2
GenerationUnit       1
Validation errors: 0
```

---

## Run it yourself

```bash
python examples/example_hydro_reservoir_plant.py
```
