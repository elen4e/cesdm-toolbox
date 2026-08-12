"""
example_import_pypsa.py
==========================

Import a PyPSA NetCDF network into a CESDM V4 model, including reservoir hydro composite assets where applicable.

What this example demonstrates
-------------------------------
- Converting a PyPSA network (*.nc) to a CESDM V4 model using the V4 schema
- Validating the model against the CESDM V4 YAML schemas
- Exporting to hierarchical YAML, flat YAML, and per-class CSV tables
- Exporting Profile numeric payloads to HDF5 (flat-matrix FlexEco layout:
    /series_names  ASCII S64  (n_profiles,)
    /values        float64    (n_timesteps, n_profiles))
- Optionally exporting to FlexEco .jpn format + HDF5 profiles
- Exporting a Frictionless Data Package (datapackage.json + one CSV per class)

Prerequisites
-------------
- pypsa  (``pip install pypsa``)
- h5py   (``pip install h5py``)
- The V4 schema directory (schemas/cesdm/) and toolbox files

Run
---
    python examples/example_import_pypsa.py \\
        --nc-path data/elec.nc \\
        --schema-dir schemas/cesdm \\
        --output-dir output/pypsa_import
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repo_root()))
sys.path.insert(0, str(_repo_root() / "tools"))


def _optional_imports():
    """Import optional dependencies with a helpful error message."""
    try:
        import pypsa  # type: ignore
    except Exception as e:
        raise SystemExit(
            "This example requires the optional dependency 'pypsa'.\n"
            "Install it with:  pip install pypsa\n\n"
            f"Original error: {e}"
        )

    try:
        from import_pypsa import (
            build_cesdm_from_pypsa,
            collect_timeseries_from_pypsa,
            save_timeseries_to_hdf5,
        )
    except Exception as e:
        raise SystemExit(
            "Could not import the PyPSA→CESDM converter utilities.\n"
            "Make sure import_pypsa.py is on PYTHONPATH.\n\n"
            f"Original error: {e}"
        )

    return pypsa, build_cesdm_from_pypsa, collect_timeseries_from_pypsa, \
        save_timeseries_to_hdf5


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a PyPSA NetCDF network to a CESDM V4 model."
    )
    parser.add_argument(
        "--nc-path",
        default=str(_repo_root() / "data" / "elec.nc"),
        help="Path to the PyPSA NetCDF file (*.nc).",
    )
    parser.add_argument(
        "--schema-dir",
        default=str(_repo_root() / "schemas/cesdm"),
        help="Path to the CESDM V4 schema directory.",
    )
    parser.add_argument(
        "--default-region-name",
        default="DefaultRegion",
        help="Geographical region name when the network has no country info.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_repo_root() / "output" / "pypsa_nodal_model"),
        help="Directory for CESDM outputs.",
    )
    parser.add_argument(
        "--nuts-shapefile",
        default=None,
        help=(
            "Optional path to a NUTS shapefile (EPSG:4326) for NUTS2/NUTS3 "
            "sub-national region assignment. Requires geopandas. "
            "Example: data/NUTS_RG_20M_2021_4326.shp"
        ),
    )
    parser.add_argument(
        "--export-flexeco",
        action="store_true",
        default=False,
        help="Also export to FlexECO .jpn + HDF5 (requires cesdm-flexeco package).",
    )
    args = parser.parse_args()

    nc_path    = Path(args.nc_path)
    schema_dir = Path(args.schema_dir)
    out_dir    = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not nc_path.exists():
        raise SystemExit(f"NetCDF file not found: {nc_path}")
    if not schema_dir.exists():
        raise SystemExit(f"Schema directory not found: {schema_dir}")

    pypsa, build_cesdm_from_pypsa, collect_timeseries_from_pypsa, \
        save_timeseries_to_hdf5 = _optional_imports()

    # ------------------------------------------------------------------
    # 1) Convert PyPSA network → CESDM V4 model
    #    build_cesdm_from_pypsa now returns (model, profiles_values)
    #    where profiles_values is { Profile entity id → np.ndarray }
    # ------------------------------------------------------------------
    model, profiles_values = build_cesdm_from_pypsa(
        nc_path=str(nc_path),
        schema_dir=str(schema_dir),
        region_name=args.default_region_name,
        nuts_shapefile=args.nuts_shapefile,
    )

    errors = model.validate()
    if errors:
        print(f"Model has {len(errors)} validation issue(s):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Model validated successfully.")

    # ------------------------------------------------------------------
    # 2) Output directories
    # ------------------------------------------------------------------
    yaml_dir = out_dir / "cesdm" / "yaml"
    cesdm_h5 = out_dir / "cesdm" / "profiles"
    # csv_dir  = out_dir / "cesdm" / "csv"
    flex_dir = out_dir / "flexeco"
    for d in (yaml_dir, cesdm_h5, flex_dir):
        d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 3) YAML exports
    # ------------------------------------------------------------------
    model.export_yaml_hierarchical(yaml_dir / "pypsa_nodal_model_hierarchical.yaml")
    model.export_yaml(yaml_dir / "pypsa_nodal_model_flat.yaml")
    print(f"Wrote YAML to: {yaml_dir}")

    # # ------------------------------------------------------------------
    # # 5) CSV exports (one file per entity class)
    # # ------------------------------------------------------------------
    # model.export_csv_hierarchical(csv_dir, wide=True, long=False)
    # print(f"Wrote CSV tables to: {csv_dir}")

    # # ------------------------------------------------------------------
    # # 5b) Excel export (one sheet per entity class, no unit suffixes)
    # # ------------------------------------------------------------------
    # excel_dir = out_dir / "cesdm" / "excel"
    # excel_dir.mkdir(parents=True, exist_ok=True)
    # excel_path = excel_dir / "pypsa_nodal_model.xlsx"
    # model.export_excel(str(excel_path))
    # print(f"Wrote Excel (hierarchical) to: {excel_path}")

    # flat_path = excel_dir / "pypsa_nodal_model_flat.xlsx"
    # model.export_excel_flat(str(flat_path))
    # print(f"Wrote Excel (flat) to: {flat_path}")

    # ------------------------------------------------------------------
    # 4) CESDM HDF5: hierarchical format
    #    Layout:
    #      /timestamps/<id>/  attrs: start_datetime, resolution, length, timezone
    #      /profiles/<id>/    attrs: profile_type, profile_unit, data_reference
    #                         dataset "values": float64 [n_timesteps]
    # ------------------------------------------------------------------
    if profiles_values:
        model.export_hdf5(cesdm_h5 / "profiles.h5", values_map=profiles_values)
        print(f"Wrote CESDM HDF5 ({len(profiles_values)} profiles) to: "
              f"{cesdm_h5 / 'profiles.h5'}")
    else:
        print("No profile data to write.")

    # ------------------------------------------------------------------
    # 5) Optional FlexECO .jpn + HDF5 (requires separate cesdm-flexeco package)
    # ------------------------------------------------------------------
    if args.export_flexeco and profiles_values:
        try:
            from cesdm_flexeco import export_to_flexeco, _attach_profile_values
        except ImportError as exc:
            print(
                "[WARN] FlexECO export skipped — install the separate "
                f"cesdm-flexeco package ({exc})."
            )
        else:
            _attach_profile_values(model, profiles_values)
            flex_dir.mkdir(parents=True, exist_ok=True)
            export_to_flexeco(
                model,
                flex_dir / "pypsa_nodal_model.jpn",
                hdf5_path=flex_dir / "profiles" / "profiles.h5",
            )
            print(f"Wrote FlexECO .jpn + HDF5 profiles to: {flex_dir}")

    # ------------------------------------------------------------------
    # 9) Frictionless Data Package
    #    Self-describing multi-file package with embedded Table Schema.
    #    Layout:
    #      datapackage.json        — Frictionless descriptor
    #      resources/
    #        GenerationUnit.csv    — one CSV per entity class
    #        ElectricalBus.csv
    #        Carrier.csv
    #        …
    # ------------------------------------------------------------------
    fp_dir  = out_dir / "cesdm" / "frictionless"
    nc_stem = nc_path.stem
    dp_path = model.export_frictionless(
        fp_dir,
        name        = f"cesdm-pypsa-{nc_stem}".lower(),
        title       = f"PyPSA Network '{nc_stem}' — CESDM V4 Model",
        description = (f"CESDM V4 energy system model derived from PyPSA "
                       f"network file '{nc_path.name}'."),
        version     = "1.0.0",
    )
    print(f"Wrote Frictionless Data Package to: {dp_path}")


if __name__ == "__main__":
    main()
