# 1.0.0

- Replaced per-generator `DynamicMachineModel` instances with reusable `DynamicMachineModelType` parameter entities.
- Renamed `DynamicMachineModel.Synchronous` to `DynamicMachineModelType.Synchronous`.
- Replaced `usesDynamicModelType` with `usesDynamicModelType`.
- Moved `rated_apparent_power` and `rated_voltage` to `GenerationUnit`.
- Removed the required inverse model-to-generator relation so one model type can be shared by multiple generators.

## 0.9.0 — Compact CHP asset

- Added `CHPUnit` as a semantic one-fuel/two-output asset with dedicated fuel, electricity, and heat connections.
- Added CHP-specific capacity and efficiency attributes.
- Retained `ConversionUnit` + `ConversionPort` as the generic M×N conversion representation.
- Renamed the running documentation example to **Reference Energy System Model Tutorial**.

## Export fix: schema-only `belongsToGroup`

- `belongsToGroup` remains part of attribute/relation schema definitions.
- Normal YAML/JSON model export no longer writes `belongsToGroup`.
- Hierarchical YAML model export no longer writes `belongsToGroup`.
- Exported model files now contain only entity data: attribute values, units, and relation targets.

# CESDM changelog

This file tracks both the **schema tree** (`schemas/` and
`schemas_agentbased/` — see `schemas/SCHEMA_MANIFEST.yaml` /
`schemas_agentbased/SCHEMA_MANIFEST.yaml`'s `changelog:` field and the
version-compatibility check in
`cesdm.domain.model.hierarchical_yaml.import_yaml_hierarchical`) and
the Python toolbox (`ear/`, `cesdm/`, `tools/`, examples, and
documentation) built on top of it.

Schema versioning follows semver (`MAJOR.MINOR.PATCH`) as defined in
`docs/architecture/schema_governance.md`.

## [Unreleased]

### Added -- Conversion Units demo + tutorial

- Runnable `examples/example_conversion_units.py` (district hub with
  HeatPump / Electrolyser / Boiler / FuelCell / CHP).
- Step-by-step docs under `docs/tutorials/conversion-units/`.

### Changed -- TYNDP / PyPSA prefer ``library/regions_library``

- TYNDP importers map countries to ``region.country.XX`` (import
  ``regions_library`` via ``import_tyndp_libraries``); create only if missing.
- PyPSA importer maps to ``region.country.XX`` / ``region.nuts3.XXXX`` the
  same way; aggregate/explore parsers accept both library and legacy ids.

### Added -- compact ConversionUnit leaves (schema 2.1.0)

- `HeatPumpUnit` (electricity → heat), `ElectrolyserUnit` (electricity → hydrogen),
  `BoilerUnit` (fuel → heat), `FuelCellUnit` (hydrogen/fuel → electricity, optional heat).
- New relations `atHydrogenNode`, `hasHydrogenOutputCarrier`; attribute
  `coefficient_of_performance`.
- `GenericConversionUnit` remains the MxN/`ConversionPort` escape hatch.

### Changed -- BREAKING: `locatedIn` → `belongsToGeographicalRegion` (CESDM)

- Canonical NetworkNode spatial relation is now
  `belongsToGeographicalRegion` (schema **2.0.0**).
- Legacy `locatedIn` remains accepted on write/import/proxy assignment
  (same pattern as `representsAsset` → `reportsOn`).
- Agent-based `locatedIn` → Municipality is unchanged
  (`schemas/agentbased`).

### Changed -- introduction examples consolidated

- Canonical intros: `docs/examples/minimal_electricity_model.py` and
  `docs/examples/reference_energy_system_model.py` (renamed from
  `reference_energy_system_model_core_api.py`).
- Removed overlapping intro scripts: `example_simple.py`,
  `example_in_readme.py`, `example_switzerland_cesdm.py`,
  `examples/reference_energy_system_model.py`, and
  `docs/examples/reference_energy_system_model_proxy_api.py`
  (notebook remains the interactive Proxy walkthrough).

### Changed -- `download_external_data` moved under `tools/`

- Script lives at `tools/download_external_data.py`; console entry point is
  `cesdm-download-data = tools.download_external_data:main`.
- Download/extract paths are anchored to the repository root (not CWD).

### Changed -- FlexECO adapter moved to separate package

- Removed in-house FlexECO bridge from `cesdm-toolbox`
  (`tools/import_flexeco*.py`, `tools/cesdm_*_to_flexeco.py`, related test).
- Use the sibling package **`cesdm-flexeco`** (`export_to_flexeco`,
  `cesdm-yaml-to-flexeco`, …). See `docs/guides/tool-adapters.md`.
- Aggregate tests that assert FlexECO class names skip unless
  `cesdm-flexeco` is installed.

### Changed -- FlexECO demand timeseries exported as negative

- *(Now in `cesdm-flexeco`)* HDF5 export writes profiles linked via
  `DemandUnit.hasDemandProfile` as non-positive series (`-abs(values)`),
  matching FlexEco load convention. CESDM in-memory / native HDF5 shapes
  stay positive.

### Changed -- separate `library/tyndp_library`

- Core catalogue stays in `library/default_library` (`Existing` / `New` /
  `CCS` / `Biofuel`, solar Rooftop/Utility, hydrogen FuelCell/CCGT, …).
- TYNDP vintages (`Old1` / `Old2` / `Present*`, heavy-oil Old*, oil shale)
  moved to `library/tyndp_library` (GeneratorTypes only; carriers remain
  in default).
- TYNDP importers load both via `import_tyndp_libraries()`.
- Default also gained `Oil.HeavyOil.Existing`; oil-shale types are
  TYNDP-only.

### Changed -- BREAKING: GeneratorType taxonomy cleanup

- Nuclear: removed duplicate `Generation.Thermal.Nuclear.Standard`; use
  `Generation.Nuclear.LWR` / `Generation.Nuclear.SMR`.
- Other: renamed `Generation.Adequacy` → `Generation.Other.Adequacy` and
  `Generation.DemandResponse` → `Generation.Other.DemandResponse`.
- Supply proxy: renamed `Supply.Gas` → `Generation.Other.Supply.Gas`
  (still a GeneratorType placeholder; prefer `ExternalSupply` for fuel
  balance when modelling gas networks).
- Solar: removed bare `Generation.Renewable.Solar.PV` (was parallel to
  Rooftop/Utility). Canonical leaves are `…Solar.PV.Rooftop`,
  `…Solar.PV.Utility`, and `…Solar.Thermal` (CSP). Bare `…Solar.PV`
  aliases to `…Solar.PV.Utility`; use Rooftop for prosumers.
- Hydrogen: both conversion paths under `Generation.Hydrogen.*` —
  `FuelCell` (electrochemical) and `CCGT` (thermal combustion; was
  `Generation.Thermal.Hydrogen.CCGT`).
- Gas/Coal vintages: collapsed TYNDP `Old*` / `Present*` into
  `Existing`, keeping `New` / `CCS` / `Biofuel` (and Gas
  `Conventional.Existing`, `CCGT.*`, `OCGT.Existing|New`).
- No runtime technology-id remapping: models and importers must use the
  canonical ids above (legacy `Old*` / `Present*` / bare `Solar.PV` /
  `Thermal.Hydrogen.CCGT` / … are not aliased).

### Changed -- Controller attrs are dynamics-grouped and schema-optional

- All concrete Controller leaf attributes (AVR/GOV/PSS) now
  `belongsToGroup: [dynamics]` and `required: false`.
- Former schema-required controller parameters are enforced by the
  `dynamics` analysis profile instead.

### Changed -- analysis-group attrs are schema-optional

- Set the remaining analysis-grouped attributes that were still
  `required: true` to `required: false`: `ExternalSupply.supply_capacity` /
  `is_slack`, `HVDCLink.max_flow`, and the ten core
  `DynamicMachineModelType.Synchronous` dynamics parameters.
- Study-level requirements moved to analysis profiles:
  `optimal_dispatch` (ExternalSupply + existing HVDC `max_flow`),
  `power_flow` (HVDC `max_flow`), new `dynamics` profile for
  synchronous-machine parameters.

### Changed -- BREAKING: belongsToCarrierDomain required on NetworkNode

- `NetworkNode.belongsToCarrierDomain` is now required (`cardinality: 1`),
  matching the CarrierDomain rule that every bus belongs to exactly one domain.

### Changed -- remove unused catalog attributes

- Dropped 30 orphan attribute definitions that were never declared on any
  entity: legacy HVDC `HVDC_*` / `q_*_from|to` / `firing_angle_min` /
  `reactive_power_absorption_factor`; reservoir volume fields and
  `nominal_head`; old conversion MxN fields (`conversion_rules`,
  `energy_conversion_efficiency_in1_out*`, `nominal_power_capacity_output_*`);
  plus unused `id` and `control_mode`.
- Kept intentional legacy aliases (`machine_role`, `is_reversible`,
  `is_reference_port`, `hvdc_technology_type`, `p_max_hvdc`,
  `has_active_charging`, `has_natural_inflow`).

### Changed -- BREAKING: drop orphan relations hasPort / hasInitialCondition

- Removed unused registry relations `hasPort` and `hasInitialCondition`
  (never declared on any entity; no code references).
- Wired `hasFlowCoefficientProfile` onto `ConversionPort` (optional,
  `belongsToGroup: [dispatch]`) so the catalog entry is no longer orphaned.

### Changed -- BREAKING: referencePort is SoT (drop is_reference_port)

- Removed `ConversionPort.is_reference_port`.
- `GenericConversionUnit.referencePort` is the sole source of truth for
  the flow_coefficient / nominal_power_capacity scale port.
- Import remap: `is_reference_port=true` → unit.`referencePort` (via
  `belongsToUnit`, deferred if the unit link is not yet present).

### Changed -- BREAKING: hydro_machine_kind replaces machine_role / is_reversible

- Renamed `HydroGenerationUnit.machine_role` → `hydro_machine_kind`
  (enum unchanged: `turbine` / `pump` / `reversible`).
- Removed `is_reversible`; pump capability is `hydro_machine_kind = reversible`.
- Import aliases: `machine_role` → `hydro_machine_kind`; `is_reversible=true`
  → `hydro_machine_kind=reversible`.

### Changed -- CHPUnit variable_operating_cost

- Added optional `variable_operating_cost` on `CHPUnit`
  (`belongsToGroup: [dispatch]`), aligned with generation dispatch costs.
  `ConverterType` remains the technology-template default source.

### Changed -- BREAKING: remove WaterBus

- Removed `WaterBus` network-node class. Hydro water balance stays on
  `HydraulicStorageUnit` + `HydroGenerationUnit`; there is no water
  bus/pipe node family yet. `carrier_group: water` remains for labelling.

### Changed -- BREAKING: P1 attribute/relation cleanup

- **Hydro:** dropped `suppliesResourceTo` from `HydraulicStorageUnit`;
  couple only via `drawsFromHydraulicStorage` /
  `dischargesToHydraulicStorage` (machine → basin).
- **`powerflow_bus_type`:** removed from `GenerationUnit`; lives only on
  `ElectricalBus`. Power-flow analysis profile, Kundur/export/import
  tools updated accordingly.
- **`HydroGenerationUnit`:** removed redundant `hasTechnology`
  redeclaration (inherited from `GenerationUnit`).
- **`TransmissionElement.DispatchResult`:** `reportsOn` includes
  `Transformer`.
- **`hasTechnology`:** wired on `ConversionUnit` → `ConverterType` and
  `TransmissionElement` → `TransmissionType`; `StorageUnit.hasTechnology`
  targets `StorageType`.
- **Carrier rule:** documented on Gen/Storage/Demand/External/Transmission;
  optional `hasCarrier` on `DemandUnit` for import overrides.
- **HVDC:** removed duplicate `hvdc_technology_type` / `p_max_hvdc` from
  `HVDCLink`; keep `converter_technology` + `max_flow` (dispatch and
  power_flow). Write aliases remap the legacy attribute ids.

### Changed -- BREAKING: P0 attribute/relation ontology fixes

- **`reportsOn`:** registry targets are now `EnergyAssetInstance` **and**
  `NetworkNode` (node-scoped results were already declared on leaves).
- **`HydraulicStorageUnit`:** removed `hasTechnology`→`StorageType` and
  `storage_technology_type`. Water bodies are not battery-style storage
  templates; hydro tech classification stays on `HydroGenerationUnit` /
  `GeneratorType`.
- **`StorageType`:** dropped PHS/reservoir/inflow fields
  (`has_natural_inflow`, `has_active_charging`) and PHS wording. Default
  library keeps only `Storage.Electrochemical.Battery` (removed
  `Storage.Hydro.*` templates). TYNDP importers no longer attach
  `hasTechnology`→`StorageType` on `HydraulicStorageUnit` or write the
  removed StorageType flags.

### Changed -- schema description cleanup (PATCH)

- Shortened overcrowded entity, attribute, and relation descriptions:
  keep identity + one-line distinction; drop attribute catalogues,
  modelling essays, and duplicated how-to. Longest offenders included
  `ConversionPort`, `EnergyAssetInstance`, `NetworkNode`,
  `HydraulicStorageUnit`, `Profile`, and `powerflow_bus_type`.

### Changed -- BREAKING: slim abstract ConversionUnit

- Removed `variable_operating_cost` and `hasTechnology` from abstract
  `ConversionUnit`. Concrete leaves (`CHPUnit`, `GenericConversionUnit`)
  no longer inherit those slots from the base; add them on a leaf (or
  port) only when needed. `ConverterType` remains in the technology
  library for optional use elsewhere.

### Changed -- BREAKING: EnergyAssetInstance spatial removed; planning → capacity_expansion

- Removed `latitude` / `longitude` / `elevation` and `locatedIn` from
  `EnergyAssetInstance`. Spatial location stays on `NetworkNode` only;
  assets attach via topology (`atNode` / `fromNode`+`toNode`).
- Renamed attribute group `planning` → `capacity_expansion` for the
  lifecycle slots on `EnergyAssetInstance` (`commissioning_year`,
  `commission_date`, `retrofit_date`, `retirement_date`) and for
  `fixed_operating_cost` on `CHPUnit`. Proxy access is now
  `.capacity_expansion` (was `.planning`). Manifest key updated
  accordingly (`capacity_expansion: experimental`).

### Changed -- schema stability keys + glossary (P4)

- **P4a:** `SCHEMA_MANIFEST.yaml` uses finer stability keys for run
  records (`system.run_records.dispatch` stable;
  `system.run_records.power_flow` / `.dynamics` experimental) and marks
  placeholder `transmission.gas` / `transmission.heat` experimental.
  Documented in `docs/guides/schema-governance.md`.
- **P4b:** `docs/community/glossary.md` expanded with ontology terms
  (NetworkNode, HydraulicStorageUnit, Conversion/Transmission families,
  Result / RunRecord / `reportsOn`) and a legacy-name table.

### Changed -- P3a/P3b schema cleanup

- **P3b:** Removed unused abstract `CompositeAsset` and orphan
  `hasComponent` relation for now (typed couplings remain the
  composition pattern).
- **P3c:** `GasTransmission` / `HeatTransmission` stay abstract
  placeholders (no pipe leaves yet); hydro water is not a pipe family.

### Changed -- BREAKING: `ReservoirStorageUnit` → `HydraulicStorageUnit`

Hydro water bodies are named for their role (hydraulic balance point),
not only large reservoirs. RoR uses `energy_storage_capacity = 0` (or
small pondage) on the same class.

- Class: `ReservoirStorageUnit` → `HydraulicStorageUnit` (import alias).
- Relations: `drawsFromReservoir` → `drawsFromHydraulicStorage`,
  `dischargesToReservoir` → `dischargesToHydraulicStorage` (aliases).
- Single inflow profile: `hasNaturalInflowProfile` (+
  `annual_natural_inflow_energy`). Removed `hasRunOfRiverInflowProfile`
  (alias → `hasNaturalInflowProfile`).

### Changed -- BREAKING: ConversionUnit / TransmissionElement hierarchies (P2)

**Conversion**
- `ConversionUnit` is now abstract.
- Concrete leaves: `CHPUnit` (compact 1→2) and `GenericConversionUnit`
  (MxN via `ConversionPort`).
- Legacy concrete class name `ConversionUnit` aliases to
  `GenericConversionUnit` on create/import.
- `hasTechnology` on the family targets `ConverterType`.

**Transmission**
- Level-2 carrier families: `ElectricityTransmission`,
  `GasTransmission`, `HeatTransmission` (abstract; gas/heat leaves TBD).
- Electrical leaves (`TransmissionLine`, `Transformer`, `HVDCLink`)
  parent `ElectricityTransmission` (fromNode/toNode → `ElectricalBus`).
- `Interconnector` renamed to `GenericInterconnector` (capacity-only;
  carrier from connected nodes). Legacy class name aliases on
  create/import.
- Capacity-only vs physics: NTC → `GenericInterconnector`; HVDC with
  converter params → `HVDCLink`.

### Changed -- BREAKING: `representsAsset` → `reportsOn`

Result entities link to their subject via `reportsOn` (registry default
`EnergyAssetInstance`; node-scoped Results still narrow to
`NetworkNode` / typed buses). Proxy attribute and Frictionless column
are `reportsOn`. Import accepts legacy `representsAsset` as an alias
(`CesdmModel.add_relation` + Frictionless column remap). Constant
renamed `_REPRESENTS_ASSET_REL` → `_REPORTS_ON_REL`.

### Changed -- schema naming drift cleanup (P0)

Aligned leftover pre-rename vocabulary with the current Result /
NetworkNode model:

- Relation and RunRecord descriptions: `*ResultView` → `*Result`
  (e.g. `GenerationResultView` → `GenerationUnit.DispatchResult`,
  `NodalPriceResultView` → `NetworkNode.DispatchResult`).
- Asset descriptions: `EnergyBus` → `NetworkNode`
  (`StorageUnit`, `DemandUnit`, `ExternalSupply`).
- **BREAKING (experimental `results.dynamics`):** class rename
  `Generator.DynamicResult` → `GenerationUnit.DynamicResult`
  (proxy `GenerationUnitDynamicResultProxy`). Models that persist the
  old class name need a one-line migration.

### Changed -- NetworkNode spatial parity + `reportsOn` docs (P1)

- Moved `latitude` / `longitude` / `elevation` and spatial-tagged
  `locatedIn` from `ElectricalBus` onto `NetworkNode`, so Gas/Heat/
  Hydrogen/Water buses inherit spatial attributes (docs already claimed
  this; the YAML now matches). Additive / backward-compatible for
  existing ElectricalBus models.
- Clarified Result→subject linking (now `reportsOn`; see BREAKING
  entry above): registry default `EnergyAssetInstance`; node-scoped
  Results override to `NetworkNode` / typed buses.

### Changed -- Frictionless index table `AllAssets` → `AllEntities`

The universal FK index CSV is now `resources/AllEntities.csv`
(resource name `all-entities`, column `entity_class`). Import still
accepts legacy `AllAssets.csv` / `asset_class` / `asset-index`.

### Changed -- export `include_library` flag

`export_frictionless`, `export_yaml`, `export_json`, and
`export_yaml_hierarchical` accept
`include_library="none"|"referenced"|"all"` (default `"referenced"`).
Unused default-/imported-library master data is omitted unless
`include_library="all"`. Library ids are tracked on `import_library` /
`ensure_default_library_entity` and recognized via the generated
default-library registry.

### Changed -- Frictionless export uses a flat `resources/` layout

`export_frictionless()` now writes CSVs as `resources/<Class>.csv`
(plus index tables such as `AllEntities.csv`) instead of role subfolders
`BaseEntities/` / `Assets/` / `Representations/`. Roles remain in
`datapackage.json` (`custom.role`). Import still accepts the older
nested layout.

### Changed -- rename `asset_as` → `get_entity_as`

Typed retrieval is now `model.get_entity_as(entity_id, ProxyClass)`.
`asset_as` was removed (no compatibility alias).

### Fixed -- `Controller.*` attributes unreachable through `validate_for_analysis()`

Found while auditing documentation for staleness after the
representation-views removal, not from a bug report: an analysis
profile checking a genuinely controller-only attribute (e.g.
`AVR_SEXS_Ka` on a generator's linked `Controller.AVR.SEXS`) always
failed with "not a known attribute", even when a correctly linked
controller existed on the asset -- confirmed directly rather than
assumed, with a real `Controller.AVR.SEXS` entity linked via
`hasAutomaticVoltageRegulator`/`controlsGenerationUnit`.

Root cause: `Controller.AVR`/`.GOV`/`.PSS` classes *do* still declare a
schema-level `view_family` (`avr`/`governor`/`pss`), but
`CesdmAnalysisValidationMixin._find_view_family_for_attribute()`/
`_find_existing_view_for_family()` only ever searched entities
discoverable through `_discover_view_map()`, which is keyed on
`representsAsset` -- and controllers are linked via
`controlsGenerationUnit`/`hasAutomaticVoltageRegulator` instead, so
they were structurally invisible to this lookup no matter what. (By
contrast, `Result` entity classes -- the only classes that *do* use
`representsAsset` today -- declare no `view_family` at all any more,
so that half of the mechanism was already correctly a no-op, not
broken.)

Fixed in `cesdm/domain/model/analysis_validation.py` with an explicit
`family -> relation` map (`avr` -> `hasAutomaticVoltageRegulator`,
`governor` -> `hasTurbineGovernor`, `pss` -> `hasPowerSystemStabilizer`),
consulted as a fallback alongside the existing `representsAsset`-based
path -- both auto-detection and the explicit `view_family:` escape
hatch now resolve correctly. 4 new regression tests added to
`tests/test_analysis_validation.py`, covering: auto-resolution,
explicit `view_family`, a generator with no controller attached
(reported as a clear "no such view" error, not a crash), and confirming
`Result`-entity attributes still correctly don't resolve (no
`view_family` there -- unchanged, intentional behaviour, not part of
this fix). Full suite green throughout (349 tests, up from 345).

See `docs/architecture/analysis_validation.md` for the corrected design
description.

### Added -- direct EAR entity accessors documented and FlexECO documentation added

- Documented `Entity.get_attr_value()`, `Entity.get_relation()`, and
  `Entity.get_relations()` in the EAR and proxy API guides.
- Added a dedicated FlexECO importer/exporter page describing the flattened
  direct-asset model.
- Added FlexECO to the MkDocs importer navigation.
- Clarified that importer-specific helpers such as `_av()` and `_rel_target()`
  are no longer required.


### Fixed -- codebase-wide search confirms the `view_family` bug was isolated to two files

After finding the same broken `getattr(cdef, "view_family", None)`
pattern in two separate files (see entry below), searched every
remaining `view_family` reference across the whole codebase --
`cesdm/domain/model/analysis_validation.py` looked like a third
candidate at first glance, but checked directly rather than assumed:
its `_resolve_check_beyond_entity()` hook is only ever reached *after*
the generic EAR-level check already failed to find the attribute
directly on the entity -- so for flattened attributes (the vast
majority now), the generic check succeeds first and this CESDM-specific
`view_family` lookup is never reached at all. Confirmed with a direct
test: `validate_for_analysis()` correctly flags a missing
`variable_operating_cost` (a flattened `GenerationUnit` attribute)
without ever touching this code path. What's left of this mechanism
correctly handles only its actual remaining job -- resolving an
attribute against a linked Result entity, which still legitimately
carries `view_family` -- so no fix needed here.
`tools/import_pandapower.py`/`tools/import_matpower.py` (the reverse,
already-tested import direction) confirmed to have no equivalent
helper function at all, so nothing to check there either.

Full test suite (355 tests) and all 11 examples green throughout.

### Fixed -- `_view_by_asset()`'s flattened-pattern fallback was completely broken

Found while continuing the broader codebase sweep, not from a report:
`tools/export_matpower.py` and `tools/export_pandapower.py` each had
their own copy of a `_view_by_asset()` helper whose fallback for the
flattened pattern depended on `getattr(view_cdef, "view_family",
None)` -- but `view_cdef = model.classes.get(view_class)` is always
`None` now (e.g. `"Generator.PowerFlowView"` isn't a real class any
more), so `family` was always `None` and the entire fallback branch
was silently dead. Every power-flow attribute (voltage setpoints,
active/reactive power setpoints, bus type, thermal ratings, ...) on
every asset class using the flattened pattern was invisible to both
export functions.

Confirmed directly, not assumed: `_view_by_asset(model,
"Generator.PowerFlowView")` on a `GenerationUnit` with
`active_power_setpoint` set returned `{}` before the fix. Fixed the
same way as everywhere else this session: derive the group directly
from `view_class`'s own suffix string ("PowerFlowView" -> "power_flow")
instead of a schema lookup that has nothing left to find. Re-verified
after the fix: the same call now correctly returns the entity: real
end-to-end confirmation, not just the unit-level check -- re-ran
`example_cesdm_to_pandapower_and_matpower.py` and inspected the actual
`.m` output file directly: bus 1's voltage magnitude column now shows
the real configured `1.02`, not a default.

`_single_port_bus()`/`_two_port_buses()` in the same two files had a
similar-looking first loop searching the same removed view classes,
but were *not* actually broken -- their flattened-pattern fallback
derives the group from a direct `belongsToGroup` check on the
`atNode`/`fromNode`/`toNode` relation definitions themselves, not a
schema `view_family` lookup, so it already worked correctly. Cleaned
up the dead first loop in both anyway, for clarity, since it could
never find anything.

`tools/import_pypsa.py` and `tools/import_pandapower.py`'s docstrings/
comments (describing separate view entities as the current CESDM
structure) also updated to match, continuing the same sweep as the
previous entry.

Full test suite (355 tests) and all 11 examples green throughout.

### Fixed -- hydrogen misclassified as water, losing its carrier and cost on FlexECO export

Reported directly: hydrogen as a carrier, and its cost, were not
showing up in FlexECO exports. Root cause confirmed concretely, not
assumed: `_carrier_for_type()` (`examples/example_import_tyndp.py`)
checked `"hydro" in tech_name.lower()` before ever checking for
"hydrogen" -- and "hydrogen" contains "hydro" as its first five
characters, so every hydrogen technology (`Hydrogen CCGT`, `Hydrogen
Fuel Cell`) matched the water branch instead and got
`hasInputResource=resource.water` wired up, never
`hasInputCarrier=carrier.hydrogen` at all. By the time
`export_to_flexeco()` (`tools/import_flexeco.py`) ran, there was
nothing hydrogen-specific left on the generator to export -- fixing
the export function itself would have found nothing wrong, since it
correctly reads whatever `hasInputCarrier` relation actually exists.

