# PyPSA to CESDM Import Logic

This document describes the logic for importing a PyPSA nodal network into a CESDM
model. It explains how PyPSA network data, elements, time series, geographical mappings,
and exports are handled in the import workflow.

The workflow is based on the `example_import_pypsa.py` example, which imports a PyPSA
NetCDF network into CESDM, validates the result, and exports the model in several
formats.

---

# Prerequisites

Before running the importer, **PyPSA and some other packages must be installed**.

You can install it using `pip`:

```bash
pip install -e ".[pypsa]"
```

Besides these Python packages, the following resources are required:

- the CESDM schema directory (`schemas/cesdm/`),
- the CESDM toolbox,
- the PyPSA network (`*.nc`) to be imported.

---

# 1. Purpose of the import

The PyPSA import converts a PyPSA network file into a CESDM model.

The import is designed to:

- read a PyPSA `*.nc` network file,
- create CESDM entities from PyPSA components,
- map PyPSA buses and network topology to CESDM nodes, with topology attributes/relations declared directly on the connected assets,
- map PyPSA assets such as generators, storage units, loads, and links to CESDM assets,
- convert time-dependent PyPSA data into CESDM profile entities,
- optionally map nodes to geographical regions,
- validate the generated CESDM model,
- export the result to YAML, HDF5, FlexEco, and Frictionless formats.

The goal is not to reproduce PyPSA internally, but to translate PyPSA data into a
schema-valid CESDM representation that can be exchanged with other tools.

---

# 2. Input data

## Required example data

In addition to the Python dependencies, the PyPSA import example requires external example datasets that are **not distributed with the CESDM repository**.

These datasets include:

- the original **PyPSA** example network (`elec.nc`),
- the **TYNDP 2024** input datasets used by the TYNDP importer.

For convenience, both datasets are bundled in the following archive:

> https://ethz.ch/content/dam/ethz/special-interest/mavt/ctr-energy-networks-fen-dam/data/cesdm_external_data.zip

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
│       └── ...
└── ...
```

Once the archive has been extracted, both the PyPSA and TYNDP import examples can be executed without any additional data preparation.

The original `elec.nc` network originates from the **PyPSA** project, while the TYNDP datasets are based on the **ENTSO-E Ten-Year Network Development Plan (TYNDP 2024)**.

---

The main input is a PyPSA NetCDF network:

```bash
--nc-path ./external_data/elec.nc
```

The converter also requires the CESDM schema directory:

```bash
--schema-dir schemas/cesdm
```

Optional geographical information can be provided with:

```bash
--nuts-shapefile ./external_data/NUTS_RG_20M_2021_4326.shp
```

Full command to run the conversion example

```bash
python ./examples/example_import_pypsa.py --nc-path ./external_data/PYPSA/elec.nc --schema-dir schemas/cesdm --nuts-shapefile external_data/PYPSA/NUTS_RG_20M_2021_4326.shp --output-dir ./output/pypsa_nodal_model/nodal/
```
---

# 3. High-level workflow

```text
PyPSA NetCDF network
        │
        ▼
Read PyPSA network
        │
        ▼
Create CESDM model from schemas
        │
        ▼
Map carriers, nodes, assets, topology, and profiles
        │
        ▼
Validate CESDM model
        │
        ▼
Attach time-series arrays to Profile entities
        │
        ▼
Export CESDM YAML
        │
        ▼
Export CESDM HDF5 profiles
        │
        ▼
Optionally export FlexEco
        │
        ▼
Export Frictionless Data Package
```

---

# 4. Main conversion function

The central conversion step is:

```python
model, profiles_values = build_cesdm_from_pypsa(
    nc_path=str(nc_path),
    schema_dir=str(schema_dir),
    region_name=args.default_region_name,
    nuts_shapefile=args.nuts_shapefile,
)
```

This function performs the actual PyPSA to CESDM mapping.

It returns:

```python
model
```

A CESDM model containing the imported energy-system structure.

```python
profiles_values
```

A dictionary containing numeric time-series arrays:

```python
{
    "profile.entity.id": numpy_array
}
```

The numeric arrays are kept separate from the structural CESDM model until export time.

---

# 5. Mapping PyPSA nodal data

PyPSA buses represent the nodal structure of the network.

In CESDM, buses are mapped to node entities, for example:

```text
PyPSA Bus
      │
      ▼
CESDM ElectricalBus / node entity
```

The importer should preserve:

- bus ID,
- carrier or carrier domain,
- voltage level where available,
- geographical coordinates where available,
- regional assignment,
- connections to assets and branches.

Typical CESDM mapping:

```text
PyPSA bus
  name / index       → CESDM node ID
  carrier            → CarrierDomain / Carrier relation
  x, y coordinates   → geographical mapping
  country / region   → GeographicalRegion relation
```

The node layer is important because `atNode`/`fromNode`/`toNode` relations connect assets to nodes rather than
embedding network structure directly inside the asset entities.

---

# 6. Mapping energy carriers and carrier domains

PyPSA carrier information is mapped into CESDM energy carriers and carrier domains.

Example logic:

```text
PyPSA carrier: AC
      │
      ├── Carrier: Electricity
      └── CarrierDomain: electricity domain
