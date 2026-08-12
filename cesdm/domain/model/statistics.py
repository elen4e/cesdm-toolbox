"""cesdm.domain.model.statistics — Model statistics & top-level convenience wrappers

total_capacity() and the validate_or_raise / export_yaml_model /
import_yaml_model convenience wrappers.

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
Behaviour is unchanged; only module boundaries moved.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Union
import os
import pathlib
import re
import yaml


class StatisticsMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def _top_level_asset_family(self, class_name: str) -> str:
        """Return the direct child of EnergyAssetInstance that `class_name`
        descends from (or `class_name` itself if it IS that direct child).

        Used by summary() to roll up e.g. HydroGenerationUnit under
        GenerationUnit -- purely from the inheritance graph, no hardcoded
        class-name lists, same "derive it, don't enumerate it" approach
        already used by _derive_role_from_parents().
        """
        current = class_name
        seen = set()
        while current not in seen:
            seen.add(current)
            parents = self.inheritance.get(current) or []
            if isinstance(parents, str):
                parents = [parents]
            if not parents or "EnergyAssetInstance" in parents:
                return current
            current = parents[0]
        return current  # cycle guard, shouldn't happen in a valid schema

    def summary(self, *, detailed: bool = False, as_dict: bool = False):
        """Return a human-readable count of every asset actually present in
        the model, e.g.:

            GenerationUnit      5321
            DemandUnit          1420
            StorageUnit           88
            TransmissionLine    7421
            Transformer           812
            HVDCLink               17

        By default, subclasses are rolled up under their top-level asset
        family (HydroGenerationUnit counted together with GenerationUnit,
        under the "GenerationUnit" label) -- pass detailed=True to instead
        list every concrete class separately. Pass as_dict=True for a
        plain {label: count} dict (honors `detailed`) instead of the
        formatted string, for programmatic use.

        Only counts real asset entities (role == "asset", see
        _derive_role_from_parents) -- technology-type library entries,
        representation views, and domain entities are excluded, since
        those aren't what "how big is this model" usually means.
        """
        counts: dict[str, int] = {}
        for cname, ents in (self.entities or {}).items():
            if not ents:
                continue
            if self._derive_role_from_parents(cname) != "asset":
                continue
            label = cname if detailed else self._top_level_asset_family(cname)
            counts[label] = counts.get(label, 0) + len(ents)

        if as_dict:
            return counts
        if not counts:
            return "(no assets in this model)"
        width = max(len(c) for c in counts)
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return "\n".join(f"{label:<{width}}  {n:>6}" for label, n in ordered)

    def total_capacity(self, *, asset_class: str | None = None, region_id: str | None = None) -> float:
        """Return sum of nominal_power_capacity across matching assets,
        optionally filtered by class and/or region (via atNode ->
        belongsToGeographicalRegion)."""
        total = 0.0
        for cls, entities in self.entities.items():
            cdef = self.classes.get(cls)
            if cdef is None or getattr(cdef, "abstract", False):
                continue
            for aid in entities:
                if asset_class and cls != asset_class and asset_class not in self._all_parents_of(cls or ""):
                    continue
                if region_id:
                    nodes = self.get_relation_targets(aid, "atNode")
                    if not any(
                        region_id in self.get_relation_targets(n, "belongsToGeographicalRegion")
                        for n in nodes
                    ):
                        continue
                val = self.get_attribute_value(aid, "nominal_power_capacity")
                if val is not None:
                    try:
                        total += float(val)
                    except Exception:
                        pass
        return total

    def validate_or_raise(self) -> None:
        """Run model validation and raise ValueError with a compact report if invalid."""
        errors = self.validate()
        if errors:
            raise ValueError("CESDM model validation failed:\n- " + "\n- ".join(map(str, errors[:50])))

    def export_yaml_model(self, path: str | pathlib.Path) -> None:
        """User-friendly alias for hierarchical YAML export."""
        return self.export_yaml_hierarchical(str(path))

    def import_yaml_model(self, path: str | pathlib.Path, *, strict_unknown: bool = False):
        """User-friendly alias for hierarchical YAML import."""
        return self.import_yaml_hierarchical(str(path), strict_unknown=strict_unknown)

# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------
