"""Tests for the `when:` conditional-check mechanism in analysis
profiles (ear.model.analysis_validation.AnalysisValidationMixin), added
because several real checks (run-of-river vs. reservoir-coupled hydro,
a reservoir's paired inflow profile + annual energy) only apply to a
subset of a class's instances, not every one -- something plain
per-class `required:` couldn't express before this.

Each condition kind is tested directly and in isolation, on top of the
real, end-to-end coverage in test_optimal_dispatch_profile_coverage.py.
Relations only ever get presence/absence conditions
(relation_set/relation_unset) -- a relation links to another entity,
which has no single scalar value to compare algebraically against, so
there is no relation equivalent of attribute_compare.
"""
from cesdm_toolbox import build_model_from_yaml


def _model():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("ElectricalBus", "bus.1")
    return model


def _profile(condition):
    return {
        "name": "when_test",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "variable_operating_cost", "required": True, "when": condition},
            ]},
        ],
    }


def test_relation_unset_condition():
    model = _model()
    with_bus = model.add_entity("GenerationUnit", "gen.with_bus")
    with_bus.atNode = "bus.1"
    without_bus = model.add_entity("GenerationUnit", "gen.without_bus")

    errors = model.validate_for_analysis(_profile({"relation_unset": "atNode"}))
    assert any("gen.without_bus" in e for e in errors)
    assert not any("gen.with_bus" in e for e in errors)


def test_relation_set_condition():
    model = _model()
    with_bus = model.add_entity("GenerationUnit", "gen.with_bus")
    with_bus.atNode = "bus.1"
    without_bus = model.add_entity("GenerationUnit", "gen.without_bus")

    errors = model.validate_for_analysis(_profile({"relation_set": "atNode"}))
    assert any("gen.with_bus" in e for e in errors)
    assert not any("gen.without_bus" in e for e in errors)


def test_attribute_set_condition():
    model = _model()
    with_capacity = model.add_entity("GenerationUnit", "gen.with_capacity")
    with_capacity.dispatch.nominal_power_capacity = 100
    without_capacity = model.add_entity("GenerationUnit", "gen.without_capacity")

    errors = model.validate_for_analysis(_profile({"attribute_set": "nominal_power_capacity"}))
    assert any("gen.with_capacity" in e for e in errors)
    assert not any("gen.without_capacity" in e for e in errors)


def test_attribute_unset_condition():
    model = _model()
    with_capacity = model.add_entity("GenerationUnit", "gen.with_capacity")
    with_capacity.dispatch.nominal_power_capacity = 100
    without_capacity = model.add_entity("GenerationUnit", "gen.without_capacity")

    errors = model.validate_for_analysis(_profile({"attribute_unset": "nominal_power_capacity"}))
    assert any("gen.without_capacity" in e for e in errors)
    assert not any("gen.with_capacity" in e for e in errors)


def test_attribute_equals_condition():
    model = _model()
    gas = model.add_entity("GenerationUnit", "gen.gas")
    gas.dispatch.dispatch_type = "dispatchable"
    wind = model.add_entity("GenerationUnit", "gen.wind")
    wind.dispatch.dispatch_type = "nondispatchable"

    condition = {"attribute_equals": {"attribute": "dispatch_type", "value": "dispatchable"}}
    errors = model.validate_for_analysis(_profile(condition))
    assert any("gen.gas" in e for e in errors)
    assert not any("gen.wind" in e for e in errors)


def test_multiple_conditions_combine_with_and():
    model = _model()
    both = model.add_entity("GenerationUnit", "gen.both")
    both.atNode = "bus.1"
    both.dispatch.nominal_power_capacity = 100
    only_bus = model.add_entity("GenerationUnit", "gen.only_bus")
    only_bus.atNode = "bus.1"

    condition = [{"relation_set": "atNode"}, {"attribute_set": "nominal_power_capacity"}]
    errors = model.validate_for_analysis(_profile(condition))
    assert any("gen.both" in e for e in errors)
    assert not any("gen.only_bus" in e for e in errors)


