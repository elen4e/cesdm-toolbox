from ear.entity import Entity


class _ModelStub:
    def get_relation_targets(self, entity_id, relation_name):
        assert entity_id == "asset.1"
        return {"atNode": ["bus.1"], "connectedTo": ["a", "b"]}.get(relation_name, [])


def test_get_attr_value_unwraps_attribute_value():
    entity = Entity("GenerationUnit", "asset.1", {"nominal_power_capacity": {"value": 250.0, "unit": "MW"}})
    assert entity.get_attr_value("nominal_power_capacity") == 250.0
    assert entity.get_attr_value("missing", 7.0) == 7.0


def test_get_relation_for_flat_entity_data():
    entity = Entity("GenerationUnit", "asset.1", {"atNode": "bus.1", "connectedTo": ["a", "b"]})
    assert entity.get_relation("atNode") == "bus.1"
    assert entity.get_relations("connectedTo") == ["a", "b"]
    assert entity.get_relation("missing") is None


def test_get_relation_delegates_to_owning_model():
    entity = Entity("GenerationUnit", "asset.1", {}, _model=_ModelStub())
    assert entity.get_relation("atNode") == "bus.1"
    assert entity.get_relations("connectedTo") == ["a", "b"]
