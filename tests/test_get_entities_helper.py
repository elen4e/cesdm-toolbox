"""Tests for Model.get_entities / ear.helpers.get_entities."""

from __future__ import annotations

from pathlib import Path

import pytest
import warnings

from ear import build_model_from_yaml, get_entities
from ear.entity import Entity

ROOT = Path(__file__).resolve().parent.parent


def test_model_get_entities_returns_class_store():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    bus_a = model.add_entity("ElectricalBus", "bus.a")
    bus_b = model.add_entity("ElectricalBus", "bus.b")
    model.add_entity("GenerationUnit", "gen.a")

    ents = model.get_entities("ElectricalBus")
    assert set(ents) == {"bus.a", "bus.b"}
    assert ents["bus.a"] is bus_a
    assert ents["bus.b"] is bus_b
    assert all(isinstance(e, Entity) for e in ents.values())


def test_helper_get_entities_delegates_to_model():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    bus = model.add_entity("ElectricalBus", "bus.a")
    assert get_entities(model, "ElectricalBus") is model.get_entities("ElectricalBus")
    assert get_entities(model, "ElectricalBus")["bus.a"] is bus


def test_get_entities_empty_for_known_class_without_instances():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ents = model.get_entities("ElectricalBus")
    assert ents == {}
    assert caught == []


def test_get_entities_warns_for_unknown_class():
    model = build_model_from_yaml(str(ROOT / "schemas/cesdm"))
    with pytest.warns(UserWarning, match="unknown entity class 'NotARealClass'"):
        ents = model.get_entities("NotARealClass")
    assert ents == {}
