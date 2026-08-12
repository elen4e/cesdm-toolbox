"""example_multienergy.py

Multi-energy (electricity + heat + gas) toy model — CESDM V4
=============================================================

Built with core EAR calls (`add_entity`/`add_attribute`/`add_relation`)
throughout, plus `ensure_entity()` (returns an `EntityProxy` directly)
and the proxy layer for convenient reading/writing afterward
(`demand.dispatch.x = y`, ...) -- see docs/getting_started.md for the
same style, and docs/architecture/proxy_api.md for the full proxy
design.

What this example demonstrates
-------------------------------
- Building a CESDM V4 model programmatically (no YAML input required)
- Multiple carrier domains and typed bus subclasses per carrier
- Cross-domain conversion (CHP: Gas → Electricity + Heat) using
  ``ConversionUnit`` + explicit ``ConversionPort`` entities
- Demand as ``DemandUnit``, generation as ``GenerationUnit`` -- dispatch
  attributes flattened directly onto each asset (see
  docs/schema_layout.md, "Flattened representation views")

Model sketch
------------
- One region: Switzerland (``region.country.CH`` from ``library/regions_library``)
- Three carriers: Gas (fuel), Electricity, Heat
- Three CarrierDomains: D_GAS, D_ELEC, D_HEAT
- One bus per domain: GasBus, ElectricalBus, HeatBus
- One exogenous gas supply
- One CHP plant (ConversionUnit: Gas → Electricity + Heat)
- Two loads (electricity + heat demand)
"""

from __future__ import annotations

from pathlib import Path
import sys

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

sys.path.insert(0, str(_repo_root()))

from cesdm_toolbox import build_model_from_yaml, CesdmModel  # noqa: E402
from cesdm.generated_proxies import ExternalSupplyProxy  # noqa: E402

