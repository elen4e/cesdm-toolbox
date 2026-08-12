"""Cleaned-up GeneratorType ids are canonical; legacy ids are absent."""
from __future__ import annotations

from cesdm.default_library import GeneratorTypes
from cesdm.helpers import build_model_from_yaml


def test_canonical_library_ids_present_legacy_absent():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")
    assert model.entity_class(GeneratorTypes.GENERATION_NUCLEAR_LWR) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_OTHER_ADEQUACY) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_OTHER_DEMANDRESPONSE) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_OTHER_SUPPLY_GAS) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_ROOFTOP) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_RENEWABLE_SOLAR_THERMAL) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_HYDROGEN_FUELCELL) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_HYDROGEN_CCGT) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_THERMAL_GAS_CCGT_EXISTING) == "GeneratorType"
    assert model.entity_class(GeneratorTypes.GENERATION_THERMAL_COAL_HARDCOAL_EXISTING) == "GeneratorType"
    # Legacy taxonomy ids are not in the library and are not remapped.
    assert model.entity_class("Generation.Thermal.Nuclear.Standard") is None
    assert model.entity_class("Generation.Adequacy") is None
    assert model.entity_class("Generation.DemandResponse") is None
    assert model.entity_class("Supply.Gas") is None
    assert model.entity_class("Generation.Renewable.Solar.PV") is None
    assert model.entity_class("Generation.Thermal.Hydrogen.CCGT") is None
    assert model.entity_class("Generation.Thermal.Gas.CCGT.Present2") is None
    assert model.entity_class("Generation.Thermal.Coal.HardCoal.Old1") is None
    assert model.entity_class("Generation.Thermal.OilShale.Standard.Old") is None
