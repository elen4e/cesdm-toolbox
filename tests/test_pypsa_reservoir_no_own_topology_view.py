"""
tools/import_pypsa.py gave every PyPSA storage_unit/store its own
SinglePort.TopologyView unconditionally, before checking whether it
was hydro/PHS storage -- which then also got a *second*,
paired HydroGenerationUnit with its own topology view via
_ensure_hydro_reservoir_composite(). The result: a hydro/PHS
reservoir ended up with two separate electrical connections to the
same bus for what CESDM models as one physical asset (only the
generator should carry the connection; the reservoir is a water/
energy-storage concept, connected to the network only through its
paired generator) -- reported directly, confirmed by inspecting the
exact PyPSA-imported YAML the report was based on.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("numpy")

# import_pypsa imports pypsa and h5py at module load; neither is needed
# for the helper functions exercised here.
sys.modules.setdefault("pypsa", types.SimpleNamespace(Network=object))
sys.modules.setdefault("h5py", types.SimpleNamespace())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from cesdm_toolbox import build_model_from_yaml

from import_pypsa import (
    _is_reservoir_hydro_storage,
    _is_pumped_hydro_storage,
    _ensure_hydro_reservoir_composite,
    _hydro_generator_id,
)


@pytest.mark.parametrize("carrier", ["PHS", "phs", "pumped hydro", "reservoir", "hydro", "dam", "pondage"])
def test_is_reservoir_hydro_storage_covers_phs_and_plain_reservoirs(carrier):
    """The guard added around _ensure_nodal_view() relies on this
    correctly covering PHS, not just plain reservoir hydro -- if it
    didn't, PHS reservoirs would still incorrectly get their own
    topology view."""
    assert _is_reservoir_hydro_storage(carrier) is True


def test_is_pumped_hydro_storage_recognizes_phs():
    assert _is_pumped_hydro_storage("PHS") is True
    assert _is_pumped_hydro_storage("battery") is False


def test_hydro_reservoir_composite_gives_generator_not_reservoir_the_topology_view():
    """_ensure_hydro_reservoir_composite() itself only ever attaches a
    SinglePort.TopologyView to the generator it creates -- confirming
    the reservoir-side fix (skip the *separate* unconditional
    _ensure_nodal_view() call in the storage_units/stores loops for
    hydro/PHS storage) is correct: nothing else in the pairing
    function gives the reservoir a connection of its own."""
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    model.import_library(str(ROOT / "library" / "default_library"))

    model.add_entity("GeographicalRegion", "nuts3.de111")
    model.add_attribute("nuts3.de111", "name", "DE region")
    model.add_entity("ElectricalBus", "node.de111.380")
    model.add_attribute("node.de111.380", "nominal_voltage", 380)
    model.add_relation("node.de111.380", "belongsToGeographicalRegion", "nuts3.de111")
    bus = "node.de111.380"

    reservoir_id = "storage.phs.01.de111.380"
    model.add_entity("HydraulicStorageUnit", reservoir_id)
    model.add_attribute(reservoir_id, "name", reservoir_id)

    gen_id = _ensure_hydro_reservoir_composite(
        model, reservoir_id=reservoir_id, bus_id=bus,
        power_capacity=200.0, resource_potential=None, is_reversible=True,
    )

    assert gen_id == _hydro_generator_id(reservoir_id)

    assert model.get_relation_targets(gen_id, "atNode") == [bus]
    assert model.get_relation_targets(reservoir_id, "atNode") == []

    # The pairing relations themselves are still correctly set.
    gen_ent = model.entities["HydroGenerationUnit"][gen_id]
    assert gen_ent.data.get("drawsFromHydraulicStorage") == reservoir_id
    res_ent = model.entities["HydraulicStorageUnit"][reservoir_id]
    assert "suppliesResourceTo" not in (res_ent.data or {})
