"""
schema_audit.py — cross-references the CESDM schema tree against actual
usage in examples/, tests/, tools/, and the ear/cesdm library source, to
surface maturity gaps that are otherwise only found by accident:

1. Dead relations/attributes: declared in the central registry, never
   used anywhere.
2. Orphaned classes: concrete classes never instantiated anywhere.
3. Misapplied-generality relations: declared on a base class, but only
   ever exercised on one specific (strict-descendant) subclass — see
   StorageUnit.storesResource, CHANGELOG.md 0.4.0/revert.
4. `stable`-tier classes with zero usage evidence: the stability tier
   is currently a location-based claim (SCHEMA_MANIFEST.yaml), not a
   measured one; this surfaces where that claim isn't backed by any
   example/test exercising the class.

Usage:
    python tools/schema_audit.py [schema_dir] [output.md]

Both arguments are optional; defaults are ./schemas/cesdm and
docs/architecture/schema_audit_report.md.

IMPORTANT — this is a static, best-effort AST scan, not a sound
analysis. It only sees `add_entity(class, id)` / `add_relation(id, rel,
target)` / `add_attribute(id, attr, value)` calls where the relevant
argument is a **literal string**. Calls using a computed/variable class
or field name are invisible to it. Section 4 in particular has a
documented, verified false positive (`hasInputResource`) caused by
exactly this limitation — always check a finding against the actual
library source in cesdm/ and ear/ before acting on it, not just this
report. Re-run this after any schema or example/test change; findings
will drift as coverage changes.
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys
from collections import defaultdict

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml

from cesdm_toolbox import build_model_from_yaml

# ---------------------------------------------------------------------------
# 1. Raw schema scan: own-declared (unmerged) relations/attributes per class,
#    read directly from YAML rather than through the model, since
#    Model.classes[...] holds the *merged* (post-inheritance) view.
# ---------------------------------------------------------------------------

EXEMPT_FILENAMES = {"attributes.yaml", "relations.yaml", "SCHEMA_MANIFEST.yaml"}


def iter_class_files(schema_root: pathlib.Path):
    for f in sorted(schema_root.rglob("*.y*ml")):
        if f.name in EXEMPT_FILENAMES or f.name.startswith("_"):
            continue
        yield f


def own_declared(schema_root: pathlib.Path) -> dict:
    """Returns {class_name: {"file", "parents", "abstract", "own_relations",
    "own_attributes"}} read directly from each class's own YAML file."""
    out = {}
    for f in iter_class_files(schema_root):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "name" not in data:
            continue
        name = data["name"]
        parents = data.get("parents") or []
        if isinstance(parents, str):
            parents = [parents]
        own_rel = data.get("relations") or []
        own_attr = data.get("attributes") or []
        rel_ids = [r["id"] for r in own_rel if isinstance(r, dict) and "id" in r]
        attr_ids = [a["id"] for a in own_attr if isinstance(a, dict) and "id" in a]
        out[name] = {
            "file": f,
            "parents": parents,
            "abstract": bool(data.get("abstract", False)),
            "own_relations": rel_ids,
            "own_attributes": attr_ids,
        }
    return out


# ---------------------------------------------------------------------------
# 2. Usage scan: AST-based, over two different scopes (see module docstring
#    and SCAN_DIRS_FOR_DEAD_CODE / CLASS_ATTRIBUTION_DIRS below).
# ---------------------------------------------------------------------------

# Dead-code detection must cover the library source too -- a lot of real
# relation/attribute setting happens generically inside builder methods
# (e.g. create_generation_unit sets hasInputResource for every generator, not
# just hydro ones), not only at examples/tests call sites.
SCAN_DIRS_FOR_DEAD_CODE = ["examples", "tests", "tools", "ear", "cesdm"]

# Class-attribution (which class was a relation/attribute actually set on --
# used for the "misapplied generality" check) stays scoped to examples/tests:
# library code almost always uses a variable entity id (a function
# parameter), not a literal, so it can't be attributed to a specific class
# by this lightweight a static scan. Findings from this scope alone can
# still be false positives if the same relation is ALSO set generically
# inside a builder method for other subclasses/siblings -- always check the
# library source before trusting a "misapplied generality" finding.
CLASS_ATTRIBUTION_DIRS = ["examples", "tests"]


