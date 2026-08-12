# EAR API Reference

!!! warning "Energy system modellers — start elsewhere"
    For day-to-day model building, use **`cesdm_toolbox`** and the [Proxy API guide](../guides/proxy-api.md).

    To look up classes, attributes, and relations, open the **[CESDM Schema Reference](schema-reference.html)** (interactive HTML) or the [Modeller cheat sheet](../getting-started/modeller-cheat-sheet.md).

    This page documents the low-level **`ear`** engine package used by integrators and contributors.

    ```python
    from cesdm_toolbox import build_model_from_yaml  # modellers
    from ear import Model, build_model_from_yaml     # engine-level (this page)
    ```

> The `ear` package provides the generic **Entity–Attribute–Relation (EAR)** engine used by CESDM — domain-independent: it knows how to load schemas, create entities, validate attributes and relations, and persist models, but contains no energy-system-specific concepts.

!!! note "Recommended import"

    New code should import directly from `ear`:

    ```python
    from ear import Model, build_model_from_yaml
    ```

    The legacy module `ear_toolbox.py` is retained only as a backward-compatible shim (`from ear_toolbox import Model, build_model_from_yaml`) — both currently expose the same public API, but `ear` is the preferred package.

## Contents

- [Public API](#public-api)
- [Creating a Model](#creating-a-model)
- [Core EAR Operations](#core-ear-operations)
- [Entity-oriented API](#entity-oriented-api)
- [Reading Model Data](#reading-model-data)
- [Model Accessors](#model-accessors)
- [Schema Loading and Introspection](#schema-loading-and-introspection)
- [Libraries](#libraries)
- [Validation](#validation)
- [YAML and JSON Persistence](#yaml-and-json-persistence)
- [CSV Import](#csv-import)
- [Frictionless Data Packages](#frictionless-data-packages)
- [Pydantic Export](#pydantic-export)
- [Schema Definition Classes](#schema-definition-classes)
- [Helper Functions](#helper-functions)
- [Function Index](#function-index)
- [Minimal Complete Example](#minimal-complete-example)
- [Recommended Usage](#recommended-usage)

## Public API

The top-level package exports:

```python
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
```

## Creating a Model

#### `Model()`

**Signature**

```python
Model()
```

Creates an empty in-memory EAR model. An empty model has no schema classes or entity instances — in most applications, use `build_model_from_yaml()` instead.

**Example**

```python
from ear import Model

model = Model()
```

---

#### `build_model_from_yaml()`

**Signature**

```python
build_model_from_yaml(
    schema_path: str | Path | Sequence[str | Path],
) -> Model
```

Loads one or more schema trees, resolves inheritance, and returns a ready-to-use model.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `schema_path` | `str \| Path \| Sequence[str \| Path]` | One schema directory, or an ordered list of them — a later path's classes can extend/reference an earlier one's. |

**Returns**

A ready-to-use `Model`.

**Example**

```python
from ear import build_model_from_yaml

model = build_model_from_yaml("schemas/cesdm")
```

Multiple schema roots can be loaded together:

```python
model = build_model_from_yaml(
    [
        "schemas/cesdm",
        "schemas/application_extension",
    ]
)
```

---

## Core EAR Operations

Every model instance is constructed using three core operations:

```python
model.add_entity(...)
model.add_attribute(...)
model.add_relation(...)
```

#### `Model.add_entity()`

**Signature**

```python
model.add_entity(
    entity_class: str,
    entity_id: str,
) -> Entity
```

Creates an entity of a schema-defined class. Schema defaults are applied automatically, except for group-dependent defaults that are resolved lazily.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `entity_class` | `str` | Name of a class defined in the loaded schema. |
| `entity_id` | `str` | Globally unique identifier for the new entity. |

**Returns**

The newly created `Entity`.

**Raises**

- `ValueError` if the class is unknown.
- `ValueError` if the identifier already exists anywhere in the model.

**Example**

```python
generator = model.add_entity(
    entity_class="GenerationUnit",
    entity_id="gen.ch.001",
)
```

---

#### `Model.add_attribute()`

**Signature**

```python
model.add_attribute(
    entity_id: str,
    attribute_id: str,
    value,
    unit: str | None = None,
    provenance_ref: str | None = None,
) -> Entity
```

Sets or replaces an attribute on an existing entity. The method verifies that the attribute exists on the entity class, coerces supported scalar types, checks enum/minimum/maximum/pattern/unit constraints, and stores the value together with optional unit and provenance metadata.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `entity_id` | `str` | Identifier of the entity to update. |
| `attribute_id` | `str` | Schema-defined attribute name. |
| `value` | — | Scalar value, or a complete attribute-value dictionary. |
| `unit` | `str \| None` | Optional unit. Must satisfy the schema's unit constraints. |
| `provenance_ref` | `str \| None` | Optional identifier of the value's source. |

**Returns**

The updated `Entity`.

**Example**

```python
model.add_attribute(
    entity_id="gen.ch.001",
    attribute_id="nominal_power_capacity",
    value=500.0,
    unit="MW",
    provenance_ref="source.dataset.2025",
)
```

An attribute may also be supplied as a complete dictionary:

```python
model.add_attribute(
    entity_id="gen.ch.001",
    attribute_id="nominal_power_capacity",
    value={
        "value": 500.0,
        "unit": "MW",
        "provenance_ref": "source.dataset.2025",
    },
)
```

---

#### `Model.add_relation()`

**Signature**

```python
model.add_relation(
    entity_id: str,
    relation_id: str,
    target_entity_id: str,
    **kwargs,
) -> Entity
```

Creates a schema-defined relation from one entity to another. The method validates that the relation exists on the source class, that the target entity exists, that the target class is permitted, and relation cardinality and other schema constraints.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `entity_id` | `str` | Source entity identifier. |
| `relation_id` | `str` | Schema-defined relation name. |
| `target_entity_id` | `str` | Target entity identifier. |
| `**kwargs` | — | Backward-compatible aliases accepted by the implementation. |

**Returns**

The updated `Entity`.

**Example**

```python
model.add_relation(
    entity_id="gen.ch.001",
    relation_id="atNode",
    target_entity_id="bus.ch.001",
)
```

---

## Entity-oriented API

`Model.add_entity()` returns an `Entity` that provides equivalent object-oriented methods:

```python
generator = model.add_entity(
    entity_class="GenerationUnit",
    entity_id="gen.ch.001",
)

generator.add_attribute(
    attribute_id="nominal_power_capacity",
    value=500.0,
    unit="MW",
    provenance_ref=None,
)

generator.add_relation(
    relation_id="atNode",
    target_entity_id="bus.ch.001",
)
```

#### `Entity.add_attribute()`

**Signature**

```python
entity.add_attribute(
    attribute_id: str,
    value,
    *,
    unit: str | None = None,
    provenance_ref: str | None = None,
) -> Entity
```

Delegates to `Model.add_attribute()` and returns the entity, allowing chained calls.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `attribute_id` | `str` | Schema-defined attribute name. |
| `value` | — | Scalar value, or a complete attribute-value dictionary. |
| `unit` | `str \| None` | Optional unit. |
| `provenance_ref` | `str \| None` | Optional identifier of the value's source. |

**Returns**

`self` (the same `Entity`), to allow chaining.

**Example**

```python
generator.add_attribute(
    "name",
    "Generator 1",
).add_relation(
    "atNode",
    "bus.ch.001",
)
```

---

#### `Entity.add_relation()`

**Signature**

```python
entity.add_relation(
    relation_id: str,
    target_entity_id,
    **kwargs,
) -> Entity
```

Delegates to `Model.add_relation()`. Entities constructed manually without an owning model cannot use these write methods.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `relation_id` | `str` | Schema-defined relation name. |
| `target_entity_id` | `str` | Target entity identifier. |
| `**kwargs` | — | Backward-compatible aliases accepted by the implementation. |

**Returns**

`self` (the same `Entity`), to allow chaining.

---

## Reading Model Data

#### `Entity.get_attr_value()`

**Signature**

```python
entity.get_attr_value(
    name: str,
    default=None,
)
```

Returns the scalar value of an attribute. Unit and provenance metadata are not returned.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Attribute name. |
| `default` | — | Value returned if the attribute is unset. |

**Returns**

The attribute's scalar value, or `default`.

**Example**

```python
capacity = generator.get_attr_value(
    "nominal_power_capacity",
    default=0.0,
)
```

---

#### `Entity.get_relation()`

**Signature**

```python
entity.get_relation(
    name: str,
    default=None,
)
```

Returns the first relation target, or `default`.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Relation name. |
| `default` | — | Value returned if the relation has no target. |

**Returns**

The first target id, or `default`.

**Example**

```python
node_id = generator.get_relation("atNode")
```

---

#### `Entity.get_relations()`

**Signature**

```python
entity.get_relations(
    name: str,
) -> list[str]
```

Returns all targets of a relation. Missing relations return an empty list.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Relation name. |

**Returns**

`list[str]` — every target id, in order. Empty if none.

**Example**

```python
controller_ids = generator.get_relations("controlledBy")
```

---

## Model Accessors

### Entity lookup

```python
model.entity_class(entity_id: str)
model.entity_data(entity_id: str)
model.has_entity(entity_id: str)
model.get_entities(entity_class: str)
```

| Method | Type | Result |
|---|---|---|
| `entity_class(entity_id)` | `str \| None` | The class name of an entity. |
| `entity_data(entity_id)` | `dict` | The entity's internal data mapping. |
| `has_entity(entity_id)` | `bool` | Whether an entity identifier exists. |
| `get_entities(entity_class)` | `dict[str, Entity]` | All instances of a class. Warns and returns `{}` if the class is unknown. |

---

### Schema field lookup

```python
model.class_attributes(class_name: str)
model.class_relations(class_name: str)
model.field_allowed(entity_or_class: str, field_id: str)
```

| Method | Type | Result |
|---|---|---|
| `class_attributes(class_name)` | `dict` | Inherited attribute definitions for a class. |
| `class_relations(class_name)` | `dict` | Inherited relation definitions for a class. |
| `field_allowed(entity_or_class, field_id)` | `bool` | Whether an attribute or relation is valid for the entity/class. |

These methods inspect inherited schema fields.

---

### Generic value access

```python
model.get_attribute_value(
    entity_id: str,
    attribute_id: str,
    default=None,
)

model.get_relation_targets(
    entity_id: str,
    relation_id: str,
)
```

| Method | Type | Result |
|---|---|---|
| `get_attribute_value(entity_id, attribute_id, default=None)` | — | Scalar attribute value, or `default`. |
| `get_relation_targets(entity_id, relation_id)` | `list[str]` | All targets. Always a list, even if empty. |

---

### Conditional writes

```python
model.set_attribute_if_allowed(
    entity_id: str,
    attribute_id: str,
    value,
    unit: str | None = None,
    *,
    strict: bool = False,
)

model.add_relation_if_allowed(
    entity_id: str,
    relation_id: str,
    target_id: str,
    *,
    strict: bool = False,
)
```

| Method | Type | Result |
|---|---|---|
| `set_attribute_if_allowed(entity_id, attribute_id, value, unit=None, *, strict=False)` | `bool` | Writes the attribute only if permitted by the schema. |
| `add_relation_if_allowed(entity_id, relation_id, target_id, *, strict=False)` | `bool` | Writes the relation only if permitted by the schema. |

These methods write a field only when it is permitted by the entity schema — useful for generic importers that operate across several entity classes.

- With `strict=False`, unsupported fields are skipped.
- With `strict=True`, unsupported fields raise an error.

---

## Schema Loading and Introspection

#### `Model.load_classes_from_yaml()`

**Signature**

```python
model.load_classes_from_yaml(
    path: str | Path | Sequence[str | Path],
)
```

Loads schema definitions from one or more paths. For normal usage, `build_model_from_yaml()` performs this whole workflow automatically.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `path` | `str \| Path \| Sequence[str \| Path]` | One schema directory/file, or an ordered list of them. |

**Example**

After loading schemas manually, resolve inheritance:

```python
model.resolve_inheritance()
```

---

### Inheritance and indexes

```python
model.resolve_inheritance()
model.build_class_indexes()
model.build_inheritance_map(schema_dir)
```

| Method | Result |
|---|---|
| `resolve_inheritance()` | Materialises each class's own attributes/relations plus everything inherited. |
| `build_class_indexes()` | (Re)builds internal lookup indexes over the loaded classes. |
| `build_inheritance_map(schema_dir)` | Builds a class-name → parent-list map directly from a schema directory. |

---

### Schema inspection

```python
model.class_defs()
model.get_attributes_grouped(class_name)
model.unit_info(symbol)
model.debug_schema()
model.format_class_tree()
model.print_class_tree()
model.format_attribute_tree(groups)
model.print_attribute_tree(groups)
```

| Method | Result |
|---|---|
| `class_defs()` | All loaded `EntityClass` definitions. |
| `get_attributes_grouped(class_name)` | A class's attributes grouped by `belongsToGroup`. |
| `unit_info(symbol)` | Registry metadata for one unit symbol. |
| `debug_schema()` | A diagnostic dump of the loaded schema. |
| `format_class_tree()` / `print_class_tree()` | The class inheritance tree, as a string / printed directly. |
| `format_attribute_tree(groups)` / `print_attribute_tree(groups)` | A `get_attributes_grouped()` result, as a string / printed directly. |

**Example**

```python
print(model.format_class_tree())

groups = model.get_attributes_grouped(
    "GenerationUnit"
)
print(model.format_attribute_tree(groups))
```

---

### Class relationships

#### `model.is_class_derived_from()`

**Signature**

```python
model.is_class_derived_from(
    subclass_name: str,
    parent_name: str,
    inheritance,
)
```

Returns whether one schema class inherits from another.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `subclass_name` | `str` | Candidate subclass name. |
| `parent_name` | `str` | Candidate parent/ancestor class name. |
| `inheritance` | — | The inheritance map to check against. |

**Returns**

`bool`

---

## Libraries

#### `Model.import_library()`

**Signature**

```python
model.import_library(
    library_yaml: str,
    *,
    namespace: str | None = None,
    conflict: str = "error",
)
```

Imports reusable entity instances from one YAML file or a directory of YAML files.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `library_yaml` | `str` | Path to a library YAML file or directory. |
| `namespace` | `str \| None` | Optional prefix for imported entity identifiers. |
| `conflict` | `str` | One of `"error"` / `"skip"` / `"overwrite"` — see below. |

| `conflict` value | Behaviour |
|---|---|
| `"error"` | Raise when an identifier already exists. |
| `"skip"` | Keep the existing entity. |
| `"overwrite"` | Replace existing entity data. |

**Example**

```python
model.import_library(
    "library/default_library",
)
```

---

## Validation

#### `Model.validate()`

**Signature**

```python
model.validate() -> list[str]
```

Validates the complete model against the loaded schemas — covers schema-defined attributes, relations, types, constraints, targets, and required fields.

**Returns**

`list[str]` — one message per validation error. Empty if the model is structurally valid.

**Example**

```python
errors = model.validate()

if errors:
    for error in errors:
        print(error)
```

---

#### Analysis-specific validation

**Signature**

```python
model.load_analysis_profile(path)
model.validate_for_analysis(profile)
model.validate_for_analysis_or_raise(profile)
```

Checks whether the model contains what a *specific analysis* needs, independent of schema-level validity. The raising variant throws `ValueError` when requirements are not satisfied.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `profile` | `dict \| str \| Path` | A loaded dictionary, a YAML file/directory path, or a bare profile name resolved as `analysis_profiles/<name>.yaml`. |

**Returns**

`validate_for_analysis()` returns `list[str]`; `validate_for_analysis_or_raise()` returns `None` (raises on failure).

**Raises**

- `ValueError` from `validate_for_analysis_or_raise()` when the model doesn't meet the profile's requirements.

**Example**

```python
errors = model.validate_for_analysis(
    "optimal_dispatch"
)
```

```python
model.validate_for_analysis_or_raise(
    "power_flow"
)
```

---

## YAML and JSON Persistence

#### Export

**Signature**

```python
model.export_yaml(path)
model.export_json(path)
```

**Example**

```python
model.export_yaml("model.yaml")
model.export_json("model.json")
```

---

#### Import

**Signature**

```python
model.import_yaml(
    path,
    *,
    strict_unknown: bool = False,
)

model.import_json(
    path,
    *,
    strict_unknown: bool = False,
)
```

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `path` | `str \| Path` | File to import. |
| `strict_unknown` | `bool` | If `True`, unknown classes or fields raise errors rather than being skipped. |

---

## CSV Import

**Signature**

```python
model.import_csv_by_class(
    dir_path,
    create_missing_refs: bool = False,
)

model.import_csv_by_class_wide(
    dir_path,
    create_missing_refs: bool = False,
)

model.import_csv_by_class_wide_meta(
    dir_path,
    create_missing_refs: bool = False,
    strict_unknown: bool = False,
)

model.import_long_csv(
    path,
    *,
    strict_unknown: bool = False,
)
```

These methods support different class-oriented and long-table CSV layouts.

| Method | Layout |
|---|---|
| `import_csv_by_class(dir_path, create_missing_refs=False)` | One CSV file per class, one row per entity. |
| `import_csv_by_class_wide(dir_path, create_missing_refs=False)` | Same, wide format (one column per attribute/relation). |
| `import_csv_by_class_wide_meta(dir_path, create_missing_refs=False, strict_unknown=False)` | Wide format with an additional metadata header. |
| `import_long_csv(path, *, strict_unknown=False)` | A single long-format CSV (one row per attribute/relation value). |

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dir_path` / `path` | `str \| Path` | Directory (per-class variants) or file (long variant) to import. |
| `create_missing_refs` | `bool` | If `True`, auto-create a placeholder entity for a referenced id that doesn't exist yet. |
| `strict_unknown` | `bool` | If `True`, unknown classes or fields raise errors rather than being skipped. |

---

## Frictionless Data Packages

!!! note "CESDM override"
    On `CesdmModel`, `export_frictionless` / `import_frictionless` add role annotations,
    flat `resources/` layout, the `AllEntities` index table, and optional library filtering.
    The signatures below describe that CESDM-aware API.

#### Export (Frictionless)

**Signature**

```python
model.export_frictionless(
    dir_path,
    *,
    name: str = "cesdm-model",
    title=None,
    description: str = "",
    version: str = "1.0.0",
    contributors=None,
    include_library: str = "referenced",
)
```

**Layout**

```text
<dir_path>/
  datapackage.json
  resources/
    AllEntities.csv      # universal FK index (entity_id, entity_class, name)
    GenerationUnit.csv
    ElectricalBus.csv
    …
```

CSVs are flat under `resources/`. Roles (`asset`, `domain`, `entity-index`, …) are
recorded only in `datapackage.json` (`custom.role`).

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dir_path` | `str \| Path` | Output directory for the data package. |
| `name` | `str` | Package name (defaults to `"cesdm-model"`). |
| `title` | `str \| None` | Human-readable package title. |
| `description` | `str` | Package description. |
| `version` | `str` | Package version string. |
| `contributors` | — | Optional contributor metadata. |
| `include_library` | `str` | `"none"` \| `"referenced"` \| `"all"` — how much library master data (Carrier, GeneratorType, …) to embed. Default `"referenced"`. |

**Example**

```python
model.export_frictionless(
    "output/frictionless",
    name="example-model",
    title="Example CESDM Model",
    version="1.0.0",
    include_library="referenced",
)
```

---

#### Import (Frictionless)

**Signature**

```python
model.import_frictionless(
    dir_path,
    *,
    skip_unknown_classes: bool = True,
    skip_unknown_fields: bool = True,
)
```

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dir_path` | `str \| Path` | Directory containing a `datapackage.json` and its resources. |
| `skip_unknown_classes` | `bool` | If `True`, silently skip rows for classes the schema doesn't define. |
| `skip_unknown_fields` | `bool` | If `True`, silently skip columns the schema doesn't define. |

Import accepts both the current flat `resources/*.csv` layout and older packages
that used `resources/Assets/`, `resources/BaseEntities/`, or `AllAssets.csv`.

---

## Pydantic Export

#### `Model.build_pydantic_models()`

**Signature**

```python
models = model.build_pydantic_models()
```

Builds Pydantic model classes from the loaded EAR schema definitions.

**Returns**

A mapping of class name to generated Pydantic model class.

---

## Schema Definition Classes

These classes represent parsed and resolved schema content.

#### `EntityClass`

**Signature**

```python
EntityClass(
    name: str,
    attributes: dict[str, AttributeDef],
    description: str = "",
    parents: str | list[str] | None = None,
    abstract: bool = False,
    relations: dict[str, RelationDef] = {},
    view_family: str | None = None,
)
```

A schema-level entity-class definition.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Class name. |
| `attributes` | `dict[str, AttributeDef]` | The class's own attribute definitions. |
| `description` | `str` | Human-readable description. |
| `parents` | `str \| list[str] \| None` | Parent class name(s), for inheritance. |
| `abstract` | `bool` | Whether the class can be instantiated directly. |
| `relations` | `dict[str, RelationDef]` | The class's own relation definitions. |
| `view_family` | `str \| None` | Optional linked-entity family (Controller/Result). |

**Example**

```python
EntityClass.from_dict(
    name: str,
    d: dict,
)
```

---

#### `AttributeDef`

Represents one schema-defined attribute, including identifier and description, data type, default value, unit definition, requiredness, constraints, and optional group assignment.

**Example**

```python
AttributeDef.from_dict(
    name: str,
    d: dict,
)
```

---

#### `RelationDef`

Represents one schema-defined relation, including permitted target classes, requiredness, cardinality, description, and optional group assignment. The compatibility property `target` returns the first permitted target when one exists.

**Example**

```python
RelationDef.from_dict(
    name: str,
    d: dict,
)
```

---

#### `Constraint`

Represents value constraints such as `enum`, `minimum`, `maximum`, and regular-expression patterns.

**Example**

```python
Constraint.from_dict(d)
```

---

#### `AttributeValueDict`

A dictionary wrapper used for stored attribute values.

**Example**

Typical structure:

```python
{
    "value": 500.0,
    "unit": "MW",
    "provenance_ref": "source.dataset.2025",
}
```

---

## Helper Functions

#### `get_entities()`

**Signature**

```python
get_entities(
    model: Model,
    entity_class: str,
) -> dict[str, Entity]
```

Returns the `{entity_id: Entity}` mapping for `entity_class`. Equivalent to
`model.get_entities(entity_class)`. If the class is not in the loaded schema,
emits a `UserWarning` (with optional close-match suggestions) and returns `{}`.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `model` | `Model` | Model to read from. |
| `entity_class` | `str` | Schema class name. |

---

#### `safe_set_attr()`

**Signature**

```python
safe_set_attr(
    model: Model,
    entity_id: str,
    attr: str,
    value,
)
```

Sets an attribute only when a non-empty value is provided and the schema allows it.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `model` | `Model` | The model to write to. |
| `entity_id` | `str` | Target entity identifier. |
| `attr` | `str` | Attribute name. |
| `value` | — | Value to set, if non-empty. |

---

#### `safe_add_ref()`

**Signature**

```python
safe_add_ref(
    model: Model,
    entity_id: str,
    ref_name: str,
    target_id: str | None,
)
```

Adds a relation only when a target identifier is provided.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `model` | `Model` | The model to write to. |
| `entity_id` | `str` | Source entity identifier. |
| `ref_name` | `str` | Relation name. |
| `target_id` | `str \| None` | Target entity identifier, if any. |

---

#### `get_attr_value()`

**Signature**

```python
get_attr_value(
    entity,
    name,
    default=None,
)
```

Returns the scalar value of an attribute from an entity-like object.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `entity` | — | An entity-like object (dict or `Entity`). |
| `name` | `str` | Attribute name. |
| `default` | — | Value returned if the attribute is unset. |

---

#### `get_attr_value_unit_prov()`

**Signature**

```python
get_attr_value_unit_prov(
    entity,
    name,
    default=None,
)
```

Returns attribute value, unit, and provenance information.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `entity` | — | An entity-like object (dict or `Entity`). |
| `name` | `str` | Attribute name. |
| `default` | — | Value returned if the attribute is unset. |

**Returns**

A `(value, unit, provenance_ref)` tuple.

---

#### `slugify()`

**Signature**

```python
slugify(s: str) -> str
```

Converts text into a normalized identifier-friendly string.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `s` | `str` | Text to convert. |

**Returns**

`str`

---

## Function Index

Every function and method on this page, for quick lookup.

| Name | Category |
|---|---|
| `Model()` | [Creating a Model](#creating-a-model) |
| `build_model_from_yaml()` | [Creating a Model](#creating-a-model) |
| `Model.add_entity()` | [Core EAR Operations](#core-ear-operations) |
| `Model.add_attribute()` | [Core EAR Operations](#core-ear-operations) |
| `Model.add_relation()` | [Core EAR Operations](#core-ear-operations) |
| `Entity.add_attribute()` | [Entity-oriented API](#entity-oriented-api) |
| `Entity.add_relation()` | [Entity-oriented API](#entity-oriented-api) |
| `Entity.get_attr_value()` | [Reading Model Data](#reading-model-data) |
| `Entity.get_relation()` | [Reading Model Data](#reading-model-data) |
| `Entity.get_relations()` | [Reading Model Data](#reading-model-data) |
| `Model.entity_class()` | [Model Accessors](#entity-lookup) |
| `Model.entity_data()` | [Model Accessors](#entity-lookup) |
| `Model.has_entity()` | [Model Accessors](#entity-lookup) |
| `Model.get_entities()` | [Model Accessors](#entity-lookup) |
| `Model.class_attributes()` | [Model Accessors](#schema-field-lookup) |
| `Model.class_relations()` | [Model Accessors](#schema-field-lookup) |
| `Model.field_allowed()` | [Model Accessors](#schema-field-lookup) |
| `Model.get_attribute_value()` | [Model Accessors](#generic-value-access) |
| `Model.get_relation_targets()` | [Model Accessors](#generic-value-access) |
| `Model.set_attribute_if_allowed()` | [Model Accessors](#conditional-writes) |
| `Model.add_relation_if_allowed()` | [Model Accessors](#conditional-writes) |
| `Model.load_classes_from_yaml()` | [Schema Loading and Introspection](#schema-loading-and-introspection) |
| `Model.resolve_inheritance()` | [Schema Loading and Introspection](#inheritance-and-indexes) |
| `Model.build_class_indexes()` | [Schema Loading and Introspection](#inheritance-and-indexes) |
| `Model.build_inheritance_map()` | [Schema Loading and Introspection](#inheritance-and-indexes) |
| `Model.class_defs()` | [Schema Loading and Introspection](#schema-inspection) |
| `Model.get_attributes_grouped()` | [Schema Loading and Introspection](#schema-inspection) |
| `Model.unit_info()` | [Schema Loading and Introspection](#schema-inspection) |
| `Model.debug_schema()` | [Schema Loading and Introspection](#schema-inspection) |
| `Model.format_class_tree()` / `print_class_tree()` | [Schema Loading and Introspection](#schema-inspection) |
| `Model.format_attribute_tree()` / `print_attribute_tree()` | [Schema Loading and Introspection](#schema-inspection) |
| `Model.is_class_derived_from()` | [Schema Loading and Introspection](#class-relationships) |
| `Model.import_library()` | [Libraries](#libraries) |
| `Model.validate()` | [Validation](#validation) |
| `Model.load_analysis_profile()` | [Validation](#analysis-specific-validation) |
| `Model.validate_for_analysis()` | [Validation](#analysis-specific-validation) |
| `Model.validate_for_analysis_or_raise()` | [Validation](#analysis-specific-validation) |
| `Model.export_yaml()` / `export_json()` | [YAML and JSON Persistence](#export) |
| `Model.import_yaml()` / `import_json()` | [YAML and JSON Persistence](#import) |
| `Model.import_csv_by_class()` | [CSV Import](#csv-import) |
| `Model.import_csv_by_class_wide()` | [CSV Import](#csv-import) |
| `Model.import_csv_by_class_wide_meta()` | [CSV Import](#csv-import) |
| `Model.import_long_csv()` | [CSV Import](#csv-import) |
| `Model.export_frictionless()` | [Frictionless Data Packages](#export-frictionless) |
| `Model.import_frictionless()` | [Frictionless Data Packages](#import-frictionless) |
| `Model.build_pydantic_models()` | [Pydantic Export](#pydantic-export) |
| `EntityClass` | [Schema Definition Classes](#schema-definition-classes) |
| `AttributeDef` | [Schema Definition Classes](#schema-definition-classes) |
| `RelationDef` | [Schema Definition Classes](#schema-definition-classes) |
| `Constraint` | [Schema Definition Classes](#schema-definition-classes) |
| `AttributeValueDict` | [Schema Definition Classes](#schema-definition-classes) |
| `get_entities()` | [Helper Functions](#helper-functions) |
| `safe_set_attr()` | [Helper Functions](#helper-functions) |
| `safe_add_ref()` | [Helper Functions](#helper-functions) |
| `get_attr_value()` | [Helper Functions](#helper-functions) |
| `get_attr_value_unit_prov()` | [Helper Functions](#helper-functions) |
| `slugify()` | [Helper Functions](#helper-functions) |

## Minimal Complete Example

```python
from ear import build_model_from_yaml

model = build_model_from_yaml(
    "schemas/example"
)

model.add_entity(
    entity_class="Node",
    entity_id="node.1",
)

model.add_attribute(
    entity_id="node.1",
    attribute_id="name",
    value="Node 1",
    unit=None,
    provenance_ref=None,
)

model.add_entity(
    entity_class="Asset",
    entity_id="asset.1",
)

model.add_attribute(
    entity_id="asset.1",
    attribute_id="capacity",
    value=100.0,
    unit="MW",
    provenance_ref=None,
)

model.add_relation(
    entity_id="asset.1",
    relation_id="connectedTo",
    target_entity_id="node.1",
)

errors = model.validate()

if errors:
    raise ValueError(
        "\n".join(errors)
    )

model.export_yaml(
    "model.yaml"
)
```

## Recommended Usage

Use the core operations when creating generic EAR tooling:

```python
model.add_entity(...)
model.add_attribute(...)
model.add_relation(...)
```

Use entity-oriented methods when the entity object is already available:

```python
entity.add_attribute(...)
entity.add_relation(...)
```

Use `ear` rather than `ear_toolbox` for new imports:

```python
from ear import Model, build_model_from_yaml
```

The `ear_toolbox.py` module remains available only to preserve compatibility with older code.
