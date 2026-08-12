"""cesdm.domain.model.rdf_export — RDF/OWL schema export

Exports the loaded CESDM *schema* (classes, attributes, relations) as
an OWL ontology in Turtle syntax — the first concrete step toward the
"formal ontology alignment" gap discussed in
docs/architecture/schema_governance.md and CHANGELOG.md.

This exports the schema definition, not model instance data (entities
and their attribute/relation values) — that would be a separate,
larger feature (mapping entities to RDF individuals, typing every
literal value, ...) and isn't attempted here.

IMPORTANT — the namespace used (CESDM_ONTOLOGY_NAMESPACE below) is
PROVISIONAL. Minting a permanent identifier and later having to change
it breaks everyone who referenced it, so this uses the project's
existing published GitHub Pages docs URL as a reasonable placeholder
rather than inventing something new — but it has not been confirmed as
final by the schema's maintainers. Re-basing later only requires
changing this one constant.
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict, Optional, Union

# Provisional. See module docstring.
CESDM_ONTOLOGY_NAMESPACE = "https://demirayt.github.io/sweet-cosi-cesdm/ontology/"

QUDT_UNIT_NAMESPACE = "http://qudt.org/vocab/unit/"

_XSD_TYPE_MAP = {
    "decimal": "xsd:decimal",
    "float": "xsd:decimal",
    "number": "xsd:decimal",
    "double": "xsd:decimal",
    "integer": "xsd:integer",
    "int": "xsd:integer",
    "long": "xsd:integer",
    "boolean": "xsd:boolean",
    "bool": "xsd:boolean",
    "string": "xsd:string",
}


def _turtle_escape(text: str) -> str:
    """Escape a string for use inside a Turtle double-quoted literal."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _turtle_string(text: str) -> str:
    return f'"{_turtle_escape(text)}"'


def _iri(namespace: str, local: str) -> str:
    """Build a full <...> IRI rather than a prefixed name, to sidestep Turtle
    PN_LOCAL edge cases with dot-namespaced CESDM ids (e.g.
    'GenerationUnit.DispatchResult') and slash-containing unit symbols."""
    return f"<{namespace}{local}>"


class RdfExportMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def export_rdf_schema(
        self,
        path: Union[str, pathlib.Path],
        namespace: Optional[str] = None,
    ) -> None:
        """
        Export the loaded schema (classes, attributes, relations) as an
        OWL ontology in Turtle syntax.

        Parameters
        ----------
        path :
            Output .ttl file path.
        namespace :
            Override the ontology namespace. Defaults to
            CESDM_ONTOLOGY_NAMESPACE (provisional — see module docstring).

        Notes
        -----
        - Classes become owl:Class, with rdfs:subClassOf edges from the
          schema's inheritance graph (multiple parents -> multiple
          rdfs:subClassOf triples).
        - Relations become owl:ObjectProperty. rdfs:range is set from
          the relation's default target (the global registry
          definition); per-class target narrowing (e.g.
          Result.hasRunRecord narrowed to a specific RunRecord
          subclass by each domain's abstract base) is not represented
          at the OWL level — this is a simplification, not a bug.
          rdfs:domain is intentionally omitted rather than computed as
          an owl:unionOf of every declaring class, to keep the output
          readable; the relation is left domain-unconstrained in OWL
          terms.
        - Attributes become owl:DatatypeProperty, with rdfs:range set
          from the attribute's value type (decimal/integer/boolean/
          string -> xsd:*). Where an attribute's unit registry entry
          (schemas/cesdm/units/units.yaml) has a verified QUDT IRI *and* the
          attribute accepts exactly one unit, a cesdm:hasUnit
          annotation points at it. Attributes with zero or multiple
          registered units, or an unverified/no-equivalent QUDT status,
          get no cesdm:hasUnit triple.
        """
        ns = namespace or CESDM_ONTOLOGY_NAMESPACE
        out_path = pathlib.Path(path)

        classes: Dict[str, Any] = getattr(self, "classes", {}) or {}
        inheritance: Dict[str, Any] = getattr(self, "inheritance", {}) or {}
        global_relations: Dict[str, Any] = getattr(self, "global_relations", {}) or {}
        global_attributes: Dict[str, Any] = getattr(self, "global_attributes", {}) or {}
        global_units: Dict[str, Any] = getattr(self, "global_units", {}) or {}

        lines: list[str] = []

        def p(s: str = ""):
            lines.append(s)

        # --- prefixes & ontology header -----------------------------------
        p(f"@prefix cesdm: <{ns}> .")
        p("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
        p("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
        p("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
        p("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
        p(f"@prefix qudt-unit: <{QUDT_UNIT_NAMESPACE}> .")
        p()
        schema_version = getattr(getattr(self, "schema_manifest", None), "version", None)
        p(f"<{ns}> a owl:Ontology ;")
        p(f'    rdfs:label "CESDM ontology (auto-generated, provisional namespace)" ;')
        p(
            f'    rdfs:comment "Generated from the CESDM YAML schema tree by '
            f'export_rdf_schema(). Namespace is PROVISIONAL -- not yet confirmed '
            f'final by the schema maintainers. See docs/architecture/'
            f'schema_governance.md." '
            + (f';\n    owl:versionInfo {_turtle_string(schema_version)} .' if schema_version else ".")
        )
        p()

        # --- classes ---------------------------------------------------------
        p("# " + "-" * 76)
        p("# Classes")
        p("# " + "-" * 76)
        for cname in sorted(classes.keys()):
            cdef = classes[cname]
            iri = _iri(ns, cname)
            p(f"{iri} a owl:Class ;")
            triples = []
            parents = inheritance.get(cname) or []
            if isinstance(parents, str):
                parents = [parents]
            for parent in parents:
                triples.append(f"    rdfs:subClassOf {_iri(ns, parent)}")
            triples.append(f"    rdfs:label {_turtle_string(cname)}")
            description = getattr(cdef, "description", None)
            if description:
                triples.append(f"    rdfs:comment {_turtle_string(description)}")
            if getattr(cdef, "abstract", False):
                triples.append(
                    f'    cesdm:isAbstract "true"^^xsd:boolean'
                )
            p(" ;\n".join(triples) + " .")
            p()

        # --- relations (owl:ObjectProperty) -----------------------------------
        p("# " + "-" * 76)
        p("# Relations (owl:ObjectProperty)")
        p("# " + "-" * 76)
        for rid in sorted(global_relations.keys()):
            rdef = global_relations[rid] or {}
            iri = _iri(ns, rid)
            p(f"{iri} a owl:ObjectProperty ;")
            triples = [f"    rdfs:label {_turtle_string(rid)}"]
            targets = rdef.get("target")
            if isinstance(targets, str):
                targets = [targets]
            if targets:
                for t in targets:
                    triples.append(f"    rdfs:range {_iri(ns, t)}")
            description = rdef.get("description")
            if description:
                triples.append(f"    rdfs:comment {_turtle_string(description.strip())}")
            p(" ;\n".join(triples) + " .")
            p()

        # --- attributes (owl:DatatypeProperty) --------------------------------
        p("# " + "-" * 76)
        p("# Attributes (owl:DatatypeProperty)")
        p("# " + "-" * 76)
        for aid in sorted(global_attributes.keys()):
            adef = global_attributes[aid] or {}
            iri = _iri(ns, aid)
            p(f"{iri} a owl:DatatypeProperty ;")
            triples = []
            label = adef.get("label") or aid
            triples.append(f"    rdfs:label {_turtle_string(label)}")
            value_type = ((adef.get("value") or {}).get("type") or "string").lower()
            xsd_type = _XSD_TYPE_MAP.get(value_type, "xsd:string")
            triples.append(f"    rdfs:range {xsd_type}")
            description = adef.get("description")
            if description:
                triples.append(f"    rdfs:comment {_turtle_string(str(description).strip())}")

            unit_enum = ((adef.get("unit") or {}).get("constraints") or {}).get("enum") or []
            if len(unit_enum) == 1:
                unit_id = unit_enum[0]
                unit_entry = global_units.get(unit_id) or {}
                if unit_entry.get("qudt_status") == "verified" and unit_entry.get("qudt_iri"):
                    triples.append(f"    cesdm:hasUnit <{unit_entry['qudt_iri']}>")

            p(" ;\n".join(triples) + " .")
            p()

        out_path.write_text("\n".join(lines), encoding="utf-8")