def test_unmet_condition_skips_the_check_entirely_not_just_required():
    """A skipped check is not reported at all -- not as a missing
    field, not as a constraint violation -- even if the check would
    otherwise have found a real constraint problem."""
    model = _model()
    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.dispatch.variable_operating_cost = -50  # would fail 'minimum: 0' if checked

    profile = {
        "name": "when_test",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "variable_operating_cost", "required": True,
                 "constraints": {"minimum": 0}, "when": {"relation_set": "atNode"}},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert errors == []


def test_malformed_dict_condition_is_treated_as_not_met_rather_than_crashing():
    """Scope: the *dict* condition form specifically. A string is no
    longer "just a malformed dict" now that strings are evaluated as
    expressions instead -- see
    test_expression_syntax_error_is_reported and
    test_expression_function_call_is_rejected_as_invalid_not_silently_skipped
    below for how a malformed *expression* is handled (visibly, unlike
    here)."""
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    for bad_condition in ({"unknown_kind": "atNode"}, {"a": 1, "b": 2}, 42):
        errors = model.validate_for_analysis(_profile(bad_condition))
        assert not any("gen.1" in e for e in errors)


def test_when_absent_behaves_exactly_as_before():
    """A check with no `when:` at all is completely unaffected --
    confirms the new mechanism is purely additive."""
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    profile = {
        "name": "when_test",
        "requirements": [
            {"entity_class": "GenerationUnit", "checks": [
                {"attribute": "variable_operating_cost", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert any("gen.1" in e and "variable_operating_cost" in e for e in errors)


def test_attribute_compare_supports_every_algebraic_operator():
    """Relations only ever support presence/absence
    (relation_set/relation_unset -- see the other tests above); a
    relation links to another entity, which has no single "value" to
    compare algebraically. attribute_compare is attribute-only, and
    supports every operator a schema numeric constraint might need."""
    model = _model()
    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.dispatch.nominal_power_capacity = 500  # exactly 500

    for op, expected in [(">=", True), ("<", False), ("<=", True), ("==", True), ("!=", False)]:
        condition = {"attribute_compare": {
            "attribute": "nominal_power_capacity", "operator": op, "value": 500,
        }}
        errors = model.validate_for_analysis(_profile(condition))
        assert any("gen.1" in e for e in errors) == expected, f"operator {op!r} gave the wrong result"


def test_attribute_compare_with_incompatible_types_is_not_met_not_a_crash():
    model = _model()
    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.dispatch.dispatch_type = "dispatchable"  # a string attribute

    condition = {"attribute_compare": {"attribute": "dispatch_type", "operator": ">", "value": 100}}
    errors = model.validate_for_analysis(_profile(condition))
    assert not any("gen.1" in e for e in errors)


def test_attribute_compare_against_an_unset_attribute_is_not_met():
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")  # nominal_power_capacity never set

    condition = {"attribute_compare": {"attribute": "nominal_power_capacity", "operator": ">", "value": 100}}
    errors = model.validate_for_analysis(_profile(condition))
    assert not any("gen.1" in e for e in errors)


def test_attribute_compare_with_unknown_operator_is_not_met():
    model = _model()
    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.dispatch.nominal_power_capacity = 500

    condition = {"attribute_compare": {"attribute": "nominal_power_capacity", "operator": "~=", "value": 500}}
    errors = model.validate_for_analysis(_profile(condition))
    assert not any("gen.1" in e for e in errors)


# ---------------------------------------------------------------------
# String-expression form of `when:` -- e.g. "nominal_power_capacity > 100
# and atNode" -- an alternative to the dict form above, added because
# the dict form for a simple algebraic comparison
# (`attribute_compare: {attribute: ..., operator: ">", value: 0}`) was
# judged too verbose for something this common. Parsed with
# `ast.parse(mode="eval")` (pure syntax, nothing executed) and walked
# against a strict allow-list of node types -- boolean logic, single
# comparisons, bare names, and literal constants only.
# ---------------------------------------------------------------------

def test_expression_simple_comparison():
    model = _model()
    big = model.add_entity("GenerationUnit", "gen.big")
    big.dispatch.nominal_power_capacity = 500
    small = model.add_entity("GenerationUnit", "gen.small")
    small.dispatch.nominal_power_capacity = 50

    errors = model.validate_for_analysis(_profile("nominal_power_capacity > 100"))
    assert any("gen.big" in e for e in errors)
    assert not any("gen.small" in e for e in errors)


def test_expression_bare_name_means_is_set():
    model = _model()
    with_bus = model.add_entity("GenerationUnit", "gen.with_bus")
    with_bus.atNode = "bus.1"
    without_bus = model.add_entity("GenerationUnit", "gen.without_bus")

    errors = model.validate_for_analysis(_profile("atNode"))
    assert any("gen.with_bus" in e for e in errors)
    assert not any("gen.without_bus" in e for e in errors)


def test_expression_not():
    model = _model()
    with_bus = model.add_entity("GenerationUnit", "gen.with_bus")
    with_bus.atNode = "bus.1"
    without_bus = model.add_entity("GenerationUnit", "gen.without_bus")

    errors = model.validate_for_analysis(_profile("not atNode"))
    assert not any("gen.with_bus" in e for e in errors)
    assert any("gen.without_bus" in e for e in errors)


def test_expression_and_or():
    model = _model()
    both = model.add_entity("GenerationUnit", "gen.both")
    both.atNode = "bus.1"
    both.dispatch.nominal_power_capacity = 200
    only_bus = model.add_entity("GenerationUnit", "gen.only_bus")
    only_bus.atNode = "bus.1"

    errors = model.validate_for_analysis(_profile("atNode and nominal_power_capacity > 100"))
    assert any("gen.both" in e for e in errors)
    assert not any("gen.only_bus" in e for e in errors)

    errors = model.validate_for_analysis(_profile("atNode or nominal_power_capacity > 100"))
    assert any("gen.both" in e for e in errors)
    assert any("gen.only_bus" in e for e in errors)


def test_expression_parentheses_and_string_equality():
    model = _model()
    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.atNode = "bus.1"
    gen.dispatch.nominal_power_capacity = 200
    gen.dispatch.dispatch_type = "dispatchable"

    expr = "(nominal_power_capacity > 100 and dispatch_type == 'dispatchable') or atNode"
    errors = model.validate_for_analysis(_profile(expr))
    assert any("gen.1" in e for e in errors)


def test_expression_negative_number_literal():
    model = _model()
    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.dispatch.minimum_generation = -5

    errors = model.validate_for_analysis(_profile("minimum_generation < 0"))
    assert any("gen.1" in e for e in errors)


def test_expression_function_call_is_rejected_as_invalid_not_silently_skipped():
    """A malformed/disallowed expression is a bug in the profile itself
    -- reported as a real validation error, not silently treated as
    not-met the way the dict form's malformed conditions are."""
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    errors = model.validate_for_analysis(_profile('__import__("os").system("x")'))
    assert any("invalid when expression" in e for e in errors)
    assert any("gen.1" in e for e in errors)


def test_expression_attribute_access_is_rejected():
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    errors = model.validate_for_analysis(_profile("nominal_power_capacity.__class__"))
    assert any("invalid when expression" in e for e in errors)


def test_expression_syntax_error_is_reported():
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    errors = model.validate_for_analysis(_profile("nominal_power_capacity >"))
    assert any("invalid when expression" in e for e in errors)


def test_expression_chained_comparison_is_rejected():
    """a < b < c is deliberately unsupported -- keeps the evaluator's
    contract simple (exactly one comparison per Compare node)."""
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    errors = model.validate_for_analysis(_profile("0 < nominal_power_capacity < 1000"))
    assert any("chained comparisons" in e for e in errors)


def test_expression_comparing_a_relation_to_a_value_is_rejected():
    """A relation links to another entity -- it has no scalar value to
    compare algebraically. Only presence/absence applies to it (a bare
    name, or `not name`)."""
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    errors = model.validate_for_analysis(_profile("atNode == 5"))
    assert any("is a relation, not an attribute" in e for e in errors)


def test_expression_unknown_name_is_treated_as_not_set():
    """A name that isn't a known attribute or relation of the class at
    all is treated as "not set" (fail-safe), not an error -- the same
    `when:` might be checked against several subclasses where the name
    only applies to some."""
    model = _model()
    model.add_entity("GenerationUnit", "gen.1")

    errors = model.validate_for_analysis(_profile("some_field_that_does_not_exist"))
    assert not any("gen.1" in e for e in errors)
