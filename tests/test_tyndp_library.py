"""default_library vs tyndp_library split."""
from __future__ import annotations

from cesdm.helpers import build_model_from_yaml


TYNDP_ONLY = [
    "Generation.Thermal.Coal.HardCoal.Old1",
    "Generation.Thermal.Coal.HardCoal.Old2",
    "Generation.Thermal.Gas.CCGT.Present1",
    "Generation.Thermal.Gas.CCGT.Present2",
    "Generation.Thermal.Gas.OCGT.Old",
    "Generation.Thermal.Oil.HeavyOil.Old1",
    "Generation.Thermal.OilShale.Standard.Old",
]

DEFAULT_CORE = [
    "Generation.Thermal.Coal.HardCoal.Existing",
    "Generation.Thermal.Gas.CCGT.Existing",
    "Generation.Thermal.Gas.CCGT.New",
    "Generation.Thermal.Oil.HeavyOil.Existing",
    "Generation.Hydrogen.CCGT",
]


def test_default_library_has_core_not_tyndp_vintages():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")
    for tid in DEFAULT_CORE:
        assert model.entity_class(tid) == "GeneratorType", tid
    for tid in TYNDP_ONLY:
        assert model.entity_class(tid) is None, tid


def test_tyndp_library_adds_vintages_after_default():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")
    model.import_library("library/tyndp_library")
    for tid in DEFAULT_CORE + TYNDP_ONLY:
        assert model.entity_class(tid) == "GeneratorType", tid
    # Distinct efficiencies preserved for Old1 vs Old2
    assert model.get_attribute_value(
        "Generation.Thermal.Coal.HardCoal.Old1", "energy_conversion_efficiency"
    ) == 0.35
    assert model.get_attribute_value(
        "Generation.Thermal.Coal.HardCoal.Old2", "energy_conversion_efficiency"
    ) == 0.4
    assert model.get_attribute_value(
        "Generation.Thermal.Gas.CCGT.Present2", "energy_conversion_efficiency"
    ) == 0.58


def test_import_tyndp_libraries_helper():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for p in (str(root), str(root / "examples"), str(root / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from example_import_tyndp import import_tyndp_libraries

    model = build_model_from_yaml("schemas/cesdm")
    import_tyndp_libraries(model)
    assert model.entity_class("Generation.Thermal.Gas.CCGT.Present2") == "GeneratorType"
    assert model.entity_class("carrier.electricity") == "Carrier"
