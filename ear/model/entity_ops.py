"""ear.model.entity_ops — Entity/attribute/relation CRUD

Creating entities, setting attributes, adding relations, and the
low-level field/library helpers that back them.

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
Behaviour is unchanged; only module boundaries moved.
"""

from __future__ import annotations
import json
import warnings
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Union, Tuple
from difflib import get_close_matches
import os, pathlib
import yaml
from pathlib import Path
import re


from ear.entity import Entity
from ear.constraint import Constraint
from ear.relation_def import RelationDef
from ear.attribute_def import AttributeDef

class EntityOpsMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def get_attr_value(self, entity_class: str, entity_id: str, attribute_id: str, default=None):
        """
        Return the scalar value of an attribute on an entity.

        Returns *default* (rather than raising) if the entity class, entity id,
        or attribute is not present, making it safe to call before an attribute
        has been set for the first time.
        """
        cls_store = self.entities.get(entity_class)
        if cls_store is None:
            return default
        entity = cls_store.get(entity_id)
        if entity is None:
            return default

        raw = getattr(entity, "data", {}).get(attribute_id, default)

        if isinstance(raw, dict) and "value" in raw:
            return raw["value"]
        if isinstance(entity, dict) and attribute_id in entity:
            return entity[attribute_id]
        return raw

    ##  schema loading & introspection

    def set_attr_value(self, entity_id: str, attr: str, value):
        """Return the 'value' part of an attribute (handles AttributeValue and legacy scalars)."""
        if value is None:
            return
        self.add_attribute(entity_id, attr, value)

    def import_library(self, library_yaml: str, *, namespace: str | None = None,
                       conflict: str = "error"):
        """
        Import a master-data library (YAML) and optionally prefix entity IDs.

        conflict:
          - "error": raise if an ID already exists
          - "skip": keep existing entity, skip incoming
          - "overwrite": replace existing entity data
        """
        import yaml
        library_path = Path(library_yaml)
        if library_path.is_dir():
            blob = {}
            for part in sorted(library_path.rglob("*.y*ml")):
                doc = yaml.safe_load(part.read_text(encoding="utf-8")) or {}
                if not isinstance(doc, dict):
                    continue
                for key, value in doc.items():
                    if key == "description":
                        continue
                    if key in blob and isinstance(blob[key], dict) and isinstance(value, dict):
                        overlap = set(blob[key]) & set(value)
                        if overlap:
                            raise ValueError(f"Duplicate library ids in {part}: {sorted(overlap)}")
                        blob[key].update(value)
                    elif key in blob and blob[key] != value:
                        raise ValueError(f"Duplicate library section {key!r} while loading {part}")
                    else:
                        blob[key] = value
        else:
            blob = yaml.safe_load(library_path.read_text(encoding="utf-8")) or {}

        if namespace:
            ns = namespace.rstrip("__") + "__"
            renamed = {}
            for cls, ents in blob.items():
                renamed.setdefault(cls, {})
                for eid, edata in (ents or {}).items():
                    renamed[cls][ns + eid] = edata

                    # also rewrite relation targets inside the library if they point to local IDs
                    rels = ((edata or {}).get("relations") or [])
                    for r in rels:
                        if isinstance(r, dict) and "target_entity_ids" in r:
                            r["target_entity_ids"] = [
                                (ns + t) if isinstance(t, str) and not t.startswith(ns) else t
                                for t in r["target_entity_ids"]
                            ]
            blob = renamed

        # now merge according to conflict strategy using existing import logic:
        # simplest: write to temp file and call import_yaml()
        tmp_base = library_path if library_path.is_file() else (library_path / "__combined__")
        tmp = tmp_base.with_suffix(".tmp.__import__.yaml")
        tmp.write_text(yaml.safe_dump(blob, sort_keys=False), encoding="utf-8")
        try:
            return self.import_yaml(str(tmp), strict_unknown=False)
        finally:
            tmp.unlink(missing_ok=True)

    def add_entity(self, entity_class: str, entity_id: str):

        """
        Create a new entity of a given class with a globally unique ID --
        or, if that ID already exists (in any class), return the
        existing entity as-is and emit a warning, rather than creating
        a second one.

        Parameters
        ----------
        entity_class :
            Name of the CESDM class to instantiate (as defined in the YAML schema).
        entity_id :
            Globally unique identifier for this entity. If an entity
            with this ID already exists (in any class), that existing
            entity is returned unchanged instead of creating a new one.

        Returns
        -------
        Entity
            The newly created entity, or -- if ``entity_id`` was already
            in use -- the existing entity with that ID (its class is
            not checked against ``entity_class``; use ``ensure_entity()``
            instead if a class mismatch on reuse should raise). Its own
            ``add_attribute()``/``add_relation()`` methods are
            equivalent, object-oriented shortcuts for
            ``model.add_attribute(entity_id, ...)``/
            ``model.add_relation(entity_id, ...)``::

                gen = model.add_entity("GenerationUnit", "gen.1")
                gen.add_attribute("name", "gen.1")
                gen.add_relation("hasTechnology", "Generation.Thermal.Gas.CCGT")

        Raises
        ------
        ValueError
            If the class does not exist. (A duplicate ID no longer
            raises -- see above.)
        """

        cname = self._canonicalize_class(entity_class)
        # Coerce to a genuine `str` (not a subclass like EntityProxy) before
        # storage -- equality/hashing/dict-lookup treat a str subclass
        # instance identically to a plain str, so this class of bug stays
        # invisible until something tries to *serialize* the stored value
        # (PyYAML's representer dispatch is exact-type, not isinstance-based,
        # so a stored EntityProxy fails to export while looking completely
        # normal everywhere else). See CHANGELOG.md.
        entity_id = str(entity_id)

        # global uniqueness prüfen -- reuse instead of raising
        for other_cls, ents in self.entities.items():
            if entity_id in ents:
                warnings.warn(
                    f"add_entity(): id '{entity_id}' already exists in class "
                    f"'{other_cls}' -- returning the existing entity unchanged "
                    f"instead of creating a new one. Use ensure_entity() if a "
                    f"class mismatch here should raise instead.",
                    stacklevel=2,
                )
                return ents[entity_id]

        # Klassen-Definition (inkl. vererbter Attribute – wird in resolve_inheritance gemerged)
        cdef = self.classes.get(cname)
        if cdef is None:
            raise ValueError(f"Unknown entity class: {entity_class}")

        # Daten-Dict mit Defaults initialisieren
        init_data: Dict[str, Any] = {}

        if cname not in self.entities:
            self.entities[cname] = {}
        new_entity = Entity(cls=cname, id=entity_id, data=init_data, _model=self)
        self.entities[cname][entity_id] = new_entity

        # now apply defaults via add_attribute so they become AttributeValue
        # -- except for belongsToGroup-tagged attributes, whose defaults
        # are resolved lazily on read instead (see
        # get_effective_attribute_value()). Writing them here
        # unconditionally would activate that group's conditional-
        # requiredness on every single instance of the class regardless
        # of whether the group was ever actually intended -- e.g. the
        # dynamic machine model's inertia_constant/reactance attributes (which all have
        # real IEEE-typical defaults) on DynamicMachineModelType.Synchronous.
        for aname, adef in cdef.attributes.items():
            if adef.default is not None and not getattr(adef, "belongsToGroup", None):
                self.add_attribute(entity_id, aname, adef.default)

        return new_entity
        # # Alle Attribute der Klasse durchgehen
        # for aname, adef in cdef.attributes.items():
        #     if adef.default is not None:
        #         # nur Attribute mit Default setzen
        #         init_data[aname] = adef.default
        #     # Wenn du *alle* Attribute sehen willst, selbst ohne Default:
        #     # else:
        #     #     init_data[aname] = None

        # # Entity anlegen
        # if cname not in self.entities:
        #     self.entities[cname] = {}
        # self.entities[cname][entity_id] = Entity(cls=cname, id=entity_id, data=init_data)

    # def _unwrap_attributevalue(self, val):
    #     """
    #     Helper: take either a scalar or an AttributeValue-like dict and return
    #     (value, unit, provenance_ref).
    #     """
    #     if isinstance(val, dict) and "value" in val:
    #         return val.get("value"), val.get("unit"), val.get("provenance_ref")
    #     return val, None, None

    def _find_existing_target_class(self, ref_def: RelationDef, tid: str) -> Optional[str]:
        for cls_name in ref_def.targets:
            if cls_name in self.entities and tid in self.entities[cls_name]:
                return cls_name
        return None

    def _unwrap_attributevalue(self, val):
        """
        Helper: take either a scalar or an AttributeValue-like dict and return
        (value, unit, provenance_ref).
        """
        if isinstance(val, dict) and "value" in val:
            return val.get("value"), val.get("unit"), val.get("provenance_ref")
        return val, None, None

    def add_attribute(
        self,
        entity_id: str,
        attribute_id: str,
        value,
        unit: str | None = None,
        provenance_ref: str | None = None,
    ):
        """
        Set or update an attribute_id on an existing entity.

        Internally attributes are stored as AttributeValue objects::

            {
              "value": <typed value>,
              "unit": "<unit or '-'>",           # optional
              "provenance_ref": "<source-id>",  # optional
            }

        Behaviour:

        - Reads the attribute *type* and *constraints* from the class schema
          (AttributeDef) and coerces the value accordingly.
        - Supports both scalar values and full AttributeValue dicts.
        - Derives default + allowed units from the nested ``unit`` definition
          in the schema (via constraints.enum).
        - Checks both value-constraints (enum/min/max/pattern) and
          unit-constraints (allowed units) before storing.
        """
        entity_id = str(entity_id)
        ent, cdef = self._get_entity_and_class(entity_id)

        attrs = getattr(cdef, "attributes", {}) or {}
        if attribute_id not in attrs:
            known = list(attrs.keys()) if hasattr(attrs, "keys") else []
            raise KeyError(
                f"[{getattr(cdef, 'name', type(cdef).__name__)}:{entity_id}] "
                f"Unknown attribute '{attribute_id}'. Known: {known}"
            )

        ad = attrs[attribute_id]

        # ---------- derive default & allowed units from ad.unit ----------
        default_unit = None
        allowed_units = None

        udef = getattr(ad, "unit", None)
        if isinstance(udef, str):
            default_unit = udef or None
        elif isinstance(udef, dict):
            cons = udef.get("constraints") or {}
            enum = cons.get("enum")
            if isinstance(enum, (list, tuple)) and enum:
                allowed_units = list(enum)
                default_unit = allowed_units[0]

        if default_unit == "":
            default_unit = None

        # ---------- normalize incoming to AttributeValue dict ------------
        if isinstance(value, dict) and "value" in value:
            raw_value = value.get("value")
            attr_value = dict(value)  # shallow copy
            if unit is not None:
                attr_value["unit"] = unit
            if provenance_ref is not None:
                attr_value["provenance_ref"] = provenance_ref
        else:
            raw_value = value
            attr_value = {"value": value}
            if unit is not None:
                attr_value["unit"] = unit
            if provenance_ref is not None:
                attr_value["provenance_ref"] = provenance_ref

        # ---------- type coercion on VALUE -------------------------------
        atype = self._field(ad, "type")

        # handle numpy scalars gracefully
        try:
            import numpy as _np  # type: ignore
            if isinstance(raw_value, _np.generic):
                raw_value = raw_value.item()
        except Exception:
            pass

        if atype in ("float", "number", "double", "decimal", float):
            if raw_value not in (None, ""):
                raw_value = float(raw_value)
        elif atype in ("int", int, "integer"):
            if raw_value not in (None, ""):
                raw_value = int(raw_value)
        elif atype in ("bool", "boolean", bool):
            if isinstance(raw_value, bool):
                pass
            else:
                s = str(raw_value).strip().lower()
                if s in ("true", "1", "yes"):
                    raw_value = True
                elif s in ("false", "0", "no"):
                    raw_value = False
                else:
                    raise ValueError(
                        f"[{getattr(cdef, 'name', '?')}:{entity_id}] "
                        f"Cannot coerce '{raw_value}' to bool for '{attribute_id}'."
                    )
        # else: leave strings / other types as-is

        # A str SUBCLASS (e.g. EntityProxy, if one is ever passed as a
        # string-typed attribute value by mistake) must still be coerced
        # to a genuine str -- see add_entity's identical fix for why.
        if isinstance(raw_value, str) and type(raw_value) is not str:
            raw_value = str(raw_value)

        attr_value["value"] = raw_value

        # ---------- constraint checks on VALUE ---------------------------
        cons = ad.constraints or Constraint()

        if cons.enum is not None:
            if raw_value not in cons.enum:
                print(
                    f"[{getattr(cdef, 'name', '?')}:{entity_id}] "
                    f"Value '{raw_value}' is not allowed for '{attribute_id}'. "
                    f"Allowed: {cons.enum}"
                )

        if isinstance(raw_value, (int, float)):
            if cons.minimum is not None and raw_value < cons.minimum:
                print(
                    f"[{getattr(cdef, 'name', '?')}:{entity_id}] "
                    f"Value {raw_value} for '{attribute_id}' is below minimum {cons.minimum}."
                )
            if cons.maximum is not None and raw_value > cons.maximum:
                print(
                    f"[{getattr(cdef, 'name', '?')}:{entity_id}] "
                    f"Value {raw_value} for '{attribute_id}' is above maximum {cons.maximum}."
                )

        if cons.pattern is not None:
            import re as _re
            s = "" if raw_value is None else str(raw_value)
            if not _re.fullmatch(cons.pattern, s):
                raise ValueError(
                    f"[{getattr(cdef, 'name', '?')}:{entity_id}] "
                    f"Value '{raw_value}' for '{attribute_id}' does not match pattern '{cons.pattern}'."
                )

        # ---------- determine final UNIT --------------------------------
        current_unit = attr_value.get("unit")
        if current_unit in ("", None):
            if unit is not None:
                current_unit = unit
            elif default_unit is not None:
                current_unit = default_unit
            else:
                current_unit = None

        if current_unit is not None and allowed_units:
            if current_unit not in allowed_units:
                raise ValueError(
                    f"[{getattr(cdef, 'name', '?')}:{entity_id}] "
                    f"Unit '{current_unit}' is not allowed for '{attribute_id}'. "
                    f"Allowed: {allowed_units}"
                )

        if current_unit is not None:
            attr_value["unit"] = current_unit
        else:
            attr_value.pop("unit", None)

        # ---------- store on entity -------------------------------------
        if hasattr(ent, "data") and isinstance(ent.data, dict):
            ent.data[attribute_id] = attr_value
        else:
            setattr(ent, attribute_id, attr_value)

    def add_relation(self, entity_id: str, relation_id: str, target_entity_id: str, **kwargs):

        """
        Set or update a relation on an existing entity.

        Parameters
        ----------
        entity_id :
            Identifier of the entity to modify.
        relation_id :
            Name of the relation field (must be defined in the entity's class).
        target_entity_id :
            Identifier of the target entity.

        Raises
        ------
        KeyError
            If the source entity does not exist.
        ValueError
            If the relation name is unknown, the target does not exist,
            or the target has an incompatible class.
        """

        relation_id = relation_id or kwargs.pop('attribute', None) or kwargs.pop('ref', None)
        target_entity_id = target_entity_id or kwargs.pop('target', None) or kwargs.pop('value', None)
        if relation_id is None or target_entity_id is None:
            print(f"entity_id={entity_id},relation_id={relation_id} and target_entity_id={target_entity_id}.")
            raise TypeError("add_relation requires `relation` and `target_entity_id`.")
        # Coerce to plain str -- see add_entity's identical fix for why
        # (a str-subclass like EntityProxy stored as-is behaves identically
        # everywhere except serialization, where it silently breaks).
        entity_id = str(entity_id)
        target_entity_id = str(target_entity_id)
        ent, cdef = self._get_entity_and_class(entity_id)
        refs = getattr(cdef, 'relations', {}) or {}
        if relation_id not in refs:
            cname = getattr(cdef, 'name', type(cdef).__name__)
            known = list(refs.keys()) if hasattr(refs, "keys") else []
            raise KeyError(f"[{cname}:{entity_id}] Unknown relation '{relation_id}' (declare it under `relations`). Known relations {known}")
        cls_name = getattr(cdef, 'name', type(cdef).__name__)
        self._set_entity_field(cls_name, entity_id, ent, relation_id, target_entity_id)
        return ent

    def add(self, cls_name: str | None = None, id=None, *values, **kwargs):

        """
        High-level helper to create an entity and set multiple fields at once.

        Parameters
        ----------
        class_name :
            Name of the CESDM class to instantiate.
        id :
            Globally unique entity identifier.
        **fields :
            Attribute and relation name/value pairs. The toolbox determines
            from the schema whether each key is an attribute or relation.

        Returns
        -------
        Entity
            The newly created entity with the given fields populated.

        Raises
        ------
        ValueError
            If the class does not exist, the ID is not unique, an unknown field
            is provided, or a value cannot be coerced/validated.
        """
        if cls_name is None:
            cls_name = kwargs.pop("entityclass", kwargs.pop("class", None))
        if id is None and "id" in kwargs:
            id = kwargs.pop("id")
        if cls_name is None or id is None:
            raise ValueError("add requires class/entityclass and id")
        cname = self._canonicalize_class(cls_name)
        cdef = self.classes[cname]
        order = list(cdef.attributes.keys())
        assembled = dict(kwargs)
        if len(values) > len(order):
            raise ValueError(f"Too many positional values for class '{cname}'. Expected <= {len(order)}")
        for i, v in enumerate(values):
            an = order[i]
            if an not in assembled:
                assembled[an] = v
        return self._add_raw(cname, id=id, **assembled)

    ## Validation

    def _get_entity_and_class(self, entity_id: str):
        for cname, ents in self.entities.items():
            if entity_id in ents:
                return ents[entity_id], self.classes[cname]
        raise KeyError(
            f"No entity with id {entity_id!r} found. It must be created first "
            f"(add_entity / ensure_entity / an add_* builder) before setting "
            f"attributes or relations on it."
        )

    def _set_entity_field(self, cls_name: str, entity_id: str, entity_obj, attr: str, value):
        # 1) If the backing store in self.entities is a dict, write there
        store = self.entities.get(cls_name, {}).get(entity_id)
        if isinstance(store, dict):
            store[attr] = value
            return

        # 2) If the entity is your dataclass with .data
        if hasattr(entity_obj, "data") and isinstance(entity_obj.data, dict):
            entity_obj.data[attr] = value
            return

        # 3) Fallbacks for other shapes
        if hasattr(entity_obj, "values") and isinstance(entity_obj.values, dict):
            entity_obj.values[attr] = value
            return
        if hasattr(entity_obj, "attributes") and isinstance(entity_obj.attributes, dict):
            entity_obj.attributes[attr] = value
            return

        raise TypeError("Unsupported entity storage for attribute assignment")

    def _field(self, ad, name, default=None):
        """Return attribute field from either a dict or an object.
        Robust to accidental arg swapping or non-string field names.
        """
        if not isinstance(name, str):
            # if the third arg is a string, assume args were swapped
            if isinstance(default, str):
                name, default = default, None
            else:
                return default  # fail-soft
        if isinstance(ad, dict):
            return ad.get(name, default)
        return getattr(ad, name, default)

    ## Helpers for Entity and Attribute listings

    def _add_raw(self, cls: str, id: str, **kwargs):
        if cls not in self.classes:
            raise ValueError(f"Unknown entity class: {cls}")
        # global unique id
        for other_cls, ents in self.entities.items():
            if id in ents:
                raise ValueError(f"Duplicate id '{id}' already exists in class '{other_cls}'. Entity IDs must be globally unique.")
        cdef = self.classes[cls]
        data: Dict[str, Any] = {}
        # defaults
        for an, ad in cdef.attributes.items():
            if an in kwargs:
                data[an] = kwargs[an]
            elif ad.default is not None:
                data[an] = ad.default
        # extras (unknown checked later)
        for k, v in kwargs.items():
            data[k] = v
        self.entities[cls][id] = Entity(cls=cls, id=id, data=data)

    def _slugify_name(self,s: str) -> str:
        import re
        s = s.lower()
        s = re.sub(r'[^-a-z0-9._/]+', '-', s)
        return s.strip('-')

    def _slugify_resource_name(self, s: str) -> str:
        """Convert a class name to a Frictionless-compliant resource name.

        Frictionless requires names matching ``^([-a-z0-9._/])+$``.
        PascalCase and camelCase word boundaries are converted to hyphens
        so that ``GenerationUnit`` becomes ``generation-unit``.
        """
        # Insert hyphen before each uppercase letter that follows a lowercase
        # letter or digit (CamelCase → kebab-case)
        s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', s)
        # Also handle sequences like "NTCLink" → "ntc-link"
        s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1-\2', s)
        s = s.lower()
        # Replace any remaining invalid characters with hyphens
        s = re.sub(r'[^-a-z0-9._/]+', '-', s)
        return s.strip('-')



