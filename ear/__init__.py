"""ear — generic Entity-Attribute-Relation (EAR) modelling engine.

Domain-agnostic: knows nothing about energy systems. See ``cesdm`` for
the energy-system domain layer built on top of this package.

This package replaces the legacy single-file ``ear_toolbox.py``. The
top-level ``ear_toolbox.py`` module is kept as a thin backward-compatible
shim that re-exports everything from here.
"""

from ear.constraint import Constraint
from ear.relation_def import RelationDef
from ear.attribute_def import AttributeDef, AttributeValueDict, attributevalue_representer
from ear.entity_class import EntityClass
from ear.entity import Entity
from ear.model import Model
from ear.helpers import (
    build_model_from_yaml,
    get_entities,
    safe_set_attr,
    safe_add_ref,
    get_attr_value,
    get_attr_value_unit_prov,
    slugify,
)

__all__ = [
    "Constraint", "RelationDef", "AttributeDef", "AttributeValueDict",
    "attributevalue_representer", "EntityClass", "Entity", "Model",
    "build_model_from_yaml", "get_entities", "safe_set_attr", "safe_add_ref",
    "get_attr_value", "get_attr_value_unit_prov", "slugify",
]
