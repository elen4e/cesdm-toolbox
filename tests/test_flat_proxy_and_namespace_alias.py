"""
cesdm.proxy: flat attribute access (gen.nominal_power_capacity = 400)
and namespace-alias access (gen.dispatch.nominal_power_capacity = 400)
both read and write the *same* underlying storage, for any asset class
migrated to the flattened representation-view model (see
CHANGELOG.md) -- requested directly, with belongsToGroup as the field
name instead of "tag".

There are no more separate representation-view entities at all now
(see CHANGELOG.md: this toolbox's "initial version without views"),
so FlatGroupViewProxy is the only mechanism -- the earlier backward-
compatibility concern (an old, separate view entity needing priority
over the flattened pattern) no longer applies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cesdm_toolbox import build_model_from_yaml
from cesdm.proxy import FlatGroupViewProxy, _entity_proxy

ROOT = Path(__file__).resolve().parent.parent


def _model_with_bus():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.add_entity("GeographicalRegion", "nuts3.ch021")
    model.add_attribute("nuts3.ch021", "name", "r")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    model.add_relation("bus.1", "belongsToGeographicalRegion", "nuts3.ch021")
    return model, "bus.1"


def test_flat_set_then_flat_get_on_a_fresh_asset():
    model, bus = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.fresh")
    model.add_attribute("gen.fresh", "name", "gen.fresh")
    gen = _entity_proxy(model, "gen.fresh")

    gen.nominal_power_capacity = 400.0
    assert gen.nominal_power_capacity == 400.0


def test_flat_set_visible_through_namespace_alias():
    model, bus = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.fresh")
    model.add_attribute("gen.fresh", "name", "gen.fresh")
    gen = _entity_proxy(model, "gen.fresh")

    gen.nominal_power_capacity = 400.0
    assert gen.dispatch.nominal_power_capacity == 400.0


def test_namespace_alias_set_visible_through_flat_access():
    model, bus = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.fresh")
    model.add_attribute("gen.fresh", "name", "gen.fresh")
    gen = _entity_proxy(model, "gen.fresh")

    gen.dispatch.variable_operating_cost = 25.0
    assert gen.variable_operating_cost == 25.0


def test_namespace_alias_over_flat_storage_is_a_flat_group_view_proxy():
    model, bus = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.fresh")
    model.add_attribute("gen.fresh", "name", "gen.fresh")
    gen = _entity_proxy(model, "gen.fresh")

    assert isinstance(gen.dispatch, FlatGroupViewProxy)
    # Same asset id, not a separate view entity id.
    assert gen.dispatch.id == "gen.fresh"


# Note: the old "separate view entity still takes priority" backward-
# compatibility case this used to test no longer applies at all -- the
# schema classes a separate view entity would need (e.g.
# "Generation.DispatchView") don't exist any more (see CHANGELOG.md:
# this toolbox's "initial version without views"), so there's nothing
# left to prioritize over the flattened pattern. Removed rather than
# kept as a dead, un-testable scenario.


def test_flat_group_view_proxy_rejects_unknown_field_with_suggestion():
    model, bus = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.fresh")
    model.add_attribute("gen.fresh", "name", "gen.fresh")
    gen = _entity_proxy(model, "gen.fresh")

    with pytest.raises(AttributeError, match="nominal_power_capacity"):
        gen.dispatch.nominal_power_capaciyt = 1  # typo


def test_bus_powerflow_and_spatial_attributes_actually_land():
    """Found directly while migrating ElectricalBus: its
    ElectricalBus.PowerFlowView never declared powerflow_bus_type/
    voltage_magnitude_setpoint/voltage_angle_setpoint as attributes at
    all, so the old add_bus(powerflow_bus_type=..., ...) builder had
    always silently done nothing (set_attribute_if_allowed() only sets
    a value if the class declares the attribute). Fixed while
    flattening these onto ElectricalBus directly -- pins down that
    they actually land now."""
    model, bus = _model_with_bus()
    model.add_entity("GeographicalRegion", "region.test")
    model.add_attribute("region.test", "name", "region.test")
    model.add_entity("ElectricalBus", "bus.new")
    model.add_attribute("bus.new", "nominal_voltage", 380)
    model.add_relation("bus.new", "belongsToGeographicalRegion", "region.test")
    model.add_attribute("bus.new", "powerflow_bus_type", "slack")
    model.add_attribute("bus.new", "voltage_magnitude_setpoint", 1.0)
    model.add_attribute("bus.new", "voltage_angle_setpoint", 0.0)
    model.add_attribute("bus.new", "latitude", 47.3)
    model.add_attribute("bus.new", "longitude", 8.5)
    b = _entity_proxy(model, "bus.new")
    assert b.powerflow_bus_type == "slack"
    assert b.voltage_magnitude_setpoint == 1.0
    assert b.voltage_angle_setpoint == 0.0
    assert b.latitude == 47.3
    assert b.longitude == 8.5
    assert model.views_for_asset(str(b)) == {}


def test_bare_generation_unit_validates_cleanly_despite_defaulted_attributes_elsewhere():
    """The dynamic machine model's parameters (inertia_constant,
    d_axis_synchronous_reactance, ...) live on the reusable DynamicMachineModelType.Synchronous
    GenerationUnit itself -- so a bare GenerationUnit with no linked
    dynamic model has no dynamics-tagged attributes at all and validates
    cleanly, exactly as it should for e.g. a wind or solar generator
    that has no synchronous-machine dynamics to model in the first
    place. This test locks that in."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.add_entity("GenerationUnit", "gen.bare")
    model.add_attribute("gen.bare", "name", "gen.bare")
    assert model.validate() == []


def test_total_capacity_finds_flattened_generation_units():
    """Found directly while rewriting reference_energy_system_model.py to use
    core EAR calls: total_capacity() silently returned 0.0 for an
    otherwise fully correct, flattened-pattern model -- it only ever
    searched for a separate dispatch view via reportsOn. Fixed
    to also check the asset's own data directly when no separate view
    holds nominal_power_capacity, without changing the shared
    _build_view_index() used by export_yaml_hierarchical (adding a
    self-referencing entry there would have wrongly nested an asset
    under itself in the exported "representations" block -- caught by
    3 aggregation tests immediately when first tried that way)."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.add_entity("GenerationUnit", "gen.flat")
    model.add_attribute("gen.flat", "name", "gen.flat")
    model.add_attribute("gen.flat", "nominal_power_capacity", 400.0)
    assert model.total_capacity() == 400.0
