#!/usr/bin/env python3
"""example_schema_extension.py

Demonstrates how to add a genuinely new entity type to CESDM *without
touching the core schema at all* -- writing a small, separate schema
tree that `extends:` the core `schemas/cesdm/` directory (the same mechanism
`schemas/agentbased/` uses), then loading and using it exactly like
any built-in class. See docs/getting-started/schemas-in-depth.md for the
schema authoring model this relies on.

The new type here is `ElectricVehicleChargingStation`, a controllable
electricity demand asset that doesn't correspond well to any existing
CESDM class -- its dispatch attributes are declared directly on it,
tagged `belongsToGroup: [dispatch]`, so `.dispatch` on the proxy API
resolves to them automatically, exactly like any built-in asset class
(see CHANGELOG.md: this toolbox's "initial version without views" --
there's no separate DispatchView class to define at all any more).

One schema-authoring practice worth noting: before defining a new
attribute, check whether one with the same meaning already exists.
`maximum_charging_power` turned out to already be a registered CESDM
attribute (added for a different asset originally) -- reused directly
below, rather than redefined. Only `number_of_charging_points` was
genuinely new.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cesdm_toolbox import build_model_from_yaml  # noqa: E402


def write_schema_extension(extension_dir: Path) -> None:
    """Write a small, self-contained schema extension to disk."""
    (extension_dir / "assets").mkdir(parents=True, exist_ok=True)
    (extension_dir / "attributes").mkdir(parents=True, exist_ok=True)

    # extends: is resolved relative to this manifest's own directory --
    # computed here so the example works regardless of where it's run from.
    core_schemas_rel = os.path.relpath(REPO_ROOT / "schemas/cesdm", extension_dir)

    (extension_dir / "SCHEMA_MANIFEST.yaml").write_text(f"""\
version: "0.1.0"
description: >
  Example schema extension adding ElectricVehicleChargingStation as a
  new CESDM asset type, without modifying the core schema at all.
changelog: none
extends:
  - {core_schemas_rel}
stability:
  assets: experimental
  attributes: experimental
  relations: experimental
""")

    # Only the genuinely new attribute -- maximum_charging_power already
    # exists in the core schema and is reused as-is below.
    (extension_dir / "attributes" / "attributes.yaml").write_text("""\
attributes:
  number_of_charging_points:
    label: Number of Charging Points
    description: Count of individual EV charging points at the station.
    value:
      type: integer
      constraints:
        minimum: 1
""")

    (extension_dir / "assets" / "ElectricVehicleChargingStation.yaml").write_text("""\
name: ElectricVehicleChargingStation
parents:
  - EnergyAssetInstance
description: >
  A public or private electric-vehicle charging installation, modelled
  as a controllable electricity demand asset. Dispatch attributes are
  declared directly here (belongsToGroup: [dispatch]) rather than on a
  separate view class -- see CHANGELOG.md.
attributes:
  - id: number_of_charging_points
    required: true
  - id: maximum_charging_power
    required: true
    belongsToGroup: [dispatch]
  - id: annual_energy_demand
    required: false
    belongsToGroup: [dispatch]
relations:
  - id: atNode
    required: false
    belongsToGroup: [topology]
""")


def main() -> None:
    out_dir = REPO_ROOT / "output" / "schema_extension_example"
    extension_dir = out_dir / "schemas_ev_charging"
    write_schema_extension(extension_dir)
    print(f"Wrote schema extension to {extension_dir}")

    # Loading the extension directory also pulls in every core CESDM
    # class via `extends:`.
    model = build_model_from_yaml(extension_dir)
    print("ElectricVehicleChargingStation registered:",
          "ElectricVehicleChargingStation" in model.classes)

    carrier = model.ensure_entity(
        class_name="Carrier", entity_id="carrier.electricity", name="Electricity",
    )
    electricity = model.ensure_entity(
        class_name="CarrierDomain", entity_id="domain.electricity",
    )
    electricity.hasCarrier = carrier
    bus = model.ensure_entity(class_name="ElectricalBus", entity_id="bus.1")
    bus.nominal_voltage = 20
    bus.belongsToCarrierDomain = electricity

    # No add_entity()-wrapping constructor exists specifically for this
    # new class -- there are no per-class constructors at all any more
    # (see CHANGELOG.md), so it's built with the exact same
    # add_entity()/ensure_entity() calls every entity, built-in or not,
    # uses.
    station = model.ensure_entity(
        class_name="ElectricVehicleChargingStation", entity_id="ev.station.1",
        name="Highway rest-stop charger",
    )
    station.number_of_charging_points = 8
    station.dispatch.maximum_charging_power = 2.0
    station.dispatch.annual_energy_demand = 3500

    # atNode is declared with belongsToGroup: [topology] directly on the
    # new class above, so connect() (the same proxy method every other
    # asset uses) works on it exactly as-is -- no separate topology view
    # or dedicated builder needed for the new class at all.
    station.connect("bus.1")

    errors = model.validate()
    print(f"model.validate(): {len(errors)} error(s)")
    for err in errors:
        print(f"  - {err}")

    model.export_yaml_hierarchical(out_dir / "ev_charging_model.yaml")
    print(f"Wrote {out_dir / 'ev_charging_model.yaml'}")


if __name__ == "__main__":
    main()
