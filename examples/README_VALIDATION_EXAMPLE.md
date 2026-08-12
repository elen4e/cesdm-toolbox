# `example_validation.py` — Schema checks (and notebook twin)

## Why this example

`model.validate()` is the structured way to catch schema problems: missing
required relations, bad enums, out-of-range numbers, and incompatible
relation targets. Some mistakes (especially **wrong units**) raise at
assign time instead.

This example walks through those cases one by one. The same functions are
imported by:

```text
notebooks/cesdm_schema_validation.ipynb
```

For **analysis / study readiness** (`validate_for_analysis`), see
[`example_analysis_validation.py`](example_analysis_validation.py) and its
[README](README_ANALYSIS_VALIDATION_EXAMPLE.md).

Docs: [`docs/getting-started/validation.md`](../docs/getting-started/validation.md).

---

## Run

```bash
# Script (all sections)
python examples/example_validation.py

# Notebook (from repo root)
jupyter notebook notebooks/cesdm_schema_validation.ipynb
# or: jupyter lab notebooks/cesdm_schema_validation.ipynb
```

---

## What each section shows

| # | Topic | Failure mode | Schema / profile shown |
|---|--------|----------------|-------------------------|
| 1 | Clean model | `validate()` → `[]` | — |
| 2 | Missing `belongsToCarrierDomain` | required relation | `NetworkNode.yaml` + `relations.yaml` |
| 3 | `dispatch_type = "steerable"` | enum | `attributes.yaml` → `dispatch_type` |
| 4 | Capacity `< 0`, efficiency `> 1` | min / max | `nominal_power_capacity`, `energy_conversion_efficiency` |
| 5 | `initial_state_of_charge = 1.5` | range `[0, 1]` | `initial_state_of_charge` |
| 6 | `hasOutputCarrier` → `StorageType` | wrong target class | `relations.yaml` → `hasOutputCarrier` |
| 7 | Demand in `GWh` | `ValueError` at assign | `annual_energy_demand` unit enum |
| 8 | `powerflow_bus_type = "slackk"` | enum | `powerflow_bus_type` |
| 9 | Schema OK, dispatch profile not | `validate_for_analysis` | `analysis_profiles/optimal_dispatch.yaml` (DemandUnit) |
| 10 | Broken model | `validate_or_raise()` | same enum as §3 |

In the notebook, each failure cell also renders these YAML excerpts via `show_schema_reason(...)`.

---

## Import in your own notebook

```python
import sys
from pathlib import Path

ROOT = Path("..")  # if the notebook lives under notebooks/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

from example_validation import build_minimal_valid_model, demo_enum_constraint

model = build_minimal_valid_model()
assert model.validate() == []
demo_enum_constraint()
```
