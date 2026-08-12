"""
Reorganizing cesdm/domain/model/builders.py around one clear rule:
a function belongs there only if it's genuinely generic construction/
query infrastructure (ensure_entity/ensure_carrier/ensure_resource/
ensure_technology, connect_single_port/connect_two_port, attach_profile
and friends) -- not a per-asset-type domain convenience wrapper.
Everything else moved out or was fixed:

1. Read-only query/lookup helpers (views_for_asset, reservoir_for_hydro,
   hydro_units_for_reservoir) moved to accessors.py -- they don't build
   anything, they read existing structure, so mixing them into
   builders.py diluted exactly the "this file means construction"
   signal the reorganization is about.

   get_dispatch_view/get_topology_view/get_powerflow_view/get_view
   (also moved to accessors.py at the time) were later removed
   entirely: since every asset's dispatch/topology/power-flow data
   lives directly on the asset itself, the answer to "does this asset
   support group X" is a static property of its *class*, not something
   that varies per instance -- checked directly against the two real
   call sites (tools/export_pandapower.py, tools/export_matpower.py),
   both of which only ever call it on hardcoded lists of
   GenerationUnit subclasses that always carry dispatch data by
   construction, making the per-entity check dead code in practice.

2. connect_to_bus deleted -- a literal one-line alias for
   connect_single_port, with exactly one external caller
   (tools/import_flexeco.py), updated to call connect_single_port
   directly.

3. ensure_carrier/ensure_resource/ensure_technology fixed to return the
   typed proxy ensure_entity() already computes internally, instead of
   discarding it for a bare id string -- the one thing that made them
   genuinely differ from calling ensure_entity(<fixed class name>, ...)
   directly, and they weren't even doing that correctly before.

(All the per-asset-type domain convenience wrappers this reorganization
originally kept in builders.py alongside the generic infrastructure --
add_generator, add_bus, create_generation_unit, and the rest -- were
removed entirely later, along with GeneratedBuildersMixin/
generated_builders.py's add_<EntityClass>() constructors, requested
directly. See CHANGELOG.md.)
"""

from cesdm_toolbox import build_model_from_yaml
from cesdm.generated_proxies import CarrierProxy, NaturalResourceProxy, GeneratorTypeProxy


def _model():
    return build_model_from_yaml("schemas/cesdm")


def test_moved_query_functions_still_work_from_accessors():
    model = _model()
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    model.add_entity("HydroGenerationUnit", "hydro.1")
    model.add_relation("hydro.1", "atNode", "bus.1")
    model.add_attribute("hydro.1", "nominal_power_capacity", 100)
    model.add_entity("HydraulicStorageUnit", "reservoir.1")
    model.add_relation("hydro.1", "drawsFromHydraulicStorage", "reservoir.1")

    # reservoir_for_hydro / hydro_units_for_reservoir: genuinely generic
    # relation lookups, still live in accessors.py.
    assert model.reservoir_for_hydro("hydro.1") == "reservoir.1"
    assert model.hydro_units_for_reservoir("reservoir.1") == ["hydro.1"]

    # get_dispatch_view/get_topology_view/get_powerflow_view/get_view no
    # longer exist at all -- see the module docstring above.
    assert not hasattr(model, "get_dispatch_view")
    assert not hasattr(model, "get_topology_view")
    assert not hasattr(model, "get_powerflow_view")
    assert not hasattr(model, "get_view")


def test_reservoir_hydro_query_helpers_still_work_from_accessors():
    model = _model()
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    model.add_entity("HydraulicStorageUnit", "reservoir.1")
    model.add_entity("HydroGenerationUnit", "gen.hydro.1")
    model.add_relation("gen.hydro.1", "atNode", "bus.1")
    model.add_relation("gen.hydro.1", "drawsFromHydraulicStorage", "reservoir.1")
    model.add_attribute("gen.hydro.1", "nominal_power_capacity", 50)
    reservoir, gen = "reservoir.1", "gen.hydro.1"

    assert model.reservoir_for_hydro(gen) == reservoir
    assert gen in model.hydro_units_for_reservoir(reservoir)


def test_connect_to_bus_no_longer_exists():
    """Deleted -- was a literal one-line alias for connect_single_port."""
    model = _model()
    assert not hasattr(model, "connect_to_bus")


def test_ensure_carrier_returns_the_typed_proxy_not_a_bare_string():
    model = _model()
    carrier = model.ensure_carrier("carrier.test", name="Test Carrier")
    assert isinstance(carrier, CarrierProxy)
    assert carrier == "carrier.test"  # still usable as a plain string everywhere
    assert model.get_attribute_value(carrier, "name") == "Test Carrier"


def test_ensure_resource_returns_the_typed_proxy_not_a_bare_string():
    model = _model()
    resource = model.ensure_resource("resource.test", name="Test Resource")
    assert isinstance(resource, NaturalResourceProxy)
    assert resource == "resource.test"


def test_ensure_technology_returns_the_typed_proxy_not_a_bare_string():
    model = _model()
    tech = model.ensure_technology("Test.Technology")
    assert isinstance(tech, GeneratorTypeProxy)
    assert tech == "Test.Technology"


def test_ensure_carrier_return_value_supports_direct_attribute_assignment():
    """The whole point of returning a typed proxy instead of a bare
    string: it can be used with the object-oriented API immediately,
    not just re-passed around as an id."""
    model = _model()
    carrier = model.ensure_carrier("carrier.test2", name="Test")
    carrier.co2_emission_intensity = 0.5
    assert model.get_attribute_value(carrier, "co2_emission_intensity") == 0.5
