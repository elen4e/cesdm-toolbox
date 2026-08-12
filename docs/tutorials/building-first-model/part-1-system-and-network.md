# Part 1: System and Electricity Network

!!! info "Checkpoint"
    After Part 1 you should have `EnergySystemModel`, `CarrierDomain`, library `GeographicalRegion`s, and `ElectricalBus` entities.

## 1. Load the schema and libraries

```python
from cesdm_toolbox import build_model_from_yaml
from cesdm.default_library import GeneratorTypes, Carriers

model = build_model_from_yaml("schemas/cesdm")
model.import_library("library/default_library")
model.import_library("library/regions_library")
```

The schema defines the permitted [entity classes](../../community/glossary.md#entity-class), attributes, relations, inheritance, and constraints.

The [Default Library](../../community/glossary.md#default-library) contributes reusable entity instances such as carriers and technology definitions. The [regions library](../../guides/libraries.md) adds NUTS / country `GeographicalRegion` entities (e.g. `region.country.CH`). Importing libraries does not create project-specific physical assets.

---

## 2. Create the system and electricity Carrier Domain

An entity is created first, then described by attributes and connected through relations. With the [Proxy API](../../community/glossary.md#proxy-api), you assign them on the handle returned by `add_entity`:

```python
system = model.add_entity("EnergySystemModel", "CH_NEIGHBOURS_2030")
system.long_name = "CH + neighbours multi-domain energy system, 2030"
system.co2_price = 80.0

electricity_domain = model.add_entity("CarrierDomain", "domain.electricity")
electricity_domain.name = "Electricity"
electricity_domain.hasCarrier = Carriers.CARRIER_ELECTRICITY
```

This demonstrates the complete modelling pattern:

1. create an entity;
2. set descriptive or quantitative attributes;
3. relate it to other entities.

!!! abstract "Core EAR alternative"

    The same steps with explicit [EAR](../../community/glossary.md#ear) calls:

    ```python
    model.add_entity(
        entity_class="EnergySystemModel",
        entity_id="CH_NEIGHBOURS_2030",
    )
    model.add_attribute(
        entity_id="CH_NEIGHBOURS_2030",
        attribute_id="long_name",
        value="CH + neighbours multi-domain energy system, 2030",
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id="CH_NEIGHBOURS_2030",
        attribute_id="co2_price",
        value=80.0,
        unit=None,
        provenance_ref=None,
    )

    model.add_entity(
        entity_class="CarrierDomain",
        entity_id="domain.electricity",
    )
    model.add_attribute(
        entity_id="domain.electricity",
        attribute_id="name",
        value="Electricity",
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id="domain.electricity",
        relation_id="hasCarrier",
        target_entity_id=Carriers.CARRIER_ELECTRICITY,
    )
    ```

---

## 3. Use geographical regions from the library

```python
countries = [
    "region.country.CH",
    "region.country.DE",
    "region.country.FR",
    "region.country.IT",
    "region.country.AT",
]

for region_id in countries:
    region = model.get_entity(region_id)  # already present via regions_library
```

Do not recreate these country entities by hand — reference the shared ids from `library/regions_library`.

---

## 4. Build the electricity network

Each country is represented by an aggregated high-voltage bus:

```python
buses = [
    ("bus.ch", "region.country.CH", "Switzerland 380kV", 380.0, 47.0, 8.0),
    ("bus.de", "region.country.DE", "Germany 380kV", 380.0, 51.0, 10.0),
    ("bus.fr", "region.country.FR", "France 400kV", 400.0, 46.0, 2.0),
    ("bus.it", "region.country.IT", "Italy 380kV", 380.0, 42.0, 12.0),
    ("bus.at", "region.country.AT", "Austria 380kV", 380.0, 47.5, 14.0),
]

for bus_id, region_id, name, voltage_kv, latitude, longitude in buses:
    bus = model.add_entity("ElectricalBus", bus_id)
    bus.name = name
    bus.nominal_voltage = (voltage_kv, "kV")
    bus.latitude = latitude
    bus.longitude = longitude
    bus.belongsToGeographicalRegion = model.get_entity(region_id)
    bus.belongsToCarrierDomain = electricity_domain
```

Nothing is hidden behind a bus-specific constructor:

- `ElectricalBus` identifies the [entity class](../../community/glossary.md#entity-class);
- attributes describe the bus;
- relations place it within the geographical and carrier-domain structures.

!!! abstract "Core EAR alternative"

    ```python
    model.add_entity(entity_class="ElectricalBus", entity_id="bus.ch")
    model.add_attribute(
        entity_id="bus.ch",
        attribute_id="name",
        value="Switzerland 380kV",
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id="bus.ch",
        attribute_id="nominal_voltage",
        value=380.0,
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id="bus.ch",
        relation_id="belongsToGeographicalRegion",
        target_entity_id="region.country.CH",
    )
    model.add_relation(
        entity_id="bus.ch",
        relation_id="belongsToCarrierDomain",
        target_entity_id="domain.electricity",
    )
    ```

---

## Navigation

→ Next: [Part 2 — Demand and Generation](part-2-demand-and-generation.md)
