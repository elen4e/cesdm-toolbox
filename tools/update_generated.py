"""Regenerate concrete convenience API methods, editor typings, and the
generated schema HTML reference."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from tools.generate_default_library import main as generate_default_library
from tools.generate_convenience_api import main as generate_api
from tools.generate_typings import main as generate_typings
from tools.generate_cesdm_schema_html import main as generate_schema_html


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schemas", type=Path, default=Path("schemas/cesdm"))
    parser.add_argument("--library", type=Path, default=Path("library/default_library"))
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--proxy-output", type=Path, default=Path("cesdm/generated_proxies.py"))
    parser.add_argument("--typings-output", type=Path, default=Path("typings"))
    parser.add_argument("--schema-html-output", type=Path,
                         default=Path("docs/reference/schema-reference.html"))
    args = parser.parse_args(argv)
    result = generate_default_library([
        "--library", str(args.library),
        "--output", "cesdm/default_library.py",
        "--stub-output", str(args.typings_output / "cesdm/default_library.pyi"),
    ])
    if result:
        return result
    result = generate_api(["--schemas", str(args.schemas), "--proxy-output", str(args.proxy_output)])
    if result:
        return result
    result = generate_typings(["--schemas", str(args.schemas), "--source-root", str(args.source_root), "--output", str(args.typings_output)])
    if result:
        return result
    generate_schema_html([str(args.schemas), str(args.schema_html_output)])
    # Keep underscore alias in sync (older docs / CONTRIBUTING links).
    alias = Path("docs/reference/schema_reference.html")
    if args.schema_html_output.resolve() != alias.resolve():
        alias.write_bytes(args.schema_html_output.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
