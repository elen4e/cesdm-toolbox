"""ear.model.pydantic_export — Pydantic model generation

Generates runtime pydantic models from the loaded schema classes.

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


from ear.constraint import Constraint
from ear.attribute_def import AttributeDef

class PydanticExportMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def build_pydantic_models(self):
        """
        Build Pydantic models (v2) for all classes (inheritance-aware).
        Exposes self.py_models[class_name] for non-abstract classes.
        """
        from typing import Optional, Literal
        try:
            from pydantic import BaseModel, Field, ConfigDict, field_validator, create_model, conint, confloat  # type: ignore
        except Exception as e:
            raise RuntimeError("Pydantic is required for build_pydantic_models()") from e

        self.py_models = {}
        bases = {}

        # topo order
        seen, out = set(), []
        def dfs(cn):
            if cn in seen:
                return
            seen.add(cn)
            c = self.classes[cn]
            parents = getattr(c, "parents", []) or []
            if isinstance(parents, str):
                parents = [parents]
            for p in parents:
                dfs(p)
            out.append(cn)
        for cn in self.classes:
            dfs(cn)

        type_map = {"string": str, "int": int, "float": float, "bool": bool}

        def pyd_type(a: AttributeDef):
            base = type_map.get(a.type, str)
            ann = base
            cons = a.constraints or Constraint()

            if cons.enum:
                ann = Literal[tuple(cons.enum)]  # type: ignore

            if base is int:
                ge, le = cons.minimum, cons.maximum
                if ge is not None or le is not None:
                    ann = conint(ge=ge if ge is not None else None, le=le if le is not None else None)  # type: ignore
            elif base is float:
                ge, le = cons.minimum, cons.maximum
                if ge is not None or le is not None:
                    ann = confloat(ge=ge if ge is not None else None, le=le if le is not None else None)  # type: ignore

            default = ... if a.required and a.default is None else (a.default)
            if not a.required and a.default is None:
                from typing import Optional as _Opt
                ann = _Opt[ann]  # type: ignore
                default = None

            fld = Field(default, description=a.description)
            return ann, fld

        for cname in out:
            c = self.classes[cname]
            fields = { an: pyd_type(ad) for an, ad in c.attributes.items() }

            parents = getattr(c, "parents", []) or []
            if isinstance(parents, str):
                parents = [parents]
            # For Pydantic we take the first parent as base; all attributes from
            # additional parents are already merged into ``c.attributes``.
            base = BaseModel
            if parents:
                base = bases.get(parents[0], BaseModel)

            mdl = create_model(cname, __base__=base, **fields)  # type: ignore
            mdl.model_config = ConfigDict(extra="forbid", validate_default=True)

            # ref_fields = [an for an, ad in c.attributes.items() if ad.constraints and ad.constraints.ref]
            # if ref_fields:
            #     @field_validator(*ref_fields)
            #     def _check_refs(cls, v, info):
            #         if v is None:
            #             return v
            #         an = info.field_name
            #         ref_cls = c.attributes[an].constraints.ref
            #         if ref_cls and (ref_cls not in self.entities or str(v) not in self.entities[ref_cls]):
            #             raise ValueError(f"Relation '{an}': id '{v}' not found in '{ref_cls}'")
            #         return v
            #     setattr(mdl, "_check_refs", _check_refs)

            bases[cname] = mdl
            if not c.abstract:
                self.py_models[cname] = mdl

    ## Internal helper methods

    ### Type coercion & validation:
