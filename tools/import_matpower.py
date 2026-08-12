"""MATPOWER -> CESDM importer.

This module imports a MATPOWER case into CESDM. It supports the standard
MATPOWER power-flow core:

* ``mpc.bus``    -> ``ElectricalBus`` + optional demand units + bus power-flow views
* ``mpc.gen``    -> ``GenerationUnit`` + topology/dispatch/power-flow views
* ``mpc.branch`` -> ``TransmissionLine`` or ``Transformer`` + topology/power-flow views

The importer accepts either an in-memory MATPOWER case dictionary or a MATLAB
``.m`` case file. For ordinary MATPOWER files, a lightweight built-in parser is
used. If that parser cannot read a file, users may install ``pypower`` and pass
its loaded case dictionary to :func:`import_matpower_case`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from cesdm_toolbox import CesdmModel, build_model_from_yaml


# MATPOWER column indices -----------------------------------------------------
BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, VM, VA, BASE_KV, ZONE, VMAX, VMIN = range(13)
GEN_BUS, PG, QG, QMAX, QMIN, VG, MBASE, GEN_STATUS, PMAX, PMIN = range(10)
F_BUS, T_BUS, BR_R, BR_X, BR_B, RATE_A, RATE_B, RATE_C, TAP, SHIFT, BR_STATUS, ANGMIN, ANGMAX = range(13)


def _as_rows(value: Any) -> list[list[float]]:
    """Convert numpy arrays / lists to a plain list-of-lists of floats."""
    if value is None:
        return []
    try:
        # numpy array or pandas-like object
        value = value.tolist()
    except Exception:
        pass
    rows = value if isinstance(value, list) else []
    if rows and not isinstance(rows[0], (list, tuple)):
        rows = [rows]
    out: list[list[float]] = []
    for row in rows:
        out.append([float(x) for x in row])
    return out


def _parse_numeric_matrix(text: str, key: str) -> list[list[float]]:
    """Parse ``mpc.<key> = [ ... ];`` from a MATPOWER ``.m`` file."""
    pattern = rf"mpc\.{re.escape(key)}\s*=\s*\[(.*?)\];"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    body = match.group(1)
    rows: list[list[float]] = []
    for raw_line in body.splitlines():
        line = raw_line.split("%", 1)[0].strip()
        if not line:
            continue
        line = line.rstrip(";").strip()
        if not line:
            continue
        parts = re.split(r"[\s,]+", line)
        try:
            rows.append([float(p) for p in parts if p != ""])
        except ValueError:
            # Ignore non-numeric lines; MATPOWER matrices should be numeric.
            continue
    return rows


def load_matpower_case(path: str | Path) -> dict[str, Any]:
    """Load a MATPOWER ``.m`` case file into a Python dictionary.

    The built-in parser supports the common MATPOWER case structure with
    ``mpc.version``, ``mpc.baseMVA``, ``mpc.bus``, ``mpc.gen``, ``mpc.branch``
    and optional ``mpc.gencost`` matrices.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")

    base_match = re.search(r"mpc\.baseMVA\s*=\s*([0-9eE+\-.]+)\s*;", text)
    version_match = re.search(r"mpc\.version\s*=\s*['\"]([^'\"]+)['\"]\s*;", text)

    case = {
        "version": version_match.group(1) if version_match else "2",
        "baseMVA": float(base_match.group(1)) if base_match else 100.0,
        "bus": _parse_numeric_matrix(text, "bus"),
        "gen": _parse_numeric_matrix(text, "gen"),
        "branch": _parse_numeric_matrix(text, "branch"),
        "gencost": _parse_numeric_matrix(text, "gencost"),
    }

    if not case["bus"]:
        raise ValueError(f"No mpc.bus matrix found in MATPOWER case: {p}")
    return case


def _ensure_basics(model: CesdmModel, *, region_id: str, region_name: str) -> None:
    model.ensure_carrier("carrier.electricity", name="Electricity")
    model.ensure_carrier("carrier.natural_gas", name="Natural gas")
    model.ensure_entity(class_name="CarrierDomain", entity_id="domain.electricity", name="Electricity domain")
    model.add_relation_if_allowed("domain.electricity", "hasCarrier", "carrier.electricity")
    model.ensure_entity(class_name="GeographicalRegion", entity_id=region_id, name=region_name)


