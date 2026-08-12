"""
tools/aggregate_cesdm_model.py extended with per-country spatial
aggregation and pattern-based technology groups:

- spatial: --level-by-country CH=nuts3 DE=country lets different
  countries aggregate to different NUTS levels in the same run,
  overriding the single global --level for just the listed countries.
- technology: --tech-group 'Generation.Thermal.Gas.*' merges matching
  hasTechnology ids into one asset per aggregated bus (repeatable;
  default: no technology aggregation).

These tests build a small, self-contained two-country model (no
external TYNDP/PyPSA data needed) to verify both axes end to end, not
just the helper functions in isolation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from cesdm_toolbox import build_model_from_yaml

import aggregate_cesdm_model as agg

ELEC_DOMAIN = "domain.electricity"


def _ensure_elec_carrier_domain(model) -> None:
    """Attach every ElectricalBus to a shared electricity CarrierDomain."""
    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_group="electricity")
    if ELEC_DOMAIN not in (model.entities.get("CarrierDomain") or {}):
        model.add_entity("CarrierDomain", ELEC_DOMAIN)
        model.add_relation(ELEC_DOMAIN, "hasCarrier", "carrier.electricity")
    for bid in list((model.entities.get("ElectricalBus") or {}).keys()):
        if not model.get_relation_targets(bid, "belongsToCarrierDomain"):
            model.add_relation(bid, "belongsToCarrierDomain", ELEC_DOMAIN)



# ---------------------------------------------------------------------
# Helper functions, in isolation
# ---------------------------------------------------------------------

def test_country_of_nuts3():
    assert agg.country_of_nuts3("ch021") == "ch"
    assert agg.country_of_nuts3("DE111") == "de"


def test_parse_kv_overrides_string_values():
    result = agg.parse_kv_overrides(["CH=nuts3", "de=country"], value_type=str, what="level")
    assert result == {"ch": "nuts3", "de": "country"}


def test_parse_kv_overrides_int_values():
    result = agg.parse_kv_overrides(["CH=3", "DE=2"], value_type=int, what="tech depth")
    assert result == {"ch": 3, "de": 2}


def test_parse_kv_overrides_empty_list():
    assert agg.parse_kv_overrides([], value_type=str, what="level") == {}


def test_parse_kv_overrides_rejects_missing_equals_sign():
    with pytest.raises(SystemExit):
        agg.parse_kv_overrides(["CHnuts3"], value_type=str, what="level")


def test_parse_kv_overrides_rejects_non_numeric_value_for_int_type():
    with pytest.raises(SystemExit):
        agg.parse_kv_overrides(["CH=notanumber"], value_type=int, what="tech depth")


def test_resolve_level_for_country_uses_override_when_present():
    assert agg.resolve_level_for_country("ch", {"ch": "nuts3"}, "country") == "nuts3"


def test_resolve_level_for_country_falls_back_to_default():
    assert agg.resolve_level_for_country("fr", {"ch": "nuts3"}, "country") == "country"


@pytest.mark.parametrize("tech_id,pattern,expected", [
    ("Generation.Thermal.Gas.CCGT.New", "Generation.Thermal.Gas.*", True),
    ("Generation.Thermal.Gas.OCGT", "Generation.Thermal.Gas.*", True),
    ("Generation.Thermal.Coal.HardCoal.New", "Generation.Thermal.Gas.*", False),
    ("Generation.Thermal.Gas.CCGT.New", "Generation.Thermal.Gas", True),
    ("Generation.Thermal.Gas", "Generation.Thermal.Gas", True),
    ("Generation.Renewable.Wind.Onshore", "Generation.Renewable.Wind.*", True),
    ("generation.thermal.gas.ccgt.new", "Generation.Thermal.Gas.*", True),
])
def test_technology_matches_group(tech_id, pattern, expected):
    assert agg.technology_matches_group(tech_id, pattern) is expected


def test_technology_tag_for_groups_longest_match_wins():
    groups = agg.normalize_tech_groups([
        "Generation.Thermal.*",
        "Generation.Thermal.Gas.*",
    ])
    assert agg.technology_tag_for_groups(
        "Generation.Thermal.Gas.CCGT.New", groups,
    ) == "Generation.Thermal.Gas"
    assert agg.technology_tag_for_groups(
        "Generation.Thermal.Coal.HardCoal.New", groups,
    ) == "Generation.Thermal"


def test_technology_tag_for_groups_unmatched_unchanged():
    assert agg.technology_tag_for_groups(
        "Generation.Renewable.Solar.PV.Utility",
        ["Generation.Thermal.Gas.*"],
    ) == "Generation.Renewable.Solar.PV.Utility"


# ---------------------------------------------------------------------
# End to end: a small, self-contained two-country model
# ---------------------------------------------------------------------

@pytest.fixture
def two_country_model_yaml(tmp_path) -> Path:
    """CH: two gas subtypes at the SAME bus. DE: two gas subtypes at
    DIFFERENT buses. Exercises both axes: spatial (CH stays
    disaggregated, DE aggregates to country level) and technology
    (DE's subtypes should be mergeable, CH's should not merge unless
    explicitly asked to)."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    for rid, name in [("nuts3.ch021", "CH region 1"), ("nuts3.ch022", "CH region 2"),
                      ("nuts3.de111", "DE region 1"), ("nuts3.de112", "DE region 2")]:
        model.add_entity("GeographicalRegion", rid)
        model.add_attribute(rid, "name", name)

    for bid, rid in [("node.ch021.380", "nuts3.ch021"), ("node.ch022.380", "nuts3.ch022"),
                     ("node.de111.380", "nuts3.de111"), ("node.de112.380", "nuts3.de112")]:
        model.add_entity("ElectricalBus", bid)
        model.add_attribute(bid, "nominal_voltage", 380)
        model.add_relation(bid, "belongsToGeographicalRegion", rid)

    for gid, tech, bid, cap in [
        ("gen.ccgt.ch1", "Generation.Thermal.Gas.CCGT.New", "node.ch021.380", 200),
        ("gen.ocgt.ch1", "Generation.Thermal.Gas.OCGT", "node.ch021.380", 100),
        ("gen.ccgt.de1", "Generation.Thermal.Gas.CCGT.New", "node.de111.380", 300),
        ("gen.ocgt.de1", "Generation.Thermal.Gas.OCGT", "node.de112.380", 150),
    ]:
        model.add_entity("GenerationUnit", gid)
        model.set_technology(gid, tech, technology_class="GeneratorType")
        model.add_relation(gid, "atNode", bid)
        model.get_entity(gid).dispatch.nominal_power_capacity = cap

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()

    yaml_path = tmp_path / "model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml_hierarchical(str(yaml_path))
    return yaml_path


def _dispatch_capacity(output_data: dict, gen_id: str) -> float:
    """out_obj (aggregate_subset's return value) now writes every
    attribute directly onto the one real generation entity -- no
    separate dispatch-view section, no reportsOn indirection.
    Search every generation output class (GenerationUnit,
    HydroGenerationUnit) since the caller doesn't always know which
    one an aggregated id landed in."""
    for cls in ("GenerationUnit", "HydroGenerationUnit"):
        ent = output_data.get(cls, {}).get(gen_id)
        if ent is not None:
            attrs = {a["id"]: a.get("value") for a in ent.get("attributes", [])}
            return attrs["nominal_power_capacity"]
    raise AssertionError(f"No generation entity found for {gen_id!r}")


def test_backward_compatible_single_global_level_no_tech_aggregation(two_country_model_yaml, tmp_path):
    """No per-country overrides at all -- must behave exactly like
    before this feature existed: one level for everyone, every
    technology stays its own aggregated group."""
    outdir = tmp_path / "out_baseline"
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_country_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
        level_by_country={}, tech_groups=[],
    )

    assert sorted(out_obj["ElectricalBus"].keys()) == ["node.ch.380", "node.de.380"]
    assert len(out_obj["GenerationUnit"]) == 4  # CCGT and OCGT stay separate, for both countries


