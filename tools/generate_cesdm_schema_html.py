#!/usr/bin/env python3
"""
generate_cesdm_schema_html.py
─────────────────────────────
Generate a self-contained HTML reference from a CESDM schema directory.

Usage
-----
    python generate_cesdm_schema_html.py [schema_dir] [output.html]

    schema_dir   Path to the root schema folder (contains entities/,
                 attributes/, relations/).  Defaults to ./schemas/cesdm
    output.html  Path for the generated HTML file.
                 Defaults to cesdm_schema_ref.html

Requirements
------------
    pip install pyyaml
"""

from __future__ import annotations

import argparse
import html as _html
import json
import pathlib
import sys
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required.  Install it with:  pip install pyyaml")


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Schema loading
# ─────────────────────────────────────────────────────────────────────────────

def load_attribute_registry(schema_dir: pathlib.Path) -> dict[str, Any]:
    """Merge all attribute definition files into one flat dict."""
    registry: dict[str, Any] = {}
    attr_dir = schema_dir / "attributes"
    if not attr_dir.exists():
        return registry
    for f in sorted(attr_dir.glob("*.yaml")):
        if f.stem.startswith("_"):
            continue
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        # Top-level may be {"attributes": {...}} or just the flat dict
        top = d.get("attributes", d)
        if isinstance(top, dict):
            registry.update(top)
    return registry


def load_relation_registry(schema_dir: pathlib.Path) -> dict[str, Any]:
    """Load relations/relations.yaml."""
    rel_file = schema_dir / "relations" / "relations.yaml"
    if not rel_file.exists():
        return {}
    try:
        d = yaml.safe_load(rel_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(d, dict):
        return {}
    return d.get("relations", d)


def load_entities(schema_dir: pathlib.Path) -> dict[str, dict]:
    """Load entity YAMLs from either legacy entities/ or semantic schema folders."""
    entities: dict[str, dict] = {}
    ent_dir = schema_dir / "entities"
    search_root = ent_dir if ent_dir.exists() else schema_dir
    for f in sorted(search_root.rglob("*.yaml")):
        if "attributes" in f.parts or "relations" in f.parts:
            continue
        if f.stem.startswith("_"):
            continue
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict) or "name" not in d:
            continue
        entities[d["name"]] = d
    return entities


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Inheritance helpers
# ─────────────────────────────────────────────────────────────────────────────

def parents_of(name: str, entities: dict) -> list[str]:
    d = entities.get(name, {})
    p = d.get("parents", [])
    return [p] if isinstance(p, str) else list(p)


def all_ancestors(name: str, entities: dict, _visited: set | None = None) -> list[str]:
    """Return ancestor names breadth-first (parents, then grandparents…)."""
    if _visited is None:
        _visited = set()
    result = []
    for p in parents_of(name, entities):
        if p not in _visited:
            _visited.add(p)
            result.append(p)
            result.extend(all_ancestors(p, entities, _visited))
    return result


def collect_inherited(name: str, entities: dict) -> tuple[list, list]:
    """
    Return (inherited_attrs, inherited_rels) — fields from ancestor classes
    that are NOT already declared on the entity itself.
    Each attr element: (id, required)
    Each rel  element: (id, required, target)
    """
    d = entities.get(name, {})
    seen_a = {a["id"] for a in (d.get("attributes") or [])}
    seen_r = {r["id"] for r in (d.get("relations") or [])}
    inh_a: list = []
    inh_r: list = []

    def _gather(pname: str, depth: int = 0) -> None:
        if depth > 12:
            return
        pe = entities.get(pname, {})
        for a in pe.get("attributes") or []:
            if a["id"] not in seen_a:
                seen_a.add(a["id"])
                inh_a.append((a["id"], a.get("required", False)))
        for r in pe.get("relations") or []:
            if r["id"] not in seen_r:
                seen_r.add(r["id"])
                inh_r.append((r["id"], r.get("required", False), r.get("target", ""),
                              r.get("description", "") or r.get("comment", "")))
        for pp in parents_of(pname, entities):
            _gather(pp, depth + 1)

    for p in parents_of(name, entities):
        _gather(p)

    return inh_a, inh_r


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Categorisation
# ─────────────────────────────────────────────────────────────────────────────

_ASSET_ROOTS       = {"EnergyAssetInstance"}
_REPR_ROOTS        = {"Result"}
_NETWORK_ROOTS     = {"NetworkNode"}
_TECH_TYPE_ROOTS   = {"EnergyTechnologyType"}

# Sub-categories within the "domain" bucket — used for tab labels and
# section grouping in the HTML.  Everything that is not an asset,
# result, or network node falls into domain by default because
# the YAML schemas do not carry an explicit category field; we infer it
# purely from the inheritance tree.
#
# The domain bucket therefore contains heterogeneous things:
#   - Technology types  (GeneratorType, StorageType, …) — EnergyTechnologyType tree
#   - Carriers          (Carrier, CarrierDomain, GeographicalRegion)
#   - Time-series       (Profile, TimestampSeries)
#   - Agents            (Agent, Household, EnergyCommittee, …)
#   - Abstract bases    (SemanticEntity, SystemAsset, Port)
#   - Run records       (DispatchRunRecord, EnergySystemModel)
#
# To give users a better label in the UI we call this tab "Domain & Types"
# and explain in the page header what it contains.

