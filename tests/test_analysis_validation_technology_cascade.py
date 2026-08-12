"""Regression tests for the technology-template cascade fallback in
analysis-profile checks (cesdm.domain.model.analysis_validation's
`_resolve_check_beyond_entity` override).

Real bug reported directly: an analysis profile requiring
`charging_efficiency`/`discharging_efficiency` flagged a StorageUnit as
incomplete even though its linked StorageType technology template
supplied real values for both -- correct for `model.validate()`
(schema-level, deliberately a literal-value check, never follows the
cascade) but wrong for `validate_for_analysis()`, whose whole point is
"does this model have what the analysis needs", the same question
`entity.dispatch.attribute` already answers via
`get_effective_attribute_value()`. Fixed by trying that same cascade
before falling through to the existing Controller/Result-family
resolution.

A second, independent real bug was found and fixed while verifying
this: `get_effective_attribute_value()` crashed with an unhelpful
`KeyError` (not a graceful "nothing to fall back to") whenever
`hasTechnology` pointed at an id that was never actually created as a
real entity -- confirmed this also affects a plain
`entity.dispatch.attribute` read, not just analysis validation.
"""
from cesdm_toolbox import build_model_from_yaml


def _model_with_bus():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("ElectricalBus", "bus.1")
    return model


def test_storage_unit_charging_efficiency_resolves_from_technology_template():
    model = _model_with_bus()
    tech = model.add_entity("StorageType", "tech.battery_li_ion")
    tech.add_attribute(attribute_id="charging_efficiency", value=0.95)
    tech.add_attribute(attribute_id="discharging_efficiency", value=0.93)

    bat = model.add_entity("StorageUnit", "bat.1")
    bat.atNode = "bus.1"
    bat.dispatch.energy_storage_capacity = 100
    bat.dispatch.maximum_charging_power = 50
    bat.dispatch.maximum_discharging_power = 50
    bat.add_relation(relation_id="hasTechnology", target_entity_id="tech.battery_li_ion")
    # charging_efficiency/discharging_efficiency deliberately not set
    # directly on the instance -- only on the linked technology.

    errors = model.validate_for_analysis("optimal_dispatch")
    assert not any("bat.1" in e for e in errors)


def test_storage_unit_still_fails_when_technology_also_lacks_the_value():
    """The cascade must not turn into "skip the check whenever
    hasTechnology is set at all" -- if the linked template genuinely
    doesn't supply the value either, the check must still fail."""
    model = _model_with_bus()
    model.add_entity("StorageType", "tech.bare")  # no efficiencies declared

    bat = model.add_entity("StorageUnit", "bat.1")
    bat.atNode = "bus.1"
    bat.dispatch.energy_storage_capacity = 100
    bat.dispatch.maximum_charging_power = 50
    bat.dispatch.maximum_discharging_power = 50
    bat.add_relation(relation_id="hasTechnology", target_entity_id="tech.bare")

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("bat.1" in e and "charging_efficiency" in e for e in errors)
    assert any("bat.1" in e and "discharging_efficiency" in e for e in errors)


def test_storage_unit_still_fails_with_no_technology_at_all():
    model = _model_with_bus()
    bat = model.add_entity("StorageUnit", "bat.1")
    bat.atNode = "bus.1"
    bat.dispatch.energy_storage_capacity = 100
    bat.dispatch.maximum_charging_power = 50
    bat.dispatch.maximum_discharging_power = 50
    # No hasTechnology at all.

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("bat.1" in e and "charging_efficiency" in e for e in errors)


def test_technology_cascaded_value_is_still_constraint_checked():
    """A value resolved through the cascade is checked against the
    same constraints (min/max/enum) as a directly-set one -- an
    invalid value in the technology template isn't silently accepted
    just because it came from there."""
    model = _model_with_bus()
    tech = model.add_entity("StorageType", "tech.bad")
    tech.add_attribute(attribute_id="charging_efficiency", value=1.5)  # invalid: must be <= 1
    tech.add_attribute(attribute_id="discharging_efficiency", value=0.95)

    bat = model.add_entity("StorageUnit", "bat.1")
    bat.atNode = "bus.1"
    bat.dispatch.energy_storage_capacity = 100
    bat.dispatch.maximum_charging_power = 50
    bat.dispatch.maximum_discharging_power = 50
    bat.add_relation(relation_id="hasTechnology", target_entity_id="tech.bad")

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("bat.1" in e and "charging_efficiency" in e and "maximum" in e for e in errors)


def test_direct_instance_value_wins_over_the_technology_template():
    """The instance's own value always overrides the template's,
    matching the cascade's documented precedence."""
    model = _model_with_bus()
    tech = model.add_entity("StorageType", "tech.template")
    tech.add_attribute(attribute_id="charging_efficiency", value=0.80)
    tech.add_attribute(attribute_id="discharging_efficiency", value=0.80)

    bat = model.add_entity("StorageUnit", "bat.1")
    bat.atNode = "bus.1"
    bat.dispatch.energy_storage_capacity = 100
    bat.dispatch.maximum_charging_power = 50
    bat.dispatch.maximum_discharging_power = 50
    bat.add_relation(relation_id="hasTechnology", target_entity_id="tech.template")
    bat.dispatch.charging_efficiency = 1.5  # invalid override, set directly
    bat.dispatch.discharging_efficiency = 0.9

    errors = model.validate_for_analysis("optimal_dispatch")
    # The instance's own (invalid) 1.5 must be what's checked, not the
    # template's valid 0.80 -- confirms the direct value takes
    # precedence, exactly like a live entity.dispatch.x read would.
    assert any("bat.1" in e and "charging_efficiency" in e and "maximum" in e for e in errors)


def test_dangling_technology_reference_does_not_crash_a_dispatch_read():
    """The real, independent bug found while verifying the cascade fix
    above: hasTechnology pointing at an id that was never actually
    created as a real entity must not crash -- it's the same as no
    technology being linked at all."""
    model = build_model_from_yaml("schemas/cesdm")
    gen = model.add_entity("HydroGenerationUnit", "gen.1")
    gen.add_relation(relation_id="hasTechnology", target_entity_id="Generation.Renewable.Hydro.RunOfRiver")
    # The technology entity above is never created in this model at all.

    assert gen.dispatch.variable_operating_cost is None


def test_dangling_technology_reference_does_not_crash_analysis_validation():
    model = _model_with_bus()
    gen = model.add_entity("HydroGenerationUnit", "gen.1")
    gen.atNode = "bus.1"
    gen.add_relation(relation_id="hasTechnology", target_entity_id="Generation.Renewable.Hydro.RunOfRiver")
    # nominal_power_capacity deliberately not set (variable_operating_cost
    # is required: false on GenerationUnit, so it doesn't exercise this)

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("gen.1" in e and "nominal_power_capacity" in e for e in errors)
