# Schema Augmentation

This page covers how CESDM schemas can be extended in **YAML** without modifying the core schema package or the Python engine (`ear/`).

Energy system modellers often need this when a study requires attributes or entity classes beyond CESDM core — you extend the **vocabulary**, not the Core API. Start with [Schemas](schemas.md) for the essentials; use the [EAR API Reference](../reference/api-reference.md) only if you integrate CESDM into application code.

!!! info "Audience"
    Energy system modellers and schema contributors who extend CESDM for project-specific semantics. You work in schema YAML — not in `ear/` or `cesdm/` Python source.

## Schema Augmentation

One of the fundamental design goals of the [EAR](../community/glossary.md#ear) engine is to allow schemas to evolve without modifying existing schema packages.

Rather than maintaining a single monolithic schema, the [EAR](../community/glossary.md#ear) engine composes multiple independent schema packages into a single semantic model at load time.

This allows different modelling communities to extend a common semantic foundation while preserving compatibility with the CESDM Core.

---

### Why Schema Augmentation?

Different applications often require additional semantic information that is irrelevant for other analyses.

For example:

- agent-based simulations require ownership information and bidding strategies;
- electricity market models require bids and market participation;
- reliability studies require failure rates and maintenance statistics;
- dynamic simulations require controller parameters.

These concepts should not become part of the CESDM Core because they are application-specific.

Likewise, creating specialised subclasses such as

```text
AgentBasedGenerationUnit
MarketGenerationUnit
ReliabilityGenerationUnit
```

would unnecessarily fragment the semantic model and require existing entities to be replaced by application-specific subclasses.

Instead, [EAR](../community/glossary.md#ear) allows existing [entity classes](../community/glossary.md#entity-class) to be **augmented** with additional semantic concepts while preserving their original identity.

A `GenerationUnit` therefore always remains a `GenerationUnit`.

Applications simply add additional semantic information when required.

---

### Extension Packages

Schema augmentation is implemented through independent schema packages.

A typical extension has exactly the same structure as the CESDM Core.

```text
agent_based/

├── entities/
│   └── Agent.yaml
│
├── attributes/
│   └── agent.yaml
│
├── relations/
│   └── agent.yaml
│
└── augmentations.yaml
```

Each extension package owns its own semantic definitions.

The CESDM Core schemas are never modified.

---

### Adding New Entity Classes

Extensions may define completely new [entity classes](../community/glossary.md#entity-class).

For example:

```yaml
name: Agent

parents:
  - SemanticEntity

attributes:
  - id: agent_name
```

The new class becomes part of the composed schema while leaving the CESDM Core unchanged.

---

### Adding New Attributes

Extensions maintain their own global attribute registry.

Example:

```yaml
attributes:

  bidding_strategy:

    description: Market bidding strategy.

    value:
      type: string

      constraints:

        enum:
          - price_taker
          - strategic
          - cooperative
```

These definitions belong to the extension package.

They are **not** copied into the CESDM Core attribute registry.

---

### Adding New Relations

Extensions likewise maintain their own global relation registry.

```yaml
relations:

  ownedByAgent:

    description: Agent responsible for operating the asset.

    target:
      - Agent

    cardinality: 0..1
```

Again, the CESDM Core remains unchanged.

---

### Augmenting Existing Entity Classes

Extensions may attach additional attributes and relations to existing [entity classes](../community/glossary.md#entity-class).

Unlike inheritance, augmentation does **not** create a new [entity class](../community/glossary.md#entity-class).

Instead, the semantic definition of an existing class is extended inside the composed schema.

Example:

```yaml
augmentations:

  EnergyAssetInstance:

    groups:

      agent:

        attributes:

          - id: bidding_strategy

        relations:

          - id: ownedByAgent
```

This augmentation extends `EnergyAssetInstance`.

Consequently, every subclass automatically inherits the additional semantic concepts, including:

- `GenerationUnit`
- `StorageUnit`
- `DemandUnit`
- `TransmissionElement`

without changing their original schema definitions.

---

### Attribute Groups

Augmentations may introduce new [Attribute Groups](../community/glossary.md#attribute-group).

In the previous example, the group

```text
agent
```

is created automatically.

The generated [Proxy API](../community/glossary.md#proxy-api) therefore exposes

```python
generator.agent.bidding_strategy = "strategic"

generator.agent.ownedByAgent = agent
```

in exactly the same way as existing groups such as

```python
generator.dispatch.nominal_power_capacity

generator.topology.atNode

generator.technical.total_efficiency
```

The augmentation therefore integrates seamlessly with the existing [Proxy API](../community/glossary.md#proxy-api).

---

### Composing Schemas

Multiple schema packages may be loaded simultaneously.

```python
model = build_model_from_yaml(
    [
        "schemas/cesdm",
        "schemas/extensions/agent_based",
        "schemas/extensions/market",
        "schemas/extensions/reliability",
    ]
)
```

The [EAR](../community/glossary.md#ear) engine composes:

- [entity classes](../community/glossary.md#entity-class);
- attribute registries;
- relation registries;
- inheritance;
- augmentations;
- validation rules;

into one validated semantic schema before any model entities are created.

Applications therefore operate on a single coherent semantic model regardless of how many schema packages contributed to it.

---

### Validation

Before the composed schema becomes available, the [EAR](../community/glossary.md#ear) engine validates:

- duplicate entity definitions;
- duplicate attribute definitions;
- duplicate relation definitions;
- augmentation conflicts;
- inheritance consistency;
- relation targets;
- [attribute groups](../community/glossary.md#attribute-group).

Conflicting schema definitions therefore fail during schema loading rather than during model construction.

---

### Proxy API and Typings

Schema augmentation is fully reflected in the generated [Proxy API](../community/glossary.md#proxy-api) and Python typings.

After regenerating the proxies,

```bash
cesdm-generate-api
```

and the typings,

```bash
cesdm-generate-typings
```

the new [Attribute Group](../community/glossary.md#attribute-group) becomes part of the generated API.

Example:

```python
generator.agent.bidding_strategy

generator.agent.ownedByAgent
```

No manual programming is required.

The generated proxies and type stubs are always derived from the composed schema.

---

### Supporting Community-driven Evolution

Schema augmentation is not merely a technical extension mechanism.

It is an architectural concept that enables collaborative evolution of semantic models.

Without augmentation, new applications would typically

- modify the CESDM Core;
- maintain private forks; or
- introduce specialised subclasses that duplicate existing concepts.

These approaches lead to fragmentation and reduce interoperability.

Schema augmentation avoids these problems.

The CESDM Core remains a stable, technology-independent semantic foundation that evolves carefully through community consensus.

Independent modelling communities can build application-specific schema packages on top of this foundation without modifying or forking the core schemas.

This provides several important benefits:

- **Stable Core** – the CESDM Core remains compact, technology-independent, and backwards compatible.
- **Independent Innovation** – application developers can introduce new semantic concepts without waiting for changes to the Core.
- **No Forks** – projects no longer need to maintain customised copies of the CESDM schemas.
- **Interoperability** – different applications continue to share the same fundamental semantic model.
- **Composability** – multiple independent extensions can be combined into one coherent schema.
- **Reuse** – semantic concepts developed by one community can be reused by others.
- **Incremental Standardisation** – successful extensions can later migrate into the CESDM Core through the normal governance process.

This creates a natural evolution path from project-specific concepts to community standards while preserving compatibility with existing models.

---

### Summary

Schema augmentation enables independent schema packages to extend existing semantic concepts without modifying the CESDM Core.

Rather than creating specialised subclasses or maintaining private schema forks, applications contribute additional semantic definitions that are composed into a single validated schema at load time.

This architecture supports long-term interoperability, collaborative schema development, and the gradual evolution of CESDM through reusable, application-driven extensions while preserving a stable semantic foundation.

---

