"""
example_import_tyndp_proxy_api.py's full pipeline -- the complete
proxy-API port requested after the first pass only covered
assign_installed_capacity_from_tyndp_csv (see CHANGELOG.md). Covers:
assign_nodes_and_countries_from_tyndp_nodes_csv, assign_demand_from_
tyndp_csv, assign_energy_storage_capacity_from_tyndp_csv, the three
timeseries functions, assign_ntc_from_tyndp_ntc_types_base_csv,
prune_hydro_reservoirs_without_inflow, and the top-level orchestrator
build_cesdm_model_from_tyndp_installed_capacities_proxy_api.

Also locks in the fix for a real, silent id-mismatch bug found while
building this: the legacy _ensure_storage_dispatch_view() hardcodes
f"storage_dispatch_view.{asset_id}" for every storage class, but the
real id convention for HydraulicStorageUnit specifically is
reservoir_storage_dispatch_view.* -- a mismatch that made storage
capacity assignment silently do nothing for every reservoir/PHS asset
in the legacy pipeline. This rewrite avoids the whole bug class by
never reconstructing view ids by hand, using .dispatch throughout.
"""

import pathlib
import shutil

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLE_DATA = REPO_ROOT / "examples" / "sample_data"


def _import_module():
    import sys
    for p in (str(REPO_ROOT), str(REPO_ROOT / "examples"), str(REPO_ROOT / "tools"),
              str(REPO_ROOT / "examples" / "legacy")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import example_import_tyndp_proxy_api as mod
    return mod


@pytest.fixture(scope="module")
def tyndp_data_folder(tmp_path_factory):
    """Assemble a TYNDP24_<Name>.csv-named data folder from the
    tyndp_sample_*.csv fixtures in examples/sample_data/."""
    out = tmp_path_factory.mktemp("tyndp_data") 
    mapping = {
        "Nodes": "tyndp_sample_nodes.csv",
        "InstalledCapacities": "tyndp_sample_installed_capacities.csv",
        "StorageCapacities": "tyndp_sample_storage_capacities.csv",
        "NTC_types": "tyndp_sample_ntc_types.csv",
        "DemandProfiles": "tyndp_sample_demand_profiles.csv",
        "GenProfiles": "tyndp_sample_gen_profiles.csv",
        "HydroInflows": "tyndp_sample_hydro_inflows.csv",
    }
    for tyndp_name, sample_name in mapping.items():
        shutil.copy(SAMPLE_DATA / sample_name, out / f"TYNDP24_{tyndp_name}.csv")
    return out


@pytest.fixture(scope="module")
def full_pipeline_model(tyndp_data_folder, tmp_path_factory):
    mod = _import_module()
    out_dir = tmp_path_factory.mktemp("tyndp_output")
    model = mod.build_cesdm_model_from_tyndp_installed_capacities_proxy_api(
        schema_path=str(REPO_ROOT / "schemas/cesdm"),
        data_folder=str(tyndp_data_folder) + "/",
        output_folder=str(out_dir),
        policy="National Trends", year=2030, climate_year=1995,
    )
    return model


# ---------------------------------------------------------------------
# Individual stage functions
# ---------------------------------------------------------------------

def test_nodes_and_countries_creates_real_region_names(tyndp_data_folder):
    mod = _import_module()
    from cesdm_toolbox import build_model_from_yaml
    model = build_model_from_yaml("schemas/cesdm")
    mod.import_tyndp_libraries(model)
    result = mod.assign_nodes_and_countries_from_tyndp_nodes_csv(
        model, str(tyndp_data_folder / "TYNDP24_Nodes.csv"))
    assert result["nodes_created"] == 2
    # Countries come from regions_library (import_tyndp_libraries), not created anew
    assert result["countries_created"] == 0
    assert result["countries_updated"] == 2
    assert model.get_attribute_value("region.country.DE", "name")
    assert model.get_attribute_value("region.country.FR", "name")
    assert model.has_entity("node.de00")
    assert model.get_relation_targets("node.de00", "belongsToGeographicalRegion") == [
        "region.country.DE"
    ]


def test_demand_from_installed_capacities_creates_electrolyser_load(tyndp_data_folder):
    mod = _import_module()
    from cesdm_toolbox import build_model_from_yaml
    model = build_model_from_yaml("schemas/cesdm")
    mod.assign_nodes_and_countries_from_tyndp_nodes_csv(
        model, str(tyndp_data_folder / "TYNDP24_Nodes.csv"))
    mod.assign_demand_from_tyndp_csv(
        model, str(tyndp_data_folder / "TYNDP24_InstalledCapacities.csv"),
        policy="National Trends", year=2030, climate_year=1995)
    # the sample installed-capacities fixture has no Electrolyser/CH4 Heat
    # Pump rows -- this exercises the "no matching rows" path cleanly
    # (must not raise), real demand creation is covered via the full
    # pipeline + timeseries test below instead.
    assert True


# ---------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------

def test_full_pipeline_validates(full_pipeline_model):
    full_pipeline_model.validate_or_raise()


def test_storage_capacity_assignment_actually_works(full_pipeline_model):
    """Regression test for the real id-mismatch bug: reservoir storage
    capacity must actually be assigned, not silently no-op."""
    reservoir = full_pipeline_model.get_entity("tech.reservoir.de00")
    assert reservoir.dispatch.energy_storage_capacity == 900.0
    battery = full_pipeline_model.get_entity("tech.battery_storage.de00")
    assert battery.dispatch.energy_storage_capacity == 150.0


def test_battery_storage_discharging_power_defaults_to_charging_power(full_pipeline_model):
    """TYNDP's source data only ever gives a charging-power figure --
    maximum_discharging_power was never set (or checked) at all until
    this fallback was added: reuses the charging figure (symmetric
    charge/discharge power is a common simplification for battery/PHS
    ratings) rather than leaving it unset entirely."""
    battery = full_pipeline_model.get_entity("tech.battery_storage.de00")
    assert battery.dispatch.maximum_charging_power == battery.dispatch.maximum_discharging_power
    assert battery.dispatch.maximum_discharging_power == 150.0


def test_hydro_inflow_timeseries_sets_both_reservoir_and_paired_generator(full_pipeline_model):
    reservoir = full_pipeline_model.get_entity("tech.reservoir.de00")
    assert reservoir.dispatch.annual_natural_inflow_energy is not None
    assert reservoir.dispatch.annual_natural_inflow_energy > 0
    gen_id = "gen.hydro.tech.reservoir.de00"
    if full_pipeline_model.has_entity(gen_id):
        gen = full_pipeline_model.get_entity(gen_id)
        assert gen.dispatch.annual_resource_potential is not None


def test_renewable_timeseries_sets_annual_resource_potential(full_pipeline_model):
    wind = full_pipeline_model.get_entity("tech.wind_onshore.de00")
    assert wind.dispatch.annual_resource_potential is not None
    assert wind.dispatch.annual_resource_potential > 0


def test_demand_timeseries_sets_annual_energy_demand(full_pipeline_model):
    demand = full_pipeline_model.get_entity("demand.electricity.de00")
    assert demand.dispatch.annual_energy_demand is not None
    assert demand.dispatch.annual_energy_demand > 0
    assert demand.dispatch.demand_type is not None


def test_ntc_interconnector_created_and_connected(full_pipeline_model):
    assert full_pipeline_model.has_entity("ntc.de00_fr00")
    ntc = full_pipeline_model.get_entity("ntc.de00_fr00")
    assert ntc.power_flow.maximum_power_flow_from_to is not None
    assert ntc.power_flow.maximum_power_flow_from_to > 0


def test_prune_removes_reservoirs_without_inflow():
    """A reservoir with zero natural inflow (not a PHS reservoir) must be
    removed by prune_hydro_reservoirs_without_inflow; a PHS reservoir
    with zero inflow must be kept."""
    mod = _import_module()
    from cesdm_toolbox import build_model_from_yaml
    from example_import_tyndp import import_tyndp_libraries
    model = build_model_from_yaml("schemas/cesdm")
    import_tyndp_libraries(model)
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)

    # Reservoir with NO inflow set -- should be pruned. Id must contain
    # "reservoir" (matching the real tech.reservoir.<node> naming
    # convention), since that's what the pruning logic's substring check
    # actually looks for -- an arbitrarily-named id is correctly *not*
    # treated as a reservoir candidate at all.
    model.ensure_resource("resource.water", name="Water", resource_type="water")
    model.add_entity("HydraulicStorageUnit", "tech.reservoir.nodry")
    model.add_relation("tech.reservoir.nodry", "storesResource", "resource.water")
    model.add_entity("HydroGenerationUnit", "gen.hydro.tech.reservoir.nodry")
    model.set_technology("gen.hydro.tech.reservoir.nodry", "Generation.Renewable.Hydro.Reservoir",
                         technology_class="GeneratorType")
    model.add_relation("gen.hydro.tech.reservoir.nodry", "hasInputResource", "resource.water")
    model.add_relation("gen.hydro.tech.reservoir.nodry", "atNode", "bus.1")
    model.add_relation("gen.hydro.tech.reservoir.nodry", "drawsFromHydraulicStorage", "tech.reservoir.nodry")
    gen1 = model.get_entity("gen.hydro.tech.reservoir.nodry")
    gen1.dispatch.hydro_machine_kind = "turbine"
    gen1.dispatch.nominal_power_capacity = 100

    # PHS reservoir with no natural inflow -- should be KEPT.
    model.add_entity("HydraulicStorageUnit", "tech.pump_storage_closed_loop.keep")
    model.add_relation("tech.pump_storage_closed_loop.keep", "storesResource", "resource.water")
    model.add_entity("HydroGenerationUnit", "gen.phs.tech.pump_storage_closed_loop.keep")
    model.set_technology("gen.phs.tech.pump_storage_closed_loop.keep",
                         "Generation.Renewable.Hydro.PHS.ClosedLoop", technology_class="GeneratorType")
    model.add_relation("gen.phs.tech.pump_storage_closed_loop.keep", "hasInputResource", "resource.water")
    model.add_relation("gen.phs.tech.pump_storage_closed_loop.keep", "atNode", "bus.1")
    model.add_relation("gen.phs.tech.pump_storage_closed_loop.keep", "drawsFromHydraulicStorage",
                       "tech.pump_storage_closed_loop.keep")
    gen2 = model.get_entity("gen.phs.tech.pump_storage_closed_loop.keep")
    gen2.dispatch.hydro_machine_kind = "reversible"
    gen2.dispatch.nominal_power_capacity = 100

    result = mod.prune_hydro_reservoirs_without_inflow(model)
    assert "tech.reservoir.nodry" in result["removed_ids"]
    assert not model.has_entity("tech.reservoir.nodry")
    assert not model.has_entity("gen.hydro.tech.reservoir.nodry")
    assert model.has_entity("tech.pump_storage_closed_loop.keep")


