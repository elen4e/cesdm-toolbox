"""
Every schema YAML file's filename must equal its declared ``name:``
field plus ``.yaml`` (e.g. ``Demand.DispatchView.yaml`` must contain
``name: Demand.DispatchView``).

This is a discoverability guarantee, not a loader requirement — CESDM
class identity comes from the ``name:`` field, not the file path (see
docs/schema_layout.md), so a mismatch doesn't break loading. But a
mismatch does mean grepping for a class name won't find its file,
which is exactly the kind of drift that crept into schemas/views/*
before this test existed (see CHANGELOG.md). This test exists so it
can't happen silently again.

Registry files (attributes.yaml, relations.yaml, SCHEMA_MANIFEST.yaml)
are exempt: they aren't single-class definition files. (Any file
starting with "_" is also exempt, for forward-compatibility — no such
files exist in the tree today; see CHANGELOG.md re. the removed
_index.yaml mechanism.)
"""

import pathlib

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_ROOTS = ["schemas/cesdm", "schemas/agentbased"]

EXEMPT_FILENAMES = {"attributes.yaml", "relations.yaml", "SCHEMA_MANIFEST.yaml"}


def _iter_class_schema_files():
    for root in SCHEMA_ROOTS:
        root_path = REPO_ROOT / root
        if not root_path.is_dir():
            continue
        for f in sorted(root_path.rglob("*.y*ml")):
            if f.name in EXEMPT_FILENAMES or f.name.startswith("_"):
                continue
            yield f


@pytest.mark.parametrize("path", list(_iter_class_schema_files()), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_schema_filename_matches_declared_class_name(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "name" not in data:
        pytest.skip(f"{path}: no top-level 'name:' field (not a single-class definition file)")

    class_name = data["name"]
    expected_filename = f"{class_name}.yaml"

    assert path.name == expected_filename, (
        f"{path.relative_to(REPO_ROOT)}: filename does not match declared "
        f"class name {class_name!r}. Expected filename {expected_filename!r}."
    )
