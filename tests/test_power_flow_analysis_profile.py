"""Tests for the new power_flow analysis profile, mirroring the style
of tests/test_analysis_validation.py. Every check here was verified
directly against a small, fully-specified test network -- confirmed
that it passes with zero errors -- and against deliberately incomplete
variants to confirm each individual check actually fires."""
from cesdm_toolbox import build_model_from_yaml


def _model_with_bus():
    model = build_model_from_yaml("schemas/cesdm")
    bus1 = model.add_entity("ElectricalBus", "bus.1")
    bus2 = model.add_entity("ElectricalBus", "bus.2")
    return model, bus1, bus2


def _fully_specified_network():
    model, bus1, bus2 = _model_with_bus()
    bus1.add_attribute(attribute_id="nominal_voltage", value=380, unit="kV")
    bus1.add_attribute(attribute_id="powerflow_bus_type", value="slack")
    bus1.add_attribute(attribute_id="voltage_magnitude_setpoint", value=1.0)
    bus2.add_attribute(attribute_id="nominal_voltage", value=380, unit="kV")
    bus2.add_attribute(attribute_id="powerflow_bus_type", value="PQ")

    gen = model.add_entity("GenerationUnit", "gen.1")
    gen.atNode = bus1
    gen.add_attribute(attribute_id="active_power_setpoint", value=100.0)

    dem = model.add_entity("DemandUnit", "dem.1")
    dem.atNode = bus2
    dem.add_attribute(attribute_id="active_power_demand", value=50.0)

    line = model.add_entity("TransmissionLine", "line.1")
    line.connect(bus1, bus2)
    line.add_attribute(attribute_id="series_resistance_per_km", value=0.01)
    line.add_attribute(attribute_id="series_reactance_per_km", value=0.1)
    line.add_attribute(attribute_id="line_length", value=10.0)
    return model


def test_fully_specified_network_passes_with_zero_errors():
    model = _fully_specified_network()
    errors = model.validate_for_analysis("power_flow")
    assert errors == []


def test_bus_requires_nominal_voltage_and_bus_type():
    model, bus1, _ = _model_with_bus()
    errors = model.validate_for_analysis("power_flow")
    assert any("bus.1" in e and "nominal_voltage" in e for e in errors)
    assert any("bus.1" in e and "powerflow_bus_type" in e for e in errors)


def test_bus_type_enum_is_enforced():
    model, bus1, _ = _model_with_bus()
    bus1.add_attribute(attribute_id="nominal_voltage", value=380, unit="kV")
    bus1.add_attribute(attribute_id="powerflow_bus_type", value="not_a_real_bus_type")

    errors = model.validate_for_analysis("power_flow")
    assert any("bus.1" in e and "powerflow_bus_type" in e for e in errors)


def test_generation_unit_requires_atnode_and_active_power_setpoint():
    model, bus1, _ = _model_with_bus()
    model.add_entity("GenerationUnit", "gen.bare")

    errors = model.validate_for_analysis("power_flow")
    assert any("gen.bare" in e and "atNode" in e for e in errors)
    assert any("gen.bare" in e and "active_power_setpoint" in e for e in errors)
    assert not any("powerflow_bus_type" in e and "gen.bare" in e for e in errors)


def test_demand_unit_requires_atnode_and_active_power_demand():
    model, bus1, _ = _model_with_bus()
    model.add_entity("DemandUnit", "dem.bare")

    errors = model.validate_for_analysis("power_flow")
    assert any("dem.bare" in e and "atNode" in e for e in errors)
    assert any("dem.bare" in e and "active_power_demand" in e for e in errors)


def test_transmission_line_requires_impedance_not_just_thermal_rating():
    """A power-flow calculation needs the line's own series impedance
    -- distinct from optimal_dispatch, which only needs
    thermal_capacity_rating and never checks impedance at all."""
    model, bus1, bus2 = _model_with_bus()
    line = model.add_entity("TransmissionLine", "line.bare")
    line.connect(bus1, bus2)

    errors = model.validate_for_analysis("power_flow")
    assert any("line.bare" in e and "series_resistance_per_km" in e for e in errors)
    assert any("line.bare" in e and "series_reactance_per_km" in e for e in errors)
    assert any("line.bare" in e and "line_length" in e for e in errors)
    assert not any("line.bare" in e and "thermal_capacity_rating" in e for e in errors)


def test_transformer_requires_rated_voltages_and_short_circuit_voltage():
    model, bus1, bus2 = _model_with_bus()
    trafo = model.add_entity("Transformer", "trafo.bare")
    trafo.connect(bus1, bus2)

    errors = model.validate_for_analysis("power_flow")
    assert any("trafo.bare" in e and "rated_primary_voltage" in e for e in errors)
    assert any("trafo.bare" in e and "rated_secondary_voltage" in e for e in errors)
    assert any("trafo.bare" in e and "short_circuit_voltage_in_percentage" in e for e in errors)


def test_interconnector_and_hvdclink_are_not_checked_for_impedance():
    """Interconnector/HVDCLink deliberately carry no detailed
    electrical parameters (see their own schema descriptions) -- the
    power_flow profile only requires topology (fromNode/toNode), not
    an impedance any AC solver would need. HVDCLink additionally
    requires ``max_flow`` when present in a power-flow study."""
    model, bus1, bus2 = _model_with_bus()
    ntc = model.add_entity("GenericInterconnector", "ntc.1")
    ntc.connect(bus1, bus2)
    hvdc = model.add_entity("HVDCLink", "hvdc.1")
    hvdc.connect(bus1, bus2)

    errors = model.validate_for_analysis("power_flow")
    assert not any("ntc.1" in e for e in errors)
    hvdc_errors = [e for e in errors if "hvdc.1" in e]
    assert any("max_flow" in e for e in hvdc_errors)
    assert not any("series_resistance" in e or "series_reactance" in e for e in hvdc_errors)

    hvdc.max_flow = 500.0
    errors_ok = model.validate_for_analysis("power_flow")
    assert not any("hvdc.1" in e for e in errors_ok)


def test_transmission_element_topology_required_for_every_subclass():
    model, _, _ = _model_with_bus()
    model.add_entity("TransmissionLine", "line.floating")
    model.add_entity("Transformer", "trafo.floating")
    model.add_entity("GenericInterconnector", "ntc.floating")
    model.add_entity("HVDCLink", "hvdc.floating")

    errors = model.validate_for_analysis("power_flow")
    for eid in ("line.floating", "trafo.floating", "ntc.floating", "hvdc.floating"):
        assert any(eid in e and "fromNode" in e for e in errors)
        assert any(eid in e and "toNode" in e for e in errors)