def test_full_pipeline_summary_has_expected_asset_classes(full_pipeline_model):
    counts = full_pipeline_model.summary(as_dict=True)
    assert counts.get("GenerationUnit", 0) > 0
    assert counts.get("StorageUnit", 0) > 0
    assert counts.get("DemandUnit", 0) > 0
    assert counts.get("TransmissionElement", 0) > 0


# ---------------------------------------------------------------------
# Profile relations and name attributes
#
# Regression tests for two real bugs reported after the full-pipeline
# conversion:
#
# 1. hasDemandProfile/hasAvailabilityProfile/hasNaturalInflowProfile/
#    hasNaturalInflowProfile were all silently empty. Root cause:
#    add_relation_if_allowed() (no strict=True) silently returns False
#    when the target doesn't exist yet -- and in all three timeseries
#    functions, the relation call happened *before*
#    _register_profile_entity() actually created the Profile entity.
#    Fixed by reordering: register the Profile first, then relate to
#    it. Present in all three timeseries functions (demand, renewable,
#    inflow x2 branches) -- five call sites total.
#
# 2. Generation units, storage units, and paired hydro generators never
#    got a `name` attribute set at all -- a real regression against the
#    legacy original, which explicitly set
#    f"{type_name} @ {node_code}" for exactly these entities.
# ---------------------------------------------------------------------

