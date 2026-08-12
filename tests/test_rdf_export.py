"""
export_rdf_schema() is the first concrete step toward the "formal
ontology alignment" gap discussed in
docs/architecture/schema_governance.md — exports the loaded schema
(not instance data) as an OWL ontology in Turtle syntax.

These tests require rdflib to actually parse and validate the
generated Turtle, not just check it was written — a syntactically
plausible-looking string is not the same guarantee as something that
actually parses as valid RDF.
"""

import pathlib

import pytest

from cesdm_toolbox import build_model_from_yaml

rdflib = pytest.importorskip("rdflib")


@pytest.fixture(scope="module")
def rdf_graph(tmp_path_factory):
    model = build_model_from_yaml("schemas/cesdm")
    out = tmp_path_factory.mktemp("rdf") / "cesdm.ttl"
    model.export_rdf_schema(str(out))
    g = rdflib.Graph()
    g.parse(str(out), format="turtle")
    return g, model


def test_output_parses_as_valid_turtle(rdf_graph):
    g, model = rdf_graph
    assert len(g) > 0


def test_every_class_becomes_an_owl_class(rdf_graph):
    g, model = rdf_graph
    from rdflib import RDF, OWL
    classes = set(g.subjects(RDF.type, OWL.Class))
    assert len(classes) == len(model.classes)


def test_every_relation_becomes_an_object_property(rdf_graph):
    g, model = rdf_graph
    from rdflib import RDF, OWL
    props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    assert len(props) == len(model.global_relations)


def test_every_attribute_becomes_a_datatype_property(rdf_graph):
    g, model = rdf_graph
    from rdflib import RDF, OWL
    props = set(g.subjects(RDF.type, OWL.DatatypeProperty))
    assert len(props) == len(model.global_attributes)


def test_subclass_of_edges_match_inheritance_graph(rdf_graph):
    g, model = rdf_graph
    from rdflib import RDFS, Namespace
    from cesdm.domain.model.rdf_export import CESDM_ONTOLOGY_NAMESPACE
    NS = Namespace(CESDM_ONTOLOGY_NAMESPACE)

    parents = list(g.objects(NS["GenerationUnit"], RDFS.subClassOf))
    assert str(parents[0]) == CESDM_ONTOLOGY_NAMESPACE + "EnergyAssetInstance"

    # multi-parent-safe: dot-namespaced class names must resolve correctly too
    parents2 = list(g.objects(NS["TransmissionElement.PowerFlowResult"], RDFS.subClassOf))
    assert str(parents2[0]) == CESDM_ONTOLOGY_NAMESPACE + "PowerFlowResult"


def test_verified_qudt_unit_annotation_present_for_single_unit_attribute(rdf_graph):
    g, model = rdf_graph
    from rdflib import Namespace
    from cesdm.domain.model.rdf_export import CESDM_ONTOLOGY_NAMESPACE
    NS = Namespace(CESDM_ONTOLOGY_NAMESPACE)

    units = list(g.objects(NS["nominal_power_capacity"], NS["hasUnit"]))
    assert [str(u) for u in units] == ["http://qudt.org/vocab/unit/MegaW"]


def test_no_unit_annotation_for_multi_unit_or_unverified_attributes(rdf_graph):
    g, model = rdf_graph
    from rdflib import Namespace
    from cesdm.domain.model.rdf_export import CESDM_ONTOLOGY_NAMESPACE
    NS = Namespace(CESDM_ONTOLOGY_NAMESPACE)

    # energy_storage_capacity accepts MWh/m3 -- ambiguous, must not get hasUnit
    assert list(g.objects(NS["energy_storage_capacity"], NS["hasUnit"])) == []
    # voltage_angle's unit (deg) is not yet QUDT-verified -- must not get hasUnit
    assert list(g.objects(NS["voltage_angle"], NS["hasUnit"])) == []


def test_ontology_header_present(rdf_graph):
    g, model = rdf_graph
    from rdflib import RDF, OWL, Namespace
    from cesdm.domain.model.rdf_export import CESDM_ONTOLOGY_NAMESPACE
    NS = Namespace(CESDM_ONTOLOGY_NAMESPACE)
    ontologies = list(g.subjects(RDF.type, OWL.Ontology))
    assert len(ontologies) == 1
    assert str(ontologies[0]) == CESDM_ONTOLOGY_NAMESPACE.rstrip()
