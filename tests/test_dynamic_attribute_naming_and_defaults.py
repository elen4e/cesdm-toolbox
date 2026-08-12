"""
Two related decisions about the dynamic/controller attribute family:

1. Every dot-separated attribute id (`MACHINE.xd`, `AVR.SEXS.Ka`, ...)
   renamed to underscore-separated (`AVR_SEXS_Ka`, ...) -- 130
   attributes total. The family-prefix disambiguation for AVR/GOV/PSS
   (many controller models reuse the same short IEEE symbol -- Ka, Ta,
   T1) is unchanged, only the separator character is, so these now
   work as plain Python identifiers/kwargs directly without a caller
   having to `str.replace(".", "_")` first --
   `examples/example_kundur_two_area.py` used to do exactly that.

2. Unlike AVR/GOV/PSS, the dynamic machine model's own parameters were
   given full semantic snake_case names instead of keeping the terse
   IEEE symbol (`MACHINE_xd` -> `d_axis_synchronous_reactance`, etc.):
   requested directly, and there's no family-prefix collision risk to
   avoid here in the first place -- a machine has only one set of
   these parameters, unlike a generator's AVR/GOV/PSS, which can be
   one of several mutually exclusive model types each reusing the
   same short symbol.

Real IEEE Std 1110-2002 / IEEE Std 421.5-2016 / Kundur / PSS/E Model
Library typical reference default values exist for 113 of these
attributes (everything except plant-specific sizing -- rated MVA/kV,
MW power limits -- and discrete model-order fields). These defaults
apply automatically regardless of construction path -- but, for
`belongsToGroup`-tagged attributes specifically (like every dynamic
machine model attribute here), lazily on *read*
(`get_effective_attribute_value()`), not written unconditionally into
the entity's own data at creation time the way non-tagged attributes'
defaults are (`ear.model.entity_ops.add_entity()`). Writing them
unconditionally would activate that group's conditional-requiredness
on every single instance regardless of whether the group was ever
actually intended.

The dynamic machine model's attributes live on the standalone
`DynamicMachineModelType.Synchronous` entity, linked to a GenerationUnit
GenerationUnit itself, since the dynamic-model family (synchronous,
here) is an independent dimension from generation technology (a wind
turbine has no synchronous machine at all) -- see
docs/guide/05_attribute_groups.md.
"""

import pathlib

from cesdm_toolbox import build_model_from_yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_no_dotted_attribute_ids_remain_anywhere_in_the_schema():
    model = build_model_from_yaml("schemas/cesdm")
    dotted = [a for a in model.global_attributes if "." in a]
    assert dotted == []


def test_avr_gov_pss_attributes_are_underscore_separated():
    """AVR/GOV/PSS keep the terse, family-prefixed IEEE symbol
    convention -- multiple mutually exclusive model types per
    controller family reuse the same short symbol (Ka, Ta, T1, ...),
    so the family prefix is needed to disambiguate."""
    model = build_model_from_yaml("schemas/cesdm")
    for cls, prefix in [
        ("Controller.AVR.SEXS", "AVR_"),
        ("Controller.GOV.IEEEG1", "GOV_"),
        ("Controller.PSS.STAB1", "PSS_"),
    ]:
        attrs = model.class_attributes(cls)
        assert any(a.startswith(prefix) for a in attrs)
        assert not any("." in a for a in attrs)


def test_dynamic_machine_model_attributes_are_fully_semantic_not_prefixed():
    """Unlike AVR/GOV/PSS, the dynamic machine model has only one
    parameter set (no per-model-type family collision to disambiguate),
    so its attributes were given full semantic names instead of a
    terse MACHINE_ prefix -- e.g. d_axis_synchronous_reactance rather
    than MACHINE_xd."""
    model = build_model_from_yaml("schemas/cesdm")
    attrs = model.class_attributes("DynamicMachineModelType.Synchronous")
    assert "d_axis_synchronous_reactance" in attrs
    assert "inertia_constant" in attrs
    assert not any(a.startswith("MACHINE_") for a in attrs)
    assert not any("." in a for a in attrs)


def test_dynamic_view_gets_ieee_defaults_automatically_on_creation():
    """The dynamic machine model's attributes live on the standalone
    DynamicMachineModelType.Synchronous entity -- create one, read
    .dynamics without ever setting anything explicitly, and its IEEE
    defaults resolve lazily (not written into the entity's own data at
    creation time, unlike non-belongsToGroup attribute defaults -- see
    ear/model/entity_ops.py's add_entity())."""
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "gen.defaults.test")
    model.add_attribute("gen.defaults.test", "rated_apparent_power", 300.0)
    model.add_attribute("gen.defaults.test", "rated_voltage", 20.0)
    model.add_entity("DynamicMachineModelType.Synchronous", "dyn.defaults.test")
    dm = model.get_entity("dyn.defaults.test")
    dyn = dm.dynamics
    assert dyn.view_class == "dynamics"
    assert dyn.d_axis_synchronous_reactance == 1.8
    assert dyn.inertia_constant == 5.0
    assert dyn.damping_coefficient == 0.0
    assert dyn.d_axis_subtransient_reactance == 0.25
    assert "d_axis_synchronous_reactance" not in model.entity_data(str(dm))


