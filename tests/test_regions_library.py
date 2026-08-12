"""Regions library: NUTS GeographicalRegions + MarketZones."""

from __future__ import annotations

from pathlib import Path

from cesdm.helpers import build_model_from_yaml

ROOT = Path(__file__).resolve().parents[1]


def _model_with_regions():
    model = build_model_from_yaml(str(ROOT / "schemas" / "cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))
    model.import_library(str(ROOT / "library" / "regions_library"))
    return model


def test_regions_library_loads_countries_nuts_and_market_zones():
    model = _model_with_regions()

    ch = model.get_entity("region.country.CH")
    assert ch.long_name == "Switzerland"
    assert ch.region_level == "country"
    assert ch.iso_country_code == "CH"

    nuts1 = model.get_entity("region.nuts1.CH0")
    assert nuts1.isSubRegionOf.id == "region.country.CH"

    mz = model.get_entity("market_zone.CH")
    assert mz.market_zone_code == "CH"
    assert mz.hasCarrier.id == "carrier.electricity"
    assert "region.country.CH" in {r.id for r in (mz.coversRegion if isinstance(mz.coversRegion, list) else [mz.coversRegion])}

    n_regions = len(model.entities.get("GeographicalRegion") or {})
    n_zones = len(model.entities.get("MarketZone") or {})
    assert n_regions >= 2000  # full NUTS 0–3 catalogue
    assert n_zones >= 40


def test_bus_can_belong_to_market_zone():
    model = _model_with_regions()
    bus = model.add_entity("ElectricalBus", "bus.test")
    bus.belongsToCarrierDomain = "domain.electricity"
    bus.belongsToGeographicalRegion = "region.country.CH"
    bus.belongsToMarketZone = "market_zone.CH"
    assert bus.belongsToMarketZone.id == "market_zone.CH"
    assert model.validate() == []


def test_market_zone_covers_multiple_countries():
    model = _model_with_regions()
    targets = set(model.get_relation_targets("market_zone.DE_LU", "coversRegion"))
    assert targets == {"region.country.DE", "region.country.LU"}
