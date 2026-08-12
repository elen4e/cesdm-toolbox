"""Smoke-test the Conversion Units demo example."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_conversion_units_demo_builds_and_validates():
    import sys

    sys.path.insert(0, str(REPO_ROOT / "examples"))
    from example_conversion_units import build_conversion_units_demo

    model = build_conversion_units_demo(REPO_ROOT / "schemas" / "cesdm")
    assert model.validate() == []
    assert model.has_entity("conv.hub.heat_pump")
    assert model.has_entity("conv.hub.electrolyser")
    assert model.has_entity("conv.hub.boiler")
    assert model.has_entity("conv.hub.fuel_cell")
    assert model.has_entity("conv.hub.chp")
    assert model.get_relation_targets("conv.hub.electrolyser", "atHydrogenNode") == [
        "bus.hub.h2"
    ]
    assert model.get_attribute_value("conv.hub.heat_pump", "coefficient_of_performance") == 3.5
