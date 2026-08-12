# Part 1: System and Carrier Domains

!!! info "Checkpoint"
    After Part 1 you should have an `EnergySystemModel`, four library `CarrierDomain`s, `region.country.CH`, and one typed bus per domain.

## 1. Load schema and libraries

```python
from cesdm_toolbox import build_model_from_yaml
from cesdm.default_library import CarrierDomains, Carriers, GeneratorTypes

model = build_model_from_yaml("schemas/cesdm")
model.import_library("library/default_library")
model.import_library("library/regions_library")
```

The default library provides carriers and domains (`domain.electricity`, `domain.gas`, `domain.heat`, `domain.hydrogen`). The regions library provides `region.country.CH`.

---

## 2. Create the study container

```python
system = model.add_entity("EnergySystemModel", "DISTRICT_HUB_CH_2030")
system.long_name = "Swiss district energy hub — conversion units demo, 2030"
system.co2_price = 120.0

region = model.get_entity("region.country.CH")
```

---

## 3. Resolve the four carrier domains

```python
elec_domain = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)
gas_domain = model.get_entity(CarrierDomains.DOMAIN_GAS)
heat_domain = model.get_entity(CarrierDomains.DOMAIN_HEAT)
h2_domain = model.get_entity(CarrierDomains.DOMAIN_HYDROGEN)
```

Cross-domain conversion never merges these domains — each keeps its own balance. Conversion units are the only semantic bridge ([Carrier Domains](../../guides/carrier-domains.md)).

---

## 4. Add one typed bus per domain

```python
bus_elec = model.add_entity("ElectricalBus", "bus.hub.elec")
bus_elec.name = "District electricity bus"
bus_elec.nominal_voltage = (20.0, "kV")
bus_elec.belongsToCarrierDomain = elec_domain
bus_elec.belongsToGeographicalRegion = region

bus_gas = model.add_entity("GasBus", "bus.hub.gas")
bus_gas.name = "District gas bus"
bus_gas.belongsToCarrierDomain = gas_domain
bus_gas.belongsToGeographicalRegion = region

bus_heat = model.add_entity("HeatBus", "bus.hub.heat")
bus_heat.name = "District heat bus"
bus_heat.belongsToCarrierDomain = heat_domain
bus_heat.belongsToGeographicalRegion = region

bus_h2 = model.add_entity("HydrogenBus", "bus.hub.h2")
bus_h2.name = "District hydrogen bus"
bus_h2.belongsToCarrierDomain = h2_domain
bus_h2.belongsToGeographicalRegion = region
```

Typed buses make topology relations on conversion units explicit (`atElectricityNode`, `atHeatNode`, `atHydrogenNode`, `atFuelNode`).

---

## Navigation

→ Next: [Part 2 — Supply and Demand](part-2-supply-and-demand.md)