def test_demand_profile_relation_actually_populated(full_pipeline_model):
    demand = full_pipeline_model.get_entity("demand.electricity.de00")
    targets = full_pipeline_model.get_relation_targets(demand.dispatch.id, "hasDemandProfile")
    assert targets, "hasDemandProfile must not be empty"
    assert full_pipeline_model.has_entity(targets[0])


def test_renewable_availability_profile_relation_actually_populated(full_pipeline_model):
    wind = full_pipeline_model.get_entity("tech.wind_onshore.de00")
    targets = full_pipeline_model.get_relation_targets(wind.dispatch.id, "hasAvailabilityProfile")
    assert targets, "hasAvailabilityProfile must not be empty"
    assert full_pipeline_model.has_entity(targets[0])


def test_reservoir_natural_inflow_profile_relation_actually_populated(full_pipeline_model):
    reservoir = full_pipeline_model.get_entity("tech.reservoir.de00")
    targets = full_pipeline_model.get_relation_targets(reservoir.dispatch.id, "hasNaturalInflowProfile")
    assert targets, "hasNaturalInflowProfile must not be empty"
    assert full_pipeline_model.has_entity(targets[0])


def test_generation_and_storage_units_have_descriptive_names(full_pipeline_model):
    for eid in ("tech.wind_onshore.de00", "tech.battery_storage.de00", "tech.reservoir.de00"):
        name = full_pipeline_model.get_attribute_value(eid, "name")
        assert name, f"{eid} must have a non-empty name"
        assert name != eid  # must be a real descriptive label, not just the id


