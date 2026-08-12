"""Generate CESDM's per-class proxy subclasses (cesdm/generated_proxies.py).

Each concrete schema class gets its own EntityProxy subclass
(DemandUnitProxy, GenerationUnitProxy, ...), mirroring the schema's own
inheritance chain -- this is what `model.get_entity(entity_id)` wraps an
entity id in (see cesdm/domain/model/builders.py), and what
`cesdm/generated_proxies.pyi` (see tools/generate_typings.py) adds
`.dispatch`/`.power_flow`/etc. type annotations onto.

This is the only thing this module generates. There is no
add_<entity>() convenience-constructor generation any more
(GeneratedBuildersMixin, cesdm/domain/model/generated_builders.py) --
removed entirely, requested directly. Building a model uses core EAR
calls (`add_entity`/`add_attribute`/`add_relation`) plus the object-
oriented proxy layer for reading/writing afterward; see
docs/getting_started.md.

Run after schema changes::

    cesdm-generate-api
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

from cesdm.helpers import build_model_from_yaml


def python_class_name(schema_name: str, suffix: str = "") -> str:
    parts = re.split(r"[^A-Za-z0-9]+", schema_name)
    base = "".join(part[:1].upper() + part[1:] for part in parts if part)
    return f"{base}{suffix}"


def render_proxies(schema_dir: Path) -> str:
    model = build_model_from_yaml(schema_dir)
    lines = [
        '"""AUTO-GENERATED CESDM proxy subclasses.\n\nDo not edit manually. Run ``cesdm-generate-api`` after schema changes.\n"""',
        'from __future__ import annotations',
        '',
        'from cesdm.proxy import EntityProxy',
        '',
    ]
    emitted: set[str] = set()

    def emit(class_name: str) -> None:
        proxy_name = python_class_name(class_name, 'Proxy')
        if proxy_name in emitted:
            return
        class_def = model.classes[class_name]
        parents = [p for p in getattr(class_def, 'parents', []) if p in model.classes]
        for parent in parents:
            emit(parent)
        bases = [python_class_name(parent, 'Proxy') for parent in parents]
        if not bases:
            bases = ['EntityProxy']
        emitted.add(proxy_name)
        lines.extend([
            f'class {proxy_name}({", ".join(bases)}):',
            f'    """Proxy for CESDM entity class ``{class_name}``."""',
            '    pass',
            '',
        ])

    for class_name in sorted(model.classes):
        emit(class_name)
    return '\n'.join(lines).rstrip() + '\n'


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
    return True


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schemas", type=Path, default=Path("schemas/cesdm"))
    parser.add_argument("--proxy-output", type=Path, default=Path("cesdm/generated_proxies.py"))
    args = parser.parse_args(argv)
    proxies_changed = write_if_changed(args.proxy_output, render_proxies(args.schemas))
    print(("Generated" if proxies_changed else "Already up to date:") + f" {args.proxy_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
