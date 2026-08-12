# Part 2: Demand and Generation

!!! info "Checkpoint"
    After Part 2 you should have demand units, a `[TimestampSeries](../../community/glossary.md#timestamp-series)`, library resources, and at least one `GenerationUnit`.

## 5. Add demand

```python
demands = [
    ("dem.ch", "CH electricity demand", 60_000, "bus.ch"),
    ("dem.de", "DE electricity demand", 500_000, "bus.de"),
    ("dem.fr", "FR electricity demand", 450_000, "bus.fr"),
    ("dem.it", "IT electricity demand", 300_000, "bus.it"),
    ("dem.at", "AT electricity demand", 70_000, "bus.at"),
]

for demand_id, name, annual_gwh, bus_id in demands:
    demand = model.add_entity("DemandUnit", demand_id)
    demand.name = name
    demand.annual_energy_demand = (annual_gwh * 1000, "MWh/year")
    demand.atNode = model.get_entity(bus_id)
```

The demand entity remains independent of a particular dispatch tool. Its annual demand and network location are part of the common system representation.

!!! abstract "Core EAR alternative"

    ```python
    model.add_entity(entity_class="DemandUnit", entity_id="dem.ch")
    model.add_attribute(
        entity_id="dem.ch",
        attribute_id="name",
        value="CH electricity demand",
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id="dem.ch",
        attribute_id="annual_energy_demand",
        value=60_000_000,
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id="dem.ch",
        relation_id="atNode",
        target_entity_id="bus.ch",
    )
    ```

---

## 6. Define the shared time axis

A `[TimestampSeries](../../community/glossary.md#timestamp-series)` is also an ordinary CESDM entity:

```python
timestamps = model.add_entity("TimestampSeries", "ts.hourly.2030")
timestamps.name = "Hourly, 2030"
timestamps.start_datetime = "2030-01-01T00:00:00"
timestamps.resolution = "PT1H"
timestamps.length = 8760
timestamps.timezone = "Europe/Zurich"
```

Several profiles can reference this one time axis.

---

## 7. Reuse natural resources from the Default Library

The imported [Default Library](../../community/glossary.md#default-library) already contains reusable resource entities such as:

```text
resource.renewable.wind
resource.renewable.solar
resource.water
```

The project model references these existing entities directly — they are not recreated. Add generators and link library resources or carriers as required:

Illustrative 2030 capacities for CH and neighbours (thermal sized with firm
headroom for peak residual load; renewables carry `annual_resource_potential`):

```python
generators = [
    ("gen.ch.gas", "CH Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 3_000, "bus.ch", "thermal", None),
    ("gen.ch.nuc", "CH Nuclear", GeneratorTypes.GENERATION_NUCLEAR_LWR, 2_000, "bus.ch", "nuclear", None),
    ("gen.ch.wind", "CH Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 500, "bus.ch", "wind", 900_000),
    ("gen.ch.solar", "CH Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 2_000, "bus.ch", "solar", 2_000_000),
    ("gen.de.gas", "DE Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 40_000, "bus.de", "thermal", None),
    ("gen.de.coal", "DE Hard Coal", GeneratorTypes.GENERATION_THERMAL_COAL_HARDCOAL_EXISTING, 25_000, "bus.de", "coal", None),
    ("gen.de.wind", "DE Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 30_000, "bus.de", "wind", 65_000_000),
    ("gen.de.solar", "DE Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 60_000, "bus.de", "solar", 60_000_000),
    ("gen.fr.nuc", "FR Nuclear", GeneratorTypes.GENERATION_NUCLEAR_LWR, 56_000, "bus.fr", "nuclear", None),
    ("gen.fr.gas", "FR Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 8_000, "bus.fr", "thermal", None),
    ("gen.fr.solar", "FR Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 25_000, "bus.fr", "solar", 30_000_000),
    ("gen.it.gas", "IT Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 40_000, "bus.it", "thermal", None),
    ("gen.it.solar", "IT Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 20_000, "bus.it", "solar", 25_000_000),
    ("gen.it.wind", "IT Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 8_000, "bus.it", "wind", 18_000_000),
    ("gen.at.gas", "AT Gas CCGT", GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW, 9_000, "bus.at", "thermal", None),
    ("gen.at.wind", "AT Wind", GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE, 4_000, "bus.at", "wind", 8_000_000),
    ("gen.at.solar", "AT Solar PV", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY, 5_000, "bus.at", "solar", 6_000_000),
]

for (
    generator_id,
    name,
    technology_id,
    capacity_mw,
    bus_id,
    family,
    annual_mwh,
) in generators:
    generator = model.add_entity("GenerationUnit", generator_id)
    generator.name = name
    generator.nominal_power_capacity = (capacity_mw, "MW")
    generator.hasTechnology = technology_id
    generator.atNode = model.get_entity(bus_id)

    if family == "thermal":
        generator.hasInputCarrier = Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
    elif family == "coal":
        generator.hasInputCarrier = Carriers.CARRIER_FUEL_FOSSIL_COAL_HARD_COAL
    elif family == "wind":
        generator.hasInputResource = "resource.renewable.wind"
    elif family == "solar":
        generator.hasInputResource = "resource.renewable.solar"

    if annual_mwh is not None:
        generator.annual_resource_potential = annual_mwh
```

The physical generator contains its asset-specific information. The reusable technology entity from the [Default Library](../../community/glossary.md#default-library) contains shared technology data such as dispatch classification, efficiency, costs, and carrier relations. The system model references that library entity instead of duplicating its content.

Variable renewables (wind, solar) receive availability profiles in [Part 3](part-3-profiles-and-interconnectors.md). The executable scripts also synthesise hourly arrays into `profiles.h5` and print an illustrative annual energy balance.

!!! abstract "Core EAR alternative"

    ```python
    model.add_entity(entity_class="GenerationUnit", entity_id="gen.ch.gas")
    model.add_attribute(
        entity_id="gen.ch.gas",
        attribute_id="name",
        value="CH Gas CCGT",
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id="gen.ch.gas",
        attribute_id="nominal_power_capacity",
        value=3000,
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id="gen.ch.gas",
        relation_id="hasTechnology",
        target_entity_id=GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW,
    )
    model.add_relation(
        entity_id="gen.ch.gas",
        relation_id="hasInputCarrier",
        target_entity_id=Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS,
    )
    model.add_relation(
        entity_id="gen.ch.gas",
        relation_id="atNode",
        target_entity_id="bus.ch",
    )
    ```

---

## Navigation

← Previous: [Part 1](part-1-system-and-network.md)  
→ Next: [Part 3 — Profiles and Interconnectors](part-3-profiles-and-interconnectors.md)
