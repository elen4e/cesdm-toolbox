# Modeller Cheat Sheet

Quick reference for the [entity classes](../community/glossary.md#entity-class) and patterns energy system modellers use most often. For complete definitions, open the interactive **[CESDM Schema Reference](../reference/schema-reference.html)**.

!!! info "Imports"
    Energy system modellers should use:

    ```python
    from cesdm_toolbox import build_model_from_yaml
    from cesdm.default_library import Carriers, GeneratorTypes, NaturalResources, StorageTypes
    ```

    The low-level `ear` package is documented in the [EAR API Reference](../reference/api-reference.md) for engine-level work.

---

## Top entity classes

| Entity class | Modeller use | Key relations / attributes |
|--------------|--------------|----------------------------|
| `EnergySystemModel` | Study container | `long_name`, scenario metadata |
| `CarrierDomain` | Electricity / gas / heat network scope | `hasCarrier` |
| `GeographicalRegion` | Countries, NUTS regions | From `library/regions_library` (e.g. `region.country.CH`) |
| `ElectricalBus` | Network node | `belongsToCarrierDomain` (required), `nominal_voltage` |
| `GenerationUnit` | Power plant | `hasTechnology`, `atNode`, `nominal_power_capacity` |
| `HydroGenerationUnit` | Hydro machine | `hydro_machine_kind` (`turbine` / `pump` / `reversible`), water links |
| `DemandUnit` | Load | `hasDemandProfile`, `atNode`, `annual_energy_demand` (`MWh/year`) |
| `GenericInterconnector` | Capacity-only transfer (any carrier) | `fromNode`, `toNode`, NTC limits |
| `CHPUnit` / `HeatPumpUnit` / `ElectrolyserUnit` / `BoilerUnit` / `FuelCellUnit` | Compact conversion leaves | Typed nodes (`atElectricityNode`, `atHeatNode`, `atHydrogenNode`, …) — [tutorial](../tutorials/conversion-units/overview.md) |
| `GenericConversionUnit` | MxN / P2X conversion | `ConversionPort`s + `referencePort` |
| `HydraulicStorageUnit` | Water body (RoR capacity 0 … reservoir / PHS) | `hasNaturalInflowProfile`, drawn by hydro gens |
| `Profile` | Time-series metadata | `profile_type`, `hasTimestampSeries`, `data_reference` |
| `[TimestampSeries](../community/glossary.md#timestamp-series)` | Shared time axis | `start_datetime`, `resolution`, `length` |

---

## Common modelling tasks

### Add a wind farm

```python
gen = model.add_entity("GenerationUnit", "gen.ch.wind")
gen.name = "Swiss wind"
gen.nominal_power_capacity = (3500, "MW")
gen.hasTechnology = GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE
gen.atNode = bus_ch
gen.hasAvailabilityProfile = wind_profile  # Profile entity
```

### Add electricity demand

```python
dem = model.add_entity("DemandUnit", "dem.ch")
dem.name = "CH electricity demand"
dem.annual_energy_demand = (60_000_000, "MWh/year")  # 60 TWh/year
dem.atNode = bus_ch
dem.hasDemandProfile = demand_profile
```

### Reference a library technology

```python
gas = model.add_entity("GenerationUnit", "gen.ch.gas")
gas.hasTechnology = GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW
# Dispatch defaults (efficiency, cost) inherited from library when not set on asset
```

### Link a profile to an asset

```python
model.add_entity("TimestampSeries", "ts.main")
# ... set start_datetime, resolution, length ...

model.add_entity("Profile", "profile.demand.ch")
profile.profile_type = "as_normalized_annual_energy"
profile.hasTimestampSeries = ts_main
profile.data_reference = "profiles.h5:/profiles/demand_ch"

dem.hasDemandProfile = profile
```

### Schema vs analysis validation

| Check | Question answered | Command |
|-------|-------------------|---------|
| Schema | Is this a valid CESDM model? | `model.validate()` |
| Analysis | Is it ready for my study? | `model.validate_for_analysis("optimal_dispatch")` (also `power_flow`, `dynamics`) |

Details: [Validation](validation.md).

---

## Profile types

| Type | Meaning | Example |
|------|---------|---------|
| `as_capacity_factor` | × installed capacity | Wind/solar availability |
| `as_normalized_annual_energy` | × annual energy | Demand shape |
| `as_SI` | Absolute values | Prices, temperatures |

---

## Attribute groups (Proxy API)

Defined in [Schemas — Attribute groups](schemas.md#attribute-groups). Typical groups exposed in Python:

| Group | Typical content |
|-------|-----------------|
| `topology` | Network attachment within a domain (`atNode`, `fromNode`, `toNode`, `belongsToCarrierDomain`) |
| `dispatch` | Capacities, costs, efficiencies, ramp rates |
| `power_flow` | Impedances, voltage limits, NTC |
| `dynamics` | Machine / controller parameters (often schema-optional; see `dynamics` profile) |
| `capacity_expansion` | Commission / retrofit / retirement lifecycle |
| `spatial` | Coordinates, `belongsToGeographicalRegion` |
| `technical` | Plant-specific parameters |

Direct attributes (no group): `name`, `long_name`, `hasTechnology`, carrier relations.

---

## Export formats

```python
model.export_yaml_hierarchical("output/my_model/demo_2030.yaml")
model.export_frictionless(
    "output/my_model/frictionless/",
    name="my-study",
    title="My study model",
    include_library="referenced",  # default; use "none" or "all" if needed
)
```

Frictionless layout: `frictionless/datapackage.json` plus flat
`frictionless/resources/*.csv` (including `AllEntities.csv`).

---

## Where to learn more

| Topic | Page |
|-------|------|
| Full workflow | [Modelling Workflow](../guides/modelling-workflow.md) |
| Validation | [Validation](validation.md) |
| [Proxy API](../community/glossary.md#proxy-api) | [Proxy API guide](../guides/proxy-api.md) |
| IDE typing (optional) | [Python Typings & Proxies](../guides/python-typing-proxies.md) |
| Multi-carrier scope | [Carrier Domains](../guides/carrier-domains.md) |
| Time series | [Profiles](../guides/profiles.md) |
| Terms | [Glossary](../community/glossary.md) |

→ [Modelling Workflow](../guides/modelling-workflow.md) · [← Quickstart](quickstart.md)
