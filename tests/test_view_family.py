"""
The proxy API's `.dispatch`/`.power_flow`/`.topology`/etc. resolution
is driven by `belongsToGroup`, declared directly on an asset's own
attributes/relations, and `cesdm.proxy.EntityProxy._view()` resolves a
keyword against a hardcoded, known set of groups (`_KNOWN_GROUPS`)
rather than schema introspection. "dynamics" (the machine model's
fully semantic-named attributes, e.g. `d_axis_synchronous_reactance`)
works the same way, but lives on a standalone
`DynamicMachineModelType.Synchronous` entity rather than on `GenerationUnit`
itself -- the dynamic-model family is an independent dimension from
generation technology (a wind turbine has no synchronous machine at
all), so it isn't flattened onto the generator the way dispatch/
topology/power-flow are. Its schema defaults are resolved lazily on
read rather than written unconditionally at entity-creation time, so a
bare entity never gets the group activated just from existing (see
ear/model/entity_ops.py's add_entity()).

See docs/architecture/proxy_api.md and docs/guide/05_attribute_groups.md.
"""

import pytest

from cesdm_toolbox import build_model_from_yaml
from cesdm.proxy import EntityProxy, FlatGroupViewProxy


@pytest.fixture(scope="module")
def model():
    return build_model_from_yaml("schemas/cesdm")


# ---------------------------------------------------------------------
# Flattened groups resolve via belongsToGroup
# ---------------------------------------------------------------------

def test_generation_unit_dispatch_resolves_to_flat_group_view_proxy(model):
    model.add_entity("GenerationUnit", "gen.vf.dispatch")
    gen = model.get_entity("gen.vf.dispatch")
    assert isinstance(gen.dispatch, FlatGroupViewProxy)
    assert gen.dispatch.view_class == "dispatch"


def test_generation_unit_topology_and_powerflow_also_resolve(model):
    model.add_entity("GenerationUnit", "gen.vf.multi")
    gen = model.get_entity("gen.vf.multi")
    assert isinstance(gen.topology, FlatGroupViewProxy)
    assert isinstance(gen.power_flow, FlatGroupViewProxy)


def test_flat_and_namespace_alias_access_share_the_same_storage(model):
    model.add_entity("GenerationUnit", "gen.vf.shared")
    gen = model.get_entity("gen.vf.shared")
    gen.dispatch.nominal_power_capacity = 400.0
    assert gen.nominal_power_capacity == 400.0
    gen.variable_operating_cost = 25.0
    assert gen.dispatch.variable_operating_cost == 25.0


def test_electrical_bus_spatial_group_resolves(model):
    model.add_entity("ElectricalBus", "bus.vf.spatial")
    bus = model.get_entity("bus.vf.spatial")
    assert isinstance(bus.spatial, FlatGroupViewProxy)
    bus.spatial.latitude = 47.3
    assert bus.latitude == 47.3


def test_gas_bus_inherits_spatial_group_from_network_node(model):
    """Spatial attrs live on NetworkNode; every typed bus inherits them."""
    model.add_entity("GasBus", "bus.vf.gas.spatial")
    bus = model.get_entity("bus.vf.gas.spatial")
    assert isinstance(bus.spatial, FlatGroupViewProxy)
    bus.spatial.longitude = 8.5
    assert bus.longitude == 8.5


# ---------------------------------------------------------------------
# Recognized group, but unavailable for this asset class -> specific error
# ---------------------------------------------------------------------

def test_recognized_group_but_unavailable_for_asset_gives_specific_error(model):
    model.add_entity("GeographicalRegion", "region.vf.test")
    region = model.get_entity("region.vf.test")
    with pytest.raises(AttributeError, match="dispatch"):
        _ = region.dispatch


def test_unrecognized_keyword_falls_through_to_generic_error(model):
    model.add_entity("GenerationUnit", "gen.vf.typo")
    gen = model.get_entity("gen.vf.typo")
    with pytest.raises(AttributeError):
        _ = gen.dispach  # typo, not a real group


# ---------------------------------------------------------------------
# The "dynamic" special case: a standalone DynamicModel.* entity
# ---------------------------------------------------------------------

def test_dynamic_resolves_to_flat_group_view_proxy_with_lazy_defaults():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "gen.dynamics.test")
    model.add_entity("DynamicMachineModelType.Synchronous", "dyn.dynamics.test")
    dm = model.get_entity("dyn.dynamics.test")

    # Lazy default, nothing explicitly set, nothing written into entity data.
    assert dm.dynamics.d_axis_synchronous_reactance == 1.8
    assert "d_axis_synchronous_reactance" not in model.entity_data("dyn.dynamics.test")

    dm.dynamics.inertia_constant = 6.5
    assert dm.dynamics.inertia_constant == 6.5
    assert dm.inertia_constant == 6.5  # same storage, flat access


def test_bare_generation_unit_dynamic_group_stays_inactive():
    """A bare GenerationUnit (no linked DynamicMachineModelType at all) has
    no dynamics-tagged attributes of its own whatsoever -- unlike
    dispatch/topology/power_flow, which do live directly on
    GenerationUnit and only "activate" their required fields once
    something in the group is set."""
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "gen.no.dynamics")
    model.add_attribute("gen.no.dynamics", "name", "gen.no.dynamics")
    assert model.validate() == []


# ---------------------------------------------------------------------
# Controllers are standalone entities, not resolved via ._view() at all
# ---------------------------------------------------------------------

def test_controllers_are_not_resolved_as_a_view_family():
    """AVR/governor/PSS controllers are linked via controlsGenerationUnit,
    not reportsOn, and are never found through ._view() -- they're
    created and read directly, the same pattern as
    HydroGenerationUnit.drawsFromHydraulicStorage."""
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "gen.controllers.test")
    gen = "gen.controllers.test"

    model.add_entity("Controller.AVR.SEXS", "avr.controllers.test")
    model.add_relation("avr.controllers.test", "controlsGenerationUnit", gen)
    avr = "avr.controllers.test"

    model.add_entity("Controller.GOV.IEEEG1", "gov.controllers.test")
    model.add_relation("gov.controllers.test", "controlsGenerationUnit", gen)
    model.add_attribute("gov.controllers.test", "GOV_Pmax", 1.0)
    gov = "gov.controllers.test"

    model.add_entity("Controller.PSS.STAB1", "pss.controllers.test")
    model.add_relation("pss.controllers.test", "controlsGenerationUnit", gen)
    pss = "pss.controllers.test"

    assert model.entity_class(str(avr)) == "Controller.AVR.SEXS"
    assert model.entity_class(str(gov)) == "Controller.GOV.IEEEG1"
    assert model.entity_class(str(pss)) == "Controller.PSS.STAB1"
    assert {str(avr), str(gov), str(pss), str(gen)} == {
        "avr.controllers.test", "gov.controllers.test", "pss.controllers.test", "gen.controllers.test",
    }
    for controller_id in (avr, gov, pss):
        assert model.get_relation_targets(str(controller_id), "controlsGenerationUnit") == [str(gen)]
