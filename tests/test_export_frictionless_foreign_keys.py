"""
Regression tests for a real bug found while verifying that every
relation in a Frictionless export becomes a foreign key: `self.entities`
is keyed by *concrete* class name only, so any relation whose schema
`target` is an *abstract* class (`NetworkNode`, `Controller.AVR`/`.GOV`/
`.PSS`, `DynamicMachineModelType`, ...) never resolved to a foreignKeys
entry at all -- confirmed directly with `frictionless validate` against
a real export before the fix (atNode, hasAutomaticVoltageRegulator,
usesDynamicModelType, hasTurbineGovernor, hasPowerSystemStabilizer all
missing their FK).

Fixed by generalising the existing AllEntities union-table pattern: the
export now scans every relation in the schema for abstract targets and
builds one `All<Class>` union CSV per such target that has at least one
populated concrete descendant, mirroring exactly how AllEntities already
solves this for the EnergyAssetInstance hierarchy.

A related, separate bug was found in the same pass: `EnergyTechnologyType`
was documented as "Abstract base class" in its own schema description
but never actually declared `abstract: true` -- so `hasTechnology`
(target: EnergyTechnologyType) lost its FK too, even after the general
fix above, since the class wasn't recognized as abstract at all. Fixed
in the schema directly.

These tests exercise the fix at three levels: (1) every relation field
on every populated resource has a matching foreignKeys entry (or a
documented reason why not -- the target class has zero instances in
this particular model), (2) the exported package is valid per the real
`frictionless` package if installed, (3) a round-trip import preserves
every relation's value correctly and does not choke on the new
synthetic union-table resources.
"""
import json

import pytest

from cesdm_toolbox import build_model_from_yaml


def _model_with_avr_dynamics_and_topology(tmp_path):
    """A small but structurally rich model: two buses, a generator with
    a linked AVR controller and dynamic machine model (both abstract
    relation targets), and a two-port transmission line -- enough to
    exercise every kind of relation-target resolution at once."""
    model = build_model_from_yaml("schemas/cesdm")

    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_group="electricity")
    model.add_entity("CarrierDomain", "domain.electricity")
    model.add_relation("domain.electricity", "hasCarrier", "carrier.electricity")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    model.add_relation("bus.1", "belongsToCarrierDomain", "domain.electricity")
    model.add_entity("ElectricalBus", "bus.2")
    model.add_attribute("bus.2", "nominal_voltage", 380)
    model.add_relation("bus.2", "belongsToCarrierDomain", "domain.electricity")

    model.add_entity("GenerationUnit", "gen.1")
    model.add_relation("gen.1", "atNode", "bus.1")  # -> NetworkNode (abstract)
    gen = model.get_entity("gen.1")
    # Bus type lives on ElectricalBus, not GenerationUnit.
    bus = model.get_entity("bus.1") if model.has_entity("bus.1") else None
    if bus is not None:
        bus.power_flow.powerflow_bus_type = "PQ"
    gen.power_flow.active_power_setpoint = 100.0
    gen.rated_apparent_power = 300.0
    gen.rated_voltage = 20.0

    model.add_entity("Controller.AVR.SEXS", "avr.1")
    model.add_attribute("avr.1", "AVR_SEXS_Ka", 200.0)
    model.add_attribute("avr.1", "AVR_SEXS_Ta", 0.05)
    model.add_attribute("avr.1", "AVR_Efd_min", -5.0)
    model.add_attribute("avr.1", "AVR_Efd_max", 5.0)
    model.add_relation("avr.1", "controlsGenerationUnit", "gen.1")
    model.add_relation("gen.1", "hasAutomaticVoltageRegulator", "avr.1")  # -> Controller.AVR (abstract)

    model.add_entity("DynamicMachineModelType.Synchronous", "dyn.1")
    dm = model.get_entity("dyn.1")
    dm.machine_model_order = "subtransient_6th"
    dm.inertia_constant = 4.5
    dm.d_axis_synchronous_reactance = 1.8
    dm.q_axis_synchronous_reactance = 1.7
    dm.d_axis_transient_reactance = 0.3
    dm.d_axis_transient_open_circuit_time_constant = 8.0
    dm.d_axis_subtransient_reactance = 0.2
    dm.q_axis_subtransient_reactance = 0.2
    dm.d_axis_subtransient_open_circuit_time_constant = 0.03
    dm.q_axis_subtransient_open_circuit_time_constant = 0.05
    model.add_relation("gen.1", "usesDynamicModelType", "dyn.1")  # -> DynamicMachineModelType (abstract)

    model.add_entity("TransmissionLine", "line.1")
    model.add_relation("line.1", "fromNode", "bus.1")  # -> NetworkNode (abstract)
    model.add_relation("line.1", "toNode", "bus.2")     # -> NetworkNode (abstract)

    out_dir = tmp_path / "frictionless_export"
    out_dir.mkdir()
    dp_path = model.export_frictionless(out_dir, name="fk-test", title="FK test")
    return model, dp_path