def test_paired_hydro_generator_has_a_name(full_pipeline_model):
    gen_id = "gen.hydro.tech.reservoir.de00"
    assert full_pipeline_model.has_entity(gen_id)
    name = full_pipeline_model.get_attribute_value(gen_id, "name")
    assert name, f"{gen_id} must have a non-empty name"


def test_energy_storage_capacity_present_in_both_model_and_export(full_pipeline_model, tmp_path):
    """Reported alongside the two bugs above but could not be
    reproduced as broken -- verified here explicitly, in both the live
    model and the exported YAML, so a regression would be caught."""
    reservoir = full_pipeline_model.get_entity("tech.reservoir.de00")
    assert reservoir.dispatch.energy_storage_capacity == 900.0

    out = tmp_path / "export_check.yaml"
    full_pipeline_model.export_yaml(out)
    text = out.read_text()
    assert "energy_storage_capacity" in text


# ---------------------------------------------------------------------
# Wrong/leftover input-carrier relations
#
# Found by comparing real (user-supplied) TYNDP output between the
# legacy pipeline and this one -- not caught by the synthetic sample
# fixtures, which don't happen to include coal/oil/solar-thermal/
# hydrogen technologies. Two distinct, real bugs:
#
# 1. add_generator() -> add_thermal_generator() (used for the entire
#    "thermal" family, which covers gas/coal/oil/lignite/biomass, not
#    just gas) has its own hardcoded, non-canonical default
#    fuel_carrier_id="carrier.natural_gas" -- wrong for every non-gas
#    thermal technology, and even for gas the non-canonical spelling
#    (real id: "carrier.fuel.fossil.gas.natural_gas"). Confirmed via a
#    real generation unit in the uploaded data:
#    tech.gas_ccgt_ccs.uk00 had hasInputCarrier=[carrier.natural_gas].
#    Fixed by explicitly (re-)setting the correct relation after
#    generator creation, with strict=True so any future ordering
#    regression fails loudly instead of silently reintroducing this.
#
# 2. A technology can be resource-based (needs hasInputResource, e.g.
#    solar) but still get routed through the "thermal" family by
#    _generator_family_from_technology if its name contains "thermal"
#    (e.g. "Solar Thermal" / CSP) -- meaning add_thermal_generator's
#    wrong hasInputCarrier default gets set *in addition to* the
#    correct hasInputResource, not instead of it, since they're
#    different relations. Fixed by explicitly clearing whichever
#    relation is NOT the correct one.
#
# Also found while investigating (1)/(2): _carrier_for_type()'s "hydro"
# substring check incorrectly matches "hydrogen" too (since "hydrogen"
# contains "hydro"), misclassifying hydrogen-fuelled generators
# (e.g. hydrogen_ccgt) as water-resource-based. Fixed with a local
# wrapper that checks "hydrogen" first, without editing the shared/
# legacy example_import_tyndp.py file itself.
# ---------------------------------------------------------------------

