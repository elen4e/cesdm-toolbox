"""
attributes/ and relations/ are the two "registry" folders (flat
id -> spec dictionaries, referenced by id from entity class
definitions elsewhere — see docs/schema_layout.md). Membership used to
require a curated `_index.yaml` with an explicit `imports:` list; that
mechanism was removed (see CHANGELOG.md) because the ordering it
provided was never functionally meaningful — a duplicate id across
files was always a hard error, never "last file wins" — and requiring
a second file to keep in sync with reality for no benefit was exactly
the kind of drift that left schemas/agentbased/assets/_index.yaml
stale.

Registry folders are now auto-discovered the same way every other
schema folder is (glob every *.yaml file). This test proves that:

1. a new file dropped into attributes/ or relations/ is picked up
   automatically, with no registration step, and
2. the one property that did matter — a registry id must not be
   defined twice with conflicting specs — is still enforced.
"""

import textwrap

import pytest

from cesdm_toolbox import build_model_from_yaml

MINIMAL_CORE_CLASS = textwrap.dedent("""\
    name: Thing
    parents: []
    description: minimal test class
    attributes:
    - id: greeting
    relations: []
""")


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_new_registry_file_is_auto_discovered_without_registration(tmp_path):
    """A file in attributes/ with no _index.yaml (or any other registration) still loads."""
    schema_dir = tmp_path / "scratch_schema"
    _write(schema_dir / "core" / "Thing.yaml", MINIMAL_CORE_CLASS)

    attrs_dir = schema_dir / "attributes"
    _write(attrs_dir / "greetings.yaml", "attributes:\n  greeting:\n    value:\n      type: string\n")
    _write(attrs_dir / "farewells.yaml", "attributes:\n  farewell:\n    value:\n      type: string\n")

    model = build_model_from_yaml(str(schema_dir))
    assert "greeting" in model.global_attributes
    assert "farewell" in model.global_attributes


def test_duplicate_registry_id_across_files_still_raises(tmp_path):
    """The one property _index.yaml's uniqueness check provided is preserved."""
    schema_dir = tmp_path / "scratch_schema_dup"
    _write(schema_dir / "core" / "Thing.yaml", MINIMAL_CORE_CLASS)

    attrs_dir = schema_dir / "attributes"
    _write(attrs_dir / "a.yaml", "attributes:\n  greeting:\n    value:\n      type: string\n")
    _write(attrs_dir / "b.yaml", "attributes:\n  greeting:\n    value:\n      type: integer\n")

    with pytest.raises(ValueError, match="Duplicate attribute id 'greeting'"):
        build_model_from_yaml(str(schema_dir))


def test_no_index_yaml_files_remain_in_repo_schema_trees():
    """_index.yaml is no longer a recognized mechanism anywhere in this repo's schemas."""
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    leftover = list((repo_root / "schemas/cesdm").rglob("_index.yaml")) + list(
        (repo_root / "schemas/agentbased").rglob("_index.yaml")
    )
    assert not leftover, f"stale _index.yaml files found: {leftover}"