def build_multienergy_model(schema_dir: Path) -> CesdmModel:
    """Create a small multi-energy CESDM V4 model."""
    root = _repo_root()
    m = build_model_from_yaml(str(schema_dir))
    m.import_library(str(root / "library" / "default_library"))
    m.import_library(str(root / "library" / "regions_library"))

    # ------------------------------------------------------------------
    # Top-level container + region (from regions_library)
    # ------------------------------------------------------------------
    m.add_entity(entity_class="EnergySystemModel", entity_id="esm")
    m.add_attribute("esm", "long_name",
                    "CH multi-energy demo (gas + electricity + heat)")

    region_ch = "region.country.CH"

    # ------------------------------------------------------------------
    # Carrier -- ensure_carrier() (proxy-returning)
    # ------------------------------------------------------------------
    for eid, name, co2, cost in [
        ("carrier.gas",         "Natural gas",  0.20, 60.0),
        ("carrier.electricity", "Electricity",  0.0,   0.0),
        ("carrier.heat",        "Heat",         0.0,   0.0),
    ]:
        carrier = m.ensure_carrier(eid, name=name)
        m.set_attribute_if_allowed(carrier, "co2_emission_intensity", co2)
        m.set_attribute_if_allowed(carrier, "energy_carrier_cost", cost)

    # ------------------------------------------------------------------
    # CarrierDomain -- ensure_entity() creates it (if missing) and
    # returns an EntityProxy directly.
    # ------------------------------------------------------------------
    for did, name, carrier in [
        ("D_GAS",  "Gas",         "carrier.gas"),
        ("D_ELEC", "Electricity", "carrier.electricity"),
        ("D_HEAT", "Heat",        "carrier.heat"),
    ]:
        domain = m.ensure_entity(class_name="CarrierDomain", entity_id=did, name=name)
        m.add_relation_if_allowed(domain, "hasCarrier", carrier)

    # ------------------------------------------------------------------
    # Buses — one typed bus per domain.
    # ------------------------------------------------------------------
    n_gas = m.ensure_entity(class_name="GasBus", entity_id="N_CH_GAS", name="CH gas bus")
    m.add_relation_if_allowed(n_gas, "belongsToCarrierDomain", "D_GAS")
    m.add_relation_if_allowed(n_gas, "belongsToGeographicalRegion", region_ch)

    n_elec = m.ensure_entity(class_name="ElectricalBus", entity_id="N_CH_ELEC", name="CH electricity bus")
    m.add_relation_if_allowed(n_elec, "belongsToCarrierDomain", "D_ELEC")
    m.add_relation_if_allowed(n_elec, "belongsToGeographicalRegion", region_ch)

    n_heat = m.ensure_entity(class_name="HeatBus", entity_id="N_CH_HEAT", name="CH heat bus")
    m.add_relation_if_allowed(n_heat, "belongsToCarrierDomain", "D_HEAT")
    m.add_relation_if_allowed(n_heat, "belongsToGeographicalRegion", region_ch)

    # ------------------------------------------------------------------
    # Exogenous gas supply -- ensure_entity() + .connect() creates and
    # wires it in two calls.
    # ------------------------------------------------------------------
    gas_supply = m.get_entity_as(
        m.ensure_entity(class_name="ExternalSupply", entity_id="GAS_SUPPLY", name="Gas supply"),
        ExternalSupplyProxy,
    )
    m.add_relation_if_allowed(gas_supply, "hasOutputCarrier", "carrier.gas")
    gas_supply.connect(n_gas)

    supply_view = gas_supply.dispatch
    supply_view.is_slack = True
    supply_view.supply_capacity = 1e6

    # ------------------------------------------------------------------
    # CHP plant: Gas → Electricity + Heat  (Tier 2 MIMO representation)
    #
    #   Tier 2 uses explicit ConversionPort entities -- one per physical
    #   port, since a ConversionUnit's ports are a genuine many-per-asset
    #   relationship (see docs/schema_layout.md). The gas input port is
    #   the reference port (flow_coefficient = -1.0); all other port
    #   flows are expressed as ratios to the reference.
    #
    #   Ports:
    #     port.CHP_1.gas_in    input   Gas bus   flow_coeff = -1.00 (reference)
    #     port.CHP_1.elec_out  output  Elec bus  flow_coeff = +0.35 (η_elec)
    #     port.CHP_1.heat_out  output  Heat bus  flow_coeff = +0.45 (η_heat)
    #
    #   ConversionUnit's own dispatch attributes (flattened directly
    #   onto the asset) declare dispatch participation and referencePort;
    #   the port entities carry the conversion coefficients.
    # ------------------------------------------------------------------
    m.add_entity(entity_class="GenericConversionUnit", entity_id="CHP_1")
    m.add_attribute("CHP_1", "name", "CHP plant")

    # ── Tier 2: ConversionPort entities ───────────────────────────────────
    # Reference port: gas input (flow_coefficient = -1.0, negative = withdrawal)
    m.add_entity(entity_class="ConversionPort", entity_id="port.CHP_1.gas_in")
    m.add_attribute("port.CHP_1.gas_in", "port_direction",    "input")
    m.add_attribute("port.CHP_1.gas_in", "flow_coefficient",  -1.0)
    m.add_relation("port.CHP_1.gas_in",  "belongsToUnit",     "CHP_1")
    m.add_relation("port.CHP_1.gas_in",  "atNode",            n_gas)
    m.add_relation("port.CHP_1.gas_in",  "hasCarrier",        "carrier.gas")
    m.add_relation("CHP_1", "referencePort", "port.CHP_1.gas_in")

    # Electricity output port
    m.add_entity(entity_class="ConversionPort", entity_id="port.CHP_1.elec_out")
    m.add_attribute("port.CHP_1.elec_out", "port_direction",    "output")
    m.add_attribute("port.CHP_1.elec_out", "flow_coefficient",   0.35)
    m.add_attribute("port.CHP_1.elec_out", "maximum_output_power", 35.0)
    m.add_relation("port.CHP_1.elec_out",  "belongsToUnit",     "CHP_1")
    m.add_relation("port.CHP_1.elec_out",  "atNode",            n_elec)
    m.add_relation("port.CHP_1.elec_out",  "hasCarrier",        "carrier.electricity")

    # Heat output port
    m.add_entity(entity_class="ConversionPort", entity_id="port.CHP_1.heat_out")
    m.add_attribute("port.CHP_1.heat_out", "port_direction",    "output")
    m.add_attribute("port.CHP_1.heat_out", "flow_coefficient",   0.45)
    m.add_attribute("port.CHP_1.heat_out", "maximum_output_power", 45.0)
    m.add_relation("port.CHP_1.heat_out",  "belongsToUnit",     "CHP_1")
    m.add_relation("port.CHP_1.heat_out",  "atNode",            n_heat)
    m.add_relation("port.CHP_1.heat_out",  "hasCarrier",        "carrier.heat")

    # Operational parameters are held directly on CHP_1 itself (see
    # CHANGELOG.md: this toolbox's "initial version without views").

    # ------------------------------------------------------------------
    # Demand: electricity + heat
    # ------------------------------------------------------------------
    for lid, name, demand_mwh, node in [
        ("LOAD_ELEC", "Electricity demand", 200_000.0, n_elec),
        ("LOAD_HEAT", "Heat demand",        300_000.0, n_heat),
    ]:
        m.add_entity(entity_class="DemandUnit", entity_id=lid)
        m.add_relation(lid, "atNode", node)
        m.add_attribute(lid, "name", name)
        load = m.get_entity(entity_id=lid)
        load.dispatch.annual_energy_demand = demand_mwh

    return m

def main() -> None:
    root       = _repo_root()
    schema_dir = root / "schemas/cesdm"
    out_dir    = root / "output" / "multienergy" / "cesdm"
    out_dir.mkdir(parents=True, exist_ok=True)

    model  = build_multienergy_model(schema_dir)

    print(model.summary())
    print()

    errors = model.validate()
    if errors:
        print("Model has validation issues:")
        for e in errors:
            print("  -", e)
    else:
        print("Model validated successfully.")

    # Hierarchical YAML — representations nested under each asset
    model.export_yaml_hierarchical(out_dir / "yaml" / "multienergy_hierarchical.yaml")

    # Flat YAML — one section per class
    model.export_yaml(out_dir/ "yaml" / "multienergy_flat.yaml")

    # Frictionless Data Package — self-describing, one CSV per class
    model.export_frictionless(
        out_dir / "frictionless",
        name  = "cesdm-multienergy-demo",
        title = "Multi-energy CESDM Demo Model",
    )

    print(f"Wrote outputs to: {out_dir}")
    print(f"  {out_dir / 'yaml' / 'multienergy_hierarchical.yaml'}")
    print(f"  {out_dir / 'yaml' / 'multienergy_flat.yaml'}")
    print(f"  {out_dir / 'frictionless' / 'datapackage.json'}")

if __name__ == "__main__":
    main()
