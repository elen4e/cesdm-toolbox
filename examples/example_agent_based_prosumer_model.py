#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Example: build an agent-based prosumer layer on top of a CESDM model.

This example uses the prosumer schema extension (Household, EnergyCommittee,
ProsumerAgent, AggregatorAgent, AgentBasedModel, AgentDecisionView) together
with standard CESDM power-system assets. It can either load an existing CESDM
YAML model or create a small low-voltage starter system.

Already written entirely on the object-oriented proxy API/builders
(``ensure_entity``, ``add_bus``, ``create_demand_unit``,
``add_solar_generator``, ``create_storage_unit``) -- no raw
``add_entity``/``add_attribute``/``add_relation`` calls for the core
domain objects at all -- so this file needed essentially no changes
when the rest of examples/ was converted; see
docs/guides/proxy-api.md.

Usage
-----
    python examples/example_agent_based_prosumer_model.py \
        --input path/to/existing_cesdm.yaml \
        --output build/agent_based_prosumer_model.yaml

If --input is omitted, the script creates a minimal CESDM electricity system
with one bus, three households, PV, batteries and demand assets.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "tools")]

from cesdm_toolbox import build_model_from_yaml  # noqa: E402


def _ensure_base_system(model):
    """Create a minimal electricity system if the input YAML does not provide one."""
    model.import_library(str(REPO_ROOT / "library" / "default_library"))
    model.import_library(str(REPO_ROOT / "library" / "regions_library"))
    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_type="electricity")
    model.ensure_resource("resource.renewable.solar", name="Solar irradiance", resource_type="solar")

    domain = model.ensure_entity(
        class_name="CarrierDomain", entity_id="domain.electricity", name="Electricity domain",
    )
    domain.hasCarrier = "carrier.electricity"

    model.add_entity(entity_class="ElectricalBus", entity_id="bus.lv.demo")
    model.add_attribute("bus.lv.demo", "nominal_voltage", 0.4)
    model.add_relation("bus.lv.demo", "belongsToGeographicalRegion", "region.country.CH")
    model.add_relation("bus.lv.demo", "belongsToCarrierDomain", "domain.electricity")    model.add_attribute("bus.lv.demo", "powerflow_bus_type", "PQ")
    model.add_attribute("bus.lv.demo", "voltage_magnitude_setpoint", 1.0)
    model.add_attribute("bus.lv.demo", "voltage_angle_setpoint", 0.0)


def _first_bus(model) -> str:
    buses = model.entities.get("ElectricalBus", {})
    if buses:
        return next(iter(buses))
    _ensure_base_system(model)
    return "bus.lv.demo"


