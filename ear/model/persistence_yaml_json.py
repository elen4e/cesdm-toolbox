"""ear.model.persistence_yaml_json — Native YAML/JSON persistence

The generic (non-CESDM-specific) flat YAML and JSON import/export
round-trip.

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
Behaviour is unchanged; only module boundaries moved.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Union, Tuple
from difflib import get_close_matches
import os, pathlib
import yaml
from pathlib import Path
import re


class PersistenceYamlJsonMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def export_json(self, path: str | pathlib.Path):
        """
        Export all entities to a nested JSON file grouped by class.

        Parameters
        ----------
        path :
            Output file path. Parent directories must exist.

        Notes
        -----
        The JSON structure has the form::

            {
              "ClassName": {
                "entity_id": {
                  "attributes": [
                    {
                      "id": "<attr_name>",
                      "value": ...,
                      "unit": "...",
                      "provenance_ref": "..."
                    },
                    ...
                  ],
                  "relations": [
                    {
                      "id": "<ref_name>",
                      "target_entity_ids": ["...", "..."]
                    },
                    ...
                  ]
                },
                ...
              },
              ...
            }
        """
        import json

        # only folder part:
        directory = os.path.dirname(path)   # -> "./path/folder"
        # A bare filename (no directory component) has directory == "" --
        # os.makedirs("") raises FileNotFoundError, so only create it when
        # there's an actual directory to create.
        if directory:
            os.makedirs(directory, exist_ok=True)

        out = {}

        class_map = getattr(self, "classes", {}) or {}
        entity_map = getattr(self, "entities", {}) or {}

        for cname, cdef in class_map.items():
            class_name = getattr(cdef, "name", cname)
            ents = entity_map.get(cname, {}) or {}

            # Collect inherited attributes and relations for that class
            attr_defs, ref_defs = self._collect_inherited_fields(cdef)
            attr_names = list(attr_defs.keys())
            ref_names = list(ref_defs.keys())

            class_blob = {}
            for eid, ent in ents.items():
                data = getattr(ent, "data", {}) or {}

                # attributes block as list-of-objects with "id"
                attrs_list = []
                for a in attr_names:
                    if a in data and data[a] not in ("", None):
                        raw = data[a]
                        if isinstance(raw, dict):
                            spec = dict(raw)
                        else:
                            spec = {"value": raw}
                        attrs_list.append({"id": a, **spec})

                # relations block as list-of-objects with "id"
                refs_list = []
                for r in ref_names:
                    if r in data and data[r] not in ("", None):
                        val = data[r]
                        if isinstance(val, (list, tuple)):
                            targets = [v for v in val if v not in ("", None)]
                        else:
                            targets = [val]
                        if targets:
                            refs_list.append({"id": r, "target_entity_ids": targets})

                if attrs_list or refs_list:
                    class_blob[eid] = {"attributes": attrs_list, "relations": refs_list}

            if class_blob:
                out[class_name] = class_blob

        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    def export_yaml(self, path: str | pathlib.Path):
            """
            Export all entities to a nested YAML file grouped by class.

            Parameters
            ----------
            path :
                Output file path. Parent directories must exist.

            Notes
            -----
            The YAML structure mirrors :meth:`export_json`, i.e.::

                {
                  "ClassName": {
                    "entity_id": {
                      "attributes": [
                        { "id": "<attr_name>", "value": ..., "unit": "...", "provenance_ref": "..." },
                        ...
                      ],
                      "relations": [
                        { "id": "<ref_name>", "target_entity_ids": ["...", "..."] },
                        ...
                      ]
                    },
                    ...
                  },
                  ...
                }
            """
            # only folder part:
            directory = os.path.dirname(path)   # -> "./path/folder"
            # A bare filename (no directory component) has directory ==
            # "" -- os.makedirs("") raises FileNotFoundError, so only
            # create it when there's an actual directory to create.
            if directory:
                os.makedirs(directory, exist_ok=True)

            out = {}

            class_map = getattr(self, "classes", {}) or {}
            entity_map = getattr(self, "entities", {}) or {}


            for cname, cdef in class_map.items():
                class_name = getattr(cdef, "name", cname)
                ents = entity_map.get(cname, {}) or {}

                # Collect inherited attributes and relations for that class
                attr_defs, ref_defs = self._collect_inherited_fields(cdef)
                attr_names = list(attr_defs.keys())
                ref_names = list(ref_defs.keys())


                class_blob = {}
                for eid, ent in ents.items():
                    data = getattr(ent, "data", {}) or {}

                    # attributes block as list-of-objects with "id"
                    attrs_list = []
                    for a in attr_names:
                        if a in data and data[a] not in ("", None):
                            raw = data[a]
                            if isinstance(raw, dict):
                                spec = dict(raw)
                            else:
                                spec = {"value": raw}
                            attrs_list.append({"id": a, **spec})

                    # relations block as list-of-objects with "id"
                    refs_list = []
                    for r in ref_names:
                        if r in data and data[r] not in ("", None):
                            val = data[r]
                            if isinstance(val, (list, tuple)):
                                targets = [v for v in val if v not in ("", None)]
                            else:
                                targets = [val]
                            if targets:
                                entry = {"id": r, "target_entity_ids": targets}
                                refs_list.append(entry)

                    if attrs_list or refs_list:
                        class_blob[eid] = {"attributes": attrs_list, "relations": refs_list}

                if class_blob:
                    out[class_name] = class_blob

            from pathlib import Path
            objpath = Path(path)
            new_path = objpath.with_suffix(".yaml")

            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(out, f, sort_keys=False)

    def import_json(self, path: str | pathlib.Path, *, strict_unknown: bool = False):
        """
        Import entities from a nested JSON file (as produced by :meth:`export_json`).

        Parameters
        ----------
        path :
            Input JSON file path.
        strict_unknown :
            If True, raise errors for unknown classes/attributes/relations.
            If False, unknowns are collected in the summary.

        Returns
        -------
        dict
            Summary dictionary with counts of created entities, set attributes,
            set relations, and a list of unknown fields encountered.

        Notes
        -----
        The JSON is expected to follow the export format, where each attribute
        entry under "attributes" is either:

        - a raw scalar value (legacy format), or
        - a full AttributeValue object with keys 'value', 'unit', 'provenance_ref'.
        """
        import json

        class_map = getattr(self, "classes", {}) or {}

        # Precompute known inherited fields per class
        known_attrs = {}
        known_refs  = {}
        for cname, cdef in class_map.items():
            a, r = self._collect_inherited_fields(cdef)
            known_attrs[cname] = set(a.keys())
            known_refs[cname]  = set(r.keys())

        created = set_attr = set_ref = 0
        unknowns = []

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f) or {}

        for class_name, items in (payload or {}).items():
            if class_name not in class_map:
                unknowns.append((class_name, None, "unknown class"))
                if strict_unknown:
                    continue
                else:
                    continue

            cdef = class_map[class_name]

            for eid, block in (items or {}).items():
                # ensure entity exists
                exists = any(eid in ents_by_cls for ents_by_cls in self.entities.values())
                if not exists:
                    self.add_entity(entity_class=class_name, entity_id=eid)
                    created += 1

                # -------- attributes: dict OR list-of-objects-with-id --------
                attrs_block = block.get("attributes") or {}
                if isinstance(attrs_block, dict):
                    attr_items = attrs_block.items()
                elif isinstance(attrs_block, list):
                    attr_items = []
                    for rec in attrs_block:
                        if not isinstance(rec, dict):
                            continue
                        aname = rec.get("id") or rec.get("name")
                        if not aname:
                            continue
                        # pass everything except "id" to add_attribute
                        aval = {k: v for k, v in rec.items() if k != "id"}
                        # if it's just {"value": scalar}, that's fine; add_attribute
                        # already knows how to handle dicts with "value"/"unit"/"provenance_ref".
                        if not aval:
                            continue
                        attr_items.append((aname, aval))
                else:
                    attr_items = []

                for aname, aval in attr_items:
                    if aname in known_attrs[class_name]:
                        if aval not in ("", None):
                            # aval may be a scalar or an AttributeValue dict:
                            # add_attribute handles both cases.
                            self.add_attribute(eid, aname, aval)
                            set_attr += 1
                    else:
                        unknowns.append((class_name, eid, f"unknown attribute: {aname}"))
                        if strict_unknown:
                            continue

                # -------- relations: dict OR list-of-objects-with-id --------
                refs_block = block.get("relations") or {}
                ref_items = []

                if isinstance(refs_block, dict):
                    # old style: { ref_name: id_or_list }
                    ref_items = list(refs_block.items())
                elif isinstance(refs_block, list):
                    # new style: [ {id: ref_name, target_entity_ids: [...]}, ... ]
                    for rec in refs_block:
                        if not isinstance(rec, dict):
                            continue
                        rname = rec.get("id") or rec.get("name")
                        if not rname:
                            continue
                        raw_ids = (
                            rec.get("target_entity_ids")
                            or rec.get("targets")
                            or rec.get("value")
                            or rec.get("target_entity_id")
                        )
                        if raw_ids in ("", None):
                            continue
                        if isinstance(raw_ids, (list, tuple)):
                            ids = [v for v in raw_ids if v not in ("", None)]
                        else:
                            ids = [raw_ids]
                        ref_items.append((rname, ids))

                for rname, rid in ref_items:
                    if rname in known_refs[class_name]:
                        targets = rid if isinstance(rid, (list, tuple)) else [rid]
                        for tgt in targets:
                            if tgt not in ("", None):
                                self.add_relation(entity_id=eid, relation_id=rname, target_entity_id=tgt)
                                set_ref += 1
                    else:
                        unknowns.append((class_name, eid, f"unknown relation: {rname}"))
                        if strict_unknown:
                            continue


        return {
            "created_entities": created,
            "set_attributes": set_attr,
            "set_relations": set_ref,
            "unknowns": unknowns,
        }

    def import_yaml(self, path: str | pathlib.Path, *, strict_unknown: bool = False):
        """
        Import entities from a nested YAML file with a structure similar to the JSON export.

        Supports both:

        Old style (attributes/relations as dicts):

            ClassName:
              entity_id:
                attributes:
                  attr_name: <scalar or {value,unit,provenance_ref}>
                relations:
                  ref_name: target_entity_id_or_list

        New style (attributes/relations as list-of-objects with "id"):

            ClassName:
              entity_id:
                attributes:
                  - id: attr_name
                    value: ...
                    unit: ...
                    provenance_ref: ...
                relations:
                  - id: ref_name
                    target_entity_ids: ["...", "..."]

        Parameters
        ----------
        path :
            Input YAML file path.
        strict_unknown :
            Same semantics as in :meth:`import_json`.

        Returns
        -------
        dict
            Summary information about created and updated entities.
        """
        import yaml

        def _normalize_section(section, key_candidates=("id", "name"), prefix="item"):
            """
            Accept dict or list and always return dict keyed by id/name/fallback.

            This is mainly here to allow for a future list-of-entities format,
            but for current exports (dict of entity_id -> block) it just passes through.
            """
            if not section:
                return {}
            if isinstance(section, dict):
                return section
            if isinstance(section, list):
                out = {}
                for i, rec in enumerate(section):
                    if not isinstance(rec, dict):
                        raise TypeError(f"Expected dict entries, got {type(rec)}: {rec!r}")
                    key = None
                    for kc in key_candidates:
                        v = rec.get(kc)
                        if v not in ("", None):
                            key = v
                            break
                    if key is None:
                        key = f"{prefix}_{i}"
                    out[key] = rec
                return out
            raise TypeError(f"Unsupported section type: {type(section)}")

        class_map = getattr(self, "classes", {}) or {}

        # Precompute known inherited fields per class
        known_attrs: dict[str, set[str]] = {}
        known_refs: dict[str, set[str]] = {}
        for cname, cdef in class_map.items():
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            known_attrs[cname] = set(attrs_def.keys())
            known_refs[cname] = set(refs_def.keys())

        created = 0
        set_attr = 0
        set_ref = 0
        unknowns: list[tuple[str, str | None, str]] = []

        with open(path, "r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}

        for class_name, section in (payload or {}).items():
            if class_name not in class_map:
                # unknown class
                unknowns.append((class_name, None, "unknown class"))
                if strict_unknown:
                    continue
                else:
                    continue

            # section is either:
            # - dict: {entity_id: {...}}
            # - list: [ {id: "...", ...}, ... ]
            entities = _normalize_section(section, key_candidates=("id", "name"), prefix=class_name)

            for eid, block in (entities or {}).items():
                # ensure entity exists
                if class_name not in self.entities:
                    self.entities[class_name] = {}
                if eid not in self.entities[class_name]:
                    self.add_entity(class_name, eid)
                    created += 1

                # -------- attributes: dict OR list-of-objects-with-id --------
                attrs_block = block.get("attributes") or {}
                if isinstance(attrs_block, dict):
                    attr_items = attrs_block.items()
                elif isinstance(attrs_block, list):
                    attr_items = []
                    for rec in attrs_block:
                        if not isinstance(rec, dict):
                            continue
                        aname = rec.get("id") or rec.get("name")
                        if not aname:
                            continue
                        aval = {k: v for k, v in rec.items() if k != "id"}
                        # If user only provided "value", that's fine; add_attribute handles dicts
                        if not aval:
                            continue
                        attr_items.append((aname, aval))
                else:
                    attr_items = []

                for aname, aval in attr_items:
                    if aname in known_attrs[class_name]:
                        if aval not in ("", None):
                            self.add_attribute(eid, aname, aval)
                            set_attr += 1
                    else:
                        unknowns.append((class_name, eid, f"unknown attribute: {aname}"))
                        if strict_unknown:
                            continue

                # -------- relations: dict OR list-of-objects-with-id --------
                refs_block = block.get("relations") or {}
                ref_items: list[tuple[str, list[str]]] = []

                if isinstance(refs_block, dict):
                    # old style: { ref_name: id_or_list }
                    for rname, rid in refs_block.items():
                        if rid in ("", None):
                            continue
                        if isinstance(rid, (list, tuple)):
                            ids = [v for v in rid if v not in ("", None)]
                        else:
                            ids = [rid]
                        ref_items.append((rname, ids))
                elif isinstance(refs_block, list):
                    # new style: [ {id: ref_name, target_entity_ids: [...]}, ... ]
                    for rec in refs_block:
                        if not isinstance(rec, dict):
                            continue
                        rname = rec.get("id") or rec.get("name")
                        if not rname:
                            continue
                        raw_ids = (
                            rec.get("target_entity_ids")
                            or rec.get("targets")
                            or rec.get("value")
                            or rec.get("target_entity_id")
                        )
                        if raw_ids in ("", None):
                            continue
                        if isinstance(raw_ids, (list, tuple)):
                            ids = [v for v in raw_ids if v not in ("", None)]
                        else:
                            ids = [raw_ids]
                        ref_items.append((rname, ids))

                for rname, ids in ref_items:
                    if rname in known_refs[class_name]:
                        targets = [t for t in ids if t not in ("", None)]
                        if not targets:
                            continue
                        # add_relation() is a *set*, not an *append* -- see
                        # import_yaml_hierarchical's identical fix for the
                        # full rationale. Set the first target normally,
                        # then build the real list directly on the
                        # entity's own data if there's more than one.
                        self.add_relation(entity_id=eid, relation_id=rname, target_entity_id=targets[0])
                        set_ref += 1
                        if len(targets) > 1:
                            entity_obj = self.entities.get(class_name, {}).get(eid)
                            if entity_obj is not None and hasattr(entity_obj, "data"):
                                entity_obj.data[rname] = list(targets)
                    else:
                        unknowns.append((class_name, eid, f"unknown relation: {rname}"))
                        if strict_unknown:
                            continue

        return {
            "created_entities": created,
            "set_attributes": set_attr,
            "set_relations": set_ref,
            "unknowns": unknowns,
        }
