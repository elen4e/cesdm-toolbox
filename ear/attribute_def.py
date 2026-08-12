"""ear.attribute_def

Schema definition of a single attribute, plus the AttributeValue
wrapper dict and its YAML representer.

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


def _normalize_belongs_to_group(raw: Any) -> List[str]:
    """Normalize a belongsToGroup schema value to a list: a single
    string becomes a one-item list (convenience for the common case),
    a list is used as-is, anything falsy becomes an empty list."""
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


@dataclass
class AttributeDef:
    """
    Definition of a single attribute in a CESDM class.

    Parameters
    ----------
    name :
        Name of the attribute (e.g. ``conversion_efficiency``).
    type :
        Expected CESDM type (``string``, ``float``, ``integer``, ``boolean``, ...).
    required :
        Whether the attribute must be present on an entity.
    description :
        Human-readable description of the attribute.
    default :
        Optional default value used when creating new entities.
    constraints :
        Optional :class:`Constraint` object with enum/min/max/pattern rules.
    """

    name: str
    type: str
    required: bool = False
    description: str = ""
    default: Optional[Any] = None
    constraints: Constraint = field(default_factory=Constraint)

    unit: Optional[Any] = None  # default unit schema (string or nested dict from YAML)
    group: Optional[str] = None   # z.B. "master_data", "power_flow", "cost", "dynamics"
    order: Optional[int] = None   # Reihenfolge innerhalb der Gruppe
    belongsToGroup: List[str] = field(default_factory=list)  # which former
        # representation-view family/families (view_class values like
        # "dispatch", "power_flow", "topology" -- not full view class
        # names) this attribute's data was merged in from, now that it
        # lives directly on the asset instead of a separate view
        # entity. A field can legitimately belong to more than one
        # group (e.g. an attribute relevant to both dispatch and
        # powerflow contexts).

        # Optional: Validierung der Gruppe
        # if group is not None and group not in ATTRIBUTE_GROUPS:
        #     raise ValueError(f"Unknown attribute group '{group}' in attribute '{name}'")



    @staticmethod
    def from_dict(name: str, d: Dict[str, Any]) -> "AttributeDef":
        """
        Create an ``AttributeDef`` from a dictionary parsed from YAML.

        This supports both the legacy flat style::

            attributes:
              foo:
                type: float
                required: true
                constraints:
                  minimum: 0.0

        and the newer nested style::

            attributes:
              foo:
                description: Some value.
                value:
                  type: float
                  required: true
                  constraints:
                    minimum: 0.0
                unit:
                  type: string
                  constraints:
                    enum: [MWh]

        Parameters
        ----------
        name :
            Attribute name in the YAML.
        d :
            Mapping of attribute properties.

        Returns
        -------
        AttributeDef
            The constructed attribute definition.
        """
        # --- detect nested "value" style --------------------------------
        if "value" in d and isinstance(d.get("value"), dict):
            vdef = d.get("value") or {}
            cons_dict = vdef.get("constraints") or {}
            cons_dict = dict(cons_dict)

            # allow enum at value-level for convenience
            if "enum" in vdef and "enum" not in cons_dict:
                cons_dict["enum"] = vdef["enum"]

            group = d.get("group")
            order = d.get("order")

            # import pdb
            # pdb.set_trace()

            return AttributeDef(
                name=name,
                type=vdef.get("type", "string"),
                required=bool(d.get("required", False)),
                description=d.get("description", ""),
                default=vdef.get("default"),
                constraints=Constraint.from_dict(cons_dict),
                group=group,
                order=order,
                unit=d.get("unit"),  # may be string or nested dict
                belongsToGroup=_normalize_belongs_to_group(d.get("belongsToGroup")),
            )

        # # --- legacy flat style ------------------------------------------
        # cons_dict = d.get("constraints") or {}
        # cons_dict = dict(cons_dict)

        # if "enum" in d and "enum" not in cons_dict:
        #     cons_dict["enum"] = d["enum"]

        # group = d.get("group")
        # order = d.get("order")

        # return AttributeDef(
        #     name=name,
        #     type=d.get("type", "string"),
        #     required=bool(d.get("required", False)),
        #     description=d.get("description", ""),
        #     default=d.get("default"),
        #     constraints=Constraint.from_dict(cons_dict),
        #     group=group,
        #     order=order,
        #     unit=d.get("unit"),
        # )

class AttributeValueDict(dict):
    """Marker-Typ für AttributeValue-Objekte, die im YAML inline (flow style) ausgegeben werden sollen."""
    pass

def attributevalue_representer(dumper, data):
    # Schreibe als Mapping im Flow-Style: { key: value, ... }
    return dumper.represent_mapping(
        u"tag:yaml.org,2002:map",
        data,
        flow_style=True,
    )

yaml.add_representer(AttributeValueDict, attributevalue_representer)
# falls du SafeDumper verwendest:
yaml.add_representer(AttributeValueDict, attributevalue_representer, Dumper=yaml.SafeDumper)