```

Carrier information is used to classify:

- buses,
- generators,
- loads,
- storage units,
- links,
- conversion assets.

In CESDM, this allows the model to distinguish between electricity, heat, gas, hydrogen,
or other energy carriers in a tool-independent way.

---

# 7. Mapping geographical regions

The importer supports two geographical mapping levels.

## 7.1 Default region mapping

If no geographical information is available, all imported objects can be assigned to a
single default region:

```bash
--default-region-name DefaultRegion
```

This ensures that the CESDM model remains valid even when the PyPSA network does not
contain country or region metadata.

## 7.2 NUTS-based mapping

If a NUTS shapefile is provided, the importer can map buses or assets to sub-national
regions:

```bash
--nuts-shapefile data/NUTS_RG_20M_2021_4326.shp
```

Expected logic:

```text
PyPSA bus coordinates
        │
        ▼
Point-in-polygon lookup
        │
        ▼
NUTS2 / NUTS3 region
        │
        ▼
CESDM GeographicalRegion
```

This is useful for regional aggregation, reporting, and coupling with other models that
use administrative zones.

---

# 8. Mapping PyPSA elements

PyPSA components are mapped to CESDM asset entities — every mapped
component's topology/dispatch/power-flow attributes and relations
live directly on that one entity (see
`docs/guide/05_attribute_groups.md`).

A typical mapping strategy is:

| PyPSA element | CESDM concept |
|---|---|
| `Bus` | node / `ElectricalBus` |
| `Generator` | generation asset (dispatch + topology attributes/relations on the same entity) |
| `Load` | demand asset (dispatch profile + topology attributes/relations on the same entity) |
| `StorageUnit` / `Store` | storage asset (dispatch + topology attributes/relations on the same entity) |
| `Line` | interconnector / branch (topology + power-flow attributes/relations on the same entity) |
| `Link` | conversion or interconnector asset, depending on carrier mapping |
| time-dependent component data | profile entities + HDF5 numeric arrays |

The important design principle is that CESDM groups, on one entity:

```text
Asset identity
      │
      ├── topology attributes/relations
      ├── dispatch attributes
      ├── power-flow attributes
      └── time-series profiles (separate Profile entities, linked by relation)
```

This means a PyPSA generator is not mapped only to identity fields --
its topology, dispatch, and power-flow attributes/relations are all
held directly on the one CESDM asset (see `docs/schema_layout.md`,
"Attribute groups"):

```text
Generation asset
      ├── topology attributes/relations (atNode, ...)
      ├── dispatch attributes (nominal_power_capacity, ...)
      ├── power-flow attributes (powerflow_bus_type, ...)
      └── Profile entities for time-dependent data
```

---

# 9. Mapping topology

Topology describes where assets are connected.

For one-port assets such as generators, loads, and many storage units:

```text
PyPSA asset connected to bus
        │
        ▼
CESDM asset's own atNode relation → bus / node ID
```

For two-port assets such as lines, links, and interconnectors:

```text
PyPSA branch from bus0 to bus1
        │
        ▼
CESDM asset's own fromNode/toNode relations
        ├── fromNode → bus0 / node ID
        └── toNode   → bus1 / node ID
```

This keeps physical assets separate from their topological representation.

---

# 10. Mapping dispatch and operational data

Operational parameters are set directly on the asset entity, tagged
`belongsToGroup: [dispatch]` or `[power_flow]`.

Examples:

```text
PyPSA generator p_nom
      → CESDM dispatch capacity attribute

PyPSA generator efficiency
      → CESDM dispatch efficiency attribute

PyPSA load demand
      → CESDM demand profile

PyPSA line s_nom
      → CESDM power-flow capacity
```

This is important because CESDM treats operational model data as a representation of an
asset, not necessarily as part of the asset identity.

---

# 11. Mapping time series

PyPSA time-dependent values are collected separately from the structural model.

The example imports:

```python
collect_timeseries_from_pypsa
save_timeseries_to_hdf5
```

and the main conversion returns:

```python
profiles_values
```

The expected structure is:

```python
{
    "profile.generator.G1.p_max_pu": array([...]),
    "profile.load.L1.p_set": array([...]),
}
```

The CESDM model contains Profile entities and metadata, while the numerical arrays are
stored externally in HDF5.

This avoids writing large numerical time-series arrays into YAML files.

---

# 12. Attaching profile values before export

Before exporting HDF5 or FlexEco outputs, profile arrays are attached to the model:

```python
from cesdm_flexeco import _attach_profile_values  # separate in-house package

_attach_profile_values(model, profiles_values)
```

This step is required so that exporters can find the numerical payloads belonging to
Profile entities.

The sequence is therefore:

```text
Create Profile entities
        │
        ▼
Collect numeric arrays
        │
        ▼
Attach arrays to model
        │
        ▼
Export HDF5 / FlexEco
```

---

# 13. CESDM validation

After conversion, the model is validated against the CESDM schemas:

```python
errors = model.validate()

if errors:
    print(f"Model has {len(errors)} validation issue(s):")
    for e in errors:
        print(f"  - {e}")
