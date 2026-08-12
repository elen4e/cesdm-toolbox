"""ear.entity_class

Resolved schema class (entity type) definition.

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

from ear.constraint import Constraint
from ear.relation_def import RelationDef
from ear.attribute_def import AttributeDef

@dataclass
class EntityClass:
    """
    Schema-level description of a CESDM class.

    Parameters
    ----------
    name :
        Name of the class (e.g. ``Generator``, ``Load``).
    parents :
        Optional name(s) of the base class(es) this class inherits from.
    abstract :
        Whether this class is abstract (no instances should be created).
    description :
        Human-readable description of the class.
    attributes :
        Mapping of attribute name → :class:`AttributeDef`.
    relations :
        Mapping of relation name → :class:`RelationDef`.
    view_family :
        Optional free-text tag (e.g. "dispatch", "power_flow", "topology")
        used by cesdm.proxy.EntityProxy to resolve `.dispatch`/`.power_flow`/
        etc. to the right representation-view class for an asset. Not a
        core EAR concept -- purely descriptive metadata for that one
        consumer. Unlike `abstract`, this genuinely inherits from parent
        to child (resolved in resolve_inheritance()): a concrete dispatch
        view tagged only on its abstract family root still resolves to
        that root's view_family. A class's own declared value always
        wins over an inherited one.
    """

    name: str
    attributes: Dict[str, AttributeDef]
    description: str = ""
    parents: Union[None, str, List[str]] = None
    abstract: bool = False
    relations: Dict[str, RelationDef] = field(default_factory=dict)
    view_family: Optional[str] = None

    @staticmethod
    def from_dict(name: str, d: Dict[str, Any]) -> "EntityClass":
        """
        Build an :class:`EntityClass` from a dictionary parsed from a YAML schema.

        Supports both:

        attributes:
          foo:
            description: ...
            value: ...
            unit: ...

        and:

        attributes:
          - id: foo
            description: ...
            value: ...
            unit: ...
        """

        # --- attributes: support dict AND list-of-objects with "id" ---
        raw_attrs = d.get("attributes") or {}
        attrs: Dict[str, AttributeDef] = {}

        if isinstance(raw_attrs, list):
            # new style: list of {id: ..., ...}
            for item in raw_attrs:
                if not isinstance(item, dict):
                    continue
                attr_id = item.get("id")
                if not attr_id:
                    continue
                spec = {k: v for k, v in item.items() if k != "id"}
                attrs[attr_id] = AttributeDef.from_dict(attr_id, spec)
        elif isinstance(raw_attrs, dict):
            # old style: mapping attr_name -> spec
            for attr_id, spec in raw_attrs.items():
                attrs[attr_id] = AttributeDef.from_dict(attr_id, spec or {})

        # --- relations: support dict AND list-of-objects with "id" ---
        raw_refs = d.get("relations") or {}
        refs: Dict[str, RelationDef] = {}

        if isinstance(raw_refs, list):
            # new style: list of {id: ..., ...}
            for item in raw_refs:
                if not isinstance(item, dict):
                    continue
                ref_id = item.get("id")
                if not ref_id:
                    continue
                spec = {k: v for k, v in item.items() if k != "id"}
                refs[ref_id] = RelationDef.from_dict(ref_id, spec)
        elif isinstance(raw_refs, dict):
            # old style: mapping ref_name -> spec
            for ref_id, spec in raw_refs.items():
                refs[ref_id] = RelationDef.from_dict(ref_id, spec or {})

        return EntityClass(
            name=name,
            attributes=attrs,
            description=d.get("description", ""),
            parents=d.get("parents"),
            abstract=bool(d.get("abstract", False)),
            relations=refs,
            view_family=d.get("view_family"),
        )