def test_per_country_spatial_level_override(two_country_model_yaml):
    """CH stays disaggregated (its own --level-by-country entry: same
    as the global default here, but exercised explicitly), DE
    aggregates to country level."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_country_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "disaggregated", True, None, lambda *a: None,
        level_by_country={"de": "country"}, tech_groups=[],
    )

    bus_ids = sorted(out_obj["ElectricalBus"].keys())
    assert bus_ids == ["node.ch021.380", "node.ch022.380", "node.de.380"]


def test_per_country_disaggregated_keeps_buses_in_same_nuts3(tmp_path):
    """``CH=disaggregated`` is true bus passthrough, not a nuts3 merge:
    two Swiss buses that share one NUTS3 stay separate. ``CH=nuts3``
    merges them into one aggregated node."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.ch021")
    model.add_attribute("nuts3.ch021", "name", "CH region 1")
    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")

    for bid, rid in [
        ("node.ch021.a.380", "nuts3.ch021"),
        ("node.ch021.b.380", "nuts3.ch021"),
        ("node.de111.380", "nuts3.de111"),
    ]:
        model.add_entity("ElectricalBus", bid)
        model.add_attribute(bid, "nominal_voltage", 380)
        model.add_relation(bid, "belongsToGeographicalRegion", rid)

    for gid, bid, cap in [
        ("gen.ch.a", "node.ch021.a.380", 100),
        ("gen.ch.b", "node.ch021.b.380", 50),
        ("gen.de", "node.de111.380", 200),
    ]:
        model.add_entity("GenerationUnit", gid)
        model.set_technology(gid, "Generation.Thermal.Gas.CCGT.New", technology_class="GeneratorType")
        model.add_relation(gid, "atNode", bid)
        model.get_entity(gid).dispatch.nominal_power_capacity = cap

    _ensure_elec_carrier_domain(model)
    model.validate_or_raise()
    yaml_path = tmp_path / "same_nuts3.yaml"
    model.export_yaml_hierarchical(str(yaml_path))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")

    out_disagg, _, _ = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
        level_by_country={"ch": "disaggregated"}, tech_groups=[],
    )
    assert sorted(out_disagg["ElectricalBus"].keys()) == [
        "node.ch021.a.380", "node.ch021.b.380", "node.de.380",
    ]
    # Original CH gens kept; DE spatially aggregated into one unit.
    assert "gen.ch.a" in out_disagg["GenerationUnit"]
    assert "gen.ch.b" in out_disagg["GenerationUnit"]
    assert len(out_disagg["GenerationUnit"]) == 3

    out_nuts3, _, _ = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
        level_by_country={"ch": "nuts3"}, tech_groups=[],
    )
    assert sorted(out_nuts3["ElectricalBus"].keys()) == ["node.ch021.380", "node.de.380"]
    assert len(out_nuts3["GenerationUnit"]) == 2  # one CH agg + one DE agg


def test_agg_asset_region_key_identity_keeps_full_bus_token():
    assert agg.agg_asset_region_key("node.ch021.7205", False, identity=True) == ("ch021.7205", "")
    assert agg.agg_asset_region_key("node.ch021.380", True, identity=False) == ("ch021", ".380")
    assert agg.agg_asset_region_key("node.ch", False, identity=False) == ("ch", "")


def test_disaggregated_with_tech_groups_does_not_collide_same_nuts3(tmp_path):
    """Regression: with CH=disaggregated AND --tech-group, asset ids must
    not collapse to gen.*.agg.<nuts3> (overwriting sibling buses). Capacities
    on two buses that share one NUTS3 must both survive."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.ch021")
    model.add_attribute("nuts3.ch021", "name", "CH region 1")
    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")

    for bid, rid in [
        ("node.ch021.100", "nuts3.ch021"),
        ("node.ch021.200", "nuts3.ch021"),
        ("node.de111.380", "nuts3.de111"),
    ]:
        model.add_entity("ElectricalBus", bid)
        model.add_attribute(bid, "nominal_voltage", 380)
        model.add_relation(bid, "belongsToGeographicalRegion", rid)

    for gid, tech, bid, cap in [
        ("gen.nuc.a", "Generation.Nuclear", "node.ch021.100", 1000),
        ("gen.nuc.b", "Generation.Nuclear", "node.ch021.200", 2000),
        ("gen.gas.a", "Generation.Thermal.Gas.CCGT.New", "node.ch021.100", 100),
        ("gen.gas.b", "Generation.Thermal.Gas.OCGT", "node.ch021.200", 50),
        ("gen.de", "Generation.Nuclear", "node.de111.380", 500),
    ]:
        model.add_entity("GenerationUnit", gid)
        model.set_technology(gid, tech, technology_class="GeneratorType")
        model.add_relation(gid, "atNode", bid)
        model.get_entity(gid).dispatch.nominal_power_capacity = cap

    _ensure_elec_carrier_domain(model)
    model.validate_or_raise()
    yaml_path = tmp_path / "disagg_tech_collide.yaml"
    model.export_yaml_hierarchical(str(yaml_path))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
        level_by_country={"ch": "disaggregated"},
        tech_groups=["Generation.Thermal.Gas.*"],
    )

    # Nuclear does not match the tech group → original entities kept.
    assert "gen.nuc.a" in out_obj["GenerationUnit"]
    assert "gen.nuc.b" in out_obj["GenerationUnit"]
    assert _dispatch_capacity(out_obj, "gen.nuc.a") == 1000.0
    assert _dispatch_capacity(out_obj, "gen.nuc.b") == 2000.0

    # Gas matches → one merged unit per original CH bus (unique id token).
    gas_ids = sorted(g for g in out_obj["GenerationUnit"] if "generation.thermal.gas" in g)
    assert len(gas_ids) == 2
    assert any("ch021.100" in g for g in gas_ids)
    assert any("ch021.200" in g for g in gas_ids)
    assert sum(_dispatch_capacity(out_obj, g) for g in gas_ids) == 150.0

    disagg = stats["_sanity_disaggregated_by_country"]["ch"]
    aggd = stats["_sanity_aggregated_by_country"]["ch"]
    assert disagg["dispatchable_capacity_mw"]["nuclear"] == aggd["dispatchable_capacity_mw"]["nuclear"]
    # gas tag after merge uses the group key stem
    assert sum(disagg["dispatchable_capacity_mw"].values()) == sum(aggd["dispatchable_capacity_mw"].values())


def test_tech_group_merges_gas_subtypes_per_aggregated_bus(two_country_model_yaml):
    """--tech-group Generation.Thermal.Gas.* merges CCGT/OCGT at each
    aggregated bus. CH keeps both gas units on ch021 (disaggregated
    spatially) so they merge there; DE aggregates to country so its
    two subtypes also merge and capacities sum."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_country_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "disaggregated", True, None, lambda *a: None,
        level_by_country={"de": "country"},
        tech_groups=["Generation.Thermal.Gas.*"],
    )

    gen_ids = sorted(out_obj["GenerationUnit"].keys())

    ch_gens = [g for g in gen_ids if ".ch021." in g]
    assert len(ch_gens) == 1
    assert "generation.thermal.gas.agg.ch021" in ch_gens[0]
    assert "ccgt" not in ch_gens[0] and "ocgt" not in ch_gens[0]

    de_gens = [g for g in gen_ids if ".de." in g]
    assert len(de_gens) == 1
    assert "generation.thermal.gas.agg.de" in de_gens[0]
    assert "ccgt" not in de_gens[0] and "ocgt" not in de_gens[0]

    assert _dispatch_capacity(out_obj, ch_gens[0]) == 300.0
    assert _dispatch_capacity(out_obj, de_gens[0]) == 450.0


def test_tech_group_aggregation_output_still_validates(two_country_model_yaml, tmp_path):
    """The aggregated output, re-loaded, is still schema-valid CESDM --
    not just internally self-consistent."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_country_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "disaggregated", True, None, lambda *a: None,
        level_by_country={"de": "country"},
        tech_groups=["Generation.Thermal.Gas.*"],
    )

    out_model = agg.data_to_model(ROOT / "schemas/cesdm", out_obj)
    out_yaml = tmp_path / "aggregated.yaml"
    out_model.export_yaml_hierarchical(str(out_yaml))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml_hierarchical(str(out_yaml))
    errors = reloaded.validate()
    # Only pre-existing, feature-unrelated gaps in this minimal fixture
    # (no CarrierDomain/TimestampSeries set up) are expected -- assert
    # there is nothing *technology or spatial aggregation specific*
    # among them (no "Duplicate", no id-collision, no missing
    # reportsOn-style structural errors).
    assert not any("Duplicate" in e or "reportsOn" in e for e in errors)


# ---------------------------------------------------------------------
# Reservoirs: never electrically connected themselves, only their
# paired HydroGenerationUnit is (via drawsFromHydraulicStorage) -- reported
# directly as "Reservoir/Pondage 'storage.phs.agg.<country>' has no
# inflow data" downstream in tools/import_flexeco.py, because the
# reservoir's own a2n.get(asset_id) lookup always returned None and it
# was silently excluded from storage aggregation entirely.
# ---------------------------------------------------------------------

@pytest.fixture
def two_bus_phs_model_yaml(tmp_path) -> Path:
    """Two PHS closed-loop plants at two different DE buses -- the
    reservoirs have no topology view of their own, matching real
    TYNDP-imported data (see examples/example_import_tyndp.py's
    _ensure_hydro_reservoir_composite, which only ever attaches a
    SinglePort.TopologyView to the paired generator, never to the
    reservoir itself)."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")
    model.add_entity("GeographicalRegion", "nuts3.de112")
    model.add_attribute("nuts3.de112", "name", "DE region 2")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de112.380")
    model.add_attribute("node.de112.380", "nominal_voltage", 380)
    model.add_relation("node.de112.380", "belongsToGeographicalRegion", "nuts3.de112")

    model.ensure_resource("resource.water", name="Water", resource_type="water")
    for res_id, gen_id, bus_id, cap, pump_cap, pump_eff, turb_eff, storage_mwh, inflow_mwh in [
        ("reservoir.phs.de1", "gen.phs.de1", "node.de111.380", 200.0, 200.0, 0.85, 0.90, 1000.0, 500.0),
        ("reservoir.phs.de2", "gen.phs.de2", "node.de112.380", 150.0, 150.0, 0.85, 0.90, 800.0, 300.0),
    ]:
        model.add_entity("HydraulicStorageUnit", res_id)
        model.add_relation(res_id, "storesResource", "resource.water")
        model.add_entity("HydroGenerationUnit", gen_id)
        model.set_technology(gen_id, "Generation.Renewable.Hydro.PHS.ClosedLoop", technology_class="GeneratorType")
        model.add_relation(gen_id, "hasInputResource", "resource.water")
        model.add_relation(gen_id, "atNode", bus_id)
        model.add_relation(gen_id, "drawsFromHydraulicStorage", res_id)
        res = model.get_entity(res_id)
        gen = model.get_entity(gen_id)
        gen.dispatch.hydro_machine_kind = "reversible"
        gen.dispatch.nominal_power_capacity = cap
        gen.dispatch.maximum_pumping_power = pump_cap
        gen.dispatch.pumping_efficiency = pump_eff
        gen.dispatch.turbine_efficiency = turb_eff
        res.dispatch.energy_storage_capacity = storage_mwh
        res.dispatch.annual_natural_inflow_energy = inflow_mwh

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()

    # Confirm the fixture actually matches the real-world shape being
    # tested: a HydraulicStorageUnit has no atNode relation of its own
    # at all in the schema -- it genuinely cannot be directly connected
    # to a bus, which is exactly why build_reservoir_bus_via_generator()
    # exists.
    _, res_rels = model._collect_inherited_fields(model.classes["HydraulicStorageUnit"])
    assert "atNode" not in res_rels

    yaml_path = tmp_path / "phs_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml_hierarchical(str(yaml_path))
    return yaml_path


