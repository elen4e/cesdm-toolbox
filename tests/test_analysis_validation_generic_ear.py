"""
Confirms ear.model.analysis_validation.AnalysisValidationMixin is
genuinely generic -- entities, attributes, relations, and constraints
are core EAR concepts, so `model.validate_for_analysis(profile)` works
on a *plain* `ear.model.Model`, built from a schema with no energy
concepts whatsoever, with zero CESDM involvement.

CESDM's addon (cesdm.domain.model.analysis_validation.
CesdmAnalysisValidationMixin) only adds one thing on top: resolving a
check against a representation view (view_family) when the attribute
isn't declared directly on the entity -- see
tests/test_analysis_validation.py for that layer's own tests. This
file exists specifically to prove the split is real, not just
documented: a bare ear.model.Model has no notion of "views" at all,
and correctly can't resolve anything beyond an entity's own direct
attributes/relations.
"""

import pathlib

import pytest

from ear.helpers import build_model_from_yaml as build_ear_model


def _widget_schema(tmp_path: pathlib.Path) -> pathlib.Path:
    """A tiny schema with no energy-system concepts at all -- proves
    this has nothing to do with CESDM specifically."""
    schema_dir = tmp_path / "schema"
    (schema_dir / "test").mkdir(parents=True)
    (schema_dir / "test" / "Widget.yaml").write_text(
        "name: Widget\n"
        "attributes:\n"
        "- id: weight_kg\n"
        "  required: false\n"
        "  value:\n"
        "    type: decimal\n"
        "    constraints:\n"
        "      minimum: 0\n"
        "- id: color\n"
        "  required: false\n"
        "  value:\n"
        "    type: string\n"
        "    constraints:\n"
        "      enum: [red, green, blue]\n"
        "relations:\n"
        "- id: partOf\n"
        "  required: false\n"
        "  target: Widget\n"
    )
    return schema_dir


def test_plain_ear_model_has_no_cesdm_mixed_in():
    """Sanity check that this really is the generic model, not
    CesdmModel under a different name."""
    from ear.model.core import Model
    from cesdm.domain.model.core import CesdmModel
    assert not issubclass(Model, CesdmModel)


def test_generic_validate_for_analysis_catches_a_missing_required_attribute(tmp_path):
    model = build_ear_model(_widget_schema(tmp_path))
    model.add_entity("Widget", "widget.1")
    # color deliberately never set

    profile = {
        "name": "generic_test",
        "requirements": [
            {"entity_class": "Widget", "checks": [
                {"attribute": "color", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "widget.1" in errors[0]
    assert "color" in errors[0]


def test_generic_validate_for_analysis_checks_numeric_constraints(tmp_path):
    model = build_ear_model(_widget_schema(tmp_path))
    model.add_entity("Widget", "widget.1")
    model.add_attribute("widget.1", "weight_kg", -5)

    profile = {
        "name": "generic_test",
        "requirements": [
            {"entity_class": "Widget", "checks": [
                {"attribute": "weight_kg", "required": True, "constraints": {"minimum": 0}},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "minimum" in errors[0]


def test_generic_validate_for_analysis_checks_enum_constraints(tmp_path):
    model = build_ear_model(_widget_schema(tmp_path))
    model.add_entity("Widget", "widget.1")
    model.add_attribute("widget.1", "color", "purple")  # not in the enum

    profile = {
        "name": "generic_test",
        "requirements": [
            {"entity_class": "Widget", "checks": [
                {"attribute": "color", "required": True, "constraints": {"enum": ["red", "green", "blue"]}},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "purple" in errors[0]


def test_generic_validate_for_analysis_checks_relations_too(tmp_path):
    """partOf is a relation, not an attribute -- must work the same way,
    using core EAR's own get_attr_value() (which reads both uniformly)."""
    model = build_ear_model(_widget_schema(tmp_path))
    model.add_entity("Widget", "widget.1")
    model.add_entity("Widget", "widget.2")
    model.add_relation("widget.1", "partOf", "widget.2")

    profile = {
        "name": "generic_test",
        "requirements": [
            {"entity_class": "Widget", "checks": [
                {"attribute": "partOf", "required": True},
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    # widget.1 has partOf set; widget.2 doesn't -- exactly one error
    assert len(errors) == 1
    assert "widget.2" in errors[0]


def test_generic_model_passes_cleanly_when_fully_specified(tmp_path):
    model = build_ear_model(_widget_schema(tmp_path))
    model.add_entity("Widget", "widget.1")
    model.add_attribute("widget.1", "weight_kg", 12.5)
    model.add_attribute("widget.1", "color", "red")

    profile = {
        "name": "generic_test",
        "requirements": [
            {"entity_class": "Widget", "checks": [
                {"attribute": "weight_kg", "required": True, "constraints": {"minimum": 0}},
                {"attribute": "color", "required": True, "constraints": {"enum": ["red", "green", "blue"]}},
            ]},
        ],
    }
    assert model.validate_for_analysis(profile) == []


def test_generic_model_cannot_resolve_a_view_family_style_attribute(tmp_path):
    """The whole point of the split: a plain EAR model has no concept
    of representation views at all, so an attribute that doesn't exist
    directly on the entity must be reported as unknown -- not silently
    resolved somewhere, since there's nowhere else to look."""
    model = build_ear_model(_widget_schema(tmp_path))
    model.add_entity("Widget", "widget.1")

    profile = {
        "name": "generic_test",
        "requirements": [
            {"entity_class": "Widget", "checks": [
                {"attribute": "nominal_power_capacity", "required": True},  # a CESDM-only attribute
            ]},
        ],
    }
    errors = model.validate_for_analysis(profile)
    assert len(errors) == 1
    assert "not a known attribute or relation" in errors[0]


def test_generic_validate_for_analysis_or_raise_works_too(tmp_path):
    model = build_ear_model(_widget_schema(tmp_path))
    model.add_entity("Widget", "widget.1")

    profile = {
        "name": "generic_test",
        "requirements": [
            {"entity_class": "Widget", "checks": [{"attribute": "color", "required": True}]},
        ],
    }
    with pytest.raises(ValueError, match="generic_test"):
        model.validate_for_analysis_or_raise(profile)
