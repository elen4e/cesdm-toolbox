#!/usr/bin/env python3
"""example_ear_generic_domain.py

Demonstrates that the EAR engine (`ear_toolbox`) is genuinely
domain-agnostic: the same `add_entity`/`add_attribute`/`add_relation`
primitives, `validate()`, and export/import methods used throughout
the energy-system examples work identically for a completely different
domain -- here, a small household/energy-community/municipality
dataset (`schemas/agentbased/`), with zero energy-specific code.

`ear.entity_proxy.EntityProxy` (a generic str-subclass wrapper with
direct attribute/relation assignment and `.add_attribute()`/
`.add_relation()`) works here too, unlike `cesdm.proxy`'s
domain-specific layer (`.dispatch`, `.power_flow`, `.connect(...)`,
built specifically for CESDM's energy-domain groups) -- see
docs/architecture/proxy_api.md for the full split between the two.
See docs/guide/09_ear_toolbox.md for the same example walked through
step by step, and docs/getting_started.md for how this compares to
the energy-domain CESDM/proxy layers.
"""

from __future__ import annotations

from pathlib import Path

from ear_toolbox import build_model_from_yaml
from ear.entity_proxy import EntityProxy


def build_model():
    model = build_model_from_yaml("schemas/agentbased")

    model.add_entity(entity_class="Canton", entity_id="canton.zh")
    model.add_attribute("canton.zh", "name", "Zürich")

    model.add_entity(entity_class="Organisation", entity_id="org.sunergy")
    model.add_attribute("org.sunergy", "name", "Sunergy Genossenschaft")

    model.add_entity(entity_class="Municipality", entity_id="mun.zurich.261")
    model.add_attribute("mun.zurich.261", "name", "Zürich")
    model.add_attribute("mun.zurich.261", "bfs_code", 261)
    model.add_attribute("mun.zurich.261", "population", 420_000)
    model.add_relation("mun.zurich.261", "isPartOf", "canton.zh")

    model.add_entity(entity_class="EnergyCommittee", entity_id="ec.sunergy.zh.001")
    model.add_attribute("ec.sunergy.zh.001", "name", "Sunergy Zürich-West")
    model.add_attribute("ec.sunergy.zh.001", "member_count", 48)
    model.add_relation("ec.sunergy.zh.001", "locatedIn", "mun.zurich.261")
    model.add_relation("ec.sunergy.zh.001", "hasOperator", "org.sunergy")

    model.add_entity(entity_class="Household", entity_id="hh.zh.001.0042")
    model.add_attribute("hh.zh.001.0042", "occupant_count", 3)
    model.add_attribute("hh.zh.001.0042", "has_pv", True)
    model.add_relation("hh.zh.001.0042", "locatedIn", "mun.zurich.261")
    model.add_relation("hh.zh.001.0042", "memberOf", "ec.sunergy.zh.001")

    model.add_entity(entity_class="Household", entity_id="hh.zh.001.0043")
    model.add_attribute("hh.zh.001.0043", "occupant_count", 2)
    model.add_attribute("hh.zh.001.0043", "has_pv", False)
    model.add_relation("hh.zh.001.0043", "locatedIn", "mun.zurich.261")

    return model


def main() -> None:
    model = build_model()

    errors = model.validate()
    print(f"model.validate(): {len(errors)} error(s)")

    # Querying uses only generic EAR primitives -- get_attr_value() reads
    # attributes *and* relations uniformly, with no energy-specific helper
    # methods anywhere (no .dispatch, no add_generator, ...).
    prosumers = [
        eid for eid, _ in model.entities["Household"].items()
        if model.get_attr_value("Household", eid, "has_pv") is True
    ]
    print("Prosumer households:", prosumers)

    total_occupants = sum(
        model.get_attr_value("Household", eid, "occupant_count") or 0
        for eid in model.entities["Household"]
    )
    print("Total occupants across all households:", total_occupants)

    # The generic EntityProxy (ear.entity_proxy) works here too -- it
    # needs nothing beyond core EAR concepts (class_attributes(),
    # class_relations(), ...), unlike cesdm.proxy's `.dispatch`/
    # `.power_flow`/`.connect(...)`, which are CESDM-specific and
    # genuinely don't apply to this schema.
    first_household_id = next(iter(model.entities["Household"]))
    household = EntityProxy(model, first_household_id)
    print(f"\n{household!r}")
    print("household.occupant_count (direct attribute access):", household.occupant_count)
    household.occupant_count = household.occupant_count + 1
    print("after household.occupant_count += 1:", household.occupant_count)

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "output" / "ear_generic_domain"
    out_dir.mkdir(parents=True, exist_ok=True)
    model.export_yaml(out_dir / "households.yaml")
    print(f"\nWrote {out_dir / 'households.yaml'}")

    # Re-import and confirm it round-trips cleanly.
    reloaded = build_model_from_yaml("schemas/agentbased")
    reloaded.import_yaml(out_dir / "households.yaml")
    reload_errors = reloaded.validate()
    assert not reload_errors, reload_errors
    print("Re-imported and re-validated successfully.")


if __name__ == "__main__":
    main()
