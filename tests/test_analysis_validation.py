"""
Analysis-dependent validation: model.validate_for_analysis(profile).

Different analyses need different subsets of attributes from different
entity classes and their views, with value checks beyond what the
schema itself requires -- declared in a YAML "analysis profile" file
(analysis_profiles/*.yaml), the same schema-driven philosophy CESDM
already uses elsewhere, applied one level up from structural schema
validation (model.validate()).
"""

import pathlib

import pytest

from cesdm_toolbox import build_model_from_yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _model_with_bus():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    model.add_entity("ElectricalBus", "bus.2")
    model.add_attribute("bus.2", "nominal_voltage", 380)
    return model, "bus.1", "bus.2"


def _add_generator(model, gen_id, *, technology, bus):
    gen = model.add_entity("GenerationUnit", gen_id)
    model.set_technology(gen_id, technology, technology_class="GeneratorType")
    gen.atNode = bus
    return gen


def _add_transmission_line(model, line_id, bus1, bus2):
    line = model.add_entity("TransmissionLine", line_id)
    line.fromNode = bus1
    line.toNode = bus2
    return line


def test_fully_specified_model_passes_with_zero_errors():
    model, bus1, bus2 = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    gas.dispatch.nominal_power_capacity = 400
    gas.dispatch.variable_operating_cost = 30.0
    gas.dispatch.energy_conversion_efficiency = 0.58
    line = _add_transmission_line(model, "line.1", bus1, bus2)
    line.power_flow.thermal_capacity_rating = 500

    assert model.validate_for_analysis("optimal_dispatch") == []


def test_missing_required_dispatch_attribute_is_reported():
    model, bus1, bus2 = _model_with_bus()
    # variable_operating_cost is required: false on GenerationUnit now
    # (see analysis_profiles/optimal_dispatch.yaml) -- nominal_power_capacity
    # is the field that's still genuinely required here.
    model.add_entity("GeneratorType", "tech.bare")
    wind = model.add_entity("GenerationUnit", "wind.1")
    wind.add_relation(relation_id="hasTechnology", target_entity_id="tech.bare")
    wind.atNode = bus1
    wind.dispatch.variable_operating_cost = 0
    # nominal_power_capacity deliberately not set

    errors = model.validate_for_analysis("optimal_dispatch")
    assert len(errors) == 1
    assert "GenerationUnit:wind.1" in errors[0]
    assert "nominal_power_capacity" in errors[0]


def test_missing_view_entirely_is_reported_not_a_crash():
    """A GenerationUnit with no dispatch attributes set at all yet --
    the checker must report this cleanly, not raise trying to look up
    an attribute that simply isn't populated (dispatch attributes now
    live directly on the asset, not a separate view entity)."""
    model, bus1, bus2 = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.bare")
    model.add_relation("gen.bare", "hasTechnology", "Generation.Thermal.Gas.CCGT.Existing")

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("missing required 'nominal_power_capacity'" in e for e in errors)


def test_value_below_minimum_is_reported():
    model, bus1, bus2 = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    gas.dispatch.nominal_power_capacity = -10  # invalid: negative
    gas.dispatch.variable_operating_cost = 30.0

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("nominal_power_capacity" in e and "minimum" in e for e in errors)


def test_value_above_maximum_is_reported():
    model, bus1, bus2 = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    gas.dispatch.nominal_power_capacity = 400
    gas.dispatch.variable_operating_cost = 30.0
    gas.dispatch.energy_conversion_efficiency = 1.4  # invalid: > 1.0

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("energy_conversion_efficiency" in e and "maximum" in e for e in errors)


def test_optional_attribute_not_flagged_when_absent():
    """energy_conversion_efficiency is required: false in the profile --
    a generator that never sets it must not be flagged."""
    model, bus1, bus2 = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    gas.dispatch.nominal_power_capacity = 400
    gas.dispatch.variable_operating_cost = 30.0
    # energy_conversion_efficiency deliberately not set

    errors = model.validate_for_analysis("optimal_dispatch")
    assert errors == []


