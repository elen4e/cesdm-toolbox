# Part 4: Multi-carrier Coupling and Export

!!! info "Checkpoint"
    After Part 4 you should have a validated model exported to [YAML](../../community/glossary.md#yaml) and [Frictionless Data Package](../../community/glossary.md#frictionless-data-package) format.

## 12. Extend the system with gas and heat

Add carriers, [Carrier Domains](../../community/glossary.md#carrier-domain), and buses with the [Proxy API](../../community/glossary.md#proxy-api):

```python
from cesdm.default_library import CarrierDomains, Carriers

region_ch = model.get_entity("region.country.CH")
gas_domain = model.get_entity(CarrierDomains.DOMAIN_GAS)
heat_domain = model.get_entity(CarrierDomains.DOMAIN_HEAT)

gas_bus = model.add_entity("GasBus", "bus.ch.gas")
gas_bus.name = "Swiss gas bus"
gas_bus.belongsToGeographicalRegion = region_ch
gas_bus.belongsToCarrierDomain = gas_domain

heat_bus = model.add_entity("HeatBus", "bus.ch.heat")
heat_bus.name = "Swiss heat bus"
heat_bus.belongsToGeographicalRegion = region_ch
heat_bus.belongsToCarrierDomain = heat_domain
```

No new modelling API is needed when another physical domain is added — the same Proxy pattern applies throughout.

---

## 13. Couple the domains with gas supply, CHP, and heat demand

```python
gas_bus = model.get_entity("bus.ch.gas")
electricity_bus = model.get_entity("bus.ch")
heat_bus = model.get_entity("bus.ch.heat")

gas_supply = model.add_entity("ExternalSupply", "supply.ch.gas")
gas_supply.name = "Swiss gas import"
gas_supply.supply_capacity = (10_000.0, "MW")
gas_supply.is_slack = True
gas_supply.hasOutputCarrier = Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
gas_supply.atNode = gas_bus

chp = model.add_entity("CHPUnit", "chp.ch")
chp.name = "Swiss CHP plant"
chp.nominal_electrical_power_capacity = (350.0, "MW")
chp.nominal_thermal_power_capacity = (450.0, "MW")
chp.electrical_efficiency = 0.35
chp.thermal_efficiency = 0.45
chp.total_efficiency = 0.80
chp.power_to_heat_ratio = 350.0 / 450.0
chp.hasInputCarrier = Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
chp.hasElectricityOutputCarrier = Carriers.CARRIER_ELECTRICITY
chp.hasHeatOutputCarrier = Carriers.CARRIER_HEAT
chp.atFuelNode = gas_bus
chp.atElectricityNode = electricity_bus
chp.atHeatNode = heat_bus

heat_demand = model.add_entity("DemandUnit", "dem.ch.heat")
heat_demand.name = "Swiss heat demand"
heat_demand.annual_energy_demand = (20_000_000.0, "MWh/year")
heat_demand.atNode = heat_bus
```

The CHP unit couples electricity, gas, and heat through explicit semantic relations on typed entity handles. Capacities here are a compact multi-carrier demo (350 MWe / 450 MWth); they are not sized against the 20 TWh heat demand for adequacy.

---

## 14. Validate and export

Validation and export are workflow operations applied after construction:

```python
errors = model.validate()

if errors:
    for error in errors:
        print(error)
else:
    print("Model validated successfully.")
```

```python
model.export_yaml_hierarchical(
    "output/reference_energy_system_model/"
    "ch_neighbours_2030.yaml"
)

model.export_frictionless(
    "output/reference_energy_system_model/frictionless",
    name="ch-neighbours-2030",
    title="CH + Neighbours 2030 — CESDM tutorial model",
)
```

Validation checks the created entities, attributes, and relations against the schema.

---

## Run the complete example

**Notebook (interactive, Proxy API):**

```bash
pip install -e ".[jupyter]"
jupyter lab notebooks/building_your_cesdm_model.ipynb
```

**Reference script (Core EAR):**

```bash
python ./docs/examples/reference_energy_system_model.py
```

Both write under:

```text
output/reference_energy_system_model/          # script
output/reference_energy_system_model_notebook/ # notebook
├── ch_neighbours_2030.yaml
├── profiles.h5
└── frictionless/
```

---

## Proxy API and Core EAR API

Both interfaces operate on exactly the same CESDM model.

| Operation | [Proxy API](../../community/glossary.md#proxy-api) (this tutorial) | Core [EAR](../../community/glossary.md#ear) API |
|---|---|---|
| Create entity | `entity = model.add_entity(...)` | `model.add_entity(...)` |
| Set attribute | `entity.attribute = value` | `model.add_attribute(...)` |
| Add relation | `entity.relation = target` | `model.add_relation(...)` |

This tutorial and notebook use the **Proxy API** for day-to-day readability. The Core EAR script shows the same model with every operation spelled out explicitly.

The [Proxy API](../../community/glossary.md#proxy-api) provides:

- schema-aware property access;
- concise relation assignments;
- typo detection;
- improved IDE completion;
- identical validation and export behaviour.

It does not introduce a second data model — it is an object-oriented view of the same entities, attributes, and relations.

---

## What the tutorial demonstrates

The Proxy API pattern is sufficient for every part of the model — for example:

```python
bus = model.get_entity("bus.ch")
bus.name          # "Switzerland 380kV"
bus.nominal_voltage  # (380, "kV")
```

It is used to represent:

- regions and [Carrier Domains](../../community/glossary.md#carrier-domain);
- network nodes and interconnectors;
- demand, generation, storage, and conversion assets;
- reusable resource references;
- profiles and time axes;
- multi-domain coupling.

---

## Next Step

See the [Proxy API guide](../../guides/proxy-api.md) for patterns beyond this reference model. Then explore [Libraries](../../guides/libraries.md) and [Profiles](../../guides/profiles.md) as you extend your own study models.

---

## Navigation

← Previous: [Part 3](part-3-profiles-and-interconnectors.md)  
→ Next: [Proxy API Guide](../../guides/proxy-api.md)
