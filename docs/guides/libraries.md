# Libraries

!!! abstract "Before you start"
    - **Prerequisites:** [Core Concepts](../getting-started/core-concepts.md)
    - **See also:** [Proxy API](proxy-api.md) — typical patterns for adding assets
    - **You'll learn:** how to import shared reference entities instead of redefining them

> Libraries provide **reusable CESDM entity instances** that can be shared across multiple projects.

Typical examples include:

- Technology types
- Energy carriers
- Natural resources
- Storage technologies
- Equipment classes
- Other reference entities

Rather than redefining these entities for every project, they can be maintained once in a shared library and referenced by many different system models.

---

## Schemas versus Libraries

Although both are fundamental parts of CESDM, they serve different purposes.

| Schemas | Libraries |
|---------|-----------|
| Define the structure and semantics | Provide reusable entity instances |
| Define entity types | Contain entities |
| Define attribute and relation types | Contain attribute values and relations |
| Define validation rules | Provide reusable reference data |
| Describe *what can exist* | Describe *commonly used objects* |

In other words:

- **Schemas define the semantics.**
- **Libraries provide shared reference entities — instances you import instead of recreating on your own each time.**
- **System models use both to describe a particular energy system.**

<!-- ![Schema to System Model](../illustrations/schema_to_system_model.svg) -->

---

## Why Libraries?

Many energy-system models use the same technologies, carriers, and resources.

Without libraries, every project would need to redefine entities such as:

- Natural Gas
- Electricity
- Wind Resource
- Combined Cycle Gas Turbine
- Lithium-ion Battery
- Pumped Hydro Storage

Libraries avoid this duplication.

Instead, projects simply reference the existing entities.

---

## The CESDM Default Library

CESDM provides a modular default library that contains commonly used reference entities.

```text
library/default_library/
├── carriers/
├── domains/          # domain.electricity, domain.gas, domain.heat, domain.hydrogen
├── resources/
├── generator_types/
└── storage_types/
```

The default library contains **entity instances**, not schema definitions. It can be imported directly into a CESDM model:

```python
from cesdm_toolbox import build_model_from_yaml
from cesdm.default_library import CarrierDomains

model = build_model_from_yaml("schemas/cesdm")
model.import_library("library/default_library")

electricity = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)
bus.belongsToCarrierDomain = electricity
```

After importing the library, the predefined entities become available for reuse throughout the model. Default CarrierDomains (`domain.electricity`, `domain.gas`, `domain.heat`, `domain.hydrogen`) are the shared single-carrier flow scopes — geography stays on regions/buses via `belongsToGeographicalRegion`, not on the domain.

### Regions & market zones library (optional add-on)

Eurostat NUTS 0–3 countries/regions and ENTSO-E-style bidding zones:

```text
library/regions_library/
├── geographical_regions/   # region.country.CH, region.nuts3.CH011, …
└── market_zones/           # market_zone.CH, market_zone.DE_LU, …
```

Regenerate from the NUTS shapefile with `python tools/generate_regions_library.py`.
Import **after** the default library (market zones reference `carrier.electricity`):

```python
model.import_library("library/default_library")
model.import_library("library/regions_library")

ch = model.get_entity("region.country.CH")
bz = model.get_entity("market_zone.CH")
bus.belongsToGeographicalRegion = ch
bus.belongsToMarketZone = bz
```

### TYNDP library (optional add-on)

Fine-grained ENTSO-E TYNDP vintages (`Old1` / `Old2` / `Present*`, oil shale)
live in a separate package so the default catalogue stays on
`Existing` / `New` / `CCS` / `Biofuel`:

```text
library/tyndp_library/
└── generator_types/
```

Import **after** the default library (carriers/resources stay in default):

```python
model.import_library("library/default_library")
model.import_library("library/tyndp_library")
```

The TYNDP importers (`examples/example_import_tyndp.py`) call
`import_tyndp_libraries(model)` which loads both. 

---

# Example: A Technology Definition

The following example shows the library entry for the predefined combined-cycle gas turbine technology **`Generation.Thermal.Gas.CCGT.Existing`**.

