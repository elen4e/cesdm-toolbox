"""
add_entity/add_relation/add_attribute used to store whatever object was
passed for an id-like parameter as-is, without coercing to a plain
`str`. Since EntityProxy is a `str` *subclass*, passing one through
(e.g. `gen.connect(bus)` where `bus` came from `model.get_entity(...)`,
or `model.ensure_entity("GenericInterconnector", ...)` returning an EntityProxy
that then gets used as a relation target elsewhere) stored the
EntityProxy object itself in entity data. This is invisible almost
everywhere -- equality, hashing, and dict-key lookup treat a str
subclass identically to a plain str -- but PyYAML's representer
dispatch is exact-type (`type(data)`), not isinstance-based, so
`export_yaml_hierarchical()` crashed with `RepresenterError: cannot
represent an object` the first time a stored EntityProxy actually got
serialized. Found while rewriting examples/example_simple.py to use
the proxy API throughout. See CHANGELOG.md.
"""

import pytest
import yaml

from cesdm_toolbox import build_model_from_yaml
from cesdm.proxy import EntityProxy


def _model():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("EnergySystemModel", "sys1")
    return model


def test_add_entity_coerces_asset_proxy_entity_id_to_plain_str():
    model = _model()
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    bus = model.get_entity("bus.1")
    assert isinstance(bus, EntityProxy)
    # Use the EntityProxy itself as a NEW entity's id
    model.add_entity("ElectricalBus", "bus.proxy_id_test")
    gen_id = EntityProxy(model, "gen.proxy_id_test")
    model.add_entity("GenerationUnit", gen_id)
    stored_id = model.entity_data("gen.proxy_id_test")  # must not raise
    assert type(list(model.entities["GenerationUnit"].keys())[-1]) is str


def test_add_relation_coerces_asset_proxy_target_to_plain_str():
    model = _model()
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    bus1 = model.get_entity("bus.1")
    model.add_entity("ElectricalBus", "bus.2")
    model.add_attribute("bus.2", "nominal_voltage", 380)
    bus2 = model.get_entity("bus.2")
    model.add_entity("TransmissionLine", "line.1")
    model.add_relation("line.1", "fromNode", bus1)  # bus1 is EntityProxy
    model.add_relation("line.1", "toNode", bus2)
    line = "line.1"

    raw = model.entity_data(line)
    from_target = raw["fromNode"]
    targets = from_target if isinstance(from_target, list) else [from_target]
    for t in targets:
        assert type(t) is str, f"expected plain str, got {type(t)}: {t!r}"


def test_add_attribute_coerces_asset_proxy_value_to_plain_str():
    model = _model()
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    bus = model.get_entity("bus.1")
    model.add_entity("GenerationUnit", "gen.1")
    model.add_relation("gen.1", "atNode", bus)
    gen = "gen.1"
    # Deliberately pass an EntityProxy as a string-typed attribute value
    model.add_attribute(gen, "name", bus)
    raw = model.entity_data(gen)["name"]
    stored = raw["value"] if isinstance(raw, dict) else raw
    assert type(stored) is str


def test_full_yaml_export_survives_asset_proxy_heavy_construction(tmp_path):
    """The actual bug: build a model where EntityProxy instances flow
    through connect() and ensure_entity() calls throughout (exactly
    like real code using get_entity() does), then export it -- must
    not raise."""
    model = _model()
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    bus1 = model.get_entity("bus.1")
    model.add_entity("ElectricalBus", "bus.2")
    model.add_attribute("bus.2", "nominal_voltage", 380)
    bus2 = model.get_entity("bus.2")
    model.add_entity("GenerationUnit", "gen.1")
    model.add_relation("gen.1", "atNode", bus1)
    gen = model.get_entity("gen.1")
    model.add_entity("TransmissionLine", "line.1")
    model.add_relation("line.1", "fromNode", bus1)
    model.add_relation("line.1", "toNode", bus2)
    interconnector = model.ensure_entity("GenericInterconnector", "ntc.1", name="test")
    interconnector.connect(bus1, bus2)

    out = tmp_path / "model.yaml"
    model.export_yaml_hierarchical(out)  # must not raise RepresenterError

    # Round-trip: the exported YAML must be plain-Python-loadable (no
    # unresolvable !!python/object tags from a leaked EntityProxy)
    loaded = yaml.safe_load(out.read_text())
    assert loaded is not None


def test_ensure_entity_returns_asset_proxy_not_raw_entity_object():
    """ensure_entity() used to return self.entities[cname][entity_id]
    (the raw internal Entity object) -- never actually used by any of
    its own internal callers (ensure_carrier/ensure_resource/
    ensure_technology all discard it and return their own id parameter
    directly), so this was a real usability gap for any external
    caller. Found via `m.get_entity(m.ensure_entity(...))` producing a
    nonsensical wrapped repr string while converting examples/
    example_simple.py."""
    model = _model()
    result = model.ensure_entity("ElectricalBus", "bus.ensure_test", name="Test bus")
    assert isinstance(result, EntityProxy)
    assert result == "bus.ensure_test"
    assert result.entity_class == "ElectricalBus"
