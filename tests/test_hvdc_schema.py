"""
HVDCLink's own distinguishing features: converter technology is
represented by a single `converter_technology` attribute (an enum of
`LCC`/`VSC`), not by subclasses -- so, unlike most other asset
classes, there's genuinely class-specific behavior here worth pinning
down beyond "can this class be created at all" (already covered
generically by countless other tests). Found while reviewing the test
suite for continued relevance: the original version of this file only
checked basic entity creation, duplicating what dozens of other tests
already do, without touching any of the schema features that actually
make HVDCLink distinct. See CHANGELOG.md.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cesdm_toolbox import build_model_from_yaml


def test_hvdc_link_can_be_created_and_typed():
    model = build_model_from_yaml(ROOT / "schemas/cesdm")
    model.add_entity("HVDCLink", "hvdc.test")
    model.add_attribute("hvdc.test", "converter_technology", "VSC")
    entity = model.entities["HVDCLink"]["hvdc.test"]
    assert entity.data["converter_technology"]["value"] == "VSC"


def test_converter_technology_rejects_a_value_outside_the_enum():
    """converter_technology is deliberately an enum (LCC/VSC), not a
    free-text string -- the whole point of representing converter
    technology this way instead of via subclasses is that validate()
    can catch a typo/invalid value directly."""
    model = build_model_from_yaml(ROOT / "schemas/cesdm")
    model.add_entity("HVDCLink", "hvdc.bad")
    model.add_attribute("hvdc.bad", "converter_technology", "MMC")  # not LCC or VSC
    errors = model.validate()
    assert any("converter_technology" in e for e in errors)


def test_hvdc_link_required_fields_are_enforced():
    """max_flow is schema-optional; analysis profiles (optimal_dispatch /
    power_flow) require it when an HVDC link is present."""
    model = build_model_from_yaml(ROOT / "schemas/cesdm")
    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_group="electricity")
    model.add_entity("CarrierDomain", "domain.electricity")
    model.add_relation("domain.electricity", "hasCarrier", "carrier.electricity")
    for bid in ("bus.1", "bus.2"):
        model.add_entity("ElectricalBus", bid)
        model.add_relation(bid, "belongsToCarrierDomain", "domain.electricity")
        model.add_attribute(bid, "nominal_voltage", 380)
        model.add_attribute(bid, "powerflow_bus_type", "PQ" if bid == "bus.2" else "slack")
    model.add_entity("HVDCLink", "hvdc.bare")
    model.add_relation("hvdc.bare", "fromNode", "bus.1")
    model.add_relation("hvdc.bare", "toNode", "bus.2")
    assert model.validate() == []  # schema-clean without max_flow

    errors = model.validate_for_analysis("power_flow")
    assert any("hvdc.bare" in e and "max_flow" in e for e in errors)


def test_hvdc_link_power_flow_and_dispatch_groups_are_flattened():
    """Both belongsToGroup families HVDCLink declares work like every
    other asset class's flattened groups: .power_flow/.dispatch alias
    directly onto the asset's own data, no separate view entity."""
    model = build_model_from_yaml(ROOT / "schemas/cesdm")
    model.add_entity("HVDCLink", "hvdc.flat")
    hvdc = model.get_entity("hvdc.flat")

    hvdc.power_flow.converter_technology = "LCC"
    hvdc.power_flow.max_flow = 1000.0
    hvdc.dispatch.variable_operating_cost = 2.5

    assert hvdc.converter_technology == "LCC"  # flat access, same storage
    assert hvdc.max_flow == 1000.0
    assert model.validate() == []


def test_legacy_hvdc_attribute_aliases_remap_on_write():
    model = build_model_from_yaml(ROOT / "schemas/cesdm")
    model.add_entity("HVDCLink", "hvdc.alias")
    model.add_attribute("hvdc.alias", "hvdc_technology_type", "VSC")
    model.add_attribute("hvdc.alias", "p_max_hvdc", 800.0)
    hvdc = model.get_entity("hvdc.alias")
    assert hvdc.converter_technology == "VSC"
    assert hvdc.max_flow == 800.0
