# `explore_cesdm_model.py` — Step by Step

## Why this tool matters

Building a model is half the story — this is the other half: querying
a model you didn't necessarily build yourself. Written for a
PyPSA-imported model specifically (capacity by country, generation
mix, storage, network summary), but every function in it is a
reusable pattern for exploring *any* CESDM model, built from nothing
but `model.entities` and plain attribute/relation lookups — no
energy-specific magic, just systematic traversal.

The report starts with a **per-country totals** block using the same
categories as `aggregate_cesdm_model`'s `sanity_check_by_country.txt`
(dispatchable / nondispatchable capacity and resource potential, hydro
turbine vs. PHS, battery storage, reservoir energy/inflow, demand).

> This script's `main()` needs a CESDM hierarchical YAML as input
> (`--yaml path/to/model.yaml`, e.g. from
> [`example_import_pypsa.py`](../examples/README_PYPSA_IMPORT_LOGIC.md)).
> Schema default is `schemas/cesdm`. The individual functions below
> are demonstrated against a small, self-contained model so they can
> be run with no external data at all.

---

## The simplest pattern: count entities by class

```python
def model_entity_counts(model: CesdmModel) -> Dict[str, int]:
    """model.entities is { class_name: { entity_id: entity_object } }."""
    return {cls: len(entities) for cls, entities in model.entities.items() if entities}
```

```python
# After running docs/examples/minimal_electricity_model.py (or the reference model):
from cesdm_toolbox import build_model_from_yaml
model = build_model_from_yaml("schemas/cesdm")
model.import_yaml_hierarchical("output/minimal_electricity_model/demo_2030.yaml")
print(model_entity_counts(model))
```

`model.entities` is the whole model — a dict keyed by class name, each
value a dict of entity id to entity object. Every exploration function
in this file starts from this same structure.

---

## Reading a nameplate attribute across every instance of a class

```python
def bus_voltage_distribution(model: CesdmModel) -> Dict[int, int]:
    """Count ElectricalBuses by nominal voltage level [kV]."""
    dist: Dict[int, int] = defaultdict(int)
    for _bus_id, bus_ent in (model.entities.get("ElectricalBus") or {}).items():
        kv = _af(bus_ent, "nominal_voltage")
        if kv is not None:
            dist[int(round(kv))] += 1
    return dict(sorted(dist.items()))
```

```python
print(bus_voltage_distribution(model))
# -> {220: 3}
```

`nominal_voltage` lives directly on `ElectricalBus` (a nameplate
property, not something that changes between modelling contexts) —
`_af()` (defined near the top of the file) is a small helper that
reads a numeric attribute value out of the raw entity dict, tolerant
of it being absent.

---

## The harder pattern: following relations across views

Several functions (`build_asset_to_node`, `build_dispatch_index`,
`generation_capacity_by_country_and_type`) follow relation chains
rather than reading one entity directly — e.g. from a
`GenerationUnit`, to its `SinglePort.TopologyView` (via
`reportsOn`), to the `atNode` it's connected to, to that node's
`GeographicalRegion` (via `belongsToGeographicalRegion`). Each hop is a plain dict
lookup; the multi-hop indexes (`build_asset_to_node`,
`build_node_to_country`) exist so later functions don't repeat the
same three-hop walk for every single asset.

---

## Run it yourself

Against a real PyPSA-imported model:

```bash
pip install -e ".[pypsa]"
python examples/example_import_pypsa.py --nc-path <network.nc> --schema-dir schemas/cesdm --output-dir output/pypsa_model
python tools/explore_cesdm_model.py --yaml output/pypsa_model/model.yaml
```

Or call any function directly against a model you already have, as
shown above.
