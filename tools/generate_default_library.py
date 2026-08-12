"""Generate runtime and typing helpers for the CESDM default library."""
from __future__ import annotations

import argparse
import keyword
import re
from pathlib import Path
from typing import Any, Iterable

import yaml


def python_class_name(name: str, suffix: str = "") -> str:
    parts = re.split(r"[^A-Za-z0-9]+", name)
    base = "".join(part[:1].upper() + part[1:] for part in parts if part)
    return f"{base}{suffix}"


def constant_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper() or "VALUE"
    if name[0].isdigit():
        name = f"VALUE_{name}"
    if keyword.iskeyword(name.lower()):
        name += "_"
    return name


def load_default_library(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for part in sorted(path.rglob("*.y*ml")):
        raw = yaml.safe_load(part.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            continue
        for class_name, entities in raw.items():
            if class_name in {"description", "version", "source"} or not isinstance(entities, dict):
                continue
            bucket = result.setdefault(str(class_name), {})
            overlap = set(bucket) & set(entities)
            if overlap:
                raise ValueError(f"Duplicate default-library ids in {part}: {sorted(overlap)}")
            for entity_id, definition in entities.items():
                bucket[str(entity_id)] = dict(definition or {})
    return result


def render_runtime(library: dict[str, dict[str, dict[str, Any]]]) -> str:
    lines = [
        '"""AUTO-GENERATED CESDM default-library registry.\n\nDo not edit manually. Run ``cesdm-update-generated``.\n"""',
        "from __future__ import annotations",
        "",
        "from typing import Final, Literal, TypeAlias",
        "",
    ]
    for class_name, entities in sorted(library.items()):
        alias = python_class_name(class_name, "Id")
        values = sorted(entities)
        literal = ", ".join(repr(v) for v in values) or "str"
        lines.append(f"{alias}: TypeAlias = Literal[{literal}]")
    lines.append("")
    for class_name, entities in sorted(library.items()):
        container = python_class_name(class_name, "s")
        alias = python_class_name(class_name, "Id")
        lines.append(f"class {container}:")
        if not entities:
            lines.append("    pass")
        used: set[str] = set()
        for entity_id in sorted(entities):
            name = constant_name(entity_id)
            base = name
            index = 2
            while name in used:
                name = f"{base}_{index}"
                index += 1
            used.add(name)
            lines.append(f"    {name}: Final[{alias}] = {entity_id!r}")
        lines.append("")
    lines.append("DEFAULT_LIBRARY_ENTITIES: Final[dict[str, dict[str, dict[str, object]]]] = " + repr(library))
    lines.append("DEFAULT_LIBRARY_IDS_BY_CLASS: Final[dict[str, frozenset[str]]] = {")
    for class_name, entities in sorted(library.items()):
        lines.append(f"    {class_name!r}: frozenset({sorted(entities)!r}),")
    lines.append("}")
    lines.append("DEFAULT_LIBRARY_CLASS_BY_ID: Final[dict[str, str]] = {")
    for class_name, entities in sorted(library.items()):
        for entity_id in sorted(entities):
            lines.append(f"    {entity_id!r}: {class_name!r},")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def render_stub(library: dict[str, dict[str, dict[str, Any]]]) -> str:
    lines = [
        "from typing import Final, Literal, TypeAlias",
        "",
    ]
    for class_name, entities in sorted(library.items()):
        alias = python_class_name(class_name, "Id")
        values = sorted(entities)
        literal = ", ".join(repr(v) for v in values) or "str"
        lines.append(f"{alias}: TypeAlias = Literal[{literal}]")
    lines.append("")
    for class_name, entities in sorted(library.items()):
        container = python_class_name(class_name, "s")
        alias = python_class_name(class_name, "Id")
        lines.append(f"class {container}:")
        if not entities:
            lines.append("    pass")
        used: set[str] = set()
        for entity_id in sorted(entities):
            name = constant_name(entity_id)
            base = name
            index = 2
            while name in used:
                name = f"{base}_{index}"
                index += 1
            used.add(name)
            lines.append(f"    {name}: Final[{alias}]")
        lines.append("")
    lines.extend([
        "DEFAULT_LIBRARY_ENTITIES: Final[dict[str, dict[str, dict[str, object]]]]",
        "DEFAULT_LIBRARY_IDS_BY_CLASS: Final[dict[str, frozenset[str]]]",
        "DEFAULT_LIBRARY_CLASS_BY_ID: Final[dict[str, str]]",
        "",
    ])
    return "\n".join(lines)


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def validate_against_schema(library: dict[str, dict[str, dict[str, Any]]], schema_dir: Path) -> None:
    """Check every attribute/relation id used in the library source
    against the real schema, before generating anything. Catches
    authoring mistakes (a typo'd attribute id, or one that belongs on a
    different entity class -- e.g. a per-asset dispatch attribute
    mistakenly given as a technology-template default) at generation
    time, with every offending entry listed at once, instead of a
    confusing runtime KeyError the first time some unrelated caller
    happens to instantiate that specific library entity via
    ensure_default_library_entity(). Found two real instances of this
    exact class of bug in GeneratorType.yaml ('label' instead of
    'long_name'; 'minimum_generation', which only exists on
    Generation.DispatchView, not GeneratorType) by testing the library
    against real code, not by reading the source. See CHANGELOG.md.
    """
    from cesdm_toolbox import build_model_from_yaml

    model = build_model_from_yaml(str(schema_dir))
    errors: list[str] = []
    for class_name, entities in library.items():
        valid_attrs = set(model.class_attributes(class_name) or [])
        valid_rels = set(model.class_relations(class_name) or [])
        for entity_id, entry in entities.items():
            for attr in entry.get("attributes", []):
                if attr["id"] not in valid_attrs:
                    errors.append(
                        f"{class_name}:{entity_id}: attribute {attr['id']!r} is not "
                        f"a valid {class_name} attribute"
                    )
            for rel in entry.get("relations", []):
                if rel["id"] not in valid_rels:
                    errors.append(
                        f"{class_name}:{entity_id}: relation {rel['id']!r} is not "
                        f"a valid {class_name} relation"
                    )
    if errors:
        raise ValueError(
            f"{len(errors)} invalid attribute/relation id(s) in the default "
            f"library source (fix the YAML under --library, not the generated "
            f"output):\n  " + "\n  ".join(errors)
        )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=Path("library/default_library"))
    parser.add_argument("--schemas", type=Path, default=Path("schemas/cesdm"))
    parser.add_argument("--output", type=Path, default=Path("cesdm/default_library.py"))
    parser.add_argument("--stub-output", type=Path, default=Path("typings/cesdm/default_library.pyi"))
    parser.add_argument("--skip-validation", action="store_true",
                        help="Skip cross-checking library attribute/relation ids "
                             "against the schema (not recommended).")
    args = parser.parse_args(argv)
    library = load_default_library(args.library)
    if not args.skip_validation:
        validate_against_schema(library, args.schemas)
    write_if_changed(args.output, render_runtime(library))
    write_if_changed(args.stub_output, render_stub(library))
    print(f"Generated {args.output} and {args.stub_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
