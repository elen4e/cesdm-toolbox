"""
Phase 1 of the requested EAR-level object-oriented API: entities
returned by Model.add_entity() (and any entity reached afterward, since
every entity-creation path -- YAML import, import_library, the CESDM
proxy builders -- goes through add_entity() internally) can now call
their own entity.add_attribute(name, value) / entity.add_relation(name,
target_id), as a thin, non-breaking convenience layer over the exact
same Model.add_attribute()/add_relation() logic.

This was explicitly phase 1 only when written -- collapsing
RepresentationViews onto the asset, renaming "tag" to "belongsToGroup",
the flat-plus-alias proxy API, and Controller entities were separate,
later phases not covered by this file at the time. Those later phases
have since landed, and with them a further evolution asked directly:
`CesdmModel.add_entity()` now returns the entity wrapped in its
schema-specific typed proxy (`EntityProxy`/a generated subclass like
`GenerationUnitProxy`) directly, not the bare `ear.entity.Entity`
dataclass -- the plain EAR-level `ear.model.Model.add_entity()`
underneath is untouched and still returns `Entity` (a generic EAR
domain has no proxy registry to wrap with at all). See CHANGELOG.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cesdm_toolbox import build_model_from_yaml
from ear.entity import Entity
from cesdm.proxy import EntityProxy

ROOT = Path(__file__).resolve().parent.parent


def test_add_entity_now_returns_a_typed_proxy():
    """CesdmModel.add_entity() returns the schema-specific typed proxy
    directly -- e.g. GenerationUnitProxy for a GenerationUnit -- so
    .dispatch etc. work immediately, both at runtime and (via the
    generated stub's overloads) in an editor's autocomplete/type
    checking too."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    ent = model.add_entity("ElectricalBus", "node.test.1")
    assert isinstance(ent, EntityProxy)
    assert ent.id == "node.test.1"
    assert ent.entity_class == "ElectricalBus"
    # Internal storage is still the plain EAR Entity dataclass, unchanged --
    # only what add_entity() *returns* is wrapped differently.
    stored = model.entities["ElectricalBus"]["node.test.1"]
    assert isinstance(stored, Entity)
    assert stored.id == "node.test.1"


def test_plain_ear_model_add_entity_still_returns_the_bare_entity():
    """The generic EAR layer underneath is untouched -- a plain,
    non-CESDM ear.model.Model still returns the bare Entity dataclass,
    since it has no CESDM proxy registry to wrap with at all."""
    from ear.helpers import build_model_from_yaml as ear_build_model_from_yaml

    model = ear_build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    assert not isinstance(model, type(build_model_from_yaml(str(ROOT / "schemas/cesdm"))))
    ent = model.add_entity("ElectricalBus", "node.test.1")
    assert isinstance(ent, Entity)
    assert not isinstance(ent, EntityProxy)
    assert ent.id == "node.test.1"
    assert ent.cls == "ElectricalBus"
    assert model.entities["ElectricalBus"]["node.test.1"] is ent


def test_entity_add_attribute_matches_model_add_attribute():
    """entity.add_attribute(name, value) must produce identical stored
    data to model.add_attribute(entity_id, name, value) -- it's meant
    to be a pure convenience wrapper, not a different code path."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))

    bus1 = model.add_entity("ElectricalBus", "node.a")
    bus1.add_attribute("nominal_voltage", 380.0, unit="kV")

    bus2 = model.add_entity("ElectricalBus", "node.b")
    model.add_attribute(bus2.id, "nominal_voltage", 380.0, unit="kV")

    assert model.entity_data(bus1)["nominal_voltage"] == model.entity_data(bus2)["nominal_voltage"]


def test_entity_add_relation_matches_model_add_relation():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))
    model.add_entity("GeographicalRegion", "nuts3.ch021")
    model.add_attribute("nuts3.ch021", "name", "Test region")
    region = "nuts3.ch021"

    bus1 = model.add_entity("ElectricalBus", "node.a")
    bus1.add_relation("belongsToGeographicalRegion", region)

    bus2 = model.add_entity("ElectricalBus", "node.b")
    model.add_relation(bus2.id, "belongsToGeographicalRegion", region)

    assert model.entity_data(bus1)["belongsToGeographicalRegion"] == model.entity_data(bus2)["belongsToGeographicalRegion"]
    assert isinstance(model.entity_data(bus1)["belongsToGeographicalRegion"], str)  # not an EntityProxy subclass


def test_entity_add_attribute_returns_self_for_chaining():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    bus = model.add_entity("ElectricalBus", "node.a")
    result = bus.add_attribute("nominal_voltage", 380.0, unit="kV")
    assert result is bus


def test_entity_add_relation_returns_self_for_chaining():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))
    model.add_entity("GeographicalRegion", "nuts3.ch021")
    model.add_attribute("nuts3.ch021", "name", "Test region")
    region = "nuts3.ch021"
    bus = model.add_entity("ElectricalBus", "node.a")
    result = bus.add_relation("belongsToGeographicalRegion", region)
    assert result is bus


def test_entities_loaded_via_import_yaml_hierarchical_also_get_the_object_api(tmp_path):
    """Every entity-creation path goes through add_entity() internally,
    including YAML import -- so entities loaded from a file, not just
    ones freshly created in this session, can also use the new
    object-oriented API."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))
    model.add_entity("GeographicalRegion", "nuts3.ch021")
    model.add_attribute("nuts3.ch021", "name", "Test region")
    region = "nuts3.ch021"
    model.add_entity("ElectricalBus", "node.test.380")
    model.add_attribute("node.test.380", "nominal_voltage", 380)
    model.add_relation("node.test.380", "belongsToGeographicalRegion", region)

    yaml_path = tmp_path / "model.yaml"
    model.export_yaml_hierarchical(str(yaml_path))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml_hierarchical(str(yaml_path))

    loaded_bus = reloaded.entities["ElectricalBus"]["node.test.380"]
    loaded_bus.add_attribute("long_name", "Test Bus")
    assert loaded_bus.data["long_name"]["value"] == "Test Bus"


def test_entity_without_a_model_reference_raises_a_clear_error():
    """An Entity constructed directly (bypassing add_entity()) has no
    way to reach the model's validation/storage logic -- this must
    fail with a clear, actionable message, not a confusing AttributeError."""
    bare = Entity(cls="ElectricalBus", id="node.bare", data={})

    with pytest.raises(RuntimeError, match="no owning model reference"):
        bare.add_attribute("nominal_voltage", 380.0)

    with pytest.raises(RuntimeError, match="no owning model reference"):
        bare.add_relation("belongsToGeographicalRegion", "nuts3.ch021")


def test_bare_entity_construction_is_unaffected_by_the_new_field():
    """The one other place across the whole codebase that constructs
    Entity(...) directly must keep working exactly as before: no model
    kwarg required, and equality/repr between two otherwise-identical
    entities must be unaffected by the new field."""
    e1 = Entity(cls="ElectricalBus", id="node.a", data={"x": 1})
    e2 = Entity(cls="ElectricalBus", id="node.a", data={"x": 1})
    assert e1 == e2  # compare=False on _model must not break this
    assert "_model" not in repr(e1)  # repr=False on _model