def test_subclass_of_requirement_entity_class_is_also_checked():
    """HydroGenerationUnit is a subclass of GenerationUnit -- a
    requirement block for GenerationUnit must also apply to it."""
    model, bus1, bus2 = _model_with_bus()
    # variable_operating_cost is required: false on GenerationUnit now
    # (see analysis_profiles/optimal_dispatch.yaml) -- nominal_power_capacity
    # is the field that's still genuinely required here.
    model.add_entity("GeneratorType", "tech.bare")
    model.add_entity("HydroGenerationUnit", "gen.ror.1")
    model.add_relation("gen.ror.1", "hasTechnology", "tech.bare")
    model.add_relation("gen.ror.1", "atNode", bus1)
    gen = model.get_entity("gen.ror.1")
    gen.dispatch.hydro_machine_kind = "turbine"
    gen.dispatch.variable_operating_cost = 0
    # nominal_power_capacity deliberately not set

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("gen.ror.1" in e and "nominal_power_capacity" in e for e in errors)


def test_relation_check_directly_on_the_asset_no_view_family():
    model, bus1, bus2 = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.no_tech")
    # hasTechnology deliberately never set -- checked directly on the
    # asset, no view_family involved for this particular check

    errors = model.validate_for_analysis("optimal_dispatch")
    assert any("gen.no_tech" in e and "hasTechnology" in e for e in errors)


def test_validate_for_analysis_or_raise_raises_with_all_errors_listed():
    model, bus1, bus2 = _model_with_bus()
    _add_generator(model, "wind.1", technology="Generation.Renewable.Wind.Onshore", bus=bus1)

    with pytest.raises(ValueError, match="optimal_dispatch"):
        model.validate_for_analysis_or_raise("optimal_dispatch")


def test_validate_for_analysis_or_raise_does_not_raise_when_clean():
    model, bus1, bus2 = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    gas.dispatch.nominal_power_capacity = 400
    gas.dispatch.variable_operating_cost = 30.0
    line = _add_transmission_line(model, "line.1", bus1, bus2)
    line.power_flow.thermal_capacity_rating = 500

    model.validate_for_analysis_or_raise("optimal_dispatch")  # must not raise


def test_load_analysis_profile_by_explicit_path():
    model, _, _ = _model_with_bus()
    profile = model.load_analysis_profile(REPO_ROOT / "analysis_profiles" / "optimal_dispatch.yaml")
    assert profile["name"] == "optimal_dispatch"
    # GenerationUnit, CHPUnit, ExternalSupply, DemandUnit,
    # WindGenerationUnit, SolarGenerationUnit, HydroGenerationUnit,
    # StorageUnit, HydraulicStorageUnit, TransmissionElement (shared
    # fromNode/toNode), plus one block per concrete transmission subclass
    # (TransmissionLine, Transformer, GenericInterconnector, HVDCLink).
    assert len(profile["requirements"]) == 14


def test_load_analysis_profile_by_directory_merges_all_files(tmp_path):
    (tmp_path / "a.yaml").write_text(
        "requirements:\n"
        "  - entity_class: GenerationUnit\n"
        "    checks:\n"
        "      - attribute: hasTechnology\n"
        "        required: true\n"
    )
    (tmp_path / "b.yaml").write_text(
        "requirements:\n"
        "  - entity_class: TransmissionLine\n"
        "    checks:\n"
        "      - attribute: fromNode\n"
        "        view_family: topology\n"
        "        required: true\n"
    )
    model, _, _ = _model_with_bus()
    profile = model.load_analysis_profile(tmp_path)
    assert len(profile["requirements"]) == 2