Fixed with a dedicated `"hydrogen" in t` check before the `"hydro"`
substring check in `_carrier_for_type()`. The exact same bug, with the
exact same root cause, found and fixed the same way in
`tools/import_flexeco.py`'s own FlexECO->CESDM import pre-pass (a
list of `(keyword, carrier_id)` pairs checked in order with a `break`
on first match -- `"hydro"` appeared before `"hydrogen"` in the list,
so the later, correct entry could never be reached; reordered rather
than deduplicating the check). `example_import_tyndp_proxy_api.py`
already had a local wrapper working around this exact bug without
editing the legacy file (confirmed via its own docstring, which
independently describes the identical root cause) -- fixed directly
in `example_import_tyndp.py` itself instead this time, since it's a
genuine bug, not a legacy convention worth preserving untouched.

Verified end to end, not just at the unit level: built a hydrogen
generator through the real `example_import_tyndp.py` construction
path (`_ensure_generator_type` -> `_carrier_for_type` ->
`_ensure_carrier`), exported it through the real `export_to_flexeco()`,
and confirmed the resulting FlexECO JSON element carries
`"carrier": "carrier.hydrogen"` directly.

**Separate finding, not a code bug, left for a decision**: the default
library's `carrier.hydrogen` entry (`library/default_library/carriers/
EnergyCarrier.yaml`) has `energy_carrier_cost: 0.0` -- a placeholder,
not a researched market value (unlike e.g. biomass's 67.68 in the same
file, which I'd initially and incorrectly attributed to hydrogen
before checking the YAML directly). Now that the carrier link itself
exports correctly, this 0.0 will show up as the exported cost too,
correctly reflecting what the library actually says -- flagged rather
than silently "fixed" with an invented number, since a real hydrogen
price is a data/research decision, not a code one.

Full test suite (355 tests) and all 11 examples green throughout.

### Fixed -- broader codebase sweep for remaining stale view-architecture references

A final, whole-codebase grep (not scoped to any single request) found
many more files than expected still mentioning the removed view
classes. Most turned out to be stale comments/docstrings only --
confirmed directly rather than assumed, e.g. `_discover_view_classes()`
now correctly returns only Result entities (which still legitimately
use the representsAsset pattern this whole mechanism is built around),
so `discovery.py`'s `_build_view_index()`, `csv.py`'s prefix-based wide
CSV column classification, and `statistics.py`'s `get_view()` calls
are all still working, correct, schema-driven code -- just with
misleading docstring examples, now fixed to match. One further piece
of genuine dead code removed along the way: `cesdm/domain/model/
builders.py`'s `_view_id()` method (confirmed nothing calls it) and its
9-entry hardcoded class-name-to-prefix mapping (which itself
documented, in a comment, an earlier copy-paste bug this session had
already fixed elsewhere).

One genuine functional regression found and fixed, not just a stale
comment: `tools/generate_cesdm_schema_html.py`'s `_REPR_ROOTS` set
(used to categorize classes as "asset"/"representation"/"network"/
"domain" for the HTML schema reference) listed only removed class
names, and its `"View" in name` fallback could never match either
(current class names contain "Result", not "View") -- so the entire
"representation" category had gone silently unreachable, misfiling
every Result entity into the "domain" catch-all in the generated
documentation. Confirmed directly: regenerated `docs/reference/
schema_reference.html` before and after -- "representation" appeared
0 times in the old output, 48 times after adding `"Result"` (the
current shared abstract root) to the set. AVR/GOV/PSS controllers
deliberately left in "domain" rather than added to "representation" --
they link via `controlsGenerationUnit`, not `representsAsset`, so they
were never part of the pattern this category is defined around.

Full test suite (355 tests) and all 11 examples green throughout.
Remaining files from the same sweep (`tools/import_pypsa.py`,
`tools/import_flexeco.py`, `tools/aggregate_cesdm_yaml_subset.py`,
`tools/export_matpower.py`/`export_pandapower.py`/
`import_pandapower.py`, and several `docs/guide/*.md` files) not yet
checked -- continuing in a follow-up.

### Fixed -- `README_TYNDP_IMPORT_LOGIC.md`/`README_PYPSA_IMPORT_LOGIC.md`, the item flagged above closed

The previous entry flagged these two companion docs as stale but out
of scope for that specific request. Closed directly rather than left
open: both described separate `SinglePort.TopologyView`/
`TwoPort.TopologyView`/`Generation.DispatchView`/`Storage.DispatchView`/
`Demand.DispatchView`/`Interconnector.PowerFlowView` entities as the
current CESDM structure a PyPSA/TYNDP asset maps to -- none of which
exist any more. Every diagram and numbered-step description rewritten
to show topology/dispatch/power-flow attributes and relations held
directly on the one asset entity instead. A broken, run-on intro
sentence in `README_TYNDP_IMPORT_LOGIC.md` (two unrelated clauses
merged mid-thought, likely from an earlier edit) fixed along the way.

Full test suite (355 tests) and `mkdocs build --strict` green throughout.

### Fixed -- `examples/example_import_tyndp.py` fully repaired, requested directly

Asked directly to update this file. Found it was completely broken
against the current schema -- built entirely on the pre-flattening
architecture (separate `SinglePort.TopologyView`/`TwoPort.TopologyView`/
`Generation.DispatchView`/`HydroGenerationUnit.DispatchView`/
`Storage.DispatchView`/`Demand.DispatchView`/`Interconnector.
PowerFlowView` entities), none of which exist in the schema any more.
Confirmed this file is "legacy" (a comment in `test_tyndp_full_pipeline.py`
already calls it that) but still load-bearing: `example_import_tyndp_
proxy_api.py` imports its pure classification/helper functions
directly (`_generation_asset_class_for_type`, `_carrier_for_type`,
`_slug`, `TECH_HIERARCHY`, `TYNDP_TECH_DATA`, and 10 others) -- checked
which functions were actually shared before touching anything, so
those signatures/behavior were preserved exactly while the entity-
creation logic around them was fixed.

- Four entity-creation helpers (`_ensure_nodal_view`,
  `_ensure_storage_dispatch_view`, `_ensure_demand_dispatch_view`,
  `_ensure_hydro_reservoir_composite`) rewritten to write directly onto
  the asset (the flattened pattern), instead of creating a separate,
  now-nonexistent view entity. `_ensure_generation_dispatch_view`
  already had a working `hasattr(model, "ensure_dispatch_view")`
  fallback to the modern path -- confirmed this was the one always
  taken with a real `CesdmModel`, dead legacy code beneath it removed.
- Two more copy-paste bugs found, the same pattern as the ones already
  fixed in `tools/import_pypsa.py` earlier this session: a dict with 8
  identical `"GenerationUnit"` keys, and two set literals with the
  same string repeated 3-4 times (harmless via set deduplication, but
  clearly meant to list distinct classes originally).
- Every remaining `model.get_attr_value("<OldViewClass>", ...)` call
  (the old class-name-plus-entity-id API) updated to
  `model.get_attribute_value(entity_id, ...)`, since every view id
  variable involved is now just the asset's own id.
- ~15 docstring/comment sections describing the old architecture as
  current updated to match.

Verified end to end with real data, not just unit-level: ran this
file's own `build_cesdm_model_from_tyndp_installed_capacities()`
against the same `examples/sample_data/tyndp_sample_*.csv` fixtures
`test_tyndp_full_pipeline.py` already uses for the proxy-api version
-- "Model validated successfully", and the resulting hierarchical YAML
inspected directly to confirm dispatch/power-flow attributes and
relations landed on the assets themselves with the correct
`belongsToGroup` tags, not lost silently the way a str-typed
"succeeded" message alone wouldn't have caught.

Not yet done, flagged rather than fixed: `README_TYNDP_IMPORT_LOGIC.md`
and `README_PYPSA_IMPORT_LOGIC.md` (companion docs describing this
file's and `tools/import_pypsa.py`'s internals) reference the same
removed view classes extensively and are now stale in the same way
the example companion docs were before an earlier response's refresh
-- out of scope for this specific request, called out for a follow-up
rather than silently left inconsistent.

Full test suite (355 tests) and all 11 examples green throughout.

### Fixed -- test-suite relevance review completed across all 36 files

An earlier response left this review not fully exhaustive, with
`test_hvdc_schema.py` flagged as a redundancy candidate but not acted
on. Finished the review properly this time -- checked every remaining
file's actual content, not just its docstring, and resolved the two
genuine findings differently based on what each one actually needed:

- **`test_hvdc_schema.py`**: rather than deleting it, checked whether
  it covered anything genuinely unique first -- it was the *only*
  test touching `converter_technology` at all, but only checked that
  the attribute could be set, missing HVDCLink's actual distinguishing
  schema features entirely: `converter_technology` is a real enum
  (`LCC`/`VSC`), and `hvdc_technology_type`/`p_max_hvdc` (power_flow
  group)/`max_flow` (dispatch group) are `required: true` fields never
  exercised by any test anywhere. Expanded from 1 trivial test to 4
  meaningful ones (enum rejection, conditional-requiredness
  enforcement, flattened-group read/write) instead of just removing
  it.
- **`test_tyndp_hydro_dispatch_efficiency.py`**: by contrast, checked
  first whether `turbine_efficiency` was already covered elsewhere --
  it was, in three other files, each exercising it as part of a
  realistic PHS/hydro import scenario rather than this file's isolated
  "can this attribute be set" check, which is trivially true for any
  schema attribute and specific to nothing about hydro dispatch or
  efficiency at all. Removed entirely rather than kept as pure
  duplication.
- **`test_model_summary.py`**: one assertion (`not any("DispatchView"
  in k or "TopologyView" in k for k in counts)`) had gone vacuous --
  those classes don't exist at all any more, so the check could never
  fail regardless of whether `summary()` actually excludes anything.
  Updated to exercise the currently-real exclusion instead: standalone
  `Controller.*`/`Result`/`RunRecord` entities (this session's
  replacement for the old view-role concept) confirmed absent from the
  asset counts.

Every other remaining file (`test_pypsa_reservoir_no_own_topology_view.py`,
`test_rdf_export.py`, `test_powerflow_snapshot_vs_timeseries.py`, plus
seven smaller schema-governance regression-guard files) checked and
confirmed still accurate and meaningful -- no further changes needed.

Full test suite (355 tests, net -1 after removing the one purely
duplicate file and adding three more meaningful ones elsewhere) and
all 11 examples green throughout.

### Fixed -- example companion docs fully refreshed, an outstanding item finally closed

An earlier response flagged two companion walkthrough docs
(`README_SIMPLE_EXAMPLE.md`, `README_HYDRO_RESERVOIR_EXAMPLE.md`) as
"more broadly stale than just a rename... a fuller refresh still
owed" and left it there. Continued that work directly rather than
letting it sit: a full inventory found **14** such docs in
`examples/`, not 2 -- seven more (`README_ANALYSIS_VALIDATION_EXAMPLE.md`,
`README_CH_NEIGHBOURS_TUTORIAL.md`, `README_IN_README_EXAMPLE.md`,
`README_KUNDUR_TWO_AREA_EXAMPLE.md`, `README_MULTIENERGY_EXAMPLE.md`,
`README_POWERFLOW_EXPORT_EXAMPLE.md`, `README_SCHEMA_EXTENSION_
EXAMPLE.md`) also referenced multiple entirely-removed builder
functions (`add_generator`, `add_bus`, `add_gas_bus`/`add_heat_bus`,
`create_generation_unit`/`create_demand_unit`/
`create_transmission_line`, `add_reservoir_hydro`/
`add_phs_closed_loop`, `add_generator_dynamic_view_subtransient`/
`add_controller_view_avr_sexs`, and non-existent `.avr`/`.governor`/
`.pss` proxy shortcuts on the generator itself -- controllers are
separate entities linked via `controlsGenerationUnit`, never a
property shortcut at all, at any point this session). All nine
rewritten in full against each doc's actual, current corresponding
`.py` file -- every code snippet and every documented output/error
message extracted and actually run, not written by inspection.

Three genuine bugs in the example `.py` files themselves, found only
by reading them closely enough to write accurate documentation, fixed
alongside:
- `example_analysis_validation.py` imported and called the internal
  `cesdm.proxy._entity_proxy()` helper directly instead of the public
  `model.get_entity()` — unidiomatic in example code meant to
  demonstrate the public API.
- `example_multienergy.py`'s and `example_schema_extension.py`'s own
  docstrings/comments still described `Demand.DispatchView`/
  `Generation.DispatchView`/`Conversion.DispatchView` as the current
  architecture, and implied other classes have "dedicated builders"
  that new ones lack -- misleading since no class has one any more.
  `README_EAR_GENERIC_DOMAIN_EXAMPLE.md` similarly still claimed "no
  proxy API applies here at all," true before the EAR/CESDM
  `EntityProxy` split (see above) but only partially true since --
  missing the walkthrough step for the generic-`EntityProxy`
  demonstration this session had already added to the `.py` file
  itself, added now.

Two test-helper functions (`test_analysis_validation.py`'s
`_add_generator`/`_add_transmission_line`,
`test_technology_default_cascade.py`'s `_add_gas_generator`)
simplified to use `add_entity()`'s new return value directly, instead
of a separate `get_entity()` call afterward.

Full test suite (353 tests) and all 11 examples green throughout.

### Changed -- `CesdmModel.add_entity()` now returns a typed proxy directly

Asked directly, repeatedly, why `get_entity()` couldn't just "know"
the right type automatically -- confirmed structurally impossible for
`get_entity()` itself (no class-name literal at its call site for a
type checker to infer from), then asked the natural follow-up: what if
`add_entity()` did this instead, since its `entity_class` argument
*is* a literal at the call site?

Previously dismissed for breaking `test_ear_entity_object_api.py`'s
existing, deliberately-tested contract (`add_entity()` returning the
bare `ear.entity.Entity` dataclass). Revisited: that test file's own
docstring already says it covers "phase 1" of the object-oriented API
work specifically, listing "the flat-plus-alias proxy API" as a
separate, later phase not covered by it -- which has since landed.
Adjusting that one contract, now that later phase exists, is
squarely within what the test file itself anticipated, not a
casual override of settled behaviour.

`CesdmModel.add_entity()` (overriding `ear.model.Model.add_entity()`,
which stays exactly as it was -- a plain EAR domain has no proxy
registry to wrap with at all) now creates the entity via the EAR
primitive underneath, then returns it wrapped in its schema-specific
typed proxy directly:

```python
gen = model.add_entity("GenerationUnit", "gen1")
gen.dispatch.nominal_power_capacity = 800   # type-checks immediately
gen.nominal_power_capacity = 800            # flat access, also type-checks
```

`tools/generate_typings.py`'s `render_model_stub()` gained one
`@overload` + `Literal["<ClassName>"]` declaration per concrete schema
class for `add_entity()`, so Pyright infers the specific proxy type
directly from the class-name string literal -- confirmed directly
with Pyright (`reveal_type` showing `GenerationUnitProxy`,
`ElectricalBusProxy`, etc.; a deliberate typo on a group attribute
correctly flagged), the same technique verified earlier for a
proposed (and, in the end, unnecessary) separate `create_entity()`
method -- no new method needed after all, `add_entity()` itself now
does this.

`tests/test_ear_entity_object_api.py`'s first test rewritten to check
the new `CesdmModel` behavior, plus a new test added confirming the
plain `ear.model.Model.add_entity()` underneath is completely
unaffected and still returns the bare `Entity` dataclass. Two other
tests in the same file (checking stored attribute/relation data)
updated from `entity.data[...]` to `model.entity_data(entity)[...]`,
since `EntityProxy` (a `str` subclass) has no `.data` field the way
`Entity` does.

Full test suite (353 tests) and all 11 examples green throughout.

### Changed -- `EntityProxy` split across the EAR/CESDM layer boundary

Asked directly whether the proxy really belonged in CESDM at all, or
whether it was mostly generic EAR functionality misplaced in the
domain-specific package -- checked each method's actual implementation
rather than assuming its file location already reflected its true
generality, the same way the earlier `AssetProxy` -> `EntityProxy`
rename was decided.

**Ten methods moved from `cesdm/domain/model/accessors.py` to a new
`ear/model/accessors.py`** (`entity_class`, `entity_data`, `has_entity`,
`class_attributes`, `class_relations`, `field_allowed`,
`get_attribute_value`, `get_relation_targets`,
`set_attribute_if_allowed`, `add_relation_if_allowed`): every one of
them, checked directly, needs nothing beyond core EAR concepts
(`_canonicalize_class()`, `_collect_inherited_fields()`, `self.classes`)
-- none reference `belongsToGroup`, technology-template cascades, or
any other CESDM domain concept. `add_relation_if_allowed()`'s one
CESDM-aware line (`ensure_default_library_entity`) was already an
optional, gracefully-degrading hook (`getattr(self, ..., None)`), so it
needed no change to move. Composed into `ear.model.Model` right after
`EntityOpsMixin`; `CesdmModel`'s own (now much smaller)
`AccessorsMixin` keeps only what's genuinely CESDM-specific
(`get_effective_attribute_value`'s technology-template cascade,
`views_for_asset`/`get_view`/`get_dispatch_view`/`get_topology_view`/
`get_powerflow_view`'s group resolution, `reservoir_for_hydro`/
`hydro_units_for_reservoir`'s hydro-domain pairing). No MRO conflict
from the two same-named `AccessorsMixin` classes living in different
modules -- confirmed directly, not assumed.

**A new, generic `ear.entity_proxy.EntityProxy`** (the str-subclass
wrapper itself: `__new__`, `.id`/`.entity_class` properties, generic
`__setattr__`/`__getattr__` built on the ten moved methods above,
`.add_attribute()`/`.add_relation()`) now underlies
`cesdm.proxy.EntityProxy`, which extends it with the CESDM-specific
behaviour that a generic EAR domain can't provide: `.dispatch`/
`.power_flow`/etc. group resolution (`_view()`), `.connect(...)`, and
-- found while doing the split, not before -- two behaviours the
generic base's `__getattr__` deliberately does *not* replicate:
reading a `belongsToGroup`-tagged attribute resolving the technology-
template/lazy-default cascade, and reading a relation wrapping its
target in a typed per-class proxy (e.g. `bus.locatedIn` returning a
`GeographicalRegionProxy`, not a plain string) -- a non-CESDM EAR
domain may have no per-class proxy registry to wrap with at all, so
the generic base intentionally returns plain target ids instead.
`__setattr__` needed no override at all: checked directly that its
logic (check relations, check attributes, delegate to
`set_attribute_if_allowed`/`add_relation_if_allowed`) was already 100%
generic, with nothing CESDM-specific baked in.

Demonstrated directly, not just asserted: `ear.entity_proxy.EntityProxy`
wrapping a genuinely non-energy entity (`Household` from
`schemas_agentbased/`, no relation to CESDM at all) works identically
-- direct attribute assignment, `.add_attribute()`, correct
`entity_class`. `examples/example_ear_generic_domain.py` updated to
show this (its docstring previously claimed no proxy API applied to a
generic EAR schema at all, which was true before this split and is
only partially true now -- `cesdm.proxy`'s domain-specific parts still
don't apply, but the generic base now does).

`tools/generate_typings.py`'s `MIXIN_SOURCES` updated to scan the new
`ear/model/accessors.py` file too (one test caught the ten moved
methods missing from the generated stub immediately).

Full test suite (351 tests) and all 11 examples green throughout.

### Changed -- `AssetProxy` renamed to `EntityProxy`, gained `add_attribute()`/`add_relation()`

Asked directly whether the class was genuinely asset-specific or
really a generic entity wrapper -- checked rather than assumed:
nothing in its logic (`entity_class()`, `class_attributes()`,
`class_relations()` lookups) is asset-role-specific at all, and the
internal helper that constructs one was already named
`_entity_proxy()`, not `_asset_proxy()` -- the class name was the odd
one out in its own surrounding naming. `model.get_entity("Electricity")`
for an `EnergyCarrier` (not an asset-role class at all) already worked
identically, confirming the mismatch.

Also requested directly: `get_entity()` should return something
exposing `add_attribute()`/`add_relation()` as explicit, chainable
method calls -- the same object-oriented convenience `ear.entity.
Entity.add_attribute()`/`.add_relation()` already offer on the object
`model.add_entity()` itself returns, not just implicit
`entity.name = "X"` assignment. Added, delegating to
`model.add_attribute()`/`model.add_relation()` and returning `self`:

```python
gen = model.get_entity("gen1")
gen.add_attribute("name", "Turbine 1").add_relation("atNode", bus)
```

Renamed everywhere: the class definition and its docstring in
`cesdm/proxy.py` (also fixed there: a stale `.powerflow` mention,
"asset/view split" framing describing the old architecture, and a
reference to the removed generated `add_<EntityClass>()` builders),
`cesdm/domain/model/builders.py`, `ear/entity_class.py` (plus a stale
`.powerflow` mention found alongside it), `ear/model/entity_ops.py`,
`cesdm/domain/model/analysis_validation.py`, both generator scripts
(`tools/generate_convenience_api.py`, `tools/generate_typings.py` --
the latter's `render_proxy_base_stub()` also updated to declare the
two new methods in the type stub, with the `typing.Any` import that
needed), all `.pyi`/generated files (regenerated from source, not
hand-edited), every example, and every test file -- including four
docstring-only mentions initially missed on the first pass and caught
by a follow-up, more exhaustive grep rather than assuming the first
pass was complete. `SystemAssetProxy`/`CompositeAssetProxy`/
`EnergyAssetInstanceProxy` (named after the schema classes `SystemAsset`/
`CompositeAsset`/`EnergyAssetInstance`, which do legitimately have
"Asset" in their own name) correctly left alone -- confirmed these are
real per-class proxy names, not leftover base-class references, before
excluding them from the rename.

`docs/architecture/proxy_api.md` rewritten in full -- it still
described `add_generator()`/`add_bus()`/`create_demand_unit()` as
active builder examples (all removed earlier this session),
`add_geographical_region()` (also removed), and `.avr`/`.governor`/
`.pss` as view-family properties (never true even before this
session's changes; controllers are separate entities linked via
`controlsGenerationUnit`). Every code example and every documented
error message in the rewrite extracted and actually run, not just
written by inspection.

Full test suite (351 tests) and all 11 examples green throughout.


Asked directly whether all `test*.py` files still make sense in the
new structure -- systematically checked, not assumed clean just
because the suite passes green (a stale docstring or dead-but-inert
lookup table doesn't fail any test, so "all green" alone doesn't mean
"nothing is misleading"). Two genuine findings, both fixed:

- **`test_flat_proxy_and_namespace_alias.py`**: a docstring described
  the dynamic-machine-model flattening as "reverted rather than
  shipped" -- true of the *first* attempt (naive flattening, which
  really was reverted), but this session later found and shipped a
  working approach (lazy default resolution) after the user pushed
  back on accepting that revert as final. The docstring never got
  updated to say so, leaving it actively wrong about the current
  state, not just outdated. Rewritten to describe both attempts and
  which one actually shipped.
- **`tools/generate_typings.py`'s `RETURN_OVERRIDES` dict**: 20 of its
  28 entries mapped functions that no longer exist at all
  (`add_bus`/`add_generator`/`create_generation_unit`/etc., all removed
  from `builders.py`) -- harmless at runtime (a dict lookup that never
  matches is simply inert), but exactly the kind of clutter "keep
  `builders.py` minimal" should extend to its supporting tooling too.
  Cleaned down to the 9 entries for functions that still exist, and a
  stale `"asset": "AssetProxy"` entry (missed during the earlier
  `asset()` -> `get_entity()` rename) corrected alongside it.
  `tests/test_generate_typings.py`'s matching comment block, which
  described two tests for a tuple-return-type bug, updated to note
  those two tests were removed along with the functions they covered
  rather than kept as dead assertions.

Also specifically verified, not just assumed, that a test's *content*
was still meaningful where its subject could plausibly have become
vacuous after this session's architecture changes:
`test_only_structural_relations_are_ever_ambiguous_across_the_whole_
schema` (in `test_analysis_validation.py`) still iterates real
candidates from `_discover_view_map()`, since `Result`/`DispatchResult`/
`PowerFlowResult`/`DynamicResult` still carry `view_family` for the
analysis-profile escape hatch -- confirmed directly
(`model._discover_view_map()["GenerationUnit"]` returns real Result
classes, not an empty list) rather than assumed correct from the test
passing alone.

Every other file checked (`test_hvdc_schema.py` flagged as a candidate
for removal/merging -- thin, and redundant with the many other tests
that also exercise basic entity creation, but not incorrect) is either
unaffected by this session's changes or already covered by the
functional rewrites described above. Full review not yet exhaustive
across all 37 files; continuing in a follow-up pass.

Full test suite (351 tests) and all 11 examples green throughout.

### Changed -- BREAKING: `builders.py` kept minimal, `generated_builders.py` removed entirely

Requested directly. `cesdm/domain/model/builders.py` shrunk from 759 to
309 lines -- every per-asset-type domain convenience wrapper
(`add_generator`, `add_bus`, `create_generation_unit`,
`add_wind_generator`/`add_solar_generator`/`add_thermal_generator`/
`add_nuclear_generator`/`add_hydro_generator`, `create_storage_unit`,
`add_reservoir_storage`/`add_reservoir_hydro`/`add_phs_closed_loop`/
`add_phs_open_loop`/`add_run_of_river`, `create_demand_unit`,
`create_transmission_line`/`create_hvdc_link`,
`create_timestamp_series`/`create_profile`,
`create_generation_unit_from_technology`, and the technology-
classification helpers that only existed to support it) removed
entirely. Kept: `get_entity`/`asset_as` (proxy wrapping),
`ensure_entity`/`ensure_carrier`/`ensure_resource`/`ensure_technology`/
`set_technology` (generic, class-agnostic construction), the flattened-
view mechanism (`ensure_view`/`dispatch_view_class_for_asset`/
`ensure_dispatch_view`), `connect_single_port`/`connect_two_port`, and
`attach_profile` and its four thin wrappers. `attach_profile()`'s
internal call to the now-removed `create_profile()` inlined directly
using `ensure_entity()`/`add_relation_if_allowed()` instead.

`cesdm/domain/model/generated_builders.py` (`GeneratedBuildersMixin`,
one auto-generated `add_<EntityClass>()` constructor per concrete
schema class) deleted outright, removed from `CesdmModel`'s
composition in `core.py`. Building any model now uses core EAR calls
(`add_entity`/`add_attribute`/`add_relation`) plus the object-oriented
proxy layer for reading/writing afterward -- see
docs/getting_started.md.

**`cesdm/generated_proxies.py` is unaffected and still generated** --
a separate, still-necessary mechanism (the per-class `AssetProxy`
subclasses `.dispatch`/`.power_flow`/etc. type-check against, and what
`get_entity()` wraps an entity id in), not to be confused with the
removed constructor layer. `tools/generate_convenience_api.py`
rewritten to only generate this half; the add_<entity>() generation
code (`render()`, `render_method()`, `HEADER`, `entity_class_to_snake()`,
`is_many_relation()`, `relation_input_annotation()`,
`unique_parameters()`, and the `DEFAULT_LIBRARY_IDS_BY_CLASS`/`keyword`
imports they alone needed) removed from that file entirely.
`tools/update_generated.py` and `tools/generate_typings.py` updated to
match (the latter had a dead code path scanning the now-nonexistent
`generated_builders.py` for return-type imports, removed rather than
left to silently no-op).

#### Test suite

Every one of the ~300 call sites across the test suite using a removed
function was individually triaged, not blanket-deleted: rewritten to
raw EAR calls where the test's actual subject was something else
(fixture setup only), or removed entirely where the removed function
*was* the test's subject and no longer exists to test at all --
`test_schema_convenience_api.py`, `test_generation_technology_routing.py`
(`create_generation_unit_from_technology`'s own routing bugs),
`test_generated_builder_default_optionality.py`,
`test_builders_return_types.py` deleted outright; two tests inside
`test_generate_typings.py` (tuple-returning composite builder stub
types) removed the same way. `test_proxy_api.py` rewritten in full.

Two genuine bugs caught by this process, not shipped:
- `test_technology_default_cascade.py`'s "no library loaded" case
  needs `set_technology()` specifically (ensures a bare `GeneratorType`
  stub exists) -- a raw `add_relation("hasTechnology", ...)` assumes
  the target already exists, which a removed builder used to guarantee
  silently.
- The README quickstart Pyright test needed `asset_as(id,
  GenerationUnitProxy)`, not `get_entity(id)`, for `.dispatch` to
  type-check -- `get_entity()`'s own docstring already says as much
  (statically typed as plain `AssetProxy`), caught by actually running
  Pyright against the snippet rather than assuming it would resolve.

Full test suite (351 tests, up from 386 before this change once the
now-untestable ones were removed) and all 11 examples green throughout.


Requested directly. Fits the existing `entity_class()`/`entity_data()`/
`has_entity()` naming family better than `asset()` did (this method
wraps *any* entity id in a typed proxy, not only asset-role classes --
e.g. `model.get_entity("Electricity")` for an `EnergyCarrier`, used
throughout the examples). `asset_as(entity_id, cls)` (the statically-
typed variant) keeps its own name -- only the plain, dynamically-typed
wrapper was renamed -- with its docstring's cross-reference updated to
match.

Renamed everywhere it was called as `.asset(` -- ~110 call sites across
9 example files, 7 test files, `cesdm/domain/model/builders.py`'s own
internal use inside `asset_as()`, the auto-generated
`typings/cesdm/domain/model/core.pyi` stub (regenerated from source,
confirmed rather than hand-edited), `README.md`, `docs/architecture/
proxy_api.md`, and two example companion walkthrough docs
(`examples/README_SIMPLE_EXAMPLE.md`, `examples/README_
HYDRO_RESERVOIR_EXAMPLE.md`) that turned out to be more broadly stale
than just this rename -- both still referenced `add_gas_bus()`/
`add_heat_bus()`, builder calls already removed from the actual
example `.py` files earlier this session. Only the mechanical rename
was applied to these two; a fuller refresh to match the current
example code is still owed.

Full test suite (385 tests) and all 11 examples green.

### Changed -- group names renamed to snake_case for consistency

Requested directly: `powerflow` -> `power_flow`, `dynamic` -> `dynamics`
(matching the rest of the codebase's snake_case convention --
attribute ids like `nominal_power_capacity` never used a bare
compound word). `dispatch`/`topology`/`spatial`/`planning`/`technical`
unchanged.

Renamed everywhere the old names appeared as actual group-name
strings (not just illustrative examples in comments, which were also
fixed for accuracy): all 8 schema files carrying `belongsToGroup:
[powerflow]`, `GenerationUnit.yaml`'s `belongsToGroup: [dynamic]`
tags, `cesdm/proxy.py`'s `_KNOWN_GROUPS`, `cesdm/domain/model/
builders.py`'s and `accessors.py`'s suffix-to-group mappings,
`tools/aggregate_cesdm_yaml_subset.py`'s and `tools/import_flexeco.py`'s
canonical-name-by-group mappings, and every example/test using
`.powerflow`/`.dynamic` as a live Python attribute.

`tools/generate_typings.py`'s stub-class-name generation fixed along
the way: it built the per-group stub class name via `grp.capitalize()`,
which only capitalizes the first character and leaves an underscore in
place (`power_flow` -> `Power_flow`, not the idiomatic `PowerFlow`).
Now converts snake_case to CamelCase properly
(`GenerationUnitPowerFlowProxy`, not `GenerationUnitPower_flowProxy`).

Full test suite (385 tests) and all 11 examples green.

### Changed -- the dynamic machine model flattened onto GenerationUnit after all

Asked directly why `MACHINE_*` was a standalone `DynamicModel.
GenerationUnit.Subtransient` entity instead of belonging to
`GenerationUnit` like every other group -- the honest answer was that
only one approach (naive flattening) had been tried before reaching
for the standalone-entity fallback, without exploring a fix for the
actual problem (every `MACHINE_*` attribute having a real default,
which `add_entity()`'s unconditional default-application would
activate on every generator). Investigated properly this time and
found a real fix, rather than accepting the earlier workaround as
final:

- **`ear/model/entity_ops.py`'s `add_entity()`**: schema defaults are
  no longer auto-applied at creation time for `belongsToGroup`-tagged
  attributes specifically (every other attribute's behaviour is
  unchanged). Confirmed directly: a bare `GenerationUnit` still
  validates with 0 errors, and nothing is written into its data for
  any `MACHINE_*` field.
- **`cesdm/domain/model/accessors.py`'s
  `get_effective_attribute_value()`**: gained a third, final fallback
  -- after the explicit value and the technology-template cascade --
  to the attribute's own schema-declared default. This is what makes
  `gen.MACHINE_xd` still return `1.8` even though nothing was ever
  written for it.
- **`cesdm/proxy.py`'s `AssetProxy.__getattr__`**: flat access
  (`gen.MACHINE_xd`) now routes through the same cascading lookup as
  namespace-alias access (`gen.dynamic.MACHINE_xd`) specifically for
  `belongsToGroup`-tagged attributes, so the two stay consistent with
  each other -- confirmed directly (both return the same lazily-
  resolved default, and both reflect an explicit override the same
  way).
- **`AssetProxy._view()`**: the "dynamic" special case (finding a
  linked standalone entity by class-name pattern) removed entirely --
  "dynamic" is just another entry in `_KNOWN_GROUPS` now, resolved the
  same generic way as `dispatch`/`topology`/etc.
- **`tools/generate_typings.py`'s `attribute_type()`**: `belongsToGroup`-
  tagged fields are now typed `| None` regardless of their schema
  `required` value, matching the conditional-requiredness `validate()`
  actually enforces (only once something else from that group is
  already present) -- the same treatment already applied to generated
  builder-method signatures in `generate_convenience_api.py`.

`MACHINE_*` and the three controller-linking relations
(`hasAutomaticVoltageRegulator`/`hasTurbineGovernor`/
`hasPowerSystemStabilizer`) now live directly on `GenerationUnit`,
tagged `belongsToGroup: [dynamic]`. `DynamicModel.
GenerationUnit.Subtransient` deleted entirely.

**AVR/governor/PSS controllers stay standalone entities** -- a
different reason than before applies here specifically: a generator
can have at most one of each, but three mutually exclusive AVR types
(and similarly governor/PSS) each carry their own distinct attribute
set, so flattening all of them onto `GenerationUnit` would mean
carrying every variant's attributes simultaneously, unlike the four
technical-view classes (whose attribute sets don't collide at all and
were flattened successfully earlier this session).

Confirmed directly, not assumed: setting `gen.MACHINE_xd` explicitly
correctly activates the `dynamic` group's conditional requiredness for
the remaining `MACHINE_*` fields with no default
(`MACHINE_rated_mva`/`MACHINE_rated_kv`/`MACHINE_model`), exactly like
every other conditionally-required group. `examples/
example_kundur_two_area.py` updated to set these directly on the
generator rather than a separate `dyn` entity, including its summary
printout (now counts generators with the dynamic group actually
engaged, since there's no separate class left to count).

Full test suite (385 tests) and all 11 examples green throughout.

Asked directly which helper functions in `builders.py`/
`generated_builders.py` are still used and whether the unnecessary ones
were deleted -- auditing this properly (grepping every one of the 20
hand-written functions across the whole codebase, not just trusting
earlier passes) surfaced three files this effort's example/tools sweep
had missed entirely:

- **`examples/example_hydro_reservoir_plant.py`** -- still called
  `add_bus()`/`add_reservoir_hydro()`/`add_phs_closed_loop()`
  throughout; an earlier response's "0 builder calls" check on this
  file was wrong. Rewritten to raw EAR calls, confirmed 0 validation
  errors on both the plain-reservoir and PHS-closed-loop scenarios.
- **`tools/import_matpower.py`** and **`tools/import_pandapower.py`**
  -- two importers (the reverse direction of `export_matpower.py`/
  `export_pandapower.py`, which *were* checked earlier and needed no
  changes) that this session's tool sweep never looked at at all.
  Each had exactly four real builder calls (`add_bus`,
  `create_demand_unit`, `create_generation_unit`,
  `create_transmission_line`); most of the surrounding code already
  worked correctly since it goes through `ensure_view()`/
  `get_dispatch_view()`/`connect_single_port()` (already fixed earlier
  this session), so only these four call sites needed replacing.
  Confirmed against a real, minimal MATPOWER `.m` case and a real
  pandapower network built and imported directly: 0 validation errors,
  every attribute (technology, carrier, topology, dispatch, power-flow
  setpoints) correctly present on the resulting flattened assets.

Also fixed two stale docstring comments (`example_cesdm_to_pandapower_
and_matpower.py`, mentioning `model.add_bus(...)` as the file's own
style though the actual code was already correct EAR calls) found
along the way. Confirmed no remaining usage anywhere in `tools/` or
`examples/` for any of the 20 hand-written builder functions via a
direct, exhaustive grep -- not assumed from memory of earlier passes.

Full test suite (386 tests) and all 11 examples green throughout.

### Changed -- BREAKING: representation views removed from the schema entirely

**This is now the toolbox's baseline, initial version, with no
representation-view concept in the schema at all** -- requested
directly, no backward compatibility with the old split-view pattern
kept or attempted. `schemas/views/` (48 files: every `*.DispatchView`,
`*.PowerFlowView`, `*.TopologyView`, `*.ResultView`, plus their
abstract bases `RepresentationView`/`StaticView`/`DynamicView`/
`PowerFlowView`/`SpatialView`/`ResultView`) deleted outright.

- **Every asset type already migrated to the flattened pattern**
  (`GenerationUnit`, `StorageUnit`, `DemandUnit`, `ExternalSupply`,
  `ElectricalBus`, `TransmissionElement` and its four subclasses) needed
  no further schema change -- their dispatch/topology/power-flow/
  spatial/planning/technical data was already directly on the asset.
- **The dynamic machine model** renamed and converted to a standalone
  entity: `Generator.DynamicView.Subtransient` ->
  `DynamicModel.GenerationUnit.Subtransient`, parent `SemanticEntity`
  (not a representation view), same treatment as AVR/governor/PSS
  controllers and for the same reason (every `MACHINE_*` attribute has
  a real default, so flattening it directly onto `GenerationUnit`
  would activate it on every generator unconditionally -- see the
  earlier, reverted flattening attempt in this same file's history).
- **Every result view converted to a standalone entity**, "View"
  dropped from the name throughout: `ResultView` -> `Result`,
  `DispatchResultView`/`PowerFlowResultView`/`DynamicResultView` ->
  `DispatchResult`/`PowerFlowResult`/`DynamicResult`, and their 9
  concrete leaf classes (`GenerationUnit.DispatchResult`,
  `ElectricalBus.PowerFlowResult`, `Generator.DynamicResult`, etc.),
  all now living under `schemas/entities/SemanticEntity/Result/`.
- **`ConversionUnit`**, never previously migrated, flattened directly
  (`nominal_power_capacity`, `variable_operating_cost`,
  `referencePort`) -- found only while fixing an example that still
  created a separate `Conversion.DispatchView`.

#### Core mechanisms simplified or fixed to match

- `cesdm/domain/model/builders.py`'s `ensure_view()` rewritten:
  derives the group directly from `view_class`'s own string suffix
  (`"DispatchView"` -> `"dispatch"`, `"TopologyView"` -> `"topology"`,
  `"PowerFlowView"` -> `"powerflow"`, `"LocationView"` -> `"spatial"`)
  rather than looking up a schema class's `view_family` -- there's
  nothing left to look up. The old fallback path (create a separate
  view entity) removed entirely.
- `cesdm/domain/model/accessors.py`'s `get_view()` simplified the same
  way.
- `cesdm/proxy.py`'s `AssetProxy._view()` (the mechanism behind
  `.dispatch`/`.topology`/etc.) rewritten: flattened groups resolve via
  `belongsToGroup` directly; `"dynamic"` is a special case, resolving
  to the linked standalone `DynamicModel.*` entity by class-name
  pattern + `representsAsset` rather than a schema `view_family`
  lookup (nothing has one any more). `_known_view_families()` (powers
  the "did you mean" typo suggestion) now returns a small hardcoded
  set instead of introspecting the schema.
- **`tools/aggregate_cesdm_yaml_subset.py`**: `_find_view_class_for_group()`
  replaced with a hardcoded `(asset_class, group) -> canonical section
  name` mapping. A second, more consequential bug found and fixed in
  `data_to_model()` itself: this tool's internal output-construction
  still organizes data into per-view sections (a legacy of the
  pre-flattening architecture) and tried to create a *separate entity*
  per section -- which silently failed once those class names no
  longer existed, dropping the data entirely rather than erroring.
  Fixed by flattening any such "legacy section" onto the asset it
  represents at the one point where the model actually gets built,
  rather than rewriting the tool's entire internal section-based
  logic.
- **`tools/import_flexeco.py`**'s `build_asset_view_map()` given the
  same hardcoded-mapping fix.
- **`tools/import_pypsa.py`**: seven internal helpers
  (`_ensure_nodal_view`, `_ensure_branch_topo`, `_ensure_line_pf`,
  `_ensure_trafo_pf`, `_ensure_gen_dispatch`, `_ensure_stor_dispatch`,
  `_ensure_dem_dispatch`) that directly created separate view entities,
  bypassing `ensure_view()` entirely, simplified to write straight onto
  the (already flattened) asset. Three more direct creation sites found
  and fixed the same way (`HydroGenerationUnit.DispatchView`,
  `HVDCLink.DispatchView`, `Conversion.DispatchView`). A pre-existing
  copy-paste bug found along the way: `_GENERATION_DISPATCH_VIEW_CLASS`
  was a dict with the same key (`"GenerationUnit"`) repeated eight
  times, clearly meant to list distinct asset classes originally.
- **`tools/generate_typings.py`** (the `.pyi` stub generator) required
  the most substantial redesign: `.dispatch`/`.topology`/etc. stub
  properties used to come from finding separate view classes sharing a
  `view_family` -- with none left, no such property was generated at
  all, silently breaking static type-checking for every proxy's group
  access (confirmed directly: Pyright accepted a deliberate typo,
  `.dispatch.anual_energy_demand`, with 0 errors). Redesigned to
  generate one dedicated stub class per `(asset class, group)` pair
  that has `belongsToGroup`-tagged fields, matching what
  `FlatGroupViewProxy` actually exposes at runtime. Along the way,
  found `FlatGroupViewProxy` itself was missing entirely from
  `proxy.pyi` (only `ViewProxy`/`AssetProxy` were declared) --
  Pyright was silently falling back to `Any` for every stub inheriting
  from it, which is what let the typo through in the first place.

#### Test suite

Recovered from **118 failed / 26 errors immediately after deleting
`schemas/views/`** down to a fully green suite (386 passed), fixing
each failure individually rather than papering over it: updated
several fixtures still manually constructing the old split-view
pattern (now impossible, since the classes don't exist), removed one
test whose entire premise -- a separate view entity "still taking
priority" for backward compatibility -- no longer applies at all, and
completely rewrote `test_view_family.py` (the old view_family-resolution
tests) and `test_view_only_asset_export.py` (used
`Storage.DispatchView`) around the new mechanism.

#### Examples

All 11 examples confirmed green throughout, including 4 found broken
only by actually running them after the schema deletion (not caught by
static review): `example_simple.py` and `example_multienergy.py` still
created a separate `Conversion.DispatchView` for their fuel-cell/CHP
ConversionUnit; `example_kundur_two_area.py` still referenced
`Generator.DynamicView.Subtransient` by its old name in several places
(including a summary print listing a now-nonexistent
`Generator.PowerFlowView` count); `example_schema_extension.py`'s
extension schema itself inherited from the deleted
`OperationalDispatchView` -- rewritten to demonstrate the flattened
pattern for the new type instead, matching the direction of this
change.

- **`test_aggregate_cesdm_yaml_subset_per_country.py` (37 real builder
  calls -- the largest test-suite file in this effort) rewritten to
  raw EAR calls throughout.** Three near-identical PHS/reservoir
  fixtures bulk-replaced via a single script once confirmed byte-for-
  byte identical, rather than three manual edits. Recurred the same
  fix found earlier this session in `example_import_tyndp_proxy_api.py`
  and needed again here: `Generation.Thermal.Gas.OCGT` isn't part of
  the default library (unlike `...CCGT.New`, which is), so linking
  `hasTechnology` to it needs `set_technology()` (ensures the
  `GeneratorType` entity exists first), not a plain `add_relation()` --
  caught immediately by `model.validate_or_raise()` in the fixture
  itself, not by a downstream test failure. All 35 tests in the file,
  and the full suite (443 tests), green throughout.

- **Started removing builder-function usage from the test suite,
  scoped per direct follow-up guidance**: only tests that use
  `add_<x>`/`create_<x>` merely as convenient fixture setup, not tests
  whose actual subject is the builder functions themselves. Categorized
  all 29 test files using these functions before touching any of them,
  rather than rewriting on principle -- files like
  `test_builders_reorganization.py`, `test_builders_return_types.py`,
  `test_generated_builder_default_optionality.py`,
  `test_generation_technology_routing.py`,
  `test_schema_convenience_api.py`,
  `test_dynamic_attribute_naming_and_defaults.py`,
  `test_default_library_source_validation.py`, and
  `test_default_library_typings_and_validation.py` explicitly test
  builder/generated-constructor behaviour (their own docstrings and
  test names say so directly) and are correctly left untouched.

  Rewritten so far: `test_pypsa_reservoir_no_own_topology_view.py`,
  `test_view_family.py` (view-family resolution is the actual subject;
  `add_generation_unit`/`add_controller_avr_sexs`/etc. were only ever
  used to set up a scenario), `test_model_summary.py` (same reasoning
  -- `model.summary()` is the subject, the entities it counts don't
  need a builder to exist). Full test suite (443 tests) confirmed
  green after each file.

  Remaining, by real (non-EAR) builder-call count:
  `test_aggregate_cesdm_yaml_subset_per_country.py` (37, likely mostly
  already-EAR from earlier sessions and worth re-auditing rather than
  assuming), `test_proxy_api.py` (18), `test_analysis_validation.py`
  (17), `test_generate_typings.py` (8), `test_technology_default_
  cascade.py` (8), `test_asset_proxy_string_coercion.py` (10),
  `test_asset_proxy_setattr.py` (9), `test_flexeco_flattened_asset_
  view_map.py` (6), `test_tyndp_full_pipeline.py` (6),
  `test_ear_entity_object_api.py` (4), `test_flat_proxy_and_
  namespace_alias.py` (4, my own file from earlier).

- **`examples/example_import_tyndp_proxy_api.py` (1192 lines) rewritten
  too, per explicit follow-up direction** ("builder functions
  generally avoided, but keep `entity.attribute = value`; no
  `add_<EntityClass>`/`create_<xxxxxx>` in this file either"). All 10
  remaining call sites (`add_generator`, `add_reservoir_storage`,
  `create_storage_unit`, `add_phs_open_loop`, `add_phs_closed_loop`,
  `add_reservoir_hydro`, `add_bus` ×2, `create_demand_unit` ×2)
  replaced with the exact `add_entity`/`add_attribute`/`add_relation`
  sequence each one wrapped internally, read directly from
  `builders.py` first given the file's own extensive, hard-won
  correctness comments around several of these exact call sites
  (documented edge cases in technology-family routing). The
  `assert gen.entity_class == generation_class` check -- there
  specifically to catch disagreement between `add_generator()`'s own
  routing and the TYNDP classifier -- became unnecessary and was
  removed: with no builder doing its own routing anymore, the
  already-computed `generation_class` is used directly to create the
  entity, so there's nothing left for the two classifiers to disagree
  about.

  **A real bug caught by the test suite immediately, not shipped**:
  `set_technology()` (which `create_generation_unit()` calls
  internally) ensures a `GeneratorType` entity actually exists before
  linking `hasTechnology` to it; a plain `add_relation(gen_id,
  "hasTechnology", phs_tech)` does not. This didn't surface in earlier
  rewrites (`tutorial_ch_neighbours.py`, `example_simple.py`, ...)
  because those files import the standard `default_library`, which
  already predefines `GeneratorType` entities for the common
  technology strings used there -- but this file's hydro/PHS
  technology strings aren't part of that library and were never
  otherwise created, so linking to them directly raised `KeyError`
  the moment anything tried to read from the (nonexistent) target
  entity. Caught by 27 failing/erroring tests the moment it was run,
  not discovered later; fixed by using `set_technology()` for these
  two call sites specifically, matching what `create_generation_unit()`
  always did internally.

  Full test suite (443 tests, including `test_tyndp_proxy_api_
  importer.py`'s dedicated PHS/reservoir composite-wiring checks) and
  all 11 examples green.

- **Checked the remaining large tools' builder usage before assuming
  a rewrite was needed, rather than rewriting on principle** --
  `tools/aggregate_cesdm_yaml_subset.py` and `tools/import_flexeco.py`
  already build their output models with core
  `add_entity`/`add_attribute`/`add_relation` calls exclusively (their
  only other `.add_`/`.create_` matches are `argparse.add_argument()`
  and h5py's `create_group`/`create_dataset`, unrelated to CESDM).
  `tools/export_matpower.py` and `tools/export_pandapower.py` only call
  *pandapower's own* `pp.create_bus`/`create_gen`/etc. (required --
  that's what building a pandapower network object means), not CESDM
  builders. `examples/example_import_tyndp.py` (1837 lines, the main
  TYNDP importer) was already pure EAR calls throughout. None of these
  five needed any changes at all.

  `tools/import_pypsa.py` had exactly one remaining call,
  `create_generation_unit()`, already inside an `if hasattr(model,
  "create_generation_unit"): ... else: # compatibility with base
  ear_toolbox.Model` fallback structure -- removed the `if` branch,
  keeping only the raw-EAR `else` path unconditionally.

  **A real, would-be-introduced bug caught before it shipped**: the
  surrounding carrier/resource-relation-setting code was itself gated
  behind `if not hasattr(model, "create_generation_unit"): ...` --
  reasonable when that method's *absence* was the trigger for the
  fallback, but since the method still exists on `builders.py` (only
  its *call site* was removed, not itself), that condition would now
  always evaluate `False`, silently skipping `hasInputCarrier`/
  `hasInputResource`/`hasOutputCarrier` for every imported generator.
  Fixed by making that block run unconditionally too, then confirmed
  directly against a real PyPSA network built and round-tripped
  through `build_cesdm_from_pypsa()`: `hasInputCarrier`/
  `hasOutputCarrier` both correctly present on the resulting
  `GenerationUnit` (previously would have been silently absent).

  Full test suite (443 tests) and all 11 examples green.

  **Remaining, deliberately not attempted this response**:
  `examples/example_import_tyndp_proxy_api.py` (1192 lines) still has
  10 builder call sites -- but unlike every other file in this effort,
  its own documented purpose is specifically *"to demonstrate and
  exercise the [builder/]proxy API against realistic complexity"* in
  contrast to the main TYNDP importer's pure-EAR style, and it carries
  extensive, hard-won, carefully-commented correctness fixes around
  several of those exact call sites (documented edge cases in
  `add_generator()`'s and `add_thermal_generator()`'s own internal
  routing that the surrounding code explicitly works around). Rewriting
  it risks both quietly undermining the file's stated pedagogical
  purpose and introducing a subtle regression in intricate,
  already-correct logic -- worth flagging plainly rather than
  proceeding on autopilot.

- **`examples/tutorial_ch_neighbours.py` (536 lines) rewritten --
  the last, most involved example in this effort.** Previously built
  its entire narrative around "the three layers of the CESDM API"
  with the builder-function layer as a first-class teaching subject;
  rewritten to teach core EAR calls plus the proxy layer instead,
  matching the direction requested. Every `add_<x>`/`create_<x>` call
  replaced with the exact `add_entity`/`add_attribute`/`add_relation`
  sequence each one wrapped internally -- read directly from
  `builders.py`'s own implementations first, given the real risk in
  this specific file: it demonstrates all four hydro plant patterns
  (run-of-river, reservoir, open-loop PHS, closed-loop PHS), the exact
  domain logic this session spent the most effort getting right
  earlier (`machine_role`, `drawsFromReservoir`/
  `dischargesToReservoir`/`suppliesResourceTo` pairing, PHS/non-PHS
  classification). Confirmed the full model still validates and the
  by-country/by-fuel capacity breakdown, hydro/reservoir counts, and
  interconnector NTC table are all unchanged from before the rewrite.

  **A second genuine, widely-used bug was found while checking the
  final "Total system capacity" line, which silently printed `0`**:
  `total_capacity()` (in `cesdm/domain/model/statistics.py`) searched
  exclusively via `_build_view_index()` -- itself keyed on a separate
  view entity's `representsAsset` relation -- so it found nothing at
  all for any flattened-pattern `GenerationUnit`. Fixed directly in
  `total_capacity()` to also read `nominal_power_capacity` from the
  asset's own data when no separate dispatch view holds it.

  A first attempt fixed this by extending `_build_view_index()` itself
  (the same central-fix approach that worked well for
  `import_flexeco.py`'s analogous `build_asset_view_map()` two
  responses ago) -- but `_build_view_index()` turned out to be used
  for two genuinely conflicting purposes: statistics functions want a
  flattened asset to self-represent (correct), but
  `export_yaml_hierarchical()` uses the exact same index to decide what
  to nest under an asset's `representations:` block, where
  self-representing is wrong -- it would nest an asset under itself.
  Caught immediately by 3 failing aggregation tests (reservoirs
  aggregating 2-to-2 instead of 2-to-1) rather than shipped; reverted
  the shared-index change and fixed `total_capacity()` on its own
  instead, once the conflict was understood. 1 new regression test
  pins down the fixed behaviour specifically.

  Full test suite (443 tests) and all 11 examples green.

- **Continued removing `add_<x>`/`create_<x>` builder calls**:
  `examples/example_agent_based_prosumer_model.py` rewritten --
  `add_bus`, `create_timestamp_series`, `create_profile` (×3),
  `create_demand_unit`, `add_solar_generator`, `create_storage_unit`
  all replaced with the raw `add_entity`/`add_attribute`/`add_relation`
  calls each one wrapped internally (read directly from `builders.py`'s
  own implementations to replicate them exactly -- e.g.
  `add_solar_generator`'s default `hasTechnology`/`hasInputResource`
  wiring, `create_storage_unit`'s `storesCarrier` relation only when a
  carrier id is given). `ensure_entity()`/`ensure_carrier()`/
  `add_relation_if_allowed()`/`attach_profile()` (generic, class-
  agnostic helpers, not per-class constructors) kept throughout.

  Full test suite (442 tests) and all 11 examples green (3 households,
  2 with PV, 1 with a battery -- same as before the rewrite).

  Remaining: `examples/tutorial_ch_neighbours.py` (536 lines, its
  narrative is built around teaching the builder-function layer as a
  first-class subject -- needs the tutorial's own framing rewritten,
  not just its code), `tools/aggregate_cesdm_yaml_subset.py`,
  `tools/import_pypsa.py`, `examples/example_import_tyndp.py` and its
  proxy-API sibling, and the test suite itself.

- **Continued removing `add_<x>`/`create_<x>` builder calls**:
  `examples/example_in_readme.py` and `examples/example_kundur_two_area.py`
  rewritten to use core EAR calls throughout, including the generated
  per-class constructors (`add_generator_dynamic_view_subtransient`,
  `add_controller_avr_sexs`/`_pss_stab1`/`_gov_ieeeg1`) in the Kundur
  file, not just the hand-written `builders.py` ones.

  **A genuine, independent bug was found and fixed in
  `example_in_readme.py`'s own statistics-computation code** while
  verifying the rewrite -- the exact same class of bug already fixed
  in `export_matpower.py`/`export_pandapower.py`/`import_flexeco.py`
  earlier, now recurring in an example script rather than a tool. Its
  energy-statistics loop specifically searched for a separate view
  entity via `representsAsset` to find `nominal_power_capacity`/
  `atNode`, so it silently reported `0.0 MW` generation capacity (and
  an empty demand-by-carrier breakdown) for any flattened-pattern
  asset -- confirmed directly: the printed "Entities in the loaded
  model" section correctly showed `nominal_power_capacity: 200.0` on
  `GT_1`, but "Generation capacity" printed `0.0 MW` right below it.
  Fixed to also self-represent when an entity carries the relevant
  data directly rather than via a separate view.

  `examples/example_explore_cesdm_model.py` confirmed to need no
  changes at all (it explores an *existing* YAML file via `--yaml`,
  never builds one, so has no builder calls in the first place).

  Full test suite (442 tests) and all 11 examples green after each
  file. Remaining: `examples/example_agent_based_prosumer_model.py`,
  `examples/tutorial_ch_neighbours.py` (536 lines, its entire narrative
  structure is built around teaching the "3 layers of the CESDM API"
  with the builder-function layer as a first-class teaching subject --
  needs a genuine rewrite of the tutorial's own framing, not just its
  code, so deliberately left for last), `tools/
  aggregate_cesdm_yaml_subset.py`, `tools/import_pypsa.py`,
  `examples/example_import_tyndp.py` and its proxy-API sibling, and the
  test suite itself.

- **Started removing calls to `cesdm/domain/model/builders.py`'s and
  `cesdm/domain/model/generated_builders.py`'s `add_<x>`/`create_<x>`
  functions from the codebase, as requested directly, prioritized
  ahead of other remaining work.** Given the true scope (roughly 300+
  call sites across examples, tools, and tests, many in 1000+-line
  importers), a single wholesale removal-and-fix pass would have been
  reckless to attempt without per-file verification -- continuing the
  same systematic, tested approach used throughout this migration
  rather than a big-bang rewrite.

  Rewrote to use core EAR calls
  (`add_entity`/`add_attribute`/`add_relation`) plus the proxy layer
  for convenient reading/writing afterward, confirming each file still
  produces the same output before moving to the next:
  - `examples/example_analysis_validation.py`
  - `examples/example_schema_extension.py`
  - `examples/example_cesdm_to_pandapower_and_matpower.py` (confirmed
    through a full, converged AC load flow, not just a clean run)
  - `examples/example_multienergy.py` (was already almost entirely
    EAR-level; the two remaining calls, `add_bus()` and
    `create_demand_unit()`, replaced)
  - `examples/example_simple.py` (the largest of this batch --
    replaced all 19 call sites across every entity type it
    demonstrates: `EnergySystemModel`, `EnergyCarrier`,
    `CarrierDomain`, `GeographicalRegion`, three bus classes,
    `DemandUnit`, `GenerationUnit`/`HydroGenerationUnit`,
    `StorageUnit`, `Interconnector`, `ConversionUnit`/`ConversionPort`)

  **A genuine bug in the rewrite was caught and fixed by validating
  after each change, not before**: `create_generation_unit(...,
  input_carrier_id="Water", ...)` maps to `hasInputCarrier`
  specifically (confirmed by reading `builders.py`'s own
  implementation), not `hasInputResource` as first guessed --
  `model.validate()` caught the mismatch immediately (`Water` is
  registered as an `EnergyCarrier` in that file, not a
  `NaturalResource`), rather than silently producing a subtly wrong
  model.

  `ensure_carrier()`/`ensure_entity()` (generic, class-agnostic
  helpers, not per-asset-type builders) and the proxy layer's
  read/write convenience (`gen.dispatch.x = y`, `.connect(...)`, etc.)
  are kept throughout -- only the `add_<x>`/`create_<x>` per-class
  constructor functions are being removed. Docstrings in each rewritten
  file updated to match (several previously described the file as
  "built entirely with the proxy API", which is no longer accurate).

  Full test suite (442 tests) and all 11 examples confirmed green after
  every file. Remaining: `tools/aggregate_cesdm_yaml_subset.py`,
  `tools/import_pypsa.py`, `examples/example_import_tyndp.py` and its
  proxy-API sibling, `examples/example_kundur_two_area.py`,
  `examples/tutorial_ch_neighbours.py`,
  `examples/example_agent_based_prosumer_model.py`,
  `examples/example_in_readme.py`,
  `examples/example_explore_cesdm_model.py`, and the test suite itself
  -- continuing in the same order (smaller, simpler files first).

- **Found and fixed a real regression in `tools/import_flexeco.py`'s
  `build_asset_view_map()`**, while checking whether other parts of
  the codebase had the same "scans `model.entities` for separate view
  entities directly" pattern already fixed in the two network-format
  exporters. They did: `build_asset_view_map()` only ever registered
  entities linked via a separate `representsAsset` relation, so a
  flattened-pattern asset (which now includes any model built with the
  ordinary builder functions, since `ensure_view()` was updated) was
  invisible to it entirely.

  Confirmed directly with a real PHS scenario, exported straight to
  FlexECO with no aggregation step in between (a genuinely untested
  path -- `export_flexeco` in `examples/example_import_pypsa.py` is
  CLI-flag-gated and not exercised by the existing test suite): the
  reservoir was silently skipped as "no inflow data" and the generator
  misclassified as `PN_GenDispatchable` instead of
  `PN_StoragePumpNoInfeed` -- the exact same class of misclassification
  bug already fixed earlier this session for the aggregation-tool code
  path specifically, now recurring on a different, previously-untested
  one.

  Fixed the same way as the exporters: `build_asset_view_map()` now
  also registers a flattened-pattern asset under every concrete view
  class name sharing one of its supported `belongsToGroup` families, so
  `avm.get(asset_id, {}).get("ReservoirStorageUnit.DispatchView")` (or
  any other specific class name checked throughout this file) finds the
  asset's own data instead of silently getting `None`. 2 new regression
  tests, one exercising the full direct-export scenario end to end and
  one targeting `build_asset_view_map()` itself. Full test suite (442
  tests) and all 11 examples green.

  Also did a broader sweep for the same pattern elsewhere (checked every
  relation target in the global registry and every entity class's own
  relation declarations against actual schema classes) -- found nothing
  else currently missing this fix, and every migrated asset class
  (`GenerationUnit`, `StorageUnit`, `DemandUnit`, `ElectricalBus`, and
  the rest) confirmed to validate cleanly as a bare instance, ruling out
  the same unconditional-default-activation problem found and reverted
  for the dynamic machine model recurring anywhere else.

- **Tried, and reverted, flattening the dynamic machine model
  (`Generator.DynamicView.Subtransient`) onto `GenerationUnit`.** A
  genuine, fundamental design conflict surfaced immediately: every
  `MACHINE_*` attribute has a real IEEE-typical default value, so
  `add_entity()`'s automatic default-population (unconditional --
  every attribute with a default gets set at creation time,
  regardless of which group it belongs to) would unconditionally
  activate the `dynamic` `belongsToGroup` on *every* `GenerationUnit*`
  the moment it's created, cascading into requiring
  `MACHINE_rated_mva`/`MACHINE_rated_kv`/`MACHINE_model` (which have no
  sensible default -- there's no "typical" generator size) even for the
  overwhelming majority of models that never intend any dynamic
  simulation at all. Confirmed directly: a bare `GenerationUnit` with
  nothing else set failed validation for these three attributes the
  moment the migration landed, and 27 tests failed or errored across
  the whole suite as a result. This is a different, more severe version
  of the tension the conditional-requiredness mechanism already handles
  for `atNode` and multi-field groups -- but those groups have no
  attribute with an unconditional default, so nothing ever silently
  activates them just from `add_entity()` alone.

  Reverted the `GenerationUnit.yaml` additions rather than trying to
  patch around it (e.g. weakening the conditional-activation check to
  ignore auto-populated defaults would have quietly broken the
  cascading technology-default mechanism other attributes rely on).
  The dynamic machine model stays a separate, opt-in view entity --
  `docs/schema_layout.md`'s original assessment that it "needs its own
  look" was correct. 1 new regression test locks in that a bare
  `GenerationUnit` keeps validating cleanly, so this exact mistake
  can't silently reappear if the dynamic view is reconsidered later.

  **A genuine, independent, pre-existing bug was found and kept
  fixed along the way, unrelated to whether flattening happens**:
  the global relation registry's `hasAutomaticVoltageRegulator`/
  `hasTurbineGovernor`/`hasPowerSystemStabilizer` targeted `AVRView`/
  `GOVView`/`PSSView` -- names that never existed as actual schema
  classes, predating even the old `ControllerView.*` naming. This had
  been silently masked because `Generator.DynamicView.Subtransient`'s
  own class-level declaration already overrode the target correctly
  to `Controller.AVR`/`Controller.GOV`/`Controller.PSS`, so the wrong
  global default was never actually exercised by that one call site --
  but it would have bitten anything else relying on the shared,
  global relation definition. Fixed in `schemas/relations/
  relations.yaml`.

  Full test suite (440 tests, including the new regression test) and
  all 11 examples green after the revert.

- **Technical views flattened onto `GenerationUnit` after all** --
  reconsidered the earlier "deferred, ambiguous" call: the four
  sibling classes (`ThermalGeneration.TechnicalView`,
  `NuclearGeneration.TechnicalView`, `SolarGeneration.TechnicalView`,
  `WindGeneration.TechnicalView`) don't actually collide on attribute
  names with each other (confirmed directly: every attribute across
  all four appears exactly once), so all merge cleanly onto
  `GenerationUnit` with `belongsToGroup: [technical]`, the same
  "single group, multiple use-case-specific attributes, only the
  relevant ones populated per instance" pattern already used for
  `Generation.DispatchView`. No need to resolve "which one is *the*
  canonical view" first, since there's no separate view entity to pick
  one for any more.

  `docs/schema_layout.md` updated to match: moved from "deliberately
  not flattened" to the migrated list. Only the dynamic machine model
  (`Generator.DynamicView.Subtransient`) remains genuinely unmigrated
  now, and for a different reason (its interaction with the
  `Controller.*` entities linked to it needs its own look, not a
  sibling-ambiguity problem).

  Full test suite (439 tests) and all 11 examples green.

- **`README.md`'s main quick-start rewritten to match the same
  direction as `docs/getting_started.md`** -- the most visible entry
  point to the project previously led with the builder-function
  approach captioned "this is what everyday code should look like" and
  closed with "neither version is more correct", directly contradicting
  the direction being asked for. Also, its EAR-level example was
  stale: it still manually created separate `SinglePort.TopologyView`/
  `Generation.DispatchView`/`Demand.DispatchView`/`TwoPort.
  TopologyView` entities, which is no longer necessary now that
  `GenerationUnit`/`DemandUnit`/`TransmissionLine` hold that data
  directly -- a reader following it verbatim would have written more
  code than needed and gotten the wrong impression that separate view
  entities are still required for these classes.

  Rewritten to lead with the core EAR calls (now genuinely simpler
  than before, since flattening removed the separate-view boilerplate)
  and present the builder-function version second, explicitly framed
  as the legacy pattern most existing importers/examples still use.
  The "CESDM: EAR applied to energy systems" description updated to
  describe the flattened pattern as the current one, listing what's
  deliberately still separate (`Controller.*`, `ConversionPort`, result
  views) rather than presenting "representation views separate from
  the asset" as the general rule. Both new code blocks extracted from
  the file and actually run, confirming both produce the exact
  documented output (`0.58`, `GenerationUnit 2`, `DemandUnit 1`,
  `TransmissionElement 1`) rather than trusting them by inspection.

  `mkdocs build --strict` and the full test suite (439 tests) confirmed
  green -- documentation-only changes, no code touched.

- **`docs/getting_started.md` rewritten to demonstrate the now-preferred
  pattern, as requested directly** ("always use the EAR level core
  functions"). Previously presented three layers (proxy/builder
  combined, plain builder functions, raw EAR calls) as equally valid,
  interchangeable choices ("pick whichever fits") -- this actively
  contradicted the direction being asked for, since it promoted the
  intermediate builder-function layer (`add_bus`,
  `add_thermal_generator`, `create_demand_unit`, ...) as a normal
  option rather than the legacy layer it now is. Rewritten to lead with
  pure EAR-level construction (`add_entity`/`add_attribute`/
  `add_relation`) plus the proxy layer for convenience
  (`_entity_proxy()`, `.dispatch`/`.connect(...)`), and to say plainly
  that the builder-function layer is what existing importers/examples
  still use for historical reasons but isn't the recommended starting
  point for new code. The exact code block in the rewritten doc was
  extracted and run to confirm it produces the documented output,
  rather than trusting it by inspection.

- **`AssetLocationView` and `AssetLifecycleView` flattened onto the
  shared `EnergyAssetInstance` parent** rather than each concrete asset
  subclass individually -- both target the generic
  `EnergyAssetInstance` (unlike the technology-specific dispatch/
  power-flow views), so every asset type (`GenerationUnit`,
  `StorageUnit`, `DemandUnit`, `TransmissionElement` and its
  subclasses, ...) now inherits `latitude`/`longitude`/`elevation`
  (`belongsToGroup: [spatial]`) and `commissioning_year`/
  `commission_date`/`retrofit_date`/`retirement_date`
  (`belongsToGroup: [planning]`) automatically through normal schema
  inheritance, with no per-subclass duplication needed. Confirmed
  directly (`latitude`/`commissioning_year` correctly present on both
  `GenerationUnit` and `DemandUnit`, `locatedIn`'s target correctly
  resolves to `GeographicalRegion`) rather than assumed. Full suite
  (439 tests) and all 11 examples green.

  Technical views (`Generation.TechnicalView` and its four
  technology-specific subclasses) remain deliberately unmigrated: four
  sibling classes share the same `view_family` and the same generic
  `representsAsset` target, with no schema-level way to tell which one
  is canonical for a given `GenerationUnit` -- unlike
  `HydroGenerationUnit.DispatchView`, which specifically targets
  `HydroGenerationUnit`. Flattening them would require resolving this
  ambiguity first, which needs its own design decision rather than a
  mechanical migration.

  Also confirmed, and worth being explicit about: the old, separate
  view schemas (`Generation.DispatchView.yaml`,
  `SinglePort.TopologyView.yaml`, etc.) can't simply be deleted yet even
  for asset types that are fully flattened -- `tools/
  aggregate_cesdm_yaml_subset.py`'s `_find_view_class_for_group()`
  looks them up by name to decide what to call the section it
  synthesizes for flattened data, so they're still structurally needed
  as naming references even though nothing instantiates them as
  separate entities any more for a migrated asset type.

- **Documentation updated to match the migration, as explicitly
  requested**:
  - `docs/schema_layout.md` rewritten (not just path-substituted): the
    new `schemas/entities/` inheritance-shaped folder tree, the
    flattened-representation-view mechanism (`belongsToGroup` as a
    list of `view_family` values, `FlatGroupViewProxy`, which asset
    classes are migrated so far and which are deliberately not),
    `Controller.*` as standalone entities linked via
    `controlsGenerationUnit`, and the consolidated single
    `attributes.yaml`/`relations.yaml` registries.
  - `docs/guide/05_representation_views.md`: the entire AVR/governor/
    PSS section rewritten -- it previously showed several real,
    now-incorrect code examples (`model.add_entity("ControllerView.
    AVR.ST1A", ...)`, `representsAsset` for controllers) that would
    fail if a reader tried them verbatim. Replaced with the
    `Controller.*`-entity pattern and `controlsGenerationUnit`
    throughout; the view-class reference table's three Controller
    rows removed (they're not views any more) with a note added
    pointing at which other rows now also live directly on their
    asset.
  - `docs/guide/03_schemas.md`: the class-hierarchy diagram and the
    "adding a new controller type" walkthrough updated to the current
    `Controller.*` naming, the consolidated attribute registry, and
    the (already-removed, confirmed via `docs/schema_layout.md`'s own
    note) registration step that no longer exists.
  - `docs/architecture/schema_governance.md`: one stale example
    (`ControllerView.GOV.*`) updated. `docs/architecture/
    schema_audit_report.md` deliberately left alone -- it's a
    point-in-time audit snapshot, not living documentation, same
    treatment as CHANGELOG entries.

  `mkdocs build --strict` and the full test suite (439 tests, all 11
  examples) confirmed green after every doc change -- documentation-only
  changes, no code touched.

- **`ElectricalBus` migrated to the flattened pattern too**:
  `ElectricalBus.PowerFlowView`'s and `BusLocationView`'s attributes/
  relations merged directly onto `ElectricalBus`, each
  `belongsToGroup`-tagged (`powerflow`/`spatial`). `locatedIn` was
  already declared on the parent `NetworkNode` class -- re-declaring it
  here with a `belongsToGroup` override correctly kept its existing
  target (`GeographicalRegion`) rather than losing it, confirmed
  directly before trusting it.

  **A genuine, pre-existing bug found and fixed along the way**:
  `ElectricalBus.PowerFlowView` never actually declared
  `powerflow_bus_type`/`voltage_magnitude_setpoint`/
  `voltage_angle_setpoint` as attributes at all -- its own attributes
  list was empty, despite its description explaining all three in
  detail. `add_bus(powerflow_bus_type="slack", ...)` had therefore
  always silently done nothing (`set_attribute_if_allowed()` only
  writes a value if the class actually declares the attribute) for as
  long as this code has existed. Fixed as part of the flattening --
  confirmed directly (`model.class_attributes("ElectricalBus.
  PowerFlowView")` returned `[]` before the fix) rather than assumed.
  1 new regression test pins this down specifically, in addition to
  confirming the flattened read/write behaviour generally.

  Full test suite (439 tests) and all 11 examples green.

- **`ensure_view()` flattening successfully re-applied and completed**
  -- the previous attempt (see the "tried and reverted" entry below)
  is now safely in place: `add_generator()`/`add_bus()`/
  `connect_single_port()`/`connect_two_port()`/etc. write directly onto
  the flattened asset whenever its class supports the pattern, with no
  separate view entity created at all. Getting there required finding
  and fixing every downstream consumer that still assumed a separate
  view entity always exists, plus two genuine bugs the attempt
  surfaced:

  - **`tools/aggregate_cesdm_yaml_subset.py`**: rather than rewriting
    its entire section-based grouping logic (a much larger undertaking
    on its own), added a normalization layer --
    `synthesize_flat_view_sections()`, wired into `model_to_data()` --
    that synthesizes a virtual separate-view-entity section entry for
    any asset using the flattened pattern, so every other function in
    the tool keeps working unchanged regardless of which pattern the
    source model used. `_find_view_class_for_group()` resolves the
    correct view class for a given (asset class, belongsToGroup) pair
    from the schema's own view_family/representsAsset declarations,
    rather than hardcoding a second, parallel mapping.
    - Found a genuine, pre-existing schema gap this surfaced:
      `NetworkTopologyView`'s own description says "Abstract base
      view" but the `abstract: true` field was missing, so it was
      wrongly picked as the synthesis target instead of the concrete
      `SinglePort.TopologyView`. Fixed in the schema.
    - Found and fixed a genuine specificity bug in
      `_find_view_class_for_group()` itself: when more than one
      candidate view class shares a view_family (e.g. both the generic
      `Generation.DispatchView`, targeting `GenerationUnit`, and the
      more specific `HydroGenerationUnit.DispatchView`, targeting
      `HydroGenerationUnit`, both count a `HydroGenerationUnit`
      instance as a covered target via inheritance), the most specific
      one now wins -- an exact target match beats one that only holds
      via an ancestor.
  - **`cesdm/domain/model/accessors.py`**: `get_view()` (and by
    extension `get_dispatch_view()`/`get_topology_view()`/
    `get_powerflow_view()`) now also recognizes the flattened pattern,
    returning the asset's own id when no separate view entity exists
    but the asset's class has the requested view's attributes/
    relations merged onto it directly.
  - **`tools/export_matpower.py` and `tools/export_pandapower.py`**:
    both had their own, independently duplicated `_view_by_asset()`/
    `_single_port_bus()`/`_two_port_buses()` helpers, scanning
    `model.entities` for separate view entities directly rather than
    going through an accessor -- fixed identically in both to also
    include flattened-pattern assets, using the asset entity itself as
    the data source when no separate view entity exists.

  Full test suite (438 tests) and all 11 examples green, including the
  TYNDP/PyPSA importer pipelines and both network-format exporters (one
  of which reached a converged AC load flow through the newly-flattened
  data end to end).

- Tried, and reverted, making `ensure_view()` (the single choke point
  behind `add_generator()`/`add_bus()`/`connect_single_port()`/etc.)
  write directly to the flattened asset instead of creating a separate
  view entity, whenever the asset's own class already supports it.
  This worked exactly as designed in isolation (confirmed:
  `add_generator(..., nominal_power_capacity=1600)` correctly wrote the
  value directly onto the asset, `views_for_asset()` came back empty,
  both flat and `.dispatch` access read the same value) -- but running
  the full suite immediately surfaced a much larger ripple effect than
  anticipated: `tools/aggregate_cesdm_yaml_subset.py`'s own tests (9 of
  them) started failing because the aggregation tool's entire grouping
  logic searches for separate `Generation.DispatchView`-style entities
  by class name, and suddenly found none for models built through the
  builders it had always relied on. Reverted rather than pushing
  forward mid-response and risking leaving the toolbox in a
  partially-broken state -- resolved properly in the entry above
  instead, once the normalization layer and downstream fixes existed
  to make it safe.

  One fix from this attempt was kept immediately, since it's safe and
  backward-compatible on its own: `get_effective_attribute_value()`
  (the technology-template-default cascade) assumed `view_id` always
  had a separate `representsAsset` relation pointing at the real asset
  -- doesn't hold once `view_id` *is* the asset itself (the flattened
  pattern), so it fell straight to `default` instead of cascading.
  Fixed to treat `view_id` as its own asset when it has no
  `representsAsset` relation, with no change in behaviour for the
  existing separate-view-entity case.

- **Tried, and reverted, making `ensure_view()` (the single choke point
  behind `add_generator()`/`add_bus()`/`connect_single_port()`/etc.)
  write directly to the flattened asset instead of creating a separate
  view entity, whenever the asset's own class already supports it.**
  This worked exactly as designed in isolation (confirmed:
  `add_generator(..., nominal_power_capacity=1600)` correctly wrote the
  value directly onto the asset, `views_for_asset()` came back empty,
  both flat and `.dispatch` access read the same value) -- but running
  the full suite immediately surfaced a much larger ripple effect than
  anticipated: `tools/aggregate_cesdm_yaml_subset.py`'s own tests (9 of
  them) started failing because the aggregation tool's entire grouping
  logic searches for separate `Generation.DispatchView`-style entities
  by class name, and suddenly found none for models built through the
  builders it had always relied on. The same is almost certainly true
  of the TYNDP/PyPSA importers and the FlexECO exporter, none of which
  have been rewritten to also handle the flattened pattern yet.
  Reverted rather than pushing forward mid-response and risking leaving
  the toolbox in a partially-broken state: this specific change needs
  the aggregation tool, both importers, and the exporter updated in the
  same pass to be safe, which is a substantially larger, multi-response
  undertaking of its own -- not something to attempt piecemeal. Full
  test suite (438 tests) and all 11 examples confirmed green again
  after reverting.

  One fix from this attempt was kept, since it's safe and
  backward-compatible on its own: `get_effective_attribute_value()`
  (the technology-template-default cascade) assumed `view_id` always
  had a separate `representsAsset` relation pointing at the real asset
  -- doesn't hold once `view_id` *is* the asset itself (the flattened
  pattern), so it fell straight to `default` instead of cascading.
  Fixed to treat `view_id` as its own asset when it has no
  `representsAsset` relation, with no change in behaviour for the
  existing separate-view-entity case.

- **AVR/GOV/PSS controllers converted to standalone `Controller.*`
  entities, as requested directly** (e.g. `Controller.AVR.SEXS`) --
  unlike the flattened-onto-the-asset views above, a controller is
  genuinely its own thing (an excitation/governor/stabiliser model), so
  it becomes a real, separate entity rather than data merged onto the
  `GenerationUnit` it's attached to -- same reasoning that already kept
  `ConversionPort` separate. All 14 `ControllerView.*` schema files
  renamed to `Controller.*` and moved into the `schemas/entities/`
  tree; `Controller`'s own parent changed from `DynamicView` to
  `SemanticEntity`, since `DynamicView` exists specifically to trigger
  automatic `role=view` classification, which would be wrong for a
  standalone entity. `representsAsset` (the view-discovery mechanism's
  key relation) replaced with a new `controlsGenerationUnit` relation,
  so `Controller.*` entities are no longer mistaken for representation
  views of `GenerationUnit` by `_discover_view_map()`.

  Two real issues found and fixed along the way:
  - The first replacement name, `controlsAsset`, collided with an
    already-existing, unrelated relation of the same name in
    `schemas_agentbased` (the generic EAR domain example schema from
    earlier this session) -- caught immediately by the schema loader's
    own duplicate-definition check, not silently. Renamed to the more
    specific `controlsGenerationUnit` instead.
  - `gen.avr`/`gen.governor`/`gen.pss` proxy shortcuts (relying on the
    old view-discovery mechanism) no longer resolve, by design --
    controllers are created directly via their generated constructor
    (`model.add_controller_avr_sexs(entity_id=..., 
    controlsGenerationUnit=gen, ...)`) and linked explicitly, the same
    pattern already used for `HydroGenerationUnit.drawsFromReservoir`/
    `ReservoirStorageUnit.suppliesResourceTo`. 3 tests and
    `examples/example_kundur_two_area.py` (which builds a full
    excitation/governor/PSS dynamic study) updated to the new pattern
    and constructor names; one stale, pre-existing comment/printout in
    that example (describing the old `.avr`/`.governor`/`.pss` access,
    and a leftover `ControllerView_AVR`-with-underscore typo that
    predates this change) corrected along the way.

  Full test suite (438 tests) and all 11 examples green.

- **`belongsToGroup` refined per direct feedback**: now a *list*
  (`belongsToGroup: [dispatch, powerflow]`), since an attribute or
  relation can legitimately belong to more than one group -- not just
  a single string as the first version had it. `ear/attribute_def.py`/
  `ear/relation_def.py` changed accordingly (with a shared
  `_normalize_belongs_to_group()` helper so a plain string in the
  schema still works, normalized to a one-item list, for convenience).
  `ear/model/validation.py`'s conditional-requiredness gating, the
  export logic in both `ear/model/persistence_yaml_json.py` and
  `cesdm/domain/model/hierarchical_yaml.py`, and
  `cesdm/proxy.py`'s `FlatGroupViewProxy` field-filtering all updated
  for list membership instead of exact-match comparison.

  Also per direct feedback: values are now the short `view_class`/
  `view_family` names (`dispatch`, `topology`, `powerflow` -- the same
  ones `cesdm.proxy`'s `.dispatch`/`.topology`/`.powerflow` already
  resolved against) rather than the original, full representation-view
  class names (`Generation.DispatchView`, `SinglePort.TopologyView`,
  `Generator.PowerFlowView`, ...). This is also a genuine
  simplification of `AssetProxy._view()`'s `FlatGroupViewProxy`
  resolution: no more looking up a view class definition and checking
  its `view_family` -- the belongsToGroup value already *is* the
  `view_family`. All schema files migrated so far (`GenerationUnit`,
  `StorageUnit`, `ReservoirStorageUnit`, `DemandUnit`, `ExternalSupply`,
  `TransmissionElement` and its four subclasses) updated to the new
  list/view_family form.

- **Schema files reorganized into folder structures showing
  inheritance, as requested directly**:
  - All 41 entity schema files (previously spread across topic-named
    folders -- `schemas/assets/`, `schemas/carrier/`, `schemas/core/`,
    `schemas/nodes/`, `schemas/profiles/`, `schemas/system/`,
    `schemas/technology/`) moved into a single `schemas/entities/`
    tree, nested by each class's own inheritance chain from the
    `SemanticEntity` root (e.g.
    `schemas/entities/SemanticEntity/SystemAsset/EnergyAssetInstance/
    GenerationUnit/HydroGenerationUnit/HydroGenerationUnit.yaml`).
    The old topic folders are gone entirely, not left behind empty.
    This didn't need any loader changes at all:
    `ear/model/schema_loading.py` already preferred an `entities/`
    subfolder with a recursive glob if one exists (a "LinkML-like
    layout" it was already designed to support) -- confirmed by
    checking the loader before moving a single file, rather than
    assuming.
  - The 7 separate attribute registry files (`schemas/attributes/
    attributes.yaml`, `carrier.yaml`, `demand_flex.yaml`,
    `dynamic.yaml`, `economics.yaml`, `generator.yaml`,
    `results.yaml`) consolidated into the single `attributes.yaml` --
    357 attribute definitions total, zero id collisions across the
    merge (attribute ids were already globally unique by design, see
    an earlier session's finding on this same point). Relations were
    already consolidated into a single `relations.yaml` -- confirmed
    before doing any work, not assumed.

  Full test suite (438 tests) and all 11 examples re-run and green
  after every step of this reorganization (list/view_family change,
  entity folder move, attribute file consolidation) -- confirmed each
  one independently rather than bundling and hoping.

- **Proxy API: both flat and namespace-alias attribute access now work
  over the same flattened storage** -- requested directly ("both would
  work"). `gen.nominal_power_capacity = 400` (flat) and
  `gen.dispatch.nominal_power_capacity = 400` (namespace alias) now
  read and write the *same* place for any asset migrated to the
  flattened representation-view model, rather than the alias silently
  pointing at an independent, separate view entity. New
  `cesdm.proxy.FlatGroupViewProxy`: same read/write interface as the
  existing `ViewProxy`, but filters the *asset's own* attributes/
  relations to whichever are `belongsToGroup`-tagged to match, instead
  of wrapping a separate view entity.

  Found and fixed a real regression while building this: a first
  version checked the flattened pattern *before* looking for an
  existing separate view entity, which broke 13 tests across the whole
  suite -- every one of them exercising `add_generator()`/
  `add_bus()`-style builder functions, which still create a genuinely
  separate view entity (the old pattern, untouched so far). Checking
  the flattened pattern first meant `.dispatch` silently started
  reading the (empty) flat asset storage instead of the separate view
  entity the builder had actually populated, making existing models
  built with the builder functions appear to have lost their dispatch
  data entirely. Fixed by keeping the existing-separate-view-entity
  check first (100% unchanged for anything already using it) and only
  falling back to `FlatGroupViewProxy` when no separate view entity
  exists yet for that asset/family. 6 new regression tests, including
  one specifically pinning down this exact backward-compatibility case
  so it can't regress silently again. Full suite (438 tests) and all
  11 examples green.

- **All major asset types migrated to the flattened representation-view
  model** -- continuing the effort above. `GenerationUnit` (+
  `Generator.PowerFlowView`), `HydroGenerationUnit` (confirmed to need
  no changes of its own: `HydroGenerationUnit.DispatchView`'s
  attributes were already 100% redundant with what `GenerationUnit`
  inherited), `StorageUnit`, `ReservoirStorageUnit` (only
  `hasNaturalInflowProfile` was actually unique to it, everything else
  already inherited from `StorageUnit`), `DemandUnit`, `ExternalSupply`,
  `TransmissionElement` (the shared parent for all branch elements --
  merging `TwoPort.TopologyView` once here rather than duplicating it
  across `TransmissionLine`/`HVDCLink`/`Interconnector`/`Transformer`),
  and each of those four subclasses' own `PowerFlowView`/`DispatchView`,
  plus `ShuntUnit`. `ConversionUnit` deliberately left as is:
  `Conversion.DispatchView` has no attributes at all, and its
  `ConversionPort` entities are a genuine many-per-asset pattern (a
  `ConversionUnit` can have several ports), not a single view that can
  be flattened onto the asset the same way -- same reasoning that
  keeps controller views as their own entities.

  Regenerating `cesdm/domain/model/generated_builders.py` against the
  fully migrated schema surfaced the same tension found with `atNode`
  earlier, now at scale: every `belongsToGroup`-tagged `required: true`
  field (e.g. `Generator.PowerFlowView`'s `powerflow_bus_type`/
  `active_power_setpoint`) became a mandatory keyword argument on the
  generated constructor, breaking every test and example that builds a
  bare asset and adds view-derived data later -- 11 tests failed purely
  from the regeneration, none from the schema content itself. Fixed at
  the right layer this time: `tools/generate_convenience_api.py`'s
  `_is_python_required()` (which already had an identical carve-out for
  attributes with a schema default) now also treats any
  `belongsToGroup`-tagged field as Python-optional, matching how
  `validate()` already enforces it -- conditionally, only once the
  group is actually in use -- rather than unconditionally at
  construction time. `powerflow_bus_type`/`active_power_setpoint` (and
  everything else in a multi-field group) restored to `required: true`
  in the schema, since the generator now correctly doesn't turn that
  into a mandatory constructor argument regardless.

  Full test suite (432 tests), all 11 examples, and the
  aggregation/PyPSA/TYNDP-specific test files (80 tests) all re-run and
  green with the fully regenerated builders across every migrated asset
  type -- confirms the downstream pipeline (TYNDP import, PyPSA import,
  aggregation, FlexECO export), which still uses the old
  separate-view-entity pattern unchanged, continues to work correctly
  alongside the new flattened one.

- **Representation views are being collapsed into their asset entity** —
  requested directly: no more separate `Generation.DispatchView`,
  `SinglePort.TopologyView`, etc. entities pointing back at an asset via
  `representsAsset` -- their attributes and relations move directly
  onto the asset itself, each tagged with a new `belongsToGroup` field
  naming which former view class it came from, so that origin stays
  traceable without a separate entity.
  - `ear/attribute_def.py`/`ear/relation_def.py`: new `belongsToGroup`
    field, alongside `required`/`description`/etc.
  - `ear/model/schema_loading.py`: reference-style attribute/relation
    items in a class's schema (`{id, required, belongsToGroup}`) now
    correctly recognized and materialized with the base attribute's
    unit/type/target still pulled from the global registry -- adding
    `belongsToGroup` without this would have silently treated the item
    as a full inline override, losing the base definition.
  - `ear/model/validation.py`: `required` on a `belongsToGroup`-tagged
    attribute/relation is now conditional on that group being *active*
    on the entity (at least one of its attributes/relations present) --
    mirrors the old semantics ("required once this view exists"), now
    that there's no separate view-entity creation event to key off of.
    Fields with no `belongsToGroup` (the base ones) are unchanged:
    unconditionally required as before.
  - `ear/model/analysis_validation.py`: fixed the check order so a
    `belongsToGroup`-tagged attribute now known directly on the asset
    is checked there *and* falls back to the old view-search extension
    hook if not actually populated there -- not just when the schema
    doesn't know about it at all -- so both old split-view data and
    new flattened-onto-asset data validate correctly.
  - `schemas/assets/GenerationUnit.yaml` migrated as the first,
    validated example: `Generation.DispatchView`'s and
    `SinglePort.TopologyView`'s attributes/relations merged in directly,
    each `belongsToGroup`-tagged. Confirmed end to end: setting
    `nominal_power_capacity`/`atNode` directly via
    `model.add_attribute()`/`model.add_relation()` (no separate view
    entity) validates cleanly, exports with `belongsToGroup` on each
    moved field, and round-trips through re-import unchanged.
  - Old split-view schemas and the code paths that create separate
    view entities are untouched for now (this is additive, not yet a
    removal) -- existing model-building code keeps working exactly as
    before while the new flattened pattern becomes available
    alongside it. Full test suite (432 tests) green throughout, only
    2 pre-existing tests needed a wording update to match the new,
    more accurate error message once dispatch attributes stopped
    requiring a separate view entity to exist at all.
  - Regenerating `cesdm/domain/model/generated_builders.py` against the
    migrated schema (as `cesdm-update-generated` always does after a
    schema change) surfaced a real tension: marking `atNode` `required:
    true` -- matching its old declaration on `SinglePort.TopologyView`
    -- turned it into a mandatory keyword argument on every generated
    `add_generation_unit()`-style constructor, breaking 11 tests that
    build a bare generator and connect it to a node later. Since the
    validation semantics above already treat a single-field group's
    `required` flag as effectively conditional (there's no *other*
    field in the group whose presence could ever activate it), changed
    `atNode` to `required: false` for consistency with how it's
    actually enforced in practice, restoring the existing
    incremental-construction flexibility. All 432 tests green again
    with the regenerated builder.

  **Not yet done** (large remaining scope, continuing across further
  turns): migrating the other 16 asset schema files and dropping their
  corresponding view schemas entirely; a new `Controller.*` entity
  pattern for AVR/GOV/PSS controller views; removing the old
  builder-function layer (`cesdm/domain/model/generated_builders.py`)
  in favour of using EAR-level `add_entity`/`add_attribute`/
  `add_relation` directly everywhere; regenerating the proxy API
  (`cesdm/generated_proxies.py`) to support both flat
  (`gen.nominal_power_capacity = 400`) and namespace-alias
  (`gen.dispatch.nominal_power_capacity = 400`) attribute access over
  the same flattened storage; updating `tools/import_tyndp*.py`,
  `tools/import_pypsa.py`, `tools/aggregate_cesdm_yaml_subset.py`,
  `tools/import_flexeco.py`, all examples, and all documentation to
  match.

### Added

- **EAR-level object-oriented API — phase 1 of a larger, multi-phase
  architectural change requested directly.** The full request also
  covers collapsing RepresentationViews onto their asset (attributes/
  relations tagged with a `belongsToGroup` field instead of living on a
  separate view entity), removing the CESDM domain layer's builder
  functions in favour of EAR-level calls everywhere, a flat-plus-alias
  proxy API, and turning controller views (`ControllerView.AVR.*`,
  `.GOV.*`, `.PSS.*`) into their own standalone `Controller.*`
  entities — deliberately **not** done yet, by agreement: this is
  phase 1 only, a small, self-contained, non-breaking step, with the
  rest to follow as separate, explicitly agreed phases given the true
  scope (62 view/controller schema files across every asset type,
  every importer, the aggregation tool, the FlexECO exporter, every
  example, every doc chapter, and the full test suite).

  `Model.add_entity()` already documented a return value in its own
  docstring but never actually returned one — fixed to match, and
  `Entity` gained its own `add_attribute(name, value)`/
  `add_relation(name, target_id)`, a thin wrapper delegating to
  `Model.add_attribute()`/`add_relation()` (not a duplicate
  implementation), so schema validation and storage stay in exactly
  one place:

  ```python
  gen = model.add_entity("GenerationUnit", "gen.1")
  gen.add_attribute("name", "gen.1").add_relation("hasTechnology", "Generation.Thermal.Gas.CCGT")
  ```

  Works for any entity regardless of how it was created — including
  ones loaded from a YAML file — since every entity-creation path
  (`import_yaml`, `import_yaml_hierarchical`, `import_library`, the
  CESDM proxy builders) already goes through `add_entity()` internally
  and so picks up the new back-reference for free. Confirmed
  non-breaking before committing to the approach: `Entity` is
  constructed directly in exactly one other place in the entire
  codebase (inside `add_entity()` itself), so the new field could be
  added with a default value, excluded from `repr()`/equality, with no
  risk to the many places across the codebase that construct or
  compare `Entity(cls=..., id=..., data=...)` directly — verified with
  the complete existing test suite (424 tests) passing completely
  unchanged before adding the 8 new ones for this feature specifically.
  Documented in `docs/guide/09_ear_toolbox.md`, right where the three
  core primitives already were.

### Fixed

- **`eta_gen` for `PN_StorageDam` came out `NULL` — the multi-target
  `drawsFromReservoir` fix above was itself only half-applied** —
  reported directly, right after the fix that made
  `drawsFromReservoir` correctly hold more than one target. Three
  places in `tools/import_flexeco.py` search for a reservoir's paired
  generator by comparing `sid` against `drawsFromReservoir`, but all
  three only ever checked the *first* element when it's a list
  (`_draws[0]`) — so once a merged generator's `drawsFromReservoir`
  genuinely held two targets, the lookup succeeded for whichever
  reservoir happened to be first and silently failed for every other
  one, leaving its efficiency, bus resolution, and
  reversible-generator detection all empty. Fixed by checking
  membership across the full list at each of the three call sites,
  not just the first entry.

- **Fixing that reverse lookup then surfaced a deeper, real modelling
  problem it had been masking: PHS and plain-hydro generators
  shouldn't merge into one aggregated unit at all** — once the lookup
  correctly found the shared merged generator for *both* reservoirs,
  the plain-hydro reservoir started inheriting the PHS generator's
  `machine_role: reversible` (since both physically different original
  units had been merged into one aggregated `HydroGenerationUnit` at
  `--tech-level 3`, where `Generation.Renewable.Hydro.{PHS.ClosedLoop,
  Reservoir,RunOfRiver}` all truncate to the same tag) — misclassifying
  it as an incomplete open-loop PHS (skipped for lacking a natural
  inflow profile) instead of a working `PN_StorageDam`. Fixed at the
  root rather than downstream: generation grouping now also checks
  whether a `HydroGenerationUnit` is PHS-paired
  (`is_phs_paired_generator()`, checking the same signals
  `tools/import_flexeco.py` itself uses for consistency), so PHS-linked
  and non-PHS-linked hydro generators never merge regardless of
  `--tech-level` — each reservoir keeps its own, correctly-classified
  generator.

- **"all NonDispatchable units export as Dispatchable after
  aggregation"** — reported directly. Same class of bug as the
  `pumping_efficiency`/`turbine_efficiency` gap found earlier:
  `dispatch_type` was listed in `allowed_agg_attrs_for_generation()` as
  an attribute the aggregator is allowed to carry through, for all
  three generation dispatch view types, but nothing ever actually
  computed or wrote it — every aggregated generator lost it regardless
  of technology, and `tools/import_flexeco.py`'s `PN_GenDispatchable`
  vs. `PN_GenNonDispatchable` classification (which reads
  `dispatch_type` directly, defaulting to dispatchable when it's
  simply absent) had no way to tell wind, solar, or anything else
  marked non-dispatchable apart from an ordinary dispatchable unit
  post-aggregation. Fixed the same way `machine_role` already was:
  preserve the dominant value among merged members.

  8 new regression tests across the three fixes above; the exact
  end-to-end scenario re-verified against the real ~44 MB nodal model:
  after these fixes, every aggregated `PN_StorageDam`/`PN_StoragePump`/
  `PN_StoragePumpNoInfeed` element has a non-null `eta_gen` (0 out of
  47 storage elements null, versus several countries with it null
  before).


- **The actual root cause of the persistent "reservoir never
  referenced" report: a real, pre-existing gap in the core EAR
  persistence layer, not the aggregation tool** — confirmed against the
  user's own real ~44 MB nodal PyPSA model and its aggregated output,
  not a synthetic reproduction. With `--tech-level 3`,
  `Generation.Renewable.Hydro.{PHS.ClosedLoop,Reservoir,RunOfRiver}`
  all truncate to the same 3-segment tag, merging generators of all
  three subtypes into one aggregated `HydroGenerationUnit` per
  country — but the reservoir side keeps its untruncated
  `storage_technology_type` tags (`"PHS"` vs `"hydro"`) distinct,
  producing two *separate* aggregated reservoirs the one merged
  generator must legitimately reference both of. This is a genuinely
  new case: no relation in the whole schema had ever needed one entity
  to hold more than one target through the same relation id before this
  aggregation scenario created it — and `add_relation()` turned out to
  have no accumulation semantics at all. Confirmed directly: calling it
  twice for the same (entity, relation) pair silently keeps only the
  *second* value (it always **sets**, never **appends**), and passing a
  list of targets directly gets **stringified** rather than stored as a
  real list. Both `ear/model/persistence_yaml_json.py`'s `import_yaml`
  and `cesdm/domain/model/hierarchical_yaml.py`'s
  `import_yaml_hierarchical` had the identical "call `add_relation()`
  once per target" pattern, so even a *correctly*-aggregated file with
  every target intact would still lose all but the last one the moment
  anything (including `tools/import_flexeco.py`, or simply re-loading
  the file to inspect it) read it back in.
  `tools/aggregate_cesdm_yaml_subset.py`'s own `data_to_model()` had the
  same pattern too. Fixed in all three places identically: set the
  first target through `add_relation()` as before (unchanged behaviour
  and validation for the overwhelming majority of relations that are
  genuinely single-valued), then, only when there's more than one
  target, write the real list directly onto the entity's own data.
  `HydroGenerationUnit.drawsFromReservoir` in
  `schemas/relations/relations.yaml` given an explicit `cardinality:
  0..*` to match (it has none currently declared elsewhere either, but
  the schema-level declaration and the persistence-layer fix are
  independent — this bug would have reproduced even with the
  cardinality already correct, since nothing in `add_relation()` or the
  import loaders actually consult the schema's cardinality to decide
  append-vs-overwrite).

  Verified end to end against the real uploaded dataset, not just a
  synthetic one: re-ran the exact reported command
  (`--no-split-voltage --tech-level 3 --level country --keep`) against
  the real ~44 MB nodal model and confirmed all 22 aggregated PHS
  reservoirs across every country are now referenced by their merged
  generator's `drawsFromReservoir` — zero orphaned, where every one of
  20 countries (all except two that only ever had a single PHS unit
  each, needing no merge) was affected before. 8 new regression tests:
  4 exercising this exact merged-generator-two-reservoirs scenario end
  to end (internal aggregation result, `data_to_model()`, and a full
  export/re-import round trip), and 4 more testing the core
  `import_yaml`/`import_yaml_hierarchical` fix directly and
  independently of the aggregation tool, including one that documents
  `add_relation()`'s actual overwrite-not-append behaviour explicitly
  so it doesn't get silently "fixed back" by a future change without
  someone noticing what depends on the workaround.


- **`pyproject.toml`'s `all` extras bundle was missing `pyright`** —
  found while verifying the reconciliation above on a genuinely fresh
  `pip install -e ".[all]"`: 2 more tests skipped ("pyright not
  installed") than the same suite reports elsewhere, even though
  `pyright` is already listed in the `dev` bundle right next to the
  other tools `all` is supposed to be the superset of. Added; the
  skip count matches across environments again.


- **A previously-uploaded package containing real infrastructure work
  (CI/CD, MkDocs/GitHub Pages publishing) had gone completely
  unnoticed and unmerged** — reported directly, after several turns of
  work that never touched it: an uploaded zip in
  `/mnt/user-data/uploads/` was never opened or reconciled with the
  delivered package, so `.github/workflows/tests.yml` (pytest CI on
  push/PR, Python 3.11 + 3.12) and `.github/workflows/docs.yml`
  (`mkdocs build --strict` → GitHub Pages), `mkdocs.yml`,
  `GITHUB_PAGES_SETUP.md`, and `docs/index.md` were silently absent
  from every delivery since. Diffed the uploaded package against the
  working tree file by file rather than assuming — confirmed the
  divergence was genuinely small and additive (their snapshot predated
  the per-country aggregation feature and the PyPSA reservoir fix by a
  few turns; everything else, `conftest.py`, `pyrightconfig.json`,
  `requirements*.txt`, matched byte for byte) — then merged their
  infrastructure in rather than starting over from their (older)
  snapshot.
  - `pyproject.toml`'s `docs` extra still listed `sphinx`/`myst-parser`/
    `sphinx-rtd-theme` — orphaned since the `doc/` Sphinx setup was
    dropped several turns ago in favour of `docs/`, and never updated
    at the time. Replaced with the `mkdocs`/`mkdocs-material`/
    `pymdown-extensions` the uploaded package's own CI actually
    installs; `Homepage`/`Documentation`/`Repository` and the README's
    docs badge and clone instructions updated to the
    `cesdm/cesdm-toolbox` identity the GitHub Pages setup already
    assumes throughout.
  - `docs/reference/schema_reference.html` (referenced in `mkdocs.yml`'s
    own nav) didn't exist in the working tree — regenerated fresh at
    that path rather than copying the uploaded (and by now stale) copy,
    and `tools/update_generated.py`/`cesdm-update-generated` extended to
    regenerate it alongside the default library, builders, and typings
    it already covered, so a schema change doesn't leave it stale
    again. The old root-level `CESDM_Schema_Reference.html` this
    replaces was removed rather than kept as a second, divergeable copy.
  - **Actually ran `mkdocs build --strict`** (the exact command
    `docs.yml`'s CI does) rather than assuming the merge was clean —
    found 6 broken links immediately: several `docs/` pages linked to
    `README.md`/`examples/`/`analysis_profiles/` with relative paths
    that escape the `docs/` directory, which MkDocs's own strict-mode
    link checker (unlike a plain "does this path exist on disk" check)
    correctly flags, since those files aren't part of the published
    site's own tree and the links would be dead on the live site
    regardless of what's on disk locally. Fixed by pointing all six at
    the equivalent `https://github.com/cesdm/cesdm-toolbox/blob/main/...`
    URL instead; rebuilt in strict mode again afterward and confirmed
    zero warnings.
  - A stray `examples/output/` directory (accumulated example run
    artifacts from earlier in this session) was being silently
    packaged into every delivered zip, since the packaging command's
    own exclusions never covered it specifically — removed, and the
    packaging step now excludes it explicitly going forward.

### Changed

- **`docs/guide/08_spatial_aggregation.md` and `docs/importers/pypsa.md`
  updated for the reservoir-topology-view fix and the per-country
  aggregation feature** — asked directly. Before writing anything,
  checked whether the reservoir-topology-view bug just fixed in
  `tools/import_pypsa.py` existed anywhere else it could still give a
  `ReservoirStorageUnit` electrical connection information of its own:
  the two other places in that file calling `_ensure_nodal_view()`
  (loads, generators) are unrelated asset classes, and the Links
  section only ever connects two buses to each other, never a
  reservoir — confirming the fix already applied to both PyPSA storage
  representations (`storage_units` and `stores`) is complete. Docs
  updated to match: the spatial-aggregation guide's Storage section now
  explains reservoirs are resolved via their paired generator's bus,
  not directly, and documents the orphaned-reservoir diagnostic's exact
  wording (kept in sync with the actual log message, not paraphrased);
  the PyPSA importer doc gained a new section explaining the
  reservoir/hydro-generator composite representation PyPSA's single
  electrically-connected storage component gets split into, matching
  how the TYNDP importer represents the same physical concept.

- **Found the actual root cause: `tools/import_pypsa.py` gave every
  hydro/PHS reservoir its own, redundant `SinglePort.TopologyView`** —
  identified directly, from the real pre-aggregation YAML: the
  reservoir had its own `atNode` connection to the same bus its paired
  `HydroGenerationUnit` was *also* separately connected to. Traced to
  the `storage_units`/`stores` import loops, which call
  `_ensure_nodal_view(model, eid, ...)` on the storage entity itself
  unconditionally, before checking whether it's hydro/PHS storage —
  which then, further down the same loop, *also* gets a paired
  `HydroGenerationUnit` with its own topology view via
  `_ensure_hydro_reservoir_composite()`. The result: two separate
  electrical connections to the same bus for what CESDM models as one
  physical asset (a reservoir is never itself electrically connected —
  only its paired generator is, via `drawsFromReservoir`), in both of
  PyPSA's two storage representations (`storage_units` and `stores`).
  Fixed by skipping the reservoir's own `_ensure_nodal_view()` call
  whenever it's hydro/PHS storage, in both loops. My own earlier fixes
  to the aggregation tool and `import_flexeco.py` (falling back to a
  reservoir's paired generator's bus when the reservoir has none) were
  real, necessary fixes for CESDM's actual convention — but they were
  compensating for this importer bug rather than the reservoir's
  intended, permanent shape; this fixes it at the source instead. 9
  new regression tests confirm `_ensure_hydro_reservoir_composite()`
  itself only ever gives the generator (never the reservoir) a
  topology view, and that PHS is correctly covered by the
  hydro-storage detection the new guard relies on.

- **`tools/aggregate_cesdm_yaml_subset.py`'s existing orphaned-reservoir
  diagnostic made much more specific** — reported again, still
  happening after the two rounds of fixes above, and specifically
  *after* aggregation with a reservoir not linked from any
  `HydroGenerationUnit`. Tried to reproduce directly with several
  different synthetic multi-country, multi-bus, mixed-per-country-level
  models (2 and 3 PHS units per country, CH/DE/FR together with
  different `--level-by-country`/`--tech-level-by-country` combinations)
  — every one aggregated correctly, so the exact failure mode hasn't
  been reproduced yet. Rather than keep guessing blindly, the existing
  "orphaned reservoir" warning (which already existed but only named
  the aggregated id) now traces every pre-aggregation source reservoir
  that fed into it individually: whether it had a paired generator in
  the input data *at all* (a genuine source-data gap, not an
  aggregation bug) versus, if it did, exactly what id
  `aggregated_storage_id_for_asset()` computes for that generator right
  now — an explicit MATCH/MISMATCH per source reservoir, rather than a
  single yes/no. Running this against the real dataset that reproduces
  the problem should show directly which of the two it is.

### Fixed

- **The reservoir fix above wasn't the whole story — same error still
  reported after it.** Tracing the exact downstream classification
  logic in `tools/import_flexeco.py` step by step (not just re-reading
  the aggregation tool) found two more bugs in the same reservoir/PHS
  pipeline, needed together to actually resolve it:
  - `import_flexeco.py`'s own `_bus_from_nodal_view(sid)` call for a
    storage asset has the *exact same* bug as the one just fixed in
    the aggregation tool — it reads the reservoir's own (nonexistent)
    `SinglePort.TopologyView` directly, so `busuid` was `None` for
    every reservoir there too. Fixed with the same "fall back to the
    bus reachable through the paired `HydroGenerationUnit`" pattern.
  - `pumping_efficiency`/`turbine_efficiency` were listed in
    `allowed_agg_attrs_for_generation()` as attributes the aggregator
    is allowed to carry through, but nothing ever actually computed or
    wrote them — every aggregated hydro/PHS generator silently lost
    both, regardless of how many original units it merged. This
    mattered specifically because `import_flexeco.py`'s closed-loop
    PHS branch (`PN_StoragePumpNoInfeed`) requires a non-`None`
    charging efficiency to be reached at all; without it, a closed-loop
    PHS reservoir fell all the way through to a silent `else: continue`
    — no output element and no error message either, worse than the
    originally-reported symptom. Fixed by computing a
    capacity-weighted average for both, the same pattern already used
    for `energy_conversion_efficiency`.

  Confirmed end to end with a real `tools/import_flexeco.py` export
  run (not just inspecting the intermediate aggregated YAML): a
  closed-loop PHS reservoir aggregated across two nodes now correctly
  produces one `PN_StoragePumpNoInfeed` element. 2 new regression
  tests, one of them running the actual export end to end via
  `export_to_flexeco()`.


- **`tools/aggregate_cesdm_yaml_subset.py`: every reservoir/PHS storage
  asset was silently excluded from aggregation entirely** — reported
  directly, from a real run: `import_flexeco.py` (downstream of
  aggregation) logged `"Reservoir/Pondage '...' has no inflow data —
  skipped"` for essentially every aggregated reservoir across every
  country in the run. Root cause: a `ReservoirStorageUnit` is never
  itself electrically connected — only its paired
  `HydroGenerationUnit` is, via `drawsFromReservoir` (confirmed against
  both `examples/example_import_tyndp.py`'s
  `_ensure_hydro_reservoir_composite`, which only ever attaches a
  `SinglePort.TopologyView` to the generator, and a hand-built PHS
  test model — same shape both ways). The storage-aggregation loop
  determined which bus to group a storage asset by via
  `a2n.get(asset_id)` — the asset's *own* topology view — which is
  always `None` for a reservoir, so every reservoir was silently
  dropped from the aggregated output before this fix, not just missing
  one attribute. Fixed with a new `build_reservoir_bus_via_generator()`
  helper that reconstructs a reservoir's effective bus via the
  generator that draws from it, used as a fallback everywhere a
  storage asset's bus is looked up — including
  `aggregated_storage_id_for_asset()`, which computes its own separate
  copy of the aggregated id to preserve `drawsFromReservoir` links and
  needed the identical fallback to stay consistent with the main
  aggregation loop. 4 new regression tests, including one that
  confirms the test fixture itself has the same "no direct topology
  view" shape being defended against, and one that reproduces the
  originally-reported symptom directly (inflow/capacity correctly
  summed on the now-present aggregated reservoir).

### Added

- **`tools/aggregate_cesdm_yaml_subset.py`: per-country customizable
  aggregation, on two independent axes** — requested directly. Spatial:
  `--level-by-country CH=nuts3 DE=country` overrides the global
  `--level` default for specific countries in the same run (e.g. keep
  one country at full nodal resolution while collapsing its neighbours
  to one node each). Technology: `--tech-level-by-country DE=3`
  overrides the global `--tech-level` default depth — a count of
  dot-separated segments to keep from each asset's `hasTechnology` id
  before grouping, so e.g. depth 3 merges `Generation.Thermal.Gas.CCGT`
  and `Generation.Thermal.Gas.OCGT` into one aggregated generator at
  the same node (summed capacity, capacity-weighted efficiency/cost,
  same rules as same-technology merging already used); omitting it
  (the default) keeps every distinct technology its own aggregated
  asset, unchanged from before. Both accept one or more `COUNTRY=VALUE`
  pairs; a country not listed in either simply uses the global default.

  Getting this right required more than just adding two new CLI flags:
  the aggregated-bus and `GeographicalRegion`-entity construction code
  both used the single global `level` to pick the id prefix
  (`nuts3.`/`country.`/...), which is now wrong per-node once
  different countries can use different levels — fixed by tracking
  which level actually produced each aggregated node/region code, not
  assuming they all came from the same one.
  `aggregated_storage_id_for_asset()` (which preserves
  `drawsFromReservoir` links across aggregation) computes its own,
  separate copy of the aggregated storage id and needed the identical
  technology-depth truncation applied to stay consistent with the main
  storage-aggregation loop — otherwise the two would compute different
  ids for the same storage unit and the relation would silently point
  at an id that was never created.

  Verified against a small, self-contained two-country synthetic model
  (no external TYNDP/PyPSA data needed): confirmed the exact scenario
  requested — Germany's CCGT and OCGT plants at two different nodes
  correctly merge into one aggregated generator with summed capacity
  (300 + 150 = 450 MW) once Germany aggregates to country level with a
  technology depth of 3, while Switzerland's own CCGT/OCGT stay
  separate; confirmed pure backward compatibility (no per-country
  overrides given at all reproduces the exact prior single-global-level
  behaviour). 23 new regression tests, plus
  `docs/guide/08_spatial_aggregation.md` updated with a dedicated
  section and both CLI examples re-run for real, not just described.

### Changed

- **README's "What is CESDM?" section restructured into three clearly
  headed subsections** — asked directly for the progression to read
  as its own section per layer: EAR (any structured system describable
  with three building blocks) first, then CESDM (EAR applied
  specifically to energy systems, with energy-domain helper APIs) as
  its own section, then the proxy API (the same system, described more
  conveniently) as its own section after that. The content itself
  already made exactly this argument — it just lived as three
  unlabelled bold-lead-in paragraphs under one heading rather than as
  three distinct, scannable sections; split apart with no wording
  changes to the substance, verified the internal links and image
  still resolve.


- **README's "What is CESDM?" restructured to lead with EAR, not
  CESDM** — requested directly: Entity/Attribute/Relation is a
  general-purpose idea that can describe *any* structured system, not
  an energy-specific one, and the README previously introduced
  entities/attributes/relations as if they were CESDM's own concepts.
  Reordered: EAR's generality first (with a pointer to
  `examples/example_ear_generic_domain.py` as direct proof — zero
  energy-specific code), then CESDM as what applying that idea to
  energy systems produces (the energy schema, helper builder
  functions, representation views, importers/exporters), then the
  object-oriented proxy API as a convenience layer describing the
  identical underlying data, not a different model.

### Fixed

- **`examples/example_import_tyndp.py` looked for
  `TYNDP24_StorageCapacitites.csv`** (extra "tites") in its actual,
  executed file-path construction — every other mention of this
  filename in the codebase (docstrings, the proxy-API sibling)
  already had the correct spelling, `TYNDP24_StorageCapacities.csv`,
  making this specifically a runtime bug, not just a documentation
  inconsistency: anyone with a correctly-named real TYNDP dataset
  would have had storage energy capacities silently go unread. Fixed
  at the one real occurrence, plus two matching mentions in
  `examples/README_TYNDP_IMPORT_LOGIC.md`; confirmed no occurrence of
  the misspelling remains anywhere in the repository.

- **`download_external_data.py` was a completely orphaned script** —
  reported directly: a user hit `[SSL: CERTIFICATE_VERIFY_FAILED]
  certificate verify failed: self-signed certificate in certificate
  chain` running it. Checking first: the script existed at the
  repository root but was never referenced from `README.md` or
  `docs/` anywhere, and — since `ethz.ch` isn't a reachable domain in
  this environment either — had never actually been exercised. The
  reported error is the specific signature of a network intercepting
  HTTPS traffic (common on corporate/institutional staff networks and
  VPNs presenting their own certificate) rather than a problem with
  the script or with ethz.ch, so the fix is better diagnostics and an
  explicit opt-in, not silently disabling verification: on an SSL
  certificate error, the script now prints both likely causes
  (intercepting proxy vs. an outdated/missing certificate bundle —
  the classic macOS python.org-installer issue, fixed by running its
  bundled "Install Certificates.command") and how to address each,
  plus a `--insecure` flag for a user who has checked both and
  explicitly accepts the risk — off by default, since disabling
  certificate verification removes protection against a genuine
  man-in-the-middle attack, not just a warning. Wired into
  `docs/importers/tyndp.md` (which `docs/importers/pypsa.md` already
  points to for this same dataset) so it's no longer orphaned. 5 new
  regression tests covering the parts that don't need a real network
  call: the default stays secure (no SSL context override unless
  `--insecure` is given), `--insecure` builds a real unverified
  context, an SSL certificate error gets the actionable message, and a
  non-certificate `URLError` (e.g. DNS failure) correctly does not.


- **`examples/legacy/` removed — 8 of its 9 files were silently
  broken** — asked directly why the folder existed at all; checking
  before answering found that 8 of the 9 files crash immediately
  (`FileNotFoundError`/`ModuleNotFoundError`), not just outdated in
  content. The cause: each computed its own repo root as
  `Path(__file__).resolve().parents[1]`, correct while these files
  lived directly in `examples/`, but never updated to `parents[2]`
  when they were moved into `examples/legacy/` (one level deeper) —
  broken since that move, invisible because none of them are in the
  test suite. Since their stated purpose (showing the pre-proxy-API
  style for comparison) is already served, working and tested, by
  `docs/getting_started.md` and the per-example companion docs added
  earlier, 8 files were deleted outright rather than repaired.
  `example_import_tyndp.py` was the one genuine exception — it's a
  real dependency, not just a comparison artifact:
  `example_import_tyndp_proxy_api.py` imports its technology-
  classification functions and constants directly to stay faithful to
  the original's business rules. Moved back to `examples/` (its
  original location, which also correctly fixes its own
  `parents[1]` path bug as a side effect, since that calculation is
  only wrong one level deeper) instead of into the deleted folder;
  `example_import_tyndp_proxy_api.py`'s `sys.path` setup and comments
  updated to match, and `docs/importers/tyndp.md`/`examples/
  README_TYNDP_IMPORT_LOGIC.md`/the six other examples' own docstring
  mentions of `examples/legacy/` all updated or removed. Verified
  after the move: both TYNDP examples run correctly, the full test
  suite passes, and a complete link check across `README.md`, `docs/`,
  and `examples/` finds nothing broken.

### Changed

- **README's "Editor typings" section expanded with per-editor setup
  instructions** — asked directly whether VS Code/Sublime Text/PyCharm
  setup was documented; it wasn't — the previous single line
  ("picked up automatically via `[tool.pyright]`") is only actually
  true for Pyright-based editors, and PyCharm doesn't read that config
  section at all, so the same sentence was silently misleading for
  PyCharm users. Verified before writing anything: PyCharm's own
  documentation confirms marking a stub directory as a *Sources Root*
  is the officially recommended mechanism for external `.pyi` stubs;
  Sublime Text's LSP-pyright package runs the same underlying Pyright
  engine as VS Code's Pylance and reads the identical `[tool.pyright]`
  config the same automatic way. Added concrete, verified steps for
  all three editors.


- **`docs/illustrations/cesdm_architecture.svg` redesigned as a proper
  layered-architecture diagram** — the previous version (a linear
  data-flow diagram: external data → importers → CesdmModel → proxy
  API → Build/Explore/Validate/Transform → export formats) didn't
  actually show the architecture: it collapsed EAR and CESDM into one
  box, never showed the schema at all, and showed the proxy API as a
  pipeline step rather than a layer on top. Redesigned bottom-up:
  Schema (YAML) and the generic EAR Engine as the two complementary
  foundations (schema = data, engine = code that interprets it), the
  CESDM Domain Layer built on both (with Representation Views,
  Composite Builders, Import/Export Adapters, and — new — Analysis
  Validation as its four sub-parts), and the object-oriented Proxy API
  as an explicitly optional layer on top of that. Verified
  programmatically (no unexpected bounding-box overlaps, every text
  line's estimated rendered width checked against its containing
  box) and by rendering to PNG. Also embedded in the README for the
  first time — the file existed in the repository already but wasn't
  linked from anywhere, so nobody browsing the docs would ever have
  actually seen it.

### Added

- **Per-example step-by-step walkthrough docs, and a "why it matters"
  column in the README's examples table** — asked directly whether the
  README described why each example matters, and whether each example
  could get a step-by-step companion doc with source code (following
  the existing pattern of `README_AGENT_BASED_EXAMPLE.md`/
  `README_PYPSA_IMPORT_LOGIC.md`/`README_TYNDP_IMPORT_LOGIC.md`, which
  only covered 3 of the (now) 14 examples). Added the remaining 11:
  `README_IN_README_EXAMPLE.md`, `README_SIMPLE_EXAMPLE.md`,
  `README_MULTIENERGY_EXAMPLE.md`, `README_HYDRO_RESERVOIR_EXAMPLE.md`,
  `README_KUNDUR_TWO_AREA_EXAMPLE.md`, `README_CH_NEIGHBOURS_TUTORIAL.md`,
  `README_EXPLORE_MODEL_EXAMPLE.md`, `README_POWERFLOW_EXPORT_EXAMPLE.md`,
  `README_ANALYSIS_VALIDATION_EXAMPLE.md`,
  `README_EAR_GENERIC_DOMAIN_EXAMPLE.md`,
  `README_SCHEMA_EXTENSION_EXAMPLE.md` — all in `examples/`, linked
  from the README table. Every code snippet shown is copied from the
  actual current example source (not reconstructed from memory) and
  every printed output shown was captured by actually running the
  example, not assumed. `example_explore_cesdm_model.py`'s functions
  needed a small self-contained model to demonstrate against, since
  the script itself requires an external PyPSA-imported YAML file as
  input — documented as such rather than silently working around it.

- **Three new examples filling gaps found in a coverage review** —
  asked directly whether the examples covered EAR, CESDM, the proxy
  API, and general usage well; on review, three real gaps: zero
  coverage of `validate_for_analysis()`, no standalone example of the
  generic EAR engine outside the energy domain, and no worked example
  of extending the schema with a genuinely new entity type.
  - `examples/example_analysis_validation.py` — `validate_for_analysis`
    against `model.validate()`, plus what a schema-constraint violation
    actually looks like in practice. Confirmed directly, not assumed:
    setting an invalid enum value through the proxy API (`gas.dispatch.
    dispatch_type = "steerable"`) prints a warning immediately but does
    *not* raise or block the assignment — `model.validate()` is the
    authoritative, structured way to catch it afterward.
  - `examples/example_ear_generic_domain.py` — the same household/
    energy-community scenario `docs/guide/09_ear_toolbox.md` walks
    through in prose, as a complete runnable script using only
    `ear_toolbox` (no proxy API, no energy-specific helpers at all).
    Found while writing it: `validate_or_raise()` is CESDM-only and
    doesn't exist on a plain `ear.model.Model` — used the generic
    `validate()` pattern instead.
  - `examples/example_schema_extension.py` — adds a new
    `ElectricVehicleChargingStation` entity type via a schema extension
    (the same `extends:` mechanism `schemas_agentbased/` uses), with no
    core schema or Python changes. Found while designing it: the
    attribute name first chosen (`maximum_charging_power`) already
    existed in the core schema for something else — reused directly
    rather than redefined, and left in as an explicit illustration of
    "check whether an attribute already exists before adding a new one."
  - Cross-referenced from `docs/architecture/analysis_validation.md`,
    `docs/guide/09_ear_toolbox.md`, and `docs/guide/03_schemas.md`;
    added to the README's examples table.

### Fixed

- **Every example referenced in the README and `docs/` audited against
  what actually exists in `examples/`** — asked directly. Found:
  - `docs/importers/pandapower.md`, `docs/importers/matpower.md`,
    `docs/exporters/pandapower.md`, `docs/exporters/matpower.md` all
    referenced two files
    (`examples/example_pandapower_to_cesdm_to_matpower.py`,
    `examples/example_matpower_to_cesdm_to_pandapower.py`) that **do
    not exist anywhere in the repository**, plus a whole "IEEE
    case118 example" section describing IEEE 118-bus test-case
    functionality that was never actually built (confirmed with a
    repository-wide search for `case118` — zero matches anywhere).
    Fixed to reference the actual existing example
    (`examples/example_cesdm_to_pandapower_and_matpower.py`); the
    fictional case118 sections removed.
  - That same actual example file's own docstring told the reader to
    run a *different*, nonexistent filename
    (`python examples/example_matpower_to_cesdm_to_pandapower.py`) —
    a copy-paste mistake, fixed to reference itself correctly. The
    same mistake existed in `examples/legacy/
    example_cesdm_to_pandapower_and_matpower.py`'s own docstring;
    fixed there too.
  - `examples/test.py` — an unlisted, broken scratch file (a literal
    `SyntaxError`, an unclosed parenthesis) left over from earlier
    interactive debugging, not a real example and not referenced
    anywhere — removed.
  - Confirmed clean otherwise: every example the README's table and
    `docs/importers/`/`docs/exporters/` reference by name exists, and
    every `.py` file actually in `examples/` is referenced from
    somewhere in the README or `docs/`.

### Changed

- **`docs/simple/` + `docs/detailed/` (19 files, 5441 lines) consolidated
  into a single `docs/guide/` (13 files, 3618 lines)** — requested
  directly: with 12 tested, runnable examples plus the README already
  covering "how to build a model" thoroughly, keeping two separate
  tutorial tiers on the same ground was pure duplicated-maintenance
  risk, not reader value (this exact duplication is what let
  `schemas/prosumer`/`schemas_v4`/`cesdm_resources` — none of which
  exist anywhere in the repository — go unnoticed for as long as they
  did, see the entries below). Removed entirely: the two
  step-by-step "building a model" tutorials
  (`docs/simple/02_building_a_model.md`,
  `docs/detailed/07_building_models.md`) and
  `docs/detailed/04b_how_to_use_cesdm_schema.md` (an 80-call raw-API
  tutorial, same duplication), all already covered by the README and
  `examples/`; `docs/detailed/00a_executive_summary.md` (near-verbatim
  restatement of the README's own "What is CESDM?"). Merged: the
  plain-language `docs/simple/00_what_is_cesdm.md` and
  `docs/detailed/01_introduction.md` into one
  `docs/guide/01_what_is_cesdm.md` (fixing an `ElectricalElectricalBus`
  typo found while merging). Everything else kept and renumbered into
  one sequence — `docs/guide/00_disclaimer.md` through
  `docs/guide/10_cesdm_toolbox.md`, plus `faq.md`/`glossary.md`. Every
  cross-reference (README, `schema_governance.md`,
  `schemas/SCHEMA_MANIFEST.yaml`, and the guide files' own links to
  each other) updated and verified with a full automated link check,
  not just assumed correct.
- **All FlexECO-related documentation removed**
  (`docs/tyndp_flexeco_field_mapping.md`, added last turn, plus a
  passing mention in the spatial-aggregation guide) — FlexECO-specific
  Python tooling (`tools/import_flexeco.py`,
  `tools/cesdm_yaml_to_flexeco.py`,
  `tools/cesdm_frictionless_to_flexeco.py`) deliberately left alone,
  since removing working import/export code is a different, larger
  decision than a documentation cleanup.
- **`docs/illustrations/cesdm_architecture.svg` updated** to show the
  object-oriented proxy API as its own layer between `CesdmModel` and
  the Build/Explore/Validate/Transform operations — the previous
  version predated the proxy API entirely. Verified programmatically
  (no bounding-box overlaps) and by rendering to PNG.
- **`docs/architecture/proxy_api.md` trimmed further** — asked
  directly whether it still had unnecessary detail for an end user;
  on a second pass, yes: the `AssetProxy` class's actual Python source
  (`__new__` implementation), internal/private method names
  (`_discover_view_map`, `connect_single_port`, `class_attributes`,
  `create_generation_unit_from_technology`, ...), a specific internal
  schema file path, and design-rationale prose in the limitations
  section were all implementation detail a user calling
  `gen.dispatch.x = y` never needs. Rewritten to describe behaviour
  only; every code example re-verified by running it.

- **Documentation prepared for release, and `doc/`/`docs/` consolidated
  into a single `docs/`** — requested directly: developer-facing
  narrative ("bugs found while building this", session references)
  didn't belong in user documentation, and having both a `doc/`
  (Sphinx) and `docs/` (plain Markdown) folder was confusing.
  `docs/architecture/proxy_api.md` rewritten to a clean design
  reference with no development-journal content; `schema_governance.md`
  had a handful of "this session"/incident-narrative references
  removed, keeping the underlying rules. `CHANGELOG.md` itself
  condensed from ~1800 lines to under 1000 by rewriting the
  accumulated `[Unreleased]` section into concise, categorized
  bullets, since a changelog documents *what changed*, not the
  debugging process that found it.

  `doc/`'s Sphinx build machinery (`conf.py`, `Makefile`, `index.rst`,
  `requirements.txt`) was dropped — confirmed unused first: no CI
  workflow builds or publishes it, and the README's own docs badge
  linked to a GitHub Pages URL that doesn't resolve. Its Markdown
  content moved into `docs/simple/` and `docs/detailed/` (same
  filenames, same relative structure), `doc/illustrations/` into
  `docs/illustrations/`, and three small, closely related stray files
  (`flexeco_roundtrip_fixes.md`, `tyndp_flexeco_value_precedence.md`,
  `tyndp_hydro_dispatch_attributes.md`) merged into one
  `docs/tyndp_flexeco_field_mapping.md`. Every cross-reference
  (README, `schema_governance.md`, `schemas/SCHEMA_MANIFEST.yaml`, and
  the moved files' own relative links to each other) updated and
  verified to actually resolve, not just assumed — a full,
  programmatic link check across every `.md` file in `docs/` and the
  README found and fixed one broken cross-directory link along the way.

  While re-reading the moved files for the narrative cleanup, also
  found and fixed: two more files (`docs/detailed/05_representation_views.md`,
  `docs/detailed/04a_schemas.md`) still using the pre-rename
  dot-separated attribute ids (`MACHINE.xd`, `AVR.SEXS.Ka`) from
  earlier in this changelog; an invalid enum value in one of
  `05_representation_views.md`'s own examples (`MACHINE_model:
  "subtransient"`, not one of the schema's real allowed values); and,
  while first attempting the dot-to-underscore substitution, two
  self-inflicted mistakes (a class name corrupted to
  `ControllerView.AVR_SEXS`, and a file-path example's `.yaml`
  extension corrupted to `_yaml`) caught by rereading the diff rather
  than assuming the substitution had landed correctly, and fixed
  before they could ship.

### Added

- **Object-oriented proxy API** (`cesdm.proxy`) as the primary,
  recommended way to build models: `AssetProxy` (a `str` subclass
  returned by every builder function) with `.dispatch`/`.powerflow`/
  `.topology`/`.dynamic`/`.avr`/`.governor`/`.pss`/etc. resolving
  lazily to a `ViewProxy` via the schema's own `view_family` field —
  no hardcoded view-class list in Python. Unknown attributes/relations
  raise immediately with a spelling suggestion instead of silently
  doing nothing. `model.asset(id)` wraps an existing entity;
  `asset_as(id, SpecificProxyClass)` gives the concrete type for
  static type-checking. `gen.connect(bus)` /
  `line.connect(bus1, bus2)` wire topology relations directly. See
  `docs/architecture/proxy_api.md`.
- **Analysis-dependent validation**: `model.validate_for_analysis(profile)`
  / `model.validate_for_analysis_or_raise(profile)` check fitness for
  a specific analysis (e.g. "optimal dispatch needs
  `variable_operating_cost` on every generator") against a YAML
  profile (`analysis_profiles/*.yaml`), independent of what the schema
  itself marks `required:`. Checks are entity-centric — a check names
  an attribute/relation and CESDM resolves which view it lives on
  automatically; `view_family` can be given explicitly for the rare
  ambiguous case. Split across a generic, schema-agnostic core
  (`ear/model/analysis_validation.py`, works on any EAR-based schema)
  and a thin CESDM addon (`cesdm/domain/model/analysis_validation.py`)
  that adds the view-resolution capability. See
  `docs/architecture/analysis_validation.md`.
- **Real IEEE Std 1110-2002 / IEEE Std 421.5-2016 / Kundur / PSS/E
  Model Library reference default values** for 113 of the
  `MACHINE_*`/`AVR_*`/`GOV_*`/`PSS_*` dynamic-simulation attributes,
  applied automatically on entity creation through any construction
  path (builder function or raw `add_entity`), independent of the
  schema's own `required:` flag.
- **`view_family`**: a new optional, inheritable schema class field
  identifying which representation-view family a class belongs to
  (`dispatch`, `topology`, `powerflow`, `dynamic`, `avr`, `governor`,
  `pss`, `planning`, `spatial`, `technical`), replacing hardcoded
  Python view-family lists with schema-driven resolution.
- RDF/OWL schema export, a central unit registry with QUDT alignment
  (partial — see `docs/architecture/schema_governance.md`),
  `model.summary()`, `model.get_effective_attribute_value(...)`.
- `cesdm-update-generated` console command regenerating the default
  library, generated builders, and typings in one call.
- `examples/example_import_tyndp_proxy_api.py`: the full TYNDP import
  pipeline (nodes, installed capacities, hydro/PHS composites,
  storage, demand, time-series profiles, NTC interconnectors) ported
  to the proxy API, with synthetic fixtures so it runs standalone.
- `LICENSE` (MIT) and `.gitignore`.

### Changed

- **Every dot-separated attribute id in the `MACHINE`/`AVR`/`GOV`/`PSS`/
  HVDC families renamed to underscore-separated** (`MACHINE.xd` →
  `MACHINE_xd`, `AVR.SEXS.Ka` → `AVR_SEXS_Ka`) so these ids work as
  plain Python identifiers/kwargs directly. The family-prefix
  disambiguation this naming exists for (many controller models reuse
  the same short IEEE symbol) is unchanged; only the separator
  character is.
- **`cesdm/domain/model/builders.py` reorganized around one rule**: a
  function belongs there only if it does something a single generated
  `add_<EntityClass>()` call can't (multi-entity/multi-view composite
  construction, or real decision-making). Read-only query/lookup
  functions (`get_dispatch_view`, `views_for_asset`, ...) moved to
  `accessors.py`; a couple of thin, redundant aliases removed.
- **`GeneratorType`/`ControllerView.AVR/GOV/PSS` view-family
  disambiguation**: `Generator.DynamicView.Subtransient` and every
  `ControllerView.AVR.*`/`GOV.*`/`PSS.*` class used to share one
  `view_family: dynamic`, so `.dynamic` could resolve to an arbitrary
  controller instead of the machine model. AVR/GOV/PSS now have their
  own `view_family`, so `.dynamic`, `.avr`, `.governor`, `.pss` are
  each independently and unambiguously resolvable.
- Every example in `examples/` rewritten to use the object-oriented
  proxy API; pre-conversion versions kept in `examples/legacy/` for
  comparison. README, `docs/getting_started.md`, and the Sphinx
  documentation under `doc/` rewritten accordingly, leading with the
  proxy API as the primary, recommended way to build a model.
- `tools/generate_typings.py` extended to cover the full generated
  API surface (builder return types, view proxies, analysis
  validation, mixin sources) so editor type-checking matches runtime
  behaviour.

### Fixed

- Several silent bugs in `create_generation_unit_from_technology` and
  the family-specific generator builders: incorrect routing between
  wind/solar/thermal/nuclear technologies, a duplicate dict key that
  silently discarded 4 of 5 view-id mappings, and a non-canonical
  default fuel carrier id (`carrier.natural_gas` →
  `carrier.fuel.fossil.gas.natural_gas`) that created an orphaned,
  wrongly-attached entity.
- `HydroGenerationUnit.drawsFromReservoir` was incorrectly
  `required: true` (run-of-river units have no reservoir by
  definition) — reverted to `required: false`.
- `AssetProxy` had no `__setattr__`, so `bus.name = "X"` silently
  became an inert, ordinary Python instance attribute instead of
  setting the actual model attribute — now raises on unknown
  names, mirroring `ViewProxy`.
- Most functions in `builders.py` (`create_demand_unit`,
  `create_transmission_line`, family-specific generator builders, and
  others) returned the generic `AssetProxy` instead of the entity's
  actual, specific generated proxy class; a few
  (`ensure_carrier`/`ensure_resource`/`ensure_technology`,
  `create_timestamp_series`, `create_profile`) computed the correctly
  typed proxy internally and then discarded it for a bare id string.
  All now return the specific type, verified with Pyright.
- `export_yaml`/`export_json`/`export_long_csv` crashed
  (`FileNotFoundError`) when given a bare filename with no directory
  component; now handled correctly.
- Two carrier-classification bugs found by diffing importer behaviour
  against the canonical carrier registry (non-canonical ids reaching
  the model instead of their canonical equivalents).
- `Model.ensure_entity()` returned the raw internal `Entity` object
  instead of a typed proxy; `AssetProxy` values leaking into stored
  entity data instead of being coerced back to plain strings on write.
- A confirmed correctness bug in `ear.model.entity_ops.
  _get_entity_and_class`: given a nonexistent entity id, it silently
  returned a stale class reference instead of raising, producing
  misleading error messages unrelated to the actual problem.
- Sphinx documentation (`doc/simple/`, `doc/detailed/`) referenced two
  schema directories (`schemas/prosumer`, `schemas_v4`) and one Python
  module (`cesdm_resources`) that did not exist anywhere in the
  repository, and described an internal role-classification mechanism
  (hardcoded class-name frozensets) that had since been replaced by a
  purely structural derivation. Corrected throughout, with every code
  example re-verified by actually running it.
- `CESDM_Schema_Reference.html` was stale (pre-rename attribute ids)
  and baked the generating machine's absolute filesystem path into the
  committed output; regenerated, and the generator fixed to show the
  schema version instead.


## [0.8.0] — entity/attribute/relation naming and description audit

A systematic pass over all 114 classes, 393 attributes, and 71
relations (naming-convention conformance, fuzzy-match near-duplicate
detection, description-completeness and -accuracy checks) — see
conversation history for the full methodology and false-positive
analysis (most fuzzy-matched "near duplicates" turned out to be
correct, consistent structured naming — `active_power_output`/
`reactive_power_output`, `maximum_X`/`minimum_X` pairs, IEEE
`T1`/`T2`/`T3` sequences — not naming problems).

### Removed
- **`storage_technology_category`**: a dead attribute whose description
  confidently claimed to be *"the single source of truth for import/
  export tool routing decisions"* — but was never referenced by any
  class or any Python code. `storage_technology_type` (described more
  modestly) is what `tools/
  import_flexeco.py` actually uses in practice (4 real call sites).
  Left in place, the unused one — reading more authoritative — was a
  real trap for the next reader. Removed rather than "finished," since
  there's no evidence the planned migration it described was ever
  picked back up.

### Fixed
- **`variable_operating_cost`'s description undersold its real scope**:
  worded as if exclusively for demand ("the marginal operational cost
  associated with providing the demand... for loads, this often
  represents...") when it's actually declared on `Generation.
  DispatchView`, `HydroGenerationUnit.DispatchView`,
  `HVDCLink.DispatchView`, and `Storage.DispatchView` too — a genuinely
  correct, generic, cross-domain cost attribute, just inaccurately
  documented as demand-only.
- **`pumping_efficiency`'s description referenced `storage_technology_
  category`'s now-removed enum values** (`"phs_closed_loop and
  phs_open_loop categories"`) — repointed at the attribute that's
  actually live (`storage_technology_type` value `"phs"`).
- `tests/test_naming_audit_fixes.py`: regression coverage for all
  three (including a check that no class anywhere still declares the
  removed attribute, not just that the registry no longer has it).

### Added
- `docs/architecture/schema_governance.md`: new naming-convention
  bullet documenting the ~130 `AVR.*`/`GOV.*`/`PSS.*`/`HVDC.*`/
  `MACHINE.*` attributes that deliberately don't follow snake_case
  (they match their source IEEE/PSS-E standard's own symbol notation,
  e.g. `AVR.SEXS.Ka`, `MACHINE.Td0_prime`) and the dot-namespacing this
  requires (many controller models reuse the same short symbol, so the
  model-family prefix avoids id collisions) — this was previously true
  but undocumented, so it looked like unexplained inconsistency to
  anyone who didn't already know why. Also flags, honestly, that the
  `provenance_ref` citation practice modeled well by `AVR.SEXS.Ka`
  (PSS/E Model Library citation + governing equation in the
  description) is applied to only ~5 of the 130 — real, unfinished
  work, not silently left looking like an oversight. Not attempted to
  fill in here: doing so correctly needs access to the actual source
  standards, and a fabricated citation would be worse than none.

## [0.7.0] — schema-driven view_family (proxy API resolution no longer hardcoded)

### Added
- **`view_family` — a new optional, inheritable class field** in the
  schema (`ear/entity_class.py`, parsed like `abstract`/`description`).
  Declared once on a view family's abstract root
  (`schemas/views/dispatch/OperationalDispatchView.yaml:
  view_family: dispatch`, and 9 more — see
  `docs/schema_layout.md`, "`view_family` (optional class field)", for
  the full table) and inherited by every concrete subclass through the
  normal resolution machinery. Unlike `abstract`, this field is
  designed to inherit (a real "is-a" categorization, not something
  becoming a subclass invalidates) — `ear/model/schema_loading.py`
  resolves it the same way as attributes/relations: child's own
  declared value wins, otherwise the first parent's resolved value,
  processed in topological order so every parent is already resolved
  by the time a child needs it.
- `cesdm.proxy.AssetProxy` now resolves `.dispatch`/`.powerflow`/
  `.topology`/etc. entirely from this schema field — `cesdm/proxy.py`
  no longer contains any hardcoded list of view-family names at all.
  Adding a new view family that "just works" as a property now only
  requires tagging one YAML file, not touching Python — proven with a
  from-scratch scratch-schema test
  (`test_new_view_family_works_with_zero_python_changes`) that defines
  an `EconomicView` family cesdm/proxy.py has never heard of and shows
  `asset.economic.irr = 0.08` resolving correctly.
- Two distinct, explicit failure modes in `AssetProxy._view()`: a
  keyword that isn't a real view family at all falls through to the
  generic "not a view, attribute, or relation" error (with a spelling
  suggestion); a keyword that *is* a real family but has no matching
  view class for a particular asset's class raises a more specific
  error naming the valid view classes for that asset instead (e.g.
  `bus.dynamic` — `ElectricalBus` has no dynamic-simulation view).
- `tests/test_view_family.py` (28 tests): every root/leaf class pair
  from the table above, both error modes, the typo-suggestion path,
  and the from-scratch new-family proof.

### Fixed
- **`_merge_common()` silently dropped any top-level YAML key it didn't
  explicitly know about** — it only ever forwarded `("description",
  "parents", "abstract")` from the raw parsed dict before `view_family`
  was added to that list. Every one of the 10 `view_family:` tags
  above initially resolved to `None` everywhere, including on the very
  class where it was declared, until this was traced back to this one
  line. A schema author adding *any* new top-level class metadata key
  in the future would hit the identical silent-drop failure mode
  without this fix, or without remembering to extend the same tuple by
  hand.
- **`AssetProxy._view()` could resolve to an abstract view class**
  instead of a concrete subclass when both declared a `representsAsset`
  relation targeting the same asset class with the same `view_family`
  (an abstract root and its concrete child can both legitimately do
  this) — `_discover_view_map()` doesn't filter out abstract classes,
  and the previous candidate-matching logic picked whichever came
  first. Found via the from-scratch `EconomicView` test above (its
  abstract root and concrete `Thing.EconomicView` subclass both
  targeted `Thing`); `ensure_view` would then instantiate the abstract
  class directly, which is never correct. Fixed by filtering abstract
  candidates out of both the existing-views and new-view-creation
  matching paths.

### Added
- `examples/example_import_tyndp_proxy_api.py`: a second TYNDP
  importer, rebuilt on the `AssetProxy`/`ViewProxy` object-oriented API
  instead of raw `add_entity`/`add_relation`/`add_attribute` calls —
  a real-world showcase of the proxy API against genuine complexity
  (technology classification, hydro reservoir and pumped-hydro
  composite pairing, capacity accumulation across repeated imports),
  not just toy examples. Reuses `example_import_tyndp.py`'s own
  classification functions and constants (`TECH_HIERARCHY`,
  `TYNDP_TECH_DATA`, `_generation_asset_class_for_type`, ...) directly
  for fidelity — only the entity-construction style changes; not a
  byte-for-byte port of the full ~1800-line original (see that file's
  module docstring for exact scope).
- `examples/sample_data/tyndp_sample_installed_capacities.csv`: a
  small, realistic, TYNDP-column-shaped synthetic fixture (nuclear,
  thermal, wind, solar, battery storage, plain reservoir hydro,
  closed-loop pumped hydro across two nodes) so the new importer runs
  and validates standalone, without needing the external TYNDP
  reference dataset.
- `tests/test_tyndp_proxy_api_importer.py` (10 tests): full pipeline
  validates against the schema; correct techno-economic defaults per
  technology; correct hydro reservoir/PHS composite wiring
  (`drawsFromReservoir`/`suppliesResourceTo`, machine_role
  reversible-vs-turbine); capacity accumulates correctly across
  repeated imports of the same source data.

### Fixed
- **`ear.model.entity_ops._get_entity_and_class`**: given a
  nonexistent entity id, silently returned `(None,
  self.classes[<cname>])` where `cname` was a *stale for-loop
  variable* left over from the failed search — not the actual entity's
  class (there wasn't one), but whichever class happened to be last in
  `self.entities`' iteration order. Every caller (`add_attribute`,
  `add_relation`) would then report a wildly misleading `"Unknown
  attribute/relation of <unrelated random class>"` error with no
  connection to the real problem. There was even dead code right below
  the buggy `return` (an unreachable `print(...)` and a commented-out
  `raise KeyError(...)`) showing a proper fix had been intended but
  never actually took effect. Found while building the TYNDP proxy-API
  importer above — a missing prerequisite entity
  (`domain.electricity`) produced an error blaming
  `TwoPort.TopologyView`, a completely unrelated class, before this
  was traced back to its real cause. Now raises a clear `KeyError`
  naming the actual missing entity id.
- `add_reservoir_storage`, `add_reservoir_hydro`, `add_phs_closed_loop`,
  `add_phs_open_loop` now also return `AssetProxy` (the last four
  high-level builders from the original proxy-API pass that were still
  returning plain strings) — same zero-risk change as the rest (`str`
  subclass), needed for the new TYNDP importer above to use the
  object-oriented API consistently for hydro composites too.
- **Test-collection failure with no editable install, environment-
  and collection-order-dependent**: reported by a user running `pytest`
  directly after unzipping (no `pip install -e .`) — exactly
  `tests/test_abstract_resolution.py`, `test_attribute_semantics.py`,
  and `test_generation_technology_routing.py` failed with
  `ModuleNotFoundError: No module named 'cesdm_toolbox'`, while ~150
  other test items collected fine. Root cause: `tests/
  test_hvdc_schema.py` (pre-existing) does its own `sys.path.insert(...)`
  as an import-time side effect, which persists in `sys.path` for the
  rest of the same pytest process — so every test file collected
  *after* it alphabetically benefited from that fix, while the three
  collected *before* "hvdc" (alphabetically) and lacking their own fix
  failed. Reproduced exactly (ran just those 3 files, then the full
  suite, both with no install) before fixing, and re-verified after.
  Fixed with a single `conftest.py` at the repo root, which pytest
  imports unconditionally before collecting *any* test file regardless
  of alphabetical order — the standard, robust solution, replacing the
  fragile "whichever file happens to be collected first must fix
  sys.path for everyone" situation entirely.
- `tests/test_pypsa_default_library_mapping.py`: a missing `numpy`
  (an optional dependency, not installed by default) caused a hard
  collection *error* that aborted collecting every other test file in
  the run (`Interrupted: N errors during collection`), not just a
  skip of that one file. Added `pytest.importorskip("numpy")` so it
  degrades to a graceful per-file skip instead.

_Note: the proxy API and generation-technology-routing bugfix entries
below were originally Python/toolbox-only changes with no schema YAML
changes of their own, so they didn't warrant their own version bump at
the time. They ended up bundled into 0.7.0 together with the
view_family schema change above them in this file, once that shipped —
not because they touch the schema themselves._

### Added
- `cesdm/proxy.py`: `AssetProxy` and `ViewProxy` — an object-oriented
  ergonomics layer over the existing low-level EAR API, in response to
  a detailed API-design proposal. `AssetProxy` is a `str` **subclass**,
  so it's usable anywhere a plain entity id was already accepted (dict
  keys, `==`, passed to any existing `model.*` method) — making every
  builder that now returns one instead of a bare string a
  zero-risk, 100%-backward-compatible change. Verified against the
  full existing test suite and every example script with no changes
  needed elsewhere.
  - `asset.dispatch` / `.powerflow` / `.dynamic` / `.topology` /
    `.planning` / `.spatial` / `.technical` / `.results` resolve to a
    `ViewProxy` for the matching representation view, created lazily
    via the schema's own `representsAsset` relationships
    (`model._discover_view_map()`) if it doesn't exist yet.
  - `ViewProxy` attribute get/set is validated against the view
    class's real attributes/relations; an unknown name raises
    immediately with a `difflib.get_close_matches` spelling
    suggestion, instead of silently doing nothing.
  - Setting a plain scalar auto-attaches the attribute's unit from
    `schemas/units/units.yaml` only when the attribute has exactly one
    registered valid unit; ambiguous attributes (e.g. `reservoir_volume`,
    which legitimately accepts GWh/TWh/hm3/m3) are left unit-less
    rather than guessed.
  - `asset.connect(bus)` (single-port) / `asset.connect(bus1, bus2)`
    (two-port) wrap `connect_single_port`/`connect_two_port`.
- `model.add_generator(id=, technology=, bus=, ...)`: clean top-level
  entry point wrapping `create_generation_unit_from_technology`, returning
  an `AssetProxy`.
- `model.asset(entity_id)`: wrap an already-existing entity (created
  via the low-level API, or an untouched builder) in an `AssetProxy`
  after the fact.
- `docs/architecture/proxy_api.md`: full design writeup, including
  what's deliberately *not* built yet (fluent method-chaining,
  `gen.static.*` metadata with no schema home yet, short
  library-hiding technology strings, importer/exporter renames,
  `model.summary()`/`model.find()`) — see the conversation history for
  the full 10-point proposal this responds to.
- `tests/test_proxy_api.py` (14 tests) and
  `tests/test_generation_technology_routing.py` (7 tests).

### Fixed
- **Three related, silent bugs in `create_generation_unit_from_technology`**,
  all found by hand-testing the closest existing analog to "smart
  defaults from technology" before designing the proxy layer above:
  1. Every non-hydro generation technology (wind, solar, thermal,
     nuclear) silently routed through `add_solar_generator()`
     regardless of what was requested. Root cause:
     `generation_asset_class_from_technology()` correctly returns the
     same CESDM entity class (`"GenerationUnit"`) for all four — the
     schema deliberately has no separate subclasses for them — but the
     routing code compared against that value across four separate
     `if cls == "GenerationUnit":` branches, so only the first was
     ever reachable. Fixed with a new, separate
     `_generator_family_from_technology()` classifier used only for
     builder routing, with no schema meaning of its own.
  2. `_view_id()`'s id-prefix dict had 5 entries for the literal key
     `"Generation.DispatchView"` (one intended per technology family);
     dict literals silently let later duplicate keys win, so every
     non-hydro generator's auto-generated view id claimed to be
     `"solar_dispatch_view"` regardless of its real technology.
     Collapsed to one entry, since the view class genuinely is shared
     across these technologies (only hydro has its own dispatch-view
     class).
  3. The thermal branch always passed
     `fuel_carrier_id=input_carrier_id` (`None` unless the caller
     explicitly supplied one), clobbering `add_thermal_generator`'s
     own sensible default (`"carrier.natural_gas"`) every time it was
     reached through the technology-routing entry point.
  - `dispatch_view_class_for_asset()` had the same duplicate-key/
    duplicate-branch pattern (5x `"GenerationUnit"` dict key, repeated
    identical `if` conditions) — harmless here since every duplicate
    mapped to the same value, but cleaned up as the same class of
    copy-paste residue as bugs 1-2 above.

## [0.6.0] — QUDT unit alignment (partial) and RDF/OWL schema export

### Added
- `qudt_iri` and `qudt_status` fields on every entry in `schemas/units/
  units.yaml`. `qudt_status` is one of `verified` (checked against the
  live QUDT vocabulary — currently `MW`→`unit:MegaW`,
  `MWh`→`unit:MegaW-HR`, `kV`→`unit:KiloV`, `kW`→`unit:KiloW`, 4 of
  47), `unverified` (plausibly has a QUDT equivalent, not yet checked
  — most of the 47), or `no_qudt_equivalent` (`date`, `Timestamp / time
  index` — definitionally outside QUDT's scope). Deliberately not a
  complete mapping: pattern-guessing the remaining unverified IRIs
  would produce a mapping that *looks* authoritative while potentially
  being wrong, which is worse than leaving them honestly unmapped.
- `CesdmModel.export_rdf_schema(path, namespace=None)`
  (`cesdm/domain/model/rdf_export.py`): exports the loaded schema
  (classes, attributes, relations — not instance data) as an OWL
  ontology in Turtle syntax. Classes → `owl:Class` with
  `rdfs:subClassOf` from the inheritance graph; relations →
  `owl:ObjectProperty`; attributes → `owl:DatatypeProperty`, with a
  `cesdm:hasUnit` annotation pointing at the real QUDT IRI when an
  attribute has exactly one registered unit and that unit's
  `qudt_status` is `verified`. Pure string generation — no new runtime
  dependency for the export itself.
- **The export namespace (`CESDM_ONTOLOGY_NAMESPACE`) is explicitly
  provisional**, using the project's existing published GitHub Pages
  docs URL as a placeholder rather than inventing a new one. Minting a
  permanent identifier is a decision for the schema's maintainers, not
  something to decide unilaterally; re-basing later is a one-constant
  change.
- `tests/test_rdf_export.py`: validates the generated Turtle actually
  *parses* (via `rdflib`, `pytest.importorskip`'d), not just that
  something was written — checks class/property counts match the
  loaded schema exactly, `rdfs:subClassOf` edges match the inheritance
  graph (including a dot-namespaced class name, to prove the
  full-IRI-not-prefixed-name approach sidesteps Turtle's PN_LOCAL
  restrictions), the verified QUDT annotation is present where
  expected, and absent for multi-unit/unverified attributes.
- `rdf` and `pydantic` extras in `pyproject.toml` (the latter was
  already a working lazy-imported optional dependency for
  `build_pydantic_models()`; formalized here for discoverability).
- `docs/architecture/schema_governance.md`: new "Formal ontology
  alignment (partial)" section documenting both limitations above
  explicitly, replacing the old "No RDF/OWL alignment yet" non-goal.

## [0.5.0] — central unit registry

### Added
- `schemas/units/units.yaml`: the single source of truth for every
  unit used anywhere in the schema tree — the structural fix for "unit
  spellings are canonical today, but nothing stops the next
  contributor from introducing a new inconsistent spelling tomorrow"
  (the exact problem the 51→47-string cleanup earlier in this file had
  to fix by hand). Same registry-folder pattern as `attributes/` and
  `relations/` (auto-discovered, no `_index.yaml`). Each of the 47
  entries has a `symbol`, a `quantity_kind` (informational dimensional
  tag — `power`, `energy`, `angle`, `cost_rate`, ... — not currently
  used for automated dimensional-consistency checking), and a
  `description`.
- `load_classes_from_yaml` now validates every attribute's
  `unit.constraints.enum` values against this registry at load time:
  an attribute referencing an unregistered unit string fails to load
  immediately with a clear error, rather than silently introducing
  drift. Verified with a negative test that deliberately introduces an
  unregistered unit and confirms the load fails.
- `Model.unit_info(symbol)`: look up a unit's registry entry from code.
- `tests/test_unit_registry.py`: regression coverage (registry loads,
  every existing attribute's units are registered, the enforcement
  actually fires on a bad unit, `units.yaml` itself is correctly
  excluded from entity-class scanning).
- `docs/architecture/schema_governance.md`: new "Central unit
  registry" section; updated the "Unit strings must be spelled
  consistently" naming-convention bullet (now enforced, not just
  documented) and removed the now-resolved "no central unit registry
  yet" non-goal.

### Fixed
- **Stray top-level `constraints:` keys, silently ignored by the
  loader** (constraints are only read from `value.constraints` or
  `unit.constraints` — see `ear/attribute_def.py`): found on 7
  attributes. Five (`initial_state_of_charge`, `maximum_state_of_charge`,
  `minimum_state_of_charge`, `discount_rate`, `salvage_fraction_value`)
  had a genuinely-intended `maximum: 1.0` bound trapped there that had
  therefore **never actually been enforced** — moved into
  `value.constraints` so it's real now. `maximum_state_of_charge` had
  its entire description trapped there too (moved to a proper
  `description:` key). The other two (`fixed_operating_cost`,
  `investment_cost`) were pure dead duplicates of already-correct
  content a few lines below (their unit enum) — removed. Also fixed
  `salvage_fraction_value`'s stray block containing a typo
  (`minnimum`) that made the dead content even harder to notice was
  dead. `tests/test_attribute_semantics.py`
  guards against this pattern recurring anywhere in either schema tree.
- **3 attributes with no description at all**: `maximum_state_of_charge`
  (recovered from the stray `constraints:` key above),
  `converter_rating_from`/`converter_rating_to` (recovered from
  `HVDC.converter_rating_from`/`HVDC.converter_rating_to` — orphaned
  near-duplicates with the correct description text but never actually
  referenced by any class; deleted after transplanting their text into
  the live, referenced attributes). `test_every_attribute_has_a_
  description` guards against this recurring.
- **Two categorical string attributes now have real closed enums**:
  `carrier_group` (`electricity`/`gas`/`heat`/`hydrogen`/`water`,
  mirroring CESDM's own fixed set of per-carrier Bus node types) and
  `resource_group` (`renewable`/`hydro`/`geothermal`/`environmental`,
  exactly matching what its own description already stated). Both were
  previously unconstrained free strings.
- **Five other categorical string attributes documented as
  intentionally open, not force-enumerated**: `carrier_type`,
  `generator_technology_type`, `resource_type`, `storage_technology_type`
  each got a recommended-vocabulary description instead of a hard
  `enum:` — checked `storage_technology_type` against its actual
  consumer (`tools/import_flexeco.py`) first and confirmed it's used
  as a soft pass-through string, not matched against a fixed set, so a
  hard enum would have risked rejecting values the code already
  handles correctly. `demand_type` was left honestly flagged as
  too ambiguous to document a vocabulary for in good faith (zero usage
  evidence anywhere in this toolbox to disambiguate sector-based vs.
  flexibility-based classification) rather than guessing.
  `solver_status`'s pre-existing enum (the one categorical attribute
  that already had one) was restyled from a shorthand `value.enum`
  form to the dominant `value.constraints.enum` form used everywhere
  else, for consistency — both forms are parsed identically, so this
  is style-only.
- `docs/architecture/schema_governance.md`: new "Attribute and relation
  naming conventions" section codifying the unit-suffix, unit-spelling,
  comma-crammed-enum, categorical-vocabulary, and stray-top-level-
  constraints rules, plus a
  central-unit-registry non-goal noting the residual risk that remains
  even after this pass (nothing yet stops a *new* spelling variant).

- **Unit-string vocabulary inconsistency**: the schema has no central
  unit registry — every attribute declares its own free-text
  `unit.constraints.enum` — and the same physical unit had drifted
  into multiple incompatible spellings across 360 attributes:
  - `pu` / `p.u.` (per-unit) → canonicalized to `pu` (the pre-existing,
    ~60-attribute-strong spelling).
  - `deg` / `degree` / `degrees` / `decimal degrees` (angle) → `deg`.
  - `percent` / `%` (percentage) → `%`.
  - `Fraction` / `Fraction (0-1)` / `Fraction 0-1` / `-` (dimensionless
    0-1 ratio) → `fraction`.
  - `tCO2/MWh` / `tCO2_per_MWh` (CO2 intensity) → `tCO2/MWh` (matching
    the slash-notation convention used everywhere else in the registry:
    `MU/MWh`, `CHF/tCO2`, `MWh/year`, ...).
  - `investment_cost` and `fixed_operating_cost`: their unit enum was a
    single comma-separated string (`"MU/kW, MU/MW, MU/unit"`) instead
    of a proper list of three enum values — split correctly.
  - `maximum_downward_adjustment`/`maximum_upward_adjustment`: same
    comma-crammed-string bug (`"kW / MW"`) — split into `[kW, MW]`.
  - `flexibility_time_resolution`: fixed a typo baked into the unit
    string itself (`"Houes / minutes"` → `[h, min]`).
  - `conversion_rules`: had `unit.constraints.enum: [List]` — not a
    unit at all, describes the value's data shape, which `value.type`
    already captures. Removed the (incorrect) `unit:` block entirely.
  - `tests/test_unit_vocabulary_consistency.py`: regression coverage
    guarding against these specific spellings reappearing, plus a
    general check that no unit enum value contains a comma.
- **Naming-convention inconsistency in the power-flow/dynamics result
  attributes**: they embedded
  their unit as a suffix in the attribute id itself (`active_power_
  flow_from_mw`, `voltage_magnitude_pu`, ...) — inconsistent with the
  dominant pre-existing convention of keeping the unit solely in the
  separate `unit:` field (`nominal_power_capacity`, `reactive_power_
  demand`, ...). Renamed 18 attributes to drop the suffix and match the
  dominant convention: `active_power_flow_from`, `reactive_power_flow_
  from`, `active_power_flow_to`, `reactive_power_flow_to`, `active_
  power_loss`, `reactive_power_loss`, `active_power_output`, `reactive_
  power_output`, `voltage_magnitude`, `average_voltage_magnitude`,
  `min_voltage_magnitude`, `max_voltage_magnitude`, `max_speed_
  deviation`, `current_magnitude`, `voltage_angle`, `max_rotor_angle_
  deviation`. Two (`active_power_injection_mw`, `reactive_power_
  injection_mvar`) were renamed to `net_active_power_injection` /
  `net_reactive_power_injection` instead of reusing the pre-existing
  bare `active_power_injection`/`reactive_power_injection` ids, since
  those are genuinely shunt-specific (MATPOWER Gs/Bs and pandapower
  sign-convention semantics baked into their description) rather than
  a generic bus-injection concept — verified before reusing rather
  than assumed.
- **Cross-tree attribute/relation duplication** (the same DRY issue
  already fixed for classes via `extends`, never applied to the
  registries): `schemas_agentbased/attributes/attributes.yaml` and
  `schemas_agentbased/relations/relations.yaml` independently
  redeclared 34 attributes and 10 relations already defined in the
  core `schemas/` registries — all verified byte-identical (after
  whitespace normalization) except 5 that had drifted to a stale unit
  spelling the unit-canonicalization above just fixed in the core copy
  only, which surfaced as a real `ValueError: Duplicate attribute id
  ... with different definitions` when loading both trees together.
  Removed all 44 duplicate blocks from the agent-based registries;
  they're already available via `extends: [../schemas]`. Verified
  `build_model_from_yaml("schemas_agentbased")` alone and
  `build_model_from_yaml(["schemas", "schemas_agentbased"])` still
  produce identical 114-class models.
- Investigated but **left alone**: `nominal_power_capacity` vs.
  `rated_electrical_power_capacity` vs. `supply_capacity` vs.
  `thermal_capacity` vs. `thermal_capacity_rating` looked like a
  cluster of near-synonymous "capacity" attributes. Checked which
  classes declare each: they're scoped to different roles (general
  dispatch capacity, a `ConverterType` technology-template rating, an
  external-supply boundary condition, nuclear thermal vs. electrical
  output, and a transmission branch's MVA rating respectively) — a
  defensible, if not optimally named, set of distinct concepts rather
  than true duplication. Not merged.

- **Severe pre-existing bug in `resolve_inheritance()`**: `abstract` was
  incorrectly propagated from a parent class to every descendant, no
  matter how many inheritance levels down. Since nearly every class in
  the tree eventually traces back to an abstract root
  (`SemanticEntity`, `EnergyAssetInstance`, ...), this meant **all 103
  classes** resolved to `abstract=True` after loading — including
  plain concrete leaf classes like `GenerationUnit` and `ElectricalBus`.
  Being a subclass of an abstract base does not make the subclass
  abstract; that is the entire point of an abstract base class.
  - **Real, silent impact**: `build_pydantic_models()` only registers a
    class in `self.py_models` when `not c.abstract` — so `py_models`
    was always empty, for every class, with no error raised. Verified
    broken before the fix, verified fixed after (see
    `tests/test_abstract_resolution.py`).
  - A previous developer had already independently discovered and
    worked around this exact bug in `cesdm/domain/model/frictionless.py`
    (~40 lines re-deriving "directly abstract" by re-parsing raw YAML
    or a parents-graph heuristic, with a comment explaining why
    `cdef.abstract` couldn't be trusted) — but the workaround was never
    applied at the root cause, so every other consumer of `.abstract`
    stayed silently broken independently. Removed the workaround now
    that `cdef.abstract` is directly correct.
  - Found via `tools/schema_audit.py` (see "Added" below): the
    "orphaned classes" check initially reported 0 findings across 103
    classes, which was itself the tell — every class being (wrongly)
    abstract meant the orphan-detection logic was skipping all of them.
  - Only 20 of 103 classes are genuinely abstract after the fix — a
    plausible number for actual abstract bases (`SemanticEntity`,
    `EnergyAssetInstance`, `RepresentationView`, `ResultView`,
    `RunRecord`, the `ControllerView` family roots, ...).

### Added
- `tools/schema_audit.py`: static-analysis tool that cross-references
  the schema tree (declared relations/attributes, class hierarchy,
  `SCHEMA_MANIFEST.yaml` stability tiers) against actual usage in
  `examples/`, `tests/`, `tools/`, and the `ear`/`cesdm` library source,
  producing `docs/architecture/schema_audit_report.md`. Surfaces: dead
  relations/attributes, orphaned (never-instantiated) concrete classes,
  relations declared on an over-broad base class (the
  `StorageUnit.storesResource` pattern, generalized into a repeatable
  check), and `stable`-tier classes with zero usage evidence. Not a
  sound analysis — literal-argument AST scan only — see the tool's own
  docstring and the documented `hasInputResource` false positive before
  acting on any finding.
- `tests/test_abstract_resolution.py`: regression coverage for the
  fix above.

- `SCHEMA_MANIFEST.yaml` in `schemas/` and `schemas_agentbased/`:
  formalizes a version number and a per-family stability tier
  (`stable` / `experimental` / `deprecated`) for the schema tree.
  Read by `ear.schema_manifest.SchemaManifest`.
- `_cesdm_meta.schema_version` header written by
  `export_yaml_hierarchical`; `import_yaml_hierarchical` now warns
  (does not fail) if a model is imported against a schema tree with a
  different major version.
- `docs/architecture/schema_governance.md`: versioning policy,
  stability-tier definitions, and the change-proposal process for
  schema edits.
- `docs/architecture/package_layout.md`: documents the split of
  `ear_toolbox.py` / `cesdm_toolbox.py` into the `ear`/`cesdm`
  packages.
- `tests/test_schema_filenames_match_class_names.py`: enforces that
  every schema file's filename matches its declared `name:` field, so
  the mismatches described below can't silently recur.
- `SchemaManifest.extends`: a schema tree can declare
  `extends: [../schemas]` to depend on and auto-load another schema
  tree, instead of forking its classes. See "Removed" below and
  `docs/schema_layout.md` ("Cross-tree dependencies").
- Registry-folder consistency check in `load_classes_from_yaml`:
  `attributes/` and `relations/` folders now fail fast (`ValueError`)
  if they contain a `*.yaml` file that isn't listed in that folder's
  `_index.yaml`, instead of silently ignoring it. Covered by
  `tests/test_registry_index_consistency.py`.

### Changed
- `cesdm.domain.model.discovery._build_view_index` now iterates
  view classes in sorted order instead of raw `frozenset` order. This
  is a **behavior fix, not a schema change**: the previous ordering
  depended on Python's per-process string-hash randomization, so the
  key order of `representations:` blocks in hierarchical YAML exports
  could vary between runs of the *same* model. Data/content is
  unaffected; only serialization order is now deterministic.
- Renamed 22 files under `schemas/views/{dispatch,dynamics,powerflow,
  technical,topology}/` to match their declared `name:` field (e.g.
  `HydroReservoirDispatchView.yaml` → `ReservoirStorageUnit.DispatchView.yaml`,
  `NodalConnectionView.yaml` → `SinglePort.TopologyView.yaml`). No class
  identity, inheritance, or loaded-model behavior changed — this is a
  filename-only fix for grep-ability; see `docs/schema_layout.md`.
- Nested `schemas/controllers/*.yaml` into `AVR/`, `GOV/`, and `PSS/`
  subdirectories by controller family, consistent with how `views/` is
  already subdivided by analysis domain. `ControllerView.yaml` (the
  family-less abstract base) stays at `controllers/` root. No class
  identity or loaded-model behavior changed — the loader scans the
  schema tree recursively regardless of nesting depth.

### Removed
- `schemas_agentbased/assets/_index.yaml`: referenced non-existent
  subdirectories (`Agents/`, `Assets/`, `Representations/`) and files
  (`DemandAsset.yaml`, `StorageAsset.yaml`, `SupplyAsset.yaml`) that
  don't exist anywhere in the repository, and listed one file three
  times. It was also never actually read by the loader — only
  `attributes/_index.yaml` and `relations/_index.yaml` are consulted
  (see `ear/model/schema_loading.py`) — so it was pure stale
  documentation actively describing a layout that no longer (or never
  did) match reality. Deleted rather than fixed, since a corrected
  version would still be dead weight.
- 8 duplicate class files from `schemas_agentbased/`
  (`assets/EnergyAssetInstance.yaml`, `core/SystemAsset.yaml`,
  `core/SemanticEntity.yaml`, `carrier/EnergyCarrier.yaml`,
  `carrier/NaturalResource.yaml`, `profiles/Profile.yaml`,
  `profiles/TimestampSeries.yaml`, `system/GeographicalRegion.yaml`;
  the emptied `core/`, `carrier/`, `profiles/`, `system/`
  subdirectories were also removed). 7 were byte-identical copies of
  the corresponding file in `schemas/`; `core/SemanticEntity.yaml` had
  already drifted (reworded description, same meaning). They existed
  only so `schemas_agentbased/` could be loaded standalone; that
  capability is now provided by `extends: [../schemas]` in
  `schemas_agentbased/SCHEMA_MANIFEST.yaml` instead, with a single
  source of truth for the shared classes. Verified that
  `build_model_from_yaml("schemas_agentbased")` alone and
  `build_model_from_yaml(["schemas", "schemas_agentbased"])` (as
  `examples/example_agent_based_prosumer_model.py` already did) now
  produce identical 104-class models.
- The `_index.yaml`-based curated file-list mechanism for the
  `attributes/` and `relations/` registry folders. These two folders
  are now auto-discovered the same way every other schema folder is
  (every `*.yaml` file present is picked up, no registration step).
  The ordering `_index.yaml`'s `imports:` list provided was never
  functionally meaningful — a duplicate registry id across files was
  always a hard error, never "last file wins" — so requiring a second,
  separately-maintained file added drift risk (exactly what happened
  to `schemas_agentbased/assets/_index.yaml`, see 0.1.0 entry below)
  for no real benefit. The one property that did matter — a registry
  id must not be defined twice with conflicting specs — is still
  enforced by `ear.model.schema_loading._load_registry_from_folder`.
  Deleted `schemas/attributes/_index.yaml`,
  `schemas/relations/_index.yaml`,
  `schemas_agentbased/attributes/_index.yaml`,
  `schemas_agentbased/relations/_index.yaml`.
  `tests/test_registry_index_consistency.py` (which tested the removed
  fail-fast behavior) replaced by `tests/test_registry_auto_discovery.py`.

## [0.4.0] — reverted

Briefly narrowed `StorageUnit.storesResource` to `ReservoirStorageUnit`
only (see rationale that was here). Reverted at the requester's
direction before this version was ever released — `StorageUnit` and
`ReservoirStorageUnit` are back to their `0.3.0` state, both declaring
`storesCarrier` and `storesResource`. Noted here rather than silently
deleted so the reasoning isn't accidentally re-proposed unaware it was
already considered: the concern was real (every non-reservoir
`StorageUnit` instance inherits an optional relation it never uses),
but was judged not worth the breaking change to a `stable`-tier class
for now.

## [0.3.0] — standard power-flow result coverage

### Added
- `ElectricalBus.PowerFlowResultView`: `voltage_angle_deg`,
  `active_power_injection_mw`, `reactive_power_injection_mvar` (in
  addition to the existing `voltage_magnitude_pu`/average/min/max).
  `hasVoltageAngleProfile` relation.
- `TransmissionElement.PowerFlowResultView`: `active_power_flow_from_mw`,
  `reactive_power_flow_from_mvar`, `active_power_flow_to_mw`,
  `reactive_power_flow_to_mvar` (flow differs at each end due to
  losses/charging, hence separate from/to values), `active_power_loss_mw`,
  `reactive_power_loss_mvar`, `current_magnitude_ka`, plain
  `loading_percent` (alongside the existing average/max). Attribute
  names anchored to this toolbox's own pandapower integration's
  `res_line`/`res_trafo` result-table convention
  (`vm_pu`/`va_degree`/`p_from_mw`/... in pandapower) rather than
  invented independently. `hasActivePowerLossProfile` relation.
- `schemas/views/results/powerflow/GenerationUnit.PowerFlowResultView.yaml`
  (new leaf class): `active_power_output_mw`, `reactive_power_output_mvar`
  — the power-flow-solved generator output (reactive power at a PV bus,
  and active power at the slack bus, are solved by the power flow, not
  given as input, unlike at a plain PQ-dispatched generator).
  `hasActivePowerOutputProfile`/`hasReactivePowerOutputProfile` relations.
- `PowerFlowRunRecord.hasTimestampSeries` (optional, unlike
  `DispatchRunRecord`'s required one): its presence/absence is now the
  explicit signal for whether a power-flow run is a single-snapshot
  solve or a time-series ("quasi-steady-state") study — see "Changed"
  below.

### Changed
- **Made the single-snapshot vs. time-series distinction explicit**
  for power-flow results, rather than leaving both cases folded into
  one ambiguous attribute set. Previously
  `ElectricalBus.PowerFlowResultView` only had `average/min/max`
  attributes, which are meaningless for the single-snapshot case (the
  most common kind of power-flow study, and what this toolbox's own
  pandapower/MATPOWER integrations solve via one `runpp()`/`PYPOWER`
  call). Every power-flow result view now has plain snapshot-value
  attributes (`voltage_magnitude_pu`, `loading_percent`, ...) that are
  always the primary values; the average/min/max attributes and
  Profile relations are populated only when the producing
  `PowerFlowRunRecord.hasTimestampSeries` is set.

All additions are optional attributes/relations and one new leaf
class — purely additive, no renames or removals — hence a MINOR bump
rather than the MAJOR a breaking change would need.

## [0.2.0] — result-view restructuring

### Added
- `schemas/system/RunRecord.yaml`: abstract provenance base, analogous
  to `EnergyAssetInstance` for assets. `DispatchRunRecord` (existing,
  re-parented), `PowerFlowRunRecord`, and `DynamicRunRecord` (both new)
  are its concrete subclasses. `RunRecord.hasInputRun` links a run to
  the upstream run whose output it used as input, making chained
  multi-stage workflows (dispatch → power-flow → dynamics)
  traversable end-to-end.
- `schemas/views/results/ResultView.yaml`: abstract base shared by all
  result-view families, declaring `hasRunRecord` (a real relation,
  target `RunRecord`) so result views from different runs — and
  different analysis domains — can coexist on the same asset. Each
  domain's abstract result-view base narrows `hasRunRecord`'s target
  to its own `RunRecord` subclass.
- `schemas/views/results/powerflow/`: `PowerFlowResultView` (abstract),
  `ElectricalBus.PowerFlowResultView` (voltage magnitude outcomes),
  `TransmissionElement.PowerFlowResultView` (loading and losses,
  covers TransmissionLine/Transformer/Interconnector).
- `schemas/views/results/dynamics/`: `DynamicResultView` (abstract),
  `Generator.DynamicResultView` (rotor-angle/speed-deviation outcomes
  of a transient stability or contingency simulation).
- `hasRunRecord`, `hasInputRun`, `hasVoltageMagnitudeProfile`,
  `hasLoadingProfile`, `hasRotorAngleProfile`, `hasSpeedDeviationProfile`
  relations; `schemas/attributes/results.yaml` (new modular attribute
  file, registered in `attributes/_index.yaml`) for the power-flow and
  dynamics run/result attributes.
- `tests/test_view_only_asset_export.py`: regression coverage for the
  export bug described below.
- New per-domain stability entries `views/results/dispatch`,
  `views/results/powerflow`, `views/results/dynamics` (all
  `experimental`) in `SCHEMA_MANIFEST.yaml`, replacing the single
  flat `views/results` entry.

### Changed
- **`schemas/views/results/` is now subdivided by analysis domain**
  (`dispatch/`, `powerflow/`, `dynamics/`), mirroring how the input
  views under `schemas/views/` are already split. Previously every
  result view inherited from `DispatchResultView` regardless of what
  kind of study produced it — there was no schema-level place for
  power-flow or dynamics results at all.
- Renamed and moved the 5 existing concrete result-view classes to
  match the dot-namespaced convention and their new location:
  - `GenerationResultView` → `views/results/dispatch/GenerationUnit.DispatchResultView.yaml`
  - `StorageResultView` → `views/results/dispatch/StorageUnit.DispatchResultView.yaml`
  - `DemandResultView` → `views/results/dispatch/DemandUnit.DispatchResultView.yaml`
  - `InterconnectorResultView` → `views/results/dispatch/TransmissionElement.DispatchResultView.yaml`
    (renamed to its actual shared parent class, since it targets both
    `Interconnector` and `TransmissionLine`)
  - `NodalPriceResultView` → `views/results/dispatch/NetworkNode.DispatchResultView.yaml`

  **This is a breaking rename** (class identity, not just filename).
  `results/` was tagged `experimental`, so this is within the churn
  that tier signals; bumped to 0.2.0 (pre-1.0, so a breaking change is
  a MINOR bump per common semver practice) rather than 1.0.0.
- Moved `DispatchResultView` itself from `views/dispatch/` (an
  *input*-view folder) to `views/results/dispatch/` — it was a result
  view misplaced among input views the whole time, which is arguably
  the clearest sign the old flat structure was hiding this asymmetry.
  Re-parented from `RepresentationView` directly to the new
  `ResultView`.
- `DispatchRunRecord`: re-parented from `SemanticEntity` to the new
  `RunRecord`; its own `run_timestamp` attribute declaration removed
  (now inherited).
- **`run_ref` attribute replaced by the `hasRunRecord` relation** on
  all result views. `run_ref` was a plain string attribute with no
  referential integrity; a proper relation (`hasDispatchRun`, target
  `DispatchRunRecord`) already existed in `relations/relations.yaml`
  but was never actually used by any concrete result-view class — the
  five concrete views all used `run_ref` instead. `hasDispatchRun` is
  removed (superseded, was unused) in favor of the generic
  `hasRunRecord` declared once on `ResultView`.

### Fixed
- **Data-loss bug in `export_yaml_hierarchical`**: an asset with no
  direct attributes or relations of its own — the normal shape for an
  asset whose only real content lives in an attached representation
  view, e.g. exactly the `GenerationUnit` + `GenerationUnit.
  DispatchResultView` pattern this restructuring is built around — was
  silently dropped from the hierarchical YAML export entirely, views
  and all. The empty-block check ran *before* the code looked up and
  attached the asset's views; reordered so views are attached first,
  and the entity is only skipped if it has neither its own
  attributes/relations nor any attached views. Found while validating
  this change against a real chained dispatch → power-flow → dynamics
  scenario; unrelated to the results restructuring itself but was
  masking the exact case this feature is meant to support. Covered by
  `tests/test_view_only_asset_export.py`.

## [0.1.0] — baseline

Initial schema tree as delivered by the SWEET-CoSi CESDM prototype:
core structural classes, electricity/gas/heat/hydrogen/water assets and
nodes, representation views (topology/dispatch/power-flow/dynamics/...),
IEEE controller model schemas, and the agent-based prosumer extension.
Not retroactively versioned family-by-family — treated as the `0.1.0`
starting point for all families going forward.

## Schema-driven `add_<entity>` convenience API

- Every concrete class in the loaded CESDM schema is now exposed lazily as an
  `add_<snake_case_class_name>(entity_id, *, ...)` method on `CesdmModel`.
- Required inherited attributes and relations are required keyword-only
  arguments in the generated, introspectable Python signature.
- Optional attributes and relations default to `None`; multi-target relations
  accept iterables.
- Schema field names that are not valid Python identifiers are deterministically
  normalized with underscores.
- Generated methods validate all writes through the existing EAR schema-safe
  attribute and relation APIs and return an `AssetProxy`.
- `available_add_methods()` lists all generated method/class mappings.
