"""Generate editor-friendly ``.pyi`` stubs from CESDM schemas and APIs.

The generator combines:
* YAML schemas: entity/view inheritance, view families, attributes, relations.
* Python AST: public builder method signatures from ``BuildersMixin``.

Usage::

    python -m tools.generate_typings --schemas schemas/cesdm --output typings

The output can be referenced by Pyright's ``stubPath`` or copied into a wheel.
"""
from __future__ import annotations

import argparse
import ast
import keyword
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


TYPE_MAP = {
    "boolean": "bool",
    "bool": "bool",
    "integer": "int",
    "int": "int",
    "number": "float",
    "float": "float",
    "decimal": "float",
    "string": "str",
    "date": "date",
    "datetime": "datetime",
    "array": "list[Any]",
    "object": "dict[str, Any]",
}

# Every mixin that composes CesdmModel (cesdm/domain/model/core.py) and,
# transitively, the base ear.model.Model it also inherits from
# (ear/model/core.py) -- in the exact order each class declares its
# bases, so a name collision between two mixins (there are none today,
# but nothing guarantees that stays true) resolves the same way
# Python's actual MRO would: earlier in this list wins, matching
# "first occurrence wins" in the merge below.
#
# Deliberately covers the *entire* public surface, not just
# BuildersMixin -- extending this was the direct fix for the coverage
# gap found by actually running Pyright against real usage (see
# CHANGELOG.md): get_attribute_value, summary(), import_library(), and
# the raw EAR primitives (add_entity, add_attribute, add_relation)
# were all invisible to editors before this.
MIXIN_SOURCES: list[tuple[str, str]] = [
    ("cesdm/domain/model/discovery.py", "DiscoveryMixin"),
    ("cesdm/domain/model/hierarchical_yaml.py", "HierarchicalYamlMixin"),
    ("cesdm/domain/model/csv.py", "CsvMixin"),
    ("cesdm/domain/model/hdf5_parquet.py", "Hdf5ParquetMixin"),
    ("cesdm/domain/model/excel.py", "ExcelMixin"),
    ("cesdm/domain/model/frictionless.py", "FrictionlessMixin"),
    ("cesdm/domain/model/library.py", "LibraryMixin"),
    ("cesdm/domain/model/json_schema.py", "JsonSchemaMixin"),
    ("cesdm/domain/model/rdf_export.py", "RdfExportMixin"),
    ("cesdm/domain/model/accessors.py", "AccessorsMixin"),
    ("cesdm/domain/model/builders.py", "BuildersMixin"),
    ("cesdm/domain/model/statistics.py", "StatisticsMixin"),
    ("cesdm/domain/model/analysis_validation.py", "CesdmAnalysisValidationMixin"),
    ("ear/model/schema_loading.py", "SchemaLoadingMixin"),
    ("ear/model/entity_ops.py", "EntityOpsMixin"),
    ("ear/model/accessors.py", "AccessorsMixin"),
    ("ear/model/validation.py", "ValidationMixin"),
    ("ear/model/persistence_yaml_json.py", "PersistenceYamlJsonMixin"),
    ("ear/model/persistence_csv.py", "PersistenceCsvMixin"),
    ("ear/model/pydantic_export.py", "PydanticExportMixin"),
    ("ear/model/analysis_validation.py", "AnalysisValidationMixin"),
]

RETURN_OVERRIDES = {
    "ensure_carrier": "CarrierProxy",
    "ensure_resource": "NaturalResourceProxy",
    "ensure_technology": "GeneratorTypeProxy",
    "attach_profile": "ProfileProxy",
    "attach_availability_profile": "ProfileProxy",
    "attach_demand_profile": "ProfileProxy",
    "attach_natural_inflow_profile": "ProfileProxy",
    "attach_natural_inflow_profile": "ProfileProxy",
    "get_entity": "EntityProxy",
}