def test_validate_for_analysis_accepts_an_already_loaded_profile_dict():
    model, bus1, bus2 = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.bare")
    profile = {
        "name": "custom",
        "requirements": [
            {"entity_class": "GenerationUnit",
             "checks": [{"attribute": "hasTechnology", "required": True}]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "custom" in errors[0]


def test_unknown_profile_name_raises_a_clear_error():
    model, _, _ = _model_with_bus()
    with pytest.raises(FileNotFoundError, match="does_not_exist"):
        model.validate_for_analysis("does_not_exist")


def test_unknown_entity_class_in_profile_is_reported_not_a_crash():
    model, _, _ = _model_with_bus()
    profile = {
        "name": "bad_profile",
        "requirements": [{"entity_class": "TotallyNotARealClass", "checks": []}],
    }
    errors = model.validate_for_analysis(profile)
    assert any("TotallyNotARealClass" in e for e in errors)


def test_unknown_attribute_in_check_is_reported_not_a_crash():
    model, bus1, bus2 = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.bare")
    profile = {
        "name": "bad_attr",
        "requirements": [
            {"entity_class": "GenerationUnit",
             "checks": [{"attribute": "totally_not_a_real_attribute", "required": True}]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert any("totally_not_a_real_attribute" in e for e in errors)


# ---------------------------------------------------------------------
# Entity-centric checks: view_family is optional
#
# Requested directly: profiles should be definable "directly based on
# entities, not on views" -- a check just names the attribute, and
# CESDM figures out on its own whether it lives on the asset directly
# or on exactly one of its representation views, the same schema-
# driven view_family lookup that already powers `.dispatch`/
# `.power_flow` on the proxy API. Confirmed there's no ambiguity for any
# real domain attribute across the whole schema before relying on
# this -- only structural, every-view-has-one relations
# (reportsOn, hasRunRecord) are ever ambiguous, and those aren't
# something a profile would check anyway.
# ---------------------------------------------------------------------

def test_view_attribute_resolves_automatically_without_view_family():
    """The exact ask: a profile written with no view_family anywhere
    must still correctly find nominal_power_capacity/
    variable_operating_cost on the dispatch view, and
    thermal_capacity_rating on the power-flow view."""
    model, bus1, bus2 = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    gas.dispatch.nominal_power_capacity = 400
    gas.dispatch.variable_operating_cost = 30.0
    line = _add_transmission_line(model, "line.1", bus1, bus2)
    line.power_flow.thermal_capacity_rating = 500

    profile = {
        "name": "entity_centric",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "nominal_power_capacity", "required": True, "constraints": {"minimum": 0}},
                {"attribute": "variable_operating_cost", "required": True},
            ]},
            {"entity_class": "TransmissionLine", "checks": [
                {"attribute": "thermal_capacity_rating", "required": True, "constraints": {"minimum": 0}},
                {"attribute": "fromNode", "required": True},
            ]},
        ],
    }
    assert model.validate_for_analysis(profile) == []


def test_view_attribute_auto_resolution_still_catches_missing_values():
    model, bus1, bus2 = _model_with_bus()
    # A bare, manually-created GeneratorType -- see the comment in
    # test_subclass_of_requirement_entity_class_is_also_checked above
    # for why the library's real wind template isn't used here.
    model.add_entity("GeneratorType", "tech.bare")
    wind = model.add_entity("GenerationUnit", "wind.1")
    wind.add_relation(relation_id="hasTechnology", target_entity_id="tech.bare")
    wind.atNode = bus1
    wind.dispatch.nominal_power_capacity = 120
    # variable_operating_cost deliberately not set, and tech.bare doesn't supply it either

    profile = {
        "name": "entity_centric",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "variable_operating_cost", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "wind.1" in errors[0]
    assert "variable_operating_cost" in errors[0]
    # variable_operating_cost is now a direct, known field of
    # GenerationUnit (flattened from Generation.DispatchView -- see
    # CHANGELOG.md), so the message is direct rather than needing to
    # say which view it had to search across to find it.
    assert "missing required 'variable_operating_cost'" in errors[0]


def test_ambiguous_attribute_without_view_family_gives_a_clear_error_not_a_crash():
    """reportsOn exists on every view class, in several different
    families for GenerationUnit -- auto-resolution can't (and
    shouldn't) guess; this must fail with an actionable message, not
    silently pick one or raise an unhandled exception."""
    model, bus1, bus2 = _model_with_bus()
    _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)

    profile = {
        "name": "ambiguous",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "reportsOn", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "reportsOn" in errors[0]
    assert "view_family" in errors[0]  # points at the escape hatch


def test_explicit_view_family_still_works_alongside_entity_centric_checks():
    """Backward compatible: a profile can still mix explicit
    view_family (e.g. to resolve the rare ambiguous case) with
    entity-centric checks in the same requirement block."""
    model, bus1, bus2 = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    gas.dispatch.nominal_power_capacity = 400

    profile = {
        "name": "mixed",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "nominal_power_capacity", "view_family": "dispatch", "required": True},
                {"attribute": "hasTechnology", "required": True},
            ]},
        ],
    }
    assert model.validate_for_analysis(profile) == []


