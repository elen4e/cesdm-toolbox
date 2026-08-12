# TYNDP to CESDM Import Logic

This document describes the logic for importing TYNDP 2024 CSV source files into a CESDM
model. It explains how nodes, countries, installed capacities, technologies, storage,
demand, renewable profiles, hydro inflows, NTC interconnectors, scenarios, and exports are
handled in the import workflow.

The workflow is based on `example_import_tyndp.py`, which builds CESDM
models from TYNDP 2024 CSV files for selected policy scenarios,
scenario years, and weather years. Kept in `examples/` alongside the
newer, recommended `example_import_tyndp_proxy_api.py` (see
`docs/architecture/proxy_api.md`) specifically because that proxy-API
sibling reuses this file's classification logic directly rather than
re-deriving it.

---

# Prerequisites

Before running the importer, the following Python packages must be available:

```bash
pip install pandas numpy h5py
```

The importer also expects the CESDM toolbox and the CESDM schema directory to be available.

Required local resources:

- CESDM toolbox files,
- CESDM schema directory,
- TYNDP 2024 CSV source files,
- optional default-library / carrier helper modules.

The importer uses helper modules such as:

```python
generation_classifier
cesdm_carriers
cesdm_toolbox
```

So the repository root and `tools/` directory must be on `PYTHONPATH`.

---

# 1. Purpose of the import

The TYNDP importer converts tabular TYNDP 2024 data into a schema-valid CESDM model.

The import is designed to:

- read TYNDP CSV source files,
- create CESDM geographical regions and electrical buses,
- create energy carriers, natural resources, and carrier domains,
- create generation, storage, demand, and interconnector assets,
- classify technologies into CESDM asset classes,
- set topology, dispatch, storage, demand, hydro, and power-flow attributes/relations directly on each asset,
- create profile entities for time-dependent data,
- store numerical profile arrays separately for HDF5 export,
- validate the generated CESDM model,
- export the model to YAML, HDF5, and Frictionless formats.

The goal is to translate TYNDP planning data into a reusable CESDM representation, not to
reproduce TYNDP internally.

---

# 2. Input data

The TYNDP importer requires the official **TYNDP 2024** input datasets, which are **not distributed with the CESDM repository**.

For convenience, the required **TYNDP 2024** datasets together with the original **PyPSA** example network (`elec.nc`) are bundled in the following archive:

> https://ethz.ch/content/dam/ethz/special-interest/mavt/ctr-energy-networks-fen-dam/data/CESDM_external_data.zip

Download the archive, extract it, and copy the extracted contents into the **root directory** of the CESDM repository. The resulting directory structure should look similar to:

```text
cesdm-toolbox/
│
├── schemas/
│   └── cesdm/
├── library/
├── examples/
├── external_data/
│   ├── PYPSA/
│   │   ├── elec.nc
│   │   └── NUTS_RG_20M_2021_4326.shp
│   └── TYNDP2024/
│       ├── TYNDP24_Nodes.csv
│       ├── TYNDP24_InstalledCapacities.csv
│       ├── TYNDP24_DemandProfiles.csv
│       ├── TYNDP24_GenProfiles.csv
│       ├── TYNDP24_HydroInflows.csv
│       ├── TYNDP24_StorageCapacities.csv
│       ├── TYNDP24_NTC_types.csv
│       └── ...
└── ...
```

Once the archive has been extracted, the TYNDP import example can be executed without any additional data preparation.

The TYNDP datasets originate from the **ENTSO-E Ten-Year Network Development Plan (TYNDP 2024)**. The archive additionally contains the original **PyPSA** example network used by the PyPSA import example.
The importer uses the selected:

```text
policy
scenario year
climate / weather year
```

Example:

```text
policy       = NT
year         = 2030
climate_year = 2009
```

The output folder is scenario-specific:

```text
SC_<policy>_SY_<year>_WY_<climate_year>/
```

For example:

```text
SC_NT_SY_2030_WY_2009/
```

---

# 3. High-level workflow

```text
TYNDP CSV files
        │
        ▼
Load CESDM schema
        │
        ▼
Create CESDM model
        │
        ▼
Import nodes and countries
        │
        ▼
Import installed capacities
        │
        ▼
Import demand capacities
        │
        ▼
Create shared TimestampSeries
        │
        ▼
Import demand time series
        │
        ▼
Import renewable generation profiles
        │
        ▼
Import hydro inflow profiles
        │
        ▼
Import storage energy capacities
        │
        ▼
Import NTC interconnectors
        │
        ▼
Validate CESDM model
        │
        ▼
Export YAML, HDF5, and Frictionless package
```

