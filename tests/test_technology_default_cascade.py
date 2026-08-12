"""
Model.get_effective_attribute_value() and its wiring into ViewProxy:
the "instance overrides technology-template default" cascade that
GeneratorType/StorageType's own schema descriptions already promised
("Each GenerationUnit then sets only instance-specific overrides...")
but nothing previously implemented. tools/import_flexeco.py had
already reinvented an equivalent local fallback (`_sv()`) before this
existed as a shared, reusable method. See CHANGELOG.md.
"""

import pytest

from cesdm_toolbox import build_model_from_yaml


@pytest.fixture(scope="module")
def model_with_library():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    return model


def _add_gas_generator(model, gen_id):
    gen = model.add_entity("GenerationUnit", gen_id)
    gen.hasTechnology = "Generation.Thermal.Gas.CCGT.Existing"
    gen.atNode = "bus.1"
    return gen


def test_cascade_resolves_technology_default_when_unset(model_with_library):
    gen = _add_gas_generator(model_with_library, "gen.cascade.1")
    # never explicitly set -- must resolve from the GeneratorType library entity
    assert gen.dispatch.energy_conversion_efficiency == pytest.approx(0.58)
    assert gen.dispatch.variable_operating_cost is not None


def test_explicit_override_takes_priority_over_cascade(model_with_library):
    gen = _add_gas_generator(model_with_library, "gen.cascade.2")
    gen.dispatch.energy_conversion_efficiency = 0.62
    assert gen.dispatch.energy_conversion_efficiency == 0.62


def test_cascade_returns_none_without_library_loaded():
    """Without import_library(), the technology entity is a bare stub
    (just a name) -- the cascade must not crash, just return None,
    same as any other unset attribute."""
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    model.add_entity("GenerationUnit", "gen.cascade.3")
    model.set_technology("gen.cascade.3", "Generation.Thermal.Gas.CCGT.Existing", technology_class="GeneratorType")
    model.add_relation("gen.cascade.3", "atNode", "bus.1")
    gen = model.get_entity("gen.cascade.3")
    assert gen.dispatch.energy_conversion_efficiency is None


def test_non_overlapping_attribute_unaffected_by_cascade(model_with_library):
    """nominal_power_capacity has no GeneratorType counterpart -- must
    behave exactly as a plain instance attribute, no cascade involved."""
    gen = _add_gas_generator(model_with_library, "gen.cascade.4")
    assert gen.dispatch.nominal_power_capacity is None
    gen.dispatch.nominal_power_capacity = 400
    assert gen.dispatch.nominal_power_capacity == 400.0


def test_get_effective_attribute_value_direct_call(model_with_library):
    gen = _add_gas_generator(model_with_library, "gen.cascade.5")
    dv_id = gen.dispatch.id
    val = model_with_library.get_effective_attribute_value(dv_id, "energy_conversion_efficiency")
    assert val == pytest.approx(0.58)


def test_cascade_default_when_neither_instance_nor_technology_has_it(model_with_library):
    gen = _add_gas_generator(model_with_library, "gen.cascade.6")
    dv_id = gen.dispatch.id
    val = model_with_library.get_effective_attribute_value(
        dv_id, "energy_conversion_efficiency_typo_field", default="fallback")
    assert val == "fallback"