def categorise(name: str, entities: dict) -> str:
    """Assign a display category based on the inheritance hierarchy.

    Categories:
      asset   — descends from EnergyAssetInstance
      result  — descends from Result (the only classes that use the
                reportsOn pattern, one per analysis run; AVR/GOV/PSS
                controllers also stand alone but link via
                controlsGenerationUnit instead, so they fall into "domain"
                like any other non-asset, non-network entity)
      network — descends from NetworkNode
      domain  — everything else: technology types, carriers, time-series,
                agents, abstract base classes, run records, controllers, etc.
                "Domain" is a catch-all; the entities here do not share
                a single conceptual role — they are simply not assets,
                results, or network nodes.
    """
    ancestors = set(all_ancestors(name, entities)) | {name}
    if ancestors & _ASSET_ROOTS:
        return "asset"
    if ancestors & _REPR_ROOTS:
        # Abstract bases in the Result tree (Result, DispatchResult,
        # PowerFlowResult, DynamicResult) never have their own
        # reportsOn target, so they'd never be nested under any
        # asset card and would otherwise never appear anywhere in the
        # page at all. Route them into "domain" (Abstract Bases group)
        # instead, alongside every other abstract base class.
        if entities.get(name, {}).get("abstract"):
            return "domain"
        return "result"
    if ancestors & _NETWORK_ROOTS:
        return "network"
    return "domain"


def domain_subcategory(name: str, entities: dict) -> str:
    """Finer-grained label for entities in the domain bucket."""
    anc = set(all_ancestors(name, entities)) | {name}
    if anc & _TECH_TYPE_ROOTS:
        return "Technology Types"
    d = entities.get(name, {})
    if name in ("Carrier", "CarrierDomain", "GeographicalRegion",
                "NaturalResource"):
        return "Carriers & Geography"
    if name in ("Profile", "TimestampSeries"):
        return "Time Series"
    if name in ("DispatchRunRecord", "EnergySystemModel"):
        return "Model Records"
    if name in ("SemanticEntity", "SystemAsset", "Port", "ConversionPort",
                "EnergyTechnologyType", "Result", "DispatchResult",
                "PowerFlowResult", "DynamicResult"):
        return "Abstract Bases"
    return "Other"


def views_for_asset(asset_name: str, entities: dict) -> list[str]:
    """Return all Result entities that have reportsOn → asset_name."""
    result = []
    for vname, vd in entities.items():
        if categorise(vname, entities) != "result":
            continue
        for r in (vd.get("relations") or []):
            targets = r.get("target", "")
            if isinstance(targets, str):
                targets = [targets]
            if asset_name in targets and r["id"] in ("reportsOn", "representsNode"):
                result.append(vname)
                break
    return sorted(result)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  HTML helpers
# ─────────────────────────────────────────────────────────────────────────────

def esc(s: Any) -> str:
    return _html.escape(str(s or ""))


def _constraints_prose(c: Any) -> str:
    """Extract human-readable prose from a top-level constraints field.

    Some attribute definitions store their description as a list of strings
    under a top-level ``constraints`` key rather than in ``description``.
    This helper extracts that prose so it can be used as a fallback description.
    Returns empty string if ``c`` is not a list of strings.
    """
    if not c:
        return ""
    if isinstance(c, list):
        # Keep only items that look like prose (not "minimum: 0.0" style constraints)
        prose = [str(item) for item in c
                 if isinstance(item, str)
                 and ":" not in str(item)[:20]]
        return " ".join(prose).strip()
    if isinstance(c, str) and ":" not in c[:20]:
        return c.strip()
    return ""


def attr_meta_html(aid: str, attrs_db: dict) -> tuple[str, str]:
    """Return (meta_html, desc_html) for an attribute id."""
    a = attrs_db.get(aid, {})
    parts: list[str] = []

    v = a.get("value", {})
    if isinstance(v, dict):
        typ = v.get("type", "")
        if typ:
            parts.append(f"<span class='typ'>{esc(typ)}</span>")
        c = v.get("constraints", {})
        if isinstance(c, dict):
            if "minimum" in c:
                parts.append(f"min&nbsp;{esc(c['minimum'])}")
            if "maximum" in c:
                parts.append(f"max&nbsp;{esc(c['maximum'])}")
            if "enum" in c:
                opts = " | ".join(esc(x) for x in c["enum"])
                parts.append(f"<span class='enum'>{opts}</span>")
        default = v.get("default")
        if default is not None:
            parts.append(f"default&nbsp;{esc(default)}")

    u = a.get("unit", {})
    if isinstance(u, dict):
        uc = u.get("constraints", {})
        if isinstance(uc, dict) and "enum" in uc:
            ustr = " | ".join(esc(x) for x in uc["enum"])
            parts.append(f"<span class='unit'>{ustr}</span>")

    meta_html = " ".join(f"<span class='meta'>{p}</span>" for p in parts)

    # Description fallback chain:
    # 1. description  2. comment  3. top-level constraints list (some schemas
    #    put prose there instead of in description)  4. label  5. empty string
    desc = (
        a.get("description", "")
        or a.get("comment", "")
        or _constraints_prose(a.get("constraints"))
        or a.get("label", "")
        or ""
    )
    return meta_html, esc(str(desc))


def rel_info_html(rid: str, rels_db: dict, target_override: Any = "",
                  inline_desc: str = "") -> tuple[str, str]:
    """Return (targets_html, desc_html) for a relation id.

    inline_desc: description declared directly on the entity relation entry
    (overrides or supplements the global relation registry description).
    """
    r = rels_db.get(rid, {})
    targets = r.get("target", target_override or "")
    if isinstance(targets, str):
        targets = [targets] if targets else []
    if not targets and target_override:
        t = target_override
        targets = [t] if isinstance(t, str) else list(t)
    thtml = " | ".join(f'<a href="#{esc(t)}" class="ref">{esc(t)}</a>' for t in targets)
    # Prefer inline description (entity-level override), fall back to global registry
    desc = inline_desc or r.get("description", "") or r.get("comment", "")
    return thtml, esc(str(desc))


def attr_row(aid: str, required: bool, attrs_db: dict, inherited: bool = False) -> str:
    meta, desc = attr_meta_html(aid, attrs_db)
    req  = '<span class="req">required</span>' if required else ''
    inh  = '<span class="inh">inherited</span>' if inherited else ''
    cls  = ' class="inherited"' if inherited else ''
    return (f'<tr{cls}>'
            f'<td class="aname">{esc(aid)}{req}{inh}</td>'
            f'<td>{meta}</td>'
            f'<td class="desc">{desc}</td>'
            f'</tr>')


