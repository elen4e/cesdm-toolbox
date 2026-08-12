"""Smoke-test the schema validation demo example."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_validation_demo_clean_model_and_checks():
    import sys

    sys.path.insert(0, str(REPO_ROOT / "examples"))
    from example_validation import (
        build_minimal_valid_model,
        demo_enum_constraint,
        demo_missing_required_relation,
        demo_numeric_min_max,
        demo_unit_error_at_assign,
        demo_wrong_relation_target,
    )

    model = build_minimal_valid_model(REPO_ROOT / "schemas" / "cesdm")
    assert model.validate() == []

    missing = demo_missing_required_relation()
    assert any("belongsToCarrierDomain" in e for e in missing)

    enum_errors = demo_enum_constraint()
    assert any("dispatch_type" in e for e in enum_errors)

    min_max = demo_numeric_min_max()
    assert any("minimum" in e for e in min_max)
    assert any("maximum" in e for e in min_max)

    wrong = demo_wrong_relation_target()
    assert any("hasOutputCarrier" in e for e in wrong)

    demo_unit_error_at_assign()  # must not raise unexpectedly


def test_schema_reason_snippets_cover_demo_topics():
    import sys

    sys.path.insert(0, str(REPO_ROOT / "examples"))
    from example_validation import schema_reason_snippets

    for topic in (
        "missing_relation",
        "enum",
        "min_max",
        "soc_range",
        "wrong_target",
        "unit",
        "bus_enum",
        "analysis",
        "or_raise",
    ):
        snippets = schema_reason_snippets(topic)
        assert snippets
        for path, caption, body in snippets:
            assert path
            assert caption
            assert ":" in body