else:
    print("Model validated successfully.")
```

Validation checks whether:

- entity classes exist in the schema,
- attributes are allowed on the respective entities,
- relation names are valid,
- relation targets are compatible,
- required schema constraints are satisfied.

Validation should happen before exporting or using the converted model downstream.

---

# 14. Exported outputs

The importer writes several outputs.

## 14.1 CESDM YAML

Two YAML representations are exported:

```python
model.export_yaml_hierarchical(
    yaml_dir / "pypsa_nodal_model_hierarchical.yaml"
)

model.export_yaml(
    yaml_dir / "pypsa_nodal_model_flat.yaml"
)
```

The hierarchical YAML is easier to inspect manually.

The flat YAML is useful for processing and conversion workflows.

## 14.2 CESDM HDF5 profiles

Time-series values are exported to HDF5:

```python
model.export_hdf5(
    cesdm_h5 / "profiles.h5",
    values_map=profiles_values,
)
```

The documented CESDM HDF5 layout is:

```text
/timestamps/<id>/
    attributes:
        start_datetime
        resolution
        length
        timezone

/profiles/<id>/
    attributes:
        profile_type
        profile_unit
        data_reference
    dataset:
        values: float64 [n_timesteps]
```

## 14.3 FlexECO export (separate package)

If `--export-flexeco` is enabled **and** [`cesdm-flexeco`](../docs/guides/tool-adapters.md) is installed:

```python
from cesdm_flexeco import export_to_flexeco, _attach_profile_values

_attach_profile_values(model, profiles_values)
export_to_flexeco(
    model,
    flex_dir / "pypsa_nodal_model.jpn",
    hdf5_path=flex_dir / "profiles" / "profiles.h5",
)
```

The FlexECO export writes:

```text
pypsa_nodal_model.jpn
profiles/profiles.h5
```

## 14.4 Frictionless Data Package

The model is also exported as a Frictionless Data Package:

```python
model.export_frictionless(
    fp_dir,
    name=f"cesdm-pypsa-{nc_stem}".lower(),
    title=f"PyPSA Network '{nc_stem}' — CESDM Model",
    description=(
        f"CESDM energy system model derived from PyPSA "
        f"network file '{nc_path.name}'."
    ),
    version="1.0.0",
)
```

The output structure is:

```text
datapackage.json
resources/
    one CSV file per CESDM class
```

This is useful for data exchange, tabular inspection, and integration with data catalogues.

---

# 15. Output directory structure

The example writes outputs below the selected output directory:

```text
output/pypsa_nodal_model/
    cesdm/
        yaml/
            pypsa_nodal_model_hierarchical.yaml
            pypsa_nodal_model_flat.yaml
        profiles/
            profiles.h5
        frictionless/
            datapackage.json
            resources/
                *.csv
```

---

# 16. Recommended import logic

A robust PyPSA to CESDM importer should follow this order:

```text
1. Read PyPSA network
2. Create CESDM model from schemas
3. Create Carrier entities
4. Create CarrierDomain entities
5. Reuse GeographicalRegion entities from ``library/regions_library``
   (``region.country.XX`` / ``region.nuts3.XXXX``); create only as fallback
6. Create node entities from PyPSA buses
7. Create asset entities from PyPSA components
8. Set topology attributes/relations directly on each asset
9. Set dispatch and power-flow attributes directly on each asset
10. Create Profile entities for time-dependent data
11. Collect time-series arrays into profiles_values
12. Validate CESDM model
13. Attach profile arrays
14. Export YAML
15. Export HDF5 profiles
16. Export Frictionless Data Package
```

---

# 17. Design principles

## Keep structure and numerical arrays separate

YAML should describe the model structure and profile metadata.

Large time-series arrays should be stored in HDF5.

## Preserve PyPSA IDs where possible

Using stable IDs makes it easier to trace CESDM entities back to PyPSA components.

## Keep topology/dispatch/power-flow attributes directly on the asset

A generator, load, line, or storage object is represented as one
asset entity; its topology, dispatch, and power-flow attributes and
relations live directly on that same entity, tagged
`belongsToGroup` — see `docs/guide/05_attribute_groups.md`.

## Use geographical regions explicitly

Even if only a default region is available, region entities make aggregation and reporting
easier.

## Validate early

Validation should happen directly after conversion so that schema or mapping errors are
detected before export.

---

# 18. Example command

```bash
python examples/example_import_pypsa.py \
    --nc-path data/elec.nc \
    --schema-dir schemas/cesdm \
    --output-dir output/pypsa_import \
    --nuts-shapefile data/NUTS_RG_20M_2021_4326.shp
```

Without a NUTS shapefile:

```bash
python examples/example_import_pypsa.py \
    --nc-path data/elec.nc \
    --schema-dir schemas/cesdm \
    --output-dir output/pypsa_import
```

---

# 19. Summary

The PyPSA import workflow translates a PyPSA nodal model into a CESDM model by mapping
network elements, topology, operational data, time series, and geography into a
schema-valid CESDM representation.

The resulting CESDM model can then be validated, inspected, exported as yaml or tabular Frictionless, and reused in other
toolchains.
