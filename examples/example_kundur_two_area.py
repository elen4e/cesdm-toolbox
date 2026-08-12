"""
Kundur Two-Area System — CESDM dynamic and power flow representation
====================================================================

Reproduces the classic four-machine, two-area benchmark from:

  P. Kundur, *Power System Stability and Control*,
  McGraw-Hill, 1994, Chapter 12, pp. 813–816.

Network summary
---------------
  Area 1: Generators G1 (bus 1) and G2 (bus 2)
  Area 2: Generators G3 (bus 3) and G4 (bus 4)
  Load buses: bus 7 (area 1, 967 MW + 100 MVAr) and bus 9 (area 2, 1767 MW + 100 MVAr)
  Tie-line: buses 7–9 via two parallel 110 km, 220 kV lines (~400 MW transfer)
  Step-up transformers: buses 1–5, 2–6, 3–11, 4–10
  Area intermediate buses: 5, 6, 7, 8, 9, 10, 11 at 230 kV

Unit convention
---------------
  All four generators are identical:
    Sn = 900 MVA,  Vn = 20 kV,  fn = 60 Hz

  CESDM stores all reactances in ohm referred to the machine's own base:
    Z_base = Vn² / Sn = 20² / 900 = 0.4444 Ω

  Per-unit source values (Kundur Table 12.6) are converted on input:
    X_ohm = X_pu × Z_base

  Transformer short-circuit voltage is stored in percent (attributes.yaml:
  short_circuit_voltage_in_percentage, unit = percent).

  Line impedances are stored per km (ohm/km, S/km) with line_length [km],
  converted from Kundur's total pu on the system base (100 MVA, 230 kV):
    Z_base_sys = 230² / 100 = 529 Ω
    X_ohm_per_km = (x_pu × Z_base_sys) / length_km
    B_S_per_km   = (b_pu / Z_base_sys) / length_km

  Power flow quantities (MW, MVAr) are absolute — no conversion needed.

Usage
-----
  python examples/example_kundur_two_area.py
  python examples/example_kundur_two_area.py --export-dir /tmp/kundur_out
  python examples/example_kundur_two_area.py --export-yaml /tmp/kundur.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

_REPO_ROOT = _repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from cesdm_toolbox import build_model_from_yaml  # noqa: E402

SCHEMA_DIR = _REPO_ROOT / "schemas/cesdm"

# ═════════════════════════════════════════════════════════════════════════════
# Impedance bases
# ═════════════════════════════════════════════════════════════════════════════

# Machine base (all four generators identical)
Sn_mva = 900.0   # MVA
Vn_kv  = 20.0    # kV (generator terminal)
Z_base_machine = Vn_kv**2 / Sn_mva   # = 0.4444 Ω

# System base (for network branches)
S_sys_mva = 100.0    # MVA system base
V_sys_kv  = 230.0    # kV network base
Z_base_sys = V_sys_kv**2 / S_sys_mva  # = 529 Ω


def pu_to_ohm(x_pu: float, z_base: float) -> float:
    """Convert a per-unit reactance/resistance to ohm (used for network branches)."""
    return round(x_pu * z_base, 6)


def pu_to_mw(p_pu: float, s_base_mva: float) -> float:
    """Convert a per-unit power to MW (used for governor limits only)."""
    return round(p_pu * s_base_mva, 4)


def pu_to_siemens(b_pu: float, z_base: float) -> float:
    """Convert a per-unit susceptance to siemens (B_S = b_pu / Z_base)."""
    return round(b_pu / z_base, 8)


# ═════════════════════════════════════════════════════════════════════════════
# Source data in per unit (Kundur 1994, Tables 12.6, 12.7, 12.8)
# ═════════════════════════════════════════════════════════════════════════════

# Machine — subtransient model, all values in pu on machine base (Sn=900 MVA, Vn=20 kV)
# Machine parameters in pu on machine base (Sn=900 MVA, Vn=20 kV).
# Attribute ids match DynamicMachineModelType.Synchronous's attributes exactly.
# Reference: Kundur (1994) Table 12.6.
_MACHINE_PU = {
    "machine_model_order":      "subtransient_6th",
    "inertia_constant":          6.5,    # s
    "damping_coefficient":          0.0,    # pu
    "d_axis_synchronous_reactance":         1.8,    "q_axis_synchronous_reactance":        1.7,
    "d_axis_transient_reactance":   0.3,    "q_axis_transient_reactance":  0.55,
    "d_axis_transient_open_circuit_time_constant":  8.0,    "q_axis_transient_open_circuit_time_constant": 0.4,
    "d_axis_subtransient_reactance":  0.25,   "q_axis_subtransient_reactance": 0.25,
    "d_axis_subtransient_open_circuit_time_constant": 0.03,   "q_axis_subtransient_open_circuit_time_constant": 0.05,
    "armature_resistance":         0.0025, "stator_leakage_reactance":        0.2,
}

# AVR — SEXS simplified exciter (all four machines identical)
_AVR = {
    "AVR_SEXS_Ka":  200.0,  # pu
    "AVR_SEXS_Ta":  0.01,   # s
    "AVR_Efd_min": -3.0,    # pu
    "AVR_Efd_max":  6.0,    # pu
}

# PSS — STAB1 dual lead-lag (all four machines identical)
_PSS = {
    "PSS_STAB1_Kstab": 20.0,  # pu
    "PSS_STAB1_Tw":    10.0,  # s
    "PSS_STAB1_T1":     0.05, # s
    "PSS_STAB1_T2":     0.02, # s
    "PSS_STAB1_T3":     3.0,  # s
    "PSS_STAB1_T4":     5.4,  # s
    "PSS_Vs_max":       0.1,  # pu
    "PSS_Vs_min":      -0.1,  # pu
}

# Governor — IEEEG1 simplified steam (all four machines identical)
# Pmax/Pmin in pu on machine base → converted to MW below
_GOV_PU = {
    "GOV_IEEEG1_R":  0.05,  # pu droop
    "GOV_IEEEG1_T1": 0.1,   # s
    "GOV_IEEEG1_T2": 0.0,   # s
    "GOV_IEEEG1_T3": 0.3,   # s
    "Pmax_pu":       1.0,   # pu → MW (converted below)
    "Pmin_pu":       0.0,   # pu → MW
}


# Power flow bus type assignment (Kundur two-area, standard convention)
#   bus.1  — slack (G1 reference bus, area 1 angular reference)
#   bus.2  — PV    (G2, voltage-controlled generator bus)
#   bus.3  — PV    (G3, voltage-controlled generator bus)
#   bus.4  — PV    (G4, voltage-controlled generator bus)
#   all others — PQ (passive transmission and load buses)
_GEN_PF = {
    "gen.g1": {"active_power_setpoint": 700.0, "reactive_power_setpoint": 185.0, "voltage_magnitude_setpoint": 1.03, "voltage_angle_setpoint":  20.2},
    "gen.g2": {"active_power_setpoint": 700.0, "reactive_power_setpoint": 235.0, "voltage_magnitude_setpoint": 1.01, "voltage_angle_setpoint":  10.5},
    "gen.g3": {"active_power_setpoint": 719.0, "reactive_power_setpoint": 176.0, "voltage_magnitude_setpoint": 1.03, "voltage_angle_setpoint":  -6.8},
    "gen.g4": {"active_power_setpoint": 700.0, "reactive_power_setpoint": 202.0, "voltage_magnitude_setpoint": 1.01, "voltage_angle_setpoint": -17.0},
}
# Bus classification lives on ElectricalBus (not on GenerationUnit).
_BUS_PF_TYPE = {
    "bus.1": "slack",
    "bus.2": "PV",
    "bus.3": "PV",
    "bus.4": "PV",
}

# Bus topology: (bus_id, nominal_voltage_kv, area_label)
_BUSES = [
    ("bus.1",  20.0, "Area 1"),
    ("bus.2",  20.0, "Area 1"),
    ("bus.3",  20.0, "Area 2"),
    ("bus.4",  20.0, "Area 2"),
    ("bus.5", 230.0, "Area 1"),
    ("bus.6", 230.0, "Area 1"),
    ("bus.7", 230.0, "Area 1"),
    ("bus.8", 230.0, "Tie"),
    ("bus.9", 230.0, "Area 2"),
    ("bus.10",230.0, "Area 2"),
    ("bus.11",230.0, "Area 2"),
]

# Transformers: (id, from_bus, to_bus, x_pu on system base, rated_mva)
# Leakage reactance 0.15 pu on 900 MVA machine base
# → short_circuit_voltage_in_percentage = 0.15 × (900/100) × 100 % = 15 % on 100 MVA system base
# stored as short_circuit_voltage_in_percentage [%] on system base per attributes.yaml
_TRANSFORMERS = [
    ("tfr.t1", "bus.1", "bus.5",  15.0, 900.0),   # 15 % on 900 MVA
    ("tfr.t2", "bus.2", "bus.6",  15.0, 900.0),
    ("tfr.t3", "bus.3", "bus.11", 15.0, 900.0),
    ("tfr.t4", "bus.4", "bus.10", 15.0, 900.0),
]

# Lines: (id, from_bus, to_bus, r_pu, x_pu, b_pu, length_km)
# pu totals on system base (100 MVA, 230 kV); lengths from Kundur Ch. 12.
_LINES = [
    ("line.l1",  "bus.5", "bus.6",  0.0,    0.0167, 0.0,  25.0),
    ("line.l2",  "bus.6", "bus.7",  0.0,    0.0167, 0.0,  10.0),
    ("line.l3",  "bus.7", "bus.8",  0.0022, 0.022,  0.33, 110.0),
    ("line.l4a", "bus.8", "bus.9",  0.0022, 0.022,  0.33, 110.0),  # first tie-line
    ("line.l4b", "bus.8", "bus.9",  0.0022, 0.022,  0.33, 110.0),  # parallel tie-line
    ("line.l5",  "bus.9", "bus.10", 0.0,    0.0167, 0.0,  10.0),
    ("line.l6", "bus.10","bus.11",  0.0,    0.0167, 0.0,  25.0),
]

# Loads: (id, bus, P [MW], Q [MVAr])
_LOADS = [
    ("load.d7", "bus.7",  967.0, 100.0),
    ("load.d9", "bus.9", 1767.0, 100.0),
]

_GEN_BUSES = {
    "gen.g1": "bus.1", "gen.g2": "bus.2",
    "gen.g3": "bus.3", "gen.g4": "bus.4",
}
_GEN_NAMES = {
    "gen.g1": "G1 (Area 1)", "gen.g2": "G2 (Area 1)",
    "gen.g3": "G3 (Area 2)", "gen.g4": "G4 (Area 2)",
}


# ═════════════════════════════════════════════════════════════════════════════
# Derived machine parameters in physical units
# ═════════════════════════════════════════════════════════════════════════════

def machine_params() -> dict:
    """Return the reusable synchronous-machine model parameters."""
    return dict(_MACHINE_PU)


def gov_params_physical() -> dict:
    """Return governor parameters converted to MW for power limits."""
    g = _GOV_PU
    gov = {k: v for k, v in _GOV_PU.items() if not k.startswith("P")}
    gov["GOV_Pmax"] = pu_to_mw(_GOV_PU["Pmax_pu"], Sn_mva)
    gov["GOV_Pmin"] = pu_to_mw(_GOV_PU["Pmin_pu"], Sn_mva)
    return gov


# ═════════════════════════════════════════════════════════════════════════════
# Model builder
# ═════════════════════════════════════════════════════════════════════════════

def build_kundur(model):
    """Populate a CesdmModel with the full Kundur two-area dataset.

    Built entirely with core add_entity/add_attribute/add_relation calls
    and typed proxy properties, including the reusable dynamic-model-type
    and controller entities (DynamicMachineModelType.Synchronous,
    Controller.AVR/.GOV/.PSS).
    """

    mach = machine_params()
    gov  = gov_params_physical()

    # ── Energy carrier + electricity CarrierDomain ────────────────────────────
    model.ensure_carrier(
        "carrier.electricity", name="Electricity", carrier_group="electricity",
    )
    model.add_entity(entity_class="CarrierDomain", entity_id="domain.electricity")
    model.add_relation("domain.electricity", "hasCarrier", "carrier.electricity")

    # ── Network nodes ────────────────────────────────────────────────────────
    for bus_id, kv, area in _BUSES:
        model.add_entity(entity_class="ElectricalBus", entity_id=bus_id)
        model.add_attribute(bus_id, "nominal_voltage", kv)
        model.add_attribute(bus_id, "name", f"{bus_id.upper()} ({area})")
        model.add_attribute(bus_id, "powerflow_bus_type", _BUS_PF_TYPE.get(bus_id, "PQ"))
        model.add_relation(bus_id, "belongsToCarrierDomain", "domain.electricity")

    # ── Reusable dynamic-machine model type ──────────────────────────────────
    # All four Kundur generators share the same normalized machine parameters.
    # Their individual rated bases remain on each GenerationUnit.
    dynamic_model_type_id = "dynamic_model_type.kundur.synchronous"
    model.add_entity(
        entity_class="DynamicMachineModelType.Synchronous",
        entity_id=dynamic_model_type_id,
    )
    for attr, val in mach.items():
        model.add_attribute(dynamic_model_type_id, attr, val)

    # ── Generators ────────────────────────────────────────────────────────────
    for gen_id, bus_id in _GEN_BUSES.items():
        model.add_entity(entity_class="GenerationUnit", entity_id=gen_id)
        model.add_relation(gen_id, "atNode", bus_id)
        gen = model.get_entity(entity_id=gen_id)
        gen.name = _GEN_NAMES[gen_id]

        # Power flow — all in MW / MVAr / pu / deg
        pf = gen.power_flow
        for attr, val in _GEN_PF[gen_id].items():
            setattr(pf, attr, val)

        # Generator-specific rated quantities define the per-unit base.
        gen.rated_apparent_power = Sn_mva
        gen.rated_voltage = Vn_kv

        # Reuse the shared dynamic-machine model parameter set.
        gen.usesDynamicModelType = dynamic_model_type_id

        # AVR/GOV/PSS controllers remain separate entities
        # (Controller.AVR.*/GOV.*/PSS.*), linked via controlsGenerationUnit,
        # for the same reason: every one of their attributes has a real
        # default too, and a generator can only ever have one of each, so
        # there's nothing gained from flattening them onto the generator.

        avr_id = f"dyn.avr.{gen_id}"
        model.add_entity(entity_class="Controller.AVR.SEXS", entity_id=avr_id)
        model.add_relation(avr_id, "controlsGenerationUnit", gen_id)
        for attr, val in _AVR.items():
            model.add_attribute(avr_id, attr, val)
        gen.hasAutomaticVoltageRegulator = avr_id

        pss_id = f"dyn.pss.{gen_id}"
        model.add_entity(entity_class="Controller.PSS.STAB1", entity_id=pss_id)
        model.add_relation(pss_id, "controlsGenerationUnit", gen_id)
        for attr, val in _PSS.items():
            model.add_attribute(pss_id, attr, val)
        gen.hasPowerSystemStabilizer = pss_id

        gov_id = f"dyn.gov.{gen_id}"
        model.add_entity(entity_class="Controller.GOV.IEEEG1", entity_id=gov_id)
        model.add_relation(gov_id, "controlsGenerationUnit", gen_id)
        for attr, val in gov.items():
            model.add_attribute(gov_id, attr, val)
        gen.hasTurbineGovernor = gov_id

    # ── Transformers ────────────────────────────────────────────────────────
    for tfr_id, from_bus, to_bus, scc_pct, rated_mva in _TRANSFORMERS:
        model.add_entity(entity_class="Transformer", entity_id=tfr_id)
        model.add_attribute(tfr_id, "name", tfr_id.upper())
        tfr = model.get_entity(entity_id=tfr_id)
        tfr.connect(from_bus, to_bus)

        pf = tfr.power_flow
        pf.short_circuit_voltage_in_percentage = scc_pct  # %
        pf.rated_primary_voltage = 230.0    # kV HV
        pf.rated_secondary_voltage = 20.0    # kV LV
        pf.thermal_capacity_rating = rated_mva  # MVA

    # ── Transmission lines ────────────────────────────────────────────────────
    for line_id, from_bus, to_bus, r_pu, x_pu, b_pu, length_km in _LINES:
        model.add_entity(entity_class="TransmissionLine", entity_id=line_id)
        model.add_relation(line_id, "fromNode", from_bus)
        model.add_relation(line_id, "toNode", to_bus)
        line = model.get_entity(entity_id=line_id)
        line.name = line_id.upper()

        # Convert total pu → Ω/km / S/km on system base
        pf = line.power_flow
        pf.line_length = length_km
        pf.series_resistance_per_km = pu_to_ohm(r_pu, Z_base_sys) / length_km
        pf.series_reactance_per_km = pu_to_ohm(x_pu, Z_base_sys) / length_km
        pf.shunt_susceptance_per_km = pu_to_siemens(b_pu, Z_base_sys) / length_km

    # ── Loads ─────────────────────────────────────────────────────────────────
    for load_id, bus_id, p_mw, q_mvar in _LOADS:
        model.add_entity(entity_class="DemandUnit", entity_id=load_id)
        model.add_relation(load_id, "atNode", bus_id)
        load = model.get_entity(entity_id=load_id)
        load.name = f"Load @ {bus_id.upper()}"

        pf = load.power_flow
        pf.active_power_demand = p_mw     # MW
        pf.reactive_power_demand = q_mvar  # MVAr

    return model


# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════

def _val(model, eid, attr, default=None):
    """Read a scalar attribute value from any entity, class-agnostic."""
    # Model.get_attr_value needs (class, entity_id, attr); look up class first.
    for cname, ents in model.entities.items():
        if eid in ents:
            try:
                raw = model.get_attr_value(cname, eid, attr)
                return raw["value"] if isinstance(raw, dict) else raw
            except Exception:
                return default
    return default


def print_summary(model):
    print("\n" + "=" * 72)
    print("  KUNDUR TWO-AREA SYSTEM — CESDM SUMMARY")
    print("=" * 72)
    print(f"  System impedance base  : {V_sys_kv}² / {S_sys_mva} = {Z_base_sys:.1f} Ω"
          f"  (used for line/cable conversion only)")

    print(f"\n  CarrierDomain  : {list((model.entities.get('CarrierDomain') or {}).keys())}")
    print(f"  Network nodes  : {len(model.entities.get('ElectricalBus', {}))} buses"
          f" (all → domain.electricity)")
    print(f"  Generators     : {len(model.entities.get('GenerationUnit', {}))} units")
    print(f"  Transformers   : {len(model.entities.get('Transformer', {}))} units")
    print(f"  Lines          : {len(model.entities.get('TransmissionLine', {}))} circuits")
    print(f"  Loads          : {len(model.entities.get('DemandUnit', {}))} units")

    print("\n  Dynamic machine models")
    n = sum(1 for gid in model.entities.get("GenerationUnit", {})
            if model.get_entity(entity_id=gid).usesDynamicModelType)
    print(f"    {'GenerationUnit with a dynamic machine model':44s}: {n}")

    print("\n  Generator machine parameters (pu on machine base, via usesDynamicModelType)")
    xd_h, xdp_h, xdpp_h = "Xd [pu]", "X'd [pu]", "X''d [pu]"
    print(f"  {'':8s} {xd_h:>10} {xdp_h:>10} {xdpp_h:>10} {'H [s]':>6} {'Pset [MW]':>10}")
    for gen_id in _GEN_BUSES:
        gen = model.get_entity(entity_id=gen_id)
        # Shared DynamicMachineModelType — not a per-generator dyn.machine.* id.
        dyn_ids = model.get_relation_targets(gen_id, "usesDynamicModelType") or []
        dyn_id = dyn_ids[0] if dyn_ids else None
        xd = xdp = xdpp = H = "n/a"
        if dyn_id:
            xd   = _val(model, dyn_id, "d_axis_synchronous_reactance", "n/a")
            xdp  = _val(model, dyn_id, "d_axis_transient_reactance", "n/a")
            xdpp = _val(model, dyn_id, "d_axis_subtransient_reactance", "n/a")
            H    = _val(model, dyn_id, "inertia_constant", "n/a")
        pm = gen.power_flow.active_power_setpoint
        pm = pm if pm is not None else "n/a"
        fmt = lambda v, w, d: f"{v:{w}.{d}f}" if isinstance(v, (int, float)) else f"{'n/a':>{w}}"
        print(f"  {gen_id:8s}"
              f" {fmt(xd,10,4)} {fmt(xdp,10,4)} {fmt(xdpp,10,4)}"
              f" {fmt(H,6,1)} {fmt(pm,10,1)}")

    print(f"\n  (Shared type dynamic_model_type.kundur.synchronous; "
          f"Sn={Sn_mva} MVA, Vn={Vn_kv} kV)")
    print("\n  Line impedances (Ω/km, S/km from total pu on system base)")
    for line_id, fb, tb, r_pu, x_pu, b_pu, length_km in _LINES:
        pf = model.get_entity(entity_id=line_id).power_flow
        r, x, b = pf.series_resistance_per_km, pf.series_reactance_per_km, pf.shunt_susceptance_per_km
        print(f"  {line_id:12s} {fb}→{tb}  L={length_km:5.0f} km  "
              f"R={r:.4f} Ω/km  X={x:.4f} Ω/km  B={b:.6f} S/km")

    print("\n  Role classification")
    for cls in ("Controller.AVR", "Controller.AVR.SEXS", "Controller.AVR.IEEET1", "Controller.AVR.AC1A",
                "Controller.GOV", "Controller.GOV.IEEEG1", "Controller.GOV.GGOV1", "Controller.GOV.HYGOV",
                "Controller.PSS", "Controller.PSS.STAB1", "Controller.PSS.PSS2A",
                "GenerationUnit", "ElectricalBus"):
        role = model._derive_role_from_parents(cls)
        print(f"    {cls:44s} → {role}")
    print()


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Build the Kundur two-area CESDM model."
    )
    parser.add_argument("--export-dir",  metavar="DIR",  default=None,
                        help="Export as Frictionless Data Package.")
    parser.add_argument("--export-yaml", metavar="FILE", default=None,
                        help="Export as hierarchical YAML.")
    args = parser.parse_args()

    print("Loading CESDM schema …")
    model = build_model_from_yaml(str(SCHEMA_DIR))

    print("Building Kundur two-area model …")
    build_kundur(model)
    print_summary(model)

    errors = model.validate()
    if errors:
        print("Model has validation issues:")
        for e in errors:
            print("  -", e)
    else:
        print("Model validated successfully.")

    # Analysis-specific checks (schema-optional fields needed by each study).
    for profile in ("power_flow", "dynamics"):
        analysis_errors = model.validate_for_analysis(profile)
        if analysis_errors:
            print(f"\nvalidate_for_analysis('{profile}'): {len(analysis_errors)} error(s)")
            for e in analysis_errors:
                print("  -", e)
        else:
            print(f"validate_for_analysis('{profile}'): OK")

    if args.export_dir:
        out = Path(args.export_dir)
        out.mkdir(parents=True, exist_ok=True)
        dp = model.export_frictionless(
            out,
            name        = "kundur-two-area",
            title       = "Kundur Two-Area System",
            description = (
                "Four-machine two-area benchmark (Kundur 1994, Ch. 12). "
                "Subtransient machine models, SEXS AVRs, STAB1 PSSs, IEEEG1 governors. "
                "Reactances stored in ohm (machine base), line impedances in ohm/S (system base)."
            ),
            version = "1.0.0",
        )
        print(f"  Exported Frictionless package → {dp}")

    if args.export_yaml:
        model.export_yaml_hierarchical(args.export_yaml)
        print(f"  Exported YAML → {args.export_yaml}")


if __name__ == "__main__":
    main()
