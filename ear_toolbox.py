"""ear_toolbox — backward-compatible shim.

The generic EAR engine was split into the ``ear`` package as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
This module re-exports the same public API from its new location so
existing ``from ear_toolbox import ...`` imports keep working.

New code should import from ``ear`` directly.
"""

from ear import (
    Constraint,
    RelationDef,
    AttributeDef,
    AttributeValueDict,
    attributevalue_representer,
    EntityClass,
    Entity,
    Model,
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
