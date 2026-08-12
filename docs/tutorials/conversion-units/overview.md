# Conversion Units Tutorial

!!! abstract "Before you start"
    - **Prerequisites:** [Your First Model (Simple)](../../getting-started/first-model-simple.md), [Carrier Domains](../../guides/carrier-domains.md), [Libraries](../../guides/libraries.md)
    - **Time:** ~30–40 minutes across four parts
    - **Audience:** modellers coupling electricity, gas, heat, and hydrogen

This tutorial builds a **Swiss district energy hub** that links four carrier domains through the compact [`ConversionUnit`](../../community/glossary.md#conversion-unit) leaves:

| Leaf | Conversion |
|------|------------|
| `HeatPumpUnit` | electricity → heat |
| `ElectrolyserUnit` | electricity → hydrogen |
| `BoilerUnit` | gas → heat |
| `FuelCellUnit` | hydrogen → electricity (+ optional heat) |
| `CHPUnit` | gas → electricity + heat |

`GenericConversionUnit` + `ConversionPort` remains the escape hatch for arbitrary MxN / P2X layouts — this tutorial stays on the compact leaves.

## Model blueprint

```mermaid
flowchart LR
  subgraph GenerationUnit
    wind([Wind])
  end
  subgraph ExternalSupply
    gasIn{{Gas import}}
  end
  subgraph NetworkNode
    elec[(ElectricalBus)]
    gas[(GasBus)]
    heat[(HeatBus)]
    h2[(HydrogenBus)]
  end
  subgraph ConversionUnit
    hp[HeatPumpUnit]
    el[ElectrolyserUnit]
    boiler[BoilerUnit]
    chp[CHPUnit]
    fc[FuelCellUnit]
  end
  subgraph DemandUnit
    demE([Elec demand])
    demH([Heat demand])
    demH2([H2 offtake])
  end

  wind --> elec
  gasIn --> gas
  elec --> hp
  elec --> el
  gas --> boiler
  gas --> chp
  el --> h2
  h2 --> fc
  hp --> heat
  boiler --> heat
  chp --> elec
  chp --> heat
  fc --> elec
  fc --> heat
  elec --> demE
  heat --> demH
  h2 --> demH2

  classDef gen fill:#C8E6C9,stroke:#66BB6A,color:#1B5E20
  classDef supply fill:#FFE0B2,stroke:#FFB74D,color:#E65100
  classDef busElec fill:#BBDEFB,stroke:#42A5F5,color:#0D47A1
  classDef busGas fill:#FFF9C4,stroke:#FBC02D,color:#F57F17
  classDef busHeat fill:#FFCDD2,stroke:#EF5350,color:#B71C1C
  classDef busH2 fill:#B2DFDB,stroke:#26A69A,color:#004D40
  classDef conv fill:#E1BEE7,stroke:#AB47BC,color:#4A148C

  class wind gen
  class gasIn supply
  class elec,demE busElec
  class gas busGas
  class heat,demH busHeat
  class h2,demH2 busH2
  class hp,el,boiler,chp,fc conv

  linkStyle 0,2,3,10,12,14 stroke:#42A5F5,stroke-width:2px
  linkStyle 1,4,5 stroke:#FBC02D,stroke-width:2px
  linkStyle 8,9,11,13,15 stroke:#EF5350,stroke-width:2px
  linkStyle 6,7,16 stroke:#26A69A,stroke-width:2px
```

| Part | What you build |
|------|----------------|
| [Part 1](part-1-system-and-carriers.md) | Schema, libraries, system, four domains, four buses |
| [Part 2](part-2-supply-and-demand.md) | Wind, gas import, electricity / heat / H₂ demands |
| [Part 3](part-3-conversion-units.md) | All five compact conversion leaves |
| [Part 4](part-4-validate-and-export.md) | Validate and export |

## Executable script

The same model as a single script:

```bash
python examples/example_conversion_units.py
```

Outputs land under `output/conversion_units_demo/`.