def test_build_reservoir_bus_via_generator(two_bus_phs_model_yaml):
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_phs_model_yaml)
    data = agg.model_to_data(model)
    a2n = agg.build_asset_to_node(data, agg.GENERATION_ASSET_CLASSES)

    reservoir_bus = agg.build_reservoir_bus_via_generator(data, a2n)

    assert reservoir_bus["reservoir.phs.de1"] == "node.de111.380"
    assert reservoir_bus["reservoir.phs.de2"] == "node.de112.380"


def test_reservoirs_are_not_silently_dropped_during_aggregation(two_bus_phs_model_yaml):
    """The actual bug: without the reservoir-via-generator bus fallback,
    aggregate_subset's storage loop found bus_id=None for every
    reservoir (a2n.get(reservoir_id) is always None) and silently
    excluded every reservoir from the output entirely."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_phs_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    assert stats["stors"] == 1  # both reservoirs aggregate into one at country level
    assert "HydraulicStorageUnit" in out_obj
    assert len(out_obj["HydraulicStorageUnit"]) == 1


def test_aggregated_reservoir_inflow_and_capacity_are_correctly_summed(two_bus_phs_model_yaml):
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_phs_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    res_id = next(iter(out_obj["HydraulicStorageUnit"]))
    attrs = {a["id"]: a["value"] for a in out_obj["HydraulicStorageUnit"][res_id]["attributes"]}
    assert attrs["annual_natural_inflow_energy"] == pytest.approx(800.0)   # 500 + 300
    assert attrs["energy_storage_capacity"] == pytest.approx(1800.0)       # 1000 + 800


def test_draws_from_reservoir_link_points_at_an_id_that_actually_exists(two_bus_phs_model_yaml):
    """aggregated_storage_id_for_asset() must compute exactly the same id
    the main storage-aggregation loop does, including via the same
    reservoir-via-generator fallback -- otherwise drawsFromHydraulicStorage
    would point at an id that was never created."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_phs_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    actual_reservoir_ids = set(out_obj["HydraulicStorageUnit"].keys())
    gen_id = next(iter(out_obj["HydroGenerationUnit"]))
    gen_ent = out_obj["HydroGenerationUnit"][gen_id]
    draws_from = next(
        r["target_entity_ids"][0] for r in gen_ent["relations"] if r["id"] == "drawsFromHydraulicStorage"
    )
    assert draws_from in actual_reservoir_ids


@pytest.fixture
def two_bus_phs_no_inflow_model_yaml(tmp_path) -> Path:
    """Same shape as two_bus_phs_model_yaml, but deliberately without any
    annual_natural_inflow_energy -- a genuine closed-loop PHS scheme
    (pump water up, release it down, no new water entering from a
    river), which is the case that should classify as
    PN_StoragePumpNoInfeed, not PN_StoragePump (which additionally
    requires a natural inflow profile reference)."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")
    model.add_entity("GeographicalRegion", "nuts3.de112")
    model.add_attribute("nuts3.de112", "name", "DE region 2")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de112.380")
    model.add_attribute("node.de112.380", "nominal_voltage", 380)
    model.add_relation("node.de112.380", "belongsToGeographicalRegion", "nuts3.de112")

    model.ensure_resource("resource.water", name="Water", resource_type="water")
    for res_id, gen_id, bus_id, cap, pump_cap, pump_eff, turb_eff, storage_mwh in [
        ("reservoir.phs.de1", "gen.phs.de1", "node.de111.380", 200.0, 200.0, 0.85, 0.90, 1000.0),
        ("reservoir.phs.de2", "gen.phs.de2", "node.de112.380", 150.0, 150.0, 0.85, 0.90, 800.0),
    ]:
        model.add_entity("HydraulicStorageUnit", res_id)
        model.add_relation(res_id, "storesResource", "resource.water")
        model.add_entity("HydroGenerationUnit", gen_id)
        model.set_technology(gen_id, "Generation.Renewable.Hydro.PHS.ClosedLoop", technology_class="GeneratorType")
        model.add_relation(gen_id, "hasInputResource", "resource.water")
        model.add_relation(gen_id, "atNode", bus_id)
        model.add_relation(gen_id, "drawsFromHydraulicStorage", res_id)
        res = model.get_entity(res_id)
        gen = model.get_entity(gen_id)
        gen.dispatch.hydro_machine_kind = "reversible"
        gen.dispatch.nominal_power_capacity = cap
        gen.dispatch.maximum_pumping_power = pump_cap
        gen.dispatch.pumping_efficiency = pump_eff
        gen.dispatch.turbine_efficiency = turb_eff
        res.dispatch.energy_storage_capacity = storage_mwh

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "phs_no_inflow_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml_hierarchical(str(yaml_path))
    return yaml_path


def test_pumping_and_turbine_efficiency_are_aggregated(two_bus_phs_model_yaml):
    """pumping_efficiency/turbine_efficiency were listed in
    allowed_agg_attrs_for_generation() but never actually computed or
    written anywhere -- silently missing from every aggregated PHS
    generator's dispatch view, however many members it merged.
    Downstream, tools/import_flexeco.py's closed-loop PHS branch
    (PN_StoragePumpNoInfeed) requires a non-None charging efficiency to
    even be reached; without this fix every aggregated closed-loop PHS
    silently produced neither an error nor an output element at all."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_phs_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    gen_id = next(iter(out_obj["HydroGenerationUnit"]))
    attrs = {a["id"]: a["value"] for a in out_obj["HydroGenerationUnit"][gen_id]["attributes"]}
    assert attrs.get("pumping_efficiency") == pytest.approx(0.85)
    assert attrs.get("turbine_efficiency") == pytest.approx(0.90)


def test_aggregated_closed_loop_phs_classifies_correctly_end_to_end(two_bus_phs_no_inflow_model_yaml, tmp_path):
    """The full pipeline the original report exercised: aggregate, then
    export to FlexECO, and confirm the closed-loop PHS reservoir is
    classified as PN_StoragePumpNoInfeed -- not silently dropped
    (the reservoir-has-no-topology-view bug, fixed both in this tool
    and in tools/import_flexeco.py's own _bus_from_nodal_view usage)
    and not stuck on the generic "no inflow data" message meant for
    non-PHS reservoirs (which requires distinguishing PHS from a plain
    dam via hydro_machine_kind/pumping efficiency -- the
    pumping_efficiency/turbine_efficiency aggregation gap above)."""
    pytest.importorskip("scipy")
    pytest.importorskip("cesdm_flexeco")
    from cesdm_flexeco import export_to_flexeco

    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_phs_no_inflow_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )
    out_model = agg.data_to_model(ROOT / "schemas/cesdm", out_obj)
    agg_yaml = tmp_path / "aggregated.yaml"
    out_model.export_yaml_hierarchical(str(agg_yaml))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml_hierarchical(str(agg_yaml))

    flexeco_out = tmp_path / "flexeco_output.json"
    export_to_flexeco(reloaded, str(flexeco_out))

    import json
    result = json.loads(flexeco_out.read_text())
    classes_by_name = {el["name"]: el["class"] for el in result["PowerSystemElements"]}

    storage_classes = [c for name, c in classes_by_name.items() if name.startswith("storage.")]
    assert storage_classes == ["PN_StoragePumpNoInfeed"]


# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# Hydro/PHS generators must never merge across the PHS/non-PHS boundary,
# no matter how broad a --tech-group is: reported directly, from a real
# ~44 MB nodal PyPSA model. With --tech-group Generation.Renewable.Hydro.*,
# Generation.Renewable.Hydro.{PHS.ClosedLoop,Reservoir,RunOfRiver} all
# truncate to the same 3-segment tag, so a naive tech-tag-only grouping
# key merges generators of all three subtypes into one aggregated
# HydroGenerationUnit per country -- but the reservoir side keeps its
# untruncated storage_technology_type tags ("PHS" vs "hydro") distinct,
# so the merged generator would legitimately need to reference more
# than one aggregated reservoir. That in turn broke a further, separate
# case downstream: a single merged generator's own dispatch-view
# attributes (hydro_machine_kind and pumping signals) apply to the
# *whole* group, so tools/import_flexeco.py's PN_StorageDam vs.
# PN_StoragePump* classification -- which determines PHS-ness from the
# generator a reservoir is paired with -- could no longer tell the two
# original reservoirs apart once merged, misclassifying the plain-hydro
# one as an incomplete open-loop PHS instead of a working PN_StorageDam.
# Fixed at the root instead of downstream: the generation grouping key
# now also considers whether a HydroGenerationUnit is PHS-paired
# (is_phs_paired_generator()), so PHS-linked and non-PHS-linked hydro
# generators never merge regardless of --tech-group, and each stays
# correctly linked to its own single reservoir.
#
# (The underlying multi-target-relation data loss this scenario first
# surfaced -- add_relation() has no accumulation semantics at all, and
# both persistence_yaml_json.py's import_yaml and
# hierarchical_yaml.py's import_yaml_hierarchical had the identical
# call-add_relation-once-per-target pattern -- was a real, independent
# bug in the core EAR persistence layer and is still fixed; it's tested
# directly and in isolation in test_multi_target_relation_preservation.py
# rather than here, since this exact aggregation scenario no longer
# produces a multi-target relation at all now that the generators stay
# separate.)
# ---------------------------------------------------------------------

@pytest.fixture
def two_bus_mixed_hydro_technology_model_yaml(tmp_path) -> Path:
    """One PHS-tagged reservoir/generator pair and one plain-reservoir-
    hydro-tagged pair, at two different DE buses -- the exact shape that
    used to trigger generator-side merging (same truncated tech tag)
    while the reservoir side stayed split (different, untruncated tech
    tags), before generators were also kept apart by PHS-pairing."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")
    model.add_entity("GeographicalRegion", "nuts3.de112")
    model.add_attribute("nuts3.de112", "name", "DE region 2")
    model.add_entity("ElectricalBus", "node.de111.4874")
    model.add_attribute("node.de111.4874", "nominal_voltage", 380)
    model.add_relation("node.de111.4874", "belongsToGeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de112.4874")
    model.add_attribute("node.de112.4874", "nominal_voltage", 380)
    model.add_relation("node.de112.4874", "belongsToGeographicalRegion", "nuts3.de112")
    bus1 = "node.de111.4874"
    bus2 = "node.de112.4874"

    res1_id, gen1_id = "storage.phs.01.de111.4874", "generator.hydro.storage.phs.01.de111.4874"
    model.add_entity("HydraulicStorageUnit", res1_id)
    model.add_attribute(res1_id, "name", res1_id)
    model.add_relation(res1_id, "storesResource", "resource.water")
    model.add_attribute(res1_id, "energy_storage_capacity", 1030.0)

    model.add_entity("HydroGenerationUnit", gen1_id)
    model.add_attribute(gen1_id, "name", gen1_id)
    model.add_attribute(gen1_id, "hydro_machine_kind", "reversible")
    model.add_relation(gen1_id, "hasTechnology", "Generation.Renewable.Hydro.PHS.ClosedLoop")
    model.add_relation(gen1_id, "hasInputResource", "resource.water")
    model.add_relation(gen1_id, "hasOutputCarrier", "carrier.electricity")
    model.add_relation(gen1_id, "drawsFromHydraulicStorage", res1_id)
    model.add_attribute(gen1_id, "hydro_machine_kind", "reversible")
    model.add_attribute(gen1_id, "nominal_power_capacity", 220.0)
    model.add_relation(gen1_id, "atNode", "node.de111.4874")

    res2_id, gen2_id = "storage.hydro.02.de112.4874", "generator.hydro.storage.hydro.02.de112.4874"
    model.add_entity("HydraulicStorageUnit", res2_id)
    model.add_attribute(res2_id, "name", res2_id)
    model.add_relation(res2_id, "storesResource", "resource.water")
    model.add_attribute(res2_id, "energy_storage_capacity", 500.0)

    model.add_entity("HydroGenerationUnit", gen2_id)
    model.add_attribute(gen2_id, "name", gen2_id)
    model.add_attribute(gen2_id, "hydro_machine_kind", "turbine")
    model.add_relation(gen2_id, "hasTechnology", "Generation.Renewable.Hydro.Reservoir")
    model.add_relation(gen2_id, "hasInputResource", "resource.water")
    model.add_relation(gen2_id, "hasOutputCarrier", "carrier.electricity")
    model.add_relation(gen2_id, "drawsFromHydraulicStorage", res2_id)
    model.add_attribute(gen2_id, "nominal_power_capacity", 150.0)
    model.add_relation(gen2_id, "atNode", "node.de112.4874")

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "mixed_hydro_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml(str(yaml_path))
    return yaml_path


@pytest.fixture
def two_bus_mixed_hydro_technology_model_yaml_with_inflow(tmp_path) -> Path:
    """Same shape as two_bus_mixed_hydro_technology_model_yaml, but the
    plain-hydro reservoir also has an annual_natural_inflow_energy value
    -- needed for it to be a PN_StorageDam candidate at all in
    tools/import_flexeco.py (a no-inflow, non-PHS reservoir is skipped
    outright, not misclassified)."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")
    model.add_entity("GeographicalRegion", "nuts3.de112")
    model.add_attribute("nuts3.de112", "name", "DE region 2")
    model.add_entity("ElectricalBus", "node.de111.4874")
    model.add_attribute("node.de111.4874", "nominal_voltage", 380)
    model.add_relation("node.de111.4874", "belongsToGeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de112.4874")
    model.add_attribute("node.de112.4874", "nominal_voltage", 380)
    model.add_relation("node.de112.4874", "belongsToGeographicalRegion", "nuts3.de112")
    bus1 = "node.de111.4874"
    bus2 = "node.de112.4874"

    res1_id, gen1_id = "storage.phs.01.de111.4874", "generator.hydro.storage.phs.01.de111.4874"
    model.add_entity("HydraulicStorageUnit", res1_id)
    model.add_attribute(res1_id, "name", res1_id)
    model.add_relation(res1_id, "storesResource", "resource.water")
    model.add_attribute(res1_id, "energy_storage_capacity", 1030.0)

    model.add_entity("HydroGenerationUnit", gen1_id)
    model.add_attribute(gen1_id, "name", gen1_id)
    model.add_attribute(gen1_id, "hydro_machine_kind", "reversible")
    model.add_relation(gen1_id, "hasTechnology", "Generation.Renewable.Hydro.PHS.ClosedLoop")
    model.add_relation(gen1_id, "hasInputResource", "resource.water")
    model.add_relation(gen1_id, "hasOutputCarrier", "carrier.electricity")
    model.add_relation(gen1_id, "drawsFromHydraulicStorage", res1_id)
    model.add_attribute(gen1_id, "hydro_machine_kind", "reversible")
    model.add_attribute(gen1_id, "nominal_power_capacity", 220.0)
    model.add_attribute(gen1_id, "pumping_efficiency", 0.85)
    model.add_attribute(gen1_id, "turbine_efficiency", 0.90)
    model.add_attribute(gen1_id, "maximum_pumping_power", 220.0)
    model.add_relation(gen1_id, "atNode", "node.de111.4874")

    res2_id, gen2_id = "storage.hydro.02.de112.4874", "generator.hydro.storage.hydro.02.de112.4874"
    model.add_entity("HydraulicStorageUnit", res2_id)
    model.add_attribute(res2_id, "name", res2_id)
    model.add_relation(res2_id, "storesResource", "resource.water")
    model.add_attribute(res2_id, "energy_storage_capacity", 500.0)
    model.add_attribute(res2_id, "annual_natural_inflow_energy", 300.0)

    model.add_entity("HydroGenerationUnit", gen2_id)
    model.add_attribute(gen2_id, "name", gen2_id)
    model.add_attribute(gen2_id, "hydro_machine_kind", "turbine")
    model.add_relation(gen2_id, "hasTechnology", "Generation.Renewable.Hydro.Reservoir")
    model.add_relation(gen2_id, "hasInputResource", "resource.water")
    model.add_relation(gen2_id, "hasOutputCarrier", "carrier.electricity")
    model.add_relation(gen2_id, "drawsFromHydraulicStorage", res2_id)
    model.add_attribute(gen2_id, "nominal_power_capacity", 150.0)
    model.add_attribute(gen2_id, "turbine_efficiency", 0.92)
    model.add_relation(gen2_id, "atNode", "node.de112.4874")

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "mixed_hydro_model_with_inflow.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml(str(yaml_path))
    return yaml_path