def rel_row(rid: str, required: bool, target: Any,
            rels_db: dict, inherited: bool = False,
            inline_desc: str = "") -> str:
    thtml, desc = rel_info_html(rid, rels_db, target, inline_desc=inline_desc)
    req  = '<span class="req">required</span>' if required else ''
    inh  = '<span class="inh">inherited</span>' if inherited else ''
    cls  = ' class="inherited"' if inherited else ''
    return (f'<tr{cls}>'
            f'<td class="aname">{esc(rid)}{req}{inh}</td>'
            f'<td>{thtml}</td>'
            f'<td class="desc">{desc}</td>'
            f'</tr>')


def attr_table(rows_html: str, title: str = "") -> str:
    if not rows_html:
        return ""
    hdr = ""
    if title:
        hdr = f'<tr class="sub-hdr"><td colspan="3">{esc(title)}</td></tr>'
    return (f'<table>'
            f'<thead><tr><th>Attribute</th><th>Type / Constraints</th>'
            f'<th>Description</th></tr></thead>'
            f'<tbody>{hdr}{rows_html}</tbody>'
            f'</table>')


def rel_table(rows_html: str, title: str = "") -> str:
    if not rows_html:
        return ""
    hdr = ""
    if title:
        hdr = f'<tr class="sub-hdr"><td colspan="3">{esc(title)}</td></tr>'
    return (f'<table>'
            f'<thead><tr><th>Relation</th><th>Target</th>'
            f'<th>Description</th></tr></thead>'
            f'<tbody>{hdr}{rows_html}</tbody>'
            f'</table>')


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Entity card
# ─────────────────────────────────────────────────────────────────────────────

def entity_card(name: str, entities: dict,
                attrs_db: dict, rels_db: dict) -> str:
    d = entities.get(name, {})
    # Entity description: use description, fall back to comment
    _edesc = d.get("description", "") or d.get("comment", "")
    desc   = esc(str(_edesc)).replace("\n", "<br>")
    plist = parents_of(name, entities)
    plinks = " ".join(
        f'<a href="#{esc(p)}" class="parent">{esc(p)}</a>' for p in plist
    )
    abs_badge = '<span class="abstract-badge">abstract</span>' if d.get("abstract") else ""

    # Own attrs / rels
    own_a = [(a["id"], a.get("required", False)) for a in (d.get("attributes") or [])]
    own_r = [(r["id"], r.get("required", False), r.get("target", ""),
              r.get("description", "") or r.get("comment", ""))
              for r in (d.get("relations") or [])]

    # Inherited
    inh_a, inh_r = collect_inherited(name, entities)

    a_rows = "".join(attr_row(a, req, attrs_db)          for a, req in own_a)
    a_rows += "".join(attr_row(a, req, attrs_db, True)   for a, req in inh_a)
    r_rows = "".join(rel_row(rid, req, tgt, rels_db, inline_desc=idesc)
                     for rid, req, tgt, idesc in own_r)
    r_rows += "".join(rel_row(rid, req, tgt, rels_db, True, inline_desc=idesc)
                      for rid, req, tgt, idesc in inh_r)

    tables = attr_table(a_rows) + rel_table(r_rows)

    # Result entities for this asset
    views_html = ""
    view_names = views_for_asset(name, entities)
    if view_names:
        vblocks: list[str] = []
        for vname in view_names:
            vblocks.append(_view_block(vname, entities, attrs_db, rels_db))
        views_html = (
            '<div class="views-section">'
            '<h4>Results</h4>'
            + "".join(vblocks) +
            '</div>'
        )

    return (
        f'<div class="card" id="{esc(name)}">'
        f'<div class="card-header">'
        f'<span class="entity-name">{esc(name)}</span>{abs_badge}'
        f'<span class="parents">{plinks}</span>'
        f'</div>'
        f'<div class="entity-desc">{desc}</div>'
        f'{tables}'
        f'{views_html}'
        f'</div>'
    )