@dataclass
class ClassDef:
    name: str
    parents: list[str] = field(default_factory=list)
    attributes: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    view_family: str | None = None
    abstract: bool = False
    description: str = ""


@dataclass
class SchemaModel:
    classes: dict[str, ClassDef]
    attributes: dict[str, dict[str, Any]]
    relations: dict[str, dict[str, Any]]

    def ancestors(self, name: str) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()

        def walk(item: str) -> None:
            for parent in self.classes.get(item, ClassDef(item)).parents:
                if parent not in seen:
                    seen.add(parent)
                    walk(parent)
                    out.append(parent)

        walk(name)
        return out

    def inherited_family(self, name: str) -> str | None:
        current = self.classes.get(name)
        if current and current.view_family:
            return current.view_family
        for parent in reversed(self.ancestors(name)):
            value = self.classes.get(parent)
            if value and value.view_family:
                return value.view_family
        return None

    def inherited_members(self, name: str, member: str) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for cls_name in [*self.ancestors(name), name]:
            cls = self.classes.get(cls_name)
            if not cls:
                continue
            for entry in getattr(cls, member):
                if isinstance(entry, str):
                    entry = {"id": entry}
                if isinstance(entry, dict) and entry.get("id"):
                    base = self.relations.get(str(entry["id"]), {}) if member == "relations" else {}
                    merged[entry["id"]] = {**base, **entry}
        return list(merged.values())

    def is_subclass(self, child: str, parent: str) -> bool:
        return child == parent or parent in self.ancestors(child)


def safe_identifier(name: str) -> str:
    value = re.sub(r"\W", "_", name)
    if value[:1].isdigit():
        value = "_" + value
    if keyword.iskeyword(value):
        value += "_"
    return value


def python_class_name(schema_name: str, suffix: str = "") -> str:
    parts = re.split(r"[^A-Za-z0-9]+", schema_name)
    base = "".join(part[:1].upper() + part[1:] for part in parts if part)
    return f"{base}{suffix}"


def load_schema(schema_dir: Path) -> SchemaModel:
    classes: dict[str, ClassDef] = {}
    attributes: dict[str, dict[str, Any]] = {}
    relations: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.rglob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
        if not isinstance(raw, dict):
            continue
        if isinstance(raw.get("attributes"), dict) and "name" not in raw:
            for name, definition in raw["attributes"].items():
                attributes[name] = definition or {}
        if isinstance(raw.get("relations"), dict) and "name" not in raw:
            for name, definition in raw["relations"].items():
                relations[name] = definition or {}
        if raw.get("name"):
            name = str(raw["name"])
            classes[name] = ClassDef(
                name=name,
                parents=list(raw.get("parents") or []),
                attributes=list(raw.get("attributes") or []),
                relations=list(raw.get("relations") or []),
                view_family=raw.get("view_family"),
                abstract=bool(raw.get("abstract", False)),
                description=str(raw.get("description") or "").strip(),
            )
    return SchemaModel(classes=classes, attributes=attributes, relations=relations)