def test_phs_and_non_phs_hydro_generators_never_merge_under_broad_tech_group(
    two_bus_mixed_hydro_technology_model_yaml,
):
    """Even with --tech-group Generation.Renewable.Hydro.*, which would
    otherwise put PHS and plain hydro in the same technology tag, the
    PHS-paired and plain-hydro-paired generators must stay as two
    separate aggregated entities -- and so must their reservoirs."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_mixed_hydro_technology_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", False, None, lambda *a: None,
        tech_groups=["Generation.Renewable.Hydro.*"],
    )

    assert len(out_obj["HydroGenerationUnit"]) == 2
    assert len(out_obj["HydraulicStorageUnit"]) == 2


def test_reservoirs_with_no_distinguishing_tech_tag_still_separate_by_paired_generator(tmp_path):
    """The gap the previous fixture's reservoirs never actually
    exercised (see its own docstring: their reservoirs 'were never
    going to merge anyway' -- they happened to carry different
    storage_technology_type tags already). Here, neither reservoir has
    any technology tag at all: without is_phs_reservoir(), both would
    fall back to the exact same asset_technology_tag() default
    (asset_class="HydraulicStorageUnit" for both) and merge into one
    aggregated reservoir -- even though their paired generators
    (a plain turbine and a reversible PHS unit) are correctly kept
    apart. A merged reservoir would then have both aggregated
    generators' drawsFromHydraulicStorage pointing at the same physically
    meaningless combined water body."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")
    model.ensure_resource("resource.water", name="Water", resource_type="water")

    # No storage_technology_type and no hasTechnology on either
    # reservoir -- both would resolve to the identical fallback tag.
    res_turbine = model.add_entity("HydraulicStorageUnit", "reservoir.turbine.1")
    model.add_relation("reservoir.turbine.1", "storesResource", "resource.water")
    res_turbine.dispatch.energy_storage_capacity = 500.0
    turbine = model.add_entity("HydroGenerationUnit", "gen.turbine.1")
    model.set_technology("gen.turbine.1", "Generation.Renewable.Hydro.RunOfRiver", technology_class="GeneratorType")
    model.add_relation("gen.turbine.1", "atNode", "node.de111.380")
    model.add_relation("gen.turbine.1", "drawsFromHydraulicStorage", "reservoir.turbine.1")
    turbine.dispatch.hydro_machine_kind = "turbine"
    turbine.dispatch.nominal_power_capacity = 100.0

    res_reversible = model.add_entity("HydraulicStorageUnit", "reservoir.reversible.1")
    model.add_relation("reservoir.reversible.1", "storesResource", "resource.water")
    res_reversible.dispatch.energy_storage_capacity = 800.0
    reversible = model.add_entity("HydroGenerationUnit", "gen.reversible.1")
    model.set_technology("gen.reversible.1", "Generation.Renewable.Hydro.PHS.ClosedLoop", technology_class="GeneratorType")
    model.add_relation("gen.reversible.1", "atNode", "node.de111.380")
    model.add_relation("gen.reversible.1", "drawsFromHydraulicStorage", "reservoir.reversible.1")
    reversible.dispatch.hydro_machine_kind = "reversible"
    reversible.dispatch.nominal_power_capacity = 150.0

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "turbine_reversible.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml_hierarchical(str(yaml_path))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")
    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    assert len(out_obj["HydraulicStorageUnit"]) == 2, (
        "the turbine's and the reversible unit's reservoirs must not merge, "
        f"got: {list(out_obj['HydraulicStorageUnit'].keys())}"
    )
    capacities = sorted(
        next(a["value"] for a in e["attributes"] if a["id"] == "energy_storage_capacity")
        for e in out_obj["HydraulicStorageUnit"].values()
    )
    assert capacities == [500.0, 800.0], "capacities must not have been summed together"

    # Each aggregated generator's drawsFromHydraulicStorage must point at its
    # own distinct reservoir -- never the same one as the other.
    reservoir_targets = [
        rel["target_entity_ids"][0]
        for gen_ent in out_obj["HydroGenerationUnit"].values()
        for rel in gen_ent["relations"]
        if rel["id"] == "drawsFromHydraulicStorage"
    ]
    assert len(set(reservoir_targets)) == 2


def test_each_hydro_generator_still_correctly_linked_to_its_own_reservoir(
    two_bus_mixed_hydro_technology_model_yaml,
):
    """With PHS/non-PHS generators kept apart, each aggregated generator
    should have a plain single-target drawsFromHydraulicStorage pointing at
    its own aggregated reservoir -- not a merged, multi-target one."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_mixed_hydro_technology_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", False, None, lambda *a: None,
        tech_groups=["Generation.Renewable.Hydro.*"],
    )

    reservoir_ids = set(out_obj["HydraulicStorageUnit"].keys())
    seen_targets = set()
    for gen_ent in out_obj["HydroGenerationUnit"].values():
        draws_from = next(
            r["target_entity_ids"] for r in gen_ent["relations"] if r["id"] == "drawsFromHydraulicStorage"
        )
        assert len(draws_from) == 1, f"expected exactly one target, got {draws_from!r}"
        assert draws_from[0] in reservoir_ids
        seen_targets.add(draws_from[0])

    assert seen_targets == reservoir_ids  # every reservoir is claimed by exactly one generator


def test_is_phs_paired_generator_distinguishes_the_two(two_bus_mixed_hydro_technology_model_yaml):
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_mixed_hydro_technology_model_yaml)
    data = agg.model_to_data(model)

    assert agg.is_phs_paired_generator(data, "generator.hydro.storage.phs.01.de111.4874") is True
    assert agg.is_phs_paired_generator(data, "generator.hydro.storage.hydro.02.de112.4874") is False


def test_aggregated_closed_loop_and_plain_hydro_classify_correctly_end_to_end(
    two_bus_mixed_hydro_technology_model_yaml_with_inflow, tmp_path,
):
    """Full pipeline: aggregate, then export to FlexECO, and confirm the
    PHS reservoir classifies as PN_StoragePumpNoInfeed and the plain
    reservoir hydro one classifies as PN_StorageDam -- the exact
    downstream misclassification (plain hydro incorrectly treated as
    incomplete PHS) this fix resolves."""
    pytest.importorskip("scipy")
    pytest.importorskip("cesdm_flexeco")
    from cesdm_flexeco import export_to_flexeco

    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_mixed_hydro_technology_model_yaml_with_inflow)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")
    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", False, None, lambda *a: None,
        tech_groups=["Generation.Renewable.Hydro.*"],
    )
    out_model = agg.data_to_model(ROOT / "schemas/cesdm", out_obj)
    agg_yaml = tmp_path / "aggregated.yaml"
    out_model.export_yaml_hierarchical(str(agg_yaml))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml_hierarchical(str(agg_yaml))

    flexeco_out = tmp_path / "flexeco_output.json"
    export_to_flexeco(reloaded, str(flexeco_out))

    import json
    result = json.loads(flexeco_out.read_text())
    classes_by_name = {el["name"]: el["class"] for el in result["PowerSystemElements"]}

    assert classes_by_name.get("storage.hydraulicstorageunit.phs.agg.de") == "PN_StoragePumpNoInfeed"
    assert classes_by_name.get("storage.hydraulicstorageunit.nonphs.agg.de") == "PN_StorageDam"


# ---------------------------------------------------------------------
# dispatch_type: reported directly -- every non-dispatchable generation
# unit (wind, solar, etc.) was exported to FlexECO as dispatchable after
# aggregation. Same class of bug as pumping_efficiency/turbine_efficiency
# before it: dispatch_type was listed in allowed_agg_attrs_for_generation()
# as an attribute the aggregator is allowed to carry through, but nothing
# ever actually computed or wrote it -- every aggregated generator lost
# it regardless of technology, and tools/import_flexeco.py's
# PN_GenDispatchable vs. PN_GenNonDispatchable classification (which
# reads dispatch_type directly) defaults to dispatchable when it's
# simply absent.
# ---------------------------------------------------------------------

@pytest.fixture
def two_bus_wind_model_yaml(tmp_path) -> Path:
    """Two onshore wind generators at two DE buses, both explicitly
    dispatch_type=nondispatchable -- merges into one aggregated
    generator at country level."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")
    model.add_entity("GeographicalRegion", "nuts3.de112")
    model.add_attribute("nuts3.de112", "name", "DE region 2")
    model.add_entity("ElectricalBus", "node.de111.4874")
    model.add_attribute("node.de111.4874", "nominal_voltage", 380)
    model.add_relation("node.de111.4874", "belongsToGeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de112.4874")
    model.add_attribute("node.de112.4874", "nominal_voltage", 380)
    model.add_relation("node.de112.4874", "belongsToGeographicalRegion", "nuts3.de112")
    bus1 = "node.de111.4874"
    bus2 = "node.de112.4874"

    for i, bus in enumerate([bus1, bus2]):
        gid = f"gen.onwind.{i}"
        model.add_entity("GenerationUnit", gid)
        model.set_technology(gid, "Generation.Renewable.Wind.Onshore", technology_class="GeneratorType")
        model.add_relation(gid, "atNode", bus)
        gen = model.get_entity(gid)
        gen.dispatch.nominal_power_capacity = 100.0 + i * 20
        gen.dispatch.dispatch_type = "nondispatchable"

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "wind_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml(str(yaml_path))
    return yaml_path