def _bus_entity_id(bus_number: int | float) -> str:
    return f"mp.bus.{int(bus_number)}"


def import_matpower_case(
    case: dict[str, Any],
    *,
    schema_dir: str | Path = "schemas/cesdm",
    model: CesdmModel | None = None,
    region_id: str = "region.default",
    region_name: str = "Default region",
) -> CesdmModel:
    """Import an in-memory MATPOWER case dictionary into a CESDM model."""
    if model is None:
        model = build_model_from_yaml(schema_dir)

    _ensure_basics(model, region_id=region_id, region_name=region_name)

    bus_rows = _as_rows(case.get("bus"))
    gen_rows = _as_rows(case.get("gen"))
    branch_rows = _as_rows(case.get("branch"))
    base_mva = float(case.get("baseMVA", 100.0) or 100.0)
    bus_lookup = {int(row[BUS_I]): row for row in bus_rows if len(row) > BUS_I}

    # Buses and embedded bus demands.
    for row in bus_rows:
        if len(row) < 10:
            continue
        bus_no = int(row[BUS_I])
        btype = int(row[BUS_TYPE])
        bid = _bus_entity_id(bus_no)
        model.add_entity(entity_class="ElectricalBus", entity_id=bid)
        if len(row) > BASE_KV:
            model.add_attribute(bid, "nominal_voltage", float(row[BASE_KV]))
        model.add_relation_if_allowed(bid, "belongsToGeographicalRegion", region_id)
        model.add_relation_if_allowed(bid, "belongsToCarrierDomain", "domain.electricity")
        model.set_attribute_if_allowed(bid, "name", f"MATPOWER bus {bus_no}")

        pd = float(row[PD]) if len(row) > PD else 0.0
        qd = float(row[QD]) if len(row) > QD else 0.0
        if abs(pd) > 0 or abs(qd) > 0:
            did = f"mp.load.{bus_no}"
            model.add_entity(entity_class="DemandUnit", entity_id=did)
            model.add_relation(did, "atNode", bid)
            model.ensure_carrier("carrier.electricity")
            model.add_relation_if_allowed(did, "hasInputCarrier", "carrier.electricity")
            model.set_attribute_if_allowed(did, "active_power_demand", pd, unit="MW")
            model.set_attribute_if_allowed(did, "reactive_power_demand", qd, unit="MVAr")

        gs = float(row[GS]) if len(row) > GS else 0.0
        bs = float(row[BS]) if len(row) > BS else 0.0
        if abs(gs) > 0 or abs(bs) > 0:
            sid = f"mp.shunt.{bus_no}"
            model.ensure_entity(class_name="ShuntUnit", entity_id=sid)
            model.set_attribute_if_allowed(sid, "name", f"MATPOWER shunt at bus {bus_no}")
            model.connect_single_port(sid, bid)
            model.set_attribute_if_allowed(sid, "active_power_injection", gs, unit="MW")
            model.set_attribute_if_allowed(sid, "reactive_power_injection", bs, unit="MVAr")

    # Generators.
    for idx, row in enumerate(gen_rows):
        if len(row) < 10:
            continue
        status = int(row[GEN_STATUS]) if len(row) > GEN_STATUS else 1
        if status == 0:
            continue
        bus_no = int(row[GEN_BUS])
        bid = _bus_entity_id(bus_no)
        if not model.has_entity(bid):
            continue
        gid = f"mp.gen.{idx}"
        pmax = float(row[PMAX]) if len(row) > PMAX else abs(float(row[PG]))
        pmin = float(row[PMIN]) if len(row) > PMIN else 0.0
        model.add_entity(entity_class="GenerationUnit", entity_id=gid)
        model.set_technology(gid, "Generation.Generic.MATPOWER", technology_class="GeneratorType")
        model.ensure_carrier("carrier.electricity")
        model.add_relation_if_allowed(gid, "hasOutputCarrier", "carrier.electricity")
        model.add_relation(gid, "atNode", bid)
        if pmax > 0:
            model.set_attribute_if_allowed(gid, "nominal_power_capacity", pmax)
        model.set_attribute_if_allowed(gid, "name", f"MATPOWER generator {idx}")
        bus_row = bus_lookup.get(bus_no)
        bus_type = int(bus_row[BUS_TYPE]) if bus_row is not None and len(bus_row) > BUS_TYPE else 2
        # PQ/PV/slack is a bus classification (ElectricalBus), not a generator attr.
        powerflow_bus_type = "slack" if bus_type == 3 else "PV" if bus_type == 2 else "PQ"
        model.set_attribute_if_allowed(bid, "powerflow_bus_type", powerflow_bus_type)
        model.set_attribute_if_allowed(gid, "active_power_setpoint", float(row[PG]), unit="MW")
        model.set_attribute_if_allowed(gid, "reactive_power_setpoint", float(row[QG]), unit="MVAr")
        model.set_attribute_if_allowed(gid, "maximum_reactive_power_output", (float(row[QMAX]), "MVAr") if len(row) > QMAX else None)
        model.set_attribute_if_allowed(gid, "minimum_reactive_power_output", (float(row[QMIN]), "MVAr") if len(row) > QMIN else None)
        model.set_attribute_if_allowed(gid, "voltage_magnitude_setpoint", float(row[VG]) if len(row) > VG else (float(bus_row[VM]) if bus_row is not None and len(bus_row) > VM else 1.0))
        model.set_attribute_if_allowed(gid, "voltage_angle_setpoint", float(bus_row[VA]) if bus_row is not None and len(bus_row) > VA else None)
        dv = gid
        if dv:
            model.set_attribute_if_allowed(dv, "minimum_power_output", pmin, unit="MW")
            model.set_attribute_if_allowed(dv, "maximum_power_output", pmax, unit="MW")
            model.set_attribute_if_allowed(dv, "base_power", base_mva, unit="MVA")

    # Branches / lines. MATPOWER branch impedance/admittance values are
    # stored as per-unit branch totals on the MATPOWER system base.  CESDM stores
    # physical line parameters, so the importer converts these values to
    # Ohm/km and microS/km using the branch voltage base and case baseMVA.
    # Since MATPOWER has no physical line length, line_length = 1 km is used.
    for idx, row in enumerate(branch_rows):
        if len(row) < 11:
            continue
        status = int(row[BR_STATUS]) if len(row) > BR_STATUS else 1
        if status == 0:
            continue
        fb = _bus_entity_id(int(row[F_BUS]))
        tb = _bus_entity_id(int(row[T_BUS]))
        if not model.has_entity(fb) or not model.has_entity(tb):
            continue
        tap = float(row[TAP]) if len(row) > TAP else 0.0
        shift = float(row[SHIFT]) if len(row) > SHIFT else 0.0
        is_transformer = abs(tap) > 0.0 and abs(tap - 1.0) > 1e-12
        lid = f"mp.transformer.{idx}" if is_transformer else f"mp.branch.{idx}"
        if is_transformer:
            model.ensure_entity(class_name="Transformer", entity_id=lid)
            model.connect_two_port(lid, fb, tb)
            lid
            model.set_attribute_if_allowed(lid, "name", f"MATPOWER transformer branch {idx}")
        else:
            model.add_entity(entity_class="TransmissionLine", entity_id=lid)
            model.add_relation(lid, "fromNode", fb)
            model.add_relation(lid, "toNode", tb)
            model.set_attribute_if_allowed(lid, "name", f"MATPOWER branch {idx}")
        pfv = lid
        if pfv:
            # MATPOWER stores r, x, b as per-unit branch totals on case baseMVA.
            # CESDM stores physical branch parameters per km:
            #   R/X  -> Ohm/km
            #   B    -> microS/km (shunt susceptance, not capacitance)
            # Since MATPOWER cases do not provide physical line lengths, use
            # line_length = 1 km and store total physical values as per-km values.
            model.set_attribute_if_allowed(pfv, "line_length", 1.0, unit="km")
            try:
                vn_from_kv = float(bus_lookup[int(row[F_BUS])][BASE_KV])
            except Exception:
                vn_from_kv = 110.0
            try:
                vn_to_kv = float(bus_lookup[int(row[T_BUS])][BASE_KV])
            except Exception:
                vn_to_kv = vn_from_kv
            z_base_ohm = (vn_from_kv * vn_from_kv) / float(base_mva or 100.0) if vn_from_kv > 0 else 1.0
            r_ohm_per_km = float(row[BR_R]) * z_base_ohm
            x_ohm_per_km = float(row[BR_X]) * z_base_ohm
            b_micro_s_per_km = (float(row[BR_B]) / z_base_ohm) * 1e6
            model.set_attribute_if_allowed(pfv, "series_resistance_per_km", r_ohm_per_km, unit="Ohm/km")
            model.set_attribute_if_allowed(pfv, "series_reactance_per_km", x_ohm_per_km, unit="Ohm/km")
            model.set_attribute_if_allowed(pfv, "shunt_susceptance_per_km", b_micro_s_per_km, unit="microS/km")
            model.set_attribute_if_allowed(pfv, "line_parameter_basis", "physical")
            model.set_attribute_if_allowed(pfv, "base_power", base_mva, unit="MVA")
            model.set_attribute_if_allowed(pfv, "thermal_capacity_rating", float(row[RATE_A]), unit="MVA")
            if is_transformer:
                model.set_attribute_if_allowed(pfv, "rated_primary_voltage", vn_from_kv, unit="kV")
                model.set_attribute_if_allowed(pfv, "rated_secondary_voltage", vn_to_kv, unit="kV")
            model.set_attribute_if_allowed(pfv, "tap_ratio", tap if tap != 0 else 1.0)
            model.set_attribute_if_allowed(pfv, "phase_shift_angle", shift, unit="degree")

    return model


