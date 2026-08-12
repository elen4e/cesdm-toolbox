"""Tests for export include_library='none'|'referenced'|'all'."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

from cesdm import build_model_from_yaml
from cesdm.default_library import GeneratorTypes


ROOT = Path(__file__).resolve().parent.parent


def _model_with_full_library_and_one_generator():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library/default_library"))
    model.add_entity("EnergySystemModel", "demo")
    model.add_entity("ElectricalBus", "bus.1")
    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.hasTechnology = GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW
    gen.atNode = "bus.1"
    return model


def _csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as f:
        return max(0, sum(1 for _ in csv.DictReader(f)))


def test_include_library_referenced_keeps_only_reachable_library_entities(tmp_path):
    model = _model_with_full_library_and_one_generator()
    out = tmp_path / "referenced"
    model.export_frictionless(out, name="ref", include_library="referenced")

    dp = json.loads((out / "datapackage.json").read_text())
    assert dp["custom"]["cesdm:include_library"] == "referenced"

    assert _csv_row_count(out / "resources" / "GeneratorType.csv") == 1
    assert _csv_row_count(out / "resources" / "Carrier.csv") >= 1
    # Full library has dozens of generator types; referenced must be far smaller.
    assert _csv_row_count(out / "resources" / "GeneratorType.csv") < 10
    assert (out / "resources" / "GenerationUnit.csv").exists()
    assert (out / "resources" / "ElectricalBus.csv").exists()


def test_include_library_none_omits_library_tables(tmp_path):
    model = _model_with_full_library_and_one_generator()
    out = tmp_path / "none"
    model.export_frictionless(out, name="none", include_library="none")

    assert not (out / "resources" / "GeneratorType.csv").exists()
    assert not (out / "resources" / "Carrier.csv").exists()
    assert not (out / "resources" / "NaturalResource.csv").exists()
    assert not (out / "resources" / "StorageType.csv").exists()
    assert (out / "resources" / "GenerationUnit.csv").exists()
    # Relation value is still on the asset row.
    with (out / "resources" / "GenerationUnit.csv").open(newline="", encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["hasTechnology"] == GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW


def test_include_library_all_keeps_full_catalogue(tmp_path):
    model = _model_with_full_library_and_one_generator()
    out = tmp_path / "all"
    model.export_frictionless(out, name="all", include_library="all")

    # Catalogue size follows library/default_library (not a fixed magic number).
    n_gen_types = len(model.entities.get("GeneratorType") or {})
    n_carriers = len(model.entities.get("Carrier") or {})
    assert n_gen_types >= 30
    assert _csv_row_count(out / "resources" / "GeneratorType.csv") == n_gen_types
    assert _csv_row_count(out / "resources" / "Carrier.csv") == n_carriers
    assert n_carriers >= 5


def test_include_library_default_is_referenced(tmp_path):
    model = _model_with_full_library_and_one_generator()
    out = tmp_path / "default"
    model.export_frictionless(out, name="default")
    assert _csv_row_count(out / "resources" / "GeneratorType.csv") == 1


def test_include_library_invalid_raises():
    model = _model_with_full_library_and_one_generator()
    with pytest.raises(ValueError, match="include_library"):
        model._exportable_entity_ids("maybe")


def test_yaml_hierarchical_respects_include_library(tmp_path):
    model = _model_with_full_library_and_one_generator()
    path = tmp_path / "model.yaml"
    model.export_yaml_hierarchical(path, include_library="referenced")
    doc = yaml.safe_load(path.read_text())
    assert "GenerationUnit" in doc
    assert set(doc.get("GeneratorType", {})) == {
        GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_NEW
    }
