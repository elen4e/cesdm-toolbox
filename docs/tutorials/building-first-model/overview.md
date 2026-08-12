# Building a CESDM Model (Tutorial)

!!! abstract "Before you start"
    - **Prerequisites:** [Installation](../../getting-started/installation.md); complete [Your First Model (Simple)](../../getting-started/first-model-simple.md) first
    - **Time:** ~60 minutes across four parts
    - **Audience:** energy system modellers building the full CH + neighbours reference model

!!! note "Start simple"
    Begin with [Your First Model (Simple)](../../getting-started/first-model-simple.md). This four-part tutorial and the [Jupyter notebook](../advanced-reference-notebook.md) cover the same full reference model in more detail.

This tutorial constructs a simplified multi-domain energy system for Switzerland and its neighbouring countries using the [Proxy API](../../community/glossary.md#proxy-api).

## Model blueprint

| Part | Sections | What you build |
|------|----------|----------------|
| [Part 1](part-1-system-and-network.md) | 1–4 | Schema, system container, electricity domain, regions, buses |
    | [Part 2](part-2-demand-and-generation.md) | 5–7 | Demand, time axis, library resources, CH + neighbour fleet (incl. DE coal) |
| [Part 3](part-3-profiles-and-interconnectors.md) | 9–11 | Profiles, reservoir hydro (CH/DE/FR/IT/AT), 8 NTCs |
| [Part 4](part-4-multicarrier-and-export.md) | 12–14 | Gas and heat domains, CHP coupling, validation, export |

**Checkpoint tip:** After each part, run `print_class_counts(model)` (from the notebook helpers) to verify entity counts grow as expected.

## Jupyter notebook (recommended)

Interactive **Proxy API** version with step-by-step markdown and inspection helpers (`print_entity`, `print_class_counts`):

```text
notebooks/building_your_cesdm_model.ipynb
```

Uses typed entity handles (`bus.name = ...`, `gen.atNode = bus`) — the style from [Proxy API](../../guides/proxy-api.md) and [Your First Model (Simple)](../../getting-started/first-model-simple.md).

```bash
pip install -e ".[jupyter]"
jupyter lab
```

Open `notebooks/building_your_cesdm_model.ipynb` from the repository root and run all cells sequentially.

## Executable scripts

| Script | Role |
|--------|------|
| `docs/examples/minimal_electricity_model.py` | First model (quickstart) |
| `docs/examples/reference_energy_system_model.py` | Full CH + neighbours reference (Core EAR; Proxy snippets in comments) |
| `notebooks/building_your_cesdm_model.ipynb` | Interactive Proxy API walkthrough of the same reference model |

Run from the repository root after activating your virtual environment.
