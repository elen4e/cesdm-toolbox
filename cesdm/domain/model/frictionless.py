"""cesdm.domain.model.frictionless — Frictionless Data Package persistence (CESDM-aware)

CESDM-specific override of the generic Frictionless exporter:
annotates resources with cesdm:role and sorts imports so domain
entities load before representation views.

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


class FrictionlessMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def import_datapackage(
        self,
        dir_path: Union[str, pathlib.Path],
        *,
        skip_unknown_classes: bool = True,
        skip_unknown_fields:  bool = True,
    ) -> Dict[str, int]:
        """
        Import a Frictionless Data Package produced by
        :meth:`export_datapackage` or :meth:`export_frictionless`.

        Reads ``datapackage.json`` in ``dir_path``, then imports each
        CSV resource listed in it using the embedded Frictionless Table
        Schema to route columns correctly.

        Falls back to schema-driven routing (``_collect_inherited_fields``)
        when the ``title`` field in the resource matches a known class.

        Parameters
        ----------
        dir_path :
            Directory containing ``datapackage.json`` and the CSV files.
        skip_unknown_classes :
            Silently skip resources whose class cannot be resolved.
        skip_unknown_fields :
            Silently skip columns not in the schema.

        Returns
        -------
        dict
            ``{class_name: n_entities_imported}``
        """
        import json as _json
        import csv  as _csv

        base = pathlib.Path(dir_path)
        dp_file = base / "datapackage.json"
        if not dp_file.exists():
            raise FileNotFoundError(f"datapackage.json not found in {base}")

        dp = _json.loads(dp_file.read_text(encoding="utf-8"))
        stats: Dict[str, int] = {}

        # ── Pass 0: AllEntities.csv — register every entity id + class ────────
        # AllEntities.csv is the canonical entity registry.  Reading it first
        # guarantees every entity exists before any View CSV tries to set a
        # reportsOn / atNode relation on it. Legacy packages used
        # AllAssets.csv / column asset_class — both are still accepted.
        _INDEX_CLASSES = {"AllEntities", "AllAssets"}
        _all_assets_index: Dict[str, str] = {}  # entity_id → entity_class
        for _resource in dp.get("resources", []):
            _custom = _resource.get("custom") or {}
            _cname  = _custom.get("class") or _resource.get("title", "")
            if _cname not in _INDEX_CLASSES:
                continue
            _csv_path = base / _resource.get("path", "")
            if not _csv_path.exists():
                break
            with _csv_path.open(newline="", encoding="utf-8-sig") as _f:
                for _row in _csv.DictReader(_f):
                    _eid   = str(_row.get("entity_id", "")).strip()
                    _acls  = str(
                        _row.get("entity_class")
                        or _row.get("asset_class")
                        or ""
                    ).strip()
                    if not _eid or not _acls:
                        continue
                    _acls = self._resolve_entity_class_alias(_acls)
                    _all_assets_index[_eid] = _acls
                    if _acls in self.classes:
                        if _eid not in self.entities.get(_acls, {}):
                            self.add_entity(_acls, _eid)
            break  # only one index resource

        # Strict validation: if AllEntities.csv was present, every entity
        # found in concrete class CSVs must match the declared entity_class.
        _has_all_assets = bool(_all_assets_index)

        def _is_inherited_lookup_row(_eid: str, _cname: str) -> bool:
            """True if this row is from an abstract base class CSV (legacy).
            In the new format only concrete classes have CSVs, so this always
            returns False.  Kept for backwards compatibility with old exports
            that still have SemanticEntity.csv / EnergyAssetInstance.csv.
            """
            if not _has_all_assets:
                # Legacy export — fall back to old subclass-detection logic
                return False
            # New format: skip row if entity is registered under a different
            # (more specific) class
            registered_cls = _all_assets_index.get(_eid)
            if registered_cls and registered_cls != _cname:
                try:
                    if self.is_class_derived_from(registered_cls, _cname, self.inheritance):
                        return True  # _cname is abstract base — skip
                except Exception:
                    pass
            return False

        for resource in dp.get("resources", []):
            # Resolve class name: prefer explicit cesdm:class annotation,
            # then title (human-readable, often PascalCase), then convert
            # the kebab-case resource name back to PascalCase.
            cname = (
                (resource.get("custom") or {}).get("class")
                or resource.get("cesdm:class")   # backwards compat
                or resource.get("title")
                or "".join(
                    w.capitalize()
                    for w in resource.get("name", "").replace("-", "_").split("_")
                )
            )
            cname = self._resolve_entity_class_alias(cname)
            if cname not in self.classes:
                if not skip_unknown_classes:
                    raise KeyError(
                        f"Resource '{resource.get('name')}' maps to "
                        f"unknown class '{cname}'"
                    )
                continue

            cdef = self.classes[cname]
            attrs_def, rels_def = self._collect_inherited_fields(cdef)

            # Build field-type map from embedded schema
            schema_fields: Dict[str, str] = {}
            for field in (resource.get("schema") or {}).get("fields", []):
                schema_fields[field["name"]] = field.get("type", "string")

            csv_path_raw = resource.get("path", "")
            csv_path = base / csv_path_raw
            if not csv_path.exists():
                continue

            with csv_path.open(newline="", encoding="utf-8-sig") as f:
                reader = _csv.DictReader(f)
                count  = 0
                for row in reader:
                    eid = str(row.get("entity_id", "")).strip()
                    if not eid:
                        continue

                    if _is_inherited_lookup_row(eid, cname):
                        continue

                    if eid not in self.entities.get(cname, {}):
                        if any(
                            eid in _ents and _cls != cname
                            for _cls, _ents in (self.entities or {}).items()
                        ):
                            continue
                        self.add_entity(cname, eid)

                    _rel_aliases = getattr(self, "_RELATION_ID_ALIASES", {}) or {}
                    for col, val in row.items():
                        if col == "entity_id" or not val or val.strip() == "":
                            continue
                        val = val.strip()
                        col_rel = _rel_aliases.get(col, col)
                        col_attr = self._attribute_id_for_schema_lookup(col)
                        if col_rel in rels_def:
                            if val.startswith("["):
                                import json as _jj
                                try:
                                    for t in _jj.loads(val):
                                        if t:
                                            self.add_relation(eid, col_rel, str(t))
                                except Exception:
                                    self.add_relation(eid, col_rel, val)
                            else:
                                self.add_relation(eid, col_rel, val)
                        elif col_attr in attrs_def or self._is_legacy_attribute_write(col):
                            ftype = schema_fields.get(col_attr, "string")
                            if self._is_legacy_attribute_write(col):
                                ftype = "boolean"
                            coerced: Any = val
                            try:
                                if ftype == "number":
                                    coerced = float(val)
                                elif ftype == "integer":
                                    coerced = int(val)
                                elif ftype == "boolean":
                                    coerced = val.lower() in ("true", "1", "yes")
                                else:
                                    coerced = val
                            except (ValueError, TypeError):
                                coerced = val
                            # Pass original col so add_attribute can remap
                            # legacy ids (machine_role / is_reversible /
                            # is_reference_port).
                            self.add_attribute(eid, col, coerced)
                        else:
                            if not skip_unknown_fields:
                                raise KeyError(
                                    f"Column '{col}' in resource "
                                    f"'{resource.get('name')}' is not a "
                                    f"known field of class '{cname}'"
                                )
                    count += 1
            stats[cname] = count

        return stats


    # ================================================================== #
    #  export_frictionless  /  import_frictionless                         #
    # ================================================================== #

    def export_frictionless(
        self,
        dir_path: Union[str, pathlib.Path],
        *,
        name:        str = "cesdm-model",
        title:       Optional[str] = None,
        description: str = "",
        version:     str = "1.0.0",
        contributors: Optional[list] = None,
        include_library: str = "referenced",
    ) -> pathlib.Path:
        """
        CESDM-aware override of :meth:`ear_toolbox.Model.export_frictionless`.

        Extends the generic implementation with:

        - ``cesdm:role`` annotation on each resource (``"asset"``,
          ``"representation"``, ``"domain"``) derived from the schema
          inheritance graph via ``_discover_*`` methods.
        - Resource ordering: domain entities first, representations last,
          matching the expected import order.
        - Every relation becomes a real ``foreignKeys`` entry, including
          ones whose schema `target` is an abstract class (`NetworkNode`,
          `Controller.AVR`/`.GOV`/`.PSS`, `DynamicMachineModelType`, ...):
          an ``All<Class>`` union table is generated per such target
          (mirroring the ``AllEntities`` pattern already used for the
          asset hierarchy), so the exported package passes
          `frictionless validate` in full, not just for relations whose
          target happens to be a concrete class.
        - Library filtering via ``include_library`` (default
          ``"referenced"``): omit unused default-/imported-library
          master data from the package.

        Export the model as a Frictionless Data Package.

        Layout
        ------
        ::

            <dir_path>/
                datapackage.json          ← Frictionless descriptor
                resources/
                    AllEntities.csv
                    GenerationUnit.csv
                    ElectricalBus.csv
                    Carrier.csv
                    …  (one CSV per class / index table)

        CSVs live flat under ``resources/``. Resource roles (``asset``,
        ``domain``, ``entity-index``, …) are recorded only in
        ``datapackage.json`` (``custom.role``), not as subfolders.

        The descriptor embeds a full Frictionless Table Schema per resource
        (field names, types, constraints, foreign keys) so the package is
        self-describing — a consumer does not need the YAML schema to
        understand the data.

        Each CSV uses the wide format: one row per entity, one column per
        attribute or relation (schema-driven column order).

        Parameters
        ----------
        dir_path :
            Output directory.
        name :
            Machine-readable package name (lowercase, hyphens).
        title :
            Human-readable title.
        description :
            Package description.
        version :
            Semantic version string.
        contributors :
            List of contributor dicts ``{"title": "...", "role": "..."}``.
        include_library :
            ``"none"`` | ``"referenced"`` | ``"all"`` — how much library
            master data (Carrier, GeneratorType, …) to embed. Default
            ``"referenced"`` keeps only library entities reachable from
            the system model; ``"none"`` omits them entirely (relations
            may still point at library ids); ``"all"`` embeds every
            library entity present in the in-memory model.

        Returns
        -------
        pathlib.Path
            Path to the written ``datapackage.json``.
        """
        with self._export_entity_scope(include_library):  # type: ignore[attr-defined]
            return self._export_frictionless_body(
                dir_path,
                name=name,
                title=title,
                description=description,
                version=version,
                contributors=contributors,
                include_library=include_library,
            )

    def _export_frictionless_body(
        self,
        dir_path: Union[str, pathlib.Path],
        *,
        name: str,
        title: Optional[str],
        description: str,
        version: str,
        contributors: Optional[list],
        include_library: str,
    ) -> pathlib.Path:
        import json as _json
        import csv  as _csv
        import datetime

        base = pathlib.Path(dir_path)
        # Flat layout: resources/<ClassOrIndex>.csv
        # Roles stay in datapackage.json (custom.role), not as subfolders.
        resources_dir = base / "resources"
        resources_dir.mkdir(parents=True, exist_ok=True)

        def _res_dir(_role: str = "") -> pathlib.Path:
            return resources_dir

        def _res_path(_role: str, cname: str) -> str:
            """Return the datapackage-relative path string for a resource."""
            return f"resources/{cname}.csv"

        resources = []

        # ── AllEntities.csv: universal FK target for all View.reportsOn ──
        # Abstract classes (SemanticEntity, EnergyAssetInstance,
        # GenerationUnit, …) are NOT exported as their own CSV.
        # Instead, every concrete asset entity appears exactly once in its
        # own class CSV (e.g. GenerationUnit.csv) AND in AllEntities.csv.
        # All reportsOn / atNode / similar foreign keys reference
        # AllEntities instead of the abstract base class, so the FK graph
        # remains valid without polluting base-class CSVs with subclass rows.

        all_entities_rows: list[dict] = []   # {entity_id, entity_class, name}
        asset_classes   = self._discover_asset_classes()

        for _acls, _aents in (self.entities or {}).items():
            if _acls not in asset_classes or not _aents:
                continue
            for _aeid, _aent in _aents.items():
                _aname = (
                    getattr(_aent, "data", {}).get("name") or ""
                )
                if isinstance(_aname, dict):
                    _aname = _aname.get("value", "")
                all_entities_rows.append({
                    "entity_id":     _aeid,
                    "entity_class":  _acls,
                    "name":          str(_aname or ""),
                })

        all_entities_path = _res_dir("entity-index") / "AllEntities.csv"
        with all_entities_path.open("w", newline="", encoding="utf-8") as _f:
            _w = _csv.DictWriter(
                _f, fieldnames=["entity_id", "entity_class", "name"]
            )
            _w.writeheader()
            for _r in sorted(all_entities_rows, key=lambda x: x["entity_id"]):
                _w.writerow(_r)

        all_entities_resource: Dict[str, Any] = {
            "name":      "all-entities",
            "title":     "AllEntities",
            "path":      _res_path("entity-index", "AllEntities"),
            "type":      "table",
            "format":    "csv",
            "mediatype": "text/csv",
            "encoding":  "utf-8",
            "dialect":   {"delimiter": ",", "header": True, "headerRows": [1]},
            "schema": {
                "primaryKey": ["entity_id"],
                "fields": [
                    {"name": "entity_id", "type": "string",
                     "constraints": {"required": True},
                     "description": "Unique entity id (same as in the concrete class CSV)."},
                    {"name": "entity_class", "type": "string",
                     "constraints": {"required": True},
                     "description": "Concrete CESDM class name of this entity."},
                    {"name": "name", "type": "string",
                     "description": "Human-readable name attribute (denormalised for convenience)."},
                ],
            },
            "custom": {
                "class":             "AllEntities",
                "role":              "entity-index",
                "cesdm:description": (
                    "Universal FK target for asset-hierarchy relations "
                    "(reportsOn, and asset-typed targets). "
                    "Every concrete asset entity appears here exactly once. "
                    "Abstract base classes (SemanticEntity, EnergyAssetInstance, "
                    "GenerationUnit, …) are not exported as separate CSVs."
                ),
            },
        }
        resources.insert(0, all_entities_resource)  # always first

        # ── Union tables for every OTHER abstract relation target ──────────
        # AllEntities solves this for the EnergyAssetInstance hierarchy
        # already (any relation targeting an asset class, concrete or
        # abstract, points there). The exact same structural problem
        # exists for every other abstract class used as a relation
        # target -- NetworkNode (ElectricalBus/GasBus/HeatBus/
        # HydrogenBus), Controller.AVR/.GOV/.PSS (each with
        # several concrete IEEE model subclasses), DynamicMachineModelType,
        # RunRecord, Result, ... -- since self.entities is keyed by
        # concrete class name only, never by the abstract target string
        # a relation actually declares. Without this, every relation
        # targeting an abstract class (e.g. atNode -> NetworkNode,
        # hasAutomaticVoltageRegulator -> Controller.AVR) would silently
        # get no foreignKeys entry at all, for every model, regardless
        # of content -- confirmed directly with `frictionless validate`
        # against a real export before this fix.
        #
        # Scan every relation definition in the schema for abstract
        # targets not already covered by the asset hierarchy, and build
        # one union CSV per such target that actually has at least one
        # populated concrete descendant in this model.
        _abstract_targets: set = set()
        for _cn, _cd in self.classes.items():
            _, _cd_rels = self._collect_inherited_fields(_cd)
            for _rd in _cd_rels.values():
                _t = getattr(_rd, "target", None) or getattr(_rd, "targets", None)
                for _ts in ([_t] if isinstance(_t, str) else (_t or [])):
                    if not _ts or _ts in asset_classes:
                        continue
                    _ts_cd = self.classes.get(_ts)
                    if _ts_cd is not None and getattr(_ts_cd, "abstract", False):
                        _abstract_targets.add(_ts)

        # abstract target class name -> resource name (or None if no
        # populated concrete descendant exists in this model at all)
        abstract_target_resource: Dict[str, Optional[str]] = {}

        for _abs_cls in sorted(_abstract_targets):
            _rows = []
            for _cn2, _ents2 in (self.entities or {}).items():
                if not _ents2 or self.classes.get(_cn2) is None:
                    continue
                if getattr(self.classes[_cn2], "abstract", False):
                    continue
                if not self.is_class_derived_from(_cn2, _abs_cls, self.inheritance):
                    continue
                for _eid2, _ent2 in _ents2.items():
                    _nm = (getattr(_ent2, "data", {}) or {}).get("name") or ""
                    if isinstance(_nm, dict):
                        _nm = _nm.get("value", "")
                    _rows.append({"entity_id": _eid2, "entity_class": _cn2, "name": str(_nm or "")})

            if not _rows:
                abstract_target_resource[_abs_cls] = None
                continue

            _union_slug = self._slugify_resource_name("All" + _abs_cls.replace(".", ""))
            _union_title = "All" + _abs_cls.replace(".", "")
            _union_path = _res_path("domain", _union_title)
            _union_csv = _res_dir("domain") / f"{_union_title}.csv"
            with _union_csv.open("w", newline="", encoding="utf-8") as _f:
                _w = _csv.DictWriter(_f, fieldnames=["entity_id", "entity_class", "name"])
                _w.writeheader()
                for _r in sorted(_rows, key=lambda x: x["entity_id"]):
                    _w.writerow(_r)

            resources.append({
                "name":      _union_slug,
                "title":     _union_title,
                "path":      _union_path,
                "type":      "table",
                "format":    "csv",
                "mediatype": "text/csv",
                "encoding":  "utf-8",
                "dialect":   {"delimiter": ",", "header": True, "headerRows": [1]},
                "schema": {
                    "primaryKey": ["entity_id"],
                    "fields": [
                        {"name": "entity_id", "type": "string",
                         "constraints": {"required": True},
                         "description": f"Unique entity id (same as in the concrete class CSV)."},
                        {"name": "entity_class", "type": "string",
                         "constraints": {"required": True},
                         "description": "Concrete CESDM class name of this entity."},
                        {"name": "name", "type": "string",
                         "description": "Human-readable name attribute (denormalised for convenience)."},
                    ],
                },
                "custom": {
                    "class": _union_title,
                    "role":  "domain",
                    "cesdm:description": (
                        f"Universal FK target for relations declaring '{_abs_cls}' "
                        "(an abstract class) as their target. Every populated concrete "
                        f"descendant of {_abs_cls} appears here exactly once."
                    ),
                },
            })
            abstract_target_resource[_abs_cls] = _union_slug

        # cdef.abstract is now directly correct: resolve_inheritance() no
        # longer propagates abstract=True from parents to concrete
        # subclasses (that was a real bug, fixed in ear/model/schema_loading.py
        # — see CHANGELOG.md). Previously this method had to re-derive
        # "directly abstract" itself, either by re-parsing the raw schema
        # YAML or via a parents-graph heuristic, to work around it.
        def _is_abstract_class(_cname: str) -> bool:
            _cd = self.classes.get(_cname)
            return bool(getattr(_cd, "abstract", False))

        # Write one CSV per NON-ABSTRACT class that has direct entities.
        # Abstract classes are skipped — their instances appear only in
        # their concrete subclass CSVs and in AllEntities.csv.
        views_set     = self._discover_view_classes()
        assets_set    = asset_classes  # already computed above

        def _class_role(cn: str) -> str:
            if cn in views_set:  return "representation"
            if cn in assets_set: return "asset"
            return "domain"

        for cname in sorted(self.classes.keys()):
            if _is_abstract_class(cname):
                continue
            ents = dict(self.entities.get(cname, {}) or {})

            # HydroGenerationUnit.DispatchView used to be created with two
            # different id conventions by some import paths:
            #   hydro_dispatch_view.<asset_id>
            #   generation_dispatch_view.<asset_id>
            # Both rows represent the same HydroGenerationUnit and therefore
            # produce duplicate Frictionless records.  Keep exactly one row per
            # reportsOn, preferring the canonical hydro_dispatch_view.* id.
            if cname == "HydroGenerationUnit.DispatchView" and len(ents) > 1:
                grouped: dict[str, list[tuple[str, Any]]] = {}
                for _eid, _ent in ents.items():
                    _data = getattr(_ent, "data", {}) or {}
                    _asset = _data.get("reportsOn")
                    if isinstance(_asset, (list, tuple)):
                        _asset = _asset[0] if _asset else None
                    grouped.setdefault(str(_asset or _eid), []).append((_eid, _ent))
                _deduped: dict[str, Any] = {}
                for _asset, _items in grouped.items():
                    _items.sort(key=lambda x: (
                        0 if x[0].startswith("hydro_dispatch_view.") else
                        1 if x[0].startswith("generation_dispatch_view.") else 2,
                        x[0],
                    ))
                    _eid, _ent = _items[0]
                    _deduped[_eid] = _ent
                ents = _deduped

            if not ents:
                continue
            _role = _class_role(cname)

            cdef = self.classes[cname]
            attrs_def, rels_def = self._collect_inherited_fields(cdef)
            attr_names = list(attrs_def.keys())
            rel_names  = list(rels_def.keys())
            header     = ["entity_id"] + rel_names + attr_names

            csv_path = _res_dir(_role) / f"{cname}.csv"

            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = _csv.DictWriter(f, fieldnames=header,
                                         extrasaction="ignore")
                writer.writeheader()
                for eid, ent in ents.items():
                    data = getattr(ent, "data", {}) or {}
                    row: Dict[str, Any] = {"entity_id": eid}

                    # Denormalise: if a relation is empty on the instance
                    # but hasTechnology is set, inherit the value from the
                    # referenced GeneratorType / StorageType entity.
                    # This makes the Frictionless export self-contained —
                    # consumers do not need to join against the type table.
                    _type_id = None
                    _type_ent_data = None

                    def _resolve_from_type(col_name: str, cur_val: str) -> str:
                        nonlocal _type_id, _type_ent_data
                        if cur_val:
                            return cur_val
                        # Lazy-load the type entity once per row
                        if _type_id is None:
                            raw_t = data.get("hasTechnology")
                            _type_id = (
                                raw_t[0] if isinstance(raw_t, (list, tuple)) else raw_t
                            ) or ""
                        if not _type_id:
                            return cur_val
                        if _type_ent_data is None:
                            for _tcls in ("GeneratorType", "StorageType",
                                          "EnergyTechnologyType"):
                                _te = (self.entities.get(_tcls) or {}).get(_type_id)
                                if _te is not None:
                                    _type_ent_data = getattr(_te, "data", {}) or {}
                                    break
                            if _type_ent_data is None:
                                _type_ent_data = {}
                        raw_tv = _type_ent_data.get(col_name)
                        if raw_tv is None:
                            return cur_val
                        if isinstance(raw_tv, (list, tuple)):
                            return str(raw_tv[0]) if raw_tv else cur_val
                        return str(raw_tv)

                    # Relations that should be denormalised from type
                    _DENORM_RELS = {
                        "hasInputCarrier", "hasOutputCarrier",
                        "storesCarrier",
                    }

                    for rn in rel_names:
                        val = data.get(rn)
                        if val is None:
                            raw_str = ""
                        elif isinstance(val, list):
                            raw_str = str(val[0]) if val else ""
                        else:
                            raw_str = str(val)
                        # Denormalise from GeneratorType if empty
                        if rn in _DENORM_RELS:
                            raw_str = _resolve_from_type(rn, raw_str)
                        row[rn] = raw_str

                    for an in attr_names:
                        raw = data.get(an)
                        if raw is None:
                            row[an] = ""
                        elif isinstance(raw, dict):
                            v = raw.get("value")
                            row[an] = "" if v is None else str(v)
                        else:
                            row[an] = str(raw)

                    writer.writerow(row)

            # Build Frictionless Table Schema for this class
            fields_schema = [
                {
                    "name": "entity_id",
                    "type": "string",
                    "constraints": {"required": True},
                    "description": f"Unique id of the {cname} entity.",
                }
            ]
            foreign_keys = []

            for rn in rel_names:
                rd  = rels_def[rn]
                tgt = getattr(rd, "target", None) or getattr(rd, "targets", None)
                req = getattr(rd, "required", False)
                fld = {
                    "name": rn,
                    "type": "string",
                    "description": f"Relation to {tgt or 'entity'}.",
                }
                if req:
                    fld["constraints"] = {"required": True}
                fields_schema.append(fld)

                # Foreign key: if the target is an asset class (concrete or
                # abstract), point at AllEntities (the universal FK table).
                # If the target is a domain entity (Carrier, etc.) or
                # another view, point at the target class CSV directly.
                tgt_str = (tgt[0] if isinstance(tgt, list) and tgt else tgt)
                if tgt_str:
                    tgt_is_asset = (
                        tgt_str in asset_classes
                        or any(
                            self.is_class_derived_from(tgt_str, a, self.inheritance)
                            for a in asset_classes
                        )
                        or tgt_str in {"EnergyAssetInstance", "SemanticEntity",
                                       "SystemAsset"}
                    )
                    if tgt_is_asset:
                        # All asset FKs → AllEntities (handles abstract bases + subclasses)
                        foreign_keys.append({
                            "fields": [rn],
                            "reference": {
                                "resource": "all-entities",
                                "fields":   ["entity_id"],
                            },
                        })
                    elif tgt_str in abstract_target_resource:
                        # Abstract, non-asset target → its union table, if it
                        # has at least one populated concrete descendant in
                        # this model (see the union-table construction above).
                        _union_res = abstract_target_resource[tgt_str]
                        if _union_res:
                            foreign_keys.append({
                                "fields": [rn],
                                "reference": {
                                    "resource": _union_res,
                                    "fields":   ["entity_id"],
                                },
                            })
                    elif self.entities.get(tgt_str):
                        # Domain / view FK → concrete target CSV
                        ref_resource = ("" if tgt_str == cname
                                        else self._slugify_resource_name(tgt_str))
                        foreign_keys.append({
                            "fields": [rn],
                            "reference": {
                                "resource": ref_resource,
                                "fields":   ["entity_id"],
                            },
                        })

            for an in attr_names:
                ad  = attrs_def[an]
                req = getattr(ad, "required", False)
                # Full field descriptor with constraints, units, defaults
                fld = self._frictionless_field_for_attr(an, ad, required=req)
                fields_schema.append(fld)

            table_schema: Dict[str, Any] = {"fields": fields_schema}
            if foreign_keys:
                table_schema["foreignKeys"] = foreign_keys
            table_schema["primaryKey"] = ["entity_id"]

            cdef_desc = getattr(cdef, "description", "") or ""

            res_entry: Dict[str, Any] = {
                "name":      self._slugify_resource_name(cname),
                "title":     cname,
                "path":      _res_path(_role, cname),
                "type":      "table",
                "format":    "csv",
                "mediatype": "text/csv",
                "encoding":  "utf-8",
                "dialect": {
                    "delimiter":  ",",
                    "header":     True,
                    "headerRows": [1],
                },
                "schema":    table_schema,
                "custom":    {"class": cname, "role": _role},
            }
            if cdef_desc:
                res_entry["description"] = cdef_desc
            resources.append(res_entry)

        # Write datapackage.json
        pkg: Dict[str, Any] = {
            "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
            "name":        name,
            "title":       title or name,
            "description": description,
            "version":     version,
            "created":     datetime.datetime.utcnow().isoformat() + "Z",
            "custom": {
                "cesdm:include_library": str(include_library or "referenced"),
            },
        }
        if contributors:
            pkg["contributors"] = contributors

        # Ensure every resource has a role annotation (roles are not
        # encoded as subfolders in the flat layout).
        # AllEntities already has role=entity-index set at creation.
        for r in resources:
            cname_r = (r.get("custom") or {}).get("class", r.get("title", ""))
            if not (r.get("custom") or {}).get("role"):
                r.setdefault("custom", {})["role"] = _class_role(cname_r)

        pkg["resources"] = resources

        dp_path = base / "datapackage.json"
        dp_path.write_text(
            _json.dumps(pkg, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return dp_path

    def _frictionless_type_for_attr(self, attr_def) -> str:
        """Map a schema AttributeDef to a Frictionless field type string."""
        raw_type = getattr(attr_def, "type", None) or                    getattr(attr_def, "value_type", None) or ""
        t = str(raw_type).lower()
        if t in ("float", "double", "number", "decimal"):
            return "number"
        if t in ("int", "integer", "long"):
            return "integer"
        if t in ("bool", "boolean"):
            return "boolean"
        if t in ("date",):
            return "date"
        if t in ("datetime",):
            return "datetime"
        return "string"

    def _frictionless_field_for_attr(self,
                                     name: str,
                                     attr_def,
                                     required: bool = False) -> dict:
        """
        Build a complete Frictionless field descriptor for an attribute.

        Transfers from the CESDM schema:
        - ``type``        — Frictionless type (number, integer, boolean, …)
        - ``description`` — attribute description
        - ``constraints`` — minimum, maximum, enum, pattern, required
        - ``default``     — default value
        - ``unit``        — added as a custom ``cesdm:unit`` annotation
                            and as ``constraints.enum`` on the unit column
                            (when the Frictionless field represents a
                            physical quantity)
        """
        ftype = self._frictionless_type_for_attr(attr_def)

        field: dict = {
            "name":        name,
            "type":        ftype,
            "description": getattr(attr_def, "description", "") or "",
        }

        # ── Constraints ───────────────────────────────────────────────
        constraints: dict = {}

        if required:
            constraints["required"] = True

        c = getattr(attr_def, "constraints", None)
        if c is not None:
            minimum = getattr(c, "minimum", None)
            maximum = getattr(c, "maximum", None)
            enum    = getattr(c, "enum",    None)
            pattern = getattr(c, "pattern", None)

            if minimum is not None:
                constraints["minimum"] = minimum
            if maximum is not None:
                constraints["maximum"] = maximum
            if enum:
                constraints["enum"] = list(enum)
            if pattern:
                constraints["pattern"] = str(pattern)

        if constraints:
            field["constraints"] = constraints

        # ── Default value ──────────────────────────────────────────────
        default = getattr(attr_def, "default", None)
        if default is not None:
            field["default"] = default

        # ── Unit annotation ────────────────────────────────────────────
        # Custom metadata goes in "custom" (Frictionless v2 extension point).
        unit = getattr(attr_def, "unit", None)
        unit_val = None
        if isinstance(unit, dict):
            unit_enum = (unit.get("constraints") or {}).get("enum")
            if unit_enum:
                unit_val = unit_enum[0] if len(unit_enum) == 1 else ", ".join(unit_enum)
        elif isinstance(unit, str) and unit:
            unit_val = unit
        if unit_val is not None:
            field.setdefault("custom", {})["unit"] = unit_val

        return field

    def import_frictionless(
        self,
        dir_path: Union[str, pathlib.Path],
        *,
        skip_unknown_classes: bool = True,
        skip_unknown_fields:  bool = True,
    ) -> Dict[str, int]:
        """
        CESDM-aware override of :meth:`ear_toolbox.Model.import_frictionless`.

        Extends the generic implementation by sorting resources on import
        using the ``cesdm:role`` annotation — assets and domain entities
        are loaded before representation views so that ``reportsOn``
        relations can be resolved in a single pass.

        Import a Frictionless Data Package produced by
        :meth:`export_frictionless`.

        This is a full round-trip counterpart: every entity, attribute, and
        relation exported by :meth:`export_frictionless` is restored.

        Delegates to :meth:`import_datapackage` which handles the generic
        Frictionless format.  The ``cesdm:role`` annotation on each resource
        is used to prioritise asset resources before representation resources
        so ``reportsOn`` relations can be resolved.

        Parameters
        ----------
        dir_path :
            Directory containing ``datapackage.json``.
        skip_unknown_classes :
            Silently skip unknown resource classes.
        skip_unknown_fields :
            Silently skip unknown columns.

        Returns
        -------
        dict
            ``{class_name: n_entities_imported}``
        """
        import json as _json

        base    = pathlib.Path(dir_path)
        dp_file = base / "datapackage.json"
        if not dp_file.exists():
            raise FileNotFoundError(f"datapackage.json not found in {base}")

        dp = _json.loads(dp_file.read_text(encoding="utf-8"))

        # Sort resources for correct multi-pass import:
        #   Pass 0 — AllEntities (entity-index): register all entity ids
        #   Pass 1 — domain + concrete asset CSVs
        #   Pass 2 — representation / view CSVs (if any)
        # Older packages used role subfolders (Assets/, BaseEntities/,
        # Representations/); new packages are flat under resources/.
        def _sort_key(r: dict) -> int:
            custom = r.get("custom") or {}
            role   = custom.get("role") or r.get("cesdm:role", "other")
            cname  = custom.get("class") or r.get("title", "")
            # Derive role from legacy path subfolders for backwards-compat
            rpath  = r.get("path", "")
            if not role:
                if "/Assets/"         in rpath: role = "asset"
                elif "/Representations/" in rpath: role = "representation"
                elif "/BaseEntities/"  in rpath: role = "domain"
            if cname in {"AllEntities", "AllAssets"} or role in {
                "entity-index", "asset-index"
            }:
                return 0
            if role in ("asset", "domain"):  return 1
            if role == "representation":     return 2
            return 1

        resources_sorted = sorted(dp.get("resources", []), key=_sort_key)

        # Strict class consistency check for the universal entity index.
        # If AllEntities says entity X is class A, a concrete asset CSV for class B
        # must not also contain X.  This catches corrupted/subclass-mismatched
        # packages before the generic importer silently merges rows.
        #
        # Be deliberately tolerant about descriptor metadata here: older or
        # hand-edited Data Packages may miss custom.role/custom.class.
        # Flat path resources/<Class>.csv is the current convention; legacy
        # resources/Assets/<Class>.csv and AllAssets.csv are still accepted.
        import csv as _csv
        entity_class_by_id: dict[str, str] = {}
        _INDEX_CLASSES = {"AllEntities", "AllAssets"}
        _INDEX_ROLES = {"entity-index", "asset-index"}
        _INDEX_FILENAMES = {"AllEntities.csv", "AllAssets.csv"}

        def _resource_class_name(r: dict) -> str:
            custom = r.get("custom") or {}
            cname = custom.get("class") or r.get("cesdm:class") or r.get("title")
            if cname:
                return str(cname)
            path = pathlib.Path(r.get("path", ""))
            return path.stem

        def _is_asset_resource(r: dict) -> bool:
            custom = r.get("custom") or {}
            role = custom.get("role") or r.get("cesdm:role")
            path = str(r.get("path", "")).replace("\\", "/")
            cname = _resource_class_name(r)
            return (
                role == "asset"
                or "/Assets/" in f"/{path}"
            ) and cname not in _INDEX_CLASSES

        # Prefer the descriptor entry, but also support a plain file at the
        # standard locations when descriptors were trimmed.
        all_entities_paths = []
        for r in resources_sorted:
            custom = r.get("custom") or {}
            cname = _resource_class_name(r)
            if cname in _INDEX_CLASSES or custom.get("role") in _INDEX_ROLES:
                all_entities_paths.append(base / r.get("path", ""))
        for fallback in (
            base / "resources" / "AllEntities.csv",
            base / "resources" / "AllAssets.csv",  # legacy name
            base / "resources" / "Assets" / "AllEntities.csv",
            base / "resources" / "Assets" / "AllAssets.csv",  # legacy path
        ):
            if fallback not in all_entities_paths:
                all_entities_paths.append(fallback)

        for path in all_entities_paths:
            if not path.exists():
                continue
            with path.open(newline="", encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    eid = row.get("entity_id") or row.get("id")
                    cls = (
                        row.get("entity_class")
                        or row.get("asset_class")
                        or row.get("class")
                    )
                    if eid and cls:
                        entity_class_by_id[str(eid)] = str(cls)
            if entity_class_by_id:
                break

        if entity_class_by_id:
            # Check descriptor-listed asset resources.
            checked_paths: set[pathlib.Path] = set()
            candidate_paths: list[tuple[str, pathlib.Path]] = []
            for r in resources_sorted:
                if not _is_asset_resource(r):
                    continue
                cname = _resource_class_name(r)
                path = base / r.get("path", "")
                candidate_paths.append((cname, path))
                checked_paths.add(path.resolve())

            # Also check any physical resources/Assets/*.csv files that might
            # not be listed in datapackage.json after manual tampering.
            assets_dir = base / "resources" / "Assets"
            if assets_dir.exists():
                for path in sorted(assets_dir.glob("*.csv")):
                    if path.name in _INDEX_FILENAMES or path.resolve() in checked_paths:
                        continue
                    candidate_paths.append((path.stem, path))

            for cname, path in candidate_paths:
                if not path.exists() or cname in _INDEX_CLASSES:
                    continue
                with path.open(newline="", encoding="utf-8") as f:
                    for row in _csv.DictReader(f):
                        eid = row.get("entity_id") or row.get("id")
                        expected = entity_class_by_id.get(str(eid or ""))
                        if expected and expected != cname:
                            raise ValueError(
                                f"Strict import error: entity '{eid}' appears in {cname}.csv "
                                f"but AllEntities declares entity_class '{expected}'"
                            )

        dp_sorted = dict(dp)
        dp_sorted["resources"] = resources_sorted

        # Write temp sorted descriptor and delegate to import_datapackage
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dp = pathlib.Path(tmp) / "datapackage.json"
            tmp_dp.write_text(_json.dumps(dp_sorted), encoding="utf-8")
            # Symlink/copy resources so import_datapackage can find them
            for r in resources_sorted:
                src = base / r["path"]
                dst = pathlib.Path(tmp) / r["path"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.exists():
                    shutil.copy2(str(src), str(dst))
            stats = self.import_datapackage(
                tmp,
                skip_unknown_classes=skip_unknown_classes,
                skip_unknown_fields=skip_unknown_fields,
            )
        return stats

    def export_datapackage(self, dir_path):
        """
        Export a Frictionless datapackage.json ONLY for by_class_wide resources,
        embedding each schema inline (no external schema files required).
        """
        import json
        import pathlib

        base = pathlib.Path(dir_path)
        bcw_dir = base / "energy_system_data"
        bcw_dir.mkdir(parents=True, exist_ok=True)

        self.export_csv_by_class_wide_with_schema(bcw_dir)

        resources = []

        for cname in sorted(self.classes.keys()):
            csv_path = bcw_dir / f"{cname}.csv"
            schema_path = bcw_dir / f"{cname}.csv.schema.json"

            if not csv_path.exists():
                continue
            if not schema_path.exists():
                raise FileNotFoundError(f"Missing schema file: {schema_path}")

            schema_obj = json.loads(schema_path.read_text(encoding="utf-8"))

            rname = f"{cname.lower()}"
            cdef = self.classes.get(cname)
            desc = getattr(cdef, "description", None) if cdef else None

            resources.append({
                "name": rname,
                "path": str((pathlib.Path("energy_system_data") / f"{cname}.csv").as_posix()),
                "profile": "tabular-data-resource",
                "format": "csv",
                "mediatype": "text/csv",
                "title": cname,
                "description": desc or "",
                "schema": schema_obj,
            })

        pkg = {
            "profile": "data-package",
            "name": base.name.lower().replace(" ", "-"),
            "resources": resources,
        }

        out_path = base / "datapackage.json"
        out_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
        return out_path

    # def export_datapackage(
    #     self,
    #     base_dir: Union[str, pathlib.Path],
    #     name: str = "cesdm-model",
    #     title: Optional[str] = None,
    #     description: str = "",
    #     include_long: bool = False,
    #     include_by_class: bool = False,
    #     include_by_class_wide: bool = True,
    #     include_placeholders: bool = True,) -> pathlib.Path:
    #     """
    #     Export the model as a Frictionless Data Package.

    #     Parameters
    #     ----------
    #     base_dir :
    #         Output directory for ``datapackage.json`` and CSV resources.
    #     name :
    #         Machine-readable name of the data package.
    #     title :
    #         Optional human-readable title.
    #     include_long :
    #         Whether to include the long CSV representation as a resource.
    #     include_by_class :
    #         Whether to include narrow per-class CSVs.
    #     include_by_class_wide :
    #         Whether to include wide per-class CSVs (default).
    #     """

    #     import json as _json
    #     import pathlib as _pl

    #     base = _pl.Path(base_dir)
    #     base.mkdir(parents=True, exist_ok=True)

    #     resources = []

    #     # ---- 1) Long CSV ----
    #     if include_long:
    #         long_path = base / "long.csv"
    #         # uses helper that also writes long.csv.schema.json
    #         self.export_long_csv_with_schema(long_path)

    #         resources.append({
    #             "name": "long",
    #             "path": long_path.name,  # "long.csv"
    #             "profile": "tabular-data-resource",
    #             "schema": long_path.name + ".schema.json",  # "long.csv.schema.json"
    #         })

    #     # ---- 2) Per-class narrow CSVs ----
    #     if include_by_class:
    #         bc_dir = base / "by_class"
    #         bc_dir.mkdir(exist_ok=True)

    #         # will write <ClassName>.csv + .schema.json in bc_dir
    #         self.export_csv_by_class_with_schema(
    #             bc_dir,
    #             include_placeholders=include_placeholders,
    #         )

    #         for cname in sorted(self.classes.keys()):
    #             csv_path = bc_dir / f"{cname}.csv"
    #             if not csv_path.exists():
    #                 continue

    #             schema_path = csv_path.with_suffix(csv_path.suffix + ".schema.json")

    #             res_name = self._slugify_resource_name(f"{cname}_by_class_wide")

    #             resources.append({
    #                 "name": res_name,                           # e.g. "servicedemandmodel_by_class"
    #                 "path": str(csv_path.relative_to(base)),    # path may keep CamelCase
    #                 "profile": "tabular-data-resource",
    #                 "schema": str(schema_path.relative_to(base)),
    #             })

    #     # ---- 3) Per-class wide CSVs ----
    #     if include_by_class_wide:
    #         bcw_dir = base / "by_class_wide"
    #         bcw_dir.mkdir(exist_ok=True)

    #         # will write <ClassName>.csv + .schema.json in bcw_dir
    #         self.export_csv_by_class_wide_with_schema(
    #             bcw_dir,
    #             include_placeholders=include_placeholders,
    #         )

    #         for cname in sorted(self.classes.keys()):
    #             csv_path = bcw_dir / f"{cname}.csv"
    #             if not csv_path.exists():
    #                 continue

    #             schema_path = csv_path.with_suffix(csv_path.suffix + ".schema.json")

    #             res_name = self._slugify_resource_name(f"{cname}_by_class")

    #             resources.append({
    #                 "name": res_name,                           # e.g. "servicedemandmodel_by_class"
    #                 "path": str(csv_path.relative_to(base)),    # path may keep CamelCase
    #                 "profile": "tabular-data-resource",
    #                 "schema": str(schema_path.relative_to(base)),
    #             })

    #     # ---- 4) Build datapackage.json ----
    #     dp = {
    #         "profile": "data-package",
    #         "name": name,
    #         "title": title or name,
    #         "description": description,
    #         "resources": resources,
    #     }

    #     dp_path = base / "datapackage.json"
    #     dp_path.write_text(
    #         _json.dumps(dp, indent=2, ensure_ascii=False),
    #         encoding="utf-8",
    #     )

    #     return dp_path

        """
        Export all entities as a single long CSV table.

        Parameters
        ----------
        path :
            Output CSV file path.

        Notes
        -----
        The long format has one row per attribute or relation and is suited for
        generic ETL pipelines and graph-oriented processing.
        """
        import csv

        class_map = getattr(self, "classes", {}) or {}
        entity_map = getattr(self, "entities", {}) or {}

        fieldnames = [
            "entity_class",
            "entity_id",
            "attribute_id",
            "attribute_value",
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

                # Attributes
                for a in attr_names:
                    has_val  = a in data and data[a] not in ("", None)
                    if has_val:
                        rows.append({
                            "entity_class": class_name,
                            "entity_id": eid,
                            "attribute_id": a if has_val else "",
                            "attribute_value": data.get(a, "") if has_val else "",
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
                            "relation_type": r,
                            "relation_id": tgt,
                        })

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
