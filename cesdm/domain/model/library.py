"""cesdm.domain.model.library — Default-library import

Loads reusable master-data instances (carriers, resources,
technology types) from library/default_library/.

Also provides export filtering via ``include_library``
(``"none"`` | ``"referenced"`` | ``"all"``) so model exports need not
duplicate the full library catalogue.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, ClassVar, Dict, Iterator, List, Literal, Optional, Set, Union
import os
import pathlib
import re
import yaml

IncludeLibrary = Literal["none", "referenced", "all"]


class LibraryMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def _library_entity_id_set(self) -> Set[str]:
        ids = getattr(self, "_library_entity_ids", None)
        if ids is None:
            ids = set()
            self._library_entity_ids = ids
        return ids

    def _mark_library_entity(self, entity_id: str) -> None:
        self._library_entity_id_set().add(str(entity_id))

    def _known_library_entity_ids(self) -> Set[str]:
        """IDs treated as library master data for export filtering.

        Union of (1) entities loaded via :meth:`import_library` /
        :meth:`ensure_default_library_entity` and (2) any in-model id that
        belongs to the generated default-library registry.
        """
        known = set(self._library_entity_id_set())
        try:
            from cesdm.default_library import DEFAULT_LIBRARY_CLASS_BY_ID
            present = {
                eid
                for ents in (self.entities or {}).values()
                for eid in (ents or {})
            }
            known.update(present & set(DEFAULT_LIBRARY_CLASS_BY_ID))
        except ImportError:
            pass
        return known

    def _relation_target_ids(self, entity_id: str) -> Set[str]:
        """Return all relation target ids stored on an entity."""
        cname = self.entity_class(entity_id)
        if not cname:
            return set()
        ent = (self.entities.get(cname) or {}).get(entity_id)
        if ent is None:
            return set()
        data = getattr(ent, "data", {}) or {}
        cdef = self.classes.get(cname)
        if cdef is None:
            return set()
        _, rels = self._collect_inherited_fields(cdef)
        out: Set[str] = set()
        for rn in rels:
            val = data.get(rn)
            if val in (None, ""):
                continue
            if isinstance(val, (list, tuple, set)):
                out.update(str(v) for v in val if v not in (None, ""))
            else:
                out.add(str(val))
        return out

    def _exportable_entity_ids(self, include_library: IncludeLibrary = "referenced") -> Set[str]:
        """Return entity ids that should appear in an export."""
        mode = str(include_library or "referenced").lower()
        if mode not in {"none", "referenced", "all"}:
            raise ValueError(
                "include_library must be one of 'none', 'referenced', 'all'; "
                f"got {include_library!r}"
            )
        all_ids = {
            str(eid)
            for ents in (self.entities or {}).values()
            for eid in (ents or {})
        }
        if mode == "all":
            return all_ids

        library_ids = self._known_library_entity_ids() & all_ids
        non_library = all_ids - library_ids
        if mode == "none":
            return non_library

        # referenced: keep non-library entities + library entities reachable
        # from them (including transitive library→library deps).
        needed_lib: Set[str] = set()
        for eid in non_library:
            for target in self._relation_target_ids(eid):
                if target in library_ids:
                    needed_lib.add(target)
        stack = list(needed_lib)
        while stack:
            cur = stack.pop()
            for target in self._relation_target_ids(cur):
                if target in library_ids and target not in needed_lib:
                    needed_lib.add(target)
                    stack.append(target)
        return non_library | needed_lib

    def _entities_for_export(
        self, include_library: IncludeLibrary = "referenced"
    ) -> Dict[str, Dict[str, Any]]:
        """Shallow-filtered ``entities`` map for export."""
        allowed = self._exportable_entity_ids(include_library)
        return {
            cname: {eid: ent for eid, ent in (ents or {}).items() if eid in allowed}
            for cname, ents in (self.entities or {}).items()
            if any(eid in allowed for eid in (ents or {}))
        }

    @contextmanager
    def _export_entity_scope(
        self, include_library: IncludeLibrary = "referenced"
    ) -> Iterator[None]:
        """Temporarily restrict ``self.entities`` for nested export calls."""
        mode = str(include_library or "referenced").lower()
        if mode == "all":
            yield
            return
        original = self.entities
        self.entities = self._entities_for_export(mode)  # type: ignore[assignment]
        try:
            yield
        finally:
            self.entities = original

    def export_yaml(
        self,
        path: str | pathlib.Path,
        *,
        include_library: IncludeLibrary = "referenced",
    ):
        """Export YAML, optionally omitting unreferenced library entities."""
        with self._export_entity_scope(include_library):
            return super().export_yaml(path)  # type: ignore[misc]

    def export_json(
        self,
        path: str | pathlib.Path,
        *,
        include_library: IncludeLibrary = "referenced",
    ):
        """Export JSON, optionally omitting unreferenced library entities."""
        with self._export_entity_scope(include_library):
            return super().export_json(path)  # type: ignore[misc]

    def import_library(self, library_yaml: str, *, namespace: str | None = None) -> int:
        """
        Load a component library YAML file into the model.

        The library defines shared technology type entities (GeneratorType,
        StorageType, ConverterType, Carrier, etc.) with pre-filled
        techno-economic parameters.  Instances (GenerationUnit, StorageUnit)
        reference these types via ``hasTechnology`` so shared parameters do
        not need to be repeated on every instance.

        Parameters
        ----------
        library_yaml :
            Path to a library YAML file or a directory containing modular YAML files.
        namespace :
            Optional id prefix to avoid clashes when loading multiple libraries.

        Returns
        -------
        int
            Number of entities loaded.
        """
        import yaml as _yaml, pathlib as _pl

        path = _pl.Path(library_yaml)
        if path.is_dir():
            lib = {}
            for part in sorted(path.rglob("*.y*ml")):
                doc = _yaml.safe_load(part.read_text(encoding="utf-8")) or {}
                if not isinstance(doc, dict):
                    continue
                for key, value in doc.items():
                    if key in {"description", "version", "source"}:
                        continue
                    if key in lib and isinstance(lib[key], dict) and isinstance(value, dict):
                        overlap = set(lib[key]) & set(value)
                        if overlap:
                            raise ValueError(f"Duplicate library ids in {part}: {sorted(overlap)}")
                        lib[key].update(value)
                    else:
                        lib[key] = value
        else:
            with open(path, encoding="utf-8") as f:
                lib = _yaml.safe_load(f)

        if not isinstance(lib, dict):
            raise ValueError(f"Library YAML must be a mapping, got {type(lib)}")

        count = 0
        # Skip metadata keys
        skip_keys = {"description", "version", "source"}

        for class_name, entities in lib.items():
            if class_name in skip_keys or not isinstance(entities, dict):
                continue
            for eid, ent_def in entities.items():
                full_id = f"{namespace}.{eid}" if namespace else eid
                # Skip if already present — library should not overwrite model data
                if full_id in self.entities.get(class_name, {}):
                    continue
                try:
                    self.add_entity(class_name, full_id)
                except Exception:
                    continue  # unknown class — skip silently

                self._mark_library_entity(full_id)

                for item in (ent_def or {}).get("attributes", []):
                    try:
                        self.add_attribute(full_id, item["id"], item["value"])
                    except (KeyError, Exception):
                        pass

                # Group relation targets by id so multi-cardinality relations
                # (e.g. MarketZone.coversRegion) keep every target. Repeated
                # add_relation() calls would overwrite — see
                # tests/test_multi_target_relation_preservation.py.
                grouped: Dict[str, List[str]] = {}
                for item in (ent_def or {}).get("relations", []) or []:
                    rid = item.get("id")
                    target = item.get("target")
                    if not rid or target in (None, ""):
                        continue
                    targets = target if isinstance(target, list) else [target]
                    bucket = grouped.setdefault(str(rid), [])
                    for t in targets:
                        tid = str(t)
                        if tid and tid not in bucket:
                            bucket.append(tid)

                for rid, targets in grouped.items():
                    try:
                        if len(targets) == 1:
                            self.add_relation(full_id, rid, targets[0])
                        else:
                            # Write the list directly — add_relation has no
                            # accumulation semantics for 0..* relations.
                            ent = (self.entities.get(class_name) or {}).get(full_id)
                            if ent is not None and hasattr(ent, "data"):
                                ent.data[rid] = list(targets)
                            else:
                                self.add_relation(full_id, rid, targets[0])
                    except (KeyError, Exception):
                        pass

                count += 1

        return count

    def ensure_default_library_entity(self, entity_id: str, expected_class: str | None = None) -> bool:
        """Materialize one generated default-library entity and its dependencies."""
        try:
            from cesdm.default_library import (
                DEFAULT_LIBRARY_CLASS_BY_ID,
                DEFAULT_LIBRARY_ENTITIES,
            )
        except ImportError:
            return False
        class_name = DEFAULT_LIBRARY_CLASS_BY_ID.get(str(entity_id))
        if class_name is None:
            return False
        if expected_class and not self.is_class_derived_from(class_name, expected_class, self.inheritance):
            return False
        if self.has_entity(str(entity_id)):
            self._mark_library_entity(str(entity_id))
            return True
        definition = DEFAULT_LIBRARY_ENTITIES[class_name][str(entity_id)]
        self.add_entity(class_name, str(entity_id))
        self._mark_library_entity(str(entity_id))
        for item in definition.get("attributes", []):
            self.add_attribute(str(entity_id), item["id"], item.get("value"))
        for item in definition.get("relations", []):
            target = str(item["target"])
            self.ensure_default_library_entity(target)
            self.add_relation(str(entity_id), item["id"], target)
        return True

