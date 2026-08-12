# Part 3: Profiles and Interconnectors

!!! info "Checkpoint"
    After Part 3 you should have explicit `Profile` entities, reservoir hydro, and `GenericInterconnector` assets.

## 9. Create a Profile explicitly

Renewable generators often need an availability profile. Create the `Profile` entity and link it to the generator and shared time axis:

```python
timestamps = model.get_entity("ts.hourly.2030")

renewable_ids = [
    "gen.ch.wind", "gen.ch.solar",
    "gen.de.wind", "gen.de.solar",
    "gen.fr.solar",
    "gen.it.solar", "gen.it.wind",
    "gen.at.wind", "gen.at.solar",
]
for generator_id in renewable_ids:
    profile_id = f"profile.{generator_id}.capacity_factor"
    profile = model.add_entity("Profile", profile_id)
    profile.profile_type = "as_capacity_factor"
    profile.profile_unit = "pu"
    profile.data_reference = f"profiles.h5:/profiles/{profile_id}"
    profile.hasTimestampSeries = timestamps
    model.get_entity(generator_id).hasAvailabilityProfile = profile
```

This makes the semantic chain visible:

```text
GenerationUnit
    └── hasAvailabilityProfile
            └── Profile
                    └── hasTimestampSeries
                            └── TimestampSeries
```

The numerical array is stored separately at the location identified by `data_reference`.

!!! abstract "Core EAR alternative"

    ```python
    profile_id = "profile.gen.ch.wind.capacity_factor"

    model.add_entity(entity_class="Profile", entity_id=profile_id)
    model.add_attribute(
        entity_id=profile_id,
        attribute_id="profile_type",
        value="as_capacity_factor",
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id=profile_id,
        attribute_id="profile_unit",
        value="pu",
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id=profile_id,
        attribute_id="data_reference",
        value=f"profiles.h5:/profiles/{profile_id}",
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id=profile_id,
        relation_id="hasTimestampSeries",
        target_entity_id="ts.hourly.2030",
    )
    model.add_relation(
        entity_id="gen.ch.wind",
        relation_id="hasAvailabilityProfile",
        target_entity_id=profile_id,
    )
    ```

---

## 10. Represent reservoir hydro

Reservoir storage and hydro generation are separate physical entities connected by explicit relations. The reference model repeats the same composite for CH, DE, FR, IT, and AT (power, energy capacity, natural inflow):

```python
# res_id, res_name, hydro_id, hydro_name, P_MW, bus, E_MWh, inflow_MWh/y
reservoirs = [
    ("storage.ch.hydro.reservoir", "CH Alpine seasonal reservoir",
     "gen.ch.hydro.reservoir", "CH Reservoir hydro turbines",
     8_000, "bus.ch", 8_800_000, 20_000_000),
    ("storage.de.hydro.reservoir", "DE storage hydro reservoir",
     "gen.de.hydro.reservoir", "DE Reservoir hydro turbines",
     2_500, "bus.de", 2_000_000, 5_000_000),
    ("storage.fr.hydro.reservoir", "FR reservoir hydro",
     "gen.fr.hydro.reservoir", "FR Reservoir hydro turbines",
     10_000, "bus.fr", 5_000_000, 15_000_000),
    ("storage.it.hydro.reservoir", "IT Alpine reservoir",
     "gen.it.hydro.reservoir", "IT Reservoir hydro turbines",
     5_000, "bus.it", 4_000_000, 10_000_000),
    ("storage.at.hydro.reservoir", "AT Alpine reservoir",
     "gen.at.hydro.reservoir", "AT Reservoir hydro turbines",
     3_000, "bus.at", 3_000_000, 18_000_000),
]

timestamps = model.get_entity("ts.hourly.2030")
for (
    reservoir_id,
    res_name,
    hydro_id,
    hydro_name,
    capacity_mw,
    bus_id,
    energy_mwh,
    inflow_mwh,
) in reservoirs:
    reservoir = model.add_entity("HydraulicStorageUnit", reservoir_id)
    reservoir.name = res_name
    reservoir.energy_storage_capacity = (energy_mwh, "MWh")
    reservoir.annual_natural_inflow_energy = (inflow_mwh, "MWh/year")
    reservoir.storesResource = "resource.water"

    hydro = model.add_entity("HydroGenerationUnit", hydro_id)
    hydro.name = hydro_name
    hydro.hydro_machine_kind = "turbine"
    hydro.nominal_power_capacity = (capacity_mw, "MW")
    hydro.turbine_efficiency = 0.90
    hydro.annual_resource_potential = inflow_mwh
    hydro.hasTechnology = "Generation.Renewable.Hydro.Reservoir"
    hydro.hasInputResource = "resource.water"
    hydro.atNode = model.get_entity(bus_id)
    hydro.drawsFromHydraulicStorage = reservoir

    inflow_profile = model.add_entity(
        "Profile",
        f"profile.{reservoir_id}.inflow",
    )
    inflow_profile.profile_type = "as_normalized_annual_energy"
    inflow_profile.profile_unit = "pu"
    inflow_profile.data_reference = (
        f"profiles.h5:/profiles/profile.{reservoir_id}.inflow"
    )
    inflow_profile.hasTimestampSeries = timestamps
    reservoir.hasNaturalInflowProfile = inflow_profile
```

The model preserves the distinction between:

- the reservoir that stores water and energy;
- the turbine that converts the resource into electricity;
- the relations that describe their physical association (`drawsFromHydraulicStorage` only; machine → basin).

---

## 11. Add interconnectors

Use explicit topology relations — CH–neighbours plus neighbour–neighbour NTCs:

```python
interconnectors = [
    ("ntc.ch.de", "CH-DE NTC", "bus.ch", "bus.de", 6_000, 5_500),
    ("ntc.ch.fr", "CH-FR NTC", "bus.ch", "bus.fr", 4_000, 3_500),
    ("ntc.ch.it", "CH-IT NTC", "bus.ch", "bus.it", 5_000, 4_500),
    ("ntc.ch.at", "CH-AT NTC", "bus.ch", "bus.at", 2_000, 2_000),
    ("ntc.de.fr", "DE-FR NTC", "bus.de", "bus.fr", 3_500, 3_500),
    ("ntc.de.at", "DE-AT NTC", "bus.de", "bus.at", 4_000, 4_000),
    ("ntc.fr.it", "FR-IT NTC", "bus.fr", "bus.it", 3_000, 3_000),
    ("ntc.at.it", "AT-IT NTC", "bus.at", "bus.it", 2_500, 2_500),
]

for (
    interconnector_id,
    name,
    from_bus,
    to_bus,
    capacity_from_to,
    capacity_to_from,
) in interconnectors:
    interconnector = model.add_entity("GenericInterconnector", interconnector_id)
    interconnector.name = name
    interconnector.maximum_power_flow_from_to = (capacity_from_to, "MW")
    interconnector.maximum_power_flow_to_from = (capacity_to_from, "MW")
    interconnector.fromNode = model.get_entity(from_bus)
    interconnector.toNode = model.get_entity(to_bus)
```

The direction of the connection and both directional transfer capacities are explicit in the model.

!!! abstract "Core EAR alternative"

    ```python
    model.add_entity(entity_class="GenericInterconnector", entity_id="ntc.ch.de")
    model.add_attribute(
        entity_id="ntc.ch.de",
        attribute_id="name",
        value="CH-DE NTC",
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id="ntc.ch.de",
        attribute_id="maximum_power_flow_from_to",
        value=6000,
        unit=None,
        provenance_ref=None,
    )
    model.add_attribute(
        entity_id="ntc.ch.de",
        attribute_id="maximum_power_flow_to_from",
        value=5500,
        unit=None,
        provenance_ref=None,
    )
    model.add_relation(
        entity_id="ntc.ch.de",
        relation_id="fromNode",
        target_entity_id="bus.ch",
    )
    model.add_relation(
        entity_id="ntc.ch.de",
        relation_id="toNode",
        target_entity_id="bus.de",
    )
    ```

---

## Navigation

← Previous: [Part 2](part-2-demand-and-generation.md)  
→ Next: [Part 4 — Multi-carrier and Export](part-4-multicarrier-and-export.md)
