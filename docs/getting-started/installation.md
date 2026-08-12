# Installation

Install and verify the CESDM Toolbox. For a guided path to your **first model**, use the **[Quickstart](quickstart.md)** (~20 min) — this page is the full reference.

!!! tip "Energy system modellers"
    **Start with [Quickstart](quickstart.md)** unless you need uv, Poetry, Conda, or optional extras below.

!!! info "Which Python package to import?"
    Energy system modellers should use `from cesdm_toolbox import build_model_from_yaml`. The low-level `ear` package is documented in the [EAR API Reference](../reference/api-reference.md) for engine-level work.

---

## Repository layout (modellers)

```text
cesdm-toolbox/
├── schemas/cesdm/              # schema vocabulary (rarely edited)
├── library/default_library/    # reusable carriers and technologies
├── docs/examples/              # minimal + reference Python scripts
├── notebooks/                  # Jupyter companions (reference model, schema validation)
├── analysis_profiles/          # validation profiles (optimal_dispatch, power_flow, dynamics, …)
└── tools/                      # import/export, validation, aggregation
```

---

## Prerequisites

Before installing CESDM, ensure that the following software is available:

- Python 3.11 or newer
- Git
- pip

```bash
python --version
git --version
```

---

## Clone the repository

```bash
git clone https://github.com/cesdm/cesdm-toolbox.git
cd cesdm-toolbox
```

---

## Create a virtual environment

CESDM supports any standard Python environment manager. Choose the one that best matches your workflow.

### Option 1: Python venv (recommended)

=== "Linux / macOS"

    ```bash
    python -m venv .sweet-cosi-cesdm
    source .sweet-cosi-cesdm/bin/activate
    ```

=== "Windows"

    ```powershell
    python -m venv .sweet-cosi-cesdm
    .sweet-cosi-cesdm\Scripts\activate
    ```

### Option 2: uv

=== "Linux / macOS"

    ```bash
    uv venv .sweet-cosi-cesdm
    source .sweet-cosi-cesdm/bin/activate
    ```

=== "Windows"

    ```powershell
    uv venv .sweet-cosi-cesdm
    .sweet-cosi-cesdm\Scripts\activate
    ```

### Option 3: Poetry

```bash
poetry install
poetry shell   # or: poetry run python
```

### Option 4: Conda

```bash
conda create --name sweet-cosi-cesdm python=3.12
conda activate sweet-cosi-cesdm
```

---

## Install CESDM

Upgrade pip, then install in editable mode:

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

For the interactive tutorial, install Jupyter support:

```bash
pip install -e ".[jupyter]"
```

Editable mode allows local source code changes to become immediately available without reinstalling the package.

---

## Optional components

??? note "Documentation build (`[docs]`)"
    ```bash
    pip install -e ".[docs]"
    mkdocs serve
    ```
    Opens at http://127.0.0.1:8000

??? note "Development tools (`[dev]`)"
    ```bash
    pip install -e ".[dev]"
    ```

??? note "Everything (`[all]`)"
    ```bash
    pip install -e ".[all]"
    ```

---

## After install

→ Continue with the **[Quickstart](quickstart.md)** to run your first model, or **[Your First Model (Simple)](first-model-simple.md)** for the tutorial walkthrough.

For the multi-domain walkthrough: `pip install -e ".[jupyter]"` then see [Building your CESDM Model](../tutorials/building-first-model/overview.md).

---

## Troubleshooting

### `ModuleNotFoundError`

Ensure the virtual environment is activated and run `pip install -e .` from the repository root.

### `jupyter: command not found`

```bash
pip install -e ".[jupyter]"
```

### Notebook cannot find `schemas/cesdm/`

Run Jupyter from the **cesdm-toolbox** repository root, not from a subdirectory.

### `ImportError`

Ensure the notebook or Python interpreter uses the activated CESDM virtual environment.

---

## Next step

→ [Quickstart](quickstart.md) · [← Learning path](choose-your-path.md)
