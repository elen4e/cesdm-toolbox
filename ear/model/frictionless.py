"""ear.model.frictionless — Frictionless Data Package persistence

Generic (non-CESDM) Frictionless Data Package import/export.

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


from ear.constraint import Constraint
from ear.relation_def import RelationDef
from ear.attribute_def import AttributeDef

class FrictionlessMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def export_frictionless(
        self,
        dir_path,
        *,
        name:        str = "ear-model",
        title       = None,
        description: str = "",
        version:     str = "1.0.0",
        contributors = None,
    ):
        """
        Export the model as a Frictionless Data Package (v2 spec).

        Produces one CSV per class that has entities and a ``datapackage.json``
        descriptor with an embedded Table Schema (field names, types,
        constraints, foreign keys) for each resource.

        The output passes ``frictionless validate`` without errors:

        - Resource names are slugified to ``^([-a-z0-9._/])+$``.
        - Custom properties (``cesdm:class``, ``cesdm:unit``, etc.) are
          placed in a ``custom`` object on the resource / field, not at the
          top level where the validator rejects unknown keys.
        - ``constraints`` is omitted when empty.
        - ``description`` is omitted when empty.
        - ``foreignKeys`` reference the slugified resource name, not the
          raw class name.
        - The descriptor uses ``type: "table"`` (v2) instead of the v1
          ``profile`` string.

        This is the **generic** implementation — it serialises all classes
        without domain-specific role classification.  Domain-specific
        subclasses (e.g. CesdmModel) override this method to add role
        metadata and control export ordering.

        Returns
        -------
        pathlib.Path
            Path to the written ``datapackage.json``.
        """
        import json as _json
        import csv  as _csv
        import datetime
        import pathlib as _pl

        base    = _pl.Path(dir_path)
        res_dir = base / "resources"
        res_dir.mkdir(parents=True, exist_ok=True)

        # Build a slug→class lookup so foreign keys can reference the correct
        # resource name even before all resources are appended.
        slug_for: dict = {
            cname: self._slugify_resource_name(cname)
            for cname in self.classes
        }

        resources = []

        for cname, cdef in self.classes.items():
            entities = self.entities.get(cname, {})
            if not entities:
                continue

            attrs_def, rels_def = self._collect_inherited_fields(cdef)
            fieldnames = ["id"] + [a for a in attrs_def if a != "id"] + list(rels_def)

            # 'id' is the entity key — declare it explicitly as a required
            # string field so the schema matches the CSV primary key column.
            fields = [{
                "name": "id",
                "type": "string",
                "constraints": {"required": True},
            }]
            for fn in fieldnames:
                if fn == "id":
                    continue
                if fn in attrs_def:
                    fields.append(
                        self._frictionless_field_for_attr(fn, attrs_def[fn], required=False)
                    )
                elif fn in rels_def:
                    rd = rels_def[fn]
                    cons = self._frictionless_constraints_for_relation(rd)
                    targets = getattr(rd, "target", None)
                    fld: dict = {
                        "name": fn,
                        "type": "string",
                    }
                    desc = getattr(rd, "description", "") or ""
                    if desc:
                        fld["description"] = desc
                    if cons:
                        fld["constraints"] = cons
                    # Custom metadata goes in "custom" (v2 extension point)
                    custom: dict = {"relation": True}
                    if targets:
                        custom["target"] = targets if isinstance(targets, list) else [targets]
                    fld["custom"] = custom
                    fields.append(fld)

            # Foreign keys: reference must use the slugified resource name
            # and only point to resources that actually have entities.
            fkeys = []
            for rn, rd in rels_def.items():
                targets = getattr(rd, "target", None)
                if not targets or isinstance(targets, list):
                    continue
                ref_slug = slug_for.get(targets)
                if ref_slug and self.entities.get(targets):
                    fkeys.append({
                        "fields":    [rn],
                        "reference": {"resource": ref_slug, "fields": ["id"]},
                    })

            table_schema: dict = {"fields": fields}
            if fkeys:
                table_schema["foreignKeys"] = fkeys

            resource_name = slug_for[cname]
            csv_name = f"{cname}.csv"
            csv_path = res_dir / csv_name
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = _csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for eid, ent in entities.items():
                    row: dict = {"id": eid}
                    data = ent.data if hasattr(ent, "data") else {}
                    for an in attrs_def:
                        raw = data.get(an)
                        row[an] = raw["value"] if isinstance(raw, dict) and "value" in raw else raw
                    for rn in rels_def:
                        raw = data.get(rn)
                        if isinstance(raw, list):
                            row[rn] = "|".join(str(v) for v in raw if v)
                        elif raw:
                            row[rn] = str(raw)
                        else:
                            row[rn] = ""
                    writer.writerow(row)

            res_entry: dict = {
                "name":   resource_name,
                "type":   "table",
                "path":   f"resources/{csv_name}",
                "scheme": "file",
                "format": "csv",
                "mediatype": "text/csv",
                "encoding": "utf-8",
                "schema": table_schema,
                # cesdm:class stored in custom so the validator ignores it
                "custom": {"class": cname},
            }
            resources.append(res_entry)

        descriptor = {
            "name":        name,
            "title":       title or name,
            "version":     version,
            "created":     datetime.datetime.utcnow().isoformat() + "Z",
            "resources":   resources,
        }
        if description:
            descriptor["description"] = description
        if contributors:
            descriptor["contributors"] = contributors

        dp_path = base / "datapackage.json"
        dp_path.write_text(
            _json.dumps(descriptor, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return dp_path

    def import_frictionless(
        self,
        dir_path,
        *,
        skip_unknown_classes: bool = True,
        skip_unknown_fields:  bool = True,
    ):
        """
        Import a Frictionless Data Package produced by
        :meth:`export_frictionless`.

        This is the **generic** implementation — it imports resources in the
        order they appear in ``datapackage.json`` without any role-based
        sorting.  Domain-specific subclasses override this to control import
        ordering (e.g. importing domain entities before representation views).

        Returns
        -------
        dict[str, int]
            ``{class_name: entities_imported}``
        """
        import json as _json
        import csv  as _csv
        import pathlib as _pl

        base    = _pl.Path(dir_path)
        dp_path = base / "datapackage.json"
        if not dp_path.exists():
            raise FileNotFoundError(f"datapackage.json not found in {base}")

        descriptor = _json.loads(dp_path.read_text(encoding="utf-8"))
        stats: Dict[str, int] = {}

        for res in descriptor.get("resources", []):
            # Prefer the explicit cesdm:class annotation; fall back to
            # converting the kebab-case resource name back to PascalCase.
            cname = (
                (res.get("custom") or {}).get("class")
                or res.get("cesdm:class")   # backwards compat
                or res.get("name", "")
            )
            if cname not in self.classes:
                # Try converting kebab-case → PascalCase as a last resort
                cname_pascal = "".join(w.capitalize() for w in cname.replace("-", "_").split("_"))
                if cname_pascal in self.classes:
                    cname = cname_pascal
                elif not skip_unknown_classes:
                    raise ValueError(f"Unknown class in datapackage: {res.get('name')!r}")
                else:
                    continue

            csv_path = base / res["path"]
            if not csv_path.exists():
                continue

            cdef = self.classes[cname]
            attrs_def, rels_def = self._collect_inherited_fields(cdef)
            count = 0

            with csv_path.open(newline="", encoding="utf-8") as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    eid = (row.get("id") or "").strip()
                    if not eid:
                        continue
                    self.add_entity(cname, eid)
                    for col, val in row.items():
                        if col == "id" or not val:
                            continue
                        if col in attrs_def:
                            self.add_attribute(eid, col, val)
                        elif col in rels_def:
                            for target in val.split("|"):
                                t = target.strip()
                                if t:
                                    self.add_relation(eid, col, t)
                        elif not skip_unknown_fields:
                            raise ValueError(
                                f"Unknown field {col!r} in resource {cname!r}"
                            )
                    count += 1

            stats[cname] = count

        return stats

    ### Frictionless schema helpers:

    def _frictionless_type_for_attribute(self, t: Optional[str]) -> str:
        """Map CESDM/YAML attribute type string to Frictionless field type."""
        if not t:
            return "string"
        t = str(t).lower()
        if t in ("float", "number", "double", "decimal"):
            return "number"
        if t in ("integer", "int", "long"):
            return "integer"
        if t in ("boolean", "bool"):
            return "boolean"
        # for dates etc. we still export as string; the unit carries semantic
        return "string"

    def _frictionless_constraints_for_attribute(self, ad: AttributeDef) -> Dict[str, Any]:
        """Build Frictionless constraints dict from AttributeDef."""
        cons: Dict[str, Any] = {}
        if ad.required:
            cons["required"] = True

        c = ad.constraints or Constraint()
        if c.enum is not None:
            cons["enum"] = c.enum
        if c.minimum is not None:
            cons["minimum"] = c.minimum
        if c.maximum is not None:
            cons["maximum"] = c.maximum
        if c.pattern is not None:
            cons["pattern"] = c.pattern

        # Note: c.ref is a semantic ref to another class; we don't put this
        # into "constraints" directly but may reflect it in the description.
        return cons

    def _frictionless_constraints_for_relation(self, rd: RelationDef) -> Dict[str, Any]:
        """Build Frictionless constraints dict from RelationDef."""
        cons: Dict[str, Any] = {}
        if rd.required:
            cons["required"] = True
        # We could interpret cardinality here, but since the data is stored
        # as a string/JSON array in a single field, we keep it descriptive only.
        return cons

    def _frictionless_field_for_attr(self, name: str, attr_def, *, required: bool = False) -> dict:
        """
        Build a Frictionless v2-compliant field descriptor for a single attribute.

        - ``description`` is omitted when empty (validator rejects empty strings
          in strict mode).
        - ``constraints`` is omitted when empty.
        - Custom metadata (unit) goes in ``custom`` — the v2 extension point —
          not as a top-level ``cesdm:*`` key which the validator rejects.
        """
        attr_type = getattr(attr_def, "type", None)
        fld: dict = {
            "name": name,
            "type": self._frictionless_type_for_attribute(attr_type),
        }
        desc = getattr(attr_def, "description", "") or ""
        if desc:
            fld["description"] = desc

        cons = self._frictionless_constraints_for_attribute(attr_def)
        if required:
            cons["required"] = True
        if cons:
            fld["constraints"] = cons

        unit = getattr(attr_def, "unit", None)
        if unit:
            # unit may be a plain string ("kWp") or a dict with a constraints.enum
            # e.g. {"constraints": {"enum": ["kWp"]}} — unwrap to the plain string.
            if isinstance(unit, dict):
                enum = (unit.get("constraints") or {}).get("enum")
                unit_str = enum[0] if enum and len(enum) == 1 else (", ".join(enum) if enum else None)
            else:
                unit_str = str(unit)
            if unit_str:
                fld["custom"] = {"unit": unit_str}
        return fld

    ### Schema/meta helpers:
