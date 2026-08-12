"""
Model.summary() -- the "let me see what's in this model" explorer
method, deferred in the original API-ergonomics proposal, built here
as the minimal version: asset counts, rolled up by top-level family by
default (HydroGenerationUnit counted under GenerationUnit), with a
detailed=True escape hatch and an as_dict=True programmatic form.
"""

from cesdm_toolbox import build_model_from_yaml


def _populated_model():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")
    model.add_entity("EnergySystemModel", "sys1")
    model.add_entity("ElectricalBus", "bus.1")
    model.add_attribute("bus.1", "nominal_voltage", 380)
    model.add_entity("ElectricalBus", "bus.2")
    model.add_attribute("bus.2", "nominal_voltage", 380)

    model.add_entity("GenerationUnit", "gen.summary.1")
    model.add_relation("gen.summary.1", "hasTechnology", "Generation.Thermal.Gas.CCGT.Existing")
    model.add_relation("gen.summary.1", "atNode", "bus.1")

    model.add_entity("GenerationUnit", "gen.summary.2")
    model.add_relation("gen.summary.2", "hasTechnology", "Generation.Renewable.Wind.Onshore")
    model.add_relation("gen.summary.2", "atNode", "bus.1")

    model.add_entity("HydroGenerationUnit", "gen.summary.3")
    model.add_relation("gen.summary.3", "hasTechnology", "Generation.Renewable.Hydro.Reservoir")
    model.add_relation("gen.summary.3", "atNode", "bus.2")

    model.add_entity("DemandUnit", "dem.summary.1")
    model.add_relation("dem.summary.1", "atNode", "bus.1")

    model.add_entity("StorageUnit", "stor.summary.1")
    model.add_relation("stor.summary.1", "atNode", "bus.1")

    model.add_entity("TransmissionLine", "line.summary.1")
    model.add_relation("line.summary.1", "fromNode", "bus.1")
    model.add_relation("line.summary.1", "toNode", "bus.2")
    return model


def test_summary_default_rolls_up_subclasses():
    model = _populated_model()
    counts = model.summary(as_dict=True)
    assert counts["GenerationUnit"] == 3  # 2 GenerationUnit + 1 HydroGenerationUnit
    assert "HydroGenerationUnit" not in counts  # rolled up, not separate


def test_summary_detailed_keeps_subclasses_separate():
    model = _populated_model()
    counts = model.summary(detailed=True, as_dict=True)
    assert counts["GenerationUnit"] == 2
    assert counts["HydroGenerationUnit"] == 1


def test_summary_excludes_non_asset_entities():
    """GeneratorType, EnergySystemModel, ElectricalBus (a domain node,
    not role=="asset"), and standalone Controller/Result entities must
    not appear in the counts -- only role=="asset" classes count."""
    model = _populated_model()
    model.add_entity("Controller.AVR.SEXS", "avr.summary.1")
    model.add_relation("avr.summary.1", "controlsGenerationUnit", "gen.summary.1")
    model.add_entity("DispatchRunRecord", "run.summary.1")
    model.add_entity("GenerationUnit.DispatchResult", "res.summary.1")
    model.add_relation("res.summary.1", "reportsOn", "gen.summary.1")
    model.add_relation("res.summary.1", "hasRunRecord", "run.summary.1")

    counts = model.summary(as_dict=True)
    assert "GeneratorType" not in counts
    assert "EnergySystemModel" not in counts
    assert "Controller.AVR.SEXS" not in counts
    assert "GenerationUnit.DispatchResult" not in counts
    assert "DispatchRunRecord" not in counts


def test_summary_string_form_is_formatted_and_sorted_by_count_desc():
    model = _populated_model()
    text = model.summary()
    assert isinstance(text, str)
    lines = text.splitlines()
    counts = [int(line.split()[-1]) for line in lines]
    assert counts == sorted(counts, reverse=True)


def test_summary_empty_model():
    model = build_model_from_yaml("schemas/cesdm")
    assert model.summary() == "(no assets in this model)"
    assert model.summary(as_dict=True) == {}


def test_summary_total_matches_manual_count():
    model = _populated_model()
    counts = model.summary(as_dict=True)
    assert sum(counts.values()) == 6  # 3 generators + 1 demand + 1 storage + 1 line
