"""
ear/model/persistence_yaml_json.py's import_yaml() and
cesdm/domain/model/hierarchical_yaml.py's import_yaml_hierarchical()
both used to call add_relation() once per target when a relation had
more than one target_entity_id -- silently overwriting with only the
last one, since add_relation() itself has no accumulation semantics
(confirmed directly: calling it twice for the same (entity, relation)
pair overwrites rather than appends, and passing a list of targets
directly gets stringified rather than stored as a real list).

Found via tools/aggregate_cesdm_model.py's per-country technology
aggregation, which is the first place in the whole codebase to ever
need one entity to genuinely hold more than one target through the
same relation id (HydroGenerationUnit.drawsFromHydraulicStorage, after
merging different reservoir-side technology groups onto one
generator) -- but the bug lives in the generic EAR persistence layer
itself, not the aggregation tool, so it's tested here independently of
it.
"""

from __future__ import annotations

from pathlib import Path

from cesdm_toolbox import build_model_from_yaml

ROOT = Path(__file__).resolve().parent.parent


def _build_model_with_multi_target_relation():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.add_entity("HydraulicStorageUnit", "res.a")
    model.add_attribute("res.a", "name", "res.a")
    model.add_entity("HydraulicStorageUnit", "res.b")
    model.add_attribute("res.b", "name", "res.b")
    model.add_entity("HydroGenerationUnit", "gen.1")
    model.add_attribute("gen.1", "name", "gen.1")
    model.add_relation("gen.1", "drawsFromHydraulicStorage", "res.a")
    model.add_relation("gen.1", "drawsFromHydraulicStorage", "res.b")
    return model


def test_add_relation_itself_has_no_accumulation_semantics():
    """Documents the actual root cause directly: add_relation() always
    *sets*, never *appends* -- calling it twice for the same
    (entity, relation) pair keeps only the second value. This is why
    the import-side fix below has to build the list explicitly rather
    than relying on repeated add_relation() calls."""
    model = _build_model_with_multi_target_relation()
    stored = model.entities["HydroGenerationUnit"]["gen.1"].data.get("drawsFromHydraulicStorage")
    assert stored == "res.b"  # NOT a list -- this is the behaviour being worked around


def test_import_yaml_hierarchical_preserves_every_target(tmp_path):
    model = _build_model_with_multi_target_relation()
    # Bypass add_relation()'s single-value behaviour once, directly on
    # the entity's own data, to get a genuinely multi-valued relation
    # into the exported file -- the same thing
    # tools/aggregate_cesdm_model.py's data_to_model() now does.
    model.entities["HydroGenerationUnit"]["gen.1"].data["drawsFromHydraulicStorage"] = ["res.a", "res.b"]

    yaml_path = tmp_path / "model.yaml"
    model.export_yaml_hierarchical(str(yaml_path))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml_hierarchical(str(yaml_path))

    stored = reloaded.entities["HydroGenerationUnit"]["gen.1"].data.get("drawsFromHydraulicStorage")
    assert isinstance(stored, list), f"expected a real list, got {stored!r}"
    assert set(stored) == {"res.a", "res.b"}


def test_import_yaml_flat_preserves_every_target(tmp_path):
    model = _build_model_with_multi_target_relation()
    model.entities["HydroGenerationUnit"]["gen.1"].data["drawsFromHydraulicStorage"] = ["res.a", "res.b"]

    yaml_path = tmp_path / "model.yaml"
    model.export_yaml(str(yaml_path))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml(str(yaml_path))

    stored = reloaded.entities["HydroGenerationUnit"]["gen.1"].data.get("drawsFromHydraulicStorage")
    assert isinstance(stored, list), f"expected a real list, got {stored!r}"
    assert set(stored) == {"res.a", "res.b"}


def test_single_target_relation_still_stores_a_plain_scalar(tmp_path):
    """The common case (one target) must stay exactly as before -- a
    plain string, not a single-element list -- so this fix doesn't
    change behaviour for the overwhelming majority of relations that
    are genuinely single-valued."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.add_entity("HydraulicStorageUnit", "res.a")
    model.add_attribute("res.a", "name", "res.a")
    model.add_entity("HydroGenerationUnit", "gen.1")
    model.add_attribute("gen.1", "name", "gen.1")
    model.add_relation("gen.1", "drawsFromHydraulicStorage", "res.a")

    yaml_path = tmp_path / "model.yaml"
    model.export_yaml_hierarchical(str(yaml_path))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml_hierarchical(str(yaml_path))

    stored = reloaded.entities["HydroGenerationUnit"]["gen.1"].data.get("drawsFromHydraulicStorage")
    assert stored == "res.a"
    assert not isinstance(stored, list)
