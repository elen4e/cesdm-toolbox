from pathlib import Path

from cesdm.default_library import CarrierDomains, Carriers, GeneratorTypes, StorageTypes
from cesdm.helpers import build_model_from_yaml
from cesdm.generated_proxies import CarrierDomainProxy, CarrierProxy, GeneratorTypeProxy


def test_relation_read_wraps_default_library_targets_in_typed_proxies():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")
    model.add_entity("GenerationUnit", "generator.test")
    model.add_relation("generator.test", "hasTechnology", GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY)
    model.add_relation("generator.test", "hasOutputCarrier", Carriers.CARRIER_ELECTRICITY)
    generator = model.get_entity("generator.test")

    assert isinstance(generator.hasTechnology, GeneratorTypeProxy)
    assert isinstance(generator.hasOutputCarrier, CarrierProxy)
    assert model.entity_class(GeneratorTypes.GENERATION_RENEWABLE_SOLAR_PV_UTILITY) == "GeneratorType"
    assert model.entity_class(Carriers.CARRIER_ELECTRICITY) == "Carrier"
    assert model.validate() == []


def test_default_library_includes_carrier_domains():
    model = build_model_from_yaml("schemas/cesdm")
    model.import_library("library/default_library")

    electricity = model.get_entity(CarrierDomains.DOMAIN_ELECTRICITY)
    gas = model.get_entity(CarrierDomains.DOMAIN_GAS)
    heat = model.get_entity(CarrierDomains.DOMAIN_HEAT)
    hydrogen = model.get_entity(CarrierDomains.DOMAIN_HYDROGEN)

    assert isinstance(electricity, CarrierDomainProxy)
    assert electricity.hasCarrier.id == Carriers.CARRIER_ELECTRICITY
    assert gas.hasCarrier.id == Carriers.CARRIER_FUEL_FOSSIL_GAS_NATURAL_GAS
    assert heat.hasCarrier.id == Carriers.CARRIER_HEAT
    assert hydrogen.hasCarrier.id == Carriers.CARRIER_HYDROGEN
    assert model.entity_class(Carriers.CARRIER_HEAT) == "Carrier"
    assert model.validate() == []


def test_validator_rejects_default_library_id_of_wrong_class():
    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GenerationUnit", "generator.test")
    model.add_relation(
        "generator.test",
        "hasOutputCarrier",
        StorageTypes.STORAGE_ELECTROCHEMICAL_BATTERY,
    )
    errors = model.validate()
    assert any("StorageType" in error and "hasOutputCarrier" in error for error in errors)


def test_proxy_stub_uses_default_library_literal_aliases():
    proxy_stub = Path("typings/cesdm/generated_proxies.pyi").read_text(encoding="utf-8")
    defaults_stub = Path("typings/cesdm/default_library.pyi").read_text(encoding="utf-8")
    assert "CarrierId: TypeAlias = Literal[" in defaults_stub
    assert "GeneratorTypeId: TypeAlias = Literal[" in defaults_stub
    assert "def hasTechnology(self, value: GeneratorTypeProxy | GeneratorTypeId)" in proxy_stub
    assert "def hasOutputCarrier(self, value: CarrierProxy | CarrierId)" in proxy_stub
