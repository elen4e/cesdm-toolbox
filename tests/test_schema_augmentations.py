from pathlib import Path

import pytest

from ear import build_model_from_yaml


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _schema_trees(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "base"
    ext = tmp_path / "extension"

    _write(
        base / "attributes.yaml",
        """
attributes:
  name:
    description: Human-readable name.
    value:
      type: string
""",
    )
    _write(base / "relations.yaml", "relations: {}\n")
    _write(
        base / "entities" / "classes.yaml",
        """
entity_classes:
  Thing:
    attributes:
      - id: name
  SpecialThing:
    parents: Thing
  Agent:
    attributes:
      - id: name
""",
    )

    _write(
        ext / "attributes" / "agent.yaml",
        """
attributes:
  bidding_strategy:
    description: Strategy used by an agent-controlled thing.
    value:
      type: string
      constraints:
        enum: [price_taker, strategic]
""",
    )
    _write(
        ext / "relations" / "agent.yaml",
        """
relations:
  ownedByAgent:
    description: Agent that owns the thing.
    target: Agent
    cardinality: 0..1
""",
    )
    _write(
        ext / "augmentation.yaml",
        """
augmentations:
  Thing:
    attributes:
      - id: bidding_strategy
        belongsToGroup: agent_based
    relations:
      - id: ownedByAgent
        belongsToGroup: agent_based
""",
    )
    return base, ext


def test_augmentation_attaches_global_fields_and_is_inherited(tmp_path: Path) -> None:
    base, ext = _schema_trees(tmp_path)
    model = build_model_from_yaml([base, ext])

    thing = model.classes["Thing"]
    special = model.classes["SpecialThing"]

    assert "bidding_strategy" in thing.attributes
    assert "ownedByAgent" in thing.relations
    assert "bidding_strategy" in special.attributes
    assert "ownedByAgent" in special.relations
    assert thing.attributes["bidding_strategy"].belongsToGroup == ["agent_based"]

    model.add_entity("Agent", "agent.1")
    model.add_entity("SpecialThing", "thing.1")
    model.add_attribute("thing.1", "bidding_strategy", "strategic")
    model.add_relation("thing.1", "ownedByAgent", "agent.1")

    assert model.validate() == []


def test_augmentation_rejects_unknown_loaded_attribute(tmp_path: Path) -> None:
    base, ext = _schema_trees(tmp_path)
    _write(
        ext / "augmentation.yaml",
        """
augmentations:
  Thing:
    attributes:
      - id: not_registered
""",
    )

    with pytest.raises(ValueError, match="base or extension attributes registry"):
        build_model_from_yaml([base, ext])


def test_augmentation_rejects_inline_field_definition(tmp_path: Path) -> None:
    base, ext = _schema_trees(tmp_path)
    _write(
        ext / "augmentation.yaml",
        """
augmentations:
  Thing:
    attributes:
      - id: local_only
        value:
          type: string
""",
    )

    with pytest.raises(ValueError, match="inline field definitions are not allowed"):
        build_model_from_yaml([base, ext])


def test_augmentation_rejects_unknown_target_class(tmp_path: Path) -> None:
    base, ext = _schema_trees(tmp_path)
    _write(
        ext / "augmentation.yaml",
        """
augmentations:
  MissingThing:
    attributes:
      - id: bidding_strategy
""",
    )

    with pytest.raises(ValueError, match="Target class 'MissingThing' does not exist"):
        build_model_from_yaml([base, ext])


def test_extension_registry_does_not_modify_base_files(tmp_path: Path) -> None:
    base, ext = _schema_trees(tmp_path)
    before_attributes = (base / "attributes.yaml").read_text(encoding="utf-8")
    before_relations = (base / "relations.yaml").read_text(encoding="utf-8")

    model = build_model_from_yaml([base, ext])

    assert "bidding_strategy" in model.global_attributes
    assert "ownedByAgent" in model.global_relations
    assert (base / "attributes.yaml").read_text(encoding="utf-8") == before_attributes
    assert (base / "relations.yaml").read_text(encoding="utf-8") == before_relations