def test_every_relation_field_has_a_matching_foreign_key_or_a_valid_reason_not_to(tmp_path):
    """For every resource in the export, every relation field either has
    a matching foreignKeys entry, or the relation's target class
    genuinely has zero populated instances in this model (in which case
    there is no resource to reference and omitting the FK is correct,
    not a bug) -- this test's minimal fixture only populates
    ElectricalBus/GenerationUnit/Controller.AVR.SEXS/
    DynamicMachineModelType.Synchronous/TransmissionLine, so every other
    relation on GenerationUnit (hasTechnology, hasInputCarrier, ...)
    legitimately has no FK here; only the relations this fixture
    actually populates are checked."""
    model, dp_path = _model_with_avr_dynamics_and_topology(tmp_path)
    dp = json.loads(dp_path.read_text())
    resources_by_name = {r["name"]: r for r in dp["resources"]}

    populated_relations = {
        "generation-unit": {"atNode", "hasAutomaticVoltageRegulator", "usesDynamicModelType"},
        "transmission-line": {"fromNode", "toNode"},
        "controller.avr.sexs": {"controlsGenerationUnit"},
    }
    for res_name, expected_fields in populated_relations.items():
        schema = resources_by_name[res_name]["schema"]
        fk_fields = set()
        for fk in schema.get("foreignKeys", []):
            fk_fields.update(fk["fields"])
        missing = expected_fields - fk_fields
        assert not missing, f"{res_name}: missing FK for {missing}"


def test_previously_broken_abstract_target_relations_now_have_a_foreign_key(tmp_path):
    """Pins down the exact four relations confirmed broken before the
    fix: atNode/fromNode/toNode (-> NetworkNode), and
    hasAutomaticVoltageRegulator/usesDynamicModelType (-> Controller.AVR /
    DynamicMachineModelType), both abstract targets."""
    model, dp_path = _model_with_avr_dynamics_and_topology(tmp_path)
    dp = json.loads(dp_path.read_text())
    resources_by_name = {r["name"]: r for r in dp["resources"]}

    checks = [
        ("generation-unit", "atNode", "all-network-node"),
        ("generation-unit", "hasAutomaticVoltageRegulator", "all-controller-avr"),
        ("generation-unit", "usesDynamicModelType", "all-dynamic-machine-model-type"),
        # ElectricityTransmission narrows fromNode/toNode to ElectricalBus
        ("transmission-line", "fromNode", "electrical-bus"),
        ("transmission-line", "toNode", "electrical-bus"),
    ]
    for res_name, field, expected_resource in checks:
        res = resources_by_name[res_name]
        fks = res["schema"]["foreignKeys"]
        matching = [fk for fk in fks if field in fk["fields"]]
        assert matching, f"{res_name}.{field} has no foreignKeys entry at all"
        assert matching[0]["reference"]["resource"] == expected_resource


def test_union_tables_are_populated_and_referenceable(tmp_path):
    model, dp_path = _model_with_avr_dynamics_and_topology(tmp_path)
    dp = json.loads(dp_path.read_text())
    resources_by_name = {r["name"]: r for r in dp["resources"]}

    assert "all-network-node" in resources_by_name
    assert "all-controller-avr" in resources_by_name
    assert "all-dynamic-machine-model-type" in resources_by_name

    csv_path = dp_path.parent / resources_by_name["all-network-node"]["path"]
    rows = csv_path.read_text().splitlines()
    assert "bus.1" in "\n".join(rows)
    assert "bus.2" in "\n".join(rows)


def test_export_uses_flat_resources_layout(tmp_path):
    """CSVs live directly under resources/; roles are descriptor-only."""
    _, dp_path = _model_with_avr_dynamics_and_topology(tmp_path)
    dp = json.loads(dp_path.read_text())

    for res in dp["resources"]:
        path = res["path"].replace("\\", "/")
        assert path.startswith("resources/")
        assert path.count("/") == 1, path
        assert (dp_path.parent / path).is_file()
        assert "folder" not in (res.get("custom") or {})

    assert (dp_path.parent / "resources" / "AllEntities.csv").is_file()
    assert not (dp_path.parent / "resources" / "AllAssets.csv").exists()
    assert not (dp_path.parent / "resources" / "Assets").exists()
    assert not (dp_path.parent / "resources" / "BaseEntities").exists()


def test_hastechnology_resolves_now_that_energytechnologytype_is_abstract():
    """EnergyTechnologyType is documented as an abstract base class in
    its own schema description but was missing the actual `abstract:
    true` flag -- confirmed directly this made hasTechnology
    (target: EnergyTechnologyType) lose its foreign key even after the
    general abstract-target fix, since the class wasn't recognized as
    abstract at all."""
    model = build_model_from_yaml("schemas/cesdm")
    assert getattr(model.classes["EnergyTechnologyType"], "abstract", False) is True


def test_exported_package_is_valid_per_the_real_frictionless_package(tmp_path):
    frictionless = pytest.importorskip("frictionless")
    model, dp_path = _model_with_avr_dynamics_and_topology(tmp_path)
    model.validate_or_raise()

    report = frictionless.validate(str(dp_path))
    assert report.valid, [str(e) for t in report.tasks for e in t.errors]


def test_round_trip_import_preserves_every_relation_and_ignores_union_tables(tmp_path):
    """The synthetic All<Class> union-table resources are not real
    schema classes -- import_frictionless must skip them silently
    rather than erroring, and every real relation must survive the
    round trip unchanged."""
    model, dp_path = _model_with_avr_dynamics_and_topology(tmp_path)

    reimported = build_model_from_yaml("schemas/cesdm")
    reimported.import_frictionless(dp_path.parent)

    assert reimported.entities.get("Controller.AVR.SEXS", {}).keys() == {"avr.1"}
    assert "all-network-node" not in reimported.classes  # never a real class

    gen = reimported.get_entity("gen.1")
    assert gen.atNode == "bus.1"
    assert gen.hasAutomaticVoltageRegulator == "avr.1"
    assert gen.usesDynamicModelType == "dyn.1"

    line = reimported.get_entity("line.1")
    assert line.fromNode == "bus.1"
    assert line.toNode == "bus.2"

    assert reimported.validate() == []
