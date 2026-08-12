"""
Guards against the unit-string inconsistencies found and fixed in this
pass: the same physical unit spelled multiple incompatible ways (pu vs
p.u., deg vs degree vs degrees, percent vs %, Fraction vs Fraction
(0-1) vs Fraction 0-1 vs '-'), malformed enum values with commas baked
into a single string instead of being separate list items, and
non-unit placeholders (List) used in a unit field. See CHANGELOG.md
for the full rationale.
"""

from cesdm_toolbox import build_model_from_yaml

# Known-superseded spellings that must never reappear once a canonical
# form has been chosen. Not an exhaustive style guide -- just a
# regression guard for the specific duplicates found and fixed.
BANNED_UNIT_STRINGS = {
    "p.u.", "percent", "Fraction", "Fraction (0-1)", "Fraction 0-1", "-",
    "degree", "degrees", "decimal degrees", "tCO2_per_MWh", "List",
}


def _all_unit_enums(model):
    for aid, adef in model.global_attributes.items():
        enum = (adef.get("unit") or {}).get("constraints", {}).get("enum")
        if enum:
            yield aid, enum


def test_no_banned_unit_spellings():
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    offenders = []
    for aid, enum in _all_unit_enums(model):
        for u in enum:
            if u in BANNED_UNIT_STRINGS:
                offenders.append((aid, u))
    assert not offenders, (
        f"Superseded unit spelling(s) reappeared: {offenders}. "
        f"Use the canonical form instead (see CHANGELOG.md)."
    )


def test_no_comma_crammed_unit_values():
    """A unit enum value must be one unit, not several comma-separated
    units crammed into a single string (the investment_cost /
    fixed_operating_cost bug)."""
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    offenders = [
        (aid, u) for aid, enum in _all_unit_enums(model) for u in enum if "," in u
    ]
    assert not offenders, f"Comma-crammed unit value(s) found: {offenders}"


def test_percent_and_pu_are_singly_spelled():
    """Direct check that the two highest-traffic canonicalizations stuck."""
    model = build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])
    all_units = {u for _, enum in _all_unit_enums(model) for u in enum}
    assert "%" in all_units
    assert "percent" not in all_units
    assert "pu" in all_units
    assert "p.u." not in all_units
