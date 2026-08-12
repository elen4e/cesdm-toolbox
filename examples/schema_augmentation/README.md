# EAR Schema Extension and Grouped Augmentation Example

This example demonstrates how an extension can add application-specific concepts without modifying the CESDM core schema.

The extension does three things:

1. defines a new `Agent` entity class;
2. defines its own globally registered attribute and relation;
3. augments the existing `EnergyAssetInstance` class with a new `agent` group.

Because `GenerationUnit`, `StorageUnit`, and `DemandUnit` inherit from `EnergyAssetInstance`, they inherit the new group automatically.

## Directory layout

```text
examples/schema_augmentation/
├── example.py
├── README.md
└── schema_extension/
    ├── attributes/
    │   └── agent_based.yaml
    ├── relations/
    │   └── agent_based.yaml
    ├── entities/
    │   └── Agent.yaml
    └── augmentations.yaml
```

The files under `schemas/cesdm/` remain unchanged.

## Extension-local attribute registry

```yaml
attributes:
  bidding_strategy:
    description: Strategy used by the agent controlling an asset.
    value:
      type: string
      constraints:
        enum:
          - price_taker
          - strategic
          - cooperative
```

The attribute is global within the composed runtime schema, but its source remains the extension directory.

## Extension-local relation registry

```yaml
relations:
  ownedByAgent:
    description: Agent that owns or represents the asset.
    target: Agent
    cardinality: 0..1
```

## New entity class

```yaml
entity_classes:
  Agent:
    parents: SemanticEntity
```

## Grouped augmentation

```yaml
augmentations:
  EnergyAssetInstance:
    groups:
      agent:
        attributes:
          - id: bidding_strategy
            default: price_taker
        relations:
          - id: ownedByAgent
```

The nested `groups` syntax is shorthand for applying `belongsToGroup: agent` to each referenced field.

The augmentation does not redefine either field. It only attaches the globally registered extension fields to the existing class.

The following direct syntax remains supported and is equivalent:

```yaml
augmentations:
  EnergyAssetInstance:
    attributes:
      - id: bidding_strategy
        belongsToGroup: agent
    relations:
      - id: ownedByAgent
        belongsToGroup: agent
```

## Load the composed schema

```python
from cesdm_toolbox import build_model_from_yaml

model = build_model_from_yaml(
    [
        "schemas/cesdm",
        "examples/schema_augmentation/schema_extension",
    ]
)
```

EAR composes all loaded registries in memory. No source schema file is copied, edited, or overwritten.

## Use the extension through the Proxy API

```python
agent = model.add_entity(
    "Agent",
    "agent.utility.ch",
)
agent.name = "Swiss Utility Agent"

generator = model.add_entity(
    "GenerationUnit",
    "gen.ch.wind",
)
generator.name = "CH Wind"
generator.agent.bidding_strategy = "strategic"
generator.agent.ownedByAgent = agent
```

The entity remains a `GenerationUnit`. The extension does not require a new `AgentBasedGenerationUnit` subclass.

## Run the example

From the repository root:

```bash
python examples/schema_augmentation/example.py
```

Expected output:

```text
Augmented GenerationUnit fields:
  group:             agent
  bidding_strategy:  strategic
  ownedByAgent:      agent.utility.ch

Model validation succeeded.
Schema augmentation test succeeded.
```

## Run the automated tests

```bash
pytest -q tests/test_schema_augmentations.py
```

The tests cover:

- extension-local registries;
- inheritance of augmentations;
- grouped augmentation syntax;
- unknown target classes;
- unknown registry IDs;
- rejection of inline field definitions;
- rejection of conflicting group assignments;
- preservation of the base schema files.

## Rules

- Core registry files are never modified.
- Extensions may define their own attributes, relations, units, and entity classes.
- Registry IDs must be unique across the composed runtime schema.
- Identical duplicate definitions are tolerated; conflicting definitions fail.
- Augmentations reference registered IDs rather than defining fields inline.
- Direct augmentation supports `required`, `default`, and `belongsToGroup` for attributes.
- Direct augmentation supports `required` and `belongsToGroup` for relations.
- Grouped augmentation assigns `belongsToGroup` automatically.
- Fields attached to a parent class are inherited by its subclasses.
