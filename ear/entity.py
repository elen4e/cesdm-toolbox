"""ear.entity

Runtime instance of a schema class.

Auto-extracted from the legacy monolithic ``ear_toolbox.py``.
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



@dataclass
class Entity:
    """
    Runtime instance of a CESDM class.

    Parameters
    ----------
    id :
        Globally unique identifier of the entity.
    class_name :
        Name of the class this entity belongs to.
    data :
        Mapping of attribute and relation names to stored values.
        The internal representation is a flat dictionary; access helpers
        in :class:`Model` know which fields are attributes vs. relations.
    """

    cls: str
    id: str
    data: Dict[str, Any]
    # Back-reference to the owning Model, set by add_entity() right after
    # construction -- lets Entity offer its own add_attribute()/
    # add_relation() as a thin, object-oriented convenience layer over the
    # exact same Model.add_attribute()/add_relation() validation and
    # storage logic, without duplicating any of it. Excluded from repr()
    # and equality: existing code across the codebase constructs and
    # compares Entity(cls=..., id=..., data=...) directly (the only other
    # construction site is add_entity() itself), so a plain, defaulted,
    # non-comparing field keeps all of that unchanged.
    _model: Optional[Any] = field(default=None, repr=False, compare=False)

    def get_attr_value(self, name: str, default=None):
        """Return the 'value' part of an attribute (handles AttributeValue and legacy scalars)."""
        raw = getattr(self, "data", {}).get(name, default)

        if isinstance(raw, dict) and "value" in raw:
            return raw["value"]

        return raw

    def get_relations(self, name: str) -> List[str]:
        """Return all targets of a relation as a list of entity ids.

        When the entity belongs to a model, this delegates to the model's
        canonical relation accessor. Directly constructed entities fall back
        to their flat ``data`` mapping.
        """
        if self._model is not None:
            return self._model.get_relation_targets(self.id, name)

        raw = self.data.get(name)
        if raw in (None, ""):
            return []
        if isinstance(raw, (list, tuple, set)):
            return [str(value) for value in raw if value not in (None, "")]
        return [str(raw)]

    def get_relation(self, name: str, default=None):
        """Return the first target of a relation, or ``default``."""
        targets = self.get_relations(name)
        return targets[0] if targets else default

    def add_attribute(self, attribute_id: str, value, *, unit: str | None = None,
                       provenance_ref: str | None = None):
        """Set or update an attribute on this entity -- an object-oriented
        convenience wrapper for ``model.add_attribute(entity.id, ...)``.
        Requires this Entity to have been created via ``Model.add_entity()``
        (which sets the back-reference this delegates through); an Entity
        constructed directly, without a model, cannot use this method.
        """
        if self._model is None:
            raise RuntimeError(
                f"Entity '{self.id}' has no owning model reference -- "
                "add_attribute() only works on entities created via "
                "Model.add_entity(). Use model.add_attribute(entity_id, ...) "
                "directly instead."
            )
        self._model.add_attribute(self.id, attribute_id, value, unit=unit,
                                   provenance_ref=provenance_ref)
        return self

    def add_relation(self, relation_id: str, target_entity_id, **kwargs):
        """Set or update a relation on this entity -- an object-oriented
        convenience wrapper for ``model.add_relation(entity.id, ...)``.
        Same model-reference requirement as add_attribute() above.
        """
        if self._model is None:
            raise RuntimeError(
                f"Entity '{self.id}' has no owning model reference -- "
                "add_relation() only works on entities created via "
                "Model.add_entity(). Use model.add_relation(entity_id, ...) "
                "directly instead."
            )
        self._model.add_relation(self.id, relation_id, target_entity_id, **kwargs)
        return self

