"""ear.model.accessors — Generic read/write convenience accessors

Small, schema-safe getters/setters that only need core EAR concepts
(entity classes, inherited attributes/relations, schema validation) --
no domain-specific knowledge at all, so any EAR-based domain (CESDM or
otherwise) gets them for free.

Moved here from cesdm/domain/model/accessors.py after checking each
method's actual implementation rather than assuming its file location
reflected its true generality: none of these ten reference anything
CESDM-specific (belongsToGroup groups, reportsOn-style views,
technology-template cascades, ...) -- they were simply misplaced.
`add_relation_if_allowed()`'s one CESDM-aware line
(`ensure_default_library_entity`) was already written as an optional,
gracefully-degrading hook (`getattr(self, ..., None)`), so it needed no
change to move here. See CHANGELOG.md.
"""

from __future__ import annotations

import warnings
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ear.entity import Entity


class AccessorsMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def get_entities(self, entity_class: str) -> Dict[str, "Entity"]:
        """Return the ``{entity_id: Entity}`` mapping for ``entity_class``.

        If ``entity_class`` is not defined in the model's schema, emit a
        :class:`UserWarning` and return an empty dict. A known class with no
        instances also returns an empty dict (without a warning).
        """
        try:
            cname = self._canonicalize_class(entity_class)
        except ValueError:
            suggestions = get_close_matches(
                str(entity_class), list(self.classes), n=3, cutoff=0.6
            )
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            warnings.warn(
                f"get_entities(): unknown entity class {entity_class!r}.{hint}",
                stacklevel=2,
            )
            return {}
        return self.entities.get(cname, {})

    def entity_class(self, entity_id: str) -> Optional[str]:
        """Return the class name for an entity id, or ``None``."""
        for cname, ents in (self.entities or {}).items():
            if entity_id in (ents or {}):
                return cname
        return None

    def entity_data(self, entity_id: str) -> Dict[str, Any]:
        """Return the mutable data dictionary for an entity."""
        ent, _ = self._get_entity_and_class(entity_id)
        return getattr(ent, "data", {}) or {}

    def has_entity(self, entity_id: str) -> bool:
        """Return True if an entity id exists in any class."""
        return self.entity_class(entity_id) is not None

    def class_attributes(self, class_name: str) -> List[str]:
        """Return inherited attribute ids for a class."""
        cname = self._canonicalize_class(class_name)
        attrs, _ = self._collect_inherited_fields(self.classes[cname])
        return list(attrs.keys())

    def class_relations(self, class_name: str) -> List[str]:
        """Return inherited relation ids for a class."""
        cname = self._canonicalize_class(class_name)
        _, rels = self._collect_inherited_fields(self.classes[cname])
        return list(rels.keys())

    def field_allowed(self, entity_or_class: str, field_id: str) -> bool:
        """Return True if an attribute or relation is valid for the entity/class."""
        cname = self.entity_class(entity_or_class) or self._canonicalize_class(entity_or_class)
        if cname not in self.classes:
            return False
        attrs, rels = self._collect_inherited_fields(self.classes[cname])
        return field_id in attrs or field_id in rels

    def get_attribute_value(self, entity_id: str, attribute_id: str, default: Any = None) -> Any:
        """Return a scalar attribute value, unwrapping AttributeValue dicts."""
        val = self.entity_data(entity_id).get(attribute_id, default)
        if isinstance(val, dict) and "value" in val:
            return val.get("value", default)
        return val

    def get_relation_targets(self, entity_id: str, relation_id: str) -> List[str]:
        """Return relation targets as a list."""
        val = self.entity_data(entity_id).get(relation_id)
        if val in (None, ""):
            return []
        if isinstance(val, (list, tuple, set)):
            return [str(v) for v in val if v not in (None, "")]
        return [str(val)]

    def set_attribute_if_allowed(self, entity_id: str, attribute_id: str, value: Any,
                                 unit: str | None = None, *, strict: bool = False):
        """Set an attribute if it exists on the entity's class.

        Returns True when the value was set and False when skipped.  With
        ``strict=True`` an unknown field raises KeyError.
        """
        if value is None:
            return False
        cname = self.entity_class(entity_id)
        if not cname or attribute_id not in self.class_attributes(cname):
            if strict:
                raise KeyError(f"{attribute_id!r} is not an attribute of {entity_id!r}")
            return False
        self.add_attribute(entity_id, attribute_id, value, unit=unit)
        return True

    def add_relation_if_allowed(self, entity_id: str, relation_id: str, target_id: str,
                                *, strict: bool = False):
        """Add a relation if it exists on the entity's class and target exists."""
        if target_id is None:
            return False
        cname = self.entity_class(entity_id)
        if not cname or relation_id not in self.class_relations(cname):
            if strict:
                raise KeyError(f"{relation_id!r} is not a relation of {entity_id!r}")
            return False
        if not self.has_entity(target_id):
            # Predefined default-library ids are materialized on demand --
            # a CESDM-specific extension, hooked in optionally so this
            # method itself stays domain-agnostic.
            ensure_default = getattr(self, "ensure_default_library_entity", None)
            if ensure_default is not None:
                ensure_default(str(target_id))
        if not self.has_entity(target_id):
            if strict:
                raise KeyError(f"Target entity {target_id!r} does not exist")
            return False
        self.add_relation(entity_id, relation_id, target_id)
        return True