class UsageVisitor(ast.NodeVisitor):
    def __init__(self):
        self.entity_class_of = {}  # per-file entity_id -> class_name, reset per file
        self.instantiated_classes = set()
        self.used_relations = set()
        self.used_attributes = set()
        self.relation_usage_by_class = defaultdict(set)
        self.attribute_usage_by_class = defaultdict(set)
        self.class_instantiation_files = defaultdict(set)
        # String keys of any dict literal anywhere in the scanned files --
        # catches the common `for attr, val in {"x": 1}.items():
        # add_attribute(id, attr, val)` pattern, where the id is a loop
        # variable at the call site (invisible to the direct-literal scan)
        # but a literal at its source.
        self.dict_literal_keys = set()
        self._current_file = None

    def _literal(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit_Dict(self, node):
        for k in node.keys:
            lit = self._literal(k) if k is not None else None
            if lit:
                self.dict_literal_keys.add(lit)
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = None
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id

        args = node.args
        if func_name == "add_entity" and len(args) >= 2:
            cls = self._literal(args[0])
            eid = self._literal(args[1])
            if cls:
                self.instantiated_classes.add(cls)
                self.class_instantiation_files[cls].add(self._current_file)
            if cls and eid:
                self.entity_class_of[eid] = cls
        elif func_name == "add_relation" and len(args) >= 3:
            eid = self._literal(args[0])
            rel = self._literal(args[1])
            if rel:
                self.used_relations.add(rel)
                cls = self.entity_class_of.get(eid)
                if cls:
                    self.relation_usage_by_class[rel].add(cls)
        elif func_name == "add_attribute" and len(args) >= 3:
            eid = self._literal(args[0])
            attr = self._literal(args[1])
            if attr:
                self.used_attributes.add(attr)
                cls = self.entity_class_of.get(eid)
                if cls:
                    self.attribute_usage_by_class[attr].add(cls)

        self.generic_visit(node)


def scan_usage(repo_root: pathlib.Path, scan_dirs):
    visitor = UsageVisitor()
    files_scanned = 0
    files_failed = []
    for d in scan_dirs:
        base = repo_root / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            visitor._current_file = str(f.relative_to(repo_root))
            visitor.entity_class_of = {}  # reset symbol table per file
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
                visitor.visit(tree)
                files_scanned += 1
            except SyntaxError as e:
                files_failed.append((str(f), str(e)))
    return visitor, files_scanned, files_failed


def scan_usage_combined(repo_root: pathlib.Path):
    """Two-pass scan: dead-code signals come from the broad scan (including
    library source); class-attribution signals come from the narrower
    examples+tests scan only. See module docstring."""
    broad, n_broad, failed_broad = scan_usage(repo_root, SCAN_DIRS_FOR_DEAD_CODE)
    narrow, _, failed_narrow = scan_usage(repo_root, CLASS_ATTRIBUTION_DIRS)

    combined = UsageVisitor()
    combined.used_relations = broad.used_relations
    combined.used_attributes = broad.used_attributes
    combined.dict_literal_keys = broad.dict_literal_keys
    combined.instantiated_classes = narrow.instantiated_classes
    combined.relation_usage_by_class = narrow.relation_usage_by_class
    combined.attribute_usage_by_class = narrow.attribute_usage_by_class
    combined.class_instantiation_files = narrow.class_instantiation_files

    return combined, n_broad, failed_broad + failed_narrow


# ---------------------------------------------------------------------------
# 3. Report generation
# ---------------------------------------------------------------------------

def build_report(schema_dir: pathlib.Path) -> str:
    model = build_model_from_yaml(str(schema_dir))
    decl = own_declared(schema_dir)
    usage, n_files, failed = scan_usage_combined(REPO_ROOT)

    lines: list[str] = []

    def p(s: str = ""):
        lines.append(s)

    p("# CESDM schema audit report")
    p()
    p(f"Scanned {n_files} Python files for dead-code detection (examples/, tests/, "
      f"tools/, and the library source itself under ear/ and cesdm/ -- a lot of real "
      f"relation/attribute setting happens generically inside builder methods, not "
      f"just at example call sites). Class-attribution findings (section 4) are "
      f"scoped to examples/ and tests/ only -- see the caveat there. "
      f"{len(failed)} file(s) failed to parse.")
    try:
        schema_dir_display = schema_dir.relative_to(REPO_ROOT)
    except ValueError:
        schema_dir_display = schema_dir
    p(f"Schema tree: {len(model.classes)} classes loaded from {schema_dir_display}.")
    p()
    p("Method: static AST scan for `add_entity(class, id)` / `add_relation(id, rel, "
      "target)` / `add_attribute(id, attr, value)` calls with **literal string** "
      "arguments. Calls using computed/dynamic class or field names are invisible to "
      "this scan and will show up as false positives below -- always check the "
      "actual source before acting on a finding (see the verified false positive "
      "documented in section 4).")
    p()

    # -- 1 & 2: dead relations / attributes -----------------------------
    all_relations = set(model.global_relations.keys())
    all_attributes = set(model.global_attributes.keys())
    not_directly_used_relations = all_relations - usage.used_relations
    not_directly_used_attributes = all_attributes - usage.used_attributes

    dead_relations = sorted(not_directly_used_relations - usage.dict_literal_keys)
    likely_dynamic_relations = sorted(not_directly_used_relations & usage.dict_literal_keys)
    dead_attributes = sorted(not_directly_used_attributes - usage.dict_literal_keys)
    likely_dynamic_attributes = sorted(not_directly_used_attributes & usage.dict_literal_keys)

    p("## 1. Dead relations (declared in the registry, never used anywhere)")
    p()
    p(f"{len(dead_relations)} of {len(all_relations)} declared relations show no "
      f"evidence of use at all (neither a direct literal call nor a dict-literal key "
      f"anywhere scanned) -- highest-confidence dead code.")
    p()
    for r in dead_relations:
        p(f"- `{r}`")
    p()
    if likely_dynamic_relations:
        p(f"({len(likely_dynamic_relations)} more relations are not called directly "
          f"but appear as a dict-literal key somewhere -- likely set via a "
          f"`for k, v in {{...}}.items(): add_relation(id, k, v)` loop, e.g. the "
          f"controller-parameter pattern in example_kundur_two_area.py. Lower "
          f"confidence these are actually dead; see the appendix at the bottom.)")
        p()

    p("## 2. Dead attributes (declared in the registry, never used anywhere)")
    p()
    p(f"{len(dead_attributes)} of {len(all_attributes)} declared attributes show no "
      f"evidence of use at all (neither a direct literal call nor a dict-literal key "
      f"anywhere scanned) -- highest-confidence dead code.")
    p()
    for a in dead_attributes:
        p(f"- `{a}`")
    p()
    if likely_dynamic_attributes:
        p(f"({len(likely_dynamic_attributes)} more attributes are not called directly "
          f"but appear as a dict-literal key somewhere -- likely set via the same "
          f"dynamic-loop pattern. Lower confidence these are actually dead; see the "
          f"appendix at the bottom.)")
        p()

    # -- 3: orphaned classes ---------------------------------------------
    p("## 3. Orphaned classes (concrete, never instantiated anywhere)")
    p()
    orphaned = []
    for cname, cdata in decl.items():
        cdef = model.classes.get(cname)
        is_abstract = getattr(cdef, "abstract", False) if cdef else cdata["abstract"]
        if is_abstract:
            continue
        if cname not in usage.instantiated_classes:
            orphaned.append(cname)
    orphaned.sort()
    p(f"{len(orphaned)} of {len(decl)} classes are concrete but never appear as the "
      f"class argument of `add_entity(...)` anywhere in examples/ or tests/.")
    p()
    for c in orphaned:
        rel_path = decl[c]["file"].relative_to(REPO_ROOT)
        p(f"- `{c}` -- {rel_path}")
    p()

    # -- 4: misapplied-generality relations --------------------------------
    p("## 4. Relations declared on a base class but only ever used on one subclass")
    p()
    p("A relation declared on class X should plausibly be usable by X directly or by "
      "more than one of its subclasses. If it is only ever exercised on a single "
      "strict descendant class, declaring it on the broader base **may** be "
      "over-generalized -- but this check only sees `add_relation(id, rel, target)` "
      "calls in examples/ and tests/, where the entity id can be traced back to a "
      "literal class name. It CANNOT see relation-setting that happens generically "
      "inside a builder method in cesdm/ or ear/ (there the entity id is a function "
      "parameter, not a literal, so it can't be attributed to a class statically).")
    p()
    p("**Verified false positive from this exact check**: `hasInputResource` "
      "initially looked like it was only ever used on `HydroGenerationUnit` -- but "
      "`cesdm/domain/model/builders.py` sets it generically inside "
      "`create_generation_unit()`, which `add_wind_generator()` and "
      "`add_solar_generator()` both call too. It only looked hydro-only because no "
      "example directly calls `add_relation(..., \"hasInputResource\", ...)` with a "
      "literal wind/solar entity id -- the wind/solar builders wire it up internally "
      "instead. **Always grep the actual finding through `cesdm/` and `ear/` before "
      "concluding it's a real design issue, not just this report.**")
    p()

    declares_relation = defaultdict(list)
    for cname, cdata in decl.items():
        for rid in cdata["own_relations"]:
            declares_relation[rid].append(cname)

    findings = []
    for rid, declaring_classes in declares_relation.items():
        used_on = usage.relation_usage_by_class.get(rid, set())
        if not used_on:
            continue  # covered by "dead relations" above
        for declaring_cls in declaring_classes:
            used_on_self_or_non_descendant = False
            strict_descendant_uses = set()
            for used_cls in used_on:
                if used_cls == declaring_cls:
                    used_on_self_or_non_descendant = True
                    continue
                if model.is_class_derived_from(used_cls, declaring_cls, model.inheritance):
                    strict_descendant_uses.add(used_cls)
                else:
                    used_on_self_or_non_descendant = True
            if strict_descendant_uses and not used_on_self_or_non_descendant:
                if len(strict_descendant_uses) == 1:
                    findings.append((rid, declaring_cls, next(iter(strict_descendant_uses))))

    findings.sort()
    p(f"{len(findings)} finding(s):")
    p()
    VERIFIED_FALSE_POSITIVES = {"hasInputResource"}
    for rid, declaring_cls, used_cls in findings:
        note = ("  <-- VERIFIED FALSE POSITIVE, see note above, do not act on this one"
                if rid in VERIFIED_FALSE_POSITIVES else "")
        p(f"- `{rid}` declared on `{declaring_cls}`, only ever used on `{used_cls}`{note}")
    p()

    # -- 5: stable-tier classes with zero usage coverage -------------------
    p("## 5. `stable`-tier classes never exercised by any example or test")
    p()
    manifest = model.schema_manifest
    stable_findings = []
    for cname, cdata in decl.items():
        cdef = model.classes.get(cname)
        is_abstract = getattr(cdef, "abstract", False) if cdef else cdata["abstract"]
        if is_abstract:
            continue
        rel_path = cdata["file"].relative_to(schema_dir)
        parts = rel_path.parts
        family = None
        for i in range(len(parts) - 1, 0, -1):
            candidate = "/".join(parts[:i])
            if candidate in manifest.stability:
                family = candidate
                break
        if family is None and parts and parts[0] in manifest.stability:
            family = parts[0]
        tier = manifest.stability.get(family) if family else None
        if tier == "stable" and cname not in usage.instantiated_classes:
            stable_findings.append((family, cname))

    stable_findings.sort()
    p(f"{len(stable_findings)} finding(s): classes in a `stable`-tagged family that "
      f"are never instantiated by any example or test, i.e. the 'stable' label is "
      f"currently a location-based claim, not a measured one, for these classes.")
    p()
    for family, cname in stable_findings:
        p(f"- `{cname}` (family: `{family}`)")
    p()

    # -- appendix: full lower-confidence lists -----------------------------
    p("---")
    p()
    p("<details><summary>Appendix: full lower-confidence (likely-dynamic) lists</summary>")
    p()
    p("Likely-dynamic relations:")
    for r in likely_dynamic_relations:
        p(f"- `{r}`")
    p()
    p("Likely-dynamic attributes:")
    for a in likely_dynamic_attributes:
        p(f"- `{a}`")
    p()
    p("</details>")
    p()

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-reference the CESDM schema tree against actual usage in "
                    "examples/, tests/, tools/, and the ear/cesdm library source, to "
                    "surface dead relations/attributes, orphaned classes, "
                    "over-generalized relations, and stable-tier classes with no "
                    "usage evidence."
    )
    parser.add_argument(
        "schema_dir",
        nargs="?",
        default="schemas/cesdm",
        help="Root schema directory. Default: ./schemas/cesdm",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="docs/architecture/schema_audit_report.md",
        help="Output Markdown report path. Default: "
             "docs/architecture/schema_audit_report.md",
    )
    args = parser.parse_args()

    schema_dir = pathlib.Path(args.schema_dir)
    if not schema_dir.is_absolute():
        schema_dir = REPO_ROOT / schema_dir

    report = build_report(schema_dir)

    out_path = pathlib.Path(args.output)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