---

# 4. Main build function

The central build function is:

```python
build_cesdm_model_from_tyndp_installed_capacities(
    schema_path="schemas/cesdm",
    data_folder="data/",
    output_folder="output/TYNDP2024/",
    policy="NT",
    year=2030,
    climate_year=2009,
    drop_zero=True,
)
```

The function creates a complete CESDM model for one scenario combination.

Arguments:

| Argument | Meaning |
|---|---|
| `schema_path` | Path to the CESDM schema directory |
| `data_folder` | Folder containing TYNDP CSV files |
| `output_folder` | Root output folder |
| `policy` | TYNDP policy scenario, for example `NT`, `DE`, or `GA` |
| `year` | Scenario year, for example `2030`, `2040`, or `2050` |
| `climate_year` | Weather / climate year used for profiles |
| `drop_zero` | Whether zero-value rows should be ignored |

---

# 6. Nodes and geographical regions

Nodes and countries are read from:

```text
TYNDP24_Nodes.csv
```

The importer creates:

```text
GeographicalRegion
ElectricalBus
CarrierDomain
Carrier
```

Mapping logic:

```text
TYNDP node code
      → ElectricalBus

TYNDP country code (ISO)
      → GeographicalRegion ``region.country.XX``
        (from ``library/regions_library``; created only if missing)

Electricity
      → Carrier + CarrierDomain
```

Typical CESDM relations:

```text
ElectricalBus.belongsToCarrierDomain → CarrierDomain
ElectricalBus.belongsToGeographicalRegion              → GeographicalRegion
CarrierDomain.hasCarrier             → Electricity carrier
```

The node import function is:

```python
assign_nodes_and_countries_from_tyndp_nodes_csv(...)
```

This step should happen first because later assets are connected to these nodes.

---

# 7. Energy carriers and natural resources

The importer distinguishes between transported energy carriers and natural resources.

Examples of energy carriers:

```text
carrier.electricity
carrier.natural_gas
carrier.hard_coal
carrier.lignite
carrier.oil
carrier.uranium
```

Examples of natural resources:

```text
resource.water
resource.wind
resource.solar
```

This distinction matters because:

- generators using fuels are connected to input energy carriers,
- renewable generators can use natural resources,
- hydro storage stores water as a resource,
- electricity belongs to an electricity carrier domain.

The carrier helper logic maps technology names to canonical CESDM carrier or resource IDs.

---

# 8. Installed capacities

Installed generation and storage capacities are read from:

```text
TYNDP24_InstalledCapacities.csv
```

The import function is:

```python
assign_installed_capacity_from_tyndp_csv(...)
```

The importer filters rows by:

```text
Policy
Year
Climate Year
Variable
Value
```

Only relevant installed or charging capacity rows are retained. Zero rows can be removed
with `drop_zero=True`.

## 8.1 Generation assets

Generation rows are mapped to CESDM generation asset classes.

Examples:

| TYNDP technology | CESDM asset class |
|---|---|
| nuclear | `GenerationUnit` |
| gas CCGT / OCGT | `GenerationUnit` |
| coal / lignite / oil | `GenerationUnit` |
| wind | `GenerationUnit` |
| solar PV | `GenerationUnit` |
| run-of-river hydro | `HydroGenerationUnit` |
| residual / fallback | `GenerationUnit` |

The importer creates:

```text
Generation asset (GenerationUnit / HydroGenerationUnit)
GeneratorType
```

Typical relations, held directly on the asset itself:

```text
asset.hasTechnology → GeneratorType
asset.atNode        → ElectricalBus
```

The installed power is stored directly on the asset:

```text
asset.nominal_power_capacity
```

This keeps identity (`name`, `hasTechnology`) and operational data
(dispatch/topology attributes, tagged `belongsToGroup`) together on
one entity (see `docs/schema_layout.md`, "Attribute groups").

## 8.2 Storage assets

Storage rows are mapped to CESDM storage classes.

Examples:

| TYNDP technology | CESDM asset class |
|---|---|
| battery storage | `StorageUnit` |
| reservoir hydro | `HydraulicStorageUnit` |
| pondage | `HydraulicStorageUnit` |
| pumped hydro | `HydraulicStorageUnit` |

The importer creates:

