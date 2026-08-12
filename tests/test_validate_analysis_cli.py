"""Tests for tools/validate_analysis.py -- the CLI that checks a given
CESDM model file against one or more analysis profiles (e.g.
optimal_dispatch, power_flow). Exercises the CLI as a real subprocess
(matching how a user would actually run it), plus a couple of direct
unit-level checks of the format auto-detection.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cesdm_toolbox import build_model_from_yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "tools" / "validate_analysis.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    # Mirrors conftest.py's sys.path fix, which only applies within the
    # pytest process itself: this CLI runs as a separate subprocess (so
    # a real user's "python tools/validate_analysis.py ..." is
    # exercised faithfully), which does not inherit that -- without
    # this, every test here fails with `ModuleNotFoundError: No module
    # named 'cesdm_toolbox'` in any environment where `pip install -e .`
    # hasn't been run, even though the rest of the test suite passes
    # fine in that same environment.
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + existing if existing else "")
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture()
def complete_yaml_model(tmp_path) -> Path:
    model = build_model_from_yaml("schemas/cesdm")
    bus = model.add_entity(entity_class="ElectricalBus", entity_id="bus.1")
    bus.add_attribute(attribute_id="nominal_voltage", value=380, unit="kV")

    gen = model.add_entity(entity_class="GenerationUnit", entity_id="gen.1")
    gen.atNode = "bus.1"
    gen.add_relation(relation_id="hasTechnology", target_entity_id="Generation.Thermal.Gas.CCGT.New")
    gen.dispatch.nominal_power_capacity = 400
    gen.dispatch.variable_operating_cost = 30

    path = tmp_path / "model.yaml"
    model.export_yaml_hierarchical(str(path))
    return path


@pytest.fixture()
def incomplete_yaml_model(tmp_path) -> Path:
    model = build_model_from_yaml("schemas/cesdm")
    gen = model.add_entity(entity_class="GenerationUnit", entity_id="gen.bare")
    # A genuinely empty entity (zero attributes/relations) isn't written
    # to the export at all -- give it a plain identity attribute so it
    # round-trips through export/import, while still lacking every
    # dispatch-required field (hasTechnology, atNode,
    # nominal_power_capacity, variable_operating_cost).
    gen.name = "Bare generator"

    path = tmp_path / "model.yaml"
    model.export_yaml_hierarchical(str(path))
    return path


def test_clean_model_exits_zero_and_reports_ready(complete_yaml_model):
    result = _run(str(complete_yaml_model), "--profile", "optimal_dispatch")
    assert result.returncode == 0, result.stderr
    assert "optimal_dispatch: ready" in result.stdout
    assert "All profiles passed" in result.stdout


def test_incomplete_model_exits_one_and_lists_errors(incomplete_yaml_model):
    result = _run(str(incomplete_yaml_model), "--profile", "optimal_dispatch")
    assert result.returncode == 1
    assert "issue(s)" in result.stdout
    assert "missing required" in result.stdout


def test_multiple_profiles_in_one_run(complete_yaml_model):
    """The model is optimal_dispatch-ready but not power_flow-ready (no
    bus type / setpoints set) -- confirms both are checked independently
    and the overall exit code reflects the worse of the two."""
    result = _run(str(complete_yaml_model), "--profile", "optimal_dispatch", "--profile", "power_flow")
    assert result.returncode == 1
    assert "optimal_dispatch: ready" in result.stdout
    assert "power_flow: " in result.stdout and "issue(s)" in result.stdout


def test_json_output_is_well_formed_and_matches_human_output(complete_yaml_model):
    result = _run(str(complete_yaml_model), "--profile", "optimal_dispatch", "--profile", "power_flow", "--json")
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["results"]["optimal_dispatch"]["valid"] is True
    assert data["results"]["optimal_dispatch"]["errors"] == []
    assert data["results"]["power_flow"]["valid"] is False
    assert len(data["results"]["power_flow"]["errors"]) > 0


def test_frictionless_directory_is_auto_detected(tmp_path, complete_yaml_model):
    model = build_model_from_yaml("schemas/cesdm")
    model.import_yaml_hierarchical(str(complete_yaml_model))
    out_dir = tmp_path / "frictionless_out"
    model.export_frictionless(out_dir, name="test", title="Test")

    result = _run(str(out_dir), "--profile", "optimal_dispatch")
    assert result.returncode == 0, result.stderr
    assert "optimal_dispatch: ready" in result.stdout


def test_unrecognised_file_format_exits_two(tmp_path):
    bogus = tmp_path / "model.txt"
    bogus.write_text("not a real model file")
    result = _run(str(bogus), "--profile", "optimal_dispatch")
    assert result.returncode == 2
    assert "unrecognised" in result.stderr.lower()


def test_missing_model_file_exits_two():
    result = _run("/tmp/this_file_does_not_exist_at_all.yaml", "--profile", "optimal_dispatch")
    assert result.returncode == 2
    assert "Could not load" in result.stderr


def test_unknown_profile_name_exits_two(complete_yaml_model):
    result = _run(str(complete_yaml_model), "--profile", "no_such_profile")
    assert result.returncode == 2
    assert "Could not load analysis profile" in result.stderr


def test_multiple_schema_dirs(complete_yaml_model):
    result = _run(
        str(complete_yaml_model),
        "--profile", "optimal_dispatch",
        "--schema", "schemas/cesdm",
        "--schema", "schemas/agentbased",
    )
    assert result.returncode == 0, result.stderr


def test_profile_argument_is_required(complete_yaml_model):
    result = _run(str(complete_yaml_model))
    assert result.returncode != 0
    assert "required" in result.stderr.lower()
