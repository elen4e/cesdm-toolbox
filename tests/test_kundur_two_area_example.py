"""Kundur two-area example is analysis-ready for power flow and dynamics."""

from __future__ import annotations

from pathlib import Path

from cesdm_toolbox import build_model_from_yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_kundur():
    from examples.example_kundur_two_area import build_kundur

    model = build_model_from_yaml(str(REPO_ROOT / "schemas" / "cesdm"))
    build_kundur(model)
    return model


def test_kundur_schema_validation_is_clean():
    assert _build_kundur().validate() == []


def test_kundur_passes_power_flow_analysis_profile():
    assert _build_kundur().validate_for_analysis("power_flow") == []


def test_kundur_passes_dynamics_analysis_profile():
    assert _build_kundur().validate_for_analysis("dynamics") == []
