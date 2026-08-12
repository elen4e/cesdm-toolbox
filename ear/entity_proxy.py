"""ear.entity_proxy — a generic str-subclass entity wrapper

`EntityProxy` wraps *any* entity id in a `str` subclass that behaves as
the plain id string everywhere (dict keys, equality, formatting,
passing to any existing low-level `Model.*` method), while additionally
exposing direct attribute/relation assignment (`entity.name = "X"`)
and explicit `.add_attribute()`/`.add_relation()` methods -- the same
object-oriented convenience `ear.entity.Entity.add_attribute()`/
`.add_relation()` already offer on the object `Model.add_entity()`
itself returns, available here too since this class wraps an
*existing* id instead.

This needs nothing beyond core EAR concepts (`entity_class()`,
`class_attributes()`, `class_relations()`, `set_attribute_if_allowed()`,
`add_relation_if_allowed()` -- see `ear/model/accessors.py`), so any
EAR-based domain gets this convenience layer for free, not only CESDM.
`cesdm.proxy.EntityProxy` extends this with CESDM-specific behaviour
(`.dispatch`/`.power_flow`/etc. group resolution, `.connect(...)`) --
see docs/architecture/proxy_api.md.
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any, Optional


class EntityProxy(str):
    """A str subclass wrapping *any* entity id."""

    _model: Any

    def __new__(cls, model: Any, entity_id: str):
        obj = str.__new__(cls, entity_id)
        object.__setattr__(obj, "_model", model)
        return obj

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_model":
            object.__setattr__(self, name, value)
            return
        model = self._model
        cname = self.entity_class
        entity_id = str(self)
        rels = (model.class_relations(cname) or []) if cname else []
        if name in rels:
            model.add_relation_if_allowed(entity_id, name, value, strict=True)
            return
        attrs = (model.class_attributes(cname) or []) if cname else []
        if name in attrs:
            unit = None
            if isinstance(value, tuple) and len(value) == 2:
                value, unit = value
            else:
                # Auto-attach the unit only when the attribute has exactly
                # one valid unit -- guessing among several would be worse
                # than asking; set (value, unit) explicitly for those.
                adef = model.global_attributes.get(name) or {}
                enum = ((adef.get("unit") or {}).get("constraints") or {}).get("enum") or []
                if len(enum) == 1:
                    unit = enum[0]
            model.set_attribute_if_allowed(entity_id, name, value, unit=unit, strict=True)
            return
        # Deliberately raise rather than silently falling through to a
        # normal Python instance-attribute assignment -- EntityProxy
        # being a str subclass means that would otherwise "work" with
        # no error (stored in the instance's own __dict__) while never
        # touching the actual model data at all: `bus.name = "X"`
        # would read back as "X" from the very same object, but
        # `model.get_attribute_value(bus, "name")` would still be
        # None, and the value would silently vanish from any export.
        known = sorted(set(attrs) | set(rels))
        suggestion = get_close_matches(name, known, n=3)
        hint = f" Did you mean: {', '.join(suggestion)}?" if suggestion else ""
        raise AttributeError(
            f"{name!r} is not an attribute or relation of {cname!r}.{hint}"
        )

    @property
    def id(self) -> str:
        return str(self)

    @property
    def entity_class(self) -> Optional[str]:
        return self._model.entity_class(str(self))

    def _known_names(self) -> set:
        """Every attribute/relation name valid for this entity's class --
        the base for typo suggestions. Subclasses (e.g. CESDM's, which
        also resolves group keywords like "dispatch") extend this with
        their own additional known names."""
        model = self._model
        cname = self.entity_class
        if not cname:
            return set()
        return set(model.class_attributes(cname) or {}) | set(model.class_relations(cname) or {})

    def __getattr__(self, name: str) -> Any:
        # Only reached for names not already resolved as a real attribute/
        # method/str-builtin -- i.e. genuinely unknown names.
        model = self._model
        cname = self.entity_class
        if cname:
            attrs = model.class_attributes(cname) or {}
            if name in attrs:
                return model.get_attribute_value(str(self), name)
            rels = model.class_relations(cname) or {}
            if name in rels:
                targets = model.get_relation_targets(str(self), name)
                if not targets:
                    return None
                return targets if len(targets) > 1 else targets[0]
        known = sorted(self._known_names())
        suggestion = get_close_matches(name, known, n=3)
        hint = f" Did you mean: {', '.join(suggestion)}?" if suggestion else ""
        raise AttributeError(f"{name!r} is not an attribute or relation of {cname!r}.{hint}")

    def get_attr_value(self, name: str, default: Any = None) -> Any:
        """Return a scalar attribute value through the owning model."""
        return self._model.get_attribute_value(str(self), name, default)

    def get_relations(self, name: str) -> list[str]:
        """Return all targets of a relation as entity ids."""
        return self._model.get_relation_targets(str(self), name)

    def get_relation(self, name: str, default: Any = None) -> Any:
        """Return the first target of a relation, or ``default``."""
        targets = self.get_relations(name)
        return targets[0] if targets else default

    def add_attribute(self, attribute_id: str, value: Any, *, unit: str | None = None,
                       provenance_ref: str | None = None) -> "EntityProxy":
        """Set or update an attribute on this entity -- an explicit,
        method-call alternative to direct assignment (`entity.name = "X"`),
        matching `ear.entity.Entity.add_attribute()`'s own object-oriented
        convenience layer over the identical `model.add_attribute()` call.
        Returns self for chaining."""
        self._model.add_attribute(str(self), attribute_id, value, unit=unit,
                                   provenance_ref=provenance_ref)
        return self

    def add_relation(self, relation_id: str, target_entity_id: Any, **kwargs: Any) -> "EntityProxy":
        """Set or update a relation on this entity -- an explicit,
        method-call alternative to direct assignment
        (`entity.belongsToGeographicalRegion = region`), matching
        `ear.entity.Entity.add_relation()`'s own object-oriented
        convenience layer over the identical `model.add_relation()` call.
        Returns self for chaining."""
        self._model.add_relation(str(self), relation_id, target_entity_id, **kwargs)
        return self

    def __repr__(self) -> str:
        return f"<EntityProxy {self.entity_class} id={str(self)!r}>"