```yaml
Generation.Thermal.Gas.CCGT.Existing:
  attributes:
    - id: name
      value: Generation.Thermal.Gas.CCGT.Existing
    - id: dispatch_type
      value: dispatchable
    - id: energy_conversion_efficiency
      value: 0.58
    - id: variable_operating_cost
      value: 1.6
  relations:
    - id: hasOutputCarrier
      target: carrier.electricity
    - id: hasInputCarrier
      target: carrier.fuel.fossil.gas.natural_gas
```

This entity describes a **technology**, not a physical power plant.

It contains reusable information that is common to many combined-cycle gas turbine units, including:

- operational characteristics (`dispatch_type`);
- default technical parameters (`energy_conversion_efficiency`);
- default economic parameters (`variable_operating_cost`);
- semantic relationships describing the required input carrier and produced output carrier.

Because this information is maintained once in the library, it does not need to be duplicated by every generator that uses this technology.

---

## Example: Using a Technology from the Library

Suppose a project contains a new gas-fired power plant.

Instead of defining the technology from scratch, the generator references an existing library entity:

```python
from cesdm.default_library import GeneratorTypes

gas = model.add_entity("GenerationUnit", "gas.ch.1")
gas.name = "CH CCGT plant"
gas.dispatch.nominal_power_capacity = (3000, "MW")
gas.hasTechnology = GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW
gas.topology.atNode = bus_ch
```

When `hasTechnology` is set, defaults such as `energy_conversion_efficiency` and `variable_operating_cost` are resolved from the library technology if not explicitly set on the asset.

!!! tip "hasTechnology vs copying attributes"
    **Prefer `hasTechnology`** — it keeps shared parameters in one place. Copy attributes manually only when the asset genuinely differs from the library template (site-specific retrofit, custom efficiency study).

### Listing available library references

```python
from cesdm.default_library import Carriers, GeneratorTypes, NaturalResources, StorageTypes

# Enum-style constants for common library entity IDs
Carriers.CARRIER_ELECTRICITY
GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW
NaturalResources.NATURAL_RESOURCE_WIND
```

---

## When not to use the library

- **Site-specific parameters** (exact efficiency after retrofit, actual commissioning date) belong on the asset, not the technology template.
- **Novel technologies** not in the default library require new library entries or explicit attributes on the asset.
- **Project-specific catalogues** — create your own library [YAML](../community/glossary.md#yaml) and `import_library()` alongside the default.

---

## Exporting models that use a library

Library entities live in the in-memory model after `import_library()`, but they
do not need to be fully duplicated in every export. Exports accept:

```python
include_library="referenced"  # default — only library entities reachable from the system model
include_library="none"        # omit library tables; relation ids on assets remain
include_library="all"         # embed every library entity present in the model
```

Supported on `export_frictionless`, `export_yaml`, `export_json`, and
`export_yaml_hierarchical`. See the [EAR API Reference — Frictionless](../reference/api-reference.md#frictionless-data-packages).

---

## Libraries are Ordinary CESDM Models

A library is not a special file format.

It is simply a CESDM model whose purpose is to provide reusable entities.

This means that library entities:

- have identifiers;
- contain attributes;
- contain relations;
- conform to the same schemas;
- can be validated in the same way as any other CESDM model.

The only difference is their intended use: libraries provide reusable reference objects rather than describing a particular physical energy system.

---

## Extending Libraries

Projects are free to create additional libraries.

Examples include:

- company-specific technology catalogues;
- manufacturer equipment libraries;
- national technology databases;
- project-specific reference data.

Multiple libraries can be combined within the same CESDM model, allowing organisations to build their own reusable collections while continuing to use the standard CESDM default library.

---

## Summary

Libraries complement schemas by providing reusable reference entities.

- **Schemas** define the modelling language.
- **Libraries** provide reusable entity instances.
- **System Models** describe a specific physical energy system.

Together they enable consistent, reusable, and maintainable energy-system models.

---

## Next step

→ [Carrier Domains](carrier-domains.md) · [← Proxy API](proxy-api.md)
