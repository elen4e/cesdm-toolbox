"""
cesdm.proxy — the object-oriented ergonomics layer discussed with the
user (see CHANGELOG.md, "EntityProxy/ViewProxy object-oriented API").
Everything here is a thin wrapper over the existing low-level EAR API;
these tests exist to prove that wrapping is (a) correct and (b) 100%
backward compatible with code that treats an entity id as a plain
string id.

Built with core EAR calls (add_entity/add_attribute/add_relation) plus
get_entity()/EntityProxy for reading/writing -- there are no more
add_<x>()/create_<x>() builder-function constructors at all (see
CHANGELOG.md: builders.py kept minimal, generated_builders.py removed
entirely).
"""

import pytest

from cesdm_toolbox import build_model_from_yaml
from cesdm.proxy import EntityProxy, ViewProxy, FlatGroupViewProxy


def _model_with_bus():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("EnergySystemModel", "sys1")
    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_group="electricity")
    model.add_entity("CarrierDomain", "domain.electricity")
    model.add_relation("domain.electricity", "hasCarrier", "carrier.electricity")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_entity("ElectricalBus", "bus.2")
    model.add_relation("bus.1", "belongsToCarrierDomain", "domain.electricity")
    model.add_relation("bus.2", "belongsToCarrierDomain", "domain.electricity")
    return model


def _add_generator(model, gen_id, *, bus_id=None, nominal_power_capacity=None):
    model.add_entity("GenerationUnit", gen_id)
    model.set_technology(gen_id, "Generation.Nuclear.LWR", technology_class="GeneratorType")
    if bus_id:
        model.add_relation(gen_id, "atNode", bus_id)
    gen = model.get_entity(gen_id)
    if nominal_power_capacity is not None:
        gen.dispatch.nominal_power_capacity = nominal_power_capacity
    return gen


# ---------------------------------------------------------------------
# Backward compatibility: EntityProxy IS a plain string everywhere
# ---------------------------------------------------------------------

def test_asset_proxy_is_a_real_string_subclass():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1", bus_id="bus.1")
    assert isinstance(gen, str)
    assert isinstance(gen, EntityProxy)


def test_asset_proxy_equals_and_hashes_like_the_plain_id():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1", bus_id="bus.1")
    assert gen == "gen1"
    assert {gen: "value"}["gen1"] == "value"
    assert {"gen1": "value"}[gen] == "value"


def test_existing_low_level_methods_accept_asset_proxy_transparently():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1", bus_id="bus.1")
    # every one of these takes a plain entity-id string in the existing API
    assert model.entity_class(gen) == "GenerationUnit"
    assert model.has_entity(gen)
    assert model.get_relation_targets(gen, "hasTechnology") == ["Generation.Nuclear.LWR"]


def test_get_entity_always_returns_asset_proxy():
    model = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.w")
    model.set_technology("gen.w", "Generation.Renewable.Wind.Onshore", technology_class="GeneratorType")
    model.add_entity("StorageUnit", "stor.1")
    model.add_entity("DemandUnit", "dem.1")
    model.add_entity("TransmissionLine", "line.1")
    model.add_relation("line.1", "fromNode", "bus.1")
    model.add_relation("line.1", "toNode", "bus.2")
    model.add_entity("HVDCLink", "hvdc.1")
    model.add_relation("hvdc.1", "fromNode", "bus.1")
    model.add_relation("hvdc.1", "toNode", "bus.2")
    model.add_entity("ElectricalBus", "bus.3")
    model.add_relation("bus.3", "belongsToCarrierDomain", "domain.electricity")
    for entity_id in ("gen.w", "stor.1", "dem.1", "line.1", "hvdc.1", "bus.3"):
        obj = model.get_entity(entity_id)
        assert isinstance(obj, EntityProxy)
        assert isinstance(obj, str)


# ---------------------------------------------------------------------
# The object-oriented API itself
# ---------------------------------------------------------------------

def test_generation_unit_top_level_entry_point():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1", bus_id="bus.1")
    assert model.get_relation_targets(gen, "hasTechnology") == ["Generation.Nuclear.LWR"]
    assert model.get_relation_targets(gen, "atNode") == ["bus.1"]


def test_dispatch_view_property_get_and_set():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1", bus_id="bus.1", nominal_power_capacity=1600)
    # GenerationUnit supports the flattened pattern -- gen.dispatch is a
    # FlatGroupViewProxy over the asset's own data now, not a separate
    # view entity, but the read/write interface is identical.
    assert isinstance(gen.dispatch, FlatGroupViewProxy)
    assert gen.dispatch.nominal_power_capacity == 1600.0
    gen.dispatch.maximum_generation = 1550
    assert gen.dispatch.maximum_generation == 1550.0


def test_view_auto_attaches_unit_when_unambiguous():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1", bus_id="bus.1")
    gen.dispatch.nominal_power_capacity = 1600
    raw = model.entity_data(gen.dispatch.id)["nominal_power_capacity"]
    assert isinstance(raw, dict) and raw.get("unit") == "MW"


def test_view_setattr_rejects_unknown_attribute_with_suggestion():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1", bus_id="bus.1")
    with pytest.raises(AttributeError, match="nominal_power_capacity"):
        gen.dispatch.nominal_power_capaciyt = 100  # typo


def test_connect_single_port():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1")
    gen.connect("bus.1")
    # atNode is a plain relation declared directly on the asset.
    assert model.get_relation_targets(gen, "atNode") == ["bus.1"]


def test_connect_two_port():
    model = _model_with_bus()
    model.add_entity("TransmissionLine", "line.2")
    line2 = model.get_entity("line.2")
    line2.connect("bus.1", "bus.2")
    assert model.get_relation_targets("line.2", "fromNode") == ["bus.1"]
    assert model.get_relation_targets("line.2", "toNode") == ["bus.2"]


def test_connect_wrong_arity_raises():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1")
    with pytest.raises(TypeError):
        gen.connect("bus.1", "bus.2", "bus.3")


def test_unknown_view_keyword_raises_clear_error():
    model = _model_with_bus()
    gen = _add_generator(model, "gen1")
    with pytest.raises(AttributeError, match="dispatch"):
        gen.dispach  # typo -- must suggest "dispatch"


def test_asset_helper_wraps_existing_entity():
    model = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.manual")
    wrapped = model.get_entity("gen.manual")
    assert isinstance(wrapped, EntityProxy)
    assert wrapped == "gen.manual"
    assert wrapped.entity_class == "GenerationUnit"


def test_full_end_to_end_scenario_validates():
    """Mirrors the user's own worked example (points 1-5 of the API proposal)."""
    model = _model_with_bus()
    gen = _add_generator(model, "gen1")
    gen.dispatch.nominal_power_capacity = 1600
    gen.dispatch.maximum_generation = 1550
    gen.connect("bus.1")
    model.validate_or_raise()  # must not raise
