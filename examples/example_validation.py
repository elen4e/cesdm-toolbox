#!/usr/bin/env python3
"""
example_validation.py

Walk through typical ``model.validate()`` checks: required relations,
enums, numeric min/max, wrong relation targets, and assign-time unit
errors. Contrasts briefly with ``validate_for_analysis`` (study readiness).

Each section is a self-contained function so the same code can be imported
into a Jupyter notebook (see ``notebooks/cesdm_schema_validation.ipynb``).

Complementary example: ``example_analysis_validation.py`` focuses on
analysis profiles; this one focuses on schema constraints.

Run from the repository root:

    python examples/example_validation.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cesdm_toolbox import CesdmModel, build_model_from_yaml  # noqa: E402
from cesdm.default_library import (  # noqa: E402
    CarrierDomains,
    Carriers,
    GeneratorTypes,
    StorageTypes,
)

_ATTRS_YAML = REPO_ROOT / "schemas" / "cesdm" / "attributes" / "attributes.yaml"
_RELS_YAML = REPO_ROOT / "schemas" / "cesdm" / "relations" / "relations.yaml"
_NETWORK_NODE_YAML = (
    REPO_ROOT
    / "schemas"
    / "cesdm"
    / "entities"
    / "SemanticEntity"
    / "NetworkNode"
    / "NetworkNode.yaml"
)
_OPTIMAL_DISPATCH_YAML = REPO_ROOT / "analysis_profiles" / "optimal_dispatch.yaml"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _print_errors(errors: list[str], *, limit: int = 20) -> None:
    if not errors:
        print("  (no errors)")
        return
    print(f"  {len(errors)} error(s):")
    for err in errors[:limit]:
        print(f"   - {err}")
    if len(errors) > limit:
        print(f"   … {len(errors) - limit} more")


def _extract_indented_key_block(text: str, key: str, *, key_indent: int = 2) -> str:
    """Extract a mapping entry ``key:`` at ``key_indent`` spaces (with its children)."""
    prefix = f"{' ' * key_indent}{key}:"
    lines = text.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        if line == prefix or line.startswith(prefix + " ") or line.startswith(prefix + "\t"):
            start = i
            break
    if start is None:
        raise KeyError(f"key {key!r} not found at indent {key_indent}")

    block = [lines[start]]
    for line in lines[start + 1 :]:
        if not line.strip():
            block.append(line)
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading <= key_indent and not line.lstrip().startswith("#"):
            break
        block.append(line)
    # Drop trailing blank lines
    while block and not block[-1].strip():
        block.pop()
    return "\n".join(block)


def _extract_list_item_by_id(text: str, item_id: str) -> str:
    """Extract a YAML list item that starts with ``- id: <item_id>``."""
    needle = f"- id: {item_id}"
    lines = text.splitlines()
    start: int | None = None
    item_indent: int | None = None
    for i, line in enumerate(lines):
        if needle in line and line.lstrip().startswith("- id:"):
            start = i
            item_indent = len(line) - len(line.lstrip(" "))
            break
    if start is None or item_indent is None:
        raise KeyError(f"list item id={item_id!r} not found")

    block = [lines[start]]
    for line in lines[start + 1 :]:
        if not line.strip():
            block.append(line)
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading <= item_indent and line.lstrip().startswith("- "):
            break
        if leading < item_indent:
            break
        block.append(line)
    while block and not block[-1].strip():
        block.pop()
    return "\n".join(block)


def _extract_requirements_entity_block(text: str, entity_class: str) -> str:
    """Extract one ``- entity_class: …`` block from an analysis profile."""
    needle = f"entity_class: {entity_class}"
    lines = text.splitlines()
    start: int | None = None
    item_indent: int | None = None
    for i, line in enumerate(lines):
        if needle in line:
            # Walk back to the list dash for this requirement
            j = i
            while j >= 0 and not lines[j].lstrip().startswith("- entity_class:"):
                j -= 1
            if j < 0:
                continue
            start = j
            item_indent = len(lines[j]) - len(lines[j].lstrip(" "))
            break
    if start is None or item_indent is None:
        raise KeyError(f"entity_class {entity_class!r} not found in profile")

    block = [lines[start]]
    for line in lines[start + 1 :]:
        if not line.strip():
            block.append(line)
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading <= item_indent and line.lstrip().startswith("- "):
            break
        if leading < item_indent:
            break
        block.append(line)
    while block and not block[-1].strip():
        block.pop()
    return "\n".join(block)


def schema_reason_snippets(topic: str) -> list[tuple[str, str, str]]:
    """Return ``(relative_path, caption, yaml_snippet)`` for a demo topic."""
    attrs = _ATTRS_YAML.read_text(encoding="utf-8")
    rels = _RELS_YAML.read_text(encoding="utf-8")

    def rel(path: Path) -> str:
        try:
            return str(path.relative_to(REPO_ROOT))
        except ValueError:
            return str(path)

    table: dict[str, list[tuple[Path, str, str]]] = {
        "missing_relation": [
            (
                _NETWORK_NODE_YAML,
                "NetworkNode declares the slot as required",
                _extract_list_item_by_id(_NETWORK_NODE_YAML.read_text(encoding="utf-8"), "belongsToCarrierDomain"),
            ),
            (
                _RELS_YAML,
                "Global relation: required + target CarrierDomain",
                _extract_indented_key_block(rels, "belongsToCarrierDomain"),
            ),
        ],
        "enum": [
            (
                _ATTRS_YAML,
                "Allowed dispatch_type values",
                _extract_indented_key_block(attrs, "dispatch_type"),
            ),
        ],
        "min_max": [
            (
                _ATTRS_YAML,
                "nominal_power_capacity ≥ 0",
                _extract_indented_key_block(attrs, "nominal_power_capacity"),
            ),
            (
                _ATTRS_YAML,
                "energy_conversion_efficiency in [0, 1]",
                _extract_indented_key_block(attrs, "energy_conversion_efficiency"),
            ),
        ],
        "soc_range": [
            (
                _ATTRS_YAML,
                "initial_state_of_charge in [0, 1]",
                _extract_indented_key_block(attrs, "initial_state_of_charge"),
            ),
        ],
        "wrong_target": [
            (
                _RELS_YAML,
                "hasOutputCarrier may only target Carrier",
                _extract_indented_key_block(rels, "hasOutputCarrier"),
            ),
        ],
        "unit": [
            (
                _ATTRS_YAML,
                "annual_energy_demand unit enum",
                _extract_indented_key_block(attrs, "annual_energy_demand"),
            ),
        ],
        "bus_enum": [
            (
                _ATTRS_YAML,
                "Allowed powerflow_bus_type values",
                _extract_indented_key_block(attrs, "powerflow_bus_type"),
            ),
        ],
        "analysis": [
            (
                _OPTIMAL_DISPATCH_YAML,
                "Study profile (not schema): DemandUnit needs hasDemandProfile",
                _extract_requirements_entity_block(
                    _OPTIMAL_DISPATCH_YAML.read_text(encoding="utf-8"),
                    "DemandUnit",
                ),
            ),
        ],
        "or_raise": [
            (
                _ATTRS_YAML,
                "Same enum constraint as section 3",
                _extract_indented_key_block(attrs, "dispatch_type"),
            ),
        ],
    }
    if topic not in table:
        raise KeyError(f"Unknown schema topic {topic!r}; choose from {sorted(table)}")
    return [(rel(path), caption, body) for path, caption, body in table[topic]]


def _in_jupyter_notebook() -> bool:
    """True only inside a Jupyter kernel (not a plain terminal / script)."""
    try:
        from IPython import get_ipython

        ip = get_ipython()
    except Exception:
        return False
    return ip is not None and ip.__class__.__name__ == "ZMQInteractiveShell"


def show_schema_reason(topic: str) -> None:
    """Print / display the schema (or analysis-profile) YAML that explains a failure.

    In Jupyter this uses Markdown code blocks; in a plain terminal it prints
    the same excerpts.
    """
    snippets = schema_reason_snippets(topic)
    if _in_jupyter_notebook():
        from IPython.display import Markdown, display

        for path, caption, body in snippets:
            display(
                Markdown(
                    f"**Why validation fails** — `{path}`  \n"
                    f"*{caption}*\n\n"
                    f"```yaml\n{body}\n```"
                )
            )
        return

    print("  Why validation fails (schema / profile excerpt):")
    for path, caption, body in snippets:
        print(f"  --- {path} — {caption}")
        for line in body.splitlines():
            print(f"  | {line}")


def build_minimal_valid_model(schema_dir: Path | None = None) -> CesdmModel:
    """Tiny electricity model that passes ``model.validate()`` with no issues."""
    schema = schema_dir or (REPO_ROOT / "schemas" / "cesdm")
    model = build_model_from_yaml(str(schema))
    model.import_library(str(REPO_ROOT / "library" / "default_library"))
    model.import_library(str(REPO_ROOT / "library" / "regions_library"))

    region = model.get_entity("region.country.CH")
    elec_domain = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)

    bus = model.add_entity("ElectricalBus", "bus.demo.elec")
    bus.name = "Demo electricity bus"
    bus.nominal_voltage = (20.0, "kV")
    bus.powerflow_bus_type = "PQ"
    bus.belongsToCarrierDomain = elec_domain
    bus.belongsToGeographicalRegion = region

    gen = model.add_entity("GenerationUnit", "gen.demo.wind")
    gen.name = "Demo wind farm"
    gen.nominal_power_capacity = (50.0, "MW")
    gen.energy_conversion_efficiency = 1.0
    gen.dispatch_type = "nondispatchable"
    gen.hasTechnology = GeneratorTypes.GENERATION_RENEWABLE_WIND_ONSHORE
    gen.hasOutputCarrier = Carriers.CARRIER_ELECTRICITY
    gen.atNode = bus

    dem = model.add_entity("DemandUnit", "dem.demo.elec")
    dem.name = "Demo electricity demand"
    dem.annual_energy_demand = (100_000.0, "MWh/year")
    dem.atNode = bus

    return model


# ---------------------------------------------------------------------------
# Demo sections (each starts from a fresh valid model unless noted)
# ---------------------------------------------------------------------------

def demo_clean_validate(model: CesdmModel | None = None) -> list[str]:
    """Baseline: a well-formed model returns an empty error list."""
    model = model or build_minimal_valid_model()
    errors = model.validate()
    _print_section("1. Clean model — model.validate()")
    print("A structurally complete CESDM model should report 0 schema errors.")
    _print_errors(errors)
    return errors


def demo_missing_required_relation() -> list[str]:
    """Omit belongsToCarrierDomain → required-relation error."""
    model = build_minimal_valid_model()
    orphan = model.add_entity("ElectricalBus", "bus.demo.orphan")
    orphan.name = "Orphan bus (no carrier domain)"
    orphan.nominal_voltage = (20.0, "kV")
    # intentionally no belongsToCarrierDomain

    errors = model.validate()
    _print_section("2. Missing required relation")
    print("NetworkNode subclasses require belongsToCarrierDomain.")
    _print_errors([e for e in errors if "bus.demo.orphan" in e] or errors)
    show_schema_reason("missing_relation")
    return errors


def demo_enum_constraint() -> list[str]:
    """Invalid enum value: warns on assign, caught by validate()."""
    model = build_minimal_valid_model()
    gen = model.get_entity("gen.demo.wind")

    _print_section("3. Enum constraint (dispatch_type)")
    print("Allowed: dispatchable | nondispatchable | must_run")
    print("Assigning invalid value 'steerable' (warning may print now)…")
    with warnings.catch_warnings(record=True):
        gen.dispatch_type = "steerable"

    errors = model.validate()
    _print_errors(errors)
    show_schema_reason("enum")

    print("\nFixing to 'nondispatchable'…")
    gen.dispatch_type = "nondispatchable"
    print(f"After fix: {len(model.validate())} error(s)")
    return errors


def demo_numeric_min_max() -> list[str]:
    """Negative capacity and efficiency > 1.0 violate min/max."""
    model = build_minimal_valid_model()
    gen = model.get_entity("gen.demo.wind")

    _print_section("4. Numeric min / max constraints")
    print("Setting nominal_power_capacity = -10 MW (min 0)…")
    gen.nominal_power_capacity = (-10.0, "MW")
    print("Setting energy_conversion_efficiency = 1.4 (max 1.0)…")
    gen.energy_conversion_efficiency = 1.4

    errors = model.validate()
    _print_errors(errors)
    show_schema_reason("min_max")

    print("\nRestoring valid values…")
    gen.nominal_power_capacity = (50.0, "MW")
    gen.energy_conversion_efficiency = 1.0
    print(f"After fix: {len(model.validate())} error(s)")
    return errors


def demo_range_state_of_charge() -> list[str]:
    """initial_state_of_charge must be in [0, 1]."""
    model = build_minimal_valid_model()
    bus = model.get_entity("bus.demo.elec")
    stor = model.add_entity("StorageUnit", "stor.demo.battery")
    stor.name = "Demo battery"
    stor.atNode = bus
    stor.hasTechnology = StorageTypes.STORAGE_ELECTROCHEMICAL_BATTERY
    stor.initial_state_of_charge = 1.5  # invalid

    errors = model.validate()
    _print_section("5. Range constraint (state of charge)")
    print("initial_state_of_charge must be between 0 and 1 inclusive.")
    _print_errors([e for e in errors if "stor.demo" in e] or errors)
    show_schema_reason("soc_range")
    return errors


def demo_wrong_relation_target() -> list[str]:
    """hasOutputCarrier must point at a Carrier, not a StorageType."""
    model = build_minimal_valid_model()
    gen = model.get_entity("gen.demo.wind")
    # Core API: store an incompatible target class
    model.add_relation(
        "gen.demo.wind",
        "hasOutputCarrier",
        StorageTypes.STORAGE_ELECTROCHEMICAL_BATTERY,
    )

    errors = model.validate()
    _print_section("6. Wrong relation target class")
    print("hasOutputCarrier expects Carrier; StorageType is incompatible.")
    _print_errors([e for e in errors if "hasOutputCarrier" in e] or errors)
    show_schema_reason("wrong_target")

    # Restore for clarity if reused
    gen.hasOutputCarrier = Carriers.CARRIER_ELECTRICITY
    return errors


def demo_unit_error_at_assign() -> None:
    """Wrong unit raises ValueError immediately — never reaches validate()."""
    model = build_minimal_valid_model()
    dem = model.get_entity("dem.demo.elec")

    _print_section("7. Unit mismatch (assign-time ValueError)")
    print("annual_energy_demand allows only MWh/year — not GWh.")
    try:
        dem.annual_energy_demand = (100.0, "GWh")
    except ValueError as exc:
        print(f"  Raised: {exc}")
    else:
        print("  Unexpected: no exception")
    print(f"  model.validate() still clean: {model.validate() == []}")
    show_schema_reason("unit")


def demo_bus_type_enum() -> list[str]:
    """powerflow_bus_type enum on ElectricalBus."""
    model = build_minimal_valid_model()
    bus = model.get_entity("bus.demo.elec")
    bus.powerflow_bus_type = "slackk"  # typo

    errors = model.validate()
    _print_section("8. Enum on ElectricalBus (powerflow_bus_type)")
    print("Allowed: slack | PV | PQ")
    _print_errors(errors)
    show_schema_reason("bus_enum")
    bus.powerflow_bus_type = "PQ"
    return errors


def _optimal_dispatch_profile() -> Path:
    """Absolute path — bare names resolve via CWD and break when Jupyter starts in notebooks/."""
    return REPO_ROOT / "analysis_profiles" / "optimal_dispatch.yaml"


def demo_analysis_contrast() -> tuple[list[str], list[str]]:
    """Schema OK but not ready for optimal_dispatch (missing study fields)."""
    model = build_minimal_valid_model()
    # Schema-valid generators often omit dispatch costs — analysis profiles catch that.
    schema_errors = model.validate()
    profile = _optimal_dispatch_profile()
    analysis_errors = model.validate_for_analysis(profile)

    _print_section("9. Schema vs analysis validation")
    print("Same model, two questions:")
    print(f"  model.validate()                        → {len(schema_errors)} error(s)")
    print(f"  validate_for_analysis({profile.name!r}) → {len(analysis_errors)} error(s)")
    if analysis_errors:
        print("  Sample analysis findings:")
        for err in analysis_errors[:5]:
            print(f"   - {err}")
    print(
        "\n  Tip: see examples/example_analysis_validation.py for the full "
        "study-readiness walkthrough."
    )
    show_schema_reason("analysis")
    return schema_errors, analysis_errors


def demo_validate_or_raise() -> None:
    """CESDM helper that raises ValueError when schema validation fails."""
    model = build_minimal_valid_model()
    gen = model.get_entity("gen.demo.wind")
    gen.dispatch_type = "steerable"

    _print_section("10. validate_or_raise()")
    try:
        model.validate_or_raise()
    except ValueError as exc:
        msg = str(exc)
        print(f"  Raised ValueError ({len(msg)} chars). First line:")
        print(f"   {msg.splitlines()[0] if msg else msg}")
    else:
        print("  Unexpected: no exception")
    show_schema_reason("or_raise")


# ---------------------------------------------------------------------------
# Notebook / test entry points
# ---------------------------------------------------------------------------

SECTION_RUNNERS: list[tuple[str, Callable[[], object]]] = [
    ("clean", lambda: demo_clean_validate()),
    ("missing_relation", demo_missing_required_relation),
    ("enum", demo_enum_constraint),
    ("min_max", demo_numeric_min_max),
    ("soc_range", demo_range_state_of_charge),
    ("wrong_target", demo_wrong_relation_target),
    ("unit", demo_unit_error_at_assign),
    ("bus_enum", demo_bus_type_enum),
    ("analysis", demo_analysis_contrast),
    ("or_raise", demo_validate_or_raise),
]


def run_all_demos() -> None:
    """Run every section in order (CLI / notebook end-to-end)."""
    print("CESDM schema validation demo")
    print(f"Repo: {REPO_ROOT}")
    for _key, runner in SECTION_RUNNERS:
        runner()
    print()
    print("Done. Import individual demo_* functions in a notebook to step through.")


def main() -> None:
    run_all_demos()
    out_dir = REPO_ROOT / "output" / "validation_demo"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Export only the clean baseline (not the intentionally broken demos).
    clean = build_minimal_valid_model()
    assert clean.validate() == []
    clean.export_yaml_hierarchical(out_dir / "model.yaml")
    print(f"\nWrote clean baseline → {out_dir / 'model.yaml'}")


if __name__ == "__main__":
    main()
