"""ear.model.schema_loading — Schema loading & class introspection

Loading YAML class definitions, resolving inheritance, and
introspecting the resulting class tree (used by validation, export,
and documentation generation).

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
Behaviour is unchanged; only module boundaries moved.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Union, Tuple
from difflib import get_close_matches
import os, pathlib
import yaml
from pathlib import Path
import re

from ear.entity_class import EntityClass
from ear.relation_def import RelationDef
from ear.attribute_def import AttributeDef


class SchemaLoadingMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def resolve_inheritance(self):

        """
        Resolve inheritance between all loaded classes.

        This method:

        - checks for missing base classes,
        - detects cycles in the inheritance graph,
        - merges attributes and relations from parent classes into child classes
          (child definitions override parent definitions in case of name clashes).

        After calling this, :attr:`classes` contains fully merged class definitions
        and :attr:`inheritance` is a mapping::

            {child_class_name: [parent_class_name, ...]}.
        """

        # Normalize/canonicalize the ``parents`` names and coerce to lists
        for cname, c in self.classes.items():
            ext = getattr(c, "parents", None)
            # Accept single string, list/tuple/set of strings, or None/False/""
            if not ext:
                parents: List[str] = []
            elif isinstance(ext, str):
                parents = [ext]
            elif isinstance(ext, (list, tuple, set)):
                parents = [p for p in ext if p]
            else:
                parents = [str(ext)]

            canon_parents: List[str] = []
            for p in parents:
                try:
                    canon_parents.append(self._canonicalize_class(p))
                except Exception:
                    # keep as-is if canonicalization fails
                    canon_parents.append(p)

            c.parents = canon_parents

        # Topological order over possibly multiple parents
        order: List[str] = []
        temp: set[str] = set()
        perm: set[str] = set()

        def visit(name: str) -> None:
            if name in perm:
                return
            if name in temp:
                raise ValueError(f"Inheritance cycle at {name}")
            temp.add(name)

            c = self.classes[name]
            parents = getattr(c, "parents", []) or []
            if isinstance(parents, str):
                parents = [parents]
            for parent in parents:
                if parent not in self.classes:
                    raise ValueError(f"Unknown parent class '{parent}' for '{name}'")
                visit(parent)

            temp.remove(name)
            perm.add(name)
            order.append(name)

        for name in list(self.classes.keys()):
            if name not in perm:
                visit(name)

        # Merge in topo order so all parents are processed before the child
        for name in order:
            c = self.classes[name]
            parents: List[str] = getattr(c, "parents", []) or []
            if isinstance(parents, str):
                parents = [parents]
            if not parents:
                continue

            # Start with a fresh dict and merge parents from left to right.
            merged_attrs: Dict[str, AttributeDef] = {}
            merged_refs: Dict[str, RelationDef] = {}
            # `abstract` is NOT inherited/propagated from parents: being a
            # subclass of an abstract base does not make the subclass
            # abstract -- that is the entire point of an abstract base
            # class (e.g. GenerationUnit is a concrete subclass of the
            # abstract EnergyAssetInstance). A class's abstractness is
            # exactly what its own schema file declares (default False).
            #
            # This used to incorrectly propagate abstract=True down every
            # inheritance chain, so every class in the tree ended up
            # abstract (any class with an eventually-abstract ancestor,
            # which in practice is all of them). That silently broke
            # build_pydantic_models(), which only registers a class in
            # self.py_models when `not c.abstract` -- so py_models was
            # always empty. See CHANGELOG.md.
            abstract_flag = bool(getattr(c, "abstract", False))

            # view_family DOES genuinely inherit (unlike abstract, above) --
            # it's a real "is-a" categorization (e.g. a concrete dispatch
            # view tagged only on its abstract family root should still
            # resolve to that root's view_family), not something that
            # becoming a subclass invalidates. Own declared value always
            # wins; otherwise inherit the first parent (in declaration
            # order) that has one resolved already -- safe because we
            # process classes in topological order, so every parent here
            # has already been fully resolved.
            view_family = getattr(c, "view_family", None)
            if view_family is None:
                for pname in parents:
                    pf = getattr(self.classes[pname], "view_family", None)
                    if pf is not None:
                        view_family = pf
                        break

            for pname in parents:
                p = self.classes[pname]

                # attributes: first parent wins, then later parents, then child
                for an, a in getattr(p, "attributes", {}).items():
                    if an not in merged_attrs:
                        merged_attrs[an] = a

                # relations: same strategy
                pref = getattr(p, "relations", {}) or {}
                for rn, r in pref.items():
                    if rn not in merged_refs:
                        merged_refs[rn] = r

            # Finally, child overrides everything
            child_attrs = getattr(c, "attributes", {}) or {}
            child_refs = getattr(c, "relations", {}) or {}

            merged_attrs.update(child_attrs)
            merged_refs.update(child_refs)

            c.attributes = merged_attrs
            c.relations = merged_refs
            c.abstract = abstract_flag
            c.view_family = view_family

        # Update the public inheritance mapping: always a list of parents
        inh: Dict[str, List[str]] = {}
        for cname, c in self.classes.items():
            parents = getattr(c, "parents", []) or []
            if isinstance(parents, str):
                parents = [parents] if parents else []
            inh[cname] = list(parents)

        self.inheritance = inh

    def build_class_indexes(self):

        """
        Build internal indexes for fast class lookup and introspection.

        This is typically called automatically after loading and resolving the schema.
        It may create helper structures such as:

        - maps from canonical class names to definitions,
        - reverse inheritance mappings,
        - lists of concrete subclasses for abstract base classes.
        """

        # Children map: parent -> set(children)
        children: Dict[str, set] = {c: set() for c in self.classes}
        for cname, ec in self.classes.items():
            parents = getattr(ec, "parents", []) or []
            if isinstance(parents, str):
                parents = [parents]
            for p in parents:
                if p in children:
                    children[p].add(cname)

        # All descendants (transitive closure)
        self.descendants = {c: set() for c in self.classes}

        def dfs(c: str) -> set:
            for ch in children.get(c, ()):
                if ch not in self.descendants[c]:
                    self.descendants[c].add(ch)
                    self.descendants[c] |= dfs(ch)
            return self.descendants[c]

        for c in self.classes:
            dfs(c)

    def debug_schema(self):

        """
        Print a human-readable summary of the loaded schema to stdout.

        Useful for debugging or exploring which classes, attributes and relations
        are available.
        """

        out = {}
        for cname, cdef in self.classes.items():
            out[cname] = {
                "attributes": list(getattr(cdef, "attributes", {}).keys()),
                "relations": list(getattr(cdef, "relations", {}).keys()),
                "parents": getattr(cdef, "parents", None),
                "abstract": getattr(cdef, "abstract", False),
            }
        return out


    

    def _get_meta(self, node, key, default=None):
        """
        Read field from an attr/ref definition (dict or object).
        """
        if node is None:
            return default
        if isinstance(node, dict):
            return node.get(key, default)
        return getattr(node, key, default)

    def _get_parent_name(self, cdef):
        """Return the parent class name, regardless of the field name used."""
        return (
            getattr(cdef, "parents", None)
            or getattr(cdef, "parents", None)
            or getattr(cdef, "base_class", None)
        )

    def _lookup_class(self, name):
        """Find a class by full or short name in self.classes."""
        if not name:
            return None

        if name in self.classes:
            return self.classes[name]
        short = str(name).split(".")[-1]
        return self.classes.get(short)

    def _to_name_map(self, container):
        """
        Normalize attributes/relations into a {name: def} dict, accepting:
        - dict: {name: def}
        - list[object with .name] or list[dict with 'name']
        """
        out = {}
        if not container:
            return out
        if isinstance(container, dict):
            return dict(container)
        if isinstance(container, (list, tuple)):
            for it in container:
                if it is None:
                    continue
                if isinstance(it, dict):
                    nm = it.get("name")
                    if nm:
                        out[nm] = it
                else:
                    nm = getattr(it, "name", None)
                    if nm:
                        out[nm] = it
        return out

    def _collect_inherited_fields(self, class_def):
        """
        Collect attributes + relations along the inheritance chain (child wins).
        Uses any pre-resolved containers if present, otherwise walks parents.
        """
        # Prefer already-resolved fields if your loader provides them


        for cand in ("all_attributes", "attributes_resolved", "resolved_attributes"):
            attrs = self._to_name_map(getattr(class_def, cand, None))
            if attrs:
                break
        else:
            attrs = self._to_name_map(getattr(class_def, "attributes", None))

        for cand in ("all_relations", "relations_resolved", "resolved_relations"):
            refs = self._to_name_map(getattr(class_def, cand, None))
            if refs:
                break
        else:
            refs = self._to_name_map(getattr(class_def, "relations", None))

        # If resolved containers were non-empty, we can return now
        if attrs and refs:
            return attrs, refs

        # Otherwise, walk up the chain: child -> parent -> ...
        seen = set()
        attrs = {}
        refs = {}

        # Use a stack (DFS) or queue for BFS.
        stack = [class_def]

        while stack:
            cdef = stack.pop()

            cname = getattr(cdef, "name", None)
            if cname in seen:
                continue
            seen.add(cname)

            # Merge attributes/relations for this class (including the starting one)
            p_attrs = self._to_name_map(getattr(cdef, "attributes", None))
            p_refs  = self._to_name_map(getattr(cdef, "relations", None))

            for k, v in p_attrs.items():
                attrs.setdefault(k, v)  # first (nearest child) wins

            for k, v in p_refs.items():
                refs.setdefault(k, v)   # first (nearest child) wins

            # ---- Handle parent_name being a list OR scalar ----
            parent_names = self._get_parent_name(cdef)

            if parent_names:
                if isinstance(parent_names, str):
                    parent_names = [parent_names]

                for pname in parent_names:
                    parent_class = self._lookup_class(pname)
                    if parent_class:
                        stack.append(parent_class)

        return attrs, refs

    def _known_fields(self, class_def):
        """Return the set of all attribute+relation names for the class (incl. parents)."""
        a, r = self._collect_inherited_fields(class_def)
        return set(a.keys()) | set(r.keys())

    def _canonicalize_class(self, cls_name: str) -> str:
        if cls_name in self.classes:
            return cls_name
        for k in self.classes:
            if k.lower() == str(cls_name).lower():
                return k
        cand = str(cls_name).replace("-", "_").replace(" ", "_")
        cand = (cand[:1].upper() + cand[1:]) if cand else cand
        if cand in self.classes:
            return cand
        raise ValueError(f"Unknown entity class: {cls_name}")

    ### Entity field setters:

    def format_class_tree(self) -> str:
        """
        Baut einen Vererbungsbaum aller Klassen im Model.

        Erwartet: ``model.classes = {class_name: ClassDef}``, und jede ClassDef hat
        ``.parents`` entweder als Liste von Elternamen, einen einzelnen String oder ``None``.
        """
        # Parent-Map: child -> [parent_name, ...]
        parents: Dict[str, List[str]] = {}
        for name, cdef in self.classes.items():
            ext = getattr(cdef, "parents", []) or []
            if isinstance(ext, str):
                ext = [ext]
            parents[name] = list(ext)

        # Kinder-Map: parent_name -> [child_names]
        children: Dict[str, List[str]] = {}
        for cls, parent_list in parents.items():
            if not parent_list:
                continue
            for parent in parent_list:
                children.setdefault(parent, []).append(cls)

        # Kinder alphabetisch sortieren
        for lst in children.values():
            lst.sort()

        lines: List[str] = []

        def walk(node: str, prefix: str = "", is_last: bool = True):
            connector = "└─" if is_last else "├─"
            lines.append(f"{prefix}{connector} {node}")

            child_list = children.get(node, [])
            for i, child in enumerate(child_list):
                last_child = (i == len(child_list) - 1)
                new_prefix = prefix + ("   " if is_last else "│  ")
                walk(child, new_prefix, last_child)

        # Wurzeln (Klassen ohne Parent)
        roots = [name for name, plist in parents.items() if not plist]
        roots.sort()

        for i, root in enumerate(roots):
            walk(root, prefix="", is_last=(i == len(roots) - 1))

        return "\n".join(lines)

    def print_class_tree(self):
        print(self.format_class_tree())

    def format_attribute_tree(self, groups: Dict[str, List]):  # List[AttributeDef] in echt
        """
        Nimmt ein Dict[group_name -> List[AttributeDef]] und
        gibt einen Tree-String zurück.
        """
        lines = []

        # in stabile Reihenfolge bringen (optional: nach Gruppenname sortieren)
        group_items = list(groups.items())
        # wenn du explizite Reihenfolge willst, lass das sort() weg
        # group_items.sort(key=lambda kv: kv[0])

        for gi, (group_name, attrs) in enumerate(group_items):
            is_last_group = gi == len(group_items) - 1
            group_prefix = "└─" if is_last_group else "├─"
            lines.append(f"{group_prefix} {group_name}")

            # Attribute sortieren (erst nach order, dann Name)
            attrs_sorted = sorted(
                attrs,
                key=lambda a: (
                    getattr(a, "order", 0) if getattr(a, "order", None) is not None else 0,
                    a.name,
                ),
            )

            for ai, attr in enumerate(attrs_sorted):
                is_last_attr = ai == len(attrs_sorted) - 1
                connector = "└─" if is_last_attr else "├─"
                indent = "   " if is_last_group else "│  "
                required_mark = "*" if getattr(attr, "required", False) else ""
                attr_type = getattr(attr, "type", "?")
                lines.append(f"{indent}{connector} {attr.name}{required_mark} : {attr_type}")

        return "\n".join(lines)

    def print_attribute_tree(self, groups: Dict[str, List]):
        """
        Convenience-Funktion, die den Tree direkt auf stdout ausgibt.
        """
        print(self.format_attribute_tree(groups))

    def get_attributes_grouped(self, class_name: str) -> Dict[str, List[AttributeDef]]:
        """
        Liefert Attribute einer Klasse inkl. geerbter Attribute,
        gruppiert nach .group und sortiert nach .order / Name.
        """
        # class_def holen
        cdef = self.classes[class_name]

        # <-- HIER: Inheritance berücksichtigen
        attrs_def, _ = self._collect_inherited_fields(cdef)

        groups: Dict[str, List[AttributeDef]] = {}

        for ad in attrs_def.values():
            g = getattr(ad, "group", None) or "master_data"   # Default-Gruppe
            groups.setdefault(g, []).append(ad)

        # sortieren innerhalb der Gruppe
        for g, lst in groups.items():
            lst.sort(
                key=lambda a: (
                    getattr(a, "order", 0) if getattr(a, "order", None) is not None else 0,
                    a.name,
                )
            )

        return groups


    ### Other Helpers 

    def _constraints_to_dict(self, obj):
        """
        Normalize a constraints object to a plain dict.
        Works if obj is None, dict, or an object (e.g., pydantic/dataclass) with attributes.
        """
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        # probe common keys
        keys = (
            "minimum", "maximum", "enum", "regex",
            "min_length", "max_length",
            "min_items", "max_items", "unique"
        )
        out = {}
        for k in keys:
            if hasattr(obj, k):
                out[k] = getattr(obj, k)
        return out

    def is_class_derived_from(
        self,
        subclass_name: str,
        parent_name: str,
        inheritance: Dict[str, Union[str, List[str], None]],
    ) -> bool:
        """
        Check whether a class is derived from a given base class.

        Parameters
        ----------
        subclass_name :
            Name of the class to check.
        parent_name :
            Name of the potential base class.

        Returns
        -------
        bool
            ``True`` if ``subclass_name`` is the same as or inherits (directly or
            indirectly) from ``parent_name``, otherwise ``False``.
        """

        # Trivial case
        if subclass_name == parent_name:
            return True

        # Walk up all parents; ``inheritance`` may map to a single parent string,
        # a list of parents, or None for root classes.
        visited: set[str] = set()
        stack: List[str] = [subclass_name]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            parents = inheritance.get(current)
            if parents is None:
                continue
            if isinstance(parents, str):
                parents = [parents]

            for p in parents:
                if not p:
                    continue
                if p == parent_name:
                    return True
                if p not in visited:
                    stack.append(p)

        return False

    def obj_is_instance_of(
        obj: dict,
        parent_name: str,
        inheritance: dict[str, str | None],
        class_key: str = "class",) -> bool:

        """
        Returns True if `obj`'s class (e.g. obj["class"]) is derived from
        `parent_name` according to the inheritance map.
        """
        cls_name = obj.get(class_key)
        if cls_name is None:
            return False
        return self.is_class_derived_from(cls_name, parent_name, inheritance)

    def load_classes_from_yaml(self, path: Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]):
        """
        Load class definitions from CESDM YAML schemas.

        Supports two layouts:

        1) **Legacy / inline layout**:
           Each entity YAML contains embedded ``attributes`` and ``relations`` specs.

        2) **LinkML-like separated layout**:
           - ``attributes.yaml`` defines all attribute (slot) specifications
           - ``relations.yaml`` defines all relation specifications
           - ``entities/*.yaml`` define entity classes and *map* attributes/relations by id,
             optionally overriding ``required`` and ``default``.

        3) **Schema augmentations**:
           Extension schemas may define their own attributes and relations and attach them to
           already existing entity classes without editing the base schema. An
           augmentation references registry ids; it never defines fields inline::

               augmentations:
                 GenerationUnit:
                   groups:
                     agent_based:
                       attributes:
                         - id: bidding_strategy
                       relations:
                         - id: ownedByAgent

           The referenced ids must be defined in either the base schema or an extension-local
           ``attributes`` / ``relations`` registry. All loaded registries form one
           combined runtime registry; no base-schema file is modified.

        This implementation uses a **two-phase schema validation** approach:

        Phase 1 (parse): load registries + entity documents, collect attribute/relation *references*.
        Phase 2 (validate + materialize): verify every reference exists, then materialize the final
        per-entity attribute/relation specs (base definition + overrides).

        Parameters
        ----------
        path:
            Directory containing schemas (and optionally an ``entities`` subfolder), a single YAML
            file, or a list/tuple/set of any of those -- loaded in order, so a later path's classes
            can extend/reference an earlier one's (this is how ``schemas/agentbased``'s own
            ``extends:`` mechanism is implemented under the hood; passing
            ``["schemas/cesdm", "schemas/agentbased"]`` directly here has the same effect).
        """
        import pathlib, yaml, copy
        from difflib import get_close_matches

        # Accept either a single schema path or an ordered list/tuple/set of
        # schema paths.  Later paths may extend classes loaded from earlier
        # paths.  Duplicate global attribute/relation ids with different
        # definitions are rejected, because silently overriding them would make
        # the resulting model ambiguous.
        if isinstance(path, (list, tuple, set)):
            paths = [pathlib.Path(p) for p in path]
            if not paths:
                raise ValueError("At least one schema path must be provided")
        else:
            paths = [pathlib.Path(path)]
        path = paths[0]

        # Attach schema version/stability metadata (SCHEMA_MANIFEST.yaml
        # in the primary schema directory), if present. Never blocks
        # loading — see ear.schema_manifest.SchemaManifest.load.
        from ear.schema_manifest import SchemaManifest
        self.schema_manifest = SchemaManifest.load(path if path.is_dir() else path.parent)

        # If the primary schema declares dependencies via `extends:`,
        # auto-load them first (as the base layer) unless the caller
        # already included them explicitly. This means a domain
        # extension's SCHEMA_MANIFEST.yaml is the single source of
        # truth for "this schema tree requires that one" — callers no
        # longer need to remember to pass both paths themselves, and
        # the extension no longer needs to duplicate the base tree's
        # class definitions just to be loadable on its own.
        if self.schema_manifest.extends:
            existing_resolved = {p.resolve() for p in paths}
            base_paths = [
                ext for ext in self.schema_manifest.extends
                if ext not in existing_resolved
            ]
            if base_paths:
                paths = base_paths + paths

        # ----------------------------
        # Load global registries (if any)
        # ----------------------------
        self.global_attributes = {}
        self.global_relations = {}
        self.global_units = {}

        def _load_one_yaml(pth: pathlib.Path):
            with open(pth, "r", encoding="utf-8") as f:
                return list(yaml.safe_load_all(f))

        def _load_registry(pth: pathlib.Path, key: str) -> Dict[str, Dict[str, Any]]:
            if not pth.exists():
                return {}
            docs = _load_one_yaml(pth)
            reg: Dict[str, Dict[str, Any]] = {}
            for d in docs:
                if not d:
                    continue
                block = d.get(key) if isinstance(d, dict) else None
                if not isinstance(block, dict):
                    continue
                for _id, spec in block.items():
                    if not _id:
                        continue
                    reg[str(_id)] = spec or {}
            return reg

        def _load_registry_from_folder(folder: pathlib.Path, key: str) -> Dict[str, Dict[str, Any]]:
            """Load a registry by merging every *.yaml file in a modular registry folder.

            Auto-discovers files the same way the entity-class folders
            (assets/, views/, ...) do — no curated file list. The
            uniqueness constraint that actually mattered (a registry
            id must not be defined twice with conflicting specs) is
            still enforced here, on every file found; it never
            depended on an explicit import order in the first place,
            since a duplicate id was always a hard error rather than
            "last file wins".

            Previously this required a _index.yaml with an explicit
            'imports:' list. That was removed: it added a second file
            to keep in sync with reality for zero functional benefit
            (see CHANGELOG.md) — the exact kind of drift that left
            schemas/agentbased/assets/_index.yaml stale.
            """
            if not folder.is_dir():
                return {}
            reg: Dict[str, Dict[str, Any]] = {}
            for part_path in sorted(folder.glob("*.y*ml")):
                part = _load_registry(part_path, key)
                for _id, spec in part.items():
                    if _id in reg:
                        raise ValueError(f"Duplicate {key[:-1]} id '{_id}' across modular registry files")
                    reg[_id] = spec
            return reg

        def _merge_registry(into: Dict[str, Dict[str, Any]], part: Dict[str, Dict[str, Any]], kind: str, source: pathlib.Path):
            for _id, spec in part.items():
                if _id in into and into[_id] != spec:
                    raise ValueError(
                        f"Duplicate {kind} id '{_id}' with different definitions while loading {source}"
                    )
                into[_id] = spec

        for _schema_path in paths:
            if _schema_path.is_dir():
                # Legacy single-file registries
                attrs = _load_registry(_schema_path / "attributes.yaml", "attributes")
                rels  = _load_registry(_schema_path / "relations.yaml", "relations")
                units = _load_registry(_schema_path / "units.yaml", "units")

                # Modular registries: merge every *.yaml file found in
                # attributes/ and relations/ (auto-discovered, no
                # curated _index.yaml — see _load_registry_from_folder).
                if not attrs:
                    attrs = _load_registry_from_folder(_schema_path / "attributes", "attributes")
                if not rels:
                    rels = _load_registry_from_folder(_schema_path / "relations", "relations")
                if not units:
                    units = _load_registry_from_folder(_schema_path / "units", "units")

                _merge_registry(self.global_attributes, attrs, "attribute", _schema_path)
                _merge_registry(self.global_relations,  rels,  "relation",  _schema_path)
                _merge_registry(self.global_units,      units, "unit",      _schema_path)

        has_registries = bool(self.global_attributes or self.global_relations)

        # ----------------------------
        # Validate every attribute's unit(s) against the central unit
        # registry, if one was loaded. This is what actually prevents
        # future spelling drift (the 51->47 duplicate-spelling cleanup
        # in CHANGELOG.md) rather than just documenting the canonical
        # spellings after the fact: an attribute using an unregistered
        # unit string fails to load, immediately, instead of silently
        # introducing a new variant that only a manual audit would
        # eventually catch.
        # ----------------------------
        if self.global_units:
            unit_errors = []
            for _aid, _adef in self.global_attributes.items():
                _unit_block = (_adef or {}).get("unit") or {}
                _enum = (_unit_block.get("constraints") or {}).get("enum") or []
                for _u in _enum:
                    if _u not in self.global_units:
                        unit_errors.append(f"{_aid!r} uses unregistered unit {_u!r}")
            if unit_errors:
                raise ValueError(
                    "Unregistered unit(s) found (not present in the central "
                    "schemas/cesdm/units/units.yaml registry) -- add the unit to the "
                    "registry if it's genuinely new, or fix the spelling to "
                    "match an existing registered unit:\n- " + "\n- ".join(unit_errors)
                )

        # ----------------------------
        # Load entity/class documents
        # ----------------------------
        docs: List[Dict[str, Any]] = []

        for _schema_path in paths:
            if _schema_path.is_dir():
                candidates: List[pathlib.Path] = []

                # Prefer an "entities" subfolder if it exists (LinkML-like layout)
                entities_dir = _schema_path / "entities"
                if entities_dir.exists() and entities_dir.is_dir():
                    candidates.extend(sorted(entities_dir.rglob("*.y*ml")))

                # Also load any other yaml files in root (legacy layout), excluding registries
                for f in sorted(_schema_path.rglob("*.y*ml")):
                    if f.name in ("attributes.yaml", "relations.yaml"):
                        continue
                    if entities_dir.exists() and entities_dir in f.parents:
                        continue
                    candidates.append(f)

                # de-dup while keeping order within this schema path
                seen = set()
                ordered = []
                for f in candidates:
                    if f in seen:
                        continue
                    seen.add(f)
                    ordered.append(f)

                for f in ordered:
                    docs.extend(_load_one_yaml(f))
            else:
                docs.extend(_load_one_yaml(_schema_path))

        # ----------------------------
        # Phase 1: parse and collect refs
        # ----------------------------
        merged: Dict[str, Dict[str, Any]] = {}

        # keep reference usages so we can validate them *before* materializing
        # entries are tuples: (class_name, kind, id, usage_item)
        ref_uses: List[Tuple[str, str, str, Any]] = []

        # Schema augmentations are parsed separately from entity-class documents.
        # Entries are (target_class, kind, registry_id, usage_item, source_label).
        augmentation_uses: List[Tuple[str, str, str, Any, str]] = []

        def _merge_common(into: Dict[str, Any], src: Dict[str, Any]):
            for k in ("description", "parents", "abstract", "view_family"):
                if k in src:
                    into[k] = src[k]

        def _is_attr_ref_item(item: Any) -> bool:
            # reference/usage item: "id" + optional required/default/
            # belongsToGroup only. belongsToGroup marks which former
            # representation-view group this attribute belongs to, now
            # that its attributes/relations live directly on the asset.
            if isinstance(item, str):
                return True
            if isinstance(item, dict) and "id" in item:
                allowed = {"id", "required", "default", "belongsToGroup"}
                return set(item.keys()).issubset(allowed)
            return False

        def _is_rel_ref_item(item: Any) -> bool:
            if isinstance(item, str):
                return True
            if isinstance(item, dict) and "id" in item:
                allowed = {"id", "required", "belongsToGroup"}
                return set(item.keys()).issubset(allowed)
            return False

        def _merge_class(into: Dict[str, Any], src: Dict[str, Any], cname: str):
            _merge_common(into, src)

            # --- attributes ---
            into.setdefault("attributes", {})
            raw_attrs = src.get("attributes")
            if isinstance(raw_attrs, dict):
                # legacy mapping style
                into["attributes"].update(raw_attrs)
            elif isinstance(raw_attrs, list):
                for item in raw_attrs:
                    if _is_attr_ref_item(item):
                        aid = item if isinstance(item, str) else item.get("id")
                        if aid:
                            ref_uses.append((cname, "attribute", str(aid), item))
                    elif isinstance(item, dict):
                        # embedded full spec
                        aid = item.get("id")
                        if not aid:
                            continue
                        spec = {k: v for k, v in item.items() if k != "id"}
                        into["attributes"][str(aid)] = spec

            # --- relations ---
            into.setdefault("relations", {})
            raw_rels = src.get("relations")
            if isinstance(raw_rels, dict):
                into["relations"].update(raw_rels)
            elif isinstance(raw_rels, list):
                for item in raw_rels:
                    if _is_rel_ref_item(item):
                        rid = item if isinstance(item, str) else item.get("id")
                        if rid:
                            ref_uses.append((cname, "relation", str(rid), item))
                    elif isinstance(item, dict):
                        rid = item.get("id")
                        if not rid:
                            continue
                        spec = {k: v for k, v in item.items() if k != "id"}
                        into["relations"][str(rid)] = spec

        def _collect_augmentation_items(
            target: str,
            block: Dict[str, Any],
            source_label: str,
        ) -> None:
            if not isinstance(block, dict):
                raise ValueError(
                    f"Augmentation for '{target}' in {source_label} must be a mapping"
                )

            allowed_block_keys = {"attributes", "relations", "groups"}
            unknown_block_keys = set(block) - allowed_block_keys
            if unknown_block_keys:
                raise ValueError(
                    f"Augmentation for '{target}' in {source_label} contains unknown "
                    f"keys: {sorted(unknown_block_keys)}"
                )

            def collect_items(
                kind: str,
                key: str,
                checker,
                raw_items: Any,
                *,
                group_name: str | None = None,
            ) -> None:
                if raw_items is None:
                    return
                if isinstance(raw_items, str):
                    raw_items = [raw_items]
                if not isinstance(raw_items, list):
                    location = f"{target}.groups.{group_name}.{key}" if group_name else f"{target}.{key}"
                    raise ValueError(
                        f"Augmentation '{location}' in {source_label} must be a list"
                    )

                for original_item in raw_items:
                    if not checker(original_item):
                        location = f"{target}.groups.{group_name}.{key}" if group_name else f"{target}.{key}"
                        raise ValueError(
                            f"Augmentation '{location}' in {source_label} may only "
                            "reference globally registered ids with optional usage "
                            "overrides (required/default/belongsToGroup); inline field "
                            f"definitions are not allowed: {original_item!r}"
                        )

                    # A nested groups block is syntax sugar for the normal
                    # belongsToGroup usage override.  The registry definition
                    # itself remains global and untouched.
                    item = original_item
                    if group_name is not None:
                        if isinstance(original_item, str):
                            item = {"id": original_item, "belongsToGroup": group_name}
                        else:
                            item = dict(original_item)
                            explicit_group = item.get("belongsToGroup")
                            if explicit_group is not None:
                                values = (
                                    [explicit_group]
                                    if isinstance(explicit_group, str)
                                    else list(explicit_group or [])
                                )
                                if values != [group_name]:
                                    raise ValueError(
                                        f"Augmentation '{target}.groups.{group_name}.{key}' "
                                        f"in {source_label} must not assign a different "
                                        f"belongsToGroup value: {explicit_group!r}"
                                    )
                            item["belongsToGroup"] = group_name

                    field_id = item if isinstance(item, str) else item.get("id")
                    if field_id:
                        augmentation_uses.append(
                            (str(target), kind, str(field_id), item, source_label)
                        )

            for kind, key, checker in (
                ("attribute", "attributes", _is_attr_ref_item),
                ("relation", "relations", _is_rel_ref_item),
            ):
                collect_items(kind, key, checker, block.get(key) or [])

            groups = block.get("groups") or {}
            if not isinstance(groups, dict):
                raise ValueError(
                    f"Augmentation '{target}.groups' in {source_label} must be a mapping"
                )
            for group_name, group_block in groups.items():
                if not isinstance(group_name, str) or not group_name.strip():
                    raise ValueError(
                        f"Augmentation group name for '{target}' in {source_label} "
                        "must be a non-empty string"
                    )
                if not isinstance(group_block, dict):
                    raise ValueError(
                        f"Augmentation '{target}.groups.{group_name}' in {source_label} "
                        "must be a mapping"
                    )
                unknown_group_keys = set(group_block) - {"attributes", "relations"}
                if unknown_group_keys:
                    raise ValueError(
                        f"Augmentation '{target}.groups.{group_name}' in {source_label} "
                        f"contains unknown keys: {sorted(unknown_group_keys)}"
                    )
                collect_items(
                    "attribute",
                    "attributes",
                    _is_attr_ref_item,
                    group_block.get("attributes") or [],
                    group_name=group_name,
                )
                collect_items(
                    "relation",
                    "relations",
                    _is_rel_ref_item,
                    group_block.get("relations") or [],
                    group_name=group_name,
                )

        def _collect_augmentations(raw: Any, source_label: str) -> None:
            if raw is None:
                return
            if isinstance(raw, dict):
                for target, block in raw.items():
                    _collect_augmentation_items(str(target), block or {}, source_label)
                return
            if isinstance(raw, list):
                for index, entry in enumerate(raw):
                    if not isinstance(entry, dict):
                        raise ValueError(
                            f"Augmentation entry {index} in {source_label} must be a mapping"
                        )
                    target = entry.get("target") or entry.get("entity_class")
                    if not target:
                        raise ValueError(
                            f"Augmentation entry {index} in {source_label} has no target"
                        )
                    block = {
                        "attributes": entry.get("attributes") or [],
                        "relations": entry.get("relations") or [],
                        "groups": entry.get("groups") or {},
                    }
                    _collect_augmentation_items(str(target), block, source_label)
                return
            raise ValueError(
                f"'augmentations' in {source_label} must be a mapping or list"
            )

        for d in docs:
            if not d:
                continue
            if isinstance(d, dict) and "augmentations" in d:
                _collect_augmentations(d.get("augmentations"), "schema document")

            # Case 1: collection file
            if isinstance(d, dict) and isinstance(d.get("entity_classes"), dict):
                for cname, cdef in d["entity_classes"].items():
                    merged.setdefault(cname, {})
                    _merge_class(merged[cname], cdef or {}, cname)
            # Case 2: single-class file
            elif isinstance(d, dict) and "name" in d:
                cname = d["name"]
                merged.setdefault(cname, {})
                _merge_class(merged[cname], d, cname)
            else:
                continue

        # ----------------------------
        # Phase 2a: validate references
        # ----------------------------
        errors: List[str] = []

        def _suggest(name: str, pool: List[str]) -> str:
            matches = get_close_matches(name, pool, n=3, cutoff=0.72)
            if not matches:
                return ""
            return f" (did you mean: {', '.join(matches)})"

        # if entity uses reference-style mappings, registries must be present
        if ref_uses and not has_registries:
            errors.append(
                "Entity schemas contain attribute/relation references by id, but no registries "
                "were found (attributes.yaml / relations.yaml missing or empty)."
            )

        for cname, kind, _id, item in ref_uses:
            if kind == "attribute":
                if _id not in self.global_attributes:
                    errors.append(
                        f"[{cname}] Attribute '{_id}' is referenced but not defined in attributes.yaml"
                        + _suggest(_id, list(self.global_attributes.keys()))
                    )
            else:
                if _id not in self.global_relations:
                    errors.append(
                        f"[{cname}] Relation '{_id}' is referenced but not defined in relations.yaml"
                        + _suggest(_id, list(self.global_relations.keys()))
                    )

        # Validate augmentation targets and their registry references only after
        # all schema roots have been parsed, so an extension can target a class
        # supplied by an earlier/base schema path.
        known_class_names = set(merged)
        for target, kind, field_id, _item, source_label in augmentation_uses:
            if target not in known_class_names:
                errors.append(
                    f"[augmentation] Target class '{target}' does not exist"
                    + _suggest(target, list(known_class_names))
                )
                continue
            registry = (
                self.global_attributes if kind == "attribute"
                else self.global_relations
            )
            registry_label = "attributes" if kind == "attribute" else "relations"
            if field_id not in registry:
                errors.append(
                    f"[augmentation:{target}] {kind.title()} '{field_id}' is not "
                    f"defined in any loaded base or extension {registry_label} registry"
                    + _suggest(field_id, list(registry.keys()))
                )

        if errors:
            raise ValueError("Schema validation failed:\n- " + "\n- ".join(errors))

        # ----------------------------
        # Phase 2b: materialize references (base + overrides)
        # ----------------------------
        def _materialize_attribute(aid: str, item: Any) -> Dict[str, Any]:
            base = copy.deepcopy(self.global_attributes.get(aid, {}))
            if isinstance(item, dict):
                if "required" in item:
                    base["required"] = item["required"]
                if "default" in item:
                    base.setdefault("value", {})
                    if isinstance(base["value"], dict):
                        base["value"]["default"] = item["default"]
                if "belongsToGroup" in item:
                    base["belongsToGroup"] = item["belongsToGroup"]
            return base

        def _materialize_relation(rid: str, item: Any) -> Dict[str, Any]:
            base = copy.deepcopy(self.global_relations.get(rid, {}))
            if isinstance(item, dict):
                if "required" in item:
                    base["required"] = item["required"]
                if "belongsToGroup" in item:
                    base["belongsToGroup"] = item["belongsToGroup"]
            return base

        for cname, kind, _id, item in ref_uses:
            if kind == "attribute":
                merged[cname].setdefault("attributes", {})
                # don't overwrite an inline spec if present
                merged[cname]["attributes"].setdefault(_id, _materialize_attribute(_id, item))
            else:
                merged[cname].setdefault("relations", {})
                merged[cname]["relations"].setdefault(_id, _materialize_relation(_id, item))

        # ----------------------------
        # Apply schema augmentations
        # ----------------------------
        # Attributes and relations are defined in base or extension-local registries.
        # Loading composes them into one runtime registry without modifying any
        # source schema. The augmentation only attaches a registry field to an
        # existing class, with the same
        # limited usage overrides supported by normal entity schemas.
        augmentation_seen: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for target, kind, field_id, item, source_label in augmentation_uses:
            materialized = (
                _materialize_attribute(field_id, item)
                if kind == "attribute"
                else _materialize_relation(field_id, item)
            )
            key = (target, kind, field_id)
            previous = augmentation_seen.get(key)
            if previous is not None and previous != materialized:
                raise ValueError(
                    f"Conflicting augmentation usages for {target}.{field_id} "
                    f"({kind}) while loading {source_label}"
                )
            augmentation_seen[key] = materialized

            container_name = "attributes" if kind == "attribute" else "relations"
            container = merged[target].setdefault(container_name, {})
            if field_id in container:
                if container[field_id] != materialized:
                    raise ValueError(
                        f"Augmentation conflict: class '{target}' already declares "
                        f"{kind} '{field_id}' with a different usage definition"
                    )
                continue
            container[field_id] = materialized

        # ----------------------------
        # Build class objects
        # ----------------------------
        for cname, cdef in merged.items():
            ec = EntityClass.from_dict(cname, cdef)
            self.classes[cname] = ec
            if cname not in self.entities:
                self.entities[cname] = {}

        # Build inheritance from the materialized class definitions.  This is
        # more robust than re-reading one directory and also supports multiple
        # schema roots where a class can be extended by a later path.
        self.inheritance = {}
        for _cname, _cdef in self.classes.items():
            _parents = getattr(_cdef, "parents", None)
            if _parents is None:
                self.inheritance[_cname] = []
            elif isinstance(_parents, str):
                self.inheritance[_cname] = [_parents]
            else:
                self.inheritance[_cname] = list(_parents or [])
        self.resolve_inheritance()

    def build_inheritance_map(self, schema_dir: str | Path) -> Dict[str, List[str]]:
            """
            Build a *direct* inheritance map::

                { child_class_name: [parent_class_name, ...] }

            This helper understands the schema key ``parents`` (string or list).

            It supports both layouts:
            - legacy (entity yamls in root)
            - separated (entity yamls in ``entities/`` plus registries in root)
            """
            from pathlib import Path
            import yaml

            schema_dir = Path(schema_dir)
            inheritance: Dict[str, List[str]] = {}

            if not schema_dir.exists():
                return inheritance

            # find candidate entity yaml files
            files: List[Path] = []
            entities_dir = schema_dir / "entities"
            if entities_dir.exists() and entities_dir.is_dir():
                files.extend(sorted(entities_dir.rglob("*.y*ml")))
            # legacy root files (exclude registries)
            for f in sorted(schema_dir.glob("*.y*ml")):
                if f.name in ("attributes.yaml", "relations.yaml"):
                    continue
                files.append(f)

            for f in files:
                with f.open(encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}

                cls_name = data.get("class_name") or data.get("name") or f.stem

                raw = data.get("parents")
                if raw is None:
                    raw = data.get("inherits_from") or data.get("parent")

                if raw is None:
                    parents: List[str] = []
                elif isinstance(raw, list):
                    parents = [str(x) for x in raw if x is not None]
                else:
                    parents = [str(raw)]

                inheritance[cls_name] = parents

            return inheritance

    @property
    def class_defs(self):
        """
        Return a mapping of all class names to their :class:`EntityClass` definitions.

        Returns
        -------
        dict[str, EntityClass]
            Dictionary of class name → class definition.
        """
        return getattr(self, "classes", {})

    def unit_info(self, symbol: str):
        """
        Look up a unit's registry entry (symbol, quantity_kind, description)
        from schemas/cesdm/units/units.yaml, or None if the schema tree has no
        unit registry loaded, or the symbol isn't registered.

        Example
        -------
        >>> model.unit_info("MW")["quantity_kind"]
        'power'
        """
        return getattr(self, "global_units", {}).get(symbol)
