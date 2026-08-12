# Schema Governance

!!! warning "Integrator documentation"
    This page is **not part of the Modelling path**. It describes schema versioning and stability for toolbox maintainers. Modellers only need to know that exported models record a schema version — see the TL;DR below.

!!! info "TL;DR if you build CESDM study models"
    Schemas use **semantic versioning** (`MAJOR.MINOR.PATCH`). Exported models record their schema version. You rarely author schemas — but knowing versions exist helps when sharing models across projects or toolbox releases.

Schemas are the interoperability contract of CESDM. They define the entities, attributes, relations, and validation rules that enable different tools and organizations to exchange energy system models consistently.

To ensure long-term compatibility while allowing the data model to evolve, CESDM follows a lightweight schema governance process based on semantic versioning and clearly defined stability levels.

---

## Semantic Versioning

Each schema tree contains a semantic version in `SCHEMA_MANIFEST.yaml`.

```yaml
version: "0.1.0"
```

CESDM follows standard semantic versioning.

| Change | Version | Example |
|--------|---------|---------|
| Documentation improvements or wording changes | **PATCH** | Improved descriptions or comments |
| Backward-compatible extensions | **MINOR** | New optional entity, attribute, relation, or schema family |
| Breaking structural changes | **MAJOR** | Renaming or removing entities, attributes, relations, or inheritance changes |

A simple compatibility rule applies:

> **If an existing model no longer validates without modification, the change is considered a major change.**

This version information is also stored when models are exported, allowing tools to identify potential schema compatibility issues.

---

## Schema Stability

Not every part of CESDM evolves at the same pace. Therefore, schema families can have different stability levels.

| Level | Description |
|--------|-------------|
| **Stable** | Mature components intended for long-term use. Breaking changes are expected to be rare. |
| **Experimental** | Functional components that may still evolve based on practical experience and community feedback. |
| **Deprecated** | Components scheduled for removal in a future major release. Existing models remain supported until then. |

This gives users a clear indication of which parts of the schema are suitable for production workflows and which are still evolving.

### Family keys

Stability is declared under `stability:` in `SCHEMA_MANIFEST.yaml` as a map of **family key → tier**. Keys are logical groupings (not always one directory). Dotted keys refine a coarser family when directory layout would otherwise over-promote a class.

Examples from the CESDM core tree:

| Family key | Typical coverage | Tier |
|------------|------------------|------|
| `assets` | Generation, storage, demand, conversion, electrical transmission leaves | stable |
| `system` | `EnergySystemModel`, `GeographicalRegion`, abstract `RunRecord` | stable |
| `system.run_records.dispatch` | `DispatchRunRecord` | stable |
| `system.run_records.power_flow` | `PowerFlowRunRecord` | experimental |
| `system.run_records.dynamics` | `DynamicRunRecord` | experimental |
| `results.dispatch` / `.power_flow` / `.dynamics` | Result entity subtrees | experimental |
| `transmission.gas` / `transmission.heat` | Abstract `GasTransmission` / `HeatTransmission` (no pipe leaves yet) | experimental |

Lookup is exact: `model.schema_manifest.stability_for("system.run_records.power_flow")`. Unknown keys return `"unknown"` (informational, not an error).

---

## Extending CESDM

CESDM is designed to be extensible.

Projects and organizations can create their own schema trees while reusing the official CESDM schemas.

```yaml
extends:
  - ../cesdm
```

(the path is relative to the extension's own `SCHEMA_MANIFEST.yaml`; `schemas/agentbased/SCHEMA_MANIFEST.yaml` uses exactly this to build on `schemas/cesdm/`)

This allows domain- or project-specific extensions without modifying the CESDM core. As a result, custom schemas remain compatible with future CESDM releases while allowing organizations to introduce their own entities, attributes, and relations.

---

## Contributing Schema Changes

When proposing a schema change, contributors should clearly document:

- **What** is changing.
- **Why** the change is needed.
- Whether the change is **PATCH**, **MINOR**, or **MAJOR**.
- The expected impact on existing models and tools.

Keeping the governance process lightweight encourages community contributions while maintaining interoperability and long-term consistency.

---

## Design Principles

The schema governance process follows a few simple principles:

- **Backward compatibility whenever possible.**
- **Transparent versioning** using semantic version numbers.
- **Incremental evolution** through additive extensions.
- **Extensibility** without modifying the CESDM core schemas.
- **Clear communication** of breaking changes through major version updates.

---

## Summary

- Schemas are the interoperability contract of CESDM.
- Semantic versioning communicates compatibility between schema releases.
- Stable, experimental, and deprecated schema families can coexist.
- New schema trees can extend existing schemas without modifying the core.
- A lightweight governance process ensures that CESDM can evolve while maintaining interoperability across tools and organizations.
