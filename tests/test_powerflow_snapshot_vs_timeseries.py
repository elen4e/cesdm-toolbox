"""
A power-flow study is either a single-snapshot solve (the common
case — one fixed operating point, e.g. one pandapower runpp() call)
or a time-series ("quasi-steady-state") study across many operating
points. PowerFlowRunRecord.hasTimestampSeries (optional, unlike
DispatchRunRecord's required one) is the signal for which kind a
given run is; PowerFlowResult's snapshot attributes are always
the primary values, while average/min/max attributes and Profile
relations are only meaningful when hasTimestampSeries is set.

See docs/schema_layout.md ("Result views and RunRecord") and
CHANGELOG.md (0.3.0) for the full design rationale.
"""

from cesdm_toolbox import build_model_from_yaml


def test_powerflow_run_record_timestamp_series_is_optional():
    model = build_model_from_yaml("schemas/cesdm")
    _, rels = model._collect_inherited_fields(model.classes["PowerFlowRunRecord"])
    assert rels["hasTimestampSeries"].required is False

    # Contrast: DispatchRunRecord's is required — every dispatch run
    # covers a horizon by definition.
    _, dispatch_rels = model._collect_inherited_fields(model.classes["DispatchRunRecord"])
    assert dispatch_rels["hasTimestampSeries"].required is True


def test_single_snapshot_powerflow_result_validates_with_only_snapshot_attributes():
    model = build_model_from_yaml("schemas/cesdm")
    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_group="electricity")
    model.add_entity("CarrierDomain", "domain.electricity")
    model.add_relation("domain.electricity", "hasCarrier", "carrier.electricity")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_relation("bus.1", "belongsToCarrierDomain", "domain.electricity")
    model.add_entity("TransmissionLine", "line.1")
    model.add_entity("GenerationUnit", "gen.1")

    model.add_entity("PowerFlowRunRecord", "run.snapshot")
    model.add_attribute("run.snapshot", "converged", True)
    # deliberately no hasTimestampSeries — single-snapshot run

    model.add_entity("ElectricalBus.PowerFlowResult", "bus.1.pf")
    model.add_relation("bus.1.pf", "reportsOn", "bus.1")
    model.add_relation("bus.1.pf", "hasRunRecord", "run.snapshot")
    model.add_attribute("bus.1.pf", "voltage_magnitude", 1.02)
    model.add_attribute("bus.1.pf", "voltage_angle", -1.5)

    model.add_entity("TransmissionElement.PowerFlowResult", "line.1.pf")
    model.add_relation("line.1.pf", "reportsOn", "line.1")
    model.add_relation("line.1.pf", "hasRunRecord", "run.snapshot")
    model.add_attribute("line.1.pf", "active_power_flow_from", 10.0)
    model.add_attribute("line.1.pf", "active_power_loss", 0.2)
    model.add_attribute("line.1.pf", "loading_percent", 40.0)

    model.add_entity("GenerationUnit.PowerFlowResult", "gen.1.pf")
    model.add_relation("gen.1.pf", "reportsOn", "gen.1")
    model.add_relation("gen.1.pf", "hasRunRecord", "run.snapshot")
    model.add_attribute("gen.1.pf", "reactive_power_output", 5.0)

    model.validate_or_raise()  # must not raise despite no aggregates/Profile set

    assert model.get_relation_targets("run.snapshot", "hasTimestampSeries") == []


def test_time_series_powerflow_result_with_aggregates_and_profile(tmp_path):
    model = build_model_from_yaml("schemas/cesdm")
    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_group="electricity")
    model.add_entity("CarrierDomain", "domain.electricity")
    model.add_relation("domain.electricity", "hasCarrier", "carrier.electricity")
    model.add_entity("ElectricalBus", "bus.2")
    model.add_relation("bus.2", "belongsToCarrierDomain", "domain.electricity")
    model.add_entity("TimestampSeries", "ts.pf")
    model.add_attribute("ts.pf", "start_datetime", "2026-01-01T00:00:00")
    model.add_attribute("ts.pf", "resolution", "PT1H")
    model.add_attribute("ts.pf", "length", 24)

    model.add_entity("PowerFlowRunRecord", "run.qsts")
    model.add_relation("run.qsts", "hasTimestampSeries", "ts.pf")

    model.add_entity("Profile", "profile.bus2.vmag")
    model.add_relation("profile.bus2.vmag", "hasTimestampSeries", "ts.pf")
    model.add_attribute("profile.bus2.vmag", "profile_type", "as_SI")
    model.add_attribute("profile.bus2.vmag", "data_reference", "profiles/profile.bus2.vmag/values")

    model.add_entity("ElectricalBus.PowerFlowResult", "bus.2.pf")
    model.add_relation("bus.2.pf", "reportsOn", "bus.2")
    model.add_relation("bus.2.pf", "hasRunRecord", "run.qsts")
    model.add_attribute("bus.2.pf", "average_voltage_magnitude", 1.01)
    model.add_attribute("bus.2.pf", "min_voltage_magnitude", 0.97)
    model.add_attribute("bus.2.pf", "max_voltage_magnitude", 1.05)
    model.add_relation("bus.2.pf", "hasVoltageMagnitudeProfile", "profile.bus2.vmag")

    model.validate_or_raise()

    assert model.get_relation_targets("run.qsts", "hasTimestampSeries") == ["ts.pf"]
    assert model.get_relation_targets("bus.2.pf", "hasVoltageMagnitudeProfile") == ["profile.bus2.vmag"]