```text
Storage asset (StorageUnit / HydraulicStorageUnit)
StorageType
```

Battery storage uses:

```text
storesCarrier → electricity
```

Hydro reservoir storage uses:

```text
storesResource → resource.water
```

Charging capacity and storage capacity are stored directly on the `StorageUnit`/`HydraulicStorageUnit` entity (`belongsToGroup: [dispatch]`).

---

# 9. Hydro reservoir composite assets

Hydro reservoir and pumped-hydro assets require special handling.

A reservoir is not only a storage unit. It is represented as a composite structure:

```text
HydraulicStorageUnit
        │
        ├── storesResource → resource.water
        ├── suppliesResourceTo → HydroGenerationUnit
        │
        ▼
HydroGenerationUnit
        │
        ├── drawsFromHydraulicStorage → HydraulicStorageUnit
        ├── hasInputResource   → resource.water
        └── hasOutputCarrier   → electricity
```

For pumped hydro storage, the linked `HydroGenerationUnit` is marked as reversible:

```text
hydro_machine_kind = reversible
turbine_type  = reversible_francis
```

Power-related values are stored directly on the `HydroGenerationUnit`
itself:

```text
nominal_power_capacity
maximum_pumping_power
turbine_efficiency
pumping_efficiency
hydro_machine_kind
```

This avoids incorrectly storing turbine information directly on the reservoir object.

---

# 10. Demand capacities

Demand capacity rows are also derived from:

```text
TYNDP24_InstalledCapacities.csv
```

The function is:

```python
assign_demand_from_tyndp_csv(...)
```

It currently identifies rows such as:

```text
Electrolyser
CH4 Heat Pump
```

These are mapped to:

```text
DemandUnit
```

Capacity is stored directly on the `DemandUnit` itself:

```text
maximum_energy_demand
```

---

# 11. Timestamp series

Before importing time series, the importer creates one shared timestamp series:

```python
ts_id = "timestamp.hourly"
```

Typical attributes:

```text
name           = Hourly <climate_year>
start_datetime = <climate_year>-01-01T00:00:00
resolution     = PT1H
length         = 8784
timezone       = UTC
```

The length is set to:

```text
8784 = 8760 + 24 padding hours
```

Profile entities reference this timestamp series through:

```text
Profile.hasTimestampSeries → TimestampSeries
```

---

# 12. Demand time-series profiles

Demand profiles are read from:

```text
TYNDP24_DemandProfiles.csv
```

The function is:

```python
assign_demand_from_tyndp_timeseries_csv(...)
```

The importer:

1. filters by policy, year, and climate year,
2. detects hourly columns,
3. aggregates rows by node and demand type,
4. pads the profile by 24 hours,
5. computes annual demand,
6. creates or updates a `DemandUnit` (dispatch attributes held directly on it),
7. creates a `Profile` entity,
8. stores the numeric array in `profiles_values`.

Demand profiles are stored as normalized annual-energy profiles:

```text
profile_type = as_normalized_annual_energy
profile_unit = pu
```

The numerical array is stored outside the YAML model and later exported to HDF5.

---

# 13. Renewable generation profiles

Renewable profiles are read from:

```text
TYNDP24_GenProfiles.csv
```

The function is:

```python
assign_renewable_timeseries_from_csv(...)
```

The importer maps TYNDP profile types to technology slugs, for example:

| TYNDP profile type | Internal technology slug |
|---|---|
| `Wind_Offshore` | `wind_offshore` |
| `Wind_Onshore` | `wind_onshore` |
| `SolarPV` | `solar_photovoltaic` |
| `LFSolarPVRooftop` | `solar_photovoltaic_rooftop` |
| `LFSolarPVUtility` | `solar_photovoltaic_utility` |
| `CSP_noStorage` | `solar_thermal` |

The profile is linked directly to the generation/demand asset through:

```text
hasAvailabilityProfile
```

The profile values are normalized and stored as:

```text
profile_type = as_normalized_annual_energy
profile_unit = pu
```

The annual resource potential is derived from the profile and installed capacity.

---

# 14. Hydro inflow profiles

Hydro inflows are read from:

```text
TYNDP24_HydroInflows.csv
```

The function is:

```python
assign_inflow_timeseries_from_csv(...)
```

The importer distinguishes between:

```text
run-of-river generation
reservoir hydro
pondage
pumped hydro
```

For generation assets, inflows are linked as availability or run-of-river inflow profiles.