def test_avr_gov_pss_get_ieee_defaults_automatically_too():
    """Controllers are separate entities now (not representation views),
    created directly and linked via controlsGenerationUnit -- but they
    still get their IEEE/PSS-E defaults automatically the same way any
    other entity with schema-level attribute defaults does."""
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "gen.defaults.test2")
    gen = "gen.defaults.test2"

    model.add_entity("Controller.AVR.SEXS", "avr.defaults.test2")
    model.add_relation("avr.defaults.test2", "controlsGenerationUnit", gen)
    avr = model.get_entity("avr.defaults.test2")
    assert avr.AVR_Efd_min == -6.0
    assert avr.AVR_Efd_max == 6.0
    assert avr.AVR_SEXS_Ka == 200.0

    model.add_entity("Controller.GOV.IEEEG1", "gov.defaults.test2")
    model.add_relation("gov.defaults.test2", "controlsGenerationUnit", gen)
    model.add_attribute("gov.defaults.test2", "GOV_Pmax", 1.0)
    gov = model.get_entity("gov.defaults.test2")
    assert gov.GOV_Pmin == 0.0

    model.add_entity("Controller.PSS.STAB1", "pss.defaults.test2")
    model.add_relation("pss.defaults.test2", "controlsGenerationUnit", gen)
    pss = model.get_entity("pss.defaults.test2")
    assert pss.PSS_Vs_max == 0.1
    assert pss.PSS_Vs_min == -0.1


def test_explicit_value_overrides_the_default():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "gen.defaults.override")
    model.add_attribute("gen.defaults.override", "rated_apparent_power", 300.0)
    model.add_attribute("gen.defaults.override", "rated_voltage", 20.0)
    model.add_entity("DynamicMachineModelType.Synchronous", "dyn.defaults.override")
    dm = model.get_entity("dyn.defaults.override")
    dyn = dm.dynamics
    assert dyn.d_axis_synchronous_reactance == 1.8  # default first
    dyn.d_axis_synchronous_reactance = 2.1
    assert dyn.d_axis_synchronous_reactance == 2.1  # explicit value wins
    assert dm.d_axis_synchronous_reactance == 2.1  # same storage, flat access


def test_generator_ratings_are_instance_specific_and_not_on_model_type():
    """Rated apparent power and voltage belong to the deployed generator,
    while normalized dynamic parameters belong to the reusable model type."""
    model = build_model_from_yaml("schemas/cesdm")
    generator_attrs = set(model.class_attributes("GenerationUnit") or [])
    type_attrs = set(model.class_attributes("DynamicMachineModelType.Synchronous") or [])
    for attr in ("rated_apparent_power", "rated_voltage"):
        assert attr in generator_attrs
        assert attr not in type_attrs
        assert model.global_attributes[attr]["value"].get("default") is None


def test_multiple_generators_can_share_one_dynamic_model_type():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("DynamicMachineModelType.Synchronous", "dyn.type.shared")
    for gid, rating in (("gen.shared.1", 300.0), ("gen.shared.2", 600.0)):
        model.add_entity("GenerationUnit", gid)
        model.add_attribute(gid, "rated_apparent_power", rating)
        model.add_attribute(gid, "rated_voltage", 20.0)
        model.add_relation(gid, "usesDynamicModelType", "dyn.type.shared")
    assert model.get_entity("gen.shared.1").usesDynamicModelType == "dyn.type.shared"
    assert model.get_entity("gen.shared.2").usesDynamicModelType == "dyn.type.shared"


def test_every_new_default_matches_the_declared_value_type():
    """Integer-typed attributes (PSS2A/PSS2B's M/N ramp-tracking
    orders) must have integer defaults, not float -- a real risk when
    hand-authoring 113 numbers."""
    model = build_model_from_yaml("schemas/cesdm")
    for attr in ("PSS_PSS2A_M", "PSS_PSS2A_N", "PSS_PSS2B_M", "PSS_PSS2B_N"):
        adef = model.global_attributes[attr]
        assert adef["value"]["type"] == "integer"
        assert isinstance(adef["value"]["default"], int)


def test_kundur_example_no_longer_needs_the_replace_dance():
    """example_kundur_two_area.py used to str.replace(".", "_") its
    parameter dict keys before passing them as **kwargs -- confirms
    that workaround is gone now that the ids are underscore-separated
    at the source."""
    text = (REPO_ROOT / "examples" / "example_kundur_two_area.py").read_text()
    assert 'replace(".", "_")' not in text


def test_wind_and_solar_generation_units_do_not_inherit_machine_dynamics():
    """The dynamic machine model's parameters live on the standalone
    DynamicMachineModelType.Synchronous
    entity, not on GenerationUnit -- so a WindGenerationUnit/
    SolarGenerationUnit (converter-interfaced, no synchronous machine)
    correctly has no dynamics group at all, rather than silently
    inheriting a physically meaningless synchronous-machine default."""
    model = build_model_from_yaml("schemas/cesdm")
    for cls in ("WindGenerationUnit", "SolarGenerationUnit"):
        model.add_entity(cls, f"gen.{cls}")
        gen = model.get_entity(f"gen.{cls}")
        try:
            gen.dynamics.d_axis_synchronous_reactance
            assert False, f"{cls} should not support the dynamics group at all"
        except AttributeError:
            pass


def test_generation_unit_base_class_no_longer_carries_machine_attributes():
    model = build_model_from_yaml("schemas/cesdm")
    class_attrs = set(model.class_attributes("GenerationUnit") or [])
    assert not any(a.startswith("MACHINE_") for a in class_attrs)