def _view_block(vname: str, entities: dict,
                attrs_db: dict, rels_db: dict) -> str:
    vd = entities.get(vname, {})
    vp = parents_of(vname, entities)
    vplinks = " ".join(f'<a href="#{esc(p)}" class="parent">{esc(p)}</a>' for p in vp)

    own_a = [(a["id"], a.get("required", False)) for a in (vd.get("attributes") or [])]
    own_r = [(r["id"], r.get("required", False), r.get("target", ""),
              r.get("description", "") or r.get("comment", ""))
              for r in (vd.get("relations") or [])]
    vinh_a, vinh_r = collect_inherited(vname, entities)

    va = "".join(attr_row(a, req, attrs_db)        for a, req in own_a)
    va += "".join(attr_row(a, req, attrs_db, True) for a, req in vinh_a)
    vr = "".join(rel_row(rid, req, tgt, rels_db, inline_desc=idc)
                 for rid, req, tgt, idc in own_r)
    vr += "".join(rel_row(rid, req, tgt, rels_db, True, inline_desc=idc)
                  for rid, req, tgt, idc in vinh_r)

    vtables = ""
    if va:
        vtables += (
            f'<table class="vtable">'
            f'<thead><tr><th>Attribute</th><th>Type / Constraints</th>'
            f'<th>Description</th></tr></thead>'
            f'<tbody>{va}</tbody></table>'
        )
    if vr:
        vtables += (
            f'<table class="vtable">'
            f'<thead><tr><th>Relation</th><th>Target</th>'
            f'<th>Description</th></tr></thead>'
            f'<tbody>{vr}</tbody></table>'
        )

    return (
        f'<div class="view-block" id="{esc(vname)}">'
        f'<div class="view-header">'
        f'<span class="view-name">{esc(vname)}</span>{vplinks}'
        f'</div>'
        f'{vtables}'
        f'</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Section builders
# ─────────────────────────────────────────────────────────────────────────────

_ASSET_GROUPS: list[tuple[str, list[str]]] = [
    ("Generation", [
        "GenerationUnit", "HydroGenerationUnit",
        "GenerationUnit", "ExternalSupply",
    ]),
    ("Storage", [
        "HydraulicStorageUnit", "StorageUnit",
    ]),
    ("Transport / Network Assets", [
        "TransmissionLine", "Transformer", "GenericInterconnector",
        "HVDCLink", "HVDCLink", "HVDCLink",
        "TransmissionElement",
    ]),
    ("Demand", ["DemandUnit"]),
    ("Conversion", ["GenericConversionUnit"]),
    ("Technology Types", [
        "GeneratorType", "StorageType", "ConverterType",
        "TransmissionType", "EnergyTechnologyType",
    ]),
]

_NETWORK_NAMES = [
    "NetworkNode", "ElectricalBus", "GasBus", "HeatBus",
    "HydrogenBus",
    "CarrierDomain", "Carrier", "GeographicalRegion",
    "Port", "ConversionPort",
]

_DOMAIN_SKIP = set(_NETWORK_NAMES)


def _group_html(gname: str, members: list[str],
                entities: dict, attrs_db: dict, rels_db: dict) -> str:
    cards = [entity_card(n, entities, attrs_db, rels_db)
             for n in members if n in entities]
    if not cards:
        return ""
    return (
        f'<div class="group">'
        f'<h3 class="group-title">{esc(gname)}</h3>'
        + "".join(cards) +
        '</div>'
    )


def assets_html(entities: dict, attrs_db: dict, rels_db: dict) -> str:
    covered: set[str] = set()
    parts: list[str] = []
    for gname, members in _ASSET_GROUPS:
        avail = [n for n in members if n in entities]
        covered.update(avail)
        parts.append(_group_html(gname, avail, entities, attrs_db, rels_db))
    # Remaining assets not in predefined groups
    rest = [n for n, e in sorted(entities.items())
            if e.get("category") == "asset" and n not in covered]
    if rest:
        parts.append(_group_html("Other Assets", rest, entities, attrs_db, rels_db))
    return "".join(parts)


def network_html(entities: dict, attrs_db: dict, rels_db: dict) -> str:
    return "".join(
        entity_card(n, entities, attrs_db, rels_db)
        for n in _NETWORK_NAMES if n in entities
    )


def domain_html(entities: dict, attrs_db: dict, rels_db: dict) -> str:
    """Render domain entities grouped by their sub-category.

    Domain is a catch-all for everything that is not an Asset, Result,
    or Network node. Within it we distinguish:
      Technology Types — GeneratorType, StorageType, ConverterType, …
      Carriers & Geography — Carrier, CarrierDomain, GeographicalRegion
      Time Series — Profile, TimestampSeries
      Model Records — DispatchRunRecord, EnergySystemModel
      Abstract Bases — SemanticEntity, SystemAsset, Port, …
      Other — anything else
    """
    # Group by subcategory
    from collections import defaultdict
    groups: dict[str, list[str]] = defaultdict(list)
    for n, e in sorted(entities.items()):
        if e.get("category") != "domain" or n in _DOMAIN_SKIP:
            continue
        sub = domain_subcategory(n, entities)
        groups[sub].append(n)

    ORDER = ["Technology Types", "Carriers & Geography", "Time Series",
             "Model Records", "Abstract Bases", "Other"]
    parts: list[str] = []
    for sub in ORDER:
        names = groups.get(sub, [])
        if not names:
            continue
        cards = "".join(entity_card(n, entities, attrs_db, rels_db) for n in names)
        parts.append(
            f'<div class="group">'
            f'<h3 class="group-title">{sub}</h3>'
            f'{cards}'
            f'</div>'
        )
    return "".join(parts)


def attrs_catalogue_html(attrs_db: dict) -> str:
    rows = []
    for k, v in sorted(attrs_db.items()):
        meta, desc = attr_meta_html(k, attrs_db)
        # Label: prefer explicit label, fall back to formatted id
        label = esc(v.get("label", ""))
        u = v.get("unit", {})
        unit_str = ""
        if isinstance(u, dict):
            uc = u.get("constraints", {})
            if isinstance(uc, dict) and "enum" in uc:
                unit_str = " | ".join(esc(x) for x in uc["enum"])
        rows.append(
            f'<tr>'
            f'<td class="aname">{esc(k)}</td>'
            f'<td style="color:var(--text)">{label}</td>'
            f'<td>{meta}</td>'
            f'<td style="font-family:var(--mono);font-size:11px;color:var(--accent3)">{unit_str}</td>'
            f'<td class="desc">{desc[:250]}</td>'
            f'</tr>'
        )
    return (
        '<div class="card"><table>'
        '<thead><tr>'
        '<th>ID</th><th>Label</th><th>Type / Constraints</th>'
        '<th>Unit</th><th>Description</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table></div>'
    )


def rels_catalogue_html(rels_db: dict) -> str:
    rows = []
    for k, v in sorted(rels_db.items()):
        targets = v.get("target", [])
        if isinstance(targets, str):
            targets = [targets]
        thtml = " | ".join(
            f'<a href="#{esc(t)}" class="ref">{esc(t)}</a>' for t in targets
        )
        desc = esc(str(v.get("description", ""))[:300])
        rows.append(
            f'<tr>'
            f'<td class="aname">{esc(k)}</td>'
            f'<td>{thtml}</td>'
            f'<td class="desc">{desc}</td>'
            f'</tr>'
        )
    return (
        '<div class="card"><table>'
        '<thead><tr>'
        '<th>ID</th><th>Target(s)</th><th>Description</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Sidebar navigation
# ─────────────────────────────────────────────────────────────────────────────

def _nav_forest(
    names: list[str], entities: dict
) -> tuple[list[str], dict[str, list[str]]]:
    """Build a forest from *names* using each entity's ``parents``.

    A node is a root when none of its parents are in the same name set.
    Multi-parent entities attach under the first parent that is in the set
    (CESDM is almost entirely single-inheritance).
    """
    name_set = {n for n in names if n in entities}
    children: dict[str, list[str]] = {n: [] for n in name_set}
    roots: list[str] = []
    for n in sorted(name_set):
        parents_in = [p for p in parents_of(n, entities) if p in name_set]
        if not parents_in:
            roots.append(n)
        else:
            children[parents_in[0]].append(n)
    for kids in children.values():
        kids.sort()
    return roots, children


def _render_nav_tree(roots: list[str], entities: dict,
                     children: dict[str, list[str]],
                     seen: set[str]) -> str:
    """Render a nested, collapsible ``<ul>`` of nav links for *roots*."""
    items: list[str] = []
    for n in roots:
        if n in seen or n not in entities:
            continue
        seen.add(n)
        abs_cls = ' class="nav-abstract"' if entities[n].get("abstract") else ""
        kid_names = children.get(n, [])
        kids = _render_nav_tree(kid_names, entities, children, seen)
        if kids:
            items.append(
                f'<li class="nav-node has-kids">'
                f'<div class="nav-row">'
                f'<button type="button" class="nav-twist" aria-expanded="true" '
                f'aria-label="Toggle {esc(n)}"></button>'
                f'<a href="#{esc(n)}"{abs_cls}>{esc(n)}</a>'
                f'</div>'
                f'{kids}'
                f'</li>'
            )
        else:
            items.append(
                f'<li class="nav-node">'
                f'<div class="nav-row">'
                f'<span class="nav-twist-spacer"></span>'
                f'<a href="#{esc(n)}"{abs_cls}>{esc(n)}</a>'
                f'</div>'
                f'</li>'
            )
    if not items:
        return ""
    return '<ul class="nav-children">\n' + "\n".join(items) + "\n</ul>"


def sidebar_nav(entities: dict) -> str:
    """Single inheritance tree for all entities (no section headers)."""
    roots, children = _nav_forest(list(entities.keys()), entities)
    tree = _render_nav_tree(roots, entities, children, seen=set())
    if not tree:
        return ""
    return f'<li class="nav-tree">{tree}</li>'


# ─────────────────────────────────────────────────────────────────────────────
# 8.  CSS + JS (inline)
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """\
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

:root {
  --bg:       #0f1117;
  --surface:  #181c24;
  --surface2: #1e2330;
  --border:   #2a3045;
  --accent:   #4a9eff;
  --accent2:  #7ec8a4;
  --accent3:  #e5a050;
  --text:     #c8d0e0;
  --text-dim: #6b7899;
  --text-hi:  #eef2ff;
  --req:      #e05555;
  --inh:      #3a4a6b;
  --abstract: #6b4a9a;
  --mono:     'IBM Plex Mono', monospace;
  --sans:     'IBM Plex Sans', sans-serif;
  --nav-w:    300px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 13px;
  line-height: 1.6;
  display: flex;
}

/* ── Sidebar ── */
#sidebar {
  width: var(--nav-w);
  min-height: 100vh;
  background: var(--surface);
  border-right: 1px solid var(--border);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  flex-shrink: 0;
  padding-bottom: 2rem;
}

.sidebar-logo {
  padding: 1.4rem 1.2rem 1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.5rem;
}
.sidebar-logo h1 {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.sidebar-logo p { font-size: 11px; color: var(--text-dim); margin-top: 2px; }

#search {
  width: calc(100% - 1.6rem);
  margin: 0.6rem 0.8rem;
  padding: 0.45rem 0.7rem;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 12px;
  outline: none;
}
#search:focus { border-color: var(--accent); }

#nav-list { list-style: none; padding: 0.4rem 0 1rem; }
#nav-list .nav-tree { list-style: none; }
#nav-list .nav-children {
  list-style: none;
  margin: 0;
  padding: 0;
}
#nav-list .nav-children .nav-children {
  padding-left: 0.55rem;
  border-left: 1px solid var(--border);
  margin-left: 0.7rem;
}
#nav-list .nav-node { list-style: none; }
#nav-list .nav-node.collapsed > .nav-children { display: none; }
#nav-list .nav-row {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  min-width: 0;
}
#nav-list .nav-twist,
#nav-list .nav-twist-spacer {
  flex: 0 0 1.1rem;
  width: 1.1rem;
  height: 1.1rem;
}
#nav-list .nav-twist {
  border: none;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  padding: 0;
  font-size: 9px;
  line-height: 1.1rem;
  border-radius: 2px;
}
#nav-list .nav-twist::before { content: "▼"; display: block; text-align: center; }
#nav-list .nav-node.collapsed > .nav-row > .nav-twist::before { content: "▶"; }
#nav-list .nav-twist:hover { color: var(--accent); background: var(--surface2); }
#nav-list a {
  display: block;
  flex: 1;
  min-width: 0;
  padding: 0.2rem 0.5rem 0.2rem 0.2rem;
  color: var(--text-dim);
  text-decoration: none;
  font-size: 12px;
  font-family: var(--mono);
  border-left: 2px solid transparent;
  transition: all 0.12s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
#nav-list a.nav-abstract { color: var(--text-dim); opacity: 0.75; font-style: italic; }
#nav-list a:hover { color: var(--text-hi); border-left-color: var(--accent); background: var(--surface2); opacity: 1; }
#nav-list a.active { color: var(--accent); border-left-color: var(--accent); opacity: 1; font-style: normal; }

/* ── Main ── */
#main {
  flex: 1;
  padding: 0 2rem 4rem;
  max-width: calc(100vw - var(--nav-w));
  overflow-x: hidden;
}

.page-header {
  padding: 2rem 0 1.5rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
}
.page-header h2 { font-size: 22px; font-weight: 300; color: var(--text-hi); letter-spacing: -0.02em; }
.page-header p  { font-size: 13px; color: var(--text-dim); margin-top: 0.4rem; }

/* ── Tabs ── */
.tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 50;
  padding-top: 0.5rem;
}
.tab-btn {
  padding: 0.6rem 1.4rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-dim);
  font-family: var(--mono);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.12s;
  letter-spacing: 0.04em;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-content { display: none; }
.tab-content.active { display: block; }

/* ── Groups / Cards ── */
.group { margin-bottom: 2.5rem; }
.group-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent3);
  font-family: var(--mono);
  margin-bottom: 1rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 1.2rem;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  padding: 0.9rem 1.2rem 0.7rem;
  background: var(--surface2);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.entity-name { font-family: var(--mono); font-size: 14px; font-weight: 600; color: var(--text-hi); }
.abstract-badge {
  font-size: 10px; padding: 1px 6px; border-radius: 3px;
  background: var(--abstract); color: #dcc8ff;
  font-family: var(--mono); letter-spacing: 0.05em;
}
.parents { margin-left: auto; }
.parent {
  font-size: 11px; color: var(--text-dim); text-decoration: none;
  font-family: var(--mono); background: var(--surface);
  padding: 1px 6px; border-radius: 3px; border: 1px solid var(--border); margin-left: 4px;
}
.parent:hover { color: var(--accent); border-color: var(--accent); }

.entity-desc {
  padding: 0.7rem 1.2rem;
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.7;
  border-bottom: 1px solid var(--border);
  white-space: pre-line;
}
.entity-desc:empty { display: none; }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; font-size: 12px; }
table + table { border-top: 1px solid var(--border); }
thead tr { background: rgba(74,158,255,0.06); }
th {
  text-align: left; padding: 0.45rem 1.2rem;
  font-size: 10px; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--text-dim);
  font-family: var(--mono); border-bottom: 1px solid var(--border);
}
td { padding: 0.4rem 1.2rem; border-bottom: 1px solid rgba(42,48,69,0.6); vertical-align: top; }
tr:last-child td { border-bottom: none; }
tr.inherited { opacity: 0.6; }
tr:hover { background: rgba(255,255,255,0.015); }
tr.sub-hdr td {
  background: rgba(74,158,255,0.04);
  font-size: 10px; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--accent); font-family: var(--mono);
  padding: 0.35rem 1.2rem; border-bottom: 1px solid var(--border);
}

.aname { font-family: var(--mono); font-size: 12px; color: var(--accent2); white-space: nowrap; }
.desc  { color: var(--text-dim); font-size: 11px; max-width: 400px; }

.meta {
  display: inline-block; font-family: var(--mono); font-size: 11px;
  background: var(--surface2); border: 1px solid var(--border); border-radius: 3px;
  padding: 0 5px; margin: 1px 2px; color: var(--text);
}
.typ  { color: #7ec8ff; }
.unit { color: var(--accent3); }
.enum { color: #c8a0e8; font-size: 10px; }

.req {
  display: inline-block; font-size: 9px; padding: 0 5px; border-radius: 3px;
  background: var(--req); color: #fff; margin-left: 5px;
  font-family: var(--mono); vertical-align: middle;
}
.inh {
  display: inline-block; font-size: 9px; padding: 0 5px; border-radius: 3px;
  background: var(--inh); color: #aab; margin-left: 5px;
  font-family: var(--mono); vertical-align: middle;
}
.ref { color: var(--accent); text-decoration: none; font-family: var(--mono); font-size: 11px; }
.ref:hover { text-decoration: underline; }

/* ── Results ── */
.views-section {
  border-top: 2px solid var(--accent);
  background: rgba(74,158,255,0.03);
}
.views-section h4 {
  padding: 0.6rem 1.2rem 0.4rem;
  font-size: 10px; font-weight: 600; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--accent); font-family: var(--mono);
}
.view-block { border-top: 1px solid var(--border); margin-left: 1.2rem; }
.view-header {
  display: flex; align-items: baseline; gap: 0.5rem;
  padding: 0.5rem 0 0.3rem; flex-wrap: wrap;
}
.view-name { font-family: var(--mono); font-size: 12px; font-weight: 600; color: var(--accent); }
.vtable { font-size: 11.5px; border-top: 1px solid rgba(42,48,69,0.5); }
.vtable th  { font-size: 9.5px; padding: 0.35rem 1rem; }
.vtable td  { padding: 0.3rem 1rem; }
.vtable .aname { font-size: 11.5px; }

/* ── Legend ── */
.legend { display: flex; gap: 1.2rem; padding: 0.8rem 0; margin-bottom: 1rem; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-dim); }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

@media (max-width: 768px) {
  #sidebar { display: none; }
  #main { max-width: 100vw; padding: 0 1rem 3rem; }
}

/* ── Domain info banner ── */
.domain-info {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent3);
  border-radius: 4px;
  padding: 0.8rem 1.2rem;
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.7;
  margin-bottom: 1.5rem;
}
.domain-info strong { color: var(--text); }
.domain-info code {
  font-family: var(--mono);
  font-size: 11px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 0 4px;
  color: var(--accent2);
}

/* ── Search highlight ── */
mark.hl {
  background: rgba(255, 213, 79, 0.35);
  color: inherit;
  border-radius: 2px;
  padding: 0 1px;
}

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0 1rem;
  flex-wrap: wrap;
}
.filter-bar label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-dim);
  cursor: pointer;
  user-select: none;
}
.filter-bar input[type=checkbox] {
  width: 14px; height: 14px;
  accent-color: var(--accent);
  cursor: pointer;
}
.filter-bar label:hover { color: var(--text); }

.card.no-content { display: none; }
"""

_JS = """\
// ── Tab switching ─────────────────────────────────────────────────────────────
function showTab(id, btn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
  const q = document.getElementById('search').value;
  if (q) applySearch(q);
}

// ── Full-content search ────────────────────────────────────────────────────────
// Searches entity name, description, attribute names, relation names.
// Highlights matches and hides non-matching cards.

let _idx = null;

function buildIndex() {
  _idx = [];
  document.querySelectorAll('.card').forEach(card => {
    const id = card.id;
    if (!id) return;
    const name   = (card.querySelector('.entity-name') || {}).textContent || '';
    const desc   = (card.querySelector('.entity-desc')  || {}).textContent || '';
    const anames = [...card.querySelectorAll('.aname')].map(n => n.textContent).join(' ');
    const refs   = [...card.querySelectorAll('.ref')].map(n => n.textContent).join(' ');
    const full   = [name, desc, anames, refs].join(' ').toLowerCase();
    _idx.push({ card, id, full });
  });
}

function applySearch(raw) {
  if (!_idx) buildIndex();
  const q = raw.trim().toLowerCase();

  if (!q) {
    _idx.forEach(({ card }) => { card.style.display = ''; removeHL(card); });
    document.querySelectorAll('.group').forEach(g => g.style.display = '');
    updateNavFilter('');
    return;
  }

  const tokens = q.split(/ +/).filter(Boolean);
  _idx.forEach(({ card, full }) => {
    const match = tokens.every(t => full.includes(t));
    card.style.display = match ? '' : 'none';
    match ? addHL(card, tokens) : removeHL(card);
  });

  // Hide groups with no visible cards
  document.querySelectorAll('.group').forEach(g => {
    g.style.display = [...g.querySelectorAll('.card')].some(c => c.style.display !== 'none')
      ? '' : 'none';
  });

  updateNavFilter(q);
}

// ── Sidebar nav filter (name only; keep ancestors of matches visible) ─────────
function updateNavFilter(q) {
  const qn = (q || '').toLowerCase();
  const nodes = document.querySelectorAll('#nav-list li.nav-node');
  if (!qn) {
    nodes.forEach(li => { li.style.display = ''; });
    return;
  }
  nodes.forEach(li => {
    const a = li.querySelector(':scope > .nav-row > a');
    li.dataset.match = (a && a.textContent.toLowerCase().includes(qn)) ? '1' : '0';
  });
  nodes.forEach(li => {
    const keep = li.dataset.match === '1'
      || !!li.querySelector('li.nav-node[data-match="1"]');
    li.style.display = keep ? '' : 'none';
    if (keep) {
      // Reveal collapsed ancestors so matches stay reachable
      let p = li.parentElement && li.parentElement.closest('li.nav-node');
      while (p) {
        p.classList.remove('collapsed');
        const twist = p.querySelector(':scope > .nav-row > .nav-twist');
        if (twist) twist.setAttribute('aria-expanded', 'true');
        p = p.parentElement && p.parentElement.closest('li.nav-node');
      }
    }
  });
}

// ── Collapsible inheritance tree ──────────────────────────────────────────────
document.querySelectorAll('#nav-list .nav-twist').forEach(btn => {
  btn.addEventListener('click', e => {
    e.preventDefault();
    e.stopPropagation();
    const li = btn.closest('.nav-node');
    if (!li) return;
    const collapsed = li.classList.toggle('collapsed');
    btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  });
});

// ── Highlight matching text ────────────────────────────────────────────────────
function addHL(card, tokens) {
  removeHL(card);
  const walk = document.createTreeWalker(card, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let n;
  while ((n = walk.nextNode())) nodes.push(n);
  nodes.forEach(n => {
    if (!n.nodeValue.trim()) return;
    let html = xesc(n.nodeValue);
    tokens.forEach(t => {
      html = html.replace(new RegExp(xre(t), 'gi'), m => `<mark class="hl">${m}</mark>`);
    });
    if (html !== xesc(n.nodeValue)) {
      const s = document.createElement('span');
      s.className = 'hl-wrap'; s.innerHTML = html;
      n.parentNode.replaceChild(s, n);
    }
  });
}
function removeHL(card) {
  card.querySelectorAll('.hl-wrap').forEach(s =>
    s.parentNode.replaceChild(document.createTextNode(s.textContent), s));
}
function xesc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function xre(s)  { return s.replace(/[-.*+?^${}()|[\\]]/g, '\\$&'); }

// ── Smart nav link: switch tab if needed, then scroll ─────────────────────────
function navTo(id) {
  const card = document.getElementById(id);
  if (!card) return;
  const tab = card.closest('.tab-content');
  if (tab && !tab.classList.contains('active')) {
    const tabId = tab.id.replace('tab-', '');
    const btn = document.querySelector(`.tab-btn[onclick*="'${tabId}'"]`);
    if (btn) showTab(tabId, btn);
  }
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
document.querySelectorAll('#nav-list a').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    navTo(a.getAttribute('href').slice(1));
    document.querySelectorAll('#nav-list a').forEach(x => x.classList.remove('active'));
    a.classList.add('active');
  });
});

// ── Scroll-based active nav highlight ─────────────────────────────────────────
const obs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      const id = e.target.id;
      document.querySelectorAll('#nav-list a').forEach(a =>
        a.classList.toggle('active', a.getAttribute('href') === '#' + id));
    }
  });
}, { threshold: 0.15 });
document.querySelectorAll('[id]').forEach(el => obs.observe(el));

// ── Content filter: hide cards with no attributes or relations ─────────────
function filterContent(on) {
  document.querySelectorAll('.card').forEach(card => {
    // A card "has content" if it contains at least one .aname cell
    // (attribute or relation row), excluding the abstract-only inherited rows.
    const hasOwn = card.querySelectorAll('tbody tr:not(.inherited) .aname').length > 0;
    if (on && !hasOwn) {
      card.dataset.hiddenByContent = '1';
      card.style.display = 'none';
    } else {
      delete card.dataset.hiddenByContent;
      if (!card.dataset.hiddenByAbstract) card.style.display = '';
    }
  });
  hideEmptyGroups();
  // Rebuild search index after DOM change
  _idx = null;
}

// ── Abstract filter: hide abstract-badged cards ────────────────────────────
function filterAbstract(on) {
  document.querySelectorAll('.card').forEach(card => {
    const isAbstract = card.querySelector('.abstract-badge') !== null;
    if (on && isAbstract) {
      card.dataset.hiddenByAbstract = '1';
      card.style.display = 'none';
    } else {
      delete card.dataset.hiddenByAbstract;
      if (!card.dataset.hiddenByContent) card.style.display = '';
    }
  });
  hideEmptyGroups();
  _idx = null;
}

function hideEmptyGroups() {
  document.querySelectorAll('.group').forEach(g => {
    g.style.display = [...g.querySelectorAll('.card')]
      .some(c => c.style.display !== 'none') ? '' : 'none';
  });
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Full page assembly
# ─────────────────────────────────────────────────────────────────────────────

def _schema_version(schema_dir: pathlib.Path) -> str | None:
    manifest = schema_dir / "SCHEMA_MANIFEST.yaml"
    if not manifest.is_file():
        return None
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    return data.get("version")


def build_page(schema_dir: pathlib.Path) -> str:
    attrs_db  = load_attribute_registry(schema_dir)
    rels_db   = load_relation_registry(schema_dir)
    entities  = load_entities(schema_dir)

    # Annotate each entity with its category
    for name, d in entities.items():
        d["category"] = categorise(name, entities)
        d["views"]    = views_for_asset(name, entities)

    nav   = sidebar_nav(entities)
    tab_a = assets_html(entities, attrs_db, rels_db)
    tab_n = network_html(entities, attrs_db, rels_db)
    tab_d = domain_html(entities, attrs_db, rels_db)
    tab_c = attrs_catalogue_html(attrs_db)
    tab_r = rels_catalogue_html(rels_db)

    schema_name = schema_dir.resolve().name

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CESDM Schema Reference — {esc(schema_name)}</title>
<style>{_CSS}</style>
</head>
<body>

<aside id="sidebar">
  <div class="sidebar-logo">
    <h1>CESDM Schemas</h1>
    <p>Common Energy System Domain Model</p>
  </div>
  <input type="text" id="search"
         placeholder="Search entities, attributes, relations…"
         oninput="applySearch(this.value)">
  <ul id="nav-list">
    {nav}
  </ul>
</aside>

<main id="main">
  <div class="page-header">
    <h2>CESDM Schema Reference</h2>
    <p>Entity definitions, attributes, relations, and results —
    generated from CESDM schemas{f" v{version}" if (version := _schema_version(schema_dir)) else ""}
    ({len(entities)} entities · {len(attrs_db)} attributes · {len(rels_db)} relations).</p>
  </div>

  <div class="legend">
    <span class="legend-item"><span class="req">required</span> Required field</span>
    <span class="legend-item"><span class="inh">inherited</span> Inherited from parent</span>
    <span class="legend-item"><span class="abstract-badge">abstract</span> Abstract class</span>
    <span class="legend-item" style="color:#7ec8a4">■ </span>
    <span style="font-size:11px;color:var(--text-dim)">Attributes &amp; relations</span>
    <span class="legend-item" style="color:#4a9eff">■ </span>
    <span style="font-size:11px;color:var(--text-dim)">Results (blue border)</span>
  </div>

  <div class="filter-bar">
    <label>
      <input type="checkbox" id="chk-content" onchange="filterContent(this.checked)">
      Show only entities with attributes or relations
    </label>
    <label>
      <input type="checkbox" id="chk-no-abstract" onchange="filterAbstract(this.checked)">
      Hide abstract classes
    </label>
  </div>

  <div class="tabs">
    <button class="tab-btn active"  onclick="showTab('assets',this)">Assets</button>
    <button class="tab-btn"        onclick="showTab('network',this)">Network &amp; Carriers</button>
    <button class="tab-btn" onclick="showTab('domain',this)"
            title="Technology types, carriers, time-series, agents, abstract base classes — everything that is not an Asset, Result, or Network node">
      Domain &amp; Types
    </button>
    <button class="tab-btn"        onclick="showTab('attrs',this)">Attribute Catalogue</button>
    <button class="tab-btn"        onclick="showTab('rels',this)">Relation Catalogue</button>
  </div>

  <div id="tab-assets"  class="tab-content active">{tab_a}</div>
  <div id="tab-network" class="tab-content">{tab_n}</div>
  <div id="tab-domain"  class="tab-content">
    <div class="domain-info">
      <strong>What is a "Domain" entity?</strong>
      These entities do not descend from <code>EnergyAssetInstance</code>, <code>NetworkNode</code>, or <code>Result</code>. They are supporting concepts — technology type registries, energy carriers, time-series containers, agent/socio-economic actors, and abstract base classes. The label is a catch-all: the entities share no single role, only the absence of a more specific classification.
    </div>
    {tab_d}
  </div>
  <div id="tab-attrs"   class="tab-content">{tab_c}</div>
  <div id="tab-rels"    class="tab-content">{tab_r}</div>
</main>

<script>{_JS}</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 10. CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a self-contained HTML reference from CESDM YAML schemas."
    )
    parser.add_argument(
        "schema_dir",
        nargs="?",
        default="schemas/cesdm",
        help="Root schema directory (must contain entities/, attributes/, relations/). "
             "Default: ./schemas/cesdm",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="cesdm_schema_ref.html",
        help="Output HTML file path. Default: cesdm_schema_ref.html",
    )
    args = parser.parse_args(argv)

    schema_dir = pathlib.Path(args.schema_dir)
    if not schema_dir.exists():
        sys.exit(f"Error: schema directory not found: {schema_dir}")

    print(f"Reading schemas from: {schema_dir.resolve()}", flush=True)
    page = build_page(schema_dir)

    out = pathlib.Path(args.output)
    out.write_text(page, encoding="utf-8")
    size_kb = len(page) / 1024
    print(f"Written {size_kb:.0f} KB → {out.resolve()}")


if __name__ == "__main__":
    main()
