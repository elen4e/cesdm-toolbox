"""cesdm.domain.model.hierarchical_yaml — Hierarchical (CESDM-native) YAML persistence

The asset-nested YAML round-trip that is CESDM's native,
version-control-friendly representation.

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


class HierarchicalYamlMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def _render_entity_block(
        self,
        ent,
        cname: str,
        *,
        skip_relations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Render one entity using schema groups for hierarchical YAML.

        The internal EAR entity remains flat.  ``belongsToGroup`` is read only
        from the schema and used to organize the exported representation. Fields
        without an explicit group are placed under ``core``.

        Attribute entries retain their structured representation, for example::

            nominal_power_capacity:
              value: 500
              unit: MW

        Relations are represented analogously with ``target_entity_ids``.
        """
        cdef = self.classes.get(cname)
        if cdef is None:
            return {}
        attrs_def, refs_def = self._collect_inherited_fields(cdef)
        data = getattr(ent, "data", {}) or {}
        skip_rels = set(skip_relations or [])

        attrs_by_group: Dict[str, Dict[str, Any]] = {}
        for aname, adef in attrs_def.items():
            if aname not in data or data[aname] in ("", None):
                continue
            raw = data[aname]
            spec = dict(raw) if isinstance(raw, dict) else {"value": raw}
            groups = list(getattr(adef, "belongsToGroup", None) or ["core"])
            for group in groups:
                attrs_by_group.setdefault(str(group), {})[aname] = spec

        refs_by_group: Dict[str, Dict[str, Any]] = {}
        for rname, rdef in refs_def.items():
            if rname in skip_rels or rname not in data or data[rname] in ("", None):
                continue
            val = data[rname]
            targets = (
                [v for v in val if v not in ("", None)]
                if isinstance(val, (list, tuple))
                else [val]
            )
            if not targets:
                continue
            spec = {"target_entity_ids": targets}
            groups = list(getattr(rdef, "belongsToGroup", None) or ["core"])
            for group in groups:
                refs_by_group.setdefault(str(group), {})[rname] = spec

        block: Dict[str, Any] = {}
        if attrs_by_group:
            block["attributes"] = attrs_by_group
        if refs_by_group:
            block["relations"] = refs_by_group
        return block

    def export_yaml_hierarchical(
        self,
        path: str | pathlib.Path,
        *,
        include_library: str = "referenced",
    ) -> None:
        """
        Export the model to a hierarchical YAML file.

        Structure
        ---------
        Non-asset entities (Carrier, NetworkNode, GeographicalRegion, …)
        are exported flat, exactly as in :meth:`export_yaml`.

        Asset entities (GenerationUnit, StorageUnit, DemandUnit, …) hold
        their own dispatch/topology/power-flow attributes and relations
        directly (see CHANGELOG.md: this toolbox's "initial version
        without views") -- exported flat too, alongside the asset's
        identity fields. Only genuinely separate linked entities --
        Result entities from an analysis run (GenerationUnit.DispatchResult,
        etc.), the only classes left using the reportsOn pattern --
        are nested under a ``representations`` key, grouped by class
        name. The ``reportsOn`` back-relation is omitted from each
        nested block because it is implicit in the nesting::

            GenerationUnit:
              tech.wind.at00:
                attributes:
                  - id: name
                    value: Wind AT00
                  - id: nominal_power_capacity
                    value: 450.0
                    unit: MW
                relations:
                  - id: hasTechnology
                    target_entity_ids: [Generation.Renewable.Wind.Onshore]
                  - id: atNode
                    target_entity_ids: [node.at00]
                representations:
                  GenerationUnit.DispatchResult:
                    attributes:
                      - id: total_generation
                        value: 1234.0
                        unit: MWh
                    relations:
                      - id: hasRunRecord
                        target_entity_ids: [run.2026_scenario_A]

        The output file can be round-tripped via
        :meth:`import_yaml_hierarchical`.

        Parameters
        ----------
        path :
            Output file path. Parent directories are created if absent.
        include_library :
            ``"none"`` | ``"referenced"`` | ``"all"`` — how much library
            master data to embed (default ``"referenced"``).
        """
        with self._export_entity_scope(include_library):  # type: ignore[attr-defined]
            self._export_yaml_hierarchical_body(path)

    def _export_yaml_hierarchical_body(self, path: str | pathlib.Path) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        view_index = self._build_view_index()
        view_cls_set = set(self._discover_view_classes())
        asset_cls_set = self._discover_asset_classes()

        out: Dict[str, Any] = {}

        # Reserved metadata block (skipped on import, see
        # import_yaml_hierarchical): records which schema version this
        # model was built against, so a later import against a
        # different schema tree can warn on a major-version mismatch
        # instead of silently misinterpreting the data.
        manifest = getattr(self, "schema_manifest", None)
        if manifest is not None and manifest.is_versioned:
            out["_cesdm_meta"] = {
                "schema_version": manifest.version,
                "format": "cesdm-hierarchical-yaml",
            }

        for cname, cdef in self.classes.items():
            ents = self.entities.get(cname) or {}
            if not ents:
                continue

            # Skip view classes — they appear nested under assets
            if cname in view_cls_set:
                continue

            class_blob: Dict[str, Any] = {}

            for eid, ent in ents.items():
                block = self._render_entity_block(ent, cname)

                # For asset classes, attach their result entities *before*
                # deciding whether to skip. An asset can legitimately carry
                # zero direct attributes/relations of its own — e.g. an
                # asset whose only data lives in a DispatchResult or
                # PowerFlowResult. Previously such an asset (and its
                # attached results) was silently dropped from the export
                # entirely, because the empty-block check ran before the
                # results were even looked up.
                representations: Dict[str, Any] = {}
                if cname in asset_cls_set:
                    views_for_asset = view_index.get(eid, {})
                    if views_for_asset:
                        for vcls, vent in views_for_asset.items():
                            vblock = self._render_entity_block(
                                vent, vcls,
                                skip_relations=[self._REPORTS_ON_REL]
                            )
                            if vblock:
                                representations[vcls] = vblock
                        if representations:
                            block["representations"] = representations

                if not block:
                    continue

                class_blob[eid] = block

            if class_blob:
                out[cname] = class_blob

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(out, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)

    def import_yaml_hierarchical(self, path: str, *, strict_unknown: bool = False):
        """
        Import entities from a hierarchical YAML file produced by
        :meth:`export_yaml_hierarchical`.

        The method understands both the flat format (as produced by
        :meth:`import_yaml`) and the hierarchical format where asset entities
        carry a ``representations`` key whose values are view blocks.

        For hierarchical blocks the view entity id is reconstructed as::

            <view_class_snake_case>.<asset_id>

        e.g. ``nodal_connection_view.tech.wind.at00``.  The reportsOn
        back-relation is automatically injected on each view, so the
        round-trip is lossless.

        Parameters
        ----------
        path :
            Input YAML file path.
        strict_unknown :
            Unknowns are collected but never fatal.

        Returns
        -------
        dict
            Summary with keys created_entities, set_attributes,
            set_relations, unknowns.
        """
        import yaml as _yaml

        class_map = getattr(self, "classes", {}) or {}
        known_attrs = {}
        known_refs  = {}
        for cname, cdef in class_map.items():
            a, r = self._collect_inherited_fields(cdef)
            known_attrs[cname] = set(a.keys())
            known_refs[cname]  = set(r.keys())

        created = set_attr = set_ref = 0
        unknowns = []

        def _ensure_entity(cls, eid):
            nonlocal created
            if cls not in self.entities:
                self.entities[cls] = {}
            if eid not in self.entities[cls]:
                self.add_entity(cls, eid)
                created += 1

        def _ingest_attrs(cls, eid, attrs_block):
            nonlocal set_attr
            items = []
            if isinstance(attrs_block, dict):
                # New grouped form: attributes: {core: {name: {value: ...}}, ...}
                # Old mapping form remains supported: attributes: {name: value}.
                if attrs_block and all(
                    isinstance(v, dict) and k not in known_attrs.get(cls, set())
                    for k, v in attrs_block.items()
                ):
                    for group_block in attrs_block.values():
                        if isinstance(group_block, dict):
                            items.extend(group_block.items())
                else:
                    items = list(attrs_block.items())
            elif isinstance(attrs_block, list):
                for rec in attrs_block:
                    if not isinstance(rec, dict):
                        continue
                    aname = rec.get("id") or rec.get("name")
                    if not aname:
                        continue
                    aval = {k: v for k, v in rec.items() if k not in {"id", "name"}}
                    if aval:
                        items.append((aname, aval))
            else:
                return

            seen = set()
            for aname, aval in items:
                # A schema field can belong to multiple groups and therefore
                # appear more than once in hierarchical YAML. Import it once.
                if aname in seen:
                    continue
                seen.add(aname)
                lookup = self._attribute_id_for_schema_lookup(aname)
                if (
                    self._is_legacy_attribute_write(aname)
                    or lookup in known_attrs.get(cls, set())
                ):
                    if aval not in ("", None):
                        self.add_attribute(eid, aname, aval)
                        set_attr += 1
                else:
                    unknowns.append((cls, eid, f"unknown attribute: {aname}"))

        def _ingest_rels(cls, eid, rels_block, skip=None):
            nonlocal set_ref
            skip = skip or set()
            items = []
            if isinstance(rels_block, dict):
                # New grouped form: relations: {core: {atNode: {...}}, ...}
                # Old mapping form remains supported.
                if rels_block and all(
                    isinstance(v, dict) and k not in known_refs.get(cls, set())
                    for k, v in rels_block.items()
                ):
                    for group_block in rels_block.values():
                        if isinstance(group_block, dict):
                            items.extend(group_block.items())
                else:
                    items = list(rels_block.items())
            elif isinstance(rels_block, list):
                for rec in rels_block:
                    if not isinstance(rec, dict):
                        continue
                    rname = rec.get("id") or rec.get("name")
                    if not rname or rname in skip:
                        continue
                    raw_ids = (
                        rec.get("target_entity_ids")
                        or rec.get("targets")
                        or rec.get("target_entity_id")
                    )
                    if raw_ids in ("", None):
                        continue
                    ids = list(raw_ids) if isinstance(raw_ids, (list, tuple)) else [raw_ids]
                    items.append((rname, ids))
            else:
                return

            seen = set()
            for rname, rid in items:
                if rname in seen:
                    continue
                seen.add(rname)
                if rname in skip:
                    continue
                if rname in known_refs.get(cls, set()):
                    if isinstance(rid, dict):
                        rid = (
                            rid.get("target_entity_ids")
                            or rid.get("targets")
                            or rid.get("target_entity_id")
                        )
                    targets = rid if isinstance(rid, (list, tuple)) else [rid]
                    targets = [t for t in targets if t not in ("", None)]
                    if not targets:
                        continue
                    # add_relation() is a *set*, not an *append* -- it has
                    # no accumulation semantics, and even stringifies a
                    # list if given one directly rather than storing it.
                    # Set the first target normally (validates the
                    # relation/target exactly as before), then, if there's
                    # more than one, build the real list directly on the
                    # entity's own data -- needed for any relation a
                    # single entity can legitimately reference more than
                    # one target through (e.g. HydroGenerationUnit.
                    # drawsFromHydraulicStorage after spatial/technology
                    # aggregation merges different reservoir-side
                    # technology groups onto one generator -- see
                    # CHANGELOG).
                    self.add_relation(eid, rname, targets[0])
                    set_ref += 1
                    if len(targets) > 1:
                        entity_obj = self.entities.get(cls, {}).get(eid)
                        if entity_obj is not None and hasattr(entity_obj, "data"):
                            entity_obj.data[rname] = list(targets)
                else:
                    unknowns.append((cls, eid, f"unknown relation: {rname}"))

        def _view_id(vcls, asset_id):
            import re as _re
            snake = _re.sub(r"(?<!^)(?=[A-Z])", "_", vcls).lower()
            return f"{snake}.{asset_id}"

        with open(path, "r", encoding="utf-8") as f:
            payload = _yaml.safe_load(f) or {}

        # Reserved metadata block written by export_yaml_hierarchical.
        # Not a class section — check schema-version compatibility
        # against the currently loaded schema, then drop it before the
        # class loop below (which treats every remaining top-level key
        # as an entity class name).
        schema_version_warning = None
        meta = payload.pop("_cesdm_meta", None)
        if isinstance(meta, dict):
            file_version = meta.get("schema_version")
            manifest = getattr(self, "schema_manifest", None)
            if (
                file_version
                and manifest is not None
                and manifest.is_versioned
                and not manifest.is_compatible_with(file_version)
            ):
                schema_version_warning = (
                    f"Model was exported against CESDM schema version "
                    f"{file_version!r}, but the currently loaded schema is "
                    f"version {manifest.version!r} (different major version). "
                    f"Structural class/attribute/relation changes between "
                    f"major versions may cause data to be silently dropped "
                    f"or misclassified — see docs/architecture/"
                    f"schema_governance.md."
                )
                import warnings
                warnings.warn(schema_version_warning, stacklevel=2)

        for class_name, section in payload.items():
            class_name = self._resolve_entity_class_alias(class_name)
            if class_name not in class_map:
                unknowns.append((class_name, None, "unknown class"))
                continue
            if not isinstance(section, dict):
                continue

            for eid, block in section.items():
                if not isinstance(block, dict):
                    continue

                _ensure_entity(class_name, eid)
                _ingest_attrs(class_name, eid, block.get("attributes") or {})
                _ingest_rels(class_name, eid, block.get("relations") or {})

                representations = block.get("representations") or {}
                if not isinstance(representations, dict):
                    continue

                for vcls, vblock in representations.items():
                    if vcls not in class_map:
                        unknowns.append((vcls, None, "unknown view class"))
                        continue
                    if not isinstance(vblock, dict):
                        continue

                    vid = _view_id(vcls, eid)
                    _ensure_entity(vcls, vid)

                    ra = self._REPORTS_ON_REL
                    if ra in known_refs.get(vcls, set()):
                        self.add_relation(vid, ra, eid)
                        set_ref += 1

                    _ingest_attrs(vcls, vid, vblock.get("attributes") or {})
                    _ingest_rels(
                        vcls, vid, vblock.get("relations") or {},
                        skip={self._REPORTS_ON_REL},
                    )

        return {
            "created_entities": created,
            "set_attributes":   set_attr,
            "set_relations":    set_ref,
            "unknowns":         unknowns,
            "schema_version_warning": schema_version_warning,
        }

    ## Import methods

    # ── Parquet profile I/O ───────────────────────────────────────────────────
