# `example_agent_based_prosumer_model.py` — Step by Step

## Why this example matters

Every other example in this folder describes a purely physical energy
system. This one shows how the CESDM core schema can be **extended**
with a second, sibling schema tree (`schemas/agentbased/`) that adds
socio-economic actors and behavioural decision-making, without
touching the core schema at all — the same extension mechanism
`docs/getting-started/schemas-in-depth.md` and `example_schema_extension.py` describe.

The result is a single integrated CESDM model containing physical
electricity infrastructure, households, distributed energy resources,
local energy communities, autonomous decision-making agents, and an
agent-based simulation scenario — all in one model, queryable together.

## Step 1 — Load multiple schemas

The model is created by merging both schema folders in one call:

```python
schema_dir = REPO_ROOT / "schemas/cesdm"
schema_agent_based_dir = REPO_ROOT / "schemas/agentbased"

model = build_model_from_yaml([
    schema_dir,
    schema_agent_based_dir,
])
```

This demonstrates the toolbox's ability to merge multiple schema
folders into one coherent data model.

## Step 2 — Create or import the base electricity system

The script supports two workflows:

**Option A — import an existing CESDM model:**

```bash
python example_agent_based_prosumer_model.py \
    --input existing_model.yaml
```

The existing infrastructure becomes the basis for the agent-based
extension.

**Option B — generate a self-contained demonstration network:** if no
input model is supplied, the example creates one geographical region,
one electricity carrier, one renewable solar resource, and one
low-voltage electrical bus.

## Step 3 — Build the social layer

The script creates entities representing the local community, linked
with semantic relations such as `isPartOf`, `locatedIn`, `memberOf`:

```text
Canton → Municipality → Energy Community → Households
```

## Step 4 — Create households and physical assets

Three households are generated, each with occupants, building type,
ownership status, annual electricity demand, rooftop PV capacity,
battery capacity, and behavioural preferences. For every household,
the corresponding physical assets (`DemandUnit`, `GenerationUnit`,
`StorageUnit`) are created, with ownership explicitly represented in
the CESDM graph.

## Step 5 — Create behavioural agents

Each household receives its own `ProsumerAgent`, storing behavioural
parameters (risk aversion, price sensitivity, environmental/comfort
preference, PV/battery/EV adoption probability) and controlling the
physical assets owned by its household. Agents receive information
such as electricity prices, PV subsidies, and solar availability. This
separation between physical assets and behavioural agents is a key
concept of the example.

## Step 6 — Community aggregator

A higher-level `AggregatorAgent` coordinates all distributed assets —
managing the local energy community, observing market signals,
controlling distributed resources, and increasing community
self-consumption — while preserving household autonomy.

## Time-series profiles

Three example profiles are created:

| Profile | Purpose |
|---|---|
| Retail tariff | Electricity price signal |
| PV subsidy | Investment incentive |
| Solar availability | Renewable generation profile |

These profiles influence agent decisions during simulation.

## Agent-based simulation scenario

An `AgentBasedModel` entity specifies the simulation period
(2025–2030), yearly time step, random seed, and optimisation
objective. All agents and controlled assets are linked to this
simulation object.

## Validation and output

Before export the model is validated:

```python
errors = model.validate()
```

Only valid CESDM models are exported, as both YAML and Frictionless
representations:

```text
output/
└── agent_based_model/
    ├── yaml/
    │   └── agent_based_prosumer_model.yaml
    └── frictionless/
```

## Concepts demonstrated

This example illustrates how CESDM can combine semantic data
modelling, electrical infrastructure, distributed energy resources,
social entities, behavioural economics, agent-based modelling, and
interoperable data exchange — a reference for integrating agent-based
simulations into CESDM-based energy system models.
