# Frequently Asked Questions

## Getting started (energy system modellers)

### Which tutorial should I start with?

The **[Your First Model (Simple)](../getting-started/first-model-simple.md)** tutorial. Follow the [Quickstart](../getting-started/quickstart.md) to install and run it in about 20 minutes. When you want a full multi-domain walkthrough, use [Building your CESDM Model](../tutorials/building-first-model/overview.md).

The [Building your CESDM Model](../tutorials/building-first-model/overview.md) walkthrough (four parts) covers the same model as a script — use as reference, not as first contact.

---

### Do I need to read the schema reference before building a model?

No. Start with the [simple first model](../getting-started/first-model-simple.md), then read [Core Concepts](../getting-started/core-concepts.md). Look up specific classes in the [CESDM Schema Reference](../reference/schema-reference.md) only when needed.

---

### Core API vs Proxy API — which should I use?

| API | When to use |
|-----|-------------|
| **Core [EAR](../community/glossary.md#ear) API** | Learning, debugging, understanding the underlying representation |
| **[Proxy API](../community/glossary.md#proxy-api)** | Building and maintaining your own study models day to day |

---

### Do I need Python to use CESDM?

You need Python to **build or modify** models programmatically. You can read exported [YAML](../community/glossary.md#yaml) and inspect [Frictionless](../community/glossary.md#frictionless-data-package) exports without writing code.

---

### Can I edit a model in Excel and re-import?

Yes, for inspection and data editing. Excel is not the native exchange format — use [YAML](../community/glossary.md#yaml) + [Frictionless](../community/glossary.md#frictionless-data-package) for version control and tool exchange. Re-import via the toolbox export/import utilities.

---

### How do I connect to PyPSA or pandapower?

Import/export utilities live in the repository `tools/` directory (`import_pypsa.py`, `import_pandapower.py`, etc.). Build and validate your CESDM model first, then run the appropriate tool on the exported files.

---

### What's the difference between schema validation and analysis validation?

| Check | Question | Command |
|-------|----------|---------|
| Schema | Is this a valid CESDM model? | `model.validate()` |
| Analysis | Is it ready for my study type? | `model.validate_for_analysis("optimal_dispatch")` |

Study-facing fields (dispatch, power flow, dynamics/controllers) are often schema-optional and only required by the matching profile under `analysis_profiles/`. See [Validation](../getting-started/validation.md).

---

### Do I model every technology explicitly or use library types?

Use **`hasTechnology`** to reference [library](../guides/libraries.md) templates for standard technologies. Set site-specific parameters (capacity, location, custom efficiency) on the asset itself.

---

### Where do profile numbers live vs YAML metadata?

**[YAML](../community/glossary.md#yaml)** stores Profile metadata (`profile_type`, `data_reference`, relations). **Numerical arrays** live in HDF5 or Parquet files referenced by `data_reference`. See [Profiles](../guides/profiles.md).

---

## General

### What is the difference between CESDM and PyPSA or Calliope?

CESDM describes an energy system. PyPSA, Calliope, and similar tools build and optimise models for energy-system studies. CESDM is the shared data model they can exchange through; each tool remains the solver for its analysis type.

---

### Why is CESDM schema-driven?

The model structure is defined by human-readable schema files instead of program code. This makes models transparent, extensible and easy to validate.

---

## Concepts

### What is an Entity?

An entity represents a real-world object, such as a generator, transmission line or demand. See [Core Concepts](../getting-started/core-concepts.md).

---

### Why are Attribute Groups used?

Attribute groups organize information by modelling perspective (dispatch, topology, power flow, capacity expansion, etc.) while keeping all data on the same entity. See [Schemas — Attribute groups](../getting-started/schemas.md#attribute-groups).

---

### What is the difference between a CarrierDomain and a Carrier?

A **Carrier** describes *what* is transported (electricity, gas, heat). A **CarrierDomain** describes *where* it is transported (the corresponding network or infrastructure).

---

## Data and Formats

### How are time series stored?

CESDM entities reference time-series profiles; numerical values are stored separately (typically HDF5). See [Profiles](../guides/profiles.md).

---

### Can I open a CESDM model in Excel?

Yes, for inspection and editing. [YAML](../community/glossary.md#yaml) remains the primary exchange format for version control.

---

### What is the native exchange format?

[YAML](../community/glossary.md#yaml) files together with external profile data (HDF5). [Frictionless Data Packages](../community/glossary.md#frictionless-data-package) provide a tabular alternative.

---

### How do I know my model is ready for my analysis?

Run `model.validate()` then `model.validate_for_analysis("<profile>")`. Shipped profiles include `optimal_dispatch`, `power_flow`, and `dynamics` under `analysis_profiles/`.

→ [Modelling Workflow](../guides/modelling-workflow.md) · [Building docs locally](building-docs.md)
