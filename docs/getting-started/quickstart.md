# Quickstart for Energy System Modellers

From zero to a **validated, exportable CESDM model** in about **20 minutes**. No need to read schemas or [EAR](../community/glossary.md#ear) theory first — you pick that up as you build.

!!! abstract "What you will do"
    1. Install and verify the toolbox (~10 min)
    2. Run the minimal electricity model script (~5 min)
    3. Confirm exports — a **harmonised system description** you can share or compare

!!! info "Time"
    ~10 min install + ~10 min hands-on.  
    **Run the script first**, then read [Your First Model (Simple)](first-model-simple.md) to understand each line.

!!! tip "Need uv, Poetry, or Conda?"
    This page uses plain `venv` + `pip`. Other environment managers are in the [Installation guide](installation.md).

---

## Step 1 — Install (~10 min)

**Requirements:** Python 3.11+, Git.

```bash
git clone https://github.com/cesdm/cesdm-toolbox.git
cd cesdm-toolbox

python -m venv .sweet-cosi-cesdm
source .sweet-cosi-cesdm/bin/activate   # Windows: .sweet-cosi-cesdm\Scripts\activate

python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

Full options (uv, Poetry, Conda, extras): [Installation](installation.md).

**Verify** from the repository root:

```bash
python -c "
from cesdm_toolbox import build_model_from_yaml
model = build_model_from_yaml('schemas/cesdm')
model.import_library('library/default_library')
print(f'CESDM ready — {len(model.entities)} library entities loaded')
"
```

You should see a **non-zero** entity count (dozens of library entries).  
If you get `FileNotFoundError: schemas/cesdm`, you are not in the repo root.

---

## Step 2 — Run your first model (~5 min)

From the **repository root** (venv still active):

```bash
python docs/examples/minimal_electricity_model.py
```

**Expected output** (paths may vary):

```text
Validated model and exported to .../output/minimal_electricity_model
  profiles: demand, wind CF, PV CF, hydro inflow (8760 h → profiles.h5)
```

### Success checklist

- [ ] Command exits without error
- [ ] Folder `output/minimal_electricity_model/` exists
- [ ] File `demo_2030.yaml` is present
- [ ] File `profiles.h5` holds the synthetic hourly arrays
- [ ] Subfolder `frictionless/` contains tabular export files

If validation fails, see [Troubleshooting](#troubleshooting) or the [First Model tutorial](first-model-simple.md).

---

## Step 3 — What you have now

| Output | What it means |
|--------|----------------|
| Validated model | Electricity domain, one bus, wind + PV + reservoir hydro, demand |
| `demo_2030.yaml` | Human-readable, version-control-friendly [YAML](../community/glossary.md#yaml) |
| `profiles.h5` | Synthetic hourly demand, wind/PV capacity factors, hydro inflow |
| `frictionless/` | Tabular [Frictionless](../community/glossary.md#frictionless-data-package) package for tools and pipelines |

This is an **agreed description of the physical system** — the [Goal](../index.md#what-is-cesdm) of CESDM: harmonised data you can exchange with collaborators and use as a common basis when comparing results.

The script uses the **Core [EAR](../community/glossary.md#ear) API** for the system container and carrier domain, and the **[Proxy API](../community/glossary.md#proxy-api)** for buses and assets — the pattern you will use in your own studies.

---

## Step 4 — Understand what you ran

**Next:** open **[Your First Model (Simple)](first-model-simple.md)** (~10 min read) — it walks through the same script line by line.

Optional deeper path later: [Building your CESDM Model](../tutorials/building-first-model/overview.md) (`pip install -e ".[jupyter]"` for the notebook).

---

## Step 5 — Where to go next

| Order | Page | Why |
|-------|------|-----|
| 1 | [Core Concepts](core-concepts.md) | Name what you did — entities, attributes, relations |
| 2 | [What is CESDM?](what-is-cesdm.md) | Why exchange and multi-analysis matter |
| 3 | [Proxy API](../guides/proxy-api.md) | Build your own study models efficiently |
| 4 | [Modelling Workflow](../guides/modelling-workflow.md) | Full build → validate → export lifecycle |
| 5 | [Modeller cheat sheet](modeller-cheat-sheet.md) | Quick patterns while modelling |

Lookup: [Glossary](../community/glossary.md) · [FAQ](../community/faq.md) · [Documentation map](choose-your-path.md#documentation-map)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: cesdm_toolbox` | Activate venv; run `pip install -e .` from repo root |
| `FileNotFoundError: schemas/cesdm` | Run commands from **cesdm-toolbox** root, not `docs/` |
| `No such file: docs/examples/minimal_electricity_model.py` | Update to a recent toolbox clone; script ships in `docs/examples/` |
| Validation errors | Wrong units or missing relations — see [First Model tutorial](first-model-simple.md) |
| Python &lt; 3.11 | Upgrade Python; see [Installation](installation.md) |

More: [Installation — Troubleshooting](installation.md#troubleshooting).

---

→ **[Your First Model (Simple)](first-model-simple.md)** — understand the script you just ran
