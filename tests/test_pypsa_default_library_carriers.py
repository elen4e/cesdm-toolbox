from pathlib import Path
import yaml

LIB = Path(__file__).resolve().parents[1] / 'library' / 'default_library'

EXPECTED = {
    'Generation.Thermal.Gas.CCGT.Existing': ('carrier.fuel.fossil.gas.natural_gas', 22.68),
    'Generation.Thermal.Gas.OCGT.New': ('carrier.fuel.fossil.gas.natural_gas', 22.68),
    'Generation.Thermal.Coal.HardCoal.New': ('carrier.fuel.fossil.coal.hard_coal', 6.48),
    'Generation.Thermal.Coal.Lignite.New': ('carrier.fuel.fossil.coal.lignite', 6.48),
    'Generation.Thermal.Oil.LightOil.Standard': ('carrier.fuel.fossil.oil', 34.56),
    'Generation.Thermal.Coal.HardCoal.Biofuel': ('carrier.fuel.biofuel.biomass', 67.68),
    'Generation.Nuclear.LWR': ('carrier.fuel.nuclear.uranium', 6.12),
}

def _attr(entity, attr):
    return next(a['value'] for a in entity['attributes'] if a['id'] == attr)

def _relation(entity, relation):
    return next(r['target'] for r in entity['relations'] if r['id'] == relation)

def _load_library(path: Path):
    data = {}
    for part in sorted(path.rglob("*.y*ml")):
        doc = yaml.safe_load(part.read_text()) or {}
        for key, value in doc.items():
            if key == "description":
                continue
            if isinstance(value, dict):
                data.setdefault(key, {}).update(value)
    return data

def test_generator_types_resolve_expected_input_carriers_and_costs():
    data = _load_library(LIB)
    for technology, (carrier, expected_cost) in EXPECTED.items():
        assert _relation(data['GeneratorType'][technology], 'hasInputCarrier') == carrier
        assert _attr(data['Carrier'][carrier], 'energy_carrier_cost') == expected_cost