def build_agent_based_prosumer_model(input_yaml: Path | None = None):
    schema_dir = REPO_ROOT / "schemas/cesdm"
    schema_agent_based_dir = REPO_ROOT / "schemas/agentbased"
    model = build_model_from_yaml([schema_dir,schema_agent_based_dir])
    if input_yaml and input_yaml.exists():
        model.import_yaml_model(input_yaml)
    else:
        _ensure_base_system(model)

    bus_id = _first_bus(model)

    # ------------------------------------------------------------------
    # 1. Spatial and social entities from the prosumer schema
    # ------------------------------------------------------------------
    model.ensure_entity(class_name="Canton", entity_id="canton.zh", name="Zurich")
    model.ensure_entity(
        class_name="Municipality",
        entity_id="municipality.demo",
        name="Demo Municipality",
        bfs_code=261,
        canton="ZH",
        population=18_000,
        urbanisation_level="suburban",
    )
    model.add_relation_if_allowed("municipality.demo", "isPartOf", "canton.zh", strict=True)

    model.ensure_entity(class_name="Organisation", entity_id="org.demo.utility", name="Demo Municipal Utility")
    model.ensure_entity(
        class_name="EnergyCommittee",
        entity_id="community.demo",
        name="Demo Local Energy Community",
        founding_year=2024,
        member_count=3,
        total_pv_capacity_kwp=24.0,
        self_sufficiency_rate=0.58,
        legal_form="cooperative",
    )
    model.add_relation_if_allowed("community.demo", "locatedIn", "municipality.demo", strict=True)
    model.add_relation_if_allowed("community.demo", "hasOperator", "org.demo.utility", strict=True)

    model.ensure_entity(class_name="LowVoltageNode", entity_id="lvnode.demo.01", name="LV feeder node 01")

    # ------------------------------------------------------------------
    # 2. Time-series profiles used as agent information signals
    # ------------------------------------------------------------------
    model.ensure_entity(
        class_name="TimestampSeries", entity_id="timestamps.agent.demo.yearly",
        start_datetime="2025-01-01T00:00:00Z",
        resolution="P1Y",
        length=6,
        timezone="UTC",
    )
    ts_id = "timestamps.agent.demo.yearly"
    model.ensure_entity(
        class_name="Profile", entity_id="profile.retail_tariff.demo",
        profile_type="as_SI",
        profile_unit="CHF/MWh",
        data_reference="/profiles/profile.retail_tariff.demo/values",
    )
    model.add_relation_if_allowed("profile.retail_tariff.demo", "hasTimestampSeries", ts_id, strict=True)
    model.ensure_entity(
        class_name="Profile", entity_id="profile.pv_subsidy.demo",
        profile_type="as_SI",
        profile_unit="CHF/kWp",
        data_reference="/profiles/profile.pv_subsidy.demo/values",
    )
    model.add_relation_if_allowed("profile.pv_subsidy.demo", "hasTimestampSeries", ts_id, strict=True)
    model.ensure_entity(
        class_name="Profile", entity_id="profile.solar.demo.availability",
        profile_type="as_capacity_factor",
        profile_unit="p.u.",
        data_reference="/profiles/profile.solar.demo.availability/values",
    )
    model.add_relation_if_allowed("profile.solar.demo.availability", "hasTimestampSeries", ts_id, strict=True)

    # ------------------------------------------------------------------
    # 3. Households, physical CESDM assets, and prosumer agents
    # ------------------------------------------------------------------
    households = [
        {
            "id": "household.001",
            "occupants": 4,
            "building": "detached",
            "ownership": "owner",
            "area": 160.0,
            "demand_kwh": 5200.0,
            "pv_kw": 8.0,
            "battery_mwh": 0.012,
            "risk": 0.25,
            "price": 0.80,
            "env": 0.75,
        },
        {
            "id": "household.002",
            "occupants": 2,
            "building": "semi-detached",
            "ownership": "owner",
            "area": 105.0,
            "demand_kwh": 3600.0,
            "pv_kw": 6.0,
            "battery_mwh": 0.0,
            "risk": 0.45,
            "price": 0.65,
            "env": 0.60,
        },
        {
            "id": "household.003",
            "occupants": 3,
            "building": "apartment",
            "ownership": "tenant",
            "area": 85.0,
            "demand_kwh": 4100.0,
            "pv_kw": 0.0,
            "battery_mwh": 0.0,
            "risk": 0.70,
            "price": 0.55,
            "env": 0.40,
        },
    ]

    controlled_assets: list[str] = []
    for i, hh in enumerate(households, start=1):
        hh_id = hh["id"]
        model.ensure_entity(
            class_name="Household",
            entity_id=hh_id,
            name=f"Household {i}",
            occupant_count=hh["occupants"],
            building_type=hh["building"],
            ownership_status=hh["ownership"],
            gross_floor_area_m2=hh["area"],
            annual_consumption_kwh=hh["demand_kwh"],
            has_pv=hh["pv_kw"] > 0,
            has_battery=hh["battery_mwh"] > 0,
            has_ev=False,
            adoption_year=2025 if hh["pv_kw"] > 0 else None,
        )
        model.add_relation_if_allowed(hh_id, "locatedIn", "municipality.demo", strict=True)
        model.add_relation_if_allowed(hh_id, "memberOf", "community.demo")
        model.add_relation_if_allowed(hh_id, "connectedTo", "lvnode.demo.01")

        demand_id = f"demand.{hh_id}"
        model.add_entity(entity_class="DemandUnit", entity_id=demand_id)
        model.ensure_carrier("carrier.electricity")
        model.add_relation_if_allowed(demand_id, "hasInputCarrier", "carrier.electricity")
        model.add_relation(demand_id, "atNode", bus_id)
        demand_asset = model.get_entity(entity_id=demand_id)
        demand_asset.dispatch.annual_energy_demand = hh["demand_kwh"] / 1000.0
        model.add_relation_if_allowed(hh_id, "ownsAsset", demand_id)
        controlled_assets.append(demand_id)

        if hh["pv_kw"] > 0:
            pv_id = f"pv.{hh_id}"
            model.add_entity(entity_class="GenerationUnit", entity_id=pv_id)
            model.add_relation(pv_id, "hasTechnology", "Generation.Renewable.Solar.PV.Rooftop")
            model.add_relation(pv_id, "hasInputResource", "resource.renewable.solar")
            model.add_relation(pv_id, "atNode", bus_id)
            pv_asset = model.get_entity(entity_id=pv_id)
            pv_asset.dispatch.nominal_power_capacity = hh["pv_kw"] / 1000.0
            pv_asset.dispatch.maximum_generation = hh["pv_kw"] / 1000.0
            pv_asset.dispatch.variable_operating_cost = 0.0
            model.add_relation_if_allowed(hh_id, "ownsAsset", pv_id)
            model.attach_profile(
                pv_id,
                "hasAvailabilityProfile",
                "profile.solar.demo.availability",
            )
            controlled_assets.append(pv_id)

        if hh["battery_mwh"] > 0:
            bat_id = f"battery.{hh_id}"
            model.add_entity(entity_class="StorageUnit", entity_id=bat_id)
            model.set_technology(bat_id, "Storage.Battery.LithiumIon", technology_class="StorageType")
            model.ensure_carrier("carrier.electricity")
            model.add_relation_if_allowed(bat_id, "storesCarrier", "carrier.electricity")
            model.add_relation(bat_id, "atNode", bus_id)
            bat_asset = model.get_entity(entity_id=bat_id)
            bat_asset.dispatch.energy_storage_capacity = hh["battery_mwh"]
            bat_asset.dispatch.nominal_power_capacity = 0.005
            bat_asset.dispatch.charging_efficiency = 0.95
            bat_asset.dispatch.discharging_efficiency = 0.95
            model.add_relation_if_allowed(hh_id, "ownsAsset", bat_id)
            controlled_assets.append(bat_id)

        agent_id = f"agent.{hh_id}"
        model.ensure_entity(
            class_name="ProsumerAgent",
            entity_id=agent_id,
            name=f"Prosumer agent {i}",
            agent_kind="prosumer",
            decision_rule="bounded_rationality",
            information_level="local",
            risk_aversion=hh["risk"],
            price_sensitivity=hh["price"],
            environmental_preference=hh["env"],
            comfort_preference=0.75,
            adoption_threshold=0.55,
            pv_adoption_probability=0.70 if hh["pv_kw"] > 0 else 0.20,
            battery_adoption_probability=0.65 if hh["battery_mwh"] > 0 else 0.25,
            ev_adoption_probability=0.15,
        )
        model.add_relation_if_allowed(agent_id, "actsFor", hh_id, strict=True)
        model.add_relation_if_allowed(agent_id, "participatesIn", "community.demo")
        model.add_relation_if_allowed(agent_id, "observesProfile", "profile.retail_tariff.demo")
        model.add_relation_if_allowed(agent_id, "observesProfile", "profile.pv_subsidy.demo")
        for asset_id in controlled_assets[-3:]:
            model.add_relation_if_allowed(agent_id, "controlsAsset", asset_id)

        view_id = f"agent_decision_view.{agent_id}"
        model.ensure_entity(
            class_name="AgentDecisionView",
            entity_id=view_id,
            decision_rule="bounded_rationality",
            adoption_threshold=0.55,
            price_sensitivity=hh["price"],
            risk_aversion=hh["risk"],
            comfort_preference=0.75,
        )
        model.add_relation_if_allowed(view_id, "representsAgent", agent_id, strict=True)
        model.add_relation_if_allowed(view_id, "observesProfile", "profile.retail_tariff.demo")
        model.add_relation_if_allowed(view_id, "observesProfile", "profile.pv_subsidy.demo")

    # ------------------------------------------------------------------
    # 4. Aggregator and ABM scenario configuration
    # ------------------------------------------------------------------
    model.ensure_entity(
        class_name="AggregatorAgent",
        entity_id="agent.aggregator.demo",
        name="Community aggregator",
        agent_kind="aggregator",
        decision_rule="utility_maximisation",
        information_level="forecast",
        aggregation_strategy="self_consumption",
        price_sensitivity=0.90,
        self_sufficiency_target=0.70,
    )
    model.add_relation_if_allowed("agent.aggregator.demo", "managesCommunity", "community.demo", strict=True)
    model.add_relation_if_allowed("agent.aggregator.demo", "observesProfile", "profile.retail_tariff.demo")
    for asset_id in controlled_assets:
        model.add_relation_if_allowed("agent.aggregator.demo", "controlsAsset", asset_id)

    model.ensure_entity(
        class_name="AgentBasedModel",
        entity_id="abm.demo.prosumer_adoption",
        name="Prosumer adoption and self-consumption scenario",
        start_year=2025,
        end_year=2030,
        time_step="P1Y",
        random_seed=42,
        objective_description="Simulate PV and battery adoption in a local energy community.",
    )
    for agent_id in list(model.entities.get("ProsumerAgent", {}).keys()) + ["agent.aggregator.demo"]:
        model.add_relation_if_allowed("abm.demo.prosumer_adoption", "hasAgent", agent_id)
    for asset_id in controlled_assets:
        model.add_relation_if_allowed("abm.demo.prosumer_adoption", "simulatesAsset", asset_id)
    model.add_relation_if_allowed("abm.demo.prosumer_adoption", "usesProfile", "profile.retail_tariff.demo")
    model.add_relation_if_allowed("abm.demo.prosumer_adoption", "usesProfile", "profile.pv_subsidy.demo")

    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None, help="Optional existing CESDM YAML model")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "output" / "agent_based_prosumer_model.yaml")
    args = parser.parse_args()

    model = build_agent_based_prosumer_model(args.input)
    print(model.summary())
    print()

    errors = model.validate()
    if errors:
        print("Validation warnings/errors:")
        for err in errors[:30]:
            print(" -", err)
        raise SystemExit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.export_yaml_model(args.output.parent / "agent_based_model" / "yaml" / "agent_based_prosumer_model.yaml")
    print(f"Wrote {args.output}")
    print("Agents:", len(model.entities.get("ProsumerAgent", {})) + len(model.entities.get("AggregatorAgent", {})))
    print("Households:", len(model.entities.get("Household", {})))
    print("Controlled assets:", len(model.entities.get("DemandUnit", {})) + len(model.entities.get("GenerationUnit", {})) + len(model.entities.get("StorageUnit", {})))


    model.export_frictionless(str(args.output.parent / "agent_based_model" / "frictionless"), name="agent_based_prosumer_model")
    print(f"Exported agent_based_prosumer_model to {args.output.parent}")


if __name__ == "__main__":
    main()
