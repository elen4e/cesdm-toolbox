# Part 4: Validate and Export

!!! info "Checkpoint"
    After Part 4 you should have a validated model and YAML / Frictionless exports.

## 12. Validate

```python
errors = model.validate()
if errors:
    for error in errors:
        print(error)
else:
    print("Validation: OK")
```

Schema validation checks classes, required relations, and attribute constraints. It does not prove dispatch adequacy.

---

## 13. Inspect the conversion fleet

```python
print(model.summary())
# Expect among others:
#   ConversionUnit       5   (HeatPump, Electrolyser, Boiler, FuelCell, CHP)
#   DemandUnit           3
#   GenerationUnit       1
#   ExternalSupply       1

hp = model.get_entity("conv.hub.heat_pump")
print(hp.atElectricityNode.id, "→", hp.atHeatNode.id)
print("COP =", hp.coefficient_of_performance)
```

---

## 14. Export

```python
from pathlib import Path

out = Path("output/conversion_units_demo")
out.mkdir(parents=True, exist_ok=True)

model.export_yaml_hierarchical(out / "conversion_units_hierarchical.yaml")
model.export_frictionless(
    out / "frictionless",
    name="cesdm-conversion-units-demo",
    title="CESDM Conversion Units Demo",
)
```

---

## Run the packaged script

```bash
python examples/example_conversion_units.py
```

---

## What you practised

- Four carrier domains stay separate; conversion units bridge them
- Compact leaves use typed node relations (`atElectricityNode`, …)
- Library regions (`region.country.CH`) and domains avoid hand-rolled reference data
- `GenericConversionUnit` is reserved for true MxN cases

## See also

- [Glossary — Conversion Unit](../../community/glossary.md#conversion-unit)
- [Carrier Domains](../../guides/carrier-domains.md)
- [Building your CESDM Model — Part 4](../building-first-model/part-4-multicarrier-and-export.md) (CHP in the national reference model)
- `examples/example_multienergy.py` (port-based `GenericConversionUnit`)

← [Part 3](part-3-conversion-units.md) · [Overview](overview.md)
