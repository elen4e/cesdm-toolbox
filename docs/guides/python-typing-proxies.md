# Python Typing and Generated Proxies

!!! info "Optional — skip until you use the [Proxy API](../community/glossary.md#proxy-api) daily"
    Energy system modellers can ignore this page initially. It documents IDE autocomplete and static type checking for the [Proxy API](proxy-api.md). Start with the [Modeller cheat sheet](../getting-started/modeller-cheat-sheet.md) instead.

CESDM provides schema-aware Python typing for the object-oriented [Proxy API](../community/glossary.md#proxy-api).

The typing system has two complementary parts:

1. **Runtime proxy classes** wrap CESDM entities while the program is running.
2. **Generated `.pyi` stubs** provide static type information to editors and type checkers such as Pyright and Pylance.

Both are derived from the CESDM schemas and describe the same underlying Entity–Attribute–Relation model.

---

## Why Typing Matters

The Core [EAR](../community/glossary.md#ear) API is intentionally generic:

```python
model.add_attribute(
    entity_id="gen.ch.wind",
    attribute_id="nominal_power_capacity",
    value=500,
    unit=None,
    provenance_ref=None,
)
```

A static type checker cannot easily infer from this call:

- which attributes belong to `GenerationUnit`;
- which [Attribute Group](../community/glossary.md#attribute-group) contains an attribute;
- which value type is expected;
- which [entity classes](../community/glossary.md#entity-class) are valid relation targets.

The [Proxy API](../community/glossary.md#proxy-api) exposes this information through typed Python objects:

```python
wind.dispatch.nominal_power_capacity = 500
wind.topology.atNode = bus
```

This improves:

- editor auto-completion;
- discoverability of attributes and relations;
- detection of misspelled names;
- relation-target checking;
- refactoring support;
- consistency between schemas and application code.

---

## Runtime Proxies and Static Typings

Runtime proxies and static typings solve different problems.

| Component | Purpose |
|---|---|
| `cesdm.generated_proxies` | Provides schema-specific proxy subclasses at runtime. |
| Generated `.pyi` files | Describe proxy properties, method overloads, and return types to static type checkers. |
| CESDM schemas | Define entity inheritance, attributes, relations, groups, and constraints. |
| Runtime validation | Verifies actual values and model structure during execution. |

Static typing does not replace [schema validation](../community/glossary.md#schema-validation).

A program can pass static type checking and still contain semantically invalid values that are detected only when the model is validated.

---

## Generated Proxy Classes

CESDM generates one proxy subclass for each schema [entity class](../community/glossary.md#entity-class).

Examples include:

```python
from cesdm.generated_proxies import (
    CarrierProxy,
    DemandUnitProxy,
    ElectricalBusProxy,
    GenerationUnitProxy,
    HydroGenerationUnitProxy,
    GenericInterconnectorProxy,
    HydraulicStorageUnitProxy,
)
```

The generated inheritance structure follows the schema inheritance structure.

For example:

```text
SemanticEntityProxy
    └── SystemAssetProxy
        └── EnergyAssetInstanceProxy
            └── GenerationUnitProxy
                └── HydroGenerationUnitProxy
```

The generated runtime proxy module contains a warning:

```text
AUTO-GENERATED CESDM proxy subclasses.
Do not edit manually.
```

Generated files should always be recreated from the schemas rather than edited directly.

---

## Typed Entity Creation

`CesdmModel.add_entity()` returns a schema-specific proxy.

```python
generator = model.add_entity(
    entity_class="GenerationUnit",
    entity_id="gen.ch.wind",
)
```

At runtime, `generator` is a `GenerationUnitProxy`.

With the generated type stubs available, Pyright or Pylance can infer the same specific return type from the literal class name.

The proxy can immediately be used:

```python
generator.name = "CH Wind"
generator.dispatch.nominal_power_capacity = 500
generator.hasInputResource = "resource.renewable.wind"
generator.topology.atNode = bus
```

No explicit cast is required for an entity that has just been created with a literal schema class name.

---

## Retrieving Existing Entities

### `get_entity()`

```python
entity = model.get_entity(
    "gen.ch.wind",
)
```

At runtime, CESDM returns the schema-specific proxy associated with the entity.

However, a static type checker cannot infer the [entity class](../community/glossary.md#entity-class) from an arbitrary string identifier. The static return type is therefore the generic `EntityProxy`.

Generic access remains available:

```python
print(entity.id)
print(entity.entity_class)
```

Schema-specific group access may work at runtime, but a static checker cannot guarantee it:

```python
entity.dispatch.nominal_power_capacity
```

For statically typed access, use `get_entity_as()`.

---

## Typed Retrieval with `get_entity_as()`

`get_entity_as()` tells both CESDM and the type checker which proxy class is expected.

```python
from cesdm.generated_proxies import GenerationUnitProxy

generator = model.get_entity_as(
    "gen.ch.wind",
    GenerationUnitProxy,
)
```

The returned value is typed as `GenerationUnitProxy`:

```python
capacity = generator.dispatch.nominal_power_capacity
node = generator.topology.atNode
```

This is the recommended method when an existing entity is retrieved by identifier and its expected schema class is known.

`get_entity_as()` also verifies the runtime type. It prevents application code from treating an entity as an incompatible proxy class.

---

## Subclass-aware Typing

A subclass proxy can be used wherever its parent proxy is accepted.

```python
from cesdm.generated_proxies import (
    GenerationUnitProxy,
    HydroGenerationUnitProxy,
)


def installed_capacity(
    generator: GenerationUnitProxy,
) -> float:
    return generator.dispatch.nominal_power_capacity


hydro = model.get_entity_as(
    "gen.ch.hydro.reservoir",
    HydroGenerationUnitProxy,
)

capacity = installed_capacity(hydro)
```

This follows the schema inheritance relationship:

```text
HydroGenerationUnit
    extends GenerationUnit
```

and therefore:

```text
HydroGenerationUnitProxy
    extends GenerationUnitProxy
```

---

## Attribute Groups in the Type System

[Attribute Groups](../community/glossary.md#attribute-group) are reflected in the generated type stubs.

Examples include:

```python
generator.dispatch.nominal_power_capacity
generator.topology.atNode
bus.spatial.latitude
interconnector.power_flow.maximum_power_flow_from_to
chp.technical.total_efficiency
```

Each group exposes only the attributes and relations assigned to that group by the schema.

A group may exist globally but not be supported by every [entity class](../community/glossary.md#entity-class).

For example, attempting to access an unsupported group raises an error:

```python
bus.dispatch.nominal_power_capacity
```

```text
AttributeError:
'dispatch' is a real group, but asset class
'ElectricalBus' does not support it.
```

The generated typings allow editors to detect many such mistakes before execution.

---

## Direct and Grouped Fields

Not every field belongs to an [Attribute Group](../community/glossary.md#attribute-group).

Fields without `belongsToGroup` are accessed directly:

```python
generator.name = "CH Wind"
generator.hasTechnology = technology
profile.profile_type = "as_capacity_factor"
```

Grouped fields are accessed through their namespace:

```python
generator.dispatch.nominal_power_capacity = 500
generator.topology.atNode = bus
```

The schema is the source of truth for whether a field is direct or grouped.

---

## Typed Relation Targets

Relations can accept typed proxy instances.

```python
bus = model.add_entity(
    entity_class="ElectricalBus",
    entity_id="bus.ch",
)

generator = model.add_entity(
    entity_class="GenerationUnit",
    entity_id="gen.ch.wind",
)

generator.topology.atNode = bus
```

The relation target is stored as the entity identifier:

```text
bus.ch
```

but application code can work with the typed `ElectricalBusProxy`.

Generated stubs can restrict relation targets to the schema-defined classes.

For example, an `atNode` relation may accept a network-node proxy or identifier, but not an unrelated profile proxy.

---

## Reading Relations

Reading a relation through the CESDM [Proxy API](../community/glossary.md#proxy-api) returns wrapped proxy objects rather than plain strings.

```python
node = generator.topology.atNode
```

When exactly one relation target exists, `node` is returned as the corresponding proxy.

For multi-valued relations, the result is a collection of proxies.

This allows navigation through the model:

```python
region = node.spatial.belongsToGeographicalRegion

print(region.name)
```

---

## Typo Detection

The runtime [Proxy API](../community/glossary.md#proxy-api) provides schema-aware typo detection.

```python
generator.dispatch.nomial_power_capacity = 500
```

raises an `AttributeError` with suggestions based on the fields that are valid for that group.

A static type checker can detect the same problem before execution when the generated stubs are available.

This gives CESDM two layers of protection:

1. editor or CI type checking;
2. runtime schema-aware proxy validation.

---

## Value Types

Generated stubs map schema data types to Python types.

Typical mappings include:

| Schema type | Python type |
|---|---|
| `boolean` | `bool` |
| `integer` | `int` |
| `decimal` | `float` |
| `string` | `str` |
| `date` | `date` |
| `dateTime` | `datetime` |
| `array` | `list[Any]` |
| `object` | `dict[str, Any]` |

Example:

```python
generator.dispatch.nominal_power_capacity = 500.0
timestamps.length = 8760
gas_supply.dispatch.is_slack = True
profile.profile_type = "as_capacity_factor"
```

Constraints such as minimum values, maximum values, units, and allowed enumerations are still checked at runtime.

Static typing verifies the broad Python type; [schema validation](../community/glossary.md#schema-validation) verifies the full semantic constraint.

---

## Static Typing versus Runtime Validation

Consider:

```python
generator.dispatch.nominal_power_capacity = -500.0
```

The value is a valid Python `float`, so static typing may accept it.

The schema may define a minimum value of zero, so runtime assignment or model validation rejects it.

The responsibilities are therefore different:

| Check | Example |
|---|---|
| Static type checking | Is the value a `float`? |
| Proxy runtime checking | Is the field valid for this class and group? |
| Schema validation | Does the value satisfy all schema constraints? |
| Analysis-specific validation | Is the information complete for the intended analysis? |

All layers are complementary.

---

## Running Pyright

Install the development dependencies:

```bash
pip install -e ".[dev]"
```

Run Pyright from the repository root:

```bash
pyright
```

The project configuration contains:

```toml
[tool.pyright]
stubPath = "typings"
```

This tells Pyright and Pylance where the generated `.pyi` files are located.

No separate `pyrightconfig.json` is required.

---

## Generating the Typing Stubs

Typing stubs are generated from:

- CESDM [YAML](../community/glossary.md#yaml) schemas;
- schema inheritance;
- attributes and relations;
- [Attribute Groups](../community/glossary.md#attribute-group);
- public `CesdmModel` and [EAR](../community/glossary.md#ear) method signatures;
- known [Default Library](../community/glossary.md#default-library) [entity classes](../community/glossary.md#entity-class).

From the repository root, run:

```bash
python -m tools.generate_typings \
    --schemas schemas/cesdm \
    --output typings
```

The generated output is written to:

```text
typings/
```

The generator covers the public API of `CesdmModel`, including inherited [EAR](../community/glossary.md#ear) operations and CESDM mixins.

Do not manually edit generated `.pyi` files.

---

## Regenerating Runtime Proxy Classes

Runtime proxy subclasses are generated separately.

After changing [entity classes](../community/glossary.md#entity-class) or schema inheritance, run:

```bash
cesdm-generate-api
```

This regenerates:

```text
cesdm/generated_proxies.py
```

The two generation steps serve different purposes:

| Command | Generated content |
|---|---|
| `cesdm-generate-api` | Runtime proxy subclasses and convenience API artifacts |
| `python -m tools.generate_typings ...` | Static `.pyi` files for editors and type checkers |

After schema changes that affect classes, attributes, relations, groups, or public model methods, regenerate both outputs.

---

## Recommended Regeneration Workflow

```bash
cesdm-generate-api

python -m tools.generate_typings \
    --schemas schemas/cesdm \
    --output typings

pyright

pytest
```

This workflow verifies that:

- runtime proxies match the schemas;
- static typings match the schemas and APIs;
- application code passes static analysis;
- runtime behavior remains correct.

---

## CI Integration

A basic GitHub Actions step can verify the generated typings:

```yaml
- name: Install development dependencies
  run: python -m pip install -e ".[dev]"

- name: Regenerate Proxy API
  run: cesdm-generate-api

- name: Regenerate typings
  run: |
    python -m tools.generate_typings \
      --schemas schemas/cesdm \
      --output typings

- name: Run Pyright
  run: pyright

- name: Check generated files
  run: git diff --exit-code
```

`git diff --exit-code` detects whether committed generated files are out of date.

This prevents schema changes from being merged without corresponding proxy and typing updates.

---

## Example: A Typed Function

```python
from cesdm.generated_proxies import GenerationUnitProxy


def describe_generator(
    generator: GenerationUnitProxy,
) -> str:
    capacity = generator.dispatch.nominal_power_capacity
    node = generator.topology.atNode

    return (
        f"{generator.name}: "
        f"{capacity} MW at {node.name}"
    )
```

Usage:

```python
generator = model.get_entity_as(
    "gen.ch.wind",
    GenerationUnitProxy,
)

print(describe_generator(generator))
```

The type checker can verify:

- that `generator` is a `GenerationUnitProxy`;
- that the dispatch and topology groups are available;
- that the referenced properties exist;
- that the function returns a string.

---

## Example: Accepting Several Proxy Types

Python union types can be used when a function supports several [entity classes](../community/glossary.md#entity-class).

```python
from cesdm.generated_proxies import (
    GenerationUnitProxy,
    StorageUnitProxy,
)


DispatchableAsset = (
    GenerationUnitProxy
    | StorageUnitProxy
)


def capacity(
    asset: DispatchableAsset,
) -> float:
    return asset.dispatch.nominal_power_capacity
```

A shared parent proxy is preferable when the schema inheritance already expresses the common concept.

---

## Recommended Usage

Use the proxy returned by `add_entity()` when creating a new entity:

```python
generator = model.add_entity(
    entity_class="GenerationUnit",
    entity_id="gen.ch.wind",
)
```

Use `get_entity_as()` when retrieving an existing entity and its expected class is known:

```python
generator = model.get_entity_as(
    "gen.ch.wind",
    GenerationUnitProxy,
)
```

Use `get_entity()` for generic code where the schema class is not known in advance:

```python
entity = model.get_entity(entity_id)
```

Use the Core [EAR](../community/glossary.md#ear) API for schema-independent tooling:

```python
model.add_attribute(...)
model.add_relation(...)
```

Use generated proxies and typings for application code:

```python
generator.dispatch.nominal_power_capacity = 500
generator.topology.atNode = bus
```

---

## Summary

CESDM typing is schema-driven.

The schemas define:

- [entity classes](../community/glossary.md#entity-class) and inheritance;
- attributes and relations;
- [Attribute Groups](../community/glossary.md#attribute-group);
- relation targets;
- value types and constraints.

From those schemas, CESDM generates:

- runtime proxy subclasses;
- static `.pyi` type stubs;
- schema-aware editor support.

Static typing improves application development, but it does not replace runtime validation.

Together, the Core [EAR](../community/glossary.md#ear) API, [Proxy API](../community/glossary.md#proxy-api), generated typings, [schema validation](../community/glossary.md#schema-validation), and analysis-specific validation provide complementary layers for building reliable CESDM applications.
