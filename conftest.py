"""
Ensures the repository root is on sys.path before any test module is
collected, so `from cesdm_toolbox import ...` / `from cesdm import ...`
/ `from ear import ...` work whether or not `pip install -e .` has
been run.

Without this, whether a given test file's import succeeded depended
on pytest's alphabetical collection order: tests/test_hvdc_schema.py
did its own `sys.path.insert(...)` as an import-time side effect,
which happens to persist in sys.path for the rest of the same pytest
process -- so every test file collected *after* it (alphabetically)
worked, while the three collected *before* it
(test_abstract_resolution.py, test_attribute_semantics.py,
test_generation_technology_routing.py) failed with `ModuleNotFoundError:
No module named 'cesdm_toolbox'` in an environment without an editable
install. See CHANGELOG.md.

Recommended either way: `pip install -e .` (see README.md,
"Installation") is still the supported way to use this toolbox outside
of running its own test suite -- this conftest.py only fixes test
collection, not e.g. `python -c "import cesdm_toolbox"` from an
arbitrary working directory.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