def load_default_library_classes(library_dir: Path) -> set[str]:
    classes: set[str] = set()
    if not library_dir.is_dir():
        return classes
    for path in sorted(library_dir.rglob("*.y*ml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict):
            for name, entities in raw.items():
                if name not in {"description", "version", "source"} and isinstance(entities, dict):
                    classes.add(str(name))
    return classes


def relation_targets(entry: dict[str, Any]) -> list[str]:
    return [str(v) for v in (entry.get("targets") or ([entry.get("target")] if entry.get("target") else []))]

def relation_input_type(entry: dict[str, Any], default_library_classes: set[str]) -> str:
    targets = relation_targets(entry)
    values: list[str] = []
    for target in targets:
        values.append(python_class_name(target, "Proxy"))
        values.append(python_class_name(target, "Id") if target in default_library_classes else "str")
    element = " | ".join(dict.fromkeys(values)) or "EntityProxy | str"
    return f"Iterable[{element}]" if relation_is_many(entry) else element


def attribute_type(model: SchemaModel, entry: dict[str, Any]) -> str:
    definition = model.attributes.get(str(entry.get("id")), {})
    value_def = definition.get("value") or {}
    raw_type = str(value_def.get("type") or "Any").lower()
    py_type = TYPE_MAP.get(raw_type, "Any")
    # belongsToGroup-tagged fields are conditionally required (enforced by
    # validate() only once something else from that same group is already
    # present), not unconditionally at construction/read time -- so these
    # are always Python-optional regardless of their schema `required`
    # value, the same treatment already applied to generated builder
    # signatures in generate_convenience_api.py. See CHANGELOG.md.
    if not entry.get("required", False) or entry.get("belongsToGroup"):
        py_type += " | None"
    return py_type


def relation_is_many(entry: dict[str, Any]) -> bool:
    cardinality = str(entry.get("cardinality") or "1")
    return "*" in cardinality or cardinality.endswith("..n")


def relation_type(entry: dict[str, Any]) -> str:
    targets = entry.get("targets") or ([entry.get("target")] if entry.get("target") else [])
    proxy_types = [python_class_name(str(target), "Proxy") for target in targets]
    target_type = " | ".join(dict.fromkeys(proxy_types)) or "EntityProxy"
    if relation_is_many(entry):
        result = f"list[{target_type}]"
    else:
        result = target_type
    if not entry.get("required", False):
        result += " | None"
    return result


def render_doc(text: str, indent: str = "    ") -> list[str]:
    clean = " ".join(text.split())
    if not clean:
        return []
    clean = clean.replace('"""', "'''")
    return [f'{indent}"""{clean}"""']


def render_proxy_base_stub() -> str:
    """ViewProxy/EntityProxy/FlatGroupViewProxy themselves -- these live
    in cesdm/proxy.py."""
    return "\n".join([
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "class ViewProxy:",
        "    @property",
        "    def id(self) -> str: ...",
        "    @property",
        "    def view_class(self) -> str: ...",
        "",
        "class FlatGroupViewProxy:",
        "    \"\"\"Namespace-alias view over an asset's own flattened",
        "    attributes/relations, filtered to whichever ones are tagged",
        "    belongsToGroup: <group_name> in the schema -- see cesdm/proxy.py.\"\"\"",
        "    @property",
        "    def id(self) -> str: ...",
        "    @property",
        "    def view_class(self) -> str: ...",
        "",
        "class EntityProxy(str):",
        "    @property",
        "    def id(self) -> str: ...",
        "    @property",
        "    def entity_class(self) -> str | None: ...",
        "    def get_attr_value(self, name: str, default: Any = ...) -> Any: ...",
        "    def get_relations(self, name: str) -> list[str]: ...",
        "    def get_relation(self, name: str, default: Any = ...) -> Any: ...",
        "    def connect(self, *nodes: str) -> EntityProxy: ...",
        "    def add_attribute(self, attribute_id: str, value: Any, *, unit: str | None = ..., provenance_ref: str | None = ...) -> EntityProxy: ...",
        "    def add_relation(self, relation_id: str, target_entity_id: Any, **kwargs: Any) -> EntityProxy: ...",
        "",
    ]) + "\n"


def render_generated_proxies_stub(model: SchemaModel, default_library_classes: set[str]) -> str:
    """Every per-entity-class proxy subclass (DemandUnitProxy,
    GenerationUnitProxy, ...) -- these live in cesdm/generated_proxies.py,
    a *separate* runtime module from cesdm/proxy.py (where only the base
    ViewProxy/EntityProxy classes are defined). Declaring these classes in
    proxy.pyi instead of their own generated_proxies.pyi was a real bug:
    `from cesdm.generated_proxies import DemandUnitProxy` (the actual,
    correct import path -- it's what cesdm.proxy._entity_proxy() itself
    uses) would resolve against the real, type-annotation-free runtime
    module instead of any enriched stub, silently giving up all typing
    for `.dispatch` etc. on every single generated proxy class -- caught
    by testing a deliberate typo with Pyright and finding it wasn't
    flagged, not by reading the generator's code. See CHANGELOG.md.

    `.dispatch`/`.topology`/`.powerflow`/etc. properties are generated
    from belongsToGroup-tagged attributes/relations declared directly on
    the asset's own class, not from separate view classes with a
    view_family (there are no more of those at all -- see CHANGELOG.md:
    this toolbox's "initial version without views"). For every group an
    asset class has at least one tagged field for, a dedicated stub class
    is generated (FlatGroupViewProxyStub-style: just that group's own
    fields), matching what cesdm.proxy.FlatGroupViewProxy actually
    exposes at runtime.
    """
    lines = [
        "from __future__ import annotations",
        "",
        "from datetime import date, datetime",
        "from typing import Any, Iterable",
        "from cesdm.proxy import EntityProxy, FlatGroupViewProxy",
        "from cesdm.default_library import *",
        "",
    ]

    def group_members(cls_name: str, member: str) -> dict[str, list[dict[str, Any]]]:
        by_group: dict[str, list[dict[str, Any]]] = {}
        for entry in model.inherited_members(cls_name, member):
            for grp in entry.get("belongsToGroup") or []:
                by_group.setdefault(grp, []).append(entry)
        return by_group

    # First pass: generate one dedicated stub class per (asset class,
    # group) pair that actually has tagged fields.
    group_stub_names: dict[tuple[str, str], str] = {}
    for cls in sorted(model.classes.values(), key=lambda item: item.name):
        if cls.abstract:
            continue
        attr_groups = group_members(cls.name, "attributes")
        rel_groups = group_members(cls.name, "relations")
        all_groups = sorted(set(attr_groups) | set(rel_groups))
        for grp in all_groups:
            group_camel = "".join(part.capitalize() for part in grp.split("_"))
            stub_name = f"{python_class_name(cls.name)}{group_camel}Proxy"
            group_stub_names[(cls.name, grp)] = stub_name
            lines.append(f"class {stub_name}(FlatGroupViewProxy):")
            wrote = False
            for entry in attr_groups.get(grp, []):
                attr = safe_identifier(str(entry["id"]))
                lines.append(f"    {attr}: {attribute_type(model, entry)}")
                wrote = True
            for entry in rel_groups.get(grp, []):
                rel = safe_identifier(str(entry["id"]))
                getter_type = relation_type(entry)
                setter_type = relation_input_type(entry, default_library_classes)
                lines.append("    @property")
                lines.append(f"    def {rel}(self) -> {getter_type}: ...")
                lines.append(f"    @{rel}.setter")
                lines.append(f"    def {rel}(self, value: {setter_type}) -> None: ...")
                wrote = True
            if not wrote:
                lines.append("    pass")
            lines.append("")

    for cls in sorted(model.classes.values(), key=lambda item: item.name):
        proxy_name = python_class_name(cls.name, "Proxy")
        lines.append(f"class {proxy_name}(EntityProxy):")

        own_groups = sorted({
            grp for (cname, grp) in group_stub_names
            if cname == cls.name or model.is_subclass(cls.name, cname)
        })
        for grp in own_groups:
            # A subclass may redeclare the same group with more fields
            # than an ancestor (e.g. HydroGenerationUnit adding to
            # GenerationUnit's "dispatch") -- the most specific class
            # that actually has this group wins.
            owning_cls = cls.name
            if (cls.name, grp) not in group_stub_names:
                for ancestor in model.ancestors(cls.name):
                    if (ancestor, grp) in group_stub_names:
                        owning_cls = ancestor
                        break
            stub_name = group_stub_names[(owning_cls, grp)]
            lines.append(f"    {safe_identifier(grp)}: {stub_name}")

        wrote_member = bool(own_groups)
        for entry in model.inherited_members(cls.name, "attributes"):
            attr = safe_identifier(str(entry["id"]))
            lines.append(f"    {attr}: {attribute_type(model, entry)}")
            definition = model.attributes.get(str(entry["id"]), {})
            description = str(definition.get("description") or "")
            unit_enum = (((definition.get("unit") or {}).get("constraints") or {}).get("enum") or [])
            if unit_enum:
                description = f"{description} Unit: {', '.join(map(str, unit_enum))}."
            lines.extend(render_doc(description))
            wrote_member = True
        for entry in model.inherited_members(cls.name, "relations"):
            rel = safe_identifier(str(entry["id"]))
            getter_type = relation_type(entry)
            setter_type = relation_input_type(entry, default_library_classes)
            lines.append("    @property")
            lines.append(f"    def {rel}(self) -> {getter_type}: ...")
            lines.append(f"    @{rel}.setter")
            lines.append(f"    def {rel}(self, value: {setter_type}) -> None: ...")
            wrote_member = True
        if not wrote_member:
            lines.append("    pass")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def unparse_annotation(node: ast.expr | None) -> str:
    if node is None:
        return "Any"
    return ast.unparse(node)


def format_arg(arg: ast.arg, default: ast.expr | None = None) -> str:
    annotation = unparse_annotation(arg.annotation)
    result = f"{arg.arg}: {annotation}"
    if default is not None:
        result += " = ..."
    return result


def extract_methods(path: Path, class_name: str) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for fn in node.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if fn.name.startswith("_"):
                continue
            args = fn.args
            parts: list[str] = []
            positional = list(args.posonlyargs) + list(args.args)
            defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
            for index, (arg, default) in enumerate(zip(positional, defaults)):
                if index == 0 and arg.arg == "self":
                    parts.append("self")
                else:
                    parts.append(format_arg(arg, default))
            if args.vararg:
                parts.append(f"*{args.vararg.arg}: {unparse_annotation(args.vararg.annotation)}")
            elif args.kwonlyargs:
                parts.append("*")
            for arg, default in zip(args.kwonlyargs, args.kw_defaults):
                parts.append(format_arg(arg, default))
            if args.kwarg:
                parts.append(f"**{args.kwarg.arg}: {unparse_annotation(args.kwarg.annotation)}")
            ret = RETURN_OVERRIDES.get(fn.name, unparse_annotation(fn.returns))
            signature = f"    def {fn.name}({', '.join(parts)}) -> {ret}: ..."
            result.append((fn.name, signature))
    return sorted(result)


def render_model_stub(source_root: Path, model: SchemaModel) -> str:
    imports: set[str] = set()
    for value in RETURN_OVERRIDES.values():
        # A RETURN_OVERRIDES value can be a compound type expression, not
        # just a bare class name (e.g. add_reservoir_hydro's real return
        # is a tuple of two proxies: "tuple[HydraulicStorageUnitProxy,
        # HydroGenerationUnitProxy]") -- extracting every *Proxy
        # identifier found within it, rather than only handling the
        # bare-identifier case, avoids silently emitting the whole
        # expression string as an "import name" (invalid syntax: you
        # can't import "tuple[X, Y]").
        imports.update(re.findall(r"\b\w+Proxy\b", value))
    imports.add("EntityProxy")
    # Every concrete class needs its proxy name importable too, for
    # add_entity()'s per-class @overload declarations below.
    for cls in model.classes.values():
        if not cls.abstract:
            imports.add(python_class_name(cls.name, "Proxy"))
    lines = [
        "from __future__ import annotations",
        "",
        "from typing import Any, ClassVar, Dict, List, Literal, Optional, TypeVar, Union, overload",
        "from pathlib import Path",
        "from ear.entity import Entity",
        "from ear.entity_class import EntityClass",
        "from ear.schema_manifest import SchemaManifest",
        "from cesdm.proxy import EntityProxy",
        "from cesdm.generated_proxies import (",
        *[f"    {name}," for name in sorted(imports - {"EntityProxy"})],
        ")",
        "",
        # Generic methods (e.g. get_entity_as(entity_id, cls: type[_T]) -> _T)
        # use this bound TypeVar -- declared here so Pyright can actually
        # resolve them instead of silently falling back to Unknown/Any
        # for an undefined name (which "succeeds" with 0 errors while
        # providing zero real type-checking at all -- worse than an
        # honest error, since it looks like it's working).
        "_T = TypeVar(\"_T\", bound=EntityProxy)",
        "",
        "class CesdmModel:",
        "    classes: Dict[str, EntityClass]",
        "    entities: Dict[str, Dict[str, Entity]]",
        "    inheritance: Dict[str, Union[str, List[str], None]]",
        "    schema_manifest: SchemaManifest",
    ]
    # First-occurrence-wins merge across every mixin, processed in
    # MIXIN_SOURCES' declared order -- which matches CesdmModel's (and
    # the base Model's) actual MRO, so a genuine name collision between
    # two mixins resolves the stub the same way Python would resolve
    # the real attribute lookup.
    merged: dict[str, str] = {}
    for rel_path, class_name in MIXIN_SOURCES:
        path = source_root / rel_path
        if not path.is_file():
            continue
        for name, signature in extract_methods(path, class_name):
            if name not in merged:
                merged[name] = signature

    # add_entity() gets @overload'd per concrete class (Literal["GenerationUnit"]
    # -> GenerationUnitProxy, etc.) instead of using its single, generic
    # extracted signature -- so `model.add_entity("GenerationUnit", id)`
    # infers the specific proxy type directly, the same way get_entity_as()
    # requires an explicit cast for. Asked directly why this couldn't
    # "just happen" on add_entity() itself: it can, with this. See
    # CHANGELOG.md.
    #
    # The final fallback overload's entity_class stays a bare `str`,
    # deliberately -- tried tightening it to a closed Literal union of
    # every class name this generator knows about, and confirmed
    # directly that it breaks real, currently-supported extensibility:
    # schemas/agentbased/'s own classes (e.g. "Canton") aren't in that
    # union at all, since this generator only ever reads the one
    # `--schemas` tree passed to it (schemas/cesdm by default); neither
    # is any class a user adds via their own schema extension (e.g.
    # examples/example_schema_extension.py's "ElectricVehicleChargingStation"),
    # by definition -- CESDM's whole extensibility story is that a new
    # schema class needs no toolbox code change, and a closed union
    # here would quietly contradict that for exactly the classes that
    # matter most. A misspelled class name silently resolving to the
    # generic EntityProxy (rather than being flagged) is the accepted
    # cost of keeping that door open.
    if "add_entity" in merged:
        overload_lines = []
        for cls in sorted(model.classes.values(), key=lambda c: c.name):
            if cls.abstract:
                continue
            proxy_name = python_class_name(cls.name, "Proxy")
            overload_lines.append("    @overload")
            overload_lines.append(
                f'    def add_entity(self, entity_class: Literal["{cls.name}"], entity_id: str) -> {proxy_name}: ...'
            )
        overload_lines.append("    @overload")
        overload_lines.append(merged["add_entity"])
        merged["add_entity"] = "\n".join(overload_lines)

    # ensure_entity() takes the class name explicitly too (create-if-
    # missing + set initial attributes via **kwargs in one call), so it
    # gets the exact same per-class @overload treatment as add_entity()
    # above, for the exact same reason -- confirmed directly: without
    # this, `model.ensure_entity("GenerationUnit", id, name=...)` only
    # type-checked as the generic EntityProxy, so `.dispatch`/`.name`
    # etc. on the object it returns failed Pyright with
    # reportAttributeAccessIssue -- exactly the gap that made
    # `docs/getting_started.md`'s and the README's own quickstart
    # examples fail type-checking despite being the first thing a new
    # user is shown.
    if "ensure_entity" in merged:
        overload_lines = []
        for cls in sorted(model.classes.values(), key=lambda c: c.name):
            if cls.abstract:
                continue
            proxy_name = python_class_name(cls.name, "Proxy")
            overload_lines.append("    @overload")
            overload_lines.append(
                f'    def ensure_entity(self, class_name: Literal["{cls.name}"], entity_id: str, **attributes: Any) -> {proxy_name}: ...'
            )
        overload_lines.append("    @overload")
        overload_lines.append(merged["ensure_entity"])
        merged["ensure_entity"] = "\n".join(overload_lines)

    lines.extend(merged[name] for name in sorted(merged))
    lines.append("")
    return "\n".join(lines)


def write_output(schema_dir: Path, source_root: Path, output: Path) -> None:
    model = load_schema(schema_dir)
    default_library_classes = load_default_library_classes(source_root / "library/default_library")
    package = output / "cesdm"
    model_package = package / "domain" / "model"
    model_package.mkdir(parents=True, exist_ok=True)

    (package / "proxy.pyi").write_text(render_proxy_base_stub(), encoding="utf-8")
    (package / "generated_proxies.pyi").write_text(
        render_generated_proxies_stub(model, default_library_classes), encoding="utf-8")
    (model_package / "core.pyi").write_text(render_model_stub(source_root, model), encoding="utf-8")

    # cesdm/default_library.py is itself a fully-typed, auto-generated
    # module (Literal type aliases + Final class constants) -- mirrored
    # directly as its own .pyi rather than re-derived, so the stub can
    # never drift from the real module's actual literal values.
    default_library_py = source_root / "cesdm" / "default_library.py"
    if default_library_py.is_file():
        (package / "default_library.pyi").write_text(
            default_library_py.read_text(encoding="utf-8"), encoding="utf-8")

    (model_package / "__init__.pyi").write_text(
        "from cesdm.domain.model.core import CesdmModel as CesdmModel\n"
        "__all__ = [\"CesdmModel\"]\n",
        encoding="utf-8",
    )
    (package / "domain" / "__init__.pyi").write_text("", encoding="utf-8")
    (package / "helpers.pyi").write_text(
        "from pathlib import Path\n"
        "from typing import Sequence, Union\n"
        "from cesdm.domain.model import CesdmModel\n\n"
        "def build_model_from_yaml(schema_path: Union[str, Path, Sequence[Union[str, Path]]]) -> CesdmModel: ...\n",
        encoding="utf-8",
    )
    (package / "__init__.pyi").write_text(
        "from cesdm.domain.model import CesdmModel as CesdmModel\n"
        "from cesdm.helpers import build_model_from_yaml as build_model_from_yaml\n"
        "from cesdm.default_library import CarrierDomains as CarrierDomains, Carriers as Carriers, GeneratorTypes as GeneratorTypes, NaturalResources as NaturalResources, StorageTypes as StorageTypes\n"
        "__all__ = [\"CesdmModel\", \"build_model_from_yaml\", \"Carriers\", \"GeneratorTypes\", \"NaturalResources\", \"StorageTypes\"]\n",
        encoding="utf-8",
    )
    (output / "cesdm_toolbox.pyi").write_text(
        "from cesdm import CesdmModel as CesdmModel\n"
        "from cesdm import build_model_from_yaml as build_model_from_yaml\n"
        "__all__ = [\"CesdmModel\", \"build_model_from_yaml\"]\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schemas", type=Path, default=Path("schemas/cesdm"))
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("typings"))
    args = parser.parse_args(argv)
    write_output(args.schemas, args.source_root, args.output)
    print(f"Generated CESDM stubs in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
