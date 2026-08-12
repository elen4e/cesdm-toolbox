"""
An asset can legitimately carry zero direct attributes/relations of
its own while all its real data lives in a linked entity (e.g. a
GenerationUnit whose only content is a GenerationUnit.DispatchResult
from an analysis run) — this is a normal shape, not an edge case.

export_yaml_hierarchical() used to drop such an asset (and its
attached views) from the export entirely, because it checked whether
the asset's own block was empty *before* looking up and attaching its
views. Found while validating the results-view restructuring (see
CHANGELOG.md); fixed in
cesdm.domain.model.hierarchical_yaml.export_yaml_hierarchical.

Rewritten to use a linked Result entity instead of the old
Storage.DispatchView representation view, which no longer exists at
all -- results (and controllers, and the dynamic machine model) are
standalone entities now, linked via an ordinary relation
(reportsOn/controlsGenerationUnit), not representation views
nested under the asset on export.
"""

from cesdm_toolbox import build_model_from_yaml


def _build_bare_asset_with_linked_result():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "gen.bare")
    model.add_entity("DispatchRunRecord", "run.1")
    model.add_entity("GenerationUnit.DispatchResult", "gen.bare.result")
    model.add_relation("gen.bare.result", "reportsOn", "gen.bare")
    model.add_relation("gen.bare.result", "hasRunRecord", "run.1")
    model.add_attribute("gen.bare.result", "total_generation", 1234.0)
    return model


def test_bare_asset_with_linked_result_survives_hierarchical_export(tmp_path):
    model = _build_bare_asset_with_linked_result()
    out_path = tmp_path / "bare_with_result.yaml"
    model.export_yaml_hierarchical(str(out_path))

    text = out_path.read_text(encoding="utf-8")
    assert "gen.bare" in text
    assert "GenerationUnit.DispatchResult" in text
    assert "total_generation" in text


def test_bare_asset_with_linked_result_round_trips(tmp_path):
    model = _build_bare_asset_with_linked_result()
    out_path = tmp_path / "bare_with_result.yaml"
    model.export_yaml_hierarchical(str(out_path))

    model2 = build_model_from_yaml("schemas/cesdm")
    summary = model2.import_yaml_hierarchical(str(out_path))

    assert "gen.bare" in model2.entities.get("GenerationUnit", {})
    results = model2.entities.get("GenerationUnit.DispatchResult", {})
    result = next((r for r in results.values() if r.data.get("reportsOn") == "gen.bare"), None)
    assert result is not None
    assert not summary["unknowns"]


def test_truly_empty_entity_still_skipped(tmp_path):
    """An entity with no attributes, relations, or linked entities should
    still be omitted."""
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GeographicalRegion", "region.empty")
    out_path = tmp_path / "empty.yaml"
    model.export_yaml_hierarchical(str(out_path))

    text = out_path.read_text(encoding="utf-8")
    assert "region.empty" not in text
