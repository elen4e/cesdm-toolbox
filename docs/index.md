# Common Energy System Domain Model (CESDM)

<p align="center" markdown="1">
![CESDM](illustrations/cesdm_hero.svg){ width="78%" }
</p>

<p align="center">
  <a href="https://github.com/cesdm/cesdm-toolbox"><img src="https://img.shields.io/badge/GitHub-Repository-blue?logo=github" alt="GitHub" /></a>
  <a href="https://sweet-cosi.ch"><img src="https://img.shields.io/badge/Project-SWEET--CoSi-orange" alt="SWEET-CoSi" /></a>
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License: MIT" />
</p>

!!! quote ""
    **What is CESDM?** A common way to describe an energy system so it can be reused across studies and tools.

    **Why use it?** Keep one system description when tools update, partners join, or you run different analyses on the same assets.

[Get Started](getting-started/quickstart.md){ .md-button .md-button--primary }
[First Tutorial](getting-started/first-model-simple.md){ .md-button }
[Schema Reference](reference/schema-reference.html){ .md-button }
[GitHub Repository](https://github.com/cesdm/cesdm-toolbox){ .md-button }

---

## What is CESDM?

CESDM (**Common Energy System Domain Model**) is an open framework for describing **energy systems** — grids, plants, demand, and their data — in one shared form that studies and tools can reuse.

| | |
|---|---|
| **Goal** | One agreed description of the system so teams can share models and compare results across tools and studies |
| **Scope** | Energy systems — networks, assets, profiles; multi-carrier (electricity, gas, heat, …); schema-defined and validated — **not** a solver or optimiser |
| **Audience** | Energy system modellers (primary); tool developers and integrators (secondary) |

[Read the full introduction →](getting-started/what-is-cesdm.md)

---

## Why CESDM?

**Problem:** Different teams describe the **same system** in different software and file formats. To exchange that system — or compare results — they need a separate converter for **every pair of tools**: with 4 tools, that is **6 mappings**, not one shared model.

**Motivation:** CESDM is the **shared description of the system** in the middle. Each tool connects **once** to CESDM instead of to every other tool.

<p align="center" markdown="1">
![CESDM as common exchange hub](illustrations/cesdm_exchange_hub.svg){ width="85%" }
</p>

<div class="grid cards" markdown>

- :material-database:{ .lg .middle } __Single source of truth__

    ---

    One topology, one set of assets — one master model, not a separate export from every tool.

- :material-chart-multiple:{ .lg .middle } __Multi-analysis__

    ---

    Dispatch, grid analysis, and stability — different details on the **same equipment**, not separate models to keep in sync.

- :material-swap-horizontal:{ .lg .middle } __Multi-tool__

    ---

    Import and export through the toolbox — each analysis program connects via one shared model.

</div>

<p align="center" markdown="1">
![One energy system — many analyses and tools](illustrations/physical_system_analysis_views_tools.svg){ width="88%" }
</p>

[Hub vs chain comparison →](getting-started/what-is-cesdm.md#with-and-without-cesdm)

---

## Why would I want to use CESDM?

Beyond “one shared format”, CESDM is useful when you care about **stability of your system description** while tools and studies change around it.

| Reason | What that means in practice |
|--------|----------------------------|
| **Insulate your model from tool churn** | A PyPSA (or Calliope, pandapower, …) release can rename fields or change defaults. If the system lives in CESDM, you update the **PyPSA↔CESDM adapter** for that version — not every study script and not every other tool’s copy of the network. |
| **Keep one system, many tools** | Partners can stay on PyPSA, Calliope, OSeMOSYS, or in-house code. Each maps **once** to CESDM instead of maintaining a converter to every other tool. |
| **Reuse the same assets across study types** | Dispatch, power flow, and dynamics need different inputs — but they can hang on the **same** buses, lines, and plants instead of three divergent case files. |
| **Validate before you hand off** | Schema and analysis checks catch missing capacities, bad units, or incomplete study data **before** export or solver setup. |
| **Archive what the system *meant*** | Years later you still have a schema-defined description of the physical system — independent of which solver or file layout was fashionable when you ran it. |
| **Extend without forking the core** | Project-specific classes stay as schema augmentation; the shared vocabulary and adapters remain reusable. |

CESDM does **not** replace PyPSA or your optimiser. It is the **stable middle layer** so tool upgrades and new partners do not force you to rebuild the whole energy-system description.

[What CESDM is (and is not) →](getting-started/what-is-cesdm.md)

---

## What can I do with CESDM?

<div class="grid cards" markdown>

- :material-hammer-wrench:{ .lg .middle } __Build semantic models__

    ---

    Define your system using CESDM [schemas](community/glossary.md#schema) — Python [Proxy API](guides/proxy-api.md) or Core [EAR](community/glossary.md#ear) API

    [First model →](getting-started/first-model-simple.md)

- :material-check-circle:{ .lg .middle } __Validate models__

    ---

    Check the model is valid and complete for your study — before export

    [Validation →](getting-started/validation.md)

- :material-bookshelf:{ .lg .middle } __Reuse technologies__

    ---

    Default library for plant types and carriers

    [Libraries →](guides/libraries.md)

- :material-export:{ .lg .middle } __Exchange models__

    ---

    [YAML](community/glossary.md#yaml), JSON, CSV, Excel, Frictionless — HDF5 for time series

    [Modelling workflow →](guides/modelling-workflow.md)

- :material-shape-plus:{ .lg .middle } __Extend schemas__

    ---

    Augmentation for project-specific classes

    [Schema augmentation →](getting-started/schemas-in-depth.md)

- :material-book-search:{ .lg .middle } __Look up classes__

    ---

    Interactive catalogue of entities, attributes, and relations

    [CESDM Schema Reference →](reference/schema-reference.html)

- :material-application-brackets:{ .lg .middle } __Build applications__

    ---

    Import/export tools and custom pipelines on the [EAR engine](reference/api-reference.md)

    [EAR API Reference →](reference/api-reference.md)

</div>

---

## Lookup & reference

Need a class, attribute, or relation name? Start here — these are easy to miss if you only follow the tutorials.

| Resource | For whom | Open |
|----------|----------|------|
| **[CESDM Schema Reference](reference/schema-reference.html)** | Everyone looking up vocabulary | Interactive HTML (search, tabs, filters) |
| [Modeller Cheat Sheet](getting-started/modeller-cheat-sheet.md) | Day-to-day modelling patterns | Short patterns + snippets |
| [Glossary](community/glossary.md) | Terms (EAR, Proxy, Profile, …) | Definitions |
| [EAR API Reference](reference/api-reference.md) | Tool integrators / engine work | Low-level `ear` package |

The Schema Reference is also under the **Reference** tab in the top navigation.

---

## Get started

There is **one** guided quickstart (~20 min): install → run the minimal model → confirm exports.

[:octicons-arrow-right-24: Quickstart guide](getting-started/quickstart.md){ .md-button .md-button--primary }
[First tutorial walkthrough](getting-started/first-model-simple.md){ .md-button }

After the script runs, read [Your First Model (Simple)](getting-started/first-model-simple.md) to understand each step. For the full multi-domain example, see [Building your CESDM Model](tutorials/building-first-model/overview.md).

---

## Documentation overview

| Section | Goal | Start here |
|---------|------|------------|
| :material-rocket-launch: **Getting Started** | First model in ~20 min | [Quickstart](getting-started/quickstart.md) |
| :material-lightbulb: **Concepts** | Understand why and EAR (~25 min essential) | [Concepts overview](getting-started/concepts.md) |
| :material-hammer-wrench: **Building Models** | Build, validate, export study models | [Modelling Workflow](guides/modelling-workflow.md) |
| :material-code-braces: **Building Applications** | Schema extension | [Schema Augmentation](getting-started/schemas-in-depth.md) |
| :material-book-open-page-variant: **Reference** | Lookup schemas and API | **[CESDM Schema Reference](reference/schema-reference.html)** · [Cheat sheet](getting-started/modeller-cheat-sheet.md) · [EAR API](reference/api-reference.md) |
| :material-account-group: **Community** | FAQ, contribute, cite | [FAQ](community/faq.md) |

[Choose your path →](getting-started/choose-your-path.md) · [Documentation map →](getting-started/choose-your-path.md#documentation-map)

---

## Open source

[SWEET-CoSi](https://sweet-cosi.ch) · [Contributing](community/contributing.md) · [Citation](community/citation.md) · [Disclaimer](getting-started/disclaimer.md)
