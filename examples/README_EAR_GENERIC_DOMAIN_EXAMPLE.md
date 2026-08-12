# `example_ear_generic_domain.py` — Step by Step

## Why this example matters

Every other example in this folder is about energy systems. This one
is deliberately not — it's the proof that `ear_toolbox` genuinely has
no idea what a generator or a bus is. The exact same primitives
(`add_entity`, `add_attribute`, `add_relation`, `validate()`,
`export_yaml`/`import_yaml`) that every energy-system example uses
underneath the proxy API work identically for households and energy
communities here, with zero energy-specific helper methods anywhere.
If you ever need EAR for a completely different structured domain —
not just a different energy dataset — this is the example to start
from.

`ear.entity_proxy.EntityProxy` (a generic str-subclass wrapper with
direct attribute/relation assignment and `.add_attribute()`/
`.add_relation()`) works here too, unlike `cesdm.proxy`'s
domain-specific layer (`.dispatch`, `.power_flow`, `.connect(...)`,
built specifically for CESDM's energy-domain groups) — see
[`docs/architecture/proxy_api.md`](../docs/architecture/proxy_api.md)
for the full split between the two.

See [`docs/guide/09_ear_toolbox.md`](../docs/guide/09_ear_toolbox.md)
for the same scenario narrated in prose.

---

## Step 1: Load a completely different schema

```python
from ear_toolbox import build_model_from_yaml

model = build_model_from_yaml("schemas/agentbased")
```

`schemas/agentbased/` is a separate schema tree from the main
`schemas/cesdm/` — households, energy communities, municipalities, cantons,
and organisations, none of which exist in core CESDM.

---

## Step 2: Build the dataset with raw EAR primitives

```python
model.add_entity("Canton", "canton.zh")
model.add_attribute("canton.zh", "name", "Zürich")

model.add_entity("Organisation", "org.sunergy")
model.add_attribute("org.sunergy", "name", "Sunergy Genossenschaft")

model.add_entity("Municipality", "mun.zurich.261")
model.add_attribute("mun.zurich.261", "name", "Zürich")
model.add_attribute("mun.zurich.261", "bfs_code", 261)
model.add_attribute("mun.zurich.261", "population", 420_000)
model.add_relation("mun.zurich.261", "isPartOf", "canton.zh")

model.add_entity("EnergyCommittee", "ec.sunergy.zh.001")
model.add_attribute("ec.sunergy.zh.001", "name", "Sunergy Zürich-West")
model.add_attribute("ec.sunergy.zh.001", "member_count", 48)
model.add_relation("ec.sunergy.zh.001", "locatedIn", "mun.zurich.261")
model.add_relation("ec.sunergy.zh.001", "hasOperator", "org.sunergy")

model.add_entity("Household", "hh.zh.001.0042")
model.add_attribute("hh.zh.001.0042", "occupant_count", 3)
model.add_attribute("hh.zh.001.0042", "has_pv", True)
model.add_relation("hh.zh.001.0042", "locatedIn", "mun.zurich.261")
model.add_relation("hh.zh.001.0042", "memberOf", "ec.sunergy.zh.001")

model.add_entity("Household", "hh.zh.001.0043")
model.add_attribute("hh.zh.001.0043", "occupant_count", 2)
model.add_attribute("hh.zh.001.0043", "has_pv", False)
model.add_relation("hh.zh.001.0043", "locatedIn", "mun.zurich.261")
```

Two households, one of which belongs to an energy community and has
solar panels; both belong to the same municipality. `isPartOf` and
`hasOperator` are set here — the schema marks both as required
relations (a `Municipality` needs a `Canton`, an `EnergyCommittee`
needs an operating `Organisation`), exactly the kind of thing
`validate()` below would otherwise catch missing.

---

## Step 3: Validate — same method, same meaning, different domain

```python
errors = model.validate()
print(f"model.validate(): {len(errors)} error(s)")
# -> model.validate(): 0 error(s)
```

---

## Step 4: Query with only generic primitives

```python
prosumers = [
    eid for eid, _ in model.entities["Household"].items()
    if model.get_attr_value("Household", eid, "has_pv") is True
]
print("Prosumer households:", prosumers)
# -> Prosumer households: ['hh.zh.001.0042']

total_occupants = sum(
    model.get_attr_value("Household", eid, "occupant_count") or 0
    for eid in model.entities["Household"]
)
print("Total occupants across all households:", total_occupants)
# -> Total occupants across all households: 5
```

`get_attr_value(class_name, entity_id, field_id)` reads attributes
*and* relations uniformly — the same one method used for `has_pv`
(an attribute) here would work identically for `memberOf` (a
relation) too. `model.entities` is a plain dict of dicts, class name
to entity id to entity — no energy-specific accessor anywhere in this
step.

---

## Step 5: The generic `EntityProxy` works here too

```python
from ear.entity_proxy import EntityProxy

first_household_id = next(iter(model.entities["Household"]))
household = EntityProxy(model, first_household_id)
print(f"\n{household!r}")
print("household.occupant_count (direct attribute access):", household.occupant_count)
household.occupant_count = household.occupant_count + 1
print("after household.occupant_count += 1:", household.occupant_count)
```

```
<EntityProxy Household id='hh.zh.001.0042'>
household.occupant_count (direct attribute access): 3
after household.occupant_count += 1: 4
```

`ear.entity_proxy.EntityProxy` needs nothing beyond core EAR concepts
(`class_attributes()`, `class_relations()`, ...), so direct attribute
assignment and `.add_attribute()`/`.add_relation()` work exactly the
same way here as they do for any CESDM asset — it's `cesdm.proxy`'s
`.dispatch`/`.power_flow`/`.connect(...)` specifically that are
CESDM-only, not the proxy mechanism itself.

---

## Step 6: Export, then re-import to confirm a clean round trip

```python
model.export_yaml(out_dir / "households.yaml")

reloaded = build_model_from_yaml("schemas/agentbased")
reloaded.import_yaml(out_dir / "households.yaml")
reload_errors = reloaded.validate()
assert not reload_errors, reload_errors
print("Re-imported and re-validated successfully.")
```

`export_yaml`/`import_yaml` are the plain, flat EAR-level persistence
methods (as opposed to CESDM's `export_yaml_hierarchical`, which
nests `Result` entities under their asset — the only classes left
using CESDM's `reportsOn` pattern, a CESDM-specific concept
this generic schema doesn't have).

---

## Run it yourself

```bash
python examples/example_ear_generic_domain.py
```