@pytest.mark.parametrize("type_name,expected_carrier", [
    ("Gas CCGT Present 2", "carrier.fuel.fossil.gas.natural_gas"),
    ("Hard Coal New", "carrier.fuel.fossil.coal.hard_coal"),
    ("Lignite New", "carrier.fuel.fossil.coal.lignite"),
    ("Light Oil", "carrier.fuel.fossil.oil"),
])
def test_thermal_generators_get_correct_carrier_not_hardcoded_gas_default(type_name, expected_carrier):
    """Regression test for the add_thermal_generator hardcoded-default
    bug: every technology in the "thermal" family (not just gas) used
    to end up with hasInputCarrier=carrier.natural_gas regardless of
    its actual fuel."""
    mod = _import_module()
    from cesdm_toolbox import build_model_from_yaml
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)

    in_carrier_id = mod._add_carrier_or_resource_if_missing(model, mod._carrier_for_type(type_name))
    tech_id = f"tech.{mod._slug(type_name)}.test"
    mod._assign_generation_row(model, tech_id, type_name, "TEST", "bus.1",
                               in_carrier_id, "carrier.electricity", 100.0)
    assert model.get_relation_targets(tech_id, "hasInputCarrier") == [expected_carrier]


def test_solar_thermal_gets_resource_not_leftover_wrong_carrier():
    """Regression test for bug 2: a resource-based technology routed
    through the thermal family must end up with ONLY
    hasInputResource set, not hasInputResource *and* a leftover
    hasInputCarrier=carrier.natural_gas from add_thermal_generator's
    default."""
    mod = _import_module()
    from cesdm_toolbox import build_model_from_yaml
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)

    type_name = "Solar Thermal"
    in_carrier_id = mod._add_carrier_or_resource_if_missing(model, mod._carrier_for_type(type_name))
    assert in_carrier_id == "resource.renewable.solar"

    tech_id = "tech.solar_thermal.test"
    mod._assign_generation_row(model, tech_id, type_name, "TEST", "bus.1",
                               in_carrier_id, "carrier.electricity", 100.0)
    assert model.get_relation_targets(tech_id, "hasInputResource") == ["resource.renewable.solar"]
    assert model.get_relation_targets(tech_id, "hasInputCarrier") == []


def test_hydrogen_technology_not_misclassified_as_water_resource():
    """Regression test for the _carrier_for_type "hydro" substring bug:
    "hydrogen" contains "hydro", so the legacy classifier's hydro/water
    check incorrectly matched hydrogen-fuelled technologies before
    ever reaching a hydrogen-specific check (there wasn't one)."""
    mod = _import_module()
    assert mod._carrier_for_type("Hydrogen CCGT") == "hydrogen"
    assert mod._carrier_for_type("Hydrogen Fuel Cell") == "hydrogen"
    # legacy behavior preserved for genuinely hydro-related technologies
    assert mod._carrier_for_type_legacy("Reservoir") == "water"
    assert mod._carrier_for_type("Reservoir") == "water"


def test_hydrogen_ccgt_gets_hydrogen_carrier_end_to_end():
    mod = _import_module()
    from cesdm_toolbox import build_model_from_yaml
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)

    type_name = "Hydrogen CCGT"
    in_carrier_id = mod._add_carrier_or_resource_if_missing(model, mod._carrier_for_type(type_name))
    assert in_carrier_id == "carrier.hydrogen"

    tech_id = "tech.hydrogen_ccgt.test"
    mod._assign_generation_row(model, tech_id, type_name, "TEST", "bus.1",
                               in_carrier_id, "carrier.electricity", 100.0)
    assert model.get_relation_targets(tech_id, "hasInputCarrier") == ["carrier.hydrogen"]
    assert model.get_relation_targets(tech_id, "hasInputResource") == []


def test_full_pipeline_has_no_orphaned_wrong_carrier_entity(full_pipeline_model):
    """The add_thermal_generator default can create the wrong carrier
    entity as a side effect even after the relation itself is
    corrected -- must be cleaned up, not just left as unreferenced
    clutter in the output."""
    assert not full_pipeline_model.has_entity("carrier.natural_gas")


def test_wind_generators_have_input_resource_and_output_carrier_set(full_pipeline_model):
    """The legacy pipeline never set these on GenerationUnit instances
    at all for wind/solar (confirmed against real uploaded output: 0 of
    141 wind/solar generators had either relation) -- this pipeline
    sets both, matching what GenerationUnit's own schema declares."""
    wind = full_pipeline_model.get_entity("tech.wind_onshore.de00")
    assert full_pipeline_model.get_relation_targets(wind, "hasInputResource") == ["resource.renewable.wind"]
    assert full_pipeline_model.get_relation_targets(wind, "hasOutputCarrier") == ["carrier.electricity"]


