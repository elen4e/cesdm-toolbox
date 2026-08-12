"""
GenerationUnit used to carry every technology-specific physical/design
attribute directly -- wind (hub_height, rotor_diameter, installation_type,
number_of_turbines), solar (tilt_angle, azimuth_angle, tracking_type,
panel_technology), and thermal/nuclear (cooling_type, reactor_type,
thermal_capacity) all lived on the one shared base class, even though
they're mutually exclusive by technology (a wind turbine can't sensibly
have a reactor_type, etc.).

Following the existing HydroGenerationUnit precedent (a subclass created
for its reservoir-coupling relations), these technology-specific attributes
were moved to three new subclasses: WindGenerationUnit, SolarGenerationUnit,
ThermalGenerationUnit. Every generic dispatch/topology/power-flow/dynamics
attribute and relation continues to be inherited from GenerationUnit
unchanged.
"""
from cesdm_toolbox import build_model_from_yaml


def _model():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 20)
    return model


def test_wind_generation_unit_has_wind_specific_attributes():
    model = _model()
    model.add_entity("WindGenerationUnit", "wind.1")
    model.add_attribute("wind.1", "hub_height", 120.0)
    model.add_attribute("wind.1", "rotor_diameter", 150.0)
    model.add_attribute("wind.1", "installation_type", "offshore")
    model.add_attribute("wind.1", "number_of_turbines", 40)
    model.add_relation("wind.1", "atNode", "bus.1")

    gen = model.get_entity("wind.1")
    assert gen.hub_height == 120.0
    assert gen.rotor_diameter == 150.0


def test_solar_generation_unit_has_solar_specific_attributes():
    model = _model()
    model.add_entity("SolarGenerationUnit", "solar.1")
    model.add_attribute("solar.1", "tilt_angle", 30.0)
    model.add_attribute("solar.1", "azimuth_angle", 180.0)
    model.add_attribute("solar.1", "tracking_type", "fixed")
    model.add_attribute("solar.1", "panel_technology", "monocrystalline")
    model.add_relation("solar.1", "atNode", "bus.1")

    gen = model.get_entity("solar.1")
    assert gen.tilt_angle == 30.0
    assert gen.panel_technology == "monocrystalline"


def test_thermal_generation_unit_has_thermal_specific_attributes():
    model = _model()
    model.add_entity("ThermalGenerationUnit", "nuke.1")
    model.add_attribute("nuke.1", "reactor_type", "PWR")
    model.add_attribute("nuke.1", "cooling_type", "once_through")
    model.add_attribute("nuke.1", "thermal_capacity", 3000.0)
    model.add_relation("nuke.1", "atNode", "bus.1")

    gen = model.get_entity("nuke.1")
    assert gen.reactor_type == "PWR"
    assert gen.thermal_capacity == 3000.0


def test_generic_generation_unit_attributes_remain_on_the_base_class():
    """Every subclass must still inherit the generic, technology-agnostic
    attributes/relations directly from GenerationUnit unchanged."""
    model = _model()
    model.add_entity("WindGenerationUnit", "wind.1")
    model.add_attribute("wind.1", "nominal_power_capacity", 4.2)
    model.add_attribute("wind.1", "variable_operating_cost", 0.0)
    model.add_relation("wind.1", "atNode", "bus.1")

    gen = model.get_entity("wind.1")
    assert gen.dispatch.nominal_power_capacity == 4.2
    assert gen.atNode == "bus.1"


def test_technology_specific_attributes_are_not_cross_assignable():
    """A WindGenerationUnit must not accept a solar- or thermal-only
    attribute, and vice versa -- this is the whole point of splitting
    them into separate subclasses instead of leaving them all on
    GenerationUnit."""
    model = _model()
    model.add_entity("WindGenerationUnit", "wind.1")

    for foreign_attr, value in [
        ("reactor_type", "PWR"),           # thermal-only
        ("tilt_angle", 30.0),              # solar-only
        ("hydraulic_head", 100.0),         # hydro-only
    ]:
        try:
            model.add_attribute("wind.1", foreign_attr, value)
            assert False, f"{foreign_attr} should not be settable on WindGenerationUnit"
        except KeyError:
            pass


def test_generation_unit_base_class_no_longer_carries_technology_specific_attributes():
    """Regression pin: GenerationUnit itself must not regain any of the
    attributes that were moved out to the technology subclasses."""
    model = _model()
    class_attrs = set(model.class_attributes("GenerationUnit") or [])
    moved_out = {
        "hub_height", "rotor_diameter", "installation_type", "number_of_turbines",
        "tilt_angle", "azimuth_angle", "tracking_type", "panel_technology",
        "cooling_type", "reactor_type", "thermal_capacity",
        "hydro_machine_kind", "turbine_efficiency", "maximum_pumping_power", "pumping_efficiency",
        "minimum_up_time", "minimum_down_time", "hot_start_cost", "cold_start_cost",
    }
    assert not (class_attrs & moved_out), class_attrs & moved_out


def test_hydro_specific_dispatch_attributes_live_on_hydro_generation_unit():
    """hydro_machine_kind/turbine_efficiency/maximum_pumping_power/pumping_efficiency
    are hydro/PHS-specific by their own attribute descriptions -- they belong
    on HydroGenerationUnit, not on the shared GenerationUnit base class."""
    model = _model()
    model.add_entity("HydroGenerationUnit", "hydro.1")
    model.add_attribute("hydro.1", "hydro_machine_kind", "reversible")
    model.add_attribute("hydro.1", "turbine_efficiency", 0.9)
    model.add_attribute("hydro.1", "maximum_pumping_power", 420.0)
    model.add_attribute("hydro.1", "pumping_efficiency", 0.82)
    model.add_relation("hydro.1", "atNode", "bus.1")

    gen = model.get_entity("hydro.1")
    assert gen.dispatch.hydro_machine_kind == "reversible"
    assert gen.dispatch.maximum_pumping_power == 420.0

    # A plain GenerationUnit (e.g. a generic PyPSA-imported generator) must
    # not accept these -- they are meaningless outside the hydro context.
    model.add_entity("GenerationUnit", "gen.plain")
    try:
        model.add_attribute("gen.plain", "hydro_machine_kind", "turbine")
        assert False, "hydro_machine_kind should not be settable on plain GenerationUnit"
    except KeyError:
        pass


def test_unit_commitment_attributes_live_on_thermal_generation_unit():
    """hot_start_cost/cold_start_cost/minimum_up_time/minimum_down_time model
    a thermal unit's startup/shutdown dynamics -- not meaningful for wind,
    solar, or hydro, so they belong on ThermalGenerationUnit specifically."""
    model = _model()
    model.add_entity("ThermalGenerationUnit", "gas.1")
    model.add_attribute("gas.1", "hot_start_cost", 5000.0)
    model.add_attribute("gas.1", "cold_start_cost", 25000.0)
    model.add_attribute("gas.1", "minimum_up_time", 4.0)
    model.add_attribute("gas.1", "minimum_down_time", 2.0)
    model.add_relation("gas.1", "atNode", "bus.1")

    gen = model.get_entity("gas.1")
    assert gen.dispatch.hot_start_cost == 5000.0
    assert gen.dispatch.minimum_up_time == 4.0

    # Not meaningful on a wind turbine.
    model.add_entity("WindGenerationUnit", "wind.1")
    try:
        model.add_attribute("wind.1", "hot_start_cost", 5000.0)
        assert False, "hot_start_cost should not be settable on WindGenerationUnit"
    except KeyError:
        pass
