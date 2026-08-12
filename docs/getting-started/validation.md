# Validation

!!! abstract "Before you start"
    - **Prerequisites:** [Schemas](schemas.md) — validation checks your system model against the loaded schema contract
    - **See also:** [Profiles](../guides/profiles.md) when your study uses time series (often required by analysis profiles)
    - **You'll learn:** schema validation and analysis-specific validation — when to run each and how they differ

Once you load [schemas](schemas.md) and build a system model, CESDM offers **two validation layers**. They answer different questions and both matter before you export or hand off to an analysis tool.

| Layer | Question | Typical call |
|-------|----------|--------------|
| **[Schema validation](#schema-validation)** | Does every instance conform to the loaded schemas? | `model.validate()` |
| **[Analysis-specific validation](#analysis-specific-validation)** | Does the model contain what *your* analysis needs? | `model.validate_for_analysis("optimal_dispatch")` |

Schema validation checks the **contract**. Analysis-specific validation checks **study readiness** for a particular workflow. A model can pass the first and still be unusable for power flow if line impedances or bus voltages are missing.

---

## Schema validation

[Schema validation](../community/glossary.md#schema-validation) verifies that your **system model** conforms to the loaded **[schemas](schemas.md)** — the vocabulary and rules that define what may exist.

### What it checks

`model.validate()` inspects the complete model against every loaded schema:

- entity classes exist and are allowed;
- attributes are declared for their entity class, with valid types and units;
- relations point to permitted target classes;
- required attributes and relations are present;
- schema constraints (ranges, enumerations, …) are satisfied.

It does **not** know which analysis you intend to run. Optional schema fields may be empty even when a particular study needs them.

### Running schema validation

```python
errors = model.validate()
if errors:
    for e in errors:
        print(e)
else:
    print("Schema validation passed.")
```

`validate()` returns a `list[str]` — one message per error. An empty list means the model is structurally valid.

Use schema validation after you add or change entities, attributes, or relations, and **before export**. See [Modelling Workflow](../guides/modelling-workflow.md) Step 5.

!!! tip "Hands-on example + notebook"
    Walk through enums, min/max, required relations, wrong targets, and unit errors with
    `examples/example_validation.py` or the twin notebook `notebooks/cesdm_schema_validation.ipynb`
    (notes in `examples/README_VALIDATION_EXAMPLE.md`).
    For study readiness (`validate_for_analysis`), see `examples/example_analysis_validation.py`.

### Typical errors

```text
GenerationUnit gen.ch.wind
    Invalid unit for attribute 'annual_energy_demand': 'GWh' (expected 'MWh/year')

DemandUnit dem.ch
    Missing required relation: atNode

GenerationUnit gen.ch.gas
    Unknown attribute: efficiency_at_full_load
```

Fix these by aligning instances with the schema contract — correct units, fill required slots, remove undeclared attributes. Lookup: [CESDM Schema Reference](../reference/schema-reference.md).

---

## Analysis-specific validation

One of the fundamental ideas behind CESDM is that **one common energy system model** can support many different analyses.

However, each analysis requires different information.

| Analysis | Typical required information |
|----------|------------------------------|
| Optimal dispatch | Generator capacities, efficiencies, variable costs, demand profiles |
| Power flow | Bus voltages, line impedances, transformer parameters |
| Dynamic simulation | Machine inertia, governor parameters, excitation systems |

The same CESDM model may therefore be perfectly suitable for one analysis while being incomplete for another.

[Analysis-specific validation](../community/glossary.md#analysis-specific-validation) complements schema validation by checking whether the model contains **all information required for a particular analysis workflow**.

This allows the same CESDM model to be reused across many different applications without changing the underlying representation of the physical system.

### How it works

Each analysis is described by a **[validation profile](../community/glossary.md#validation-profile)**.

A validation profile is a simple [YAML](../community/glossary.md#yaml) file that declaratively specifies:

- which [entity classes](../community/glossary.md#entity-class) participate in the analysis;
- which attributes are required;
- which relations must exist;
- optional constraints on attribute values;
- optional conditional rules.

No Python code needs to be written. The validation engine interprets the profile and checks the model accordingly.

### Example: optimal dispatch validation profile

Suppose an optimal dispatch study requires:

- every generator to define its installed capacity and operating cost;
- every demand to define its annual demand and demand profile.

These requirements can be expressed declaratively:

```yaml
name: optimal_dispatch

requirements:

  - entity_class: GenerationUnit

    checks:

      - attribute: nominal_power_capacity
        required: true
        constraints:
          minimum: 0

      - attribute: variable_operating_cost
        required: true

  - entity_class: DemandUnit

    checks:

      - attribute: annual_energy_demand
        required: true
        constraints:
          minimum: 0

      - relation: hasDemandProfile
        required: true
```

The profile **does not describe how the analysis is performed**. It defines the **minimum information that must be available** before the analysis can run.

### Running analysis-specific validation

```python
errors = model.validate_for_analysis("optimal_dispatch")
```

If the model satisfies all requirements:

```text
No validation errors.
```

Otherwise, the validator reports the missing information:

```text
GenerationUnit gen.ch.gas

    Missing attribute:
        variable_operating_cost

DemandUnit dem.ch

    Missing relation:
        hasDemandProfile
```

This detects missing information **before** expensive model conversion or solver execution.

To stop immediately on failure:

```python
model.validate_for_analysis_or_raise("optimal_dispatch")
```

Shipped profiles include `optimal_dispatch`, `power_flow`, and `dynamics` under `analysis_profiles/`.

Many study-facing attributes (dispatch costs, power-flow parameters, controller and synchronous-machine dynamics fields) are **schema-optional** (`required: false`) and enforced only by the matching analysis profile — so a model can pass `validate()` while still failing `validate_for_analysis("dynamics")`.

### Multiple analysis profiles

Different analyses provide different validation profiles:

```text
analysis_profiles/
├── optimal_dispatch.yaml
├── power_flow.yaml
└── dynamics.yaml
```

Each profile checks only the information required for its own workflow while using exactly the same CESDM model.

For example, a power-flow analysis requires electrical network information rather than operating costs:

```python
errors = model.validate_for_analysis("power_flow")
```

The corresponding profile verifies requirements such as nominal bus voltage, bus type, line impedance, and transformer parameters.

### Conditional validation

Not every validation rule applies to every entity. Profiles support conditional rules through the optional `when:` expression.

Natural inflow lives on `HydraulicStorageUnit`. If an annual total is set, a matching profile is required (closed-loop PHS may leave both unset):

```yaml
- entity_class: HydraulicStorageUnit

  checks:

    - attribute: hasNaturalInflowProfile
      required: true
      when: "annual_natural_inflow_energy > 0"
```

Rules may also depend on attribute values:

```yaml
- attribute: maximum_ramp_rate_up
  required: true
  when: "nominal_power_capacity > 100"
```

More complex expressions are supported (`and`, `or`, `not`, comparisons, parentheses, attribute and relation names as Boolean expressions).

### Command-line validation

Validation profiles can run from the command line without Python:

```bash
python tools/validate_analysis.py model.yaml --profile optimal_dispatch

python tools/validate_analysis.py model.yaml \
    --profile optimal_dispatch \
    --profile power_flow

python tools/validate_analysis.py output/pypsa_model \
    --profile power_flow \
    --json
```

The validator accepts hierarchical [YAML](../community/glossary.md#yaml), Excel workbooks, or a [Frictionless Data Package](../community/glossary.md#frictionless-data-package) — useful for CI pipelines.

### Design principles

- **Independent from schema validation** — a model may be structurally valid while still incomplete for a particular analysis.
- **Analysis-specific** — every analysis defines its own validation profile.
- **Entity-centric** — requirements attach to the entities that own the information.
- **Inheritance-aware** — requirements apply to derived entity classes automatically.
- **Declarative** — rules are [YAML](../community/glossary.md#yaml), not procedural Python.
- **Reusable** — the same profiles apply to any CESDM model.

---

## Modeller workflow

Run both layers in order when you prepare a study for hand-off:

```text
model.validate()                                   # schema: structurally valid?
model.validate_for_analysis("optimal_dispatch")    # study: complete for dispatch?
model.export_yaml_hierarchical(...)                # then export
```

See [Modelling Workflow](../guides/modelling-workflow.md) for the full lifecycle (Steps 5–7).

!!! info "Reference model"
    Examples in tutorials use the same entities as [Building your CESDM Model](../tutorials/building-first-model/overview.md).

---

## Next step

Continue with **[Proxy API](../guides/proxy-api.md)** for day-to-day Python modelling, then **[Libraries](../guides/libraries.md)** to import shared reference entities.

→ [Proxy API](../guides/proxy-api.md) · [← Schemas](schemas.md) · [Concepts overview](concepts.md)