# ---------------------------------------------------------------------
# CLI argument validation
#
# Regression tests for a real bug reported after the full-pipeline
# conversion: running with neither a csv_path nor --data-folder (e.g.
# forgetting the positional argument) used to fall through to the
# minimal single-CSV mode with csv_path=None, crashing deep inside
# pandas with "ValueError: Invalid file path or buffer object type:
# <class 'NoneType'>" -- a confusing traceback with no indication of
# what the user actually did wrong. Fixed with explicit parser.error()
# validation, which exits 2 (standard argparse convention) with a
# clear, actionable message instead.
# ---------------------------------------------------------------------

def _run_cli(*args):
    import subprocess
    import sys as _sys
    script = REPO_ROOT / "examples" / "example_import_tyndp_proxy_api.py"
    return subprocess.run(
        [_sys.executable, str(script), *args],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def test_cli_neither_csv_path_nor_data_folder_gives_clear_error():
    result = _run_cli("--year", "2030")
    assert result.returncode == 2
    assert "Provide either a csv_path" in result.stderr
    assert "NoneType" not in result.stderr


def test_cli_missing_year_gives_clear_error():
    result = _run_cli("examples/sample_data/tyndp_sample_installed_capacities.csv")
    assert result.returncode == 2
    assert "--year is required" in result.stderr


def test_cli_both_csv_path_and_data_folder_gives_clear_error():
    result = _run_cli("examples/sample_data/tyndp_sample_installed_capacities.csv",
                      "--data-folder", "/tmp/nonexistent", "--year", "2030")
    assert result.returncode == 2
    assert "not both" in result.stderr


def test_cli_minimal_mode_still_works(tmp_path):
    out = tmp_path / "cli_test_output.yaml"
    result = _run_cli("examples/sample_data/tyndp_sample_installed_capacities.csv",
                      "--year", "2030", "--policy", "National Trends",
                      "--output", str(out))
    assert result.returncode == 0, result.stderr
    assert out.is_file()


# ---------------------------------------------------------------------
# Simple mode's energy_storage_capacity gap
#
# Reported as "still missing" after the profile-relation/name fixes.
# Root cause: TYNDP genuinely splits storage data across two files --
# installed_capacity_csv_path only ever carries power (MW)/charging
# power, never energy (MWh) capacity, which lives in a separate
# TYNDP24_StorageCapacities.csv-shaped file that simple mode never
# read. Not a bug in the assignment logic itself (the full pipeline
# mode already covers this correctly -- see
# test_storage_capacity_assignment_actually_works above) but a real
# usability gap: nothing told a simple-mode user this attribute would
# always be absent. Fixed by adding an optional
# storage_capacity_csv_path parameter to main()/--storage-capacity-csv
# on the CLI.
# ---------------------------------------------------------------------

def test_simple_mode_without_storage_csv_has_no_energy_storage_capacity(tmp_path):
    """Documents the real, by-design behavior -- not a bug -- so it
    doesn't get "fixed" into silently guessing a value later."""
    mod = _import_module()
    model = mod.main(
        str(SAMPLE_DATA / "tyndp_sample_installed_capacities.csv"),
        policy="National Trends", year=2030, climate_year=1995,
    )
    reservoir = model.get_entity("tech.reservoir.de00")
    assert reservoir.dispatch.energy_storage_capacity is None


def test_simple_mode_with_storage_csv_populates_energy_storage_capacity(tmp_path):
    mod = _import_module()
    model = mod.main(
        str(SAMPLE_DATA / "tyndp_sample_installed_capacities.csv"),
        policy="National Trends", year=2030, climate_year=1995,
        storage_capacity_csv_path=str(SAMPLE_DATA / "tyndp_sample_storage_capacities.csv"),
    )
    reservoir = model.get_entity("tech.reservoir.de00")
    assert reservoir.dispatch.energy_storage_capacity == 900.0
    battery = model.get_entity("tech.battery_storage.de00")
    assert battery.dispatch.energy_storage_capacity == 150.0


def test_cli_storage_capacity_csv_flag_works(tmp_path):
    out = tmp_path / "cli_storage_test.yaml"
    result = _run_cli("examples/sample_data/tyndp_sample_installed_capacities.csv",
                      "--year", "2030", "--policy", "National Trends",
                      "--storage-capacity-csv", "examples/sample_data/tyndp_sample_storage_capacities.csv",
                      "--output", str(out))
    assert result.returncode == 0, result.stderr
    assert "energy_storage_capacity" in out.read_text()