def import_matpower_file(
    path: str | Path,
    *,
    schema_dir: str | Path = "schemas/cesdm",
    model: CesdmModel | None = None,
    region_id: str = "region.default",
    region_name: str = "Default region",
) -> CesdmModel:
    """Load a MATPOWER ``.m`` file and import it into CESDM."""
    case = load_matpower_case(path)
    return import_matpower_case(
        case,
        schema_dir=schema_dir,
        model=model,
        region_id=region_id,
        region_name=region_name,
    )


def verify_matpower_import(model: CesdmModel, case: dict[str, Any]) -> dict[str, Any]:
    """Run simple structural checks after importing MATPOWER into CESDM."""
    bus_rows = _as_rows(case.get("bus"))
    gen_rows = [r for r in _as_rows(case.get("gen")) if len(r) <= GEN_STATUS or int(r[GEN_STATUS]) != 0]
    branch_rows = [r for r in _as_rows(case.get("branch")) if len(r) <= BR_STATUS or int(r[BR_STATUS]) != 0]
    demand_rows = [r for r in bus_rows if len(r) > QD and (abs(float(r[PD])) > 0 or abs(float(r[QD])) > 0)]
    shunt_rows = [r for r in bus_rows if len(r) > BS and (abs(float(r[GS])) > 0 or abs(float(r[BS])) > 0)]
    line_rows = [r for r in branch_rows if len(r) <= TAP or abs(float(r[TAP])) <= 0.0 or abs(float(r[TAP]) - 1.0) <= 1e-12]
    transformer_rows = [r for r in branch_rows if len(r) > TAP and abs(float(r[TAP])) > 0.0 and abs(float(r[TAP]) - 1.0) > 1e-12]

    errors: list[str] = []
    if len(model.entities.get("ElectricalBus") or {}) < len(bus_rows):
        errors.append("Not all MATPOWER buses were imported as ElectricalBus entities.")
    if len(model.entities.get("DemandUnit") or {}) < len(demand_rows):
        errors.append("Not all non-zero MATPOWER bus demands were imported as DemandUnit entities.")
    if len(model.entities.get("ShuntUnit") or {}) < len(shunt_rows):
        errors.append("Not all non-zero MATPOWER bus shunts were imported as ShuntUnit entities.")
    gen_count = sum(len(model.entities.get(c) or {}) for c in [
        "GenerationUnit", "HydroGenerationUnit",
    ])
    if gen_count < len(gen_rows):
        errors.append("Not all active MATPOWER generators were imported as generation assets.")
    if len(model.entities.get("TransmissionLine") or {}) < len(line_rows):
        errors.append("Not all active MATPOWER line branches were imported as TransmissionLine entities.")
    if len(model.entities.get("Transformer") or {}) < len(transformer_rows):
        errors.append("Not all active MATPOWER transformer branches were imported as Transformer entities.")
    return {"ok": not errors, "errors": errors}


__all__ = [
    "load_matpower_case",
    "import_matpower_case",
    "import_matpower_file",
    "verify_matpower_import",
]