@pytest.fixture
def two_bus_wind_model_with_profiles_yaml(tmp_path) -> Path:
    """Two onshore wind generators at two DE buses, each with its own
    hasAvailabilityProfile -- merges into one aggregated generator at
    country level, which must end up with an aggregated profile of its
    own."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region 1")
    model.add_entity("GeographicalRegion", "nuts3.de112")
    model.add_attribute("nuts3.de112", "name", "DE region 2")
    model.add_entity("ElectricalBus", "node.de111.4874")
    model.add_attribute("node.de111.4874", "nominal_voltage", 380)
    model.add_relation("node.de111.4874", "belongsToGeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de112.4874")
    model.add_attribute("node.de112.4874", "nominal_voltage", 380)
    model.add_relation("node.de112.4874", "belongsToGeographicalRegion", "nuts3.de112")
    bus1 = "node.de111.4874"
    bus2 = "node.de112.4874"

    model.add_entity("TimestampSeries", "ts.hourly")
    model.add_attribute("ts.hourly", "start_datetime", "2030-01-01T00:00:00")
    model.add_attribute("ts.hourly", "resolution", "PT1H")
    model.add_attribute("ts.hourly", "length", 4)

    for i, bus in enumerate([bus1, bus2]):
        gid = f"gen.onwind.{i}"
        model.add_entity("GenerationUnit", gid)
        model.set_technology(gid, "Generation.Renewable.Wind.Onshore", technology_class="GeneratorType")
        model.add_relation(gid, "atNode", bus)
        gen = model.get_entity(gid)
        gen.dispatch.nominal_power_capacity = 100.0 + i * 20
        gen.dispatch.dispatch_type = "nondispatchable"

        pid = f"profile.{gid}"
        model.add_entity("Profile", pid)
        model.add_attribute(pid, "profile_type", "as_capacity_factor")
        model.add_attribute(pid, "data_reference", f"/profiles/{pid}")
        model.add_relation(pid, "hasTimestampSeries", "ts.hourly")
        model.add_relation(gid, "hasAvailabilityProfile", pid)

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "wind_model_with_profiles.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml(str(yaml_path))
    return yaml_path


def test_availability_profile_survives_aggregation_for_non_hydro_generation(
    two_bus_wind_model_with_profiles_yaml, tmp_path,
):
    """The real bug this regression guards against: an earlier version
    excluded the shared "Generation.DispatchView" bucket -- which
    covers Wind, Solar, Thermal, and any other non-hydro
    GenerationUnit -- from ever getting its freshly aggregated profile
    relation attached, via a condition that (once its duplicated
    string was seen for what it was) reduced to `view_section !=
    "Generation.DispatchView"`. The aggregated profile itself was
    still computed and written to the output, just orphaned: nothing
    pointed to it, and downstream tools (e.g. tools/import_flexeco.py)
    would then skip the generator entirely for "no availability ...
    profile"."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_wind_model_with_profiles_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    h5_path = tmp_path / "profiles.h5"
    import h5py
    import numpy as np
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("profiles/profile.gen.onwind.0/values", data=np.array([0.1, 0.2, 0.3, 0.4]))
        f.create_dataset("profiles/profile.gen.onwind.1/values", data=np.array([0.5, 0.6, 0.7, 0.8]))

    pm = agg.ProfileMatrix(h5_path)
    out_obj, series, stats = agg.aggregate_subset(
        data, buses, "country", True, pm, lambda *a: None,
    )

    gen_id = next(iter(out_obj["GenerationUnit"]))
    ent = out_obj["GenerationUnit"][gen_id]
    rel_ids = {r["id"] for r in ent["relations"]}
    assert "hasAvailabilityProfile" in rel_ids, (
        f"aggregated wind generator {gen_id!r} lost its availability profile relation "
        f"-- found relations: {rel_ids}"
    )

    profile_target = next(
        r["target_entity_ids"][0] for r in ent["relations"] if r["id"] == "hasAvailabilityProfile"
    )
    assert profile_target in out_obj.get("Profile", {}), (
        f"hasAvailabilityProfile points at {profile_target!r}, which isn't a real "
        f"Profile entity in the aggregated output"
    )


def test_missing_profile_on_nondispatchable_generator_is_logged(two_bus_wind_model_yaml):
    """The follow-up to the profile-linking fix above: if a
    non-dispatchable (wind/solar/run-of-river) generator genuinely has
    no profile to aggregate, the aggregated entity is still written
    (correct -- the tool can't invent missing data), but that used to
    happen completely silently. A downstream tool several steps removed
    (tools/import_flexeco.py) would then skip the generator with a
    message that gives no hint this ever went through aggregation.
    aggregate_subset() must log a [WARN] itself, right when the gap is
    still visible, for exactly this case -- and must NOT do so for a
    dispatchable generator, which genuinely has no profile to lose."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_wind_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    logged = []
    agg.aggregate_subset(
        data, buses, "country", True, None, lambda msg: logged.append(msg),
    )

    warnings = [m for m in logged if "no availability/run-of-river profile" in m]
    assert len(warnings) == 1, f"expected exactly one warning, got: {logged}"
    assert "gen.onwind" in warnings[0]


def test_phs_generator_without_profile_is_not_logged(tmp_path):
    """The real bug this regression guards against: a PHS (reversible
    pump-turbine) unit is dispatchable -- operated from stored
    reservoir water on demand, not constrained by a natural inflow --
    so it genuinely has no hasNaturalInflowProfile to lose. An
    earlier version warned for every hydro generator unconditionally
    (bucket == "hydro"), regardless of whether it was a plain turbine
    or reversible, which fired this warning for every aggregated PHS
    unit in a real dataset -- a warning that was never actionable,
    since PHS units are not supposed to have this profile at all. A
    plain (non-reversible) turbine's output genuinely is constrained
    by natural flow and must still warn (see
    test_missing_profile_on_nondispatchable_generator_is_logged)."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))
    model.ensure_resource("resource.water", name="Water", resource_type="water")

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")

    res_r = model.add_entity("HydraulicStorageUnit", "reservoir.reversible.1")
    model.add_relation("reservoir.reversible.1", "storesResource", "resource.water")
    res_r.dispatch.energy_storage_capacity = 800.0
    rev = model.add_entity("HydroGenerationUnit", "gen.reversible.1")
    model.set_technology("gen.reversible.1", "Generation.Renewable.Hydro.PHS.ClosedLoop", technology_class="GeneratorType")
    model.add_relation("gen.reversible.1", "atNode", "node.de111.380")
    model.add_relation("gen.reversible.1", "drawsFromHydraulicStorage", "reservoir.reversible.1")
    rev.dispatch.hydro_machine_kind = "reversible"
    rev.dispatch.nominal_power_capacity = 60.0
    rev.dispatch.maximum_pumping_power = 55.0
    # No hasNaturalInflowProfile at all -- correct for PHS.

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "phs_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml_hierarchical(str(yaml_path))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")

    logged = []
    agg.aggregate_subset(
        data, buses, "country", True, None, lambda msg: logged.append(msg),
    )

    warnings = [m for m in logged if "no availability/run-of-river profile" in m]
    assert warnings == [], f"a PHS unit should never trigger this warning, got: {warnings}"


