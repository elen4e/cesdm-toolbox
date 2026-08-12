"""cesdm.proxy — object-oriented ergonomics over the EAR engine.

Everything here is a thin wrapper over the existing low-level API
(add_entity/add_attribute/add_relation,
...) — the schema and the underlying EAR data model are completely
unchanged. This module exists so that most users never have to write
`add_relation(id, "reportsOn", ...)` or think about view class
strings directly.

Key design decision: :class:`EntityProxy` is a ``str`` subclass. It
*is* the entity id everywhere a plain string id is expected (dict
keys, `get_relation_targets(...)`, string formatting, `==` against a
plain string, ...), so every existing builder that starts returning an
`EntityProxy` instead of a bare `str` is a 100% backward-compatible
change — nothing that already worked with the plain-string return
value breaks, and new code additionally gets `.dispatch`, `.connect()`,
etc. for free on the same object.
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any, Optional


def _known_view_families(model: Any) -> set:
    """Every recognized group/family keyword -- used to power the "Did
    you mean: dispatch?" suggestion when a keyword doesn't match
    anything. Hardcoded rather than read from the schema: there are no
    more representation-view classes carrying a view_family attribute
    to introspect (see CHANGELOG.md)."""
    return {
        "dispatch", "topology", "power_flow", "spatial",
        "capacity_expansion", "technical", "dynamics",
    }


def _entity_proxy(model: Any, entity_id: str):
    """Return the schema-specific generated proxy for an entity id."""
    class_name = model.entity_class(str(entity_id))
    if not class_name:
        return EntityProxy(model, str(entity_id))
    try:
        from cesdm import generated_proxies
        proxy_name = "".join(
            part[:1].upper() + part[1:]
            for part in __import__("re").split(r"[^A-Za-z0-9]+", class_name)
            if part
        ) + "Proxy"
        proxy_class = getattr(generated_proxies, proxy_name, EntityProxy)
    except (ImportError, AttributeError):
        proxy_class = EntityProxy
    return proxy_class(model, str(entity_id))


def _relation_value(model: Any, targets: list[str]):
    proxies = [_entity_proxy(model, target) for target in targets]
    return proxies[0] if len(proxies) == 1 else proxies


def _canonical_relation_name(model: Any, name: str) -> str:
    """Remap legacy relation ids (e.g. ``locatedIn`` → ``belongsToGeographicalRegion``)."""
    aliases = getattr(model, "_RELATION_ID_ALIASES", None) or {}
    return aliases.get(name, name)


class ViewProxy:
    """Wraps a single representation-view entity. Attribute access reads
    and writes the view's attributes directly, validated against the
    view's own class definition -- an unknown attribute name raises
    immediately with a suggestion, rather than silently doing nothing.
    """

    __slots__ = ("_model", "_view_id", "_view_class")

    def __init__(self, model: Any, view_id: str, view_class: str):
        object.__setattr__(self, "_model", model)
        object.__setattr__(self, "_view_id", view_id)
        object.__setattr__(self, "_view_class", view_class)

    @property
    def id(self) -> str:
        return self._view_id

    @property
    def view_class(self) -> str:
        return self._view_class

    def _known_fields(self) -> set:
        attrs = self._model.class_attributes(self._view_class) or []
        rels = self._model.class_relations(self._view_class) or []
        return set(attrs) | set(rels)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        model = self._model
        rels = model.class_relations(self._view_class) or {}
        if name in rels:
            targets = model.get_relation_targets(self._view_id, name)
            return _relation_value(model, targets)
        attrs = model.class_attributes(self._view_class) or {}
        if name in attrs:
            # Cascades to the represented asset's technology template
            # (GeneratorType/StorageType/...) when not explicitly set on
            # this view instance -- see
            # Model.get_effective_attribute_value's docstring.
            return model.get_effective_attribute_value(self._view_id, name)
        self._raise_unknown_field(name)

    def __setattr__(self, name: str, value: Any) -> None:
        model = self._model
        rels = model.class_relations(self._view_class) or {}
        if name in rels:
            model.add_relation_if_allowed(self._view_id, name, value, strict=True)
            return
        attrs = model.class_attributes(self._view_class) or {}
        if name in attrs:
            unit = None
            if isinstance(value, tuple) and len(value) == 2:
                value, unit = value
            else:
                # Auto-attach the unit when the attribute has exactly one
                # registered valid unit -- ambiguous (0 or 2+ valid units)
                # attributes are left without a unit rather than guessing.
                adef = model.global_attributes.get(name) or {}
                enum = ((adef.get("unit") or {}).get("constraints") or {}).get("enum") or []
                if len(enum) == 1:
                    unit = enum[0]
            model.set_attribute_if_allowed(self._view_id, name, value, unit=unit, strict=True)
            return
        self._raise_unknown_field(name)

    def _raise_unknown_field(self, name: str):
        known = sorted(self._known_fields())
        suggestion = get_close_matches(name, known, n=3)
        hint = f" Did you mean: {', '.join(suggestion)}?" if suggestion else ""
        raise AttributeError(
            f"{name!r} is not an attribute or relation of {self._view_class!r}.{hint}"
        )

    def __repr__(self) -> str:
        return f"<ViewProxy {self._view_class} id={self._view_id!r}>"


class FlatGroupViewProxy:
    """Namespace-alias view over an asset's *own* flattened attributes/
    relations, filtered to whichever ones are tagged
    ``belongsToGroup: <group_name>`` in the schema.

    Exists so `gen.dispatch.nominal_power_capacity` keeps working
    exactly as before -- same read/write semantics as `ViewProxy` --
    now that "the dispatch view" isn't a separate entity any more:
    both `gen.nominal_power_capacity = 400` (flat) and
    `gen.dispatch.nominal_power_capacity = 400` (namespace alias) read
    and write the *same* underlying storage (the asset's own data),
    rather than the alias silently pointing at an independent,
    never-populated separate view entity. See CHANGELOG.md for the
    representation-view-flattening this supports.
    """

    __slots__ = ("_model", "_asset_id", "_asset_class", "_group_name")

    def __init__(self, model: Any, asset_id: str, asset_class: str, group_name: str):
        object.__setattr__(self, "_model", model)
        object.__setattr__(self, "_asset_id", asset_id)
        object.__setattr__(self, "_asset_class", asset_class)
        object.__setattr__(self, "_group_name", group_name)

    @property
    def id(self) -> str:
        return self._asset_id

    @property
    def view_class(self) -> str:
        return self._group_name

    def _group_fields(self) -> tuple[set, set]:
        model = self._model
        attr_defs = model.classes[self._asset_class].attributes if self._asset_class in model.classes else {}
        rel_defs = model.classes[self._asset_class].relations if self._asset_class in model.classes else {}
        attrs = {n for n, d in (attr_defs or {}).items() if self._group_name in (getattr(d, "belongsToGroup", None) or [])}
        rels = {n for n, d in (rel_defs or {}).items() if self._group_name in (getattr(d, "belongsToGroup", None) or [])}
        return attrs, rels

    def _known_fields(self) -> set:
        attrs, rels = self._group_fields()
        return attrs | rels

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        attrs, rels = self._group_fields()
        model = self._model
        rel_name = _canonical_relation_name(model, name)
        if rel_name in rels:
            targets = model.get_relation_targets(self._asset_id, rel_name)
            return _relation_value(model, targets)
        if name in attrs:
            return model.get_effective_attribute_value(self._asset_id, name)
        self._raise_unknown_field(name)

    def __setattr__(self, name: str, value: Any) -> None:
        attrs, rels = self._group_fields()
        model = self._model
        rel_name = _canonical_relation_name(model, name)
        if rel_name in rels:
            model.add_relation_if_allowed(self._asset_id, rel_name, value, strict=True)
            return
        if name in attrs:
            unit = None
            if isinstance(value, tuple) and len(value) == 2:
                value, unit = value
            else:
                adef = model.global_attributes.get(name) or {}
                enum = ((adef.get("unit") or {}).get("constraints") or {}).get("enum") or []
                if len(enum) == 1:
                    unit = enum[0]
            model.set_attribute_if_allowed(self._asset_id, name, value, unit=unit, strict=True)
            return
        self._raise_unknown_field(name)

    def _raise_unknown_field(self, name: str):
        known = sorted(self._known_fields())
        suggestion = get_close_matches(name, known, n=3)
        hint = f" Did you mean: {', '.join(suggestion)}?" if suggestion else ""
        raise AttributeError(
            f"{name!r} is not an attribute or relation of group {self._group_name!r}.{hint}"
        )

    def __repr__(self) -> str:
        return f"<FlatGroupViewProxy {self._group_name} asset={self._asset_id!r}>"


from ear.entity_proxy import EntityProxy as _EarEntityProxy


class EntityProxy(_EarEntityProxy):
    """A str subclass wrapping *any* entity id -- not only asset-role
    classes, e.g. `model.get_entity("Electricity")` for an
    `Carrier` works the same way. Extends `ear.entity_proxy.
    EntityProxy` (`.id`, `.entity_class`, direct attribute/relation
    assignment, `.add_attribute()`/`.add_relation()` -- all fully
    generic, inherited unchanged) with CESDM-specific behaviour:

    - `.dispatch`, `.power_flow`, etc. as lazily-created group-view
      objects (`FlatGroupViewProxy`) for whatever `belongsToGroup`
      values the entity's own class declares -- see
      docs/architecture/proxy_api.md.
    - `.connect(...)` for wiring topology relations.
    - Reading a relation returns the target wrapped in its own typed
      proxy (e.g. `bus.belongsToGeographicalRegion` returns a
      `GeographicalRegionProxy`, not a plain string; legacy
      `bus.locatedIn` still works via alias) -- ear.entity_proxy.
      EntityProxy's generic `__getattr__` returns plain target ids
      instead, since a non-CESDM EAR domain may have no per-class
      proxy registry to wrap with at all.
    - Reading a `belongsToGroup`-tagged attribute resolves the
      technology-template/lazy-default cascade
      (`get_effective_attribute_value()`), not just the entity's own
      literal value.
    """

    def _known_names(self) -> set:
        model = self._model
        cname = self.entity_class
        names = _known_view_families(model) | super()._known_names() if cname else _known_view_families(model)
        # Surface legacy relation aliases in typo suggestions.
        aliases = getattr(model, "_RELATION_ID_ALIASES", None) or {}
        for legacy, canon in aliases.items():
            if canon in names:
                names.add(legacy)
        return names

    def __setattr__(self, name: str, value: Any) -> None:
        # Remap legacy relation ids before the EAR base membership check
        # (``name in class_relations``), so ``bus.locatedIn = region`` still
        # works after the schema rename to belongsToGeographicalRegion.
        if name != "_model":
            name = _canonical_relation_name(self._model, name)
        return super().__setattr__(name, value)

    def __getattr__(self, name: str) -> Any:
        # Only reached for names not already resolved as a real attribute/
        # method/str-builtin -- i.e. genuinely unknown names. Try resolving
        # as a group first (schema-driven, see _view()); it returns
        # None rather than raising if nothing matches, so an unrelated
        # unknown name still falls through to the checks below instead of
        # being swallowed by a group-specific error message.
        view = self._view(name)
        if view is not None:
            return view
        # Fall back to the asset's own direct attributes/relations (most
        # asset classes only carry identity fields like name/description
        # here -- CESDM's asset/view separation keeps operational data in
        # views by design).
        model = self._model
        cname = self.entity_class
        if cname:
            attrs = model.class_attributes(cname) or {}
            if name in attrs:
                cdef = model.classes.get(cname)
                adef = cdef.attributes.get(name) if cdef else None
                if adef is not None and getattr(adef, "belongsToGroup", None):
                    return model.get_effective_attribute_value(str(self), name)
                return model.get_attribute_value(str(self), name)
            rels = model.class_relations(cname) or {}
            rel_name = _canonical_relation_name(model, name)
            if rel_name in rels:
                targets = model.get_relation_targets(str(self), rel_name)
                return _relation_value(model, targets)
        known = sorted(self._known_names())
        suggestion = get_close_matches(name, known, n=3)
        hint = f" Did you mean: {', '.join(suggestion)}?" if suggestion else ""
        raise AttributeError(f"{name!r} is not a view, attribute, or relation of {cname!r}.{hint}")

    _KNOWN_GROUPS = {
        "dispatch", "topology", "power_flow", "spatial",
        "capacity_expansion", "technical", "dynamics",
    }

    def _view(self, keyword: str) -> Optional["ViewProxy"]:
        """Resolve `keyword` (e.g. "dispatch") against the asset's own
        belongsToGroup-tagged attributes/relations -- there are no more
        separate representation-view entities for any group at all
        (see CHANGELOG.md: this toolbox's "initial version without
        views"), so this only ever aliases onto the asset's own
        flattened data. Returns None when `keyword` isn't recognized at
        all, so callers fall through to checking attributes/relations
        instead (see __getattr__). Raises AttributeError directly --
        rather than returning None -- when `keyword` *is* a real group
        but this asset's class genuinely doesn't support it.
        """
        model = self._model
        asset_id = str(self)
        cname = self.entity_class

        if cname is not None:
            attr_defs = getattr(model.classes.get(cname), "attributes", {}) or {}
            rel_defs = getattr(model.classes.get(cname), "relations", {}) or {}
            groups_present: set = set()
            for d in attr_defs.values():
                groups_present.update(getattr(d, "belongsToGroup", None) or [])
            for d in rel_defs.values():
                groups_present.update(getattr(d, "belongsToGroup", None) or [])
            if keyword in groups_present:
                return FlatGroupViewProxy(model, asset_id, cname, keyword)

        if keyword in self._KNOWN_GROUPS:
            raise AttributeError(
                f"{keyword!r} is a real group, but asset class {cname!r} "
                f"doesn't support it."
            )
        return None

    def connect(self, *nodes: str):
        """gen.connect(bus) -> single-port connection (reportsOn-style
        topology, via connect_single_port). line.connect(bus1, bus2) ->
        two-port connection (fromNode/toNode, via connect_two_port)."""
        model = self._model
        asset_id = str(self)
        if len(nodes) == 1:
            model.connect_single_port(asset_id, str(nodes[0]))
        elif len(nodes) == 2:
            model.connect_two_port(asset_id, str(nodes[0]), str(nodes[1]))
        else:
            raise TypeError(f"connect() takes 1 or 2 node arguments, got {len(nodes)}")
        return self

    def __repr__(self) -> str:
        return f"<EntityProxy {self.entity_class} id={str(self)!r}>"
