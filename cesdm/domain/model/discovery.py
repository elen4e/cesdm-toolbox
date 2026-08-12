"""cesdm.domain.model.discovery — Class-role & representation-view discovery

Derives asset/view/domain role purely from schema structure and
builds the view-class index used by exporters and builders.

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


class DiscoveryMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def _derive_role_from_parents(self, class_name: str, _cache: dict | None = None) -> str:
        """
        Return the role (``"asset"``, ``"view"``, or ``"domain"``) of a class.

        Derived purely from class structure — no ``role:`` YAML field consulted,
        no hardcoded seed frozensets.

        Rules (in order):

        1. **View** — the class or any ancestor declares ``reportsOn``
           as a relation.  This covers Result entities and their abstract
           bases (``Result``, ``DispatchResult``, etc.).
        2. **Asset** — the class IS ``EnergyAssetInstance`` or inherits from it
           (directly or transitively).
        3. **Domain** — everything else.
        """
        if _cache is None:
            _cache = {}
        if class_name in _cache:
            return _cache[class_name]

        # Sentinel — breaks cycles
        _cache[class_name] = "domain"

        cdef = self.classes.get(class_name)
        if cdef is None:
            return "domain"

        praw = getattr(cdef, "parents", None)
        parents = ([praw] if isinstance(praw, str) else list(praw or []))

        # Rule 1 — view: reportsOn declared here or inherited
        _, rels = self._collect_inherited_fields(cdef)
        if self._REPORTS_ON_REL in rels:
            _cache[class_name] = "view"
            return "view"

        # Rule 2 — asset: IS EnergyAssetInstance or descends from it
        if class_name == "EnergyAssetInstance":
            _cache[class_name] = "asset"
            return "asset"
        for p in parents:
            if self._derive_role_from_parents(p, _cache) == "asset":
                _cache[class_name] = "asset"
                return "asset"

        # Rule 3 — domain
        return "domain"

    def _discover_view_classes(self) -> frozenset:
        """Return all class names whose role resolves to ``"view"``."""
        if not hasattr(self, "_view_classes_cache"):
            _cache: dict = {}
            self._view_classes_cache = frozenset(
                n for n in self.classes
                if self._derive_role_from_parents(n, _cache) == "view"
            )
        return self._view_classes_cache

    def _discover_asset_classes(self) -> frozenset:
        """Return all class names whose role resolves to ``"asset"``."""
        if not hasattr(self, "_asset_classes_cache"):
            _cache: dict = {}
            self._asset_classes_cache = frozenset(
                n for n in self.classes
                if self._derive_role_from_parents(n, _cache) == "asset"
            )
        return self._asset_classes_cache

    def _discover_non_asset_classes(self) -> frozenset:
        """Return all class names whose role resolves to ``"domain"``."""
        if not hasattr(self, "_non_asset_classes_cache"):
            _cache: dict = {}
            self._non_asset_classes_cache = frozenset(
                n for n in self.classes
                if self._derive_role_from_parents(n, _cache) == "domain"
            )
        return self._non_asset_classes_cache

    def _invalidate_discovery_cache(self) -> None:
        """Clear all cached role-discovery results (needed after runtime schema changes)."""
        for attr in ("_view_classes_cache", "_asset_classes_cache",
                     "_non_asset_classes_cache", "_view_map_cache"):
            self.__dict__.pop(attr, None)

    def _discover_view_map(self) -> dict:
        """
        Return ``{asset_class: [view_class, …]}`` derived from the schema.

        For each view class, reads ``reportsOn.target`` to find which
        asset class(es) it represents.  Inheriting asset classes are also
        covered — a view targeting ``TransmissionElement`` will appear for
        ``TransmissionLine`` and ``Transformer`` too.

        Unknown target class names are silently skipped here; they are caught
        earlier by :meth:`validate_relation_targets` which is called inside
        ``build_model_from_yaml``.

        Result is cached after the first call.
        """
        if not hasattr(self, "_view_map_cache"):
            result: dict[str, list[str]] = {}
            assets = self._discover_asset_classes()

            for cname, cdef in self.classes.items():
                _, rels = self._collect_inherited_fields(cdef)
                ra = rels.get(self._REPORTS_ON_REL)
                if ra is None:
                    continue
                # RelationDef stores list as .targets, first as .target
                targets_raw = (getattr(ra, "targets", None)
                               or getattr(ra, "target", None))
                if targets_raw is None:
                    for acls in assets:
                        result.setdefault(acls, []).append(cname)
                    continue
                targets = ([targets_raw] if isinstance(targets_raw, str)
                           else list(targets_raw))
                for t in targets:
                    if t not in self.classes:
                        continue   # unknown — already caught by validate_relation_targets
                    result.setdefault(t, []).append(cname)
                    for acls in assets:
                        if t in self._all_parents_of(acls):
                            if cname not in result.get(acls, []):
                                result.setdefault(acls, []).append(cname)

            self._view_map_cache = result
        return self._view_map_cache

    def validate_relation_targets(self) -> list:
        """
        Validate that all relation ``target`` fields in the schema refer to
        known class names.

        Returns a list of error strings; empty means valid.
        Called automatically by ``build_model_from_yaml`` after the schema
        is loaded.

        Example error::

            [GenerationUnit.DispatchResult] reportsOn.target 'GenerationUnitXXX'
            is not a known class. Did you mean: GenerationUnit?
        """
        errors = []
        known = set(self.classes.keys())
        for cname, cdef in self.classes.items():
            _, rels = self._collect_inherited_fields(cdef)
            for rel_id, rel_def in rels.items():
                targets_raw = (getattr(rel_def, "targets", None)
                               or getattr(rel_def, "target", None))
                if targets_raw is None:
                    continue
                targets = ([targets_raw] if isinstance(targets_raw, str)
                           else list(targets_raw))
                for t in targets:
                    if t not in known:
                        close = sorted(c for c in known
                                       if t.lower()[:4] in c.lower())[:4]
                        suggestion = (f"  Did you mean: {', '.join(close)}?"
                                      if close else "")
                        errors.append(
                            f"[{cname}] {rel_id}.target '{t}' is not a "
                            f"known class.{suggestion}"
                        )
        return errors

    def _abbrev_for(self, class_name: str, *, max_len: int = 15) -> str:
        """
        Return the abbreviation for a class name used in Excel sheet names.

        Reads an ``abbrev`` field from the schema class definition if present.
        Falls back to a deterministic truncation: strips common suffixes
        (``View``, ``Unit``, ``Class``) then truncates to ``max_len``.
        """
        cdef = self.classes.get(class_name)
        if cdef is not None:
            abbrev = getattr(cdef, "abbrev", None)
            if abbrev:
                return str(abbrev)[:max_len]
        # Deterministic fallback
        s = class_name
        for suffix in ("DispatchResult", "PowerFlowResult", "DynamicResult",
                       "Result", "Unit", "Element", "Class"):
            if s.endswith(suffix):
                s = s[:-len(suffix)]
                break
        return s[:max_len] if s else class_name[:max_len]

    def _all_parents_of(self, class_name: str) -> set:
        """Return the set of all ancestor class names for a class."""
        cdef = self.classes.get(class_name)
        if cdef is None:
            return set()
        parents = set(getattr(cdef, "parents", []) or [])
        for p in list(parents):
            parents |= self._all_parents_of(p)
        return parents

    def _build_view_index(self) -> Dict[str, Dict[str, Dict]]:
        """
        Build a reverse index:  asset_id  →  {ViewClassName: entity_data_dict}

        Walks every class that uses the reportsOn
        pattern -- Result entities (GenerationUnit.DispatchResult, etc.) --
        finds the reportsOn relation on each, and indexes it under
        the referenced asset id.

        Returns
        -------
        dict
            { asset_id: { "GenerationUnit.DispatchResult": ent, ... }, ... }
        """
        index: Dict[str, Dict[str, Any]] = {}
        # Sorted rather than raw frozenset iteration: frozenset order depends
        # on Python's per-process string-hash randomization, which would
        # otherwise make the rendered view order (and therefore hierarchical
        # YAML diffs) non-deterministic across runs -- git-diff-friendly
        # YAML round-tripping is one of CESDM's stated design goals.
        for vcls in sorted(self._discover_view_classes()):
            for vid, vent in (self.entities.get(vcls) or {}).items():
                data = getattr(vent, "data", {}) or {}
                raw = data.get(self._REPORTS_ON_REL)
                if raw is None:
                    continue
                if isinstance(raw, (list, tuple)):
                    asset_ids = [r for r in raw if r]
                else:
                    asset_ids = [raw]
                for aid in asset_ids:
                    views = index.setdefault(aid, {})
                    if vcls in views:
                        # Merge payloads from multiple entities of the same
                        # Result class representing the same asset (e.g.
                        # results from different analysis runs), so
                        # hierarchical YAML doesn't silently lose data.
                        existing = views[vcls]
                        existing_data = getattr(existing, "data", {}) or {}
                        current_data = getattr(vent, "data", {}) or {}
                        for key, val in current_data.items():
                            if key not in existing_data or existing_data.get(key) in (None, ""):
                                existing_data[key] = val
                    else:
                        views[vcls] = vent
        return index
