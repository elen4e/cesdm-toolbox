"""
schemas/cesdm/units/units.yaml is the central, single source of truth for
every unit used across the schema tree — the structural fix for "the
unit spellings are canonical today, but nothing stops the next
contributor from introducing a new inconsistent spelling tomorrow"
(see CHANGELOG.md and docs/architecture/schema_governance.md,
"Attribute and relation naming conventions").

load_classes_from_yaml() validates every attribute's unit(s) against
this registry at load time: an attribute using an unregistered unit
string fails to load immediately, rather than silently introducing
drift that only a manual audit would eventually catch.
"""

import pathlib

import pytest
import yaml

from cesdm_toolbox import build_model_from_yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_units_registry_loads():
    model = build_model_from_yaml("schemas/cesdm")
    assert len(model.global_units) >= 40
    assert "MW" in model.global_units
    assert model.unit_info("MW")["quantity_kind"] == "power"


def test_every_attribute_unit_is_registered():
    """Direct, from-first-principles version of what load_classes_from_yaml
    already enforces at load time -- this test exists so a CI failure here
    points straight at the offending attribute without needing to parse a
    load-time exception message."""
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    offenders = []
    for aid, adef in model.global_attributes.items():
        enum = ((adef or {}).get("unit") or {}).get("constraints", {}).get("enum") or []
        for u in enum:
            if u not in model.global_units:
                offenders.append((aid, u))
    assert not offenders, f"Unregistered unit(s): {offenders}"


def test_unregistered_unit_fails_to_load(tmp_path):
    """Prove the enforcement is real, not just documentation, using a
    throwaway scratch schema tree."""
    schema_dir = tmp_path / "scratch"
    (schema_dir / "core").mkdir(parents=True)
    (schema_dir / "attributes").mkdir()
    (schema_dir / "units").mkdir()

    (schema_dir / "core" / "Thing.yaml").write_text(
        "name: Thing\nparents: []\ndescription: test\n"
        "attributes:\n- id: bogus_attr\nrelations: []\n"
    )
    (schema_dir / "attributes" / "attributes.yaml").write_text(
        "attributes:\n  bogus_attr:\n    description: test\n"
        "    value:\n      type: decimal\n"
        "    unit:\n      constraints:\n        enum:\n        - MegaWatt\n"
    )
    # copy the real registry so MegaWatt (not MW) is the only unregistered one
    import shutil
    shutil.copy(REPO_ROOT / "schemas/cesdm" / "units" / "units.yaml", schema_dir / "units" / "units.yaml")

    with pytest.raises(ValueError, match="MegaWatt"):
        build_model_from_yaml(str(schema_dir))


def test_units_yaml_is_excluded_from_class_scan():
    """units.yaml itself must never be mistaken for an entity-class file."""
    model = build_model_from_yaml("schemas/cesdm")
    assert "units" not in model.classes
    data = yaml.safe_load((REPO_ROOT / "schemas/cesdm" / "units" / "units.yaml").read_text())
    assert "name" not in data
