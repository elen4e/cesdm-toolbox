#!/usr/bin/env python3
"""Generate library/regions_library from the Eurostat NUTS shapefile.

Writes:
  - GeographicalRegion entities for country (NUTS 0) + NUTS1–3
  - MarketZone entities for common ENTSO-E bidding zones

Usage (from repo root)::

    python tools/generate_regions_library.py
    python tools/generate_regions_library.py \\
        --nuts-shapefile external_data/PYPSA/NUTS_RG_20M_2021_4326.shp/NUTS_RG_20M_2021_4326.shp
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_NUTS = (
    _REPO
    / "external_data"
    / "PYPSA"
    / "NUTS_RG_20M_2021_4326.shp"
    / "NUTS_RG_20M_2021_4326.shp"
)

# NUTS country prefix → ISO 3166-1 alpha-2 (and preferred English long name).
_NUTS_TO_ISO = {"EL": "GR", "UK": "GB"}
_COUNTRY_LONG_NAME: dict[str, str] = {
    "AL": "Albania",
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "CH": "Switzerland",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "EL": "Greece",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GR": "Greece",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IS": "Iceland",
    "IT": "Italy",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "ME": "Montenegro",
    "MK": "North Macedonia",
    "MT": "Malta",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "RS": "Serbia",
    "SE": "Sweden",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "TR": "Türkiye",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "XK": "Kosovo",
}

# ENTSO-E style bidding zones: code → (long_name, covered ISO country codes).
# Multi-zone countries list the primary national zones used in planning models.
_MARKET_ZONES: list[tuple[str, str, list[str]]] = [
    ("AL", "Albania", ["AL"]),
    ("AT", "Austria", ["AT"]),
    ("BA", "Bosnia and Herzegovina", ["BA"]),
    ("BE", "Belgium", ["BE"]),
    ("BG", "Bulgaria", ["BG"]),
    ("CH", "Switzerland", ["CH"]),
    ("CY", "Cyprus", ["CY"]),
    ("CZ", "Czechia", ["CZ"]),
    ("DE_LU", "Germany–Luxembourg", ["DE", "LU"]),
    ("DK1", "Denmark West (DK1)", ["DK"]),
    ("DK2", "Denmark East (DK2)", ["DK"]),
    ("EE", "Estonia", ["EE"]),
    ("ES", "Spain", ["ES"]),
    ("FI", "Finland", ["FI"]),
    ("FR", "France", ["FR"]),
    ("GR", "Greece", ["GR"]),
    ("HR", "Croatia", ["HR"]),
    ("HU", "Hungary", ["HU"]),
    ("IE", "Ireland", ["IE"]),
    ("IT-Calabria", "Italy Calabria", ["IT"]),
    ("IT-Centre-North", "Italy Centre-North", ["IT"]),
    ("IT-Centre-South", "Italy Centre-South", ["IT"]),
    ("IT-North", "Italy North", ["IT"]),
    ("IT-Sardinia", "Italy Sardinia", ["IT"]),
    ("IT-Sicily", "Italy Sicily", ["IT"]),
    ("IT-South", "Italy South", ["IT"]),
    ("LT", "Lithuania", ["LT"]),
    ("LV", "Latvia", ["LV"]),
    ("ME", "Montenegro", ["ME"]),
    ("MK", "North Macedonia", ["MK"]),
    ("MT", "Malta", ["MT"]),
    ("NL", "Netherlands", ["NL"]),
    ("NO1", "Norway NO1 (Oslo)", ["NO"]),
    ("NO2", "Norway NO2 (Kristiansand)", ["NO"]),
    ("NO3", "Norway NO3 (Trondheim)", ["NO"]),
    ("NO4", "Norway NO4 (Tromsø)", ["NO"]),
    ("NO5", "Norway NO5 (Bergen)", ["NO"]),
    ("PL", "Poland", ["PL"]),
    ("PT", "Portugal", ["PT"]),
    ("RO", "Romania", ["RO"]),
    ("RS", "Serbia", ["RS"]),
    ("SE1", "Sweden SE1 (Luleå)", ["SE"]),
    ("SE2", "Sweden SE2 (Sundsvall)", ["SE"]),
    ("SE3", "Sweden SE3 (Stockholm)", ["SE"]),
    ("SE4", "Sweden SE4 (Malmö)", ["SE"]),
    ("SI", "Slovenia", ["SI"]),
    ("SK", "Slovakia", ["SK"]),
    ("TR", "Türkiye", ["TR"]),
    ("UK", "United Kingdom", ["GB"]),
]


def _iso(cntr: str) -> str:
    return _NUTS_TO_ISO.get(str(cntr), str(cntr))


def _level_name(level: int) -> str:
    return {0: "country", 1: "nuts1", 2: "nuts2", 3: "nuts3"}[level]


def _region_id(level: int, nuts_id: str) -> str:
    if level == 0:
        return f"region.country.{_iso(nuts_id)}"
    return f"region.{_level_name(level)}.{nuts_id}"


def _parent_id(level: int, nuts_id: str) -> str | None:
    if level == 0:
        return None
    if level == 1:
        return f"region.country.{_iso(nuts_id[:2])}"
    # NUTS2 → NUTS1 (drop last digit), NUTS3 → NUTS2 (drop last digit)
    return f"region.{_level_name(level - 1)}.{nuts_id[:-1]}"


def _entity(
    *,
    name: str,
    long_name: str,
    description: str,
    attrs: dict[str, Any],
    relations: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "attributes": [
            {"id": "name", "value": name},
            {"id": "long_name", "value": long_name},
            {"id": "description", "value": description},
        ],
        "relations": relations or [],
    }
    for key, value in attrs.items():
        if value is None or value == "":
            continue
        out["attributes"].append({"id": key, "value": value})
    return out


def generate_geographical_regions(nuts_path: Path) -> dict[str, dict[str, Any]]:
    import geopandas as gpd

    gdf = gpd.read_file(nuts_path)
    required = {"NUTS_ID", "LEVL_CODE", "CNTR_CODE"}
    missing = required - set(gdf.columns)
    if missing:
        raise ValueError(f"NUTS shapefile missing columns: {sorted(missing)}")

    entities: dict[str, dict[str, Any]] = {}
    for _, row in gdf.iterrows():
        level = int(row["LEVL_CODE"])
        if level not in (0, 1, 2, 3):
            continue
        nuts_id = str(row["NUTS_ID"])
        cntr = str(row["CNTR_CODE"])
        iso = _iso(cntr)
        latin = str(row.get("NAME_LATN") or row.get("NUTS_NAME") or nuts_id)
        level_name = _level_name(level)
        eid = _region_id(level, nuts_id)

        if level == 0:
            long_name = _COUNTRY_LONG_NAME.get(iso) or _COUNTRY_LONG_NAME.get(cntr) or latin
            name = iso
            description = (
                f"Country-level GeographicalRegion for {long_name} "
                f"(ISO {iso}, NUTS 0 / CNTR {cntr})."
            )
        else:
            long_name = latin
            name = nuts_id
            description = (
                f"Eurostat {level_name.upper()} region {nuts_id} ({latin}) "
                f"in country {iso}."
            )

        rels: list[dict[str, str]] = []
        parent = _parent_id(level, nuts_id)
        if parent is not None:
            rels.append({"id": "isSubRegionOf", "target": parent})

        entities[eid] = _entity(
            name=name,
            long_name=long_name,
            description=description,
            attrs={
                "region_level": level_name,
                "nuts_code": nuts_id if level > 0 else cntr,
                "iso_country_code": iso,
            },
            relations=rels,
        )
    return entities


def generate_market_zones(
    country_ids: set[str],
) -> dict[str, dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}
    for code, long_name, countries in _MARKET_ZONES:
        eid = f"market_zone.{code}"
        rels = [{"id": "hasCarrier", "target": "carrier.electricity"}]
        covered = []
        for iso in countries:
            rid = f"region.country.{iso}"
            if rid in country_ids:
                rels.append({"id": "coversRegion", "target": rid})
                covered.append(iso)
        description = (
            f"ENTSO-E-style electricity bidding / market zone {code} ({long_name})."
        )
        if covered:
            description += f" Covers country region(s): {', '.join(covered)}."
        entities[eid] = _entity(
            name=code,
            long_name=long_name,
            description=description,
            attrs={"market_zone_code": code},
            relations=rels,
        )
    return entities


def _dump(path: Path, root_key: str, entities: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stable key order for readable diffs.
    doc = {root_key: {k: entities[k] for k in sorted(entities)}}
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nuts-shapefile", type=Path, default=_DEFAULT_NUTS)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_REPO / "library" / "regions_library",
    )
    args = parser.parse_args(argv)

    if not args.nuts_shapefile.is_file():
        raise SystemExit(f"NUTS shapefile not found: {args.nuts_shapefile}")

    regions = generate_geographical_regions(args.nuts_shapefile)
    countries = {eid for eid, ent in regions.items()
                 if any(a.get("id") == "region_level" and a.get("value") == "country"
                        for a in ent["attributes"])}
    markets = generate_market_zones(countries)

    out = args.output_dir
    _dump(out / "geographical_regions" / "GeographicalRegion.yaml", "GeographicalRegion", regions)
    _dump(out / "market_zones" / "MarketZone.yaml", "MarketZone", markets)

    meta = {
        "description": (
            "CESDM regions & market-zone library — Eurostat NUTS 0–3 GeographicalRegion "
            "entities (name, long_name, description, region_level, nuts_code, "
            "iso_country_code, isSubRegionOf) plus ENTSO-E-style MarketZone entities.\n\n"
            "Import after the default library (carriers are referenced by market zones):\n\n"
            "    model.import_library('library/default_library')\n"
            "    model.import_library('library/regions_library')\n\n"
            "Regenerate from the NUTS shapefile with:\n"
            "    python tools/generate_regions_library.py\n"
        )
    }
    (out / "_metadata.yaml").write_text(
        yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )

    n_by_level = {"country": 0, "nuts1": 0, "nuts2": 0, "nuts3": 0}
    for ent in regions.values():
        for a in ent["attributes"]:
            if a["id"] == "region_level":
                n_by_level[a["value"]] = n_by_level.get(a["value"], 0) + 1
    print(f"Wrote {out}")
    print(f"  GeographicalRegion: {len(regions)}  ({n_by_level})")
    print(f"  MarketZone: {len(markets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
