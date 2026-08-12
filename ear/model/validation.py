"""ear.model.validation — Attribute/type validation & coercion

model.validate() and the type-coercion helpers it relies on.

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
Behaviour is unchanged; only module boundaries moved.
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


class ValidationMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def validate(self):

        """
        Validate all entities in the model against the loaded schema.

        Checks performed include:

        - presence of required attributes,
        - type correctness of attribute values,
        - compliance with numeric constraints (min/max),
        - compliance with enumerations and patterns,
        - existence and class compatibility of relation targets.

        Returns
        -------
        list of str
            List of human-readable error messages. The list is empty if the
            model passes all validation checks.
        """

        errors = []

        class_map = getattr(self, "classes", {}) or {}
        entity_map = getattr(self, "entities", {}) or {}

        for cname, cdef in class_map.items():
            attrs_def, refs_def = self._collect_inherited_fields(cdef)

            known_fields = set(attrs_def.keys()) | set(refs_def.keys())
            ents = entity_map.get(cname, {}) or {}

            for eid, ent in ents.items():
                data = getattr(ent, "data", {}) or {}

                # An attribute/relation tagged with belongsToGroup is only
                # required if the entity actually uses at least one of
                # its groups (a field can belong to more than one group,
                # e.g. both "dispatch" and "power_flow") -- mirrors the
                # old semantics: "required if this view exists on the
                # asset", now that a view's fields live directly on the
                # asset instead of a separate entity. Fields with no
                # belongsToGroup (the base ones) keep their unconditional
                # required semantics, unchanged.
                active_groups = set()
                for aname2, adef2 in attrs_def.items():
                    groups2 = getattr(adef2, "belongsToGroup", None) or []
                    if groups2 and aname2 in data and data[aname2] not in ("", None):
                        active_groups.update(groups2)
                for rname2, rdef2 in refs_def.items():
                    groups2 = getattr(rdef2, "belongsToGroup", None) or []
                    if groups2 and rname2 in data and data[rname2] not in ("", None):
                        active_groups.update(groups2)

                def _group_gates_required(fdef) -> bool:
                    groups = getattr(fdef, "belongsToGroup", None) or []
                    return not groups or any(g in active_groups for g in groups)

                # 2) Attribute: required + type + constraints
                for aname, adef in attrs_def.items():
                    required = bool(self._get_meta(adef, "required", False)) and _group_gates_required(adef)

                    atype = self._get_meta(adef, "type", None)
                    constraints = self._constraints_to_dict(self._get_meta(adef, "constraints", {}))

                    present = aname in data and data[aname] not in ("", None)

                    if required and not present:
                        errors.append(f"[{cname}:{eid}] Missing required attribute '{aname}'")
                        continue

                    if present:
                        val = data[aname]
                        ok, coerced, msg = self._coerce_and_check_type(val, atype)
                        if not ok:
                            errors.append(f"[{cname}:{eid}] Attribute '{aname}' type error: {msg}")
                        else:
                            # numerical constraints
                            # Only apply numeric constraints for numeric types and when coercion succeeded
                            atype_norm = (str(atype).lower() if atype is not None else None)
                            is_numeric_type = atype_norm in {"float", "number", "integer", "int", "double", "decimal"}

                            if is_numeric_type and ok:
                                if "minimum" in constraints and constraints["minimum"] is not None:
                                    try:
                                        if float(coerced) < float(constraints["minimum"]):
                                            errors.append(
                                                f"[{cname}:{eid}] Attribute '{aname}' violates minimum {constraints['minimum']}: {coerced}"
                                            )
                                    except Exception:
                                        # value couldn’t be compared numerically — treat as type error
                                        errors.append(
                                            f"[{cname}:{eid}] Attribute '{aname}' cannot be compared numerically for minimum"
                                        )

                                if "maximum" in constraints and constraints["maximum"] is not None:
                                    try:
                                        if float(coerced) > float(constraints["maximum"]):
                                            errors.append(
                                                f"[{cname}:{eid}] Attribute '{aname}' violates maximum {constraints['maximum']}: {coerced}"
                                            )
                                    except Exception:
                                        errors.append(
                                            f"[{cname}:{eid}] Attribute '{aname}' cannot be compared numerically for maximum"
                                        )
                            # If the schema accidentally defines numeric constraints on a non-numeric type,
                            # we silently ignore them (or log a warning if you prefer).

                            # enum
                            enum_vals = constraints.get("enum")
                            if enum_vals:
                                try:
                                    if coerced not in enum_vals:
                                        errors.append(
                                            f"[{cname}:{eid}] Attribute '{aname}' not in enum {enum_vals}: {coerced}"
                                        )
                                except Exception:
                                    errors.append(f"[{cname}:{eid}] Attribute '{aname}': cannot evaluate enum against '{val}'")

                            # regex (only meaningful for strings)
                            regex_pat = constraints.get("regex")
                            if regex_pat:
                                import re as _re
                                s = str(coerced)
                                if _re.fullmatch(regex_pat, s) is None:
                                    errors.append(
                                        f"[{cname}:{eid}] Attribute '{aname}' does not match regex '{regex_pat}': '{s}'"
                                    )

                            # length constraints (for strings)
                            if isinstance(coerced, str):
                                min_len = constraints.get("min_length")
                                max_len = constraints.get("max_length")
                                if min_len is not None and len(coerced) < int(min_len):
                                    errors.append(
                                        f"[{cname}:{eid}] Attribute '{aname}' length<{min_len}"
                                    )
                                if max_len is not None and len(coerced) > int(max_len):
                                    errors.append(
                                        f"[{cname}:{eid}] Attribute '{aname}' length>{max_len}"
                                    )

                # 3) Referenzen: required + kardinalität (optional)
                # if cname=="Generator":
                #     pdb.set_trace()
                for rname, rdef in refs_def.items():
                    r_required = bool(self._get_meta(rdef, "required", False)) and _group_gates_required(rdef)
                    r_constraints = self._constraints_to_dict(self._get_meta(rdef, "constraints", {}))
                    present = rname in data and data[rname] not in ("", None)

                    if r_required and not present:
                        errors.append(f"[{cname}:{eid}] Missing required relation '{rname}'")
                        continue

                    if present:
                        # normalize to list for cardinality checks
                        val = data[rname]
                        targets = val if isinstance(val, (list, tuple)) else [val]

                        # min/max items
                        min_items = r_constraints.get("min_items")
                        max_items = r_constraints.get("max_items")
                        if min_items is not None and len(targets) < int(min_items):
                            errors.append(f"[{cname}:{eid}] Relation '{rname}' has <{min_items} targets")
                        if max_items is not None and len(targets) > int(max_items):
                            errors.append(f"[{cname}:{eid}] Relation '{rname}' has >{max_items} targets")

                        # uniqueness
                        if r_constraints.get("unique", False):
                            if len(set(targets)) != len(targets):
                                errors.append(f"[{cname}:{eid}] Relation '{rname}' contains duplicate target ids")
                        
                        ref_cls = refs_def[rname].target
                        ref_par = ref_cls;
                        # self.inheritance[ref_cls]

                        ref_def = refs_def[rname]
                        allowed_targets = ref_def.targets or []

                        for target in targets:
                            try:
                                ref_entry, cdef = self._get_entity_and_class(target)
                            except KeyError:
                                ref_entry, cdef = None, None

                            if ref_entry is None:
                                # Accept generated default-library ids only when their declared
                                # library class is compatible with the relation target class.
                                try:
                                    from cesdm.default_library import DEFAULT_LIBRARY_CLASS_BY_ID
                                except ImportError:
                                    DEFAULT_LIBRARY_CLASS_BY_ID = {}
                                library_class = DEFAULT_LIBRARY_CLASS_BY_ID.get(str(target))
                                compatible = bool(library_class) and (
                                    not allowed_targets or any(
                                        self.is_class_derived_from(library_class, tgt, self.inheritance)
                                        for tgt in allowed_targets
                                    )
                                )
                                if not compatible:
                                    tgt_desc = ", ".join(allowed_targets) if allowed_targets else "<any>"
                                    if library_class:
                                        errors.append(
                                            f"[{cname}:{eid}] Relation '{rname}' with predefined id '{target}' "
                                            f"is of class '{library_class}', not compatible with [{tgt_desc}]"
                                        )
                                    else:
                                        errors.append(
                                            f"[{cname}:{eid}] Relation '{rname}' with '{target}' not among entities "
                                            f"of allowed classes [{tgt_desc}]"
                                        )
                            else:
                                if allowed_targets:
                                    # entity exists, but check that its class is compatible with at least one target
                                    if not any(self.is_class_derived_from(ref_entry.cls, tgt, self.inheritance)
                                               for tgt in allowed_targets):
                                        tgt_desc = ", ".join(allowed_targets)
                                        errors.append(
                                            f"[{cname}:{eid}] Relation '{rname}' with '{target}' is of class '{ref_entry.cls}' "
                                            f"not compatible with any of [{tgt_desc}]"
                                        )

        return errors

    ## Export methods

    def _coerce_and_check_type(self, value, expected_type: str):
        """
        Versucht value in expected_type zu überführen und gibt (ok, coerced_value, err_msg) zurück.
        expected_type (case-insensitive): float|number, integer|int, string, boolean.

        NEU: wenn `value` ein AttributeValue-Dict ist ({"value": ..., "unit": ...}),
        wird intern nur der `value`-Teil geprüft.
        """
        if expected_type is None:
            return True, value, None

        t = str(expected_type).lower()

        # already None/empty is handled außerhalb (required)
        # --- NEU: AttributeValue entpacken ---
        if isinstance(value, dict) and "value" in value:
            inner = value.get("value")
        else:
            inner = value

        v = inner

        # accept numbers given as strings "123" / "3.14"
        if t in ("float", "number", "double", "decimal"):
            # allow bools? usually no; convert True/False -> 1/0 only if string
            try:
                if isinstance(v, str):
                    v = v.strip().replace(",", ".")
                return True, float(v), None
            except Exception:
                return False, value, f"cannot parse '{inner}' as {t}"

        if t in ("integer", "int"):
            try:
                if isinstance(v, str):
                    v = v.strip()
                    # allow "3.0" -> 3
                    return True, int(float(v.replace(",", "."))), None
                return True, int(v), None
            except Exception:
                return False, value, f"cannot parse '{inner}' as integer"

        if t in ("boolean", "bool"):
            if isinstance(v, bool):
                return True, v, None
            s = str(v).strip().lower()
            if s in ("true", "1", "yes"):
                return True, True, None
            if s in ("false", "0", "no"):
                return True, False, None
            return False, value, f"cannot parse '{inner}' as boolean"

        # strings / unknown types: stringify (but validate with other constraints later)
        return True, str(inner) if inner is not None else "", None

    def _coerce_for_attr(self, cls_name: str, attr: str, value):
        """
        Best-effort coercion based on schema type.

        In the AttributeValue world:

        - If `value` is already an AttributeValue dict (has "value"),
          we do NOT coerce it here; add_attribute() will handle it.
        - If `value` is a string that looks like a dict with "value",
          we parse it to a dict first and return that.
        - Otherwise we apply the legacy scalar coercion (float/int/bool).
        """
        cdef = self.classes[cls_name]
        attrs, _ = self._collect_inherited_fields(cdef)
        ad = attrs.get(attr)
        if not ad or value is None:
            return value

        # 1) Already an AttributeValue dict → pass through
        if isinstance(value, dict) and "value" in value:
            return value

        # 2) String that looks like a dict → try to parse
        if isinstance(value, str):
            s = value.strip()
            if s.startswith("{") and "value" in s:
                import ast
                try:
                    maybe = ast.literal_eval(s)
                except Exception:
                    maybe = None
                if isinstance(maybe, dict) and "value" in maybe:
                    return maybe
            # empty string -> no value
            if s == "":
                return None

        # 3) Legacy scalar coercion
        s = value
        t = (ad.type or "").lower()

        # floats
        if t in ("float", "number", "double", "decimal"):
            try:
                if isinstance(s, str):
                    s2 = s.strip().replace(",", ".")
                    return float(s2)
                return float(s)
            except Exception:
                print(
                    f"Attribute '{attr}' type error: "
                    f"cannot parse '{value}' as float"
                )
                raise

        # ints
        if t in ("int", "integer", "long"):
            try:
                if isinstance(s, str):
                    s2 = s.strip()
                    return int(float(s2.replace(",", ".")))
                return int(s)
            except Exception:
                print(
                    f"Attribute '{attr}' type error: "
                    f"cannot parse '{value}' as int"
                )
                raise

        # bools
        if t in ("bool", "boolean"):
            if isinstance(s, bool):
                return s
            txt = str(s).strip().lower()
            if txt in ("true", "1", "yes"):
                return True
            if txt in ("false", "0", "no"):
                return False
            print(
                f"Attribute '{attr}' type error: "
                f"cannot parse '{value}' as bool"
            )
            raise ValueError(f"cannot parse '{value}' as bool")

        # default: leave as-is (string, etc.)
        return value

    def _coerce_type(self, value: Any, type_name: str) -> Any:
        if value is None:
            return None
        if type_name == "string":
            return str(value)
        if type_name in ("float", "number", "double", "decimal"):
            return float(value)
        if type_name == "int":
            return int(value)
        if type_name == "bool":
            if isinstance(value, bool):
                return value
            s = str(value).lower()
            if s in ("true", "1", "yes"):
                return True
            if s in ("false", "0", "no"):
                return False
            raise ValueError(f"Cannot coerce '{value}' to bool")
        return value


    # ------------------------------------------------------------------ #
    #  Frictionless Data Package  —  generic base implementation          #
    # ------------------------------------------------------------------ #
