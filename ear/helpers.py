"""ear.helpers

Free-function helpers: model construction and safe
attribute/relation setters that tolerate missing/None values.

Auto-extracted from the legacy monolithic ``ear_toolbox.py``.
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

from ear.entity import Entity
from ear.model.core import Model

def build_model_from_yaml(schema_path: Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]) -> Model:
    m = Model()
    m.load_classes_from_yaml(schema_path)
    return m


# ---------------------------------------------------------------------------
# Helpers: entity lookup
# ---------------------------------------------------------------------------

def get_entities(model: Model, entity_class: str) -> Dict[str, Entity]:
    """Return the ``{entity_id: Entity}`` mapping for ``entity_class``.

    Thin wrapper around :meth:`Model.get_entities`. If ``entity_class`` is
    not defined in the model's schema, emit a :class:`UserWarning` and
    return an empty dict.
    """
    return model.get_entities(entity_class)


# ---------------------------------------------------------------------------
# Helpers: safe attribute/relation setting
# ---------------------------------------------------------------------------

def safe_set_attr(model: Model, entity_id: str, attr: str, value):
    """Set attribute only if value is not None."""
    if value is None:
        return
    model.add_attribute(entity_id, attr, value)


def safe_add_ref(model: Model, entity_id: str, ref_name: str, target_id: Optional[str]):
    """Add relation only if target_id is not empty."""
    if not target_id:
        return
    model.add_relation(entity_id, ref_name, target_id)


def get_attr_value(entity, name, default=None):
    """Return the 'value' part of an attribute (handles AttributeValue and legacy scalars)."""
    raw = getattr(entity, "data", {}).get(name, default)

    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]

    if isinstance(entity, dict) and name in entity:
        return entity[name]
    return raw

def get_attr_value_unit_prov(entity, name, default=None):
    """Return (value, unit, provenance_ref) for an attribute."""
    raw = getattr(entity, "data", {}).get(name, default)
    if isinstance(raw, dict) and "value" in raw:
        return raw.get("value"), raw.get("unit"), raw.get("provenance_ref")
    if isinstance(entity, dict) and name in entity:
        return entity[name], None, None
    # legacy scalar case
    return raw, None, None

def slugify(s: str) -> str:
    import re
    s = s.lower()
    # s = re.sub(r'[a-z0-9.-/]+', '_', s)
    # return s.strip('-')
    s = re.sub(r"[ \-]+", "_", s)
    s = re.sub(r"[ \(\)]+", "", s)
    return s
