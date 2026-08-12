"""validate_analysis.py — check a CESDM model file against one or more
analysis profiles (e.g. `optimal_dispatch`, `power_flow`), independent
of schema-level `model.validate()` completeness.

Usage
-----
    python tools/validate_analysis.py model.yaml --profile optimal_dispatch
    python tools/validate_analysis.py model.yaml --profile optimal_dispatch --profile power_flow
    python tools/validate_analysis.py output/pypsa_model/ --profile power_flow
    python tools/validate_analysis.py model.yaml --profile analysis_profiles/my_custom_profile.yaml
    python tools/validate_analysis.py model.yaml --profile optimal_dispatch --json

The model file's format is auto-detected from its path:

    <file>.yaml / <file>.yml        -- hierarchical or flat CESDM YAML
    <file>.xlsx                     -- Excel workbook (export_excel)
    <file>/datapackage.json         -- Frictionless Data Package (directory)
    <dir>/ containing datapackage.json -- same, pass the directory directly

`--profile` accepts a bare name (looked up as
`analysis_profiles/<name>.yaml`, relative to the current working
directory -- run this from the repo root, or pass a full path), a path
to a single profile file, or a path to a directory of profile files
(merged together, the same convention `import_library()` uses). Pass
`--profile` more than once to check several profiles in one run.

Exit codes: 0 if every profile passed with zero errors, 1 if at least
one profile found errors, 2 if the model/schema/profile itself
couldn't be loaded at all (a setup problem, not a validation result).

See docs/guide/10_analysis_validation.md for the full design of
analysis profiles and the `when:` conditional-check mechanism, and
analysis_profiles/ for the profiles this toolbox ships with.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cesdm_toolbox import build_model_from_yaml  # noqa: E402


def _load_model(model_path: Path, schema_dirs: list[str], *, strict_unknown: bool):
    """Auto-detect `model_path`'s format from its path and load it into
    a fresh model built from `schema_dirs`. Raises ValueError for an
    unrecognised format, or whatever the underlying import_* method
    raises for a malformed file."""
    model = build_model_from_yaml(schema_dirs if len(schema_dirs) > 1 else schema_dirs[0])

    if model_path.is_dir():
        if (model_path / "datapackage.json").is_file():
            model.import_frictionless(model_path)
        else:
            raise ValueError(
                f"{model_path} is a directory but contains no datapackage.json "
                f"-- pass a specific file instead (.yaml/.yml/.xlsx), or a "
                f"Frictionless Data Package directory"
            )
        return model

    suffix = model_path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        model.import_yaml_hierarchical(str(model_path), strict_unknown=strict_unknown)
    elif suffix == ".xlsx":
        model.import_excel(model_path, strict_unknown=strict_unknown)
    elif suffix == ".json" and model_path.name == "datapackage.json":
        model.import_frictionless(model_path.parent)
    else:
        raise ValueError(
            f"{model_path}: unrecognised model file format {suffix!r} -- "
            f"expected .yaml, .yml, .xlsx, or a datapackage.json"
        )
    return model


def _format_human(model_path: Path, results: dict[str, list[str]]) -> str:
    lines = [f"Model: {model_path}", ""]
    any_errors = False
    for profile_name, errors in results.items():
        if errors:
            any_errors = True
            lines.append(f"✗ {profile_name}: {len(errors)} issue(s)")
            for error in errors:
                lines.append(f"    - {error}")
        else:
            lines.append(f"✓ {profile_name}: ready")
        lines.append("")
    if not any_errors:
        lines.append("All profiles passed.")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check a CESDM model file against one or more analysis profiles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("model_path", type=Path, help="Path to the CESDM model file or Frictionless directory")
    parser.add_argument(
        "--profile", "-p", action="append", required=True, dest="profiles",
        help="Analysis profile: a bare name (analysis_profiles/<name>.yaml), or a path "
             "to a profile file/directory. Repeatable.",
    )
    parser.add_argument(
        "--schema", "-s", action="append", default=None, dest="schema_dirs",
        help="Schema directory to build the model from. Repeatable, to load an "
             "extension tree alongside the core one (e.g. -s schemas/cesdm "
             "-s schemas/agentbased). Default: schemas/cesdm.",
    )
    parser.add_argument(
        "--strict-unknown", action="store_true",
        help="Raise instead of silently skipping unknown classes/fields while importing the model.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Machine-readable JSON output.")
    args = parser.parse_args(argv)

    schema_dirs = args.schema_dirs or ["schemas/cesdm"]

    try:
        model = _load_model(args.model_path, schema_dirs, strict_unknown=args.strict_unknown)
    except Exception as e:
        print(f"Could not load {args.model_path}: {e}", file=sys.stderr)
        return 2

    results: dict[str, list[str]] = {}
    for profile in args.profiles:
        try:
            results[profile] = model.validate_for_analysis(profile)
        except Exception as e:
            print(f"Could not load analysis profile {profile!r}: {e}", file=sys.stderr)
            return 2

    if args.as_json:
        print(json.dumps(
            {
                "model": str(args.model_path),
                "results": {
                    name: {"valid": not errors, "errors": errors}
                    for name, errors in results.items()
                },
            },
            indent=2,
        ))
    else:
        print(_format_human(args.model_path, results), end="")

    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
