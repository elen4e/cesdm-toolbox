"""cesdm.domain.model.csv — CSV persistence (narrow, wide, hierarchical)

CESDM-aware CSV import/export in several layouts, including the
representation-view-aware 'wide' layout.

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


class CsvMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def export_csv_hierarchical(
        self,
        dir_path: Union[str, pathlib.Path],
        *,
        wide: bool = True,
        long: bool = True,
    ) -> None:
        """
        Export the model to hierarchical CSV files.

        **Wide format** (one file per class, suffix ``_wide.csv``):
          - *Non-asset classes* (Carrier, NetworkNode, GeographicalRegion,
            GeneratorType, StorageType, …): one row per entity, flat columns
            for all own attributes and relations.  Written as
            ``<ClassName>_wide.csv``.
          - *Asset instance classes* (GenerationUnit, StorageUnit, DemandUnit,
            TransmissionElement, …): one row per asset, with view attributes
            appended as prefixed columns so the analytical context is
            immediately visible:

            ============================================  =========
            Result class (contains...)                    Prefix
            ============================================  =========
            "Topology"/"Connection"                            ``topo.``
            "Dispatch"/"Operational" (e.g. GenerationUnit.DispatchResult) ``disp.``
            "PowerFlow"/"Injection"/"Withdrawal" (e.g. ElectricalBus.PowerFlowResult) ``pf.``
            "Planning"/"Lifecycle"                             ``plan.``
            "Resource"/"Primary"                               ``res.``
            "Location"/"Spatial"                               ``geo.``
            ============================================  =========

          Classified dynamically from whichever classes
          ``_discover_view_classes()`` finds (Result entities -- the
          only classes left using the reportsOn pattern, see
          CHANGELOG.md), by substring match on the class name, not a
          fixed list -- so a new Result subclass gets the right prefix
          automatically.

          Written as ``<AssetClass>_wide.csv``.

        **Long (tidy) format** (one file ``all_assets_long.csv``):
          One row per attribute or relation value across all asset classes.
          Columns: ``asset_id | asset_class | view_class | field_type |
          field_id | value | unit``.

        Parameters
        ----------
        dir_path :
            Output directory. Created if absent.
        wide :
            Write wide CSV files (default True).
        long :
            Write the long tidy CSV file (default True).
        """
        import csv as _csv

        p = pathlib.Path(dir_path)
        p.mkdir(parents=True, exist_ok=True)

        # ── prefix map: view class → column prefix ────────────────────────
        _PREFIX: Dict[str, str] = {}
        for vcls in self._discover_view_classes():
            if "Topology" in vcls or "Connection" in vcls:
                _PREFIX[vcls] = "topo."
            elif "Dispatch" in vcls or "Operational" in vcls:
                _PREFIX[vcls] = "disp."
            elif "PowerFlow" in vcls or "Injection" in vcls or "Withdrawal" in vcls:
                _PREFIX[vcls] = "pf."
            elif "Planning" in vcls or "Lifecycle" in vcls:
                _PREFIX[vcls] = "plan."
            elif "Resource" in vcls or "Primary" in vcls:
                _PREFIX[vcls] = "res."
            elif "Location" in vcls or "Spatial" in vcls:
                _PREFIX[vcls] = "geo."
            else:
                _PREFIX[vcls] = "view."

        view_index = self._build_view_index()
        asset_cls_set    = self._discover_asset_classes()
        non_asset_cls_set = self._discover_non_asset_classes()

        # ── shared helpers ────────────────────────────────────────────────

        def _unwrap(raw):
            """Return (value_str, unit_str) from an attribute raw value."""
            if isinstance(raw, dict):
                v = raw.get("value", "")
                u = raw.get("unit", "")
            else:
                v, u = raw, ""
            return ("" if v is None else str(v)), ("" if u is None else str(u))

        def _entity_attrs_refs(ent, cname, skip_rels=None):
            """Yield (field_type, field_id, value_str, unit_str) for one entity."""
            cdef = self.classes.get(cname)
            if not cdef:
                return
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            data = getattr(ent, "data", {}) or {}
            skip = set(skip_rels or [])

            for aname in attrs_def:
                if aname in data and data[aname] not in ("", None):
                    v, u = _unwrap(data[aname])
                    yield "attribute", aname, v, u

            for rname in refs_def:
                if rname in skip or rname not in data or data[rname] in ("", None):
                    continue
                val = data[rname]
                targets = [str(x) for x in val if x not in ("", None)] \
                    if isinstance(val, (list, tuple)) else [str(val)]
                yield "relation", rname, "|".join(targets), ""

        # ── wide: non-asset classes (flat) ────────────────────────────────
        if wide:
            for ncls in sorted(self._discover_non_asset_classes()):
                ents = self.entities.get(ncls) or {}
                if not ents:
                    continue

                cdef = self.classes.get(ncls)
                if not cdef:
                    continue
                attrs_def, refs_def = self._collect_inherited_fields(cdef)

                col_order: List[str] = ["entity_id"]
                col_set: set = {"entity_id"}
                for name in list(refs_def) + list(attrs_def):
                    if name not in col_set:
                        col_order.append(name)
                        col_set.add(name)

                rows = []
                for eid, ent in ents.items():
                    row: Dict[str, str] = {c: "" for c in col_order}
                    row["entity_id"] = eid
                    for _, fname, fval, _ in _entity_attrs_refs(ent, ncls):
                        if fname in col_set:
                            row[fname] = fval
                    rows.append(row)

                out_path = p / f"{ncls}_wide.csv"
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    w = _csv.DictWriter(f, fieldnames=col_order)
                    w.writeheader()
                    w.writerows(rows)

        # ── wide: asset classes (with prefixed view columns) ──────────────
        if wide:
            for acls in sorted(self._discover_asset_classes()):
                ents = self.entities.get(acls) or {}
                if not ents:
                    continue

                # Restrict to view classes valid for this asset class only.
                # This prevents columns from sibling view classes appearing
                # (e.g. GenerationUnit.DispatchResult columns in StorageUnit_wide.csv)
                # which would cause incorrect view reconstruction on import.
                allowed_views = self._discover_view_map().get(acls, list(self._discover_view_classes()))

                cdef = self.classes.get(acls)
                col_order = ["asset_id"]
                col_set: set = {"asset_id"}

                # Asset-level fields
                if cdef:
                    attrs_def, refs_def = self._collect_inherited_fields(cdef)
                    for name in list(refs_def) + list(attrs_def):
                        if name not in col_set:
                            col_order.append(name)
                            col_set.add(name)

                # View-level fields — restricted to allowed views only
                for vcls in allowed_views:
                    vcdef = self.classes.get(vcls)
                    if not vcdef:
                        continue
                    prefix = _PREFIX.get(vcls, "view.")
                    vattrs, vrefs = self._collect_inherited_fields(vcdef)
                    for name in list(vrefs) + list(vattrs):
                        if name == self._REPORTS_ON_REL:
                            continue
                        col = f"{prefix}{name}"
                        if col not in col_set:
                            col_order.append(col)
                            col_set.add(col)

                rows = []
                for eid, ent in ents.items():
                    row: Dict[str, str] = {c: "" for c in col_order}
                    row["asset_id"] = eid

                    for _, fname, fval, _ in _entity_attrs_refs(ent, acls):
                        if fname in col_set:
                            row[fname] = fval

                    # Emit view data only for allowed view classes
                    for vcls, vent in (view_index.get(eid) or {}).items():
                        if vcls not in allowed_views:
                            continue
                        prefix = _PREFIX.get(vcls, "view.")
                        for _, fname, fval, _ in _entity_attrs_refs(
                            vent, vcls, skip_rels=[self._REPORTS_ON_REL]
                        ):
                            col = f"{prefix}{fname}"
                            if col in col_set:
                                row[col] = fval

                    rows.append(row)

                out_path = p / f"{acls}_wide.csv"
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    w = _csv.DictWriter(f, fieldnames=col_order)
                    w.writeheader()
                    w.writerows(rows)

        # ── long (tidy) ───────────────────────────────────────────────────
        if long:
            long_cols = ["entity_id", "entity_class", "view_class",
                         "field_type", "field_id", "value", "unit"]
            long_rows = []

            # Non-asset entities (no views — view_class == entity_class)
            for ncls in sorted(self._discover_non_asset_classes()):
                for eid, ent in (self.entities.get(ncls) or {}).items():
                    for ftype, fname, fval, funit in _entity_attrs_refs(ent, ncls):
                        long_rows.append({
                            "entity_id":    eid,
                            "entity_class": ncls,
                            "view_class":   ncls,
                            "field_type":   ftype,
                            "field_id":     fname,
                            "value":        fval,
                            "unit":         funit,
                        })

            # Asset instances + their views
            for acls in sorted(self._discover_asset_classes()):
                for eid, ent in (self.entities.get(acls) or {}).items():
                    for ftype, fname, fval, funit in _entity_attrs_refs(ent, acls):
                        long_rows.append({
                            "entity_id":    eid,
                            "entity_class": acls,
                            "view_class":   acls,
                            "field_type":   ftype,
                            "field_id":     fname,
                            "value":        fval,
                            "unit":         funit,
                        })
                    for vcls, vent in (view_index.get(eid) or {}).items():
                        for ftype, fname, fval, funit in _entity_attrs_refs(
                            vent, vcls, skip_rels=[self._REPORTS_ON_REL]
                        ):
                            long_rows.append({
                                "entity_id":    eid,
                                "entity_class": acls,
                                "view_class":   vcls,
                                "field_type":   ftype,
                                "field_id":     fname,
                                "value":        fval,
                                "unit":         funit,
                            })

            out_path = p / "all_entities_long.csv"
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = _csv.DictWriter(f, fieldnames=long_cols)
                w.writeheader()
                w.writerows(long_rows)

    def import_csv_by_class_wide(
        self,
        dir_path: Union[str, pathlib.Path],
        *,
        skip_unknown_classes: bool = True,
        skip_unknown_fields:  bool = True,
    ) -> Dict[str, int]:
        """
        Import wide CSV files produced by :meth:`export_csv_by_class_wide`.

        Reads every ``<ClassName>.csv`` file in ``dir_path``.  The first
        column must be ``entity_id``; remaining columns are routed to
        ``add_attribute`` or ``add_relation`` via the schema.

        Parameters
        ----------
        dir_path :
            Directory containing ``<ClassName>.csv`` files.
        skip_unknown_classes :
            If True (default), skip CSV files whose name does not match
            any schema class.  If False, raise ``KeyError``.
        skip_unknown_fields :
            If True (default), skip columns not declared in the schema.
            If False, raise ``KeyError``.

        Returns
        -------
        dict
            ``{class_name: n_entities_imported}``
        """
        import csv as _csv
        import json as _json

        p = pathlib.Path(dir_path)
        stats: Dict[str, int] = {}

        for csv_file in sorted(p.glob("*.csv")):
            cname = csv_file.stem
            cdef  = self.classes.get(cname)
            if cdef is None:
                if not skip_unknown_classes:
                    raise KeyError(
                        f"File '{csv_file.name}' maps to unknown class '{cname}'"
                    )
                continue

            attrs_def, rels_def = self._collect_inherited_fields(cdef)

            with csv_file.open(newline="", encoding="utf-8-sig") as f:
                reader = _csv.DictReader(f)
                count  = 0
                for row in reader:
                    eid = str(row.get("entity_id", "")).strip()
                    if not eid:
                        continue

                    # Base lookup resources may contain inherited subclass rows
                    # for Frictionless FK validation. If the same entity id
                    # already exists in another class, skip this lookup duplicate.
                    if eid not in self.entities.get(cname, {}):
                        # Strict validation: if AllEntities.csv declared a
                        # different class for this id, reject it.
                        if _has_all_assets and eid in _all_assets_index:
                            declared_cls = _all_assets_index[eid]
                            if declared_cls != cname:
                                try:
                                    is_subclass = self.is_class_derived_from(
                                        declared_cls, cname, self.inheritance)
                                except Exception:
                                    is_subclass = False
                                if not is_subclass:
                                    raise ValueError(
                                        f"Strict import error: entity '{eid}' "
                                        f"is declared as '{declared_cls}' in "
                                        f"AllEntities.csv but found in '"
                                        f"{cname}.csv'. Round-trip integrity "
                                        f"violated."
                                    )
                        if any(
                            eid in _ents and _cls != cname
                            for _cls, _ents in (self.entities or {}).items()
                        ):
                            continue
                        self.add_entity(cname, eid)

                    for col, val in row.items():
                        if col == "entity_id" or not val or val.strip() == "":
                            continue
                        val = val.strip()
                        col_rel = (getattr(self, "_RELATION_ID_ALIASES", {}) or {}).get(col, col)
                        col_attr = self._attribute_id_for_schema_lookup(col)
                        if col_rel in rels_def:
                            if val.startswith("["):
                                try:
                                    targets = _json.loads(val)
                                    for t in targets:
                                        if t:
                                            self.add_relation(eid, col_rel, str(t))
                                except Exception:
                                    self.add_relation(eid, col_rel, val)
                            else:
                                self.add_relation(eid, col_rel, val)
                        elif col_attr in attrs_def or self._is_legacy_attribute_write(col):
                            # Coerce numeric strings
                            coerced: Any = val
                            if self._is_legacy_attribute_write(col):
                                coerced = val.lower() in ("true", "1", "yes")
                            else:
                                try:
                                    if "." in val:
                                        coerced = float(val)
                                    else:
                                        coerced = int(val)
                                except (ValueError, TypeError):
                                    coerced = val
                            self.add_attribute(eid, col, coerced)
                        else:
                            if not skip_unknown_fields:
                                raise KeyError(
                                    f"Column '{col}' in '{csv_file.name}' "
                                    f"is not a known field of class '{cname}'"
                                )
                    count += 1
            stats[cname] = count

        return stats

    # ================================================================== #
    #  import_datapackage                                                   #
    # ================================================================== #

    def export_csv_by_class(self, dir_path: Union[str, pathlib.Path], include_placeholders: bool = True):
        """
        Export entities as narrow CSV tables, one file per class.

        Parameters
        ----------
        dir_path :
            Directory where the CSV files will be written.
        include_placeholders :
            If True, include placeholder rows/fields for attributes that are not set
            on a given entity (useful for templates).
        include_ref_meta :
            If True, include extra metadata columns for relations.

        Notes
        -----
        The exact column layout is documented in the module level docstring
        and in the Frictionless Table Schema created by
        :meth:`export_csv_by_class_with_schema`.
        """
        import csv, pathlib, json as _json

         # create the folder if does not exist
        os.makedirs(dir_path, exist_ok=True)

        p = pathlib.Path(dir_path)
        p.mkdir(parents=True, exist_ok=True)

        # Iterate over all classes so we also export placeholder tables for classes
        # without any entity instances (required for stable schemas/foreign keys).
        for cname, cdef in self.classes.items():
            ents = self.entities.get(cname, {})
            rows = []
            for eid, ent in ents.items():
                wrote_any = False
                for an, ad in cdef.attributes.items():
                    if an in ent.data:
                        raw = ent.data[an]
                        v, unit, prov = self._unwrap_attributevalue(raw)

                        ref = ad.constraints.ref if ad.constraints and ad.constraints.ref else ""

                        # In narrow CSV we only export the core value;
                        # unit/provenance are available via schema or other exports.
                        if isinstance(v, (dict, list)):
                            sval = _json.dumps(v, ensure_ascii=False)
                        else:
                            sval = v

                        rows.append({
                            "entity_id": eid,
                            "attribute": an,
                            "value": sval,
                            "relation": ref,
                        })
                        wrote_any = True

                # optional placeholder for attribute-less classes (e.g., Region)
                if include_placeholders and not wrote_any:
                    rows.append({
                        "entity_id": eid,
                        "attribute": "__exists__",
                        "value": "",
                        "relation": ""
                    })

            # Always write a file (with header), even if empty → helps round-trips
            with open(p / f"{cname}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["entity_id", "attribute", "value", "relation"])
                w.writeheader()
                for r in rows:
                    w.writerow(r)

    def export_csv_by_class_with_schema(self, dir_path: Union[str, pathlib.Path], include_placeholders: bool = True,):
        """
        Export narrow per-class CSV files together with Frictionless Table Schemas.

        Parameters
        ----------
        dir_path :
            Directory for the CSV and ``*.schema.json`` files.
        include_placeholders :
            Passed through to :meth:`export_csv_by_class`.
        """

        import json as _json
        import pathlib as _pl

        p = _pl.Path(dir_path)
        # run the existing exporter
        self.export_csv_by_class(p, include_placeholders=include_placeholders)

        for cname, cdef in self.classes.items():
            csv_path = p / f"{cname}.csv"
            if not csv_path.exists():
                continue

            attrs_def = cdef.attributes or {}
            attr_names = sorted(attrs_def.keys())
            attr_enum = list(attr_names)
            if include_placeholders:
                attr_enum.append("__exists__")

            # collect possible ref-target class names used on attributes
            ref_targets = sorted(
                {ad.constraints.ref for ad in attrs_def.values()
                 if ad.constraints and ad.constraints.ref}
            )

            fields = [
                {
                    "name": "entity_id",
                    "type": "string",
                    "description": f"ID of the entity within class '{cname}'.",
                    "constraints": {"required": True},
                },
                {
                    "name": "attribute",
                    "type": "string",
                    "description": "Attribute name for this entity.",
                    "constraints": {"enum": attr_enum},
                },
                {
                    "name": "value",
                    "type": "string",
                    "description": (
                        "Attribute value; complex values (dict/list) are JSON-encoded. "
                        "Different attributes have different types/constraints; see YAML."
                    ),
                },
                {
                    "name": "relation",
                    "type": "string",
                    "description": (
                        "Target class for the attribute's ref constraint, if any; otherwise empty."
                    ),
                    **({"constraints": {"enum": ref_targets}} if ref_targets else {}),
                },
            ]

            schema = {
                "$schema": "https://frictionlessdata.io/schemas/table-schema.json",
                "name": self._slugify_resource_name(cname),
                "title": f"CESDM per-class export: {cname}",
                "fields": fields,
                "primaryKey": ["entity_id", "attribute"],
            }

            schema_path = csv_path.with_suffix(csv_path.suffix + ".schema.json")
            schema_path.write_text(
                _json.dumps(schema, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def export_csv_by_class_wide(self, dir_path: Union[str, pathlib.Path], include_placeholders: bool = True, include_ref_meta: bool = True,):

        """
        Export entities as wide CSV tables, one file per class.

        Parameters
        ----------
        dir_path :
            Directory where the CSV files will be written.
        include_placeholders :
            If True, also create columns for attributes not used by any entity.
        include_ref_meta :
            If True, include extra metadata columns for relations.

        Notes
        -----
        Each CSV contains one row per entity and one column per attribute/relation.
        """
        import csv, pathlib, json as _json
        p = pathlib.Path(dir_path)
        p.mkdir(parents=True, exist_ok=True)

        for cname, cdef in self.classes.items():
            ents = self.entities.get(cname, {})

            if len(ents)==0:
                continue

            # Inheritance-aware merged fields
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            attr_names = list(attrs_def.keys())
            ref_names  = list(refs_def.keys())

            # Build header
            header = ["entity_id"]
            for rn in ref_names:
                header.append(rn)
                # if include_ref_meta:
                #     header.append(f"{rn}__ref")
            for an in attr_names:
                header.append(an)
                ad = attrs_def[an]
                # if include_ref_meta and ad.constraints and ad.constraints.ref:
                #     header.append(f"{an}__ref")

            rows = []
            for eid, ent in ents.items():
                row = {h: "" for h in header}
                row["entity_id"] = eid
                wrote_any = False

                data = getattr(ent, "data", {}) or {}

                # explicit relations
                for rn in ref_names:
                    if rn in data and data[rn] not in ("", None):
                        val = data[rn]
                        sval = _json.dumps(val, ensure_ascii=False) if isinstance(val, (list, dict, tuple)) else str(val)
                        row[rn] = sval
                        wrote_any = True
                        # if include_ref_meta:
                        #     tgt = refs_def[rn].target if hasattr(refs_def[rn], "target") else ""
                        #     row[f"{rn}__ref"] = tgt

                # attributes
                for an in attr_names:
                    if an in data and data[an] not in ("", None):
                        raw = data[an]
                        v, unit, prov = self._unwrap_attributevalue(raw)

                        # store only the core value into the wide CSV cell
                        if isinstance(v, (dict, list)):
                            sval = _json.dumps(v, ensure_ascii=False)
                        else:
                            sval = str(v)

                        row[an] = sval
                        wrote_any = True
                        ad = attrs_def[an]

                if wrote_any or include_placeholders:
                    rows.append(row)

            with open(p / f"{cname}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=header)
                w.writeheader()
                for r in rows:
                    w.writerow(r)

    def export_csv_by_class_wide_with_schema(self, dir_path: Union[str, pathlib.Path], include_placeholders: bool = True,):

        """
        Convenience wrapper:
        - calls export_csv_by_class_wide(dir_path, include_placeholders=...)
        - for each <ClassName>.csv, writes <ClassName>.csv.schema.json
          with a Frictionless Table Schema describing the *wide* format:
            - entity_id
            - one column per relation (including inherited)
            - one column per attribute (including inherited)
        Types and constraints (enum, min, max, pattern, required, default)
        are derived from the YAML schema (AttributeDef / RelationDef).
        """

        import json as _json
        import pathlib as _pl

        p = _pl.Path(dir_path)
        # run the existing exporter (no __ref meta columns in CSV itself)
        self.export_csv_by_class_wide(
            dir_path=p,
            include_placeholders=include_placeholders,
            include_ref_meta=False,
        )

        class_map = getattr(self, "classes", {}) or {}
        entity_map = getattr(self, "entities", {}) or {}

        for cname, cdef in class_map.items():
            ents = entity_map.get(cname, {})

            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            attr_names = list(attrs_def.keys())
            ref_names  = list(refs_def.keys())

            fields = [
                {
                    "name": "entity_id",
                    "type": "string",
                    "description": f"ID of the entity within class '{cname}'.",
                    "constraints": {"required": True},
                }
            ]

            foreign_keys = []

            # Relations: one column per ref (id or JSON array of ids)
            for rn in ref_names:
                rd = refs_def[rn]
                ref_cons = self._frictionless_constraints_for_relation(rd)
                ref_field = {
                    "name": rn,
                    "type": "string",  # IDs (or JSON array) are serialized as strings
                    "description": (
                        f"Relationd entity id(s) for relation '{rn}' "
                        f"targeting class '{rd.target}'. "
                        "Multi-valued relations are encoded as a JSON array."
                    ),
                }
                if ref_cons:
                    ref_field["constraints"] = ref_cons
                fields.append(ref_field)

                # Add Frictionless foreign key for single-valued relations with exactly one target
                if (rd.cardinality in ("1", "0..1", "1..1") and len(getattr(rd, "targets", []) or []) == 1):
                    tgt = rd.targets[0]
                    foreign_keys.append({
                        "fields": rn,
                        "reference": {"resource": self._slugify_resource_name(f"{tgt}"), "fields": "entity_id"},
                    })

            # Attributes: one column per attribute
            for an in attr_names:
                ad = attrs_def[an]
                ftype = self._frictionless_type_for_attribute(ad.type)
                cons = self._frictionless_constraints_for_attribute(ad)

                desc = ad.description or f"Attribute '{an}' of class '{cname}'."
                if ad.constraints and ad.constraints.ref:
                    desc += f" (Relation to class '{ad.constraints.ref}'.)"

                field = {
                    "name": an,
                    "type": ftype,
                    "description": desc,
                }
                if cons:
                    field["constraints"] = cons
                if ad.default is not None:
                    field["default"] = ad.default

                # CESDM-specific metadata (units, grouping) as an extension
                cesdm_meta = {}
                if getattr(ad, "unit", None) is not None:
                    if isinstance(ad.unit, str):
                        cesdm_meta["unit"] = {"constraints": {"enum": [ad.unit]}}
                    else:
                        cesdm_meta["unit"] = ad.unit
                if getattr(ad, "group", None) is not None:
                    cesdm_meta["group"] = ad.group
                if getattr(ad, "order", None) is not None:
                    cesdm_meta["order"] = ad.order
                if cesdm_meta:
                    field["cesdm"] = cesdm_meta

                fields.append(field)

            schema = {
                "$schema": "https://frictionlessdata.io/schemas/table-schema.json",
                "name": self._slugify_name(cname),
                "title": f"CESDM per-class wide export: {cname}",
                "fields": fields,
                "primaryKey": ["entity_id"],
            }

            if foreign_keys:
                schema["foreignKeys"] = foreign_keys

            csv_path = p / f"{cname}.csv"
            schema_path = csv_path.with_suffix(csv_path.suffix + ".schema.json")
            schema_path.write_text(
                _json.dumps(schema, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def export_csv_by_class_wide_meta(
        self,
        dir_path: str,
        include_placeholders: bool = False,
    ):
        """
        Export entities as wide CSV tables (one file per class), including
        attribute unit and provenance alongside each attribute.

        Columns per class:

            entity_id,
            <attr1>, <attr1>__unit, <attr1>__prov,
            <attr2>, <attr2>__unit, <attr2>__prov,
            ...,
            <ref1>, <ref2>, ...

        Parameters
        ----------
        dir_path :
            Directory where the CSV files will be written.
        include_placeholders :
            If True, include placeholder rows for entities with no attributes
            set (useful for templates).
        """
        import csv, pathlib, json as _json

        p = pathlib.Path(dir_path)
        p.mkdir(parents=True, exist_ok=True)

        for cname, ents in self.entities.items():
            cdef = self.classes[cname]

            # Collect inherited attributes and relations
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            attr_names = list(attrs_def.keys())
            ref_names = list(refs_def.keys())

            # Build fieldnames: entity_id, then triples per attribute, then refs
            fieldnames = ["entity_id"]
            for an in attr_names:
                fieldnames.append(an)
                fieldnames.append(f"{an}__unit")
                fieldnames.append(f"{an}__prov")
            fieldnames.extend(ref_names)

            rows = []

            for eid, ent in ents.items():
                data = getattr(ent, "data", {}) or {}
                row = {fn: "" for fn in fieldnames}
                row["entity_id"] = eid

                wrote_any = False

                # Attributes (value + unit + provenance_per_attr)
                for an in attr_names:
                    if an in data and data[an] not in ("", None):
                        raw = data[an]
                        v, unit, prov = self._unwrap_attributevalue(raw)

                        # value stringification
                        if isinstance(v, (dict, list)):
                            sval = _json.dumps(v, ensure_ascii=False)
                        else:
                            sval = "" if v is None else str(v)

                        row[an] = sval
                        row[f"{an}__unit"] = "" if unit is None else str(unit)
                        row[f"{an}__prov"] = "" if prov is None else str(prov)
                        wrote_any = True

                # Relations (same as export_csv_by_class_wide)
                for rn in ref_names:
                    if rn not in data or data[rn] in ("", None):
                        continue
                    val = data[rn]
                    if isinstance(val, (list, tuple, set)):
                        row[rn] = _json.dumps(list(val), ensure_ascii=False)
                    else:
                        row[rn] = str(val)
                    wrote_any = True

                if wrote_any or include_placeholders:
                    rows.append(row)

            # Always write file with header
            with open(p / f"{cname}_wide_meta.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                for r in rows:
                    w.writerow(r)

    def export_long_csv(self, path: str | pathlib.Path):
        """
        Write a 'long' CSV with columns:
        entity_class, entity_id, attribute_id, attribute_value, relation_type, relation_id

        - One row per attribute (value + optional unit)
        - One row per relation target (relation_type + relation_id)
        - Includes inherited attributes & relations
        """
        import csv

        # only folder part:
        directory = os.path.dirname(path)   # -> "./path/folder"
        # A bare filename (no directory component) has directory == "" --
        # os.makedirs("") raises FileNotFoundError, so only create it when
        # there's an actual directory to create.
        if directory:
            os.makedirs(directory, exist_ok=True)

        class_map = getattr(self, "classes", {}) or {}
        entity_map = getattr(self, "entities", {}) or {}

        fieldnames = [
            "entity_class",
            "entity_id",
            "attribute_id",
            "attribute_value",
            "attribute_unit",
            "attribute_provenance",
            "relation_type",
            "relation_id",
        ]

        rows = []
        for class_name, cdef in class_map.items():
            attrs, refs = self._collect_inherited_fields(cdef)
            attr_names = list(attrs.keys())
            ref_names  = list(refs.keys())

            ents = entity_map.get(class_name, {}) or {}
            for eid, ent in ents.items():
                data = getattr(ent, "data", {}) or {}

                # Attributes (1 row per attribute)
                for a in attr_names:
                    if a not in data or data[a] in ("", None):
                        continue
                    raw = data[a]
                    v, unit, prov = self._unwrap_attributevalue(raw)

                    rows.append({
                        "entity_class": class_name,
                        "entity_id": eid,
                        "attribute_id": a,
                        "attribute_value": v,
                        "attribute_unit": unit or "",
                        "attribute_provenance": prov or "",
                        "relation_type": "",
                        "relation_id": "",
                    })

                # Relations (1 row per target id)
                for r in ref_names:
                    if r not in data or data[r] in ("", None):
                        continue
                    value = data[r]
                    targets = value if isinstance(value, (list, tuple)) else [value]
                    for tgt in targets:
                        if tgt in ("", None):
                            continue
                        rows.append({
                            "entity_class": class_name,
                            "entity_id": eid,
                            "attribute_id": "",
                            "attribute_value": "",
                            "attribute_unit": "",
                            "attribute_provenance": "",
                            "relation_type": r,
                            "relation_id": tgt,
                        })

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def export_long_csv_with_schema(self, path: Union[str, pathlib.Path]):
        """
        Export a long CSV together with a Frictionless Table Schema.

        Parameters
        ----------
        path :
            Output CSV file path. The corresponding schema will be written
            to ``<path>.schema.json`` or a similar name.
        """

        import json as _json
        import pathlib as _pl

        p = _pl.Path(path)
        # run the existing exporter
        self.export_long_csv(str(p))

        class_map = getattr(self, "classes", {}) or {}

        all_attr_names = set()
        all_ref_names = set()
        for cname, cdef in class_map.items():
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            all_attr_names.update(attrs_def.keys())
            all_ref_names.update(refs_def.keys())

        schema = {
            "$schema": "https://frictionlessdata.io/schemas/table-schema.json",
            "name": self._slugify_name(p.stem),
            "title": f"CESDM long export: {p.name}",
            "fields": [
                {
                    "name": "entity_class",
                    "type": "string",
                    "description": "Name of the entity class.",
                    "constraints": {
                        "required": True,
                        "enum": sorted(class_map.keys()),
                    },
                },
                {
                    "name": "entity_id",
                    "type": "string",
                    "description": "ID of the entity within the class.",
                    "constraints": {
                        "required": True,
                    },
                },
                {
                    "name": "attribute_id",
                    "type": "string",
                    "description": "Name of the attribute (empty when row represents a relation).",
                    "constraints": {
                        "enum": sorted(all_attr_names),
                    },
                },
                {
                    "name": "attribute_value",
                    "type": "string",
                    "description": "Serialized attribute value (empty for relation rows).",
                },
                {
                    "name": "relation_type",
                    "type": "string",
                    "description": "Relation name / role (empty for attribute rows).",
                    "constraints": {
                        "enum": sorted(all_ref_names),
                    },
                },
                {
                    "name": "relation_id",
                    "type": "string",
                    "description": "Target entity id for the relation (empty for attribute rows).",
                },
            ],
            "primaryKey": [
                "entity_class",
                "entity_id",
                "attribute_id",
                "relation_type",
                "relation_id",
            ],
        }

        schema_path = p.with_suffix(p.suffix + ".schema.json")
        schema_path.write_text(
            _json.dumps(schema, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def import_csv_hierarchical(
        self,
        dir_path: Union[str, pathlib.Path],
        *,
        create_missing_refs: bool = False,
        strict_unknown: bool = False,
    ) -> Dict[str, Any]:
        """
        Import entities from the hierarchical CSV files produced by
        :meth:`export_csv_hierarchical`.

        Two file patterns are recognised and processed independently:

        **Non-asset wide files** (``<ClassName>_wide.csv``):
          Columns: ``entity_id`` + one column per attribute or relation.
          Loaded directly as flat entities — no view reconstruction.

        **Asset wide files** (``<AssetClass>_wide.csv``):
          Columns: ``asset_id`` for identity, plain columns for asset-level
          fields, and **prefixed columns** for view fields:

          ========  =============================================
          Prefix    Result class name contains...
          ========  =============================================
          topo.     "Topology", "Connection"
          disp.     "Dispatch", "Operational" (e.g. GenerationUnit.DispatchResult)
          pf.       "PowerFlow", "Injection", "Withdrawal" (e.g. ElectricalBus.PowerFlowResult)
          plan.     "Planning", "Lifecycle"
          res.      "Resource", "Primary"
          geo.      "Location", "Spatial"
          ========  =============================================

          Classified dynamically by substring match against whatever
          Result classes actually exist in the schema (see
          `_discover_view_classes()`), not a fixed list.

          For each prefix found in a row, the importer resolves which view
          class the column belongs to by looking up the field name in each
          candidate view class schema.  View entity ids are reconstructed as
          ``<view_class_snake_case>.<asset_id>``.  The ``reportsOn``
          back-relation is injected automatically.

        **Long tidy file** (``all_entities_long.csv``):
          Not imported — the wide files are the authoritative input.
          The long file is analytics-only output.

        Parameters
        ----------
        dir_path :
            Directory containing the CSV files produced by
            :meth:`export_csv_hierarchical`.
        create_missing_refs :
            If True, entities referenced by a relation that do not yet
            exist are auto-created as empty shells.
        strict_unknown :
            If True, unknown column names are included in the unknowns list.

        Returns
        -------
        dict
            Summary with keys ``created_entities``, ``set_attributes``,
            ``set_relations``, ``unknowns``.
        """
        import csv as _csv, json as _json

        p = pathlib.Path(dir_path)
        created = set_attr = set_ref = 0
        unknowns: List[tuple] = []

        # ── build field → view class lookup per prefix ────────────────────
        # For each prefix, collect {field_name: [view_class, ...]}
        # so we can resolve "disp.nominal_power_capacity" → GenerationUnit.DispatchResult
        _PREFIX_TO_VCLS: Dict[str, List[str]] = {
            "topo.": [],
            "disp.": [],
            "pf.":   [],
            "plan.": [],
            "res.":  [],
            "geo.":  [],
            "view.": [],
        }
        for vcls in self._discover_view_classes():
            if "Topology" in vcls or "Connection" in vcls:
                _PREFIX_TO_VCLS["topo."].append(vcls)
            elif "Dispatch" in vcls or "Operational" in vcls:
                _PREFIX_TO_VCLS["disp."].append(vcls)
            elif "PowerFlow" in vcls or "Injection" in vcls or "Withdrawal" in vcls:
                _PREFIX_TO_VCLS["pf."].append(vcls)
            elif "Planning" in vcls or "Lifecycle" in vcls:
                _PREFIX_TO_VCLS["plan."].append(vcls)
            elif "Resource" in vcls or "Primary" in vcls:
                _PREFIX_TO_VCLS["res."].append(vcls)
            elif "Location" in vcls or "Spatial" in vcls:
                _PREFIX_TO_VCLS["geo."].append(vcls)
            else:
                _PREFIX_TO_VCLS["view."].append(vcls)

        # Pre-collect known fields per view class
        _vcls_attrs: Dict[str, set] = {}
        _vcls_refs:  Dict[str, set] = {}
        for vcls in self._discover_view_classes():
            cdef = self.classes.get(vcls)
            if cdef:
                a, r = self._collect_inherited_fields(cdef)
                _vcls_attrs[vcls] = set(a.keys())
                _vcls_refs[vcls]  = set(r.keys())

        def _resolve_vcls(prefix: str, field_name: str):
            """Return the view class that owns field_name under prefix, or None."""
            for vcls in _PREFIX_TO_VCLS.get(prefix, []):
                if field_name in _vcls_attrs.get(vcls, set()) \
                        or field_name in _vcls_refs.get(vcls, set()):
                    return vcls
            return None

        def _view_id(vcls: str, asset_id: str) -> str:
            import re as _re
            snake = _re.sub(r"(?<!^)(?=[A-Z])", "_", vcls).lower()
            return f"{snake}.{asset_id}"

        def _ensure(cls: str, eid: str) -> None:
            nonlocal created
            if cls not in self.entities:
                self.entities[cls] = {}
            if eid not in self.entities[cls]:
                self.add_entity(cls, eid)
                created += 1

        def _set_attr(cls: str, eid: str, aname: str, raw: str,
                      known_a: set) -> None:
            nonlocal set_attr
            if aname not in known_a:
                if strict_unknown:
                    unknowns.append((cls, eid, f"unknown attribute: {aname}"))
                return
            coerced = self._coerce_for_attr(cls, aname, raw)
            self.add_attribute(eid, aname, coerced)
            set_attr += 1

        def _set_rel(cls: str, eid: str, rname: str, raw: str,
                     known_r: set, refs_def) -> None:
            nonlocal set_ref, created
            if rname not in known_r:
                if strict_unknown:
                    unknowns.append((cls, eid, f"unknown relation: {rname}"))
                return
            # parse pipe-separated, JSON-array, or plain id
            txt = raw.strip()
            try:
                parsed = _json.loads(txt)
                targets = [str(x) for x in parsed] if isinstance(parsed, list) \
                    else [str(parsed)]
            except Exception:
                targets = [t.strip() for t in txt.split("|") if t.strip()] \
                    if "|" in txt else [txt]

            rd = refs_def.get(rname)
            for tid in targets:
                if not tid:
                    continue
                if create_missing_refs and rd:
                    existing = self._find_existing_target_class(rd, tid)
                    if existing is None and rd.targets:
                        self.add_entity(rd.targets[0], tid)
                        created += 1
                self.add_relation(eid, rname, tid)
                set_ref += 1

        # ── non-asset flat files ──────────────────────────────────────────
        for ncls in sorted(self._discover_non_asset_classes()):
            fpath = p / f"{ncls}_wide.csv"
            if not fpath.exists():
                continue

            cdef = self.classes.get(ncls)
            if not cdef:
                continue
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            known_a = set(attrs_def.keys())
            known_r = set(refs_def.keys())

            with open(fpath, newline="", encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    eid = str(row.get("entity_id", "")).strip()
                    if not eid:
                        continue
                    _ensure(ncls, eid)

                    for col, val in row.items():
                        if col == "entity_id" or not val or val.strip() == "":
                            continue
                        if col in known_r:
                            _set_rel(ncls, eid, col, val, known_r, refs_def)
                        elif col in known_a:
                            _set_attr(ncls, eid, col, val, known_a)
                        elif strict_unknown:
                            unknowns.append((ncls, eid, f"unknown column: {col}"))

        # ── asset wide files (with prefixed view columns) ─────────────────
        for acls in sorted(self._discover_asset_classes()):
            fpath = p / f"{acls}_wide.csv"
            if not fpath.exists():
                continue

            cdef = self.classes.get(acls)
            if not cdef:
                continue
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            known_a = set(attrs_def.keys())
            known_r = set(refs_def.keys())

            # Group prefixed columns by resolved view class.
            # Resolution is constrained to the view classes allowed for
            # this asset class, preventing ambiguous fields (e.g.
            # nominal_power_capacity shared between GenerationUnit.DispatchResult
            # and StorageUnit.DispatchResult) from being assigned to the wrong view.
            allowed_views = set(self._discover_view_map().get(acls, list(self._discover_view_classes())))

            def _resolve_vcls_for_asset(prefix: str, field_name: str):
                for vcls in _PREFIX_TO_VCLS.get(prefix, []):
                    if vcls not in allowed_views:
                        continue
                    if field_name in _vcls_attrs.get(vcls, set()) \
                            or field_name in _vcls_refs.get(vcls, set()):
                        return vcls
                return None

            with open(fpath, newline="", encoding="utf-8") as f:
                reader = _csv.DictReader(f)
                header = reader.fieldnames or []

                # Classify each header column
                id_col = "asset_id"
                asset_cols:  Dict[str, str] = {}   # col → field_name
                view_cols:   Dict[str, Dict[str, str]] = {}  # vcls → {col: field}

                for col in header:
                    if col == id_col:
                        continue
                    # Check if it is a prefixed view column
                    matched = False
                    for prefix in _PREFIX_TO_VCLS:
                        if col.startswith(prefix):
                            field = col[len(prefix):]
                            vcls  = _resolve_vcls_for_asset(prefix, field)
                            if vcls:
                                view_cols.setdefault(vcls, {})[col] = field
                                matched = True
                                break
                    if not matched:
                        # Asset-level column
                        asset_cols[col] = col

                for row in reader:
                    eid = str(row.get(id_col, "")).strip()
                    if not eid:
                        continue
                    _ensure(acls, eid)

                    # Asset-level fields
                    for col, field in asset_cols.items():
                        val = (row.get(col) or "").strip()
                        if not val:
                            continue
                        if field in known_r:
                            _set_rel(acls, eid, field, val, known_r, refs_def)
                        elif field in known_a:
                            _set_attr(acls, eid, field, val, known_a)
                        elif strict_unknown:
                            unknowns.append((acls, eid, f"unknown column: {col}"))

                    # View-level fields
                    for vcls, col_map in view_cols.items():
                        # Collect only non-empty view columns for this row
                        view_data = {field: row[col]
                                     for col, field in col_map.items()
                                     if (row.get(col) or "").strip()}
                        if not view_data:
                            continue  # no view data in this row for this view

                        vid = _view_id(vcls, eid)
                        _ensure(vcls, vid)

                        # Inject reportsOn back-relation
                        ra = self._REPORTS_ON_REL
                        if ra in _vcls_refs.get(vcls, set()):
                            self.add_relation(vid, ra, eid)
                            set_ref += 1

                        va = _vcls_attrs.get(vcls, set())
                        vr = _vcls_refs.get(vcls, set())
                        vcdef = self.classes.get(vcls)
                        _, vrefs_def = self._collect_inherited_fields(vcdef) \
                            if vcdef else ({}, {})

                        for field, val in view_data.items():
                            val = val.strip()
                            if not val:
                                continue
                            if field in vr:
                                _set_rel(vcls, vid, field, val, vr, vrefs_def)
                            elif field in va:
                                _set_attr(vcls, vid, field, val, va)
                            elif strict_unknown:
                                unknowns.append(
                                    (vcls, vid, f"unknown view field: {field}"))

        return {
            "created_entities": created,
            "set_attributes":   set_attr,
            "set_relations":    set_ref,
            "unknowns":         unknowns,
        }
