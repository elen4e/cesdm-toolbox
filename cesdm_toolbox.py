"""cesdm_toolbox — backward-compatible shim.

The CESDM domain layer was split into the ``cesdm`` package as part of
the package-hierarchy refactor (see docs/architecture/package_layout.md).
This module re-exports the same public API from its new location so
existing ``from cesdm_toolbox import ...`` imports keep working.

New code should import from ``cesdm`` directly.
"""

from cesdm import CesdmModel, build_model_from_yaml

__all__ = ["CesdmModel", "build_model_from_yaml"]
