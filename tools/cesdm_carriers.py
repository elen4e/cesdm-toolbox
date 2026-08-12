"""
cesdm_carriers.py
=================

Shared energy carrier constants and entity creation helper for CESDM V4.

Used by:
    example_import_export_tyndp.py
    import_pypsa_nc.py

Canonical carrier ids
---------------------
All carrier entity ids follow the hierarchical naming convention:

    carrier.{type}.{family}.{subfamily}.{variant}

Examples:
    carrier.electricity
    carrier.fuel.fossil.gas.natural_gas
    carrier.fuel.fossil.coal.hard_coal
    carrier.fuel.nuclear.uranium
    resource.renewable.wind
    carrier.hydrogen
    resource.water

Canonical domain ids follow:

    domain.{carrier_slug}

Examples:
    domain.electricity
    domain.gas
    domain.heat
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cesdm_toolbox import CesdmModel

# ---------------------------------------------------------------------------
# Canonical ids
# ---------------------------------------------------------------------------

ELECTRICITY_CARRIER_ID = "carrier.electricity"
ELECTRICITY_DOMAIN_ID  = "domain.electricity"

# ---------------------------------------------------------------------------
# Carrier name → canonical id
# Covers PyPSA carrier strings, TYNDP fuel names, and common aliases.
# ---------------------------------------------------------------------------

CARRIER_ID_MAP: dict[str, str] = {
    # Electricity
    "electricity":          "carrier.electricity",
    "ac":                   "carrier.electricity",
    "dc":                   "carrier.electricity",
    "AC":                   "carrier.electricity",
    "DC":                   "carrier.electricity",

    # Fossil gas
    "natural_gas":          "carrier.fuel.fossil.gas.natural_gas",
    "gas":                  "carrier.fuel.fossil.gas.natural_gas",
    "Gas":                  "carrier.fuel.fossil.gas.natural_gas",
    "CCGT":                 "carrier.fuel.fossil.gas.natural_gas",
    "OCGT":                 "carrier.fuel.fossil.gas.natural_gas",

    # Coal
    "hard_coal":            "carrier.fuel.fossil.coal.hard_coal",
    "coal":                 "carrier.fuel.fossil.coal.hard_coal",
    "lignite":              "carrier.fuel.fossil.coal.lignite",

    # Oil
    "oil":                  "carrier.fuel.fossil.oil",
    "light_oil":            "carrier.fuel.fossil.oil.light",
    "heavy_oil":            "carrier.fuel.fossil.oil.heavy",
    "oil_shale":            "carrier.fuel.fossil.oil.shale",

    # Biofuel
    "biomass":              "carrier.fuel.biofuel.biomass",
    "biogas":               "carrier.fuel.biofuel.biomass",

    # Nuclear
    "uranium":              "carrier.fuel.nuclear.uranium",
    "nuclear":              "carrier.fuel.nuclear.uranium",

    # Renewables (resource carriers)
    "solar":                "resource.renewable.solar",
    "solar_pv":             "resource.renewable.solar",
    "pv":                   "resource.renewable.solar",
    "wind":                 "resource.renewable.wind",
    "onwind":               "resource.renewable.wind",
    "offwind":              "resource.renewable.wind",
    "offwind-ac":           "resource.renewable.wind",
    "offwind-dc":           "resource.renewable.wind",
    "ror":                  "resource.water",
    "hydro":                "resource.water",
    "water":                "resource.water",
    "run_of_river":         "resource.water",

    # Hydrogen
    "hydrogen":             "carrier.hydrogen",
    "H2":                   "carrier.hydrogen",
    "h2":                   "carrier.hydrogen",

    # Heat
    "heat":                 "carrier.heat",
    "Heat":                 "carrier.heat",

    # Other
    "other":                "carrier.other",
    "others_renewable":     "carrier.other.renewable",
    "others_non_renewable": "carrier.other.non_renewable",
}

# ---------------------------------------------------------------------------
# CO₂ emission intensity  (t CO₂ / MWh fuel input)
# ---------------------------------------------------------------------------

CARRIER_CO2: dict[str, float] = {
    "carrier.fuel.fossil.gas.natural_gas":  0.2052,
    "carrier.fuel.fossil.coal.hard_coal":   0.3384,
    "carrier.fuel.fossil.coal.lignite":     0.3636,
    "carrier.fuel.fossil.oil":              0.2808,
    "carrier.fuel.fossil.oil.light":        0.2808,
    "carrier.fuel.fossil.oil.heavy":        0.2808,
    "carrier.fuel.fossil.oil.shale":        0.3600,
    "carrier.fuel.biofuel.biomass":         0.0,
    "carrier.hydrogen":                     0.0,
    "carrier.fuel.nuclear.uranium":         0.0,
    "resource.renewable.solar":     0.0,
    "resource.renewable.wind":      0.0,
    "resource.water":               0.0,
    "carrier.electricity":                  0.0,
    "carrier.heat":                         0.0,
    "carrier.other":                        0.0,
    "carrier.other.renewable":              0.0,
    "carrier.other.non_renewable":          0.2,
}

# ---------------------------------------------------------------------------
# Carrier cost  (EUR / MWh fuel input)   — year → carrier → cost
# ---------------------------------------------------------------------------

CARRIER_PRICE: dict[int, dict[str, float]] = {
    2030: {
        "carrier.fuel.fossil.gas.natural_gas":  22.68,
        "carrier.fuel.fossil.coal.hard_coal":    6.48,
        "carrier.fuel.fossil.coal.lignite":      7.18,
        "carrier.fuel.fossil.oil":              34.56,
        "carrier.fuel.fossil.oil.heavy":        34.56,
        "carrier.fuel.fossil.oil.light":        42.12,
        "carrier.fuel.fossil.oil.shale":         6.84,
        "carrier.fuel.biofuel.biomass":         67.68,
        "carrier.hydrogen":                     63.36,
        "carrier.fuel.nuclear.uranium":          6.12,
        "resource.renewable.solar":      0.0,
        "resource.renewable.wind":       0.0,
        "resource.water":                0.0,
        "carrier.electricity":                   0.0,
        "carrier.heat":                          0.0,
    },
    2040: {
        "carrier.fuel.fossil.gas.natural_gas":  20.52,
        "carrier.fuel.fossil.coal.hard_coal":    5.76,
        "carrier.fuel.fossil.coal.lignite":      6.48,
        "carrier.fuel.fossil.oil":              32.04,
        "carrier.fuel.fossil.oil.heavy":        33.48,
        "carrier.fuel.fossil.oil.light":        41.04,
        "carrier.fuel.fossil.oil.shale":         9.72,
        "carrier.fuel.biofuel.biomass":         64.80,
        "carrier.hydrogen":                     54.36,
        "carrier.fuel.nuclear.uranium":          6.12,
        "resource.renewable.solar":      0.0,
        "resource.renewable.wind":       0.0,
        "resource.water":                0.0,
        "carrier.electricity":                   0.0,
        "carrier.heat":                          0.0,
    },
    2050: {
        "carrier.fuel.fossil.gas.natural_gas":  18.00,
        "carrier.fuel.fossil.coal.hard_coal":    5.40,
        "carrier.fuel.fossil.coal.lignite":      6.48,
        "carrier.fuel.fossil.oil":              30.96,
        "carrier.fuel.fossil.oil.heavy":        32.40,
        "carrier.fuel.fossil.oil.light":        39.60,
        "carrier.fuel.fossil.oil.shale":        14.04,
        "carrier.fuel.biofuel.biomass":         62.28,
        "carrier.hydrogen":                     54.36,
        "carrier.fuel.nuclear.uranium":          6.12,
        "resource.renewable.solar":      0.0,
        "resource.renewable.wind":       0.0,
        "resource.water":                0.0,
        "carrier.electricity":                   0.0,
        "carrier.heat":                          0.0,
    },
}

# ---------------------------------------------------------------------------
# Domain name → canonical domain id
# ---------------------------------------------------------------------------

DOMAIN_ID_MAP: dict[str, str] = {
    "electricity":  "domain.electricity",
    "gas":          "domain.gas",
    "heat":         "domain.heat",
    "hydrogen":     "domain.hydrogen",
    "water":        "domain.water",
}

# ---------------------------------------------------------------------------
# Carrier lookup helpers
# ---------------------------------------------------------------------------

def canonical_carrier_id(name: str) -> str:
    """
    Return the canonical carrier entity id for a carrier name string.

    Checks CARRIER_ID_MAP first (exact match then lower-case match).
    Falls back to ``carrier.{slugified_name}`` for unknown carriers.
    """
    if name is None:
        return ELECTRICITY_CARRIER_ID
    cid = CARRIER_ID_MAP.get(name) or CARRIER_ID_MAP.get(name.lower())
    if cid:
        return cid
    import re
    slug = re.sub(r"[^a-z0-9]+", ".", name.lower().strip()).strip(".")
    return f"carrier.{slug}"

def canonical_domain_id(carrier_id: str) -> str:
    """
    Return the canonical domain entity id for a carrier id.

    Derives the domain from the carrier id by taking the first
    meaningful segment after ``carrier.``:
        carrier.electricity          → domain.electricity
        carrier.fuel.fossil.gas.*   → domain.gas
        carrier.fuel.nuclear.*      → domain.nuclear
            resource.renewable.*       → domain.electricity  (coupled)
        resource.water       → domain.water
        carrier.hydrogen             → domain.hydrogen
        carrier.heat                 → domain.heat
    """
    if carrier_id == "carrier.electricity":
        return "domain.electricity"
    if "fossil.gas" in carrier_id:
        return "domain.gas"
    if "fossil.coal" in carrier_id:
        return "domain.coal"
    if "fossil.oil" in carrier_id:
        return "domain.oil"
    if "nuclear" in carrier_id:
        return "domain.nuclear"
    if "biofuel" in carrier_id:
        return "domain.biofuel"
    if "renewable" in carrier_id:
        return "domain.electricity"   # renewables feed electricity domain
    if "water" in carrier_id:
        return "domain.water"
    if "hydrogen" in carrier_id:
        return "domain.hydrogen"
    if "heat" in carrier_id:
        return "domain.heat"
    # fallback: derive from carrier id
    seg = carrier_id.replace("carrier.", "").split(".")[0]
    return f"domain.{seg}"

# ---------------------------------------------------------------------------
# Entity creation helper
# ---------------------------------------------------------------------------

def ensure_carrier_entities(
    model: "CesdmModel",
    carrier_id: str,
    *,
    year: int | None = None,
) -> tuple[str, str]:
    """
    Ensure a Carrier or NaturalResource entity exists.

    ``carrier.*`` ids create Carrier + CarrierDomain(hasCarrier).
    ``resource.*`` ids create NaturalResource only; resources are not transported
    carriers and therefore are not attached to CarrierDomain.hasCarrier. The
    returned domain id is the coupled network domain used by importing helpers.
    """
    domain_id = canonical_domain_id(carrier_id)
    price_year = year if year in CARRIER_PRICE else min(CARRIER_PRICE, key=lambda y: abs(y - (year or 2030)))

    if carrier_id.startswith("resource."):
        if carrier_id not in model.entities.get("NaturalResource", {}):
            model.add_entity(entity_class="NaturalResource", entity_id=carrier_id)
            name = carrier_id.split(".")[-1].replace("_", " ").title()
            model.add_attribute(carrier_id, "name", name)
            if "wind" in carrier_id:
                model.add_attribute(carrier_id, "resource_type", "wind")
            elif "solar" in carrier_id:
                model.add_attribute(carrier_id, "resource_type", "solar_irradiance")
            elif "water" in carrier_id:
                model.add_attribute(carrier_id, "resource_type", "water_inflow")
        return carrier_id, domain_id

    # Carrier
    if carrier_id not in model.entities.get("Carrier", {}):
        model.add_entity(entity_class="Carrier", entity_id=carrier_id)
        name = carrier_id.split(".")[-1].replace("_", " ").title()
        model.add_attribute(carrier_id, "name", name)
        model.add_attribute(carrier_id, "co2_emission_intensity",
                            CARRIER_CO2.get(carrier_id, 0.0))
        model.add_attribute(carrier_id, "energy_carrier_cost",
                            CARRIER_PRICE.get(price_year, {}).get(carrier_id, 0.0))

    # CarrierDomain
    if domain_id not in model.entities.get("CarrierDomain", {}):
        model.add_entity(entity_class="CarrierDomain", entity_id=domain_id)
        seg = domain_id.replace("domain.", "").replace("_", " ").title()
        model.add_attribute(domain_id, "name", f"{seg} domain")
        model.add_relation(domain_id, "hasCarrier", carrier_id)

    return carrier_id, domain_id

def ensure_all_carriers(
    model: "CesdmModel",
    carrier_ids: list[str],
    *,
    year: int | None = None,
) -> dict[str, tuple[str, str]]:
    """
    Ensure carrier + domain entities for a list of carrier ids.

    Returns {carrier_id: (carrier_entity_id, domain_entity_id)}.
    Always includes electricity.
    """
    all_ids = list(dict.fromkeys([ELECTRICITY_CARRIER_ID] + list(carrier_ids)))
    result = {}
    for cid in all_ids:
        result[cid] = ensure_carrier_entities(model, cid, year=year)
    return result
