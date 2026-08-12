"""ear.model.persistence_csv — Generic CSV persistence

Class-keyed CSV import in narrow and wide layouts.

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


class PersistenceCsvMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def import_csv_by_class(self, dir_path: Union[str, pathlib.Path], create_missing_refs: bool = False):

        """
        Import entities from narrow per-class CSV files.

        Parameters
        ----------
        dir_path :
            Directory containing per-class CSV files.
        create_missing_refs :
            If True, relationd entities that do not exist will be auto-created
            as empty shells.
        strict_unknown :
            If True, treat unknown columns/values as errors.

        Returns
        -------
        dict
            Summary of created/updated entities and encountered issues.
        """
        import csv, pathlib, os
        p = pathlib.Path(dir_path)
        if not p.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        # --- pass 1: create all entities we see in files that match known classes
        for file in sorted(p.glob("*.csv")):
            cname = file.stem
            if cname not in self.classes:
                # ignore files that don't correspond to a known class
                continue
            with open(file, "r", encoding="utf-8") as f:
                rdr = csv.DictReader(f)
                for row in rdr:
                    eid = row.get("entity_id")
                    if not eid:
                        continue
                    # already exists anywhere?
                    exists = any(eid in ents_by_cls for ents_by_cls in self.entities.values())
                    if not exists:
                        self.add_entity(entity_class=cname, entity_id=eid)

        # --- pass 2: populate attributes and relations
        for file in sorted(p.glob("*.csv")):
            cname = file.stem
            if cname not in self.classes:
                continue
            cdef = self.classes[cname]
            with open(file, "r", encoding="utf-8") as f:
                rdr = csv.DictReader(f)
                for row in rdr:
                    eid       = row.get("entity_id")
                    attr      = row.get("attribute")
                    val       = row.get("value")
                    ref_meta  = (row.get("relation") or "").strip()

                    if not eid or not attr:
                        continue
                    # skip placeholders
                    if attr.startswith("__"):
                        continue

                    ad = cdef.attributes.get(attr)
                    if not ad:
                        raise ValueError(f"[{cname}:{eid}] Unknown attribute in {file.name}: {attr}")

                    # Relation attribute?
                    if ad.constraints and ad.constraints.ref:
                        ref_cls_expected = ad.constraints.ref
                        # Convention: relationd ID is in 'value'
                        target_entity_id = (val or "").strip()
                        # If someone placed the ID in 'relation' instead (and it's not the class name), accept it
                        if ref_meta and ref_meta != ref_cls_expected:
                            target_entity_id = ref_meta
                        if not target_entity_id:
                            raise ValueError(
                                f"[{cname}:{eid}] Missing relationd id for '{attr}' "
                                f"(expected {ref_cls_expected} id in 'value' or 'relation')."
                            )
                        # Optionally auto-create the relationd entity (covers empty classes like Region)
                        if create_missing_refs and (ref_cls_expected not in self.entities or target_entity_id not in self.entities[ref_cls_expected]):
                            self.add_entity(entity_class=ref_cls_expected, entity_id=target_entity_id)

                        self.add_relation(entity_id=eid, attribute=attr, relation=target_entity_id)
                    else:
                        # Normal value; best-effort coerce based on schema type
                        coerced = self._coerce_for_attr(cname, attr, val)
                        self.add_attribute(entity_id=eid, attribute_id=attr, value=coerced)

    def import_csv_by_class_wide(
            self,
            dir_path: Union[str, pathlib.Path],
            create_missing_refs: bool = False,
        ):
            """
            Read one wide CSV per entity class (file name <ClassName>.csv).
            Columns accepted:
              - entity_id
              - one column per attribute (including inherited)
              - one column per explicit relation (including inherited)
              - optional <name>__ref columns are ignored on import (metadata only)
            Relation cells may contain a single id or a JSON array of ids for multi-cardinality.
            """
            import csv, pathlib, json as _json
            p = pathlib.Path(dir_path)
            if not p.exists():
                return  # nothing to read

            for cname, cdef in self.classes.items():
                file = p / f"{cname}.csv"
                if not file.exists():
                    continue

                attrs_def, refs_def = self._collect_inherited_fields(cdef)
                attr_names = list(attrs_def.keys())
                ref_names  = list(refs_def.keys())

                with open(file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if "entity_id" not in reader.fieldnames:
                        raise ValueError(f"{file.name} missing 'entity_id' column")

                    for row in reader:
                        eid = str(row.get("entity_id", "")).strip()
                        if not eid:
                            continue

                        if cname not in self.entities or eid not in self.entities[cname]:
                            self.add_entity(entity_class=cname, entity_id=eid)

                        # explicit relations
                        for rn in ref_names:
                            if rn not in row:
                                continue
                            raw_val = row.get(rn, "")
                            if raw_val in ("", None):
                                continue

                            # parse single or list
                            targets = None
                            txt = str(raw_val).strip()
                            try:
                                parsed = _json.loads(txt)
                                if isinstance(parsed, list):
                                    targets = [str(v).strip() for v in parsed if v not in ("", None)]
                                else:
                                    targets = [str(parsed).strip()]
                            except Exception:
                                if ";" in txt:
                                    targets = [t.strip() for t in txt.split(";") if t.strip()]
                                elif "," in txt:
                                    targets = [t.strip() for t in txt.split(",") if t.strip()]
                                else:
                                    targets = [txt]

                            if not targets:
                                continue

                            ref_def = refs_def[rn]
                            if create_missing_refs:
                                for tid in targets:
                                    if not ref_def.targets:
                                        continue  # no constraint → nothing to auto-create

                                    existing_cls = self._find_existing_target_class(ref_def, tid)
                                    if existing_cls is None:
                                        # create in the first allowed class
                                        primary_cls = ref_def.targets[0]
                                        self.add_entity(entity_class=primary_cls, entity_id=tid)

                            if len(targets) == 1:
                                self.add_relation(entity_id=eid, relation_id=rn, target_entity_id=targets[0])
                            else:
                                ent = self.entities[cname][eid]
                                self._set_entity_field(cname, eid, ent, rn, targets)

                        # attributes
                        for an in attr_names:
                            if an not in row:
                                continue
                            raw_val = row.get(an, "")
                            if raw_val in ("", None):
                                continue
                            ad = attrs_def[an]
                            coerced = self._coerce_for_attr(cname, an, raw_val)
                            self.add_attribute(entity_id=eid, attribute_id=an, value=coerced)

    def import_csv_by_class_wide_meta(
        self,
        dir_path: str | pathlib.Path,
        create_missing_refs: bool = False,
        strict_unknown: bool = False,
    ):
        """
        Import entities and attributes from wide+meta CSV tables (one file per class).

        Expected column pattern per file:

            entity_id,
            <attr1>, <attr1>__unit, <attr1>__prov,
            <attr2>, <attr2>__unit, <attr2>__prov,
            ...,
            <ref1>, <ref2>, ...

        Parameters
        ----------
        dir_path :
            Directory containing per-class *_wide_meta.csv files.
        create_missing_refs :
            If True, relationd entities that do not exist will be auto-created
            as empty shells.
        strict_unknown :
            If True, treat unknown columns/values as errors.

        Returns
        -------
        dict
            Summary of created/updated entities and encountered issues.
        """
        import csv, pathlib, os, json as _json

        dir_path = pathlib.Path(dir_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        class_map = self.classes
        created_entities = 0
        set_attributes = 0
        set_relations = 0
        unknowns: list[tuple[str, str, str]] = []

        for cname, cdef in class_map.items():
            file = dir_path / f"{cname}_wide_meta.csv"
            if not file.exists():
                continue

            # Collect known attrs/refs for this class
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            attr_names = list(attrs_def.keys())
            ref_names = list(refs_def.keys())

            with open(file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if "entity_id" not in reader.fieldnames:
                    raise ValueError(f"{file.name} missing 'entity_id' column")

                for row in reader:
                    eid = str(row.get("entity_id", "")).strip()
                    if not eid:
                        continue

                    # ensure entity exists
                    if cname not in self.entities or eid not in self.entities[cname]:
                        self.add_entity(entity_class=cname, entity_id=eid)
                        created_entities += 1

                    # attributes: value + meta per attribute
                    for an in attr_names:
                        if an not in row:
                            continue
                        raw_val = row.get(an, "")
                        if raw_val in ("", None):
                            continue

                        # Pick up unit/provenance if present
                        unit = (row.get(f"{an}__unit") or "").strip() or None
                        prov = (row.get(f"{an}__prov") or "").strip() or None

                        # Coerce type according to schema
                        coerced = self._coerce_for_attr(cname, an, raw_val)
                        self.add_attribute(
                            entity_id=eid,
                            attribute=an,
                            value=coerced,
                            unit=unit,
                            provenance_ref=prov,
                        )
                        set_attributes += 1

                    # relations (same as import_csv_by_class_wide)
                    for rn in ref_names:
                        if rn not in row:
                            continue
                        raw_val = row.get(rn, "")
                        if raw_val in ("", None):
                            continue

                        # parse single or list
                        targets = None
                        txt = str(raw_val).strip()
                        try:
                            parsed = _json.loads(txt)
                            if isinstance(parsed, list):
                                targets = [str(v).strip() for v in parsed if v not in ("", None)]
                            else:
                                targets = [str(parsed).strip()]
                        except Exception:
                            targets = [txt]

                        for tgt in targets:
                            if not tgt:
                                continue
                            if create_missing_refs:
                                # create shell if missing
                                if rn in refs_def:
                                    rdef = refs_def[rn]
                                    tgt_class = rdef.target
                                    if tgt_class and tgt_class not in self.entities:
                                        self.add_entity(entity_class=tgt_class, entity_id=tgt)
                            self.add_relation(eid, rn, tgt)
                            set_relations += 1

        return {
            "created_entities": created_entities,
            "set_attributes": set_attributes,
            "set_relations": set_relations,
            "unknowns": unknowns,
        }

    def import_long_csv(self, path: str | pathlib.Path, *, strict_unknown: bool = False):
        """
        Read a 'long' CSV with columns:
        entity_class, entity_id, attribute_id, attribute_value, relation_type, relation_id

        - Sets attributes and relations
        - Matches against inherited schema per class
        - Unknown fields: skipped (collectable) unless strict_unknown=True
        Returns a small summary dict.
        """
        import csv
        from collections import defaultdict

        class_map = getattr(self, "classes", {}) or {}

        # Pre-compute known (inherited) fields per class
        known_attrs = {}
        known_refs  = {}
        for cname, cdef in class_map.items():
            attrs, refs = self._collect_inherited_fields(cdef)
            known_attrs[cname] = set(attrs.keys())
            known_refs[cname]  = set(refs.keys())

        required_cols = {
            "entity_class",
            "entity_id",
            "attribute_id",
            "attribute_value",
            "relation_type",
            "relation_id",
        }

        created_entities = 0
        set_attr = set_ref = 0
        unknowns = []
        per_class_rows = defaultdict(int)

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not required_cols.issubset(reader.fieldnames or []):
                raise ValueError(f"CSV must contain columns exactly: {', '.join(sorted(required_cols))}")

            for i, row in enumerate(reader, start=2):  # header is line 1
                cname = (row.get("entity_class") or "").strip()
                eid   = (row.get("entity_id") or "").strip()

                if not cname or not eid:
                    continue

                if cname not in class_map:
                    msg = "unknown class"
                    unknowns.append((i, cname, eid, "", msg))
                    if strict_unknown:
                        continue
                    else:
                        continue

                # ensure entity exists
                if cname not in self.entities:
                    self.entities[cname] = {}
                if eid not in self.entities[cname]:
                    self.add_entity(cname, eid)
                    created_entities += 1

                # --- Attribute branch ---
                aname = (row.get("attribute_id") or "").strip()
                aval  = row.get("attribute_value")

                if aname:
                    if aname in known_attrs[cname]:
                        if aval not in ("", None):
                            unit = (row.get("attribute_unit") or "").strip() or None
                            prov = (row.get("attribute_provenance") or "").strip() or None

                            # Let add_attribute handle type-coercion and wrapping
                            self.add_attribute(
                                entity_id=eid,
                                attribute_id=aname,
                                value=aval,
                                unit=unit,
                                provenance_ref=prov,
                            )
                            set_attr += 1
                    else:
                        unknowns.append((i, cname, eid, aname, "unknown attribute"))
                        if strict_unknown:
                            # continue to next row (don't process relation in same row)
                            per_class_rows[cname] += 1
                            continue

                # --- Relation branch ---
                rtype = (row.get("relation_type") or "").strip()
                rid   = (row.get("relation_id") or "").strip()

                if rtype:
                    if rtype in known_refs[cname]:
                        if rid not in ("", None):
                            # If a row encodes multiple ids separated by commas, split them:
                            targets = [t.strip() for t in rid.split(",")] if ("," in rid) else [rid]
                            for tgt in targets:
                                if tgt:
                                    self.add_relation(entity_id=eid, relation_id=rtype, target_entity_id=tgt)
                                    set_ref += 1
                    else:
                        unknowns.append((i, cname, eid, rtype, "unknown relation"))
                        if strict_unknown:
                            per_class_rows[cname] += 1
                            continue

                per_class_rows[cname] += 1

        if unknowns:
            print(unknowns)
        return {
            "created_entities": created_entities,
            "set_attributes": set_attr,
            "set_relations": set_ref,
            "unknowns": unknowns,  # list of (line, class, id, field, reason)
            "per_class_rows": dict(per_class_rows),
        }

    ## Advanced / utilities

    # ---------- Pydantic bindings ----------