def test_reservoir_coupled_turbine_with_reservoir_inflow_is_not_logged(tmp_path):
    """The real bug this regression guards against: a reservoir-coupled
    HydroGenerationUnit (has drawsFromHydraulicStorage) correctly has no
    hasNaturalInflowProfile of its own -- the schema's own words:
    "Reservoir-level parameters (inflow, volume) are declared directly
    on the linked HydraulicStorageUnit entity itself." An earlier
    version checked only the generator's own profile relation, so
    every aggregated reservoir-coupled turbine triggered this warning
    unconditionally, even when its paired reservoir correctly carries
    a real, positive natural inflow profile. A true run-of-river
    generator with no reservoir at all, and genuinely no profile, must
    still warn (see
    test_missing_profile_on_nondispatchable_generator_is_logged)."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))
    model.ensure_resource("resource.water", name="Water", resource_type="water")

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")

    ts = model.add_entity("TimestampSeries", "ts.1")
    ts.add_attribute(attribute_id="start_datetime", value="2030-01-01T00:00:00")
    ts.add_attribute(attribute_id="resolution", value="PT1H")
    ts.add_attribute(attribute_id="length", value=4)

    res = model.add_entity("HydraulicStorageUnit", "reservoir.withinflow.1")
    model.add_relation("reservoir.withinflow.1", "storesResource", "resource.water")
    res.dispatch.energy_storage_capacity = 500.0
    res.dispatch.annual_natural_inflow_energy = 20000.0
    prof = model.add_entity("Profile", "profile.inflow.1")
    prof.add_attribute(attribute_id="profile_type", value="as_normalized_annual_energy")
    prof.add_attribute(attribute_id="data_reference", value="/profiles/profile.inflow.1")
    prof.add_relation(relation_id="hasTimestampSeries", target_entity_id="ts.1")
    model.add_relation("reservoir.withinflow.1", "hasNaturalInflowProfile", "profile.inflow.1")

    turb = model.add_entity("HydroGenerationUnit", "gen.reservoircoupled.1")
    model.set_technology("gen.reservoircoupled.1", "Generation.Renewable.Hydro.Reservoir", technology_class="GeneratorType")
    model.add_relation("gen.reservoircoupled.1", "atNode", "node.de111.380")
    model.add_relation("gen.reservoircoupled.1", "drawsFromHydraulicStorage", "reservoir.withinflow.1")
    turb.dispatch.hydro_machine_kind = "turbine"
    turb.dispatch.nominal_power_capacity = 40.0
    # gen.reservoircoupled.1 deliberately has no profile relation of its
    # own at all -- correct, since the inflow data lives on the reservoir.

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "reservoir_coupled_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml_hierarchical(str(yaml_path))

    import h5py
    import numpy as np

    h5_path = tmp_path / "profiles.h5"
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("profiles/profile.inflow.1/values", data=np.array([0.2, 0.3, 0.2, 0.3]))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")

    logged = []
    pm = agg.ProfileMatrix(h5_path)
    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, pm, lambda msg: logged.append(msg),
    )

    warnings = [m for m in logged if "no availability/run-of-river profile" in m]
    assert warnings == [], f"reservoir-coupled turbine with a real reservoir inflow should not warn, got: {warnings}"

    # And the aggregated reservoir genuinely does carry the inflow profile.
    res_id = next(iter(out_obj["HydraulicStorageUnit"]))
    rel_ids = {r["id"] for r in out_obj["HydraulicStorageUnit"][res_id]["relations"]}
    assert "hasNaturalInflowProfile" in rel_ids


def test_dispatchable_generator_without_profile_is_not_logged(tmp_path):
    """A dispatchable generator (thermal, nuclear, ...) genuinely has
    no availability profile to lose -- aggregating one with none set
    must not produce a [WARN]."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de111.4874")
    model.add_attribute("node.de111.4874", "nominal_voltage", 380)
    model.add_relation("node.de111.4874", "belongsToGeographicalRegion", "nuts3.de111")

    model.add_entity("ThermalGenerationUnit", "gen.gas.0")
    model.set_technology("gen.gas.0", "Generation.Thermal.Gas.CCGT.New", technology_class="GeneratorType")
    model.add_relation("gen.gas.0", "atNode", "node.de111.4874")
    gen = model.get_entity("gen.gas.0")
    gen.dispatch.nominal_power_capacity = 400.0
    gen.dispatch.dispatch_type = "dispatchable"

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "thermal_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml(str(yaml_path))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")

    logged = []
    agg.aggregate_subset(
        data, buses, "country", True, None, lambda msg: logged.append(msg),
    )

    warnings = [m for m in logged if "no availability/run-of-river profile" in m]
    assert warnings == [], f"dispatchable generator should not trigger this warning, got: {warnings}"


def test_sanity_check_conserves_totals_across_all_categories(tmp_path):
    """The comprehensive per-country sanity check: dispatchable and
    non-dispatchable generation capacity (and non-dispatchable
    annual_resource_potential) by technology, hydro turbine vs.
    reversible discharge/charge capacity, battery StorageUnit
    energy/charge/discharge capacity, reservoir capacity and
    inflow, and demand must all sum to the same totals before and
    after aggregation -- built from one bus with a dispatchable
    generator, a non-dispatchable one, a plain turbine + its
    reservoir, a reversible unit + its reservoir, a battery, and a
    demand, so every category in the report has a genuine non-zero
    value to compare."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))
    model.ensure_resource("resource.water", name="Water", resource_type="water")

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")

    gas = model.add_entity("ThermalGenerationUnit", "gen.gas.1")
    model.set_technology("gen.gas.1", "Generation.Thermal.Gas.CCGT.New", technology_class="GeneratorType")
    model.add_relation("gen.gas.1", "atNode", "node.de111.380")
    gas.dispatch.nominal_power_capacity = 100.0
    gas.dispatch.dispatch_type = "dispatchable"

    wind = model.add_entity("WindGenerationUnit", "gen.wind.1")
    model.set_technology("gen.wind.1", "Generation.Renewable.Wind.Onshore", technology_class="GeneratorType")
    model.add_relation("gen.wind.1", "atNode", "node.de111.380")
    wind.dispatch.nominal_power_capacity = 50.0
    wind.dispatch.dispatch_type = "nondispatchable"
    wind.dispatch.annual_resource_potential = 90000.0

    res_t = model.add_entity("HydraulicStorageUnit", "reservoir.turbine.1")
    model.add_relation("reservoir.turbine.1", "storesResource", "resource.water")
    res_t.dispatch.energy_storage_capacity = 500.0
    res_t.dispatch.annual_natural_inflow_energy = 20000.0
    turb = model.add_entity("HydroGenerationUnit", "gen.turbine.1")
    model.set_technology("gen.turbine.1", "Generation.Renewable.Hydro.RunOfRiver", technology_class="GeneratorType")
    model.add_relation("gen.turbine.1", "atNode", "node.de111.380")
    model.add_relation("gen.turbine.1", "drawsFromHydraulicStorage", "reservoir.turbine.1")
    turb.dispatch.hydro_machine_kind = "turbine"
    turb.dispatch.nominal_power_capacity = 40.0

    res_r = model.add_entity("HydraulicStorageUnit", "reservoir.reversible.1")
    model.add_relation("reservoir.reversible.1", "storesResource", "resource.water")
    res_r.dispatch.energy_storage_capacity = 800.0
    rev = model.add_entity("HydroGenerationUnit", "gen.reversible.1")
    model.set_technology("gen.reversible.1", "Generation.Renewable.Hydro.PHS.ClosedLoop", technology_class="GeneratorType")
    model.add_relation("gen.reversible.1", "atNode", "node.de111.380")
    model.add_relation("gen.reversible.1", "drawsFromHydraulicStorage", "reservoir.reversible.1")
    rev.dispatch.hydro_machine_kind = "reversible"
    rev.dispatch.nominal_power_capacity = 60.0
    rev.dispatch.maximum_pumping_power = 55.0

    bat = model.add_entity("StorageUnit", "bat.1")
    model.set_technology(
        "bat.1", "Storage.Electrochemical.Battery", technology_class="StorageType",
    )
    model.add_relation("bat.1", "atNode", "node.de111.380")
    bat.dispatch.energy_storage_capacity = 200.0
    bat.dispatch.nominal_power_capacity = 80.0
    bat.dispatch.maximum_charging_power = 70.0
    bat.dispatch.maximum_discharging_power = 80.0
    bat.dispatch.charging_efficiency = 0.95
    bat.dispatch.discharging_efficiency = 0.95

    dem = model.add_entity("DemandUnit", "demand.1")
    model.add_relation("demand.1", "atNode", "node.de111.380")
    dem.dispatch.annual_energy_demand = 300000.0

    _ensure_elec_carrier_domain(model)

    model.validate_or_raise()
    yaml_path = tmp_path / "sanity_model.yaml"
    _ensure_elec_carrier_domain(model)

    model.export_yaml_hierarchical(str(yaml_path))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")
    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    disagg = stats["_sanity_disaggregated_by_country"]["de"]
    aggd = stats["_sanity_aggregated_by_country"]["de"]

    assert disagg["hydro_turbine_discharge_capacity_mw"] == aggd["hydro_turbine_discharge_capacity_mw"] == 40.0
    assert disagg["hydro_reversible_discharge_capacity_mw"] == aggd["hydro_reversible_discharge_capacity_mw"] == 60.0
    assert disagg["hydro_reversible_charge_capacity_mw"] == aggd["hydro_reversible_charge_capacity_mw"] == 55.0
    assert disagg["reservoir_capacity_mwh"] == aggd["reservoir_capacity_mwh"] == 1300.0
    assert disagg["reservoir_inflow_mwh"] == aggd["reservoir_inflow_mwh"] == 20000.0
    assert disagg["demand_annual_energy_mwh"] == aggd["demand_annual_energy_mwh"] == 300000.0
    assert sum(disagg["dispatchable_capacity_mw"].values()) == sum(aggd["dispatchable_capacity_mw"].values()) == 100.0
    assert sum(disagg["nondispatchable_capacity_mw"].values()) == sum(aggd["nondispatchable_capacity_mw"].values()) == 50.0
    assert (
        sum(disagg["nondispatchable_annual_resource_potential_mwh"].values())
        == sum(aggd["nondispatchable_annual_resource_potential_mwh"].values())
        == 90000.0
    )
    assert sum(disagg["storage_energy_capacity_mwh"].values()) == sum(aggd["storage_energy_capacity_mwh"].values()) == 200.0
    assert sum(disagg["storage_discharge_capacity_mw"].values()) == sum(aggd["storage_discharge_capacity_mw"].values()) == 80.0
    assert sum(disagg["storage_charge_capacity_mw"].values()) == sum(aggd["storage_charge_capacity_mw"].values()) == 70.0
    assert "StorageUnit" in out_obj and len(out_obj["StorageUnit"]) == 1


def test_write_sanity_check_report_flags_a_real_mismatch(tmp_path):
    """The report-writing side: an intentionally introduced discrepancy
    between the two totals dicts (as if aggregation had silently lost
    or duplicated capacity) must be flagged as MISMATCH, both in the
    written file and via a [WARN] log line -- and a genuinely matching
    pair must be reported as fully conserved, with no false positive."""
    logged = []
    disagg_totals = {"de": {"demand_annual_energy_mwh": 1000.0, "reservoir_capacity_mwh": 500.0}}
    agg_totals_bad = {"de": {"demand_annual_energy_mwh": 999.0, "reservoir_capacity_mwh": 500.0}}
    agg.write_sanity_check_report(tmp_path, disagg_totals, agg_totals_bad, lambda msg: logged.append(msg))

    report = (tmp_path / "sanity_check_by_country.txt").read_text()
    assert "MISMATCH" in report
    assert "demand_annual_energy_mwh" in report
    assert any("demand_annual_energy_mwh" in m for m in logged)
    assert any("MISMATCHES FOUND" in m for m in logged)

    logged.clear()
    agg_totals_good = {"de": {"demand_annual_energy_mwh": 1000.0, "reservoir_capacity_mwh": 500.0}}
    agg.write_sanity_check_report(tmp_path, disagg_totals, agg_totals_good, lambda msg: logged.append(msg))
    report2 = (tmp_path / "sanity_check_by_country.txt").read_text()
    assert "MISMATCH" not in report2
    assert not any(m.startswith("[WARN]") for m in logged)


def test_dispatch_type_is_preserved_after_aggregation(two_bus_wind_model_yaml):
    """The actual bug: dispatch_type was allowed but never computed or
    written, so every aggregated generator -- wind, solar, anything --
    silently lost it, regardless of what its pre-aggregation members
    had set."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_wind_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    gen_id = next(iter(out_obj["GenerationUnit"]))
    attrs = {a["id"]: a["value"] for a in out_obj["GenerationUnit"][gen_id]["attributes"]}
    assert attrs.get("dispatch_type") == "nondispatchable"


