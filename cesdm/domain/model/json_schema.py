"""cesdm.domain.model.json_schema — JSON Schema export

Exports the loaded CESDM schema classes as a JSON Schema document.

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

from ear.constraint import Constraint
from ear.relation_def import RelationDef
from ear.attribute_def import AttributeDef


class JsonSchemaMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def export_json_schema(self, path: Union[str, pathlib.Path]):
            """
            Export a JSON Schema describing the structure produced by :meth:`export_json`.

            Parameters
            ----------
            path :
                Output file path for the JSON Schema document.

            Notes
            -----
            The schema is derived from the loaded class definitions, including types,
            required flags and simple constraints.

            It assumes that export_json() produces, per entity:

                {
                  "attributes": {
                    "<attr_name>": {
                      "value": <typed value>,
                      "unit": "<unit or '-'>",
                      "provenance_ref": "<source-id>"
                    },
                    ...
                  },
                  "relations": { ... }
                }
            """
            import json as _json
            import pathlib as _pl

            schema_path = _pl.Path(path)

            class_map = getattr(self, "classes", {}) or {}

            # --- helpers -----------------------------------------------------

            def _jsonschema_type_for_attribute(t: Optional[str]) -> str:
                """Map CESDM/YAML attribute type string to JSON Schema type."""
                if not t:
                    return "string"
                t = str(t).lower()
                if t in ("float", "number", "double", "decimal"):
                    return "number"
                if t in ("integer", "int", "long"):
                    return "integer"
                if t in ("bool", "boolean"):
                    return "boolean"
                # default: string (including datetime, etc. for now)
                return "string"

            def _jsonschema_constraints_for_attribute(ad: AttributeDef) -> Dict[str, Any]:
                """Build JSON Schema constraint keywords from AttributeDef."""
                cons: Dict[str, Any] = {}
                c = ad.constraints or Constraint()
                if c.enum is not None:
                    cons["enum"] = c.enum
                if c.minimum is not None:
                    cons["minimum"] = c.minimum
                if c.maximum is not None:
                    cons["maximum"] = c.maximum
                if c.pattern is not None:
                    cons["pattern"] = c.pattern
                return cons

            def _jsonschema_schema_for_relation(rd: RelationDef) -> (Dict[str, Any], bool):
                """
                Build JSON Schema for a relation value based on cardinality,
                and return (field_schema, is_required).
                """
                card = (rd.cardinality or "1").strip()

                # parse cardinality like "0..1", "1..*", "2..5", "1", "0", "*"
                lower = None
                upper = None
                if ".." in card:
                    lo, hi = card.split("..", 1)
                    lower = int(lo) if lo.isdigit() else 0
                    if hi in ("*", "n"):
                        upper = None
                    else:
                        upper = int(hi) if hi.isdigit() else None
                else:
                    if card in ("*", "n"):
                        lower, upper = 0, None
                    elif card.isdigit():
                        n = int(card)
                        lower, upper = n, n

                # build JSON Schema for the relation value
                if rd.targets:
                    if len(rd.targets) == 1:
                        desc_target = f"'{rd.targets[0]}'"
                    else:
                        desc_target = ", ".join(f"'{t}'" for t in rd.targets)
                        desc_target = f"one of {desc_target}"
                else:
                    desc_target = "any class (no target constraint)"

                base = {
                    "type": "string",
                    "description": f"ID of target class {desc_target}."
                }
                is_required = False

                if lower is None:
                    lower = 0

                if upper is None:
                    # unbounded upper → array of strings
                    field_schema: Dict[str, Any] = {
                        "type": "array",
                        "items": base,
                    }
                    if lower > 0:
                        field_schema["minItems"] = lower
                        is_required = True
                else:
                    if lower == upper == 1:
                        field_schema = base
                        if lower > 0:
                            is_required = True
                    else:
                        field_schema = {
                            "type": "array",
                            "items": base,
                        }
                        field_schema["minItems"] = lower
                        field_schema["maxItems"] = upper
                        if lower > 0:
                            is_required = True

                desc = f"Relation to '{rd.target}' (cardinality {rd.cardinality})."
                field_schema["description"] = desc

                return field_schema, is_required

            # --- build the full JSON Schema ---------------------------------

            schema: Dict[str, Any] = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "CESDM export_json()",
                "description": (
                    "JSON Schema for the export_json() representation of this CESDM model. "
                    "Top-level keys are class names; second-level keys are entity ids."
                ),
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

            for cname, cdef in class_map.items():
                # collect attributes + relations including inheritance
                attrs_def, refs_def = self._collect_inherited_fields(cdef)

                # ---- attributes schema for this class ----
                attr_props: Dict[str, Any] = {}
                attr_required: list[str] = []

                for an, ad in attrs_def.items():
                    # "value" sub-field schema
                    f_type = _jsonschema_type_for_attribute(ad.type)
                    value_field: Dict[str, Any] = {
                        "type": f_type,
                        "description": ad.description
                        or f"Value of attribute '{an}' of class '{cname}'.",
                    }

                    cons = _jsonschema_constraints_for_attribute(ad)
                    value_field.update(cons)

                    if ad.default is not None:
                        value_field["default"] = ad.default

                    # inner object: { value, unit, provenance_ref }
                    inner_props: Dict[str, Any] = {
                        "value": value_field,
                    }

                    # unit sub-schema derived from ad.unit (string or nested dict)
                    unit_schema: Dict[str, Any] = {
                        "type": "string",
                        "description": f"Unit for attribute '{an}' of class '{cname}'.",
                    }
                    udef = getattr(ad, "unit", None)
                    if isinstance(udef, str) and udef:
                        # simple default unit → enum of one
                        unit_schema["enum"] = [udef]
                        unit_schema["default"] = udef
                    elif isinstance(udef, dict):
                        ucons = (udef.get("constraints") or {}) if isinstance(udef, dict) else {}
                        uenum = ucons.get("enum")
                        if isinstance(uenum, (list, tuple)) and uenum:
                            unit_schema["enum"] = list(uenum)
                            unit_schema["default"] = uenum[0]
                        if udef.get("description"):
                            unit_schema["description"] = udef["description"]

                    inner_props["unit"] = unit_schema

                    # provenance_ref (optional)
                    inner_props["provenance_ref"] = {
                        "type": "string",
                        "description": f"Provenance relation for attribute '{an}' of class '{cname}'.",
                    }

                    attr_field: Dict[str, Any] = {
                        "type": "object",
                        "properties": inner_props,
                        "additionalProperties": False,
                    }

                    # inside the attribute object, require "value" if attribute is required
                    if ad.required:
                        attr_field["required"] = ["value"]
                        # and the attributes map must contain this attribute key
                        attr_required.append(an)

                    attr_props[an] = attr_field

                attr_schema: Dict[str, Any] = {
                    "type": "object",
                    "properties": attr_props,
                    "additionalProperties": False,
                }
                if attr_required:
                    # required keys in the attributes map
                    attr_schema["required"] = attr_required

                # ---- relations schema for this class ----
                ref_props: Dict[str, Any] = {}
                ref_required: list[str] = []

                for rn, rd in refs_def.items():
                    ref_field_schema, is_req = _jsonschema_schema_for_relation(rd)
                    ref_props[rn] = ref_field_schema
                    if is_req:
                        ref_required.append(rn)

                ref_schema: Dict[str, Any] = {
                    "type": "object",
                    "properties": ref_props,
                    "additionalProperties": False,
                }
                if ref_required:
                    ref_schema["required"] = ref_required

                # ---- entity schema for this class ----
                entity_schema: Dict[str, Any] = {
                    "type": "object",
                    "properties": {
                        "attributes": attr_schema,
                        "relations": ref_schema,
                    },
                    "required": ["attributes", "relations"],
                    "additionalProperties": False,
                }

                # ---- class-level map: { "<entity_id>": <entity_schema> } ----
                class_entities_schema: Dict[str, Any] = {
                    "type": "object",
                    "description": f"Entities of class '{cname}', keyed by entity id.",
                    "patternProperties": {
                        "^[^\\s]+$": entity_schema  # any non-empty, non-whitespace id
                    },
                    "additionalProperties": False,
                }

                schema["properties"][cname] = class_entities_schema

            with open(schema_path, "w", encoding="utf-8") as f:
                _json.dump(schema, f, indent=2, ensure_ascii=False)