def test_optimal_dispatch_profile_file_no_longer_needs_view_family():
    """The shipped example profile itself uses the simplified,
    entity-centric syntax -- confirms the file wasn't just left with
    the old, more verbose form. (The file's own comments mention
    "view_family:" to explain the escape hatch -- checking the parsed
    checks themselves, not raw text, avoids a false positive on that.)"""
    import yaml
    data = yaml.safe_load((REPO_ROOT / "analysis_profiles" / "optimal_dispatch.yaml").read_text())
    for requirement in data["requirements"]:
        for check in requirement["checks"]:
            assert "view_family" not in check


def test_only_structural_relations_are_ever_ambiguous_across_the_whole_schema():
    """Systematic sweep, not just the two entity classes the shipped
    profile happens to use: entity-centric auto-resolution is only
    actually safe in practice if no *real* domain attribute is
    ambiguous across multiple view families anywhere in the schema.
    reportsOn/hasRunRecord (every view has one, several families)
    are expected and fine -- nothing else should be.
    """
    model = build_model_from_yaml("schemas/cesdm")
    known_structural = {"reportsOn", "hasRunRecord"}
    surprises = []
    for entity_class, class_def in model.classes.items():
        if getattr(class_def, "abstract", False) or getattr(class_def, "view_family", None):
            continue  # skip abstract classes and view classes themselves
        candidates = (model._discover_view_map() or {}).get(entity_class, [])
        attr_to_families: dict = {}
        for vcls in candidates:
            vdef = model.classes.get(vcls)
            if vdef is None or getattr(vdef, "abstract", False):
                continue
            family = getattr(vdef, "view_family", None)
            if not family:
                continue
            for name in (model.class_attributes(vcls) or []) + (model.class_relations(vcls) or []):
                attr_to_families.setdefault(name, set()).add(family)
        for name, families in attr_to_families.items():
            if len(families) > 1 and name not in known_structural:
                surprises.append(f"{entity_class}.{name}: ambiguous across {families}")
    assert not surprises, "\n".join(surprises)


def _add_avr(model, avr_id, gen_id, *, avr_class="Controller.AVR.SEXS"):
    model.add_entity(avr_class, avr_id)
    model.add_relation(avr_id, "controlsGenerationUnit", gen_id)
    model.add_relation(gen_id, "hasAutomaticVoltageRegulator", avr_id)
    return model.get_entity(avr_id)


def test_controller_attribute_resolves_automatically_via_view_family():
    """Regression test for a real bug found while auditing the docs:
    Controller.AVR/.GOV/.PSS *do* declare a view_family (avr/governor/
    pss), but are linked via hasAutomaticVoltageRegulator/etc., not
    reportsOn -- so _discover_view_map() (keyed on
    reportsOn) could never see them, and a profile check for a
    genuinely controller-only attribute (e.g. AVR_SEXS_Ka) always
    failed with 'not a known attribute', even when a correctly linked
    controller existed. Fixed via an explicit family->relation map in
    CesdmAnalysisValidationMixin; this pins the fix down."""
    model, bus1, _ = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    avr = _add_avr(model, "avr.gas.1", "gas.1")
    avr.AVR_SEXS_Ka = 200.0
    avr.AVR_SEXS_Ta = 0.05
    avr.AVR_Efd_min = -5.0
    avr.AVR_Efd_max = 5.0

    profile = {
        "name": "avr_check",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "AVR_SEXS_Ka", "required": True},
            ]},
        ],
    }
    assert model.validate_for_analysis(profile) == []


