# Tool adapters

CESDM describes energy systems in a **tool-independent** way (YAML, Frictionless, HDF5 profiles). Converters to and from specific solvers live in **adapter packages**, not in the CESDM core.

| Adapter | Status | Package / location |
|---------|--------|--------------------|
| PyPSA | In toolbox | `tools/import_pypsa.py` |
| pandapower | In toolbox | `tools/import_pandapower.py` |
| MATPOWER | In toolbox | `tools/import_matpower.py` |
| FlexECO | **Separate (in-house)** | Sibling package `cesdm-flexeco` (not published with the toolbox) |

## FlexECO

FlexECO is an internal optimisation tool. The CESDM ↔ FlexECO bridge was moved out of `cesdm-toolbox` into **`cesdm-flexeco`**:

```bash
pip install -e /path/to/sweet-cosi-cesdm
pip install -e /path/to/cesdm-flexeco

cesdm-yaml-to-flexeco \
  --schema-root schemas/cesdm \
  --yaml model.yaml \
  --out-jpn out/scenario.jpn \
  --out-hdf5 out/profiles.h5
```

```python
from cesdm_flexeco import export_to_flexeco, import_from_flexeco
```

Public docs and CI for `cesdm-toolbox` do not require FlexECO.