For reservoir storage assets, inflows are stored directly on `HydraulicStorageUnit` as:

```text
annual_natural_inflow_energy
natural_inflow_profile_reference
```

Profile arrays are registered as CESDM `Profile` entities and exported to HDF5.

After inflows are assigned, the importer can prune hydro reservoirs without inflow:

```python
prune_hydro_reservoirs_without_inflow(model)
```

---

# 15. Storage energy capacity

Storage energy capacities are read from:

```text
TYNDP24_StorageCapacities.csv
```

The function is:

```python
assign_energy_storage_capacity_from_tyndp_csv(...)
```

The importer assigns:

```text
energy_storage_capacity
```

directly to the storage asset itself (`StorageUnit` or
`HydraulicStorageUnit`).

If storage units have charging power but no explicit nominal power or energy capacity, the
importer applies fallback logic so that the storage representation remains usable.

---

# 16. NTC interconnectors

Net transfer capacity data is read from:

```text
TYNDP24_NTC_types.csv
```

The function is:

```python
assign_ntc_from_tyndp_ntc_types_base_csv(...)
```

The importer creates interconnector assets, with topology and
power-flow attributes/relations held directly on the asset itself.

Typical CESDM structure:

```text
Interconnector
      ├── fromNode
      ├── toNode
      ├── maximum_power_flow_from_to
      └── maximum_power_flow_to_from
```

If the NTC file is missing, the importer skips this step and continues:

```text
NTC CSV not found — skipping.
```

---

# 17. Technology classification

The importer maps TYNDP technology labels to CESDM technology IDs and asset classes.

At pipeline start it loads stacked libraries via `import_tyndp_libraries()`:

- `library/default_library` — core types (`Existing` / `New` / `CCS` / …)
- `library/tyndp_library` — TYNDP vintages (`Old1` / `Old2` / `Present*`, oil shale)

The technology vocabulary is stored in a dictionary such as:

```python
TECH_HIERARCHY = {
    "wind_offshore": "Generation.Renewable.Wind.Offshore",
    "solar_photovoltaic": "Generation.Renewable.Solar.PV.Utility",
    "gas_ccgt_new": "Generation.Thermal.Gas.CCGT.New",
    "battery_storage": "Storage.Electrochemical.Battery",
    "reservoir": "Storage.Hydro.Reservoir",
}
```

Technology defaults are stored separately, for example:

```python
TYNDP_TECH_DATA = {
    "Generation.Thermal.Gas.CCGT.New": {
        "eff": 0.60,
        "voc": 1.6,
        "disp": True,
    }
}
```

This separation allows CESDM to distinguish:

```text
asset class        = physical asset family
technology type    = technology vocabulary
dispatch attributes = model-specific operational parameters, flattened onto the asset
```

---

# 18. Profile handling

The importer keeps model structure and numerical time-series values separate.

Profile metadata is stored in CESDM:

```text
Profile
      ├── profile_type
      ├── profile_unit
      ├── data_reference
      └── hasTimestampSeries
```

The numerical payload is stored in a Python dictionary:

```python
profiles_values = {
    "profile.demand.electricity.node_x": numpy_array,
    "profile.wind_onshore.node_y": numpy_array,
}
```

During export, these arrays are written to HDF5:

```python
model.export_hdf5(
    h5_dir / "profiles.h5",
    values_map=profiles_values,
)
```

This keeps YAML files readable and avoids embedding large time series directly into the
CESDM structure.

---

# 19. Validation

After all entities, attributes, relations, and profiles have been created, the model is
validated:

```python
errors = model.validate()

if errors:
    print(f"Validation issues ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
else:
    print("Model validated successfully.")
```

Validation checks whether:

- entity classes exist in the CESDM schema,
- attributes are valid for their entity or view class,
- relation names are valid,
- relation targets exist and have compatible classes,
- the generated model follows the CESDM schema.

Validation should happen before exporting or using the model downstream.

---

# 20. Output structure

For each scenario, outputs are written to:

```text
output/TYNDP2024/
    SC_<policy>_SY_<year>_WY_<climate_year>/
        cesdm/
            yaml/
                tyndp_<policy>_<year>_<climate_year>_hierarchical.yaml
                tyndp_<policy>_<year>_<climate_year>_flat.yaml
            profiles/
                profiles.h5
            frictionless/
                datapackage.json
                resources/
                    *.csv
```

---

# 21. YAML export

The importer writes both hierarchical and flat YAML:

```python
model.export_yaml_hierarchical(
    yaml_dir / f"{stem}_hierarchical.yaml"
)

model.export_yaml(
    yaml_dir / f"{stem}_flat.yaml"
)
```

The hierarchical YAML is easier for humans to inspect.

The flat YAML is easier for automated processing.

---

# 22. HDF5 export

The importer writes profile data to HDF5:

```python
model.export_hdf5(
    h5_dir / "profiles.h5",
    values_map=profiles_values,
)
```

The HDF5 file contains:

```text
/timestamps/<id>/
/profiles/<id>/values
```

Metadata such as profile type, unit, start datetime, resolution, and timezone is stored as
HDF5 group attributes.

---

# 23. Frictionless export

The importer also writes a Frictionless Data Package:

```python
model.export_frictionless(
    fp_dir,
    name=stem.replace("_", "-"),
    title=f"TYNDP {year} {policy} — CESDM Model",
    description=(
        f"CESDM energy system model derived from TYNDP 2024 "
        f"data (policy={policy}, year={year}, "
        f"climate_year={climate_year})."
    ),
    version="1.0.0",
)
```

The output contains:

```text
datapackage.json
resources/
    one CSV file per CESDM class
```

This is useful for tabular inspection, data catalogues, and interoperability.

---

# 24. Batch execution

The example script builds several scenario combinations.

For example:

```python
for sc in ["NT"]:
    for sy in [2030, 2040]:
        for wy in [2009]:
            build_cesdm_model_from_tyndp_installed_capacities(
                schema_path="schemas/cesdm",
                data_folder="data/",
                output_folder="output/TYNDP2024/",
                policy=sc,
                year=sy,
                climate_year=wy,
                drop_zero=True,
            )
```

It also builds additional policy scenarios:

```text
DE
GA
```

for years such as:

```text
2030
2040
2050
```

---

# 26. Recommended import order

A robust TYNDP to CESDM import should follow this order:

```text
1. Load CESDM schemas
2. Create empty CESDM model
3. Import nodes and countries
4. Ensure electricity carrier and carrier domain
5. Import installed generation and storage capacities
6. Create generation and storage technology types
7. Set topology attributes/relations directly on each asset
8. Set dispatch attributes directly on generation, storage, and demand assets
9. Import demand capacities
10. Create shared TimestampSeries
11. Import demand profiles
12. Import renewable availability profiles
13. Import hydro inflow profiles
14. Import storage energy capacities
15. Import NTC interconnectors
16. Validate the CESDM model
17. Export YAML
18. Export HDF5 profile values
19. Export Frictionless Data Package
```

---

# 27. Design principles

## Keep operational data directly on the asset entity

Asset entities represent the physical or conceptual object.

Operational values such as capacity, demand, efficiency, inflow, and availability are
set directly on that same entity, tagged `belongsToGroup` (see
`docs/guide/05_attribute_groups.md`).

## Use `atNode`/`fromNode`/`toNode` for connections

Assets are connected to buses through these relations, declared
directly on the asset, rather than direct ad-hoc fields.

## Keep time-series arrays out of YAML

YAML stores profile metadata.

HDF5 stores numerical arrays.

## Preserve TYNDP scenario context

Policy, scenario year, and climate year should be reflected in output names and metadata.

## Treat hydro reservoirs as composite assets

Reservoir hydro and pumped hydro require both storage and generation representations.

## Validate before export

Schema validation should be performed after all data has been imported and before the model
is used downstream.

---

# 28. Example usage

From the repository root:

```bash
python examples/example_import_tyndp.py
```

The script will build the scenario combinations defined in its `__main__` block.

To call the build function directly from Python:

```python
from examples.example_import_tyndp import (
    build_cesdm_model_from_tyndp_installed_capacities,
)

build_cesdm_model_from_tyndp_installed_capacities(
    schema_path="schemas/cesdm",
    data_folder="data/",
    output_folder="output/TYNDP2024/",
    policy="NT",
    year=2030,
    climate_year=2009,
    drop_zero=True,
)
```

---

# 29. Summary

The TYNDP import workflow converts scenario-dependent TYNDP 2024 CSV files into a CESDM
model by mapping nodes, countries, carriers, technologies, assets, topology, dispatch
parameters, demand, renewable profiles, hydro inflows, storage capacities, and
interconnectors into a structured CESDM representation.

The resulting model can be validated, inspected, exported to YAML, linked with HDF5
profiles, and exchanged through Frictionless.
