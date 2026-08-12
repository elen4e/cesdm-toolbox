"""
Guards the item 1/3/4 fixes from this pass:
- carrier_group / resource_group have real, closed enums (mirroring
  CESDM's own fixed Bus node types and the resource_group description's
  own stated examples, respectively).
- The five *_of_charge / discount_rate / salvage_fraction_value
  fraction attributes have their intended maximum: 1.0 bound actually
  enforced (it previously sat in a stray top-level `constraints:` key
  the loader never reads — see docs/architecture/schema_governance.md,
  "Attribute and relation naming conventions").
- No attribute has a stray top-level `constraints:` key at all.
- Every attribute has a non-empty description.
"""

import pathlib

import pytest
import yaml

from cesdm_toolbox import build_model_from_yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_carrier_group_has_closed_enum():
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    enum = model.global_attributes["carrier_group"]["value"]["constraints"]["enum"]
    assert set(enum) == {"electricity", "gas", "heat", "hydrogen", "water"}


def test_resource_group_has_closed_enum():
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    enum = model.global_attributes["resource_group"]["value"]["constraints"]["enum"]
    assert set(enum) == {"renewable", "hydro", "geothermal", "environmental"}


@pytest.mark.parametrize("aid", [
    "initial_state_of_charge",
    "maximum_state_of_charge",
    "minimum_state_of_charge",
    "discount_rate",
    "salvage_fraction_value",
])
def test_fraction_attributes_have_maximum_one_enforced(aid):
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    constraints = model.global_attributes[aid]["value"]["constraints"]
    assert constraints.get("minimum") == 0.0
    assert constraints.get("maximum") == 1.0


def test_no_stray_top_level_constraints_key_anywhere():
    """A top-level `constraints:` key on an attribute is silently
    ignored by the loader (see ear/attribute_def.py) -- this guards
    against the exact bug found and fixed this session (7 occurrences,
    several containing an intended-but-never-enforced maximum: 1.0)."""
    offenders = []
    for schema_root in ["schemas/cesdm", "schemas/agentbased"]:
        attr_dir = REPO_ROOT / schema_root / "attributes"
        if not attr_dir.is_dir():
            continue
        for f in attr_dir.glob("*.yaml"):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            for aid, adef in (data.get("attributes") or {}).items():
                if isinstance(adef, dict) and "constraints" in adef:
                    offenders.append(f"{schema_root}/attributes/{f.name}:{aid}")
    assert not offenders, f"Stray top-level 'constraints:' key found: {offenders}"


def test_every_attribute_has_a_description():
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    missing = [
        aid for aid, adef in model.global_attributes.items()
        if not (adef.get("description") or "").strip()
    ]
    assert not missing, f"Attributes missing a description: {missing}"
