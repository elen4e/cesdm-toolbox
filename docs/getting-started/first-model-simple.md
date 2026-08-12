# Your First Model (Simple)

!!! abstract "Before you start"
    - **Prerequisites:** [Installation](installation.md) or [Quickstart](quickstart.md)
    - **Time:** ~10 minutes
    - **You'll learn:** load schemas, create a tiny electricity model, mix Core and Proxy API, validate, export

This is the **recommended first hands-on tutorial**. It builds a minimal single-domain model — one bus, one wind farm, one demand unit — in about 40 lines of Python.

[Building your CESDM Model](../tutorials/building-first-model/overview.md) goes much further (gas, heat, hydro, profiles, interconnectors). Start here first.

---

## What you will build

```text
EnergySystemModel  DEMO_2030
    └── CarrierDomain  domain.electricity
            ├── ElectricalBus  bus.demo
            ├── GenerationUnit  gen.demo.wind   → library wind technology
            └── DemandUnit      dem.demo
```

| Step | API | What you create |
|------|-----|-----------------|
| 1 | Setup | Schema + default library |
| 2 | **Core [EAR](../community/glossary.md#ear)** | System container + electricity domain |
| 3 | **[Proxy API](../community/glossary.md#proxy-api)** | Bus, generator, demand |
| 4 | Either | Validate + export |

---

## Run the complete script

From the **cesdm-toolbox repository root**:

```bash
python docs/examples/minimal_electricity_model.py
```

Expected output:

```text
Validated N entities and exported to output/minimal_electricity_model
```

Inspect `output/minimal_electricity_model/demo_2030.yaml`, `profiles.h5`, and the `frictionless/` folder.

---

## Step-by-step (same model)

### 1 — Load schema and library

```python
from cesdm_toolbox import build_model_from_yaml
from cesdm.default_library import Carriers, GeneratorTypes

model = build_model_from_yaml("schemas/cesdm")
model.import_library("library/default_library")
```

### 2 — Core EAR API: system; electricity domain from the library

Use the three core operations explicitly for the study container — this is what every CESDM model uses under the hood. Default CarrierDomains come from the library after `import_library`:

```python
from cesdm.default_library import CarrierDomains

model.add_entity(entity_class="EnergySystemModel", entity_id="DEMO_2030")
model.add_attribute(
    entity_id="DEMO_2030",
    attribute_id="long_name",
    value="Minimal electricity demo",
)

electricity = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)
```

### 3 — Proxy API: bus, generator, demand

For assets, the Proxy API is shorter and easier to read:

```python
bus = model.add_entity("ElectricalBus", "bus.demo")
bus.name = "Demo bus 380 kV"
bus.nominal_voltage = (380, "kV")
bus.belongsToCarrierDomain = electricity

gen = model.add_entity("GenerationUnit", "gen.demo.wind")
gen.name = "Demo wind farm"
gen.nominal_power_capacity = (500, "MW")
gen.hasTechnology = GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE
gen.atNode = bus

demand = model.add_entity("DemandUnit", "dem.demo")
demand.name = "Demo electricity demand"
demand.annual_energy_demand = (2_000_000, "MWh/year")  # 2 TWh/year
demand.atNode = bus
```

!!! tip "Units"
    CESDM validates attribute units against the schema. `annual_energy_demand` must use **`MWh/year`** (not `GWh`). Convert: 1 GWh = 1,000 MWh.

Both APIs write to the **same model**. Core API is explicit; Proxy API is what you will use most often for your own studies — see [Object-oriented Proxy API](../guides/proxy-api.md).

### 4 — Validate and export

```python
errors = model.validate()
if errors:
    for e in errors:
        print(e)
else:
    print("Schema validation passed.")

model.export_yaml_hierarchical("output/minimal_electricity_model/demo_2030.yaml")
model.export_frictionless(
    "output/minimal_electricity_model/frictionless",
    name="minimal-electricity-demo",
    title="Minimal electricity demo model",
)
```

---

## Optional: run in Jupyter

Copy the steps above into a new notebook, or run the script in a single cell:

```python
%run docs/examples/minimal_electricity_model.py
```

You do **not** need Jupyter for this tutorial; the script is enough for a first win.

---

## What this tutorial deliberately skips

To stay short, this example omits:

- geographical regions and multi-country scope;
- gas, heat, and other [carrier domains](../community/glossary.md#carrier-domain);
- [profiles](../guides/profiles.md) and [timestamp series](../community/glossary.md#timestamp-series);
- interconnectors and conversion units.

Those appear in [Building your CESDM Model](../tutorials/building-first-model/overview.md).

---

## Next step

1. **[Core Concepts](core-concepts.md)** — name what you did (class vs instance, [EAR](../community/glossary.md#ear))
2. **[Proxy API](../guides/proxy-api.md)** — build your own models efficiently
3. **[Building your CESDM Model](../tutorials/building-first-model/overview.md)** — full multi-domain reference when you are ready

→ [Modeller cheat sheet](modeller-cheat-sheet.md)
