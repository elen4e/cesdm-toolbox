# Glossary

Key CESDM terms used throughout the documentation. Link to these entries when a concept is introduced on a page.

For a modeller quick list of classes, see the [cheat sheet](../getting-started/modeller-cheat-sheet.md). For stability tiers, see [Schema Governance](../guides/schema-governance.md).

---

## Analysis
A specific engineering workflow or study performed on an energy system model, such as optimal dispatch, power flow, dynamic simulation, or capacity expansion planning.

---

## Analysis-specific Validation
Validation that checks whether a CESDM model contains all information required for a particular [analysis](#analysis). Unlike [schema validation](#schema-validation), it verifies model completeness rather than structural correctness.

---

## Analysis View
A purpose-specific slice or projection of a [common system model](#common-system-model) for a given [analysis](#analysis) or tool — for example the attributes needed for optimal dispatch.

Not a separate schema class family. Persistable analysis *outcomes* are [Result](#result) entities linked via [`reportsOn`](#reportson); run provenance is a [RunRecord](#runrecord).

---

## Asset
A deployable or operable component of an energy system represented as an [entity](#entity) under `SystemAsset` / `EnergyAssetInstance` — for example a generator, storage unit, transmission branch, demand, or conversion unit.

A [network node](#network-node) is **not** an asset: nodes are topological balance points; assets connect *to* nodes.

---

## Attribute
A named property of an [entity](#entity). Attributes describe the characteristics of an object. Together with [relations](#relation), attributes are one of the three building blocks of the [EAR](#ear) model — see [Core Concepts](../getting-started/core-concepts.md).

---

## Attribute Group
A logical grouping of schema-defined attributes and relations by modelling perspective, such as `dispatch`, `topology`, or `power_flow`. Declared in schema YAML via `belongsToGroup` — see [Schemas — Attribute groups](../getting-started/schemas.md#attribute-groups).

Attribute groups improve the usability of the [Proxy API](#proxy-api) but do not change the underlying semantic model.

---

## Carrier
A physical commodity that can be transported, stored, converted, or consumed within an energy system, for example electricity, natural gas, hydrogen, heat, water, steam, ammonia, or CO₂.

---

## Carrier Domain
A physical transfer domain that transports exactly one [carrier](#carrier).

Typical examples include electrical transmission systems, gas networks, district heating systems, hydrogen pipelines, water systems, and CO₂ transport networks.

[Network nodes](#network-node) **must** belong to exactly one carrier domain via `belongsToCarrierDomain` (schema-required, cardinality 1).

---

## CESDM
The **Common Energy System Domain Model**.

CESDM extends the generic [EAR](#ear) framework with energy-system specific [schemas](#schema), reusable [libraries](#library), analysis support, validation, aggregation, and import/export functionality.

---

## CHP Unit
Concrete [conversion](#conversion-unit) specialisation for the common one-fuel → electricity + heat case, with typed node relations (`atFuelNode`, `atElectricityNode`, `atHeatNode`) and no required [ConversionPort](#conversion-unit) entities.

For arbitrary MxN conversion, use [GenericConversionUnit](#conversion-unit).

---

## Common System Model
The complete CESDM representation of a [physical energy system](#physical-energy-system).

It serves as the single source of truth from which [analysis views](#analysis-view) and [tool-specific models](#tool-specific-model) are derived.

---

## Conversion Unit
Abstract family of [assets](#asset) that convert one or more input carriers into one or more output carriers (`ConversionUnit`).

| Concrete class | Use when |
|----------------|----------|
| `CHPUnit` | Compact 1 fuel → electricity + heat |
| `HeatPumpUnit` | Compact electricity → heat (`coefficient_of_performance`) |
| `ElectrolyserUnit` | Compact electricity → hydrogen |
| `BoilerUnit` | Compact fuel → heat |
| `FuelCellUnit` | Compact hydrogen/fuel → electricity (+ optional heat). Prefer over `GenerationUnit` + FuelCell `GeneratorType` when cross-domain topology is explicit. |
| `GenericConversionUnit` | MxN via `ConversionPort` (arbitrary P2X / multi-port) |

Ports (`ConversionPort`) are the source of truth for carriers and topology on `GenericConversionUnit`. The unit’s `referencePort` relation names which port defines the `flow_coefficient` / `nominal_power_capacity` scale. Cross-domain conversion is never a [transmission](#transmission-element) branch.

---

## Default Library
The standard CESDM [library](#library) containing commonly used reusable entities such as [carriers](#carrier), [technology](#technology) definitions, [natural resources](#natural-resource), and other reference objects.

---

## EAR
The **Entity–Attribute–Relation** modelling framework on which CESDM is built.

Every CESDM model consists of [entities](#entity), [attributes](#attribute), and [relations](#relation). See [Core Concepts](../getting-started/core-concepts.md).

---

## Entity
A uniquely identified **instance** in a CESDM model — a concrete object in your study (e.g. `gen.ch.wind`).

Entities represent physical [assets](#asset), [carriers](#carrier), resources, [profiles](#profile), regions, [technologies](#technology), and many other concepts. Distinguished from [entity class](#entity-class), which defines the *type*.

---

## Entity Class
A [schema](#schema)-defined **type** describing the permitted attributes, relations, inheritance, and validation rules shared by a family of [entities](#entity) (e.g. `GenerationUnit`).

Modellers create **instances** of entity classes; classes are defined in [schemas](#schema) (CESDM core or [extended schemas](../getting-started/schemas-in-depth.md)).

---

## Frictionless Data Package
A tabular exchange format for CESDM models — CSV resources with a `datapackage.json` manifest. Alternative to hierarchical [YAML](#yaml) for spreadsheet-oriented workflows and tabular pipelines.

---

## Generic Interconnector
Capacity-only [transmission](#transmission-element) link (`GenericInterconnector`): NTC / max flow between two [network nodes](#network-node), no line/pipe/converter physics. Carrier is implied by the connected buses and their [carrier domain](#carrier-domain).

Prefer electrical leaves (`TransmissionLine`, `HVDCLink`, `Transformer`) when physical parameters matter.

---

## Hydraulic Storage Unit
A water body used for hydro water balance (`HydraulicStorageUnit`): natural reservoir, pondage, run-of-river reach (`energy_storage_capacity = 0`), or PHS upper/lower basin.

Not a battery-[storage](#asset) subclass. Power conversion is a separate `HydroGenerationUnit` (`hydro_machine_kind`: `turbine` / `pump` / `reversible`) linked via `drawsFromHydraulicStorage` / `dischargesToHydraulicStorage`. Natural inflow uses a single pair: `annual_natural_inflow_energy` + `hasNaturalInflowProfile`.

---

## Library
A reusable collection of CESDM [entity](#entity) instances shared across multiple projects — for example the [default library](#default-library).

Libraries typically contain [technology](#technology) definitions, [carrier](#carrier) definitions, [natural resources](#natural-resource), and other commonly used reference objects. Stored as [YAML](#yaml) like any CESDM model.

---

## Natural Resource
An exogenous resource supplied by nature rather than by another system asset.

Examples include wind, solar irradiation, water inflow, geothermal energy, and biomass resources.

---

## Network Node
Topological connection / balance point within a [carrier domain](#carrier-domain) (`NetworkNode` and typed buses such as `ElectricalBus`, `GasBus`, `HeatBus`).

Every node must set `belongsToCarrierDomain` (required). Explicitly **not** a [SystemAsset](#asset): nodes are the “where”, assets are the “what”. Spatial coordinates are declared on `NetworkNode` and inherited by every typed bus. There is no `WaterBus` — hydro water balance uses [HydraulicStorageUnit](#hydraulic-storage-unit).

---

## Physical Energy System
The real-world energy system represented by a CESDM model.

CESDM models describe the physical system rather than any particular software tool or analysis.

---

## Profile
A metadata [entity](#entity) describing the meaning, interpretation, and storage location of a time series.

The numerical values themselves are stored separately — typically in HDF5 or Parquet — while structure and semantics live in [YAML](#yaml). Linked to assets via [relations](#relation) and tied to a [timestamp series](#timestamp-series).

---

## Profile Type
Defines how the numerical values associated with a [profile](#profile) should be interpreted.

Examples include capacity factors, normalized annual energy distributions, or absolute physical quantities.

---

## Proxy API
An object-oriented programming interface providing typed access to CESDM [entities](#entity).

The Proxy API operates on exactly the same underlying [EAR](#ear) model while improving readability, auto-completion, and type safety. See the [Proxy API guide](../guides/proxy-api.md).

---

## Reference Model
A complete CESDM model used throughout the documentation and tutorials to demonstrate modelling concepts and workflows.

---

## Relation
A typed semantic connection between two [entities](#entity).

Relations describe how objects are connected within the [physical energy system](#physical-energy-system) — for example topology, geography, or classification.

---

## reportsOn
[Relation](#relation) from a [Result](#result) entity to the modelled **subject** whose outcomes it reports — typically an [asset](#asset), or a [network node](#network-node) for node-scoped results (e.g. nodal prices).

Registry targets are `EnergyAssetInstance` and `NetworkNode`; concrete Result classes may narrow further. Formerly named `representsAsset` (import alias retained).

---

## Result
Standalone [entity](#entity) holding outcomes of one [analysis](#analysis) run for one subject (dispatch, power flow, dynamics, …). Linked to that subject via [`reportsOn`](#reportson) and to provenance via [`hasRunRecord`](#runrecord).

Results are not part of the physical identity of an asset; multiple results (different runs/domains) may coexist for the same subject.

---

## RunRecord
Provenance anchor for one analysis run (`DispatchRunRecord`, `PowerFlowRunRecord`, `DynamicRunRecord`, …). Every [Result](#result) points back via `hasRunRecord`. Chained workflows use `hasInputRun` (e.g. dispatch → power flow → dynamics).

Stability differs by subclass — see [Schema Governance](../guides/schema-governance.md#family-keys).

---

## Schema
A [YAML](#yaml) definition specifying [entity classes](#entity-class), [attributes](#attribute), [relations](#relation), inheritance, constraints, and validation rules.

Schemas define the modelling vocabulary; your study model contains [entity instances](#entity). See [Schemas](../getting-started/schemas.md).

---

## Schema Validation
Validation that verifies whether a CESDM model conforms to the [schemas](#schema).

Schema validation checks entity classes, attributes, relations, inheritance rules, constraints, and data types independently of any particular [analysis](#analysis).

---

## Spatial Aggregation
The process of deriving a new CESDM model with reduced geographical resolution while preserving semantic consistency.

The original model remains unchanged.

---

## Technology
A reusable description of the characteristics shared by a class of [assets](#asset) (`EnergyTechnologyType` and concrete types such as `GeneratorType`, `ConverterType`, `StorageType`, `TransmissionType`).

Individual assets reference technology [entities](#entity) via `hasTechnology` instead of duplicating common information — see [Libraries](../guides/libraries.md).

---

## Timestamp Series
Defines the common time axis shared by one or more [profiles](#profile).

---

## Tool-specific Model
A representation of a CESDM model transformed into the format required by a particular software tool.

Tool-specific models are derived from the [common system model](#common-system-model) without redefining the physical system.

---

## Transmission Element
Abstract [asset](#asset) that transports a [carrier](#carrier) between two [network nodes](#network-node) in the **same** [carrier domain](#carrier-domain) (`fromNode` / `toNode`).

Level-2 specialisations:

| Class | Role |
|-------|------|
| `ElectricityTransmission` | Electrical branches: `TransmissionLine`, `Transformer`, `HVDCLink` |
| `GasTransmission` | Gas conveyance (abstract; pipe leaves later) |
| `HeatTransmission` | Heat conveyance (abstract; pipe leaves later) |
| `GenericInterconnector` | Capacity-only transfer (any carrier via the buses) |

Cross-domain conversion uses the [Conversion Unit](#conversion-unit) family, not transmission.

---

## Validation Profile
A [YAML](#yaml) document describing the information required for a particular [analysis](#analysis).

Validation profiles are used by [analysis-specific validation](#analysis-specific-validation). Shipped examples: `analysis_profiles/optimal_dispatch.yaml`, `analysis_profiles/power_flow.yaml`, `analysis_profiles/dynamics.yaml`.

---

## View
Informal term for a purpose-specific presentation of the [common system model](#common-system-model) (analysis slice, export layout, UI). Prefer [analysis view](#analysis-view) in prose.

Do **not** confuse with removed schema classes formerly named `*View` / `*ResultView` — those were replaced by flattened [attribute groups](#attribute-group) on assets and by [Result](#result) entities. See [Legacy names](#legacy-names-do-not-use).

---

## YAML
**YAML** (YAML Ain't Markup Language) is a human-readable, text-based data format used throughout CESDM.

Typical uses:

| Use | Example |
|-----|---------|
| [Schemas](#schema) | Entity classes, attributes, relations under `schemas/cesdm/` |
| [Libraries](#library) | Shared reference entities in `library/default_library/` (carriers, technologies, resources) |
| **Model files** | Hierarchical export of a study scenario |
| [Validation profiles](#validation-profile) | Analysis readiness rules in `analysis_profiles/` |

CESDM models are commonly exchanged as hierarchical YAML together with external profile data (HDF5 or Parquet). YAML keeps structural metadata compact and version-control friendly; bulk time-series values are stored separately.

---

## Ontology map (quick)

```text
Carrier  →  CarrierDomain  →  NetworkNode (typed bus)
                ↑
         TransmissionElement (same domain)
                ↑
EnergyAssetInstance ──atNode / fromNode+toNode──► NetworkNode
       │
       ├── ConversionUnit (cross-domain)
       ├── HydroGenerationUnit ──drawsFromHydraulicStorage──► HydraulicStorageUnit
       (no inverse suppliesResourceTo)
       └── … other assets

Result ──reportsOn──► Asset | NetworkNode
Result ──hasRunRecord──► RunRecord
```

---

## Legacy names (do not use)

Prefer the canonical name in new models. Importers often still accept the legacy id as an alias.

| Legacy | Canonical | Notes |
|--------|-----------|--------|
| `ResultView`, `*ResultView`, `GenerationResultView`, … | `Result`, `GenerationUnit.DispatchResult`, … | Renamed; descriptions cleaned |
| `EnergyBus` | `NetworkNode` / typed bus | Old topology vocabulary |
| `representsAsset` | `reportsOn` | Relation rename; alias on write/import |
| `locatedIn` (CESDM NetworkNode) | `belongsToGeographicalRegion` | Relation rename; alias on write/import/proxy. Unrelated to agent-based `locatedIn` → Municipality. |
| `Interconnector` | `GenericInterconnector` | Capacity-only link; alias |
| `ConversionUnit` (as concrete class) | `GenericConversionUnit` | `ConversionUnit` is abstract; alias maps create → Generic |
| `ReservoirStorageUnit` | `HydraulicStorageUnit` | Water body; alias |
| `drawsFromReservoir` | `drawsFromHydraulicStorage` | Alias |
| `dischargesToReservoir` | `dischargesToHydraulicStorage` | Alias |
| `hasRunOfRiverInflowProfile` | `hasNaturalInflowProfile` | Single inflow on hydraulic storage; alias |
| `Generator.DynamicResult` | `GenerationUnit.DynamicResult` | Class rename |
| `machine_role` | `hydro_machine_kind` | Enum unchanged (`turbine` / `pump` / `reversible`); alias |
| `is_reversible` | *(removed)* | Use `hydro_machine_kind = reversible`; import remaps `true` |
| `is_reference_port` | `GenericConversionUnit.referencePort` | Port flag removed; unit relation is SoT; import remaps |
| `WaterBus` | *(removed)* | Use `HydraulicStorageUnit` + `HydroGenerationUnit` |
| `hasPort`, `hasInitialCondition` | *(removed)* | Orphan registry relations; never on entities |

---

## See also

- [Core Concepts](../getting-started/core-concepts.md) — entities, attributes, relations
- [Modeller cheat sheet](../getting-started/modeller-cheat-sheet.md) — quick patterns
- [Schema Governance](../guides/schema-governance.md) — versioning and stability tiers