def test_controller_attribute_also_resolves_with_explicit_view_family():
    """Same as above, but with the explicit `view_family: avr` escape
    hatch -- must work identically to auto-detection."""
    model, bus1, _ = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    avr = _add_avr(model, "avr.gas.1", "gas.1")
    avr.AVR_SEXS_Ka = 200.0

    profile = {
        "name": "avr_check_explicit",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "AVR_SEXS_Ka", "view_family": "avr", "required": True},
            ]},
        ],
    }
    assert model.validate_for_analysis(profile) == []


def test_missing_controller_is_reported_as_a_clear_error_not_a_crash():
    """A generator with no AVR attached at all: a required controller
    attribute must be reported as a missing view, not silently pass or
    raise."""
    model, bus1, _ = _model_with_bus()
    _add_generator(model, "gas.no_avr", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)

    profile = {
        "name": "avr_missing",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "AVR_SEXS_Ka", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "avr" in errors[0] and "gas.no_avr" in errors[0]


def test_result_entity_attribute_still_does_not_resolve():
    """Documents current, verified behaviour (see
    docs/guide/10_analysis_validation.md): unlike Controller.*,
    Result entity classes declare no view_family at all today, so an
    attribute that only exists on a Result entity is correctly *not*
    resolvable through this mechanism -- even when a real, correctly
    linked Result entity exists. If this test ever starts failing
    because Result classes gained a view_family, that's a deliberate
    change worth updating the docs for, not a bug."""
    model, bus1, _ = _model_with_bus()
    _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    model.add_entity("RunRecord", "run.1")
    model.add_entity("DispatchRunRecord", "run.dispatch.1")
    model.add_entity("GenerationUnit.DispatchResult", "result.run1.gas1")
    model.add_relation("result.run1.gas1", "reportsOn", "gas.1")
    model.add_relation("result.run1.gas1", "hasRunRecord", "run.dispatch.1")
    model.add_attribute("result.run1.gas1", "total_generation", 1234.5)

    profile = {
        "name": "result_check",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "total_generation", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "total_generation" in errors[0]


def test_machine_dynamics_attribute_resolves_via_linked_dynamic_model():
    """The dynamic machine model's parameters live on the standalone
    DynamicMachineModelType.Synchronous
    entity, linked via usesDynamicModelType -- the same linked-entity pattern
    as Controller.AVR/.GOV/.PSS, so a profile check for a
    dynamics-only attribute on GenerationUnit must resolve through it
    automatically, exactly like AVR_SEXS_Ka does through
    hasAutomaticVoltageRegulator."""
    model, bus1, _ = _model_with_bus()
    gas = _add_generator(model, "gas.1", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)
    model.add_entity("DynamicMachineModelType.Synchronous", "dyn.gas.1")
    model.add_relation("gas.1", "usesDynamicModelType", "dyn.gas.1")
    dm = model.get_entity("dyn.gas.1")
    dm.d_axis_synchronous_reactance = 1.9

    profile = {
        "name": "dynamics_check",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "d_axis_synchronous_reactance", "required": True},
            ]},
        ],
    }
    assert model.validate_for_analysis(profile) == []


def test_missing_dynamic_model_is_reported_as_a_clear_error_not_a_crash():
    model, bus1, _ = _model_with_bus()
    _add_generator(model, "gas.no_dyn", technology="Generation.Thermal.Gas.CCGT.Existing", bus=bus1)

    profile = {
        "name": "dynamics_missing",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "d_axis_synchronous_reactance", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "dynamics" in errors[0] and "gas.no_dyn" in errors[0]
