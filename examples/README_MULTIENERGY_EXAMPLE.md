# `example_multienergy.py` — Step by Step

## Why this example matters

Real energy systems are rarely electricity-only. This example shows
the pattern for coupling sectors — gas, electricity, and heat — through
a single conversion unit (a CHP plant), the same multi-port pattern any
sector-coupling study (power-to-gas, electrolysis, heat pumps) needs.

---

## Three separate carrier domains, three typed buses

```python
for eid, name, co2, cost in [
    ("carrier.gas",         "Natural gas",  0.20, 60.0),
    ("carrier.electricity", "Electricity",  0.0,   0.0),
    ("carrier.heat",        "Heat",         0.0,   0.0),
]:
    carrier = m.ensure_carrier(eid, name=name)
    m.set_attribute_if_allowed(carrier, "co2_emission_intensity", co2)

for did, name, carrier in [("D_GAS", "Gas", "carrier.gas"), ("D_ELEC", "Electricity", "carrier.electricity"), ("D_HEAT", "Heat", "carrier.heat")]:
    domain = m.ensure_entity("CarrierDomain", did, name=name)
    m.add_relation_if_allowed(domain, "hasCarrier", carrier)

n_gas = m.ensure_entity("GasBus", "N_CH_GAS", name="CH gas bus")
n_elec = m.ensure_entity("ElectricalBus", "N_CH_ELEC", name="CH electricity bus")
n_heat = m.ensure_entity("HeatBus", "N_CH_HEAT", name="CH heat bus")
```

`ensure_entity()` creates the entity only if it doesn't already exist
and returns it wrapped in a typed proxy directly — the same
create-if-missing, class-agnostic escape hatch used for any class
without a more specific reason to use `add_entity()` directly.
`set_attribute_if_allowed`/`add_relation_if_allowed` are the
schema-checked, "don't raise if the attribute doesn't apply" siblings
used throughout when a field might not exist on every code path.

---

## An exogenous supply, connected like any other asset

```python
gas_supply = m.get_entity_as(
    m.ensure_entity("ExternalSupply", "GAS_SUPPLY", name="Gas supply"),
    ExternalSupplyProxy,
)
m.add_relation_if_allowed(gas_supply, "hasOutputCarrier", "carrier.gas")
gas_supply.connect(n_gas)

gas_supply.dispatch.is_slack = True
gas_supply.dispatch.supply_capacity = 1e6
```

`get_entity_as(entity_id, ExternalSupplyProxy)` gives `gas_supply` the
concrete, typed proxy so `.dispatch.is_slack` type-checks in an editor
— see [`docs/architecture/proxy_api.md`](../docs/architecture/proxy_api.md)
for when `get_entity_as` is worth reaching for over `add_entity()`/
`get_entity()`'s own automatic typing.

---

## The CHP plant: sector coupling through a multi-port conversion unit

```python
m.add_entity("GenericConversionUnit", "CHP_1")

# Reference port: gas input (flow_coefficient = -1.0, negative = withdrawal)
m.add_entity("ConversionPort", "port.CHP_1.gas_in")
m.add_attribute("port.CHP_1.gas_in", "flow_coefficient", -1.0)
m.add_relation("port.CHP_1.gas_in", "belongsToUnit", "CHP_1")
m.add_relation("port.CHP_1.gas_in", "atNode", n_gas)
m.add_relation("CHP_1", "referencePort", "port.CHP_1.gas_in")

# Electricity output: 35% of the reference gas flow
m.add_entity("ConversionPort", "port.CHP_1.elec_out")
m.add_attribute("port.CHP_1.elec_out", "flow_coefficient", 0.35)
m.add_relation("port.CHP_1.elec_out", "atNode", n_elec)

# Heat output: 45% of the reference gas flow
m.add_entity("ConversionPort", "port.CHP_1.heat_out")
m.add_attribute("port.CHP_1.heat_out", "flow_coefficient", 0.45)
m.add_relation("port.CHP_1.heat_out", "atNode", n_heat)
```

Every conversion ratio is expressed as a coefficient relative to the
unit's **`referencePort`** (typically the primary input, flow_coefficient
negative = withdrawal) — here, 1 unit of gas in becomes 0.35 units of
electricity and 0.45 units of heat out (an 80% combined efficiency CHP). A
`ConversionUnit`'s ports are a genuine many-per-asset relationship
(see [`docs/guide/03_schemas.md`](../docs/guide/03_schemas.md)), so each is
its own `ConversionPort` entity — the same pattern used in
a compact fuel-cell / conversion demo.

---

## Demand on two different carriers

```python
for lid, name, demand_mwh, node in [
    ("LOAD_ELEC", "Electricity demand", 200_000.0, n_elec),
    ("LOAD_HEAT", "Heat demand",        300_000.0, n_heat),
]:
    m.add_entity("DemandUnit", lid)
    m.add_relation(lid, "atNode", node)
    load = m.get_entity(lid)
    load.dispatch.annual_energy_demand = demand_mwh
```

---

## Result

```
DemandUnit           2
ConversionUnit       1
ExternalSupply       1

Model validated successfully.
```

---

## Run it yourself

```bash
python examples/example_multienergy.py
```
