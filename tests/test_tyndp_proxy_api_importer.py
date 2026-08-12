"""
example_import_tyndp_proxy_api.py: a second TYNDP importer built
entirely on the EntityProxy/ViewProxy API, reusing the original
example_import_tyndp.py's classification logic/constants for fidelity.
See that file's module docstring and docs/architecture/proxy_api.md
for scope.

Also covers the entity_ops._get_entity_and_class bug this importer's
own development surfaced: a nonexistent entity id used to silently
fall through to a stale for-loop variable, producing wildly misleading
"Unknown attribute/relation of <unrelated random class>" errors
instead of a clear "entity does not exist" error.
"""

import pathlib

import pytest

from cesdm_toolbox import build_model_from_yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLE_CSV = REPO_ROOT / "examples" / "sample_data" / "tyndp_sample_installed_capacities.csv"


def _import_module():
    import sys
    for p in (str(REPO_ROOT), str(REPO_ROOT / "examples"), str(REPO_ROOT / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import example_import_tyndp_proxy_api as mod
    return mod


# ---------------------------------------------------------------------
# The _get_entity_and_class bug, found while building this importer
# ---------------------------------------------------------------------

def test_nonexistent_entity_gives_clear_error_not_random_class():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("TransmissionLine", "some.line")  # populate entities dict
    with pytest.raises(KeyError, match="No entity with id 'nonexistent.entity' found"):
        model.add_attribute("nonexistent.entity", "name", "test")


def test_nonexistent_entity_relation_gives_clear_error():
    model = build_model_from_yaml("schemas/cesdm")
    with pytest.raises(KeyError, match="No entity with id"):
        model.add_relation("nonexistent.entity", "hasCarrier", "carrier.electricity")


# ---------------------------------------------------------------------
# Full pipeline, against the synthetic TYNDP-shaped fixture
# ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def imported_model():
    mod = _import_module()
    model = build_model_from_yaml(str(REPO_ROOT / "schemas/cesdm"))
    import pandas as pd
    df = pd.read_csv(SAMPLE_CSV)
    node_codes = sorted({str(n).strip()[:4] for n in df["Node"].dropna().unique()})
    mod._build_minimal_buses_for_demo(model, node_codes)
    mod.assign_installed_capacity_from_tyndp_csv_proxy_api(
        model, str(SAMPLE_CSV), policy="National Trends", year=2030, climate_year=1995,
    )
    return model


def test_full_pipeline_validates(imported_model):
    imported_model.validate_or_raise()


def test_thermal_generator_gets_techno_economic_defaults(imported_model):
    gas = imported_model.get_entity("tech.gas_ccgt_present_2.de00")
    assert gas.entity_class == "GenerationUnit"
    assert gas.dispatch.nominal_power_capacity == 800.0
    assert gas.dispatch.dispatch_type == "dispatchable"
    assert gas.dispatch.energy_conversion_efficiency == pytest.approx(0.58)


def test_nondispatchable_renewables_get_zero_cost_and_full_efficiency(imported_model):
    wind = imported_model.get_entity("tech.wind_onshore.de00")
    assert wind.dispatch.dispatch_type == "nondispatchable"
    assert wind.dispatch.variable_operating_cost == 0.0
    assert wind.dispatch.energy_conversion_efficiency == 1.0


def test_battery_storage_gets_both_power_directions(imported_model):
    battery = imported_model.get_entity("tech.battery_storage.de00")
    assert battery.entity_class == "StorageUnit"
    assert battery.dispatch.nominal_power_capacity == 150.0
    assert battery.dispatch.maximum_charging_power == 150.0
    # TYNDP's source data only ever gives a charging figure -- this test's
    # own name already promised "both power directions", but
    # maximum_discharging_power was never actually set (or asserted) at
    # all until this fallback was added: reuses the charging figure
    # (symmetric charge/discharge power is a common simplification for
    # battery/PHS ratings) rather than leaving it unset entirely.
    assert battery.dispatch.maximum_discharging_power == 150.0


def test_reservoir_hydro_composite_wired_correctly(imported_model):
    reservoir = imported_model.get_entity("tech.reservoir.de00")
    assert reservoir.entity_class == "HydraulicStorageUnit"
    gen_id = "gen.hydro.tech.reservoir.de00"
    assert imported_model.has_entity(gen_id)
    gen = imported_model.get_entity(gen_id)
    assert gen.entity_class == "HydroGenerationUnit"
    assert gen.dispatch.hydro_machine_kind == "turbine"  # not reversible -- plain reservoir
    assert gen.dispatch.nominal_power_capacity == 900.0
    assert imported_model.get_relation_targets(gen_id, "drawsFromHydraulicStorage") == ["tech.reservoir.de00"]
    assert imported_model.get_relation_targets("tech.reservoir.de00", "suppliesResourceTo") == []


def test_phs_closed_loop_composite_wired_correctly(imported_model):
    reservoir = imported_model.get_entity("tech.pump_storage_closed_loop.de00")
    assert reservoir.entity_class == "HydraulicStorageUnit"
    gen_id = "gen.hydro.tech.pump_storage_closed_loop.de00"
    gen = imported_model.get_entity(gen_id)
    assert gen.entity_class == "HydroGenerationUnit"
    assert gen.dispatch.hydro_machine_kind == "reversible"
    assert gen.dispatch.nominal_power_capacity == 500.0
    assert gen.dispatch.maximum_pumping_power == 480.0
    assert gen.dispatch.turbine_efficiency is not None
    assert gen.dispatch.pumping_efficiency is not None


def test_run_of_river_is_plain_hydro_generator_not_a_storage_composite(imported_model):
    ror = imported_model.get_entity("tech.run_of_river.fr00")
    assert ror.entity_class == "HydroGenerationUnit"
    assert not imported_model.has_entity("gen.hydro.tech.run_of_river.fr00")
    assert ror.dispatch.nominal_power_capacity == 600.0


def test_capacity_accumulates_across_repeated_imports():
    mod = _import_module()
    model = build_model_from_yaml(str(REPO_ROOT / "schemas/cesdm"))
    import pandas as pd
    df = pd.read_csv(SAMPLE_CSV)
    node_codes = sorted({str(n).strip()[:4] for n in df["Node"].dropna().unique()})
    mod._build_minimal_buses_for_demo(model, node_codes)

    mod.assign_installed_capacity_from_tyndp_csv_proxy_api(
        model, str(SAMPLE_CSV), policy="National Trends", year=2030, climate_year=1995)
    first = model.get_entity("tech.nuclear.de00").dispatch.nominal_power_capacity

    mod.assign_installed_capacity_from_tyndp_csv_proxy_api(
        model, str(SAMPLE_CSV), policy="National Trends", year=2030, climate_year=1995)
    second = model.get_entity("tech.nuclear.de00").dispatch.nominal_power_capacity

    assert second == first * 2
    model.validate_or_raise()
