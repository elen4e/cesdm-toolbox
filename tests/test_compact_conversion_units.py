from cesdm import build_model_from_yaml


def _carrier_domain_bus(m, carrier_id, domain_id, bus_class, bus_id, carrier_group=None):
    carrier = m.add_entity(entity_class="Carrier", entity_id=carrier_id)
    if carrier_group is not None:
        carrier.add_attribute(attribute_id="carrier_group", value=carrier_group)
    domain = m.add_entity(entity_class="CarrierDomain", entity_id=domain_id)
    domain.add_relation(relation_id="hasCarrier", target_entity_id=carrier.id)
    bus = m.add_entity(entity_class=bus_class, entity_id=bus_id)
    bus.add_relation(relation_id="belongsToCarrierDomain", target_entity_id=domain.id)
    return carrier, bus


def test_heat_pump_unit_schema_and_validation():
    m = build_model_from_yaml("schemas/cesdm")
    electricity, elec_bus = _carrier_domain_bus(
        m, "carrier.electricity.hp", "domain.electricity.hp", "ElectricalBus", "bus.electricity.hp",
        carrier_group="electricity",
    )
    heat, heat_bus = _carrier_domain_bus(
        m, "carrier.heat.hp", "domain.heat.hp", "HeatBus", "bus.heat.hp", carrier_group="heat",
    )
    hp = m.add_entity(entity_class="HeatPumpUnit", entity_id="hp.test")
    hp.add_attribute(attribute_id="coefficient_of_performance", value=3.5)
    hp.add_attribute(attribute_id="nominal_thermal_power_capacity", value=10, unit="MW")
    hp.add_relation(relation_id="hasInputCarrier", target_entity_id=electricity.id)
    hp.add_relation(relation_id="hasHeatOutputCarrier", target_entity_id=heat.id)
    hp.add_relation(relation_id="atElectricityNode", target_entity_id=elec_bus.id)
    hp.add_relation(relation_id="atHeatNode", target_entity_id=heat_bus.id)
    assert m.get_relation_targets(hp.id, "atElectricityNode") == [elec_bus.id]
    assert m.validate() == []


def test_electrolyser_unit_schema_and_validation():
    m = build_model_from_yaml("schemas/cesdm")
    electricity, elec_bus = _carrier_domain_bus(
        m, "carrier.electricity.el", "domain.electricity.el", "ElectricalBus", "bus.electricity.el",
        carrier_group="electricity",
    )
    hydrogen, h2_bus = _carrier_domain_bus(
        m, "carrier.hydrogen.el", "domain.hydrogen.el", "HydrogenBus", "bus.hydrogen.el",
        carrier_group="hydrogen",
    )
    el = m.add_entity(entity_class="ElectrolyserUnit", entity_id="el.test")
    el.add_attribute(attribute_id="energy_conversion_efficiency", value=0.7, unit="fraction")
    el.add_attribute(attribute_id="nominal_electrical_power_capacity", value=50, unit="MW")
    el.add_relation(relation_id="hasInputCarrier", target_entity_id=electricity.id)
    el.add_relation(relation_id="hasHydrogenOutputCarrier", target_entity_id=hydrogen.id)
    el.add_relation(relation_id="atElectricityNode", target_entity_id=elec_bus.id)
    el.add_relation(relation_id="atHydrogenNode", target_entity_id=h2_bus.id)
    assert m.get_relation_targets(el.id, "atHydrogenNode") == [h2_bus.id]
    assert m.validate() == []


def test_boiler_unit_schema_and_validation():
    m = build_model_from_yaml("schemas/cesdm")
    gas, gas_bus = _carrier_domain_bus(
        m, "carrier.gas.boiler", "domain.gas.boiler", "GasBus", "bus.gas.boiler", carrier_group="gas",
    )
    heat, heat_bus = _carrier_domain_bus(
        m, "carrier.heat.boiler", "domain.heat.boiler", "HeatBus", "bus.heat.boiler",
        carrier_group="heat",
    )
    boiler = m.add_entity(entity_class="BoilerUnit", entity_id="boiler.test")
    boiler.add_attribute(attribute_id="thermal_efficiency", value=0.9, unit="fraction")
    boiler.add_attribute(attribute_id="nominal_thermal_power_capacity", value=20, unit="MW")
    boiler.add_relation(relation_id="hasInputCarrier", target_entity_id=gas.id)
    boiler.add_relation(relation_id="hasHeatOutputCarrier", target_entity_id=heat.id)
    boiler.add_relation(relation_id="atFuelNode", target_entity_id=gas_bus.id)
    boiler.add_relation(relation_id="atHeatNode", target_entity_id=heat_bus.id)
    assert m.get_relation_targets(boiler.id, "atFuelNode") == [gas_bus.id]
    assert m.validate() == []


def test_fuel_cell_unit_schema_and_validation():
    m = build_model_from_yaml("schemas/cesdm")
    hydrogen, h2_bus = _carrier_domain_bus(
        m, "carrier.hydrogen.fc", "domain.hydrogen.fc", "HydrogenBus", "bus.hydrogen.fc",
        carrier_group="hydrogen",
    )
    electricity, elec_bus = _carrier_domain_bus(
        m, "carrier.electricity.fc", "domain.electricity.fc", "ElectricalBus", "bus.electricity.fc",
        carrier_group="electricity",
    )
    heat, heat_bus = _carrier_domain_bus(
        m, "carrier.heat.fc", "domain.heat.fc", "HeatBus", "bus.heat.fc", carrier_group="heat",
    )
    fc = m.add_entity(entity_class="FuelCellUnit", entity_id="fc.test")
    fc.add_attribute(attribute_id="electrical_efficiency", value=0.55, unit="fraction")
    fc.add_attribute(attribute_id="nominal_electrical_power_capacity", value=5, unit="MW")
    fc.add_attribute(attribute_id="nominal_thermal_power_capacity", value=2, unit="MW")
    fc.add_relation(relation_id="hasInputCarrier", target_entity_id=hydrogen.id)
    fc.add_relation(relation_id="hasElectricityOutputCarrier", target_entity_id=electricity.id)
    fc.add_relation(relation_id="hasHeatOutputCarrier", target_entity_id=heat.id)
    fc.add_relation(relation_id="atHydrogenNode", target_entity_id=h2_bus.id)
    fc.add_relation(relation_id="atElectricityNode", target_entity_id=elec_bus.id)
    fc.add_relation(relation_id="atHeatNode", target_entity_id=heat_bus.id)
    assert m.get_relation_targets(fc.id, "atHydrogenNode") == [h2_bus.id]
    assert m.validate() == []