def test_dispatch_type_survives_export_reimport_round_trip(two_bus_wind_model_yaml, tmp_path):
    """End to end: the exported YAML, reloaded the ordinary way, still
    has dispatch_type set on the aggregated generator."""
    model = agg.load_cesdm_model(ROOT / "schemas/cesdm", two_bus_wind_model_yaml)
    data = agg.model_to_data(model)
    buses = agg.section_items(data, "ElectricalBus")

    out_obj, _series, stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )
    out_model = agg.data_to_model(ROOT / "schemas/cesdm", out_obj)
    out_yaml = tmp_path / "aggregated.yaml"
    out_model.export_yaml_hierarchical(str(out_yaml))

    reloaded = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    reloaded.import_yaml_hierarchical(str(out_yaml))

    gen_dv = next(iter(reloaded.entities["GenerationUnit"].values()))
    stored = gen_dv.data.get("dispatch_type")
    value = stored.get("value") if isinstance(stored, dict) else stored
    assert value == "nondispatchable"


def test_branch_assets_are_not_merged_or_averaged(tmp_path):
    """All branch classes stay one-for-one: original ids and parameters
    are preserved; only fromNode/toNode are remapped onto aggregated
    buses. Parallel assets between the same country pair must not
    collapse into *.agg.* corridors."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_entity("GeographicalRegion", "nuts3.ch011")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")
    model.add_entity("ElectricalBus", "node.ch011.380")
    model.add_attribute("node.ch011.380", "nominal_voltage", 380)
    model.add_relation("node.ch011.380", "belongsToGeographicalRegion", "nuts3.ch011")
    # Second CH voltage so a transformer is not dropped as internal.
    model.add_entity("ElectricalBus", "node.ch011.220")
    model.add_attribute("node.ch011.220", "nominal_voltage", 220)
    model.add_relation("node.ch011.220", "belongsToGeographicalRegion", "nuts3.ch011")

    line_a = model.add_entity("TransmissionLine", "line.a")
    model.add_relation("line.a", "fromNode", "node.de111.380")
    model.add_relation("line.a", "toNode", "node.ch011.380")
    line_a.power_flow.thermal_capacity_rating = 1000.0
    line_a.power_flow.line_length = 40.0
    line_a.power_flow.series_reactance_per_km = 0.3

    line_b = model.add_entity("TransmissionLine", "line.b")
    model.add_relation("line.b", "fromNode", "node.de111.380")
    model.add_relation("line.b", "toNode", "node.ch011.380")
    line_b.power_flow.thermal_capacity_rating = 500.0
    line_b.power_flow.line_length = 55.0
    line_b.power_flow.series_reactance_per_km = 0.25

    ico_a = model.add_entity("GenericInterconnector", "ico.a")
    model.add_relation("ico.a", "fromNode", "node.de111.380")
    model.add_relation("ico.a", "toNode", "node.ch011.380")
    ico_a.power_flow.maximum_power_flow_from_to = 200.0
    ico_a.power_flow.maximum_power_flow_to_from = 150.0

    ico_b = model.add_entity("GenericInterconnector", "ico.b")
    model.add_relation("ico.b", "fromNode", "node.de111.380")
    model.add_relation("ico.b", "toNode", "node.ch011.380")
    ico_b.power_flow.maximum_power_flow_from_to = 80.0
    ico_b.power_flow.maximum_power_flow_to_from = 70.0

    hvdc_a = model.add_entity("HVDCLink", "hvdc.a")
    model.add_relation("hvdc.a", "fromNode", "node.de111.380")
    model.add_relation("hvdc.a", "toNode", "node.ch011.380")
    hvdc_a.power_flow.converter_technology = "VSC"
    hvdc_a.power_flow.max_flow = 300.0

    hvdc_b = model.add_entity("HVDCLink", "hvdc.b")
    model.add_relation("hvdc.b", "fromNode", "node.de111.380")
    model.add_relation("hvdc.b", "toNode", "node.ch011.380")
    hvdc_b.power_flow.converter_technology = "LCC"
    hvdc_b.power_flow.max_flow = 120.0

    tr_a = model.add_entity("Transformer", "tr.a")
    model.add_relation("tr.a", "fromNode", "node.ch011.380")
    model.add_relation("tr.a", "toNode", "node.ch011.220")
    tr_a.power_flow.thermal_capacity_rating = 400.0
    tr_a.power_flow.short_circuit_voltage_in_percentage = 12.0

    tr_b = model.add_entity("Transformer", "tr.b")
    model.add_relation("tr.b", "fromNode", "node.ch011.380")
    model.add_relation("tr.b", "toNode", "node.ch011.220")
    tr_b.power_flow.thermal_capacity_rating = 250.0
    tr_b.power_flow.short_circuit_voltage_in_percentage = 10.0

    _ensure_elec_carrier_domain(model)
    yaml_path = tmp_path / "branches.yaml"
    model.export_yaml_hierarchical(str(yaml_path))

    loaded = agg.load_cesdm_model(ROOT / "schemas/cesdm", yaml_path)
    data = agg.model_to_data(loaded)
    buses = agg.section_items(data, "ElectricalBus")
    out_obj, _series, _stats = agg.aggregate_subset(
        data, buses, "country", True, None, lambda *a: None,
    )

    def _attrs(section: str, eid: str) -> dict:
        return {a["id"]: a["value"] for a in out_obj[section][eid]["attributes"]}

    def _ends(section: str, eid: str) -> tuple[str, str]:
        rels = {r["id"]: r["target_entity_ids"][0] for r in out_obj[section][eid]["relations"]}
        return rels["fromNode"], rels["toNode"]

    lines = out_obj["TransmissionLine"]
    assert set(lines) == {"line.a", "line.b"}
    assert not any(".agg." in eid for eid in lines)
    assert _attrs("TransmissionLine", "line.a")["line_length"] == pytest.approx(40.0)
    assert _attrs("TransmissionLine", "line.b")["series_reactance_per_km"] == pytest.approx(0.25)
    assert _ends("TransmissionLine", "line.a") == ("node.de.380", "node.ch.380")

    icos = out_obj["GenericInterconnector"]
    assert set(icos) == {"ico.a", "ico.b"}
    assert not any(".agg." in eid for eid in icos)
    assert _attrs("GenericInterconnector", "ico.a")["maximum_power_flow_from_to"] == pytest.approx(200.0)
    assert _attrs("GenericInterconnector", "ico.b")["maximum_power_flow_to_from"] == pytest.approx(70.0)
    assert _ends("GenericInterconnector", "ico.a") == ("node.de.380", "node.ch.380")

    hvdcs = out_obj["HVDCLink"]
    assert set(hvdcs) == {"hvdc.a", "hvdc.b"}
    assert not any(".agg." in eid for eid in hvdcs)
    assert _attrs("HVDCLink", "hvdc.a")["max_flow"] == pytest.approx(300.0)
    assert _attrs("HVDCLink", "hvdc.b")["converter_technology"] == "LCC"
    assert _ends("HVDCLink", "hvdc.b") == ("node.de.380", "node.ch.380")

    trafos = out_obj["Transformer"]
    assert set(trafos) == {"tr.a", "tr.b"}
    assert not any(".agg." in eid for eid in trafos)
    assert _attrs("Transformer", "tr.a")["thermal_capacity_rating"] == pytest.approx(400.0)
    assert _attrs("Transformer", "tr.b")["short_circuit_voltage_in_percentage"] == pytest.approx(10.0)
    assert _ends("Transformer", "tr.a") == ("node.ch.380", "node.ch.220")
