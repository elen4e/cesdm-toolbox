"""CESDM -> MATPOWER exporter.

The exporter creates a MATPOWER case dictionary and can write it as a MATLAB
``.m`` case file. It supports the common power-flow core: buses, generator-like
assets, demands, transmission lines, and transformers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from cesdm_toolbox import CesdmModel


def _raw(value: Any, default=None):
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get("value", default)
    return value


def _float(value: Any, default: float = 0.0) -> float:
    try:
        v = _raw(value, default)
        if v in (None, ""):
            return default
        return float(v)
    except Exception:
        return default


def _unit(value: Any) -> str:
    """Return the unit stored in an EAR attribute dict, if present."""
    if isinstance(value, dict):
        return str(value.get("unit", "") or "").strip().lower()
    return ""


def _is_per_unit(value: Any) -> bool:
    u = _unit(value).replace(" ", "").replace("_", "-")
    return u in {"pu", "p.u.", "p.u", "per-unit", "perunit", "pu/km"}




def _matpower_number_from_bus_id(model: CesdmModel, bus_id: str, default: int) -> int:
    ent = (model.entities.get("ElectricalBus") or {}).get(bus_id)
    data = getattr(ent, "data", {}) if ent is not None else {}
    raw_no = _raw(data.get("matpower_bus_i"))
    if raw_no not in (None, ""):
        try:
            n = int(float(raw_no))
            if n >= 1:
                return n
        except Exception:
            pass
    # MATPOWER imports create stable IDs like mp.bus.69.  Preserve that
    # external bus number instead of renumbering lexicographic CESDM IDs.
    m = re.search(r"(?:^|[._-])bus[._-]?(\d+)$", bus_id, flags=re.IGNORECASE)
    if not m:
        m = re.search(r"(?:^|[._-])(\d+)$", bus_id)
    if m:
        try:
            n = int(m.group(1))
            # MATPOWER bus numbers are 1-based.  IDs imported from
            # 0-based tools such as pandapower may end in .0; do not emit
            # that literal suffix as a MATPOWER bus_i.  Fall back to the
            # exporter's 1..N numbering instead.
            if n >= 1:
                return n
        except Exception:
            pass
    return max(1, int(default))


def _sort_key_with_optional_index(model: CesdmModel, entity_id: str) -> tuple[int, str]:
    cls = model.entity_class(entity_id)
    data = getattr(model.entities[cls][entity_id], "data", {}) if cls else {}
    for key in ("matpower_gen_index", "matpower_branch_index"):
        raw_index = _raw(data.get(key))
        if raw_index not in (None, ""):
            try:
                return (int(float(raw_index)), entity_id)
            except Exception:
                pass
    m = re.search(r"(?:^|[._-])(\d+)$", entity_id)
    return (int(m.group(1)) if m else 10**9, entity_id)

def _bus_base_kv(model: CesdmModel, bus_id: str, default: float = 110.0) -> float:
    ent = (model.entities.get("ElectricalBus") or {}).get(bus_id)
    data = getattr(ent, "data", {}) if ent is not None else {}
    v = _float(data.get("nominal_voltage"), default)
    return v if v > 0 else default


def _branch_rx_b_to_matpower_pu(
    *,
    model: CesdmModel,
    data: dict[str, Any],
    from_bus: str,
    base_mva: float,
    frequency_hz: float = 50.0,
) -> tuple[float, float, float]:
    """Convert CESDM line parameters to MATPOWER r/x/b per-unit totals.

    MATPOWER expects branch r, x and b in per unit on ``mpc.baseMVA``.
    This helper supports two CESDM storage conventions:

    1. MATPOWER-origin values: unit is ``pu`` and line_length is normally 1.0.
       Values are returned as branch totals.
    2. Physical values: R/X in Ohm/km and shunt susceptance in microS/km.
       These are converted to per-unit using Z_base = V_base[kV]^2 / S_base[MVA].
       Legacy nF/km capacitance values are still accepted, but CESDM semantics
       are shunt_susceptance_per_km, not shunt_capacitance_per_km.
    """
    length = _float(data.get("line_length"), 1.0)
    if length <= 0:
        length = 1.0

    r_attr = data.get("series_resistance_per_km")
    x_attr = data.get("series_reactance_per_km")
    b_attr = data.get("shunt_susceptance_per_km")

    r = _float(r_attr, 0.0)
    x = _float(x_attr, 0.0001)
    b = _float(b_attr, 0.0)

    basis = str(_raw(data.get("line_parameter_basis"), "") or "").lower()
    if basis in {"per_unit", "per-unit", "pu"} or _is_per_unit(r_attr) or _is_per_unit(x_attr) or _is_per_unit(b_attr):
        # Values are already MATPOWER-style branch totals if length = 1.0.
        return r * length, x * length, b * length

    vn_kv = _bus_base_kv(model, from_bus)
    z_base_ohm = (vn_kv * vn_kv) / float(base_mva or 100.0)

    r_pu = (r * length) / z_base_ohm
    x_pu = (x * length) / z_base_ohm

    b_unit = _unit(b_attr).replace("µ", "micro")
    if "nf" in b_unit:
        # Legacy pandapower-style capacitance [nF/km] -> total susceptance [S].
        # New CESDM models should not use this path.
        import math
        c_f_total = b * 1e-9 * length
        b_siemens_total = 2.0 * math.pi * frequency_hz * c_f_total
        b_pu = b_siemens_total * z_base_ohm
    elif "micro" in b_unit or "us" in b_unit or "µs" in b_unit:
        # CESDM shunt susceptance [microS/km] -> total susceptance [S].
        b_pu = (b * 1e-6 * length) * z_base_ohm
    else:
        # Backwards-compatible fallback: assume S/km if explicitly given,
        # otherwise assume CESDM default microS/km for this attribute.
        if b_unit in {"s/km", "s", "siemens/km", "siemens"}:
            b_pu = (b * length) * z_base_ohm
        else:
            b_pu = (b * 1e-6 * length) * z_base_ohm

    return r_pu, x_pu, b_pu


def _relation_targets(ent) -> dict[str, list[str]]:
    data = getattr(ent, "data", {}) or {}
    out = {}
    for k, v in data.items():
        if isinstance(v, list):
            out[k] = [str(x) for x in v if x]
        elif isinstance(v, str):
            out[k] = [v]
    return out


def _view_by_asset(model: CesdmModel, view_class: str) -> dict[str, Any]:
    result = {}
    for _vid, ent in (model.entities.get(view_class) or {}).items():
        data = getattr(ent, "data", {}) or {}
        raw = data.get("reportsOn")
        targets = raw if isinstance(raw, list) else [raw]
        for aid in targets:
            if aid:
                result[str(aid)] = ent

    # Flattened pattern (see CHANGELOG.md): an asset class may have
    # view_class's attributes/relations merged directly onto it rather
    # than a separate view entity -- include those assets too, using
    # the asset entity itself as the data source. The group is derived
    # directly from view_class's own suffix string (e.g. "PowerFlowView"
    # -> "power_flow"), not looked up in the schema -- there's no view
    # class left anywhere to carry a view_family attribute to look up.
    _SUFFIX_TO_GROUP = {
        "DispatchView": "dispatch", "TopologyView": "topology",
        "PowerFlowView": "power_flow", "LocationView": "spatial",
    }
    family = next((g for suf, g in _SUFFIX_TO_GROUP.items() if view_class.endswith(suf)), None)
    if family:
        for asset_cls_name, entities in model.entities.items():
            cdef = model.classes.get(asset_cls_name)
            if cdef is None or getattr(cdef, "abstract", False):
                continue
            groups: set = set()
            for d in (getattr(cdef, "attributes", {}) or {}).values():
                groups.update(getattr(d, "belongsToGroup", None) or [])
            for d in (getattr(cdef, "relations", {}) or {}).values():
                groups.update(getattr(d, "belongsToGroup", None) or [])
            if family not in groups:
                continue
            for aid, ent in entities.items():
                result.setdefault(str(aid), ent)
    return result


def _single_port_bus(model: CesdmModel) -> dict[str, str]:
    result = {}
    # atNode is held directly on the asset itself (see CHANGELOG.md: this
    # toolbox's "initial version without views" -- there's no separate
    # SinglePort.TopologyView entity to look up any more at all).
    for asset_cls_name, entities in model.entities.items():
        cdef = model.classes.get(asset_cls_name)
        if cdef is None or getattr(cdef, "abstract", False):
            continue
        rel_groups: set = set()
        for rname, d in (getattr(cdef, "relations", {}) or {}).items():
            if rname == "atNode":
                rel_groups.update(getattr(d, "belongsToGroup", None) or [])
        if "topology" not in rel_groups:
            continue
        for aid, ent in entities.items():
            if str(aid) in result:
                continue
            node = getattr(ent, "data", {}).get("atNode")
            if isinstance(node, list):
                node = node[0] if node else None
            if node:
                result[str(aid)] = str(node)
    return result


def _two_port_buses(model: CesdmModel) -> dict[str, tuple[str, str]]:
    result = {}
    # fromNode/toNode are held directly on the asset itself (see
    # CHANGELOG.md) -- there's no separate TwoPort.TopologyView entity
    # to look up any more at all.
    for asset_cls_name, entities in model.entities.items():
        cdef = model.classes.get(asset_cls_name)
        if cdef is None or getattr(cdef, "abstract", False):
            continue
        rel_groups: set = set()
        for rname, d in (getattr(cdef, "relations", {}) or {}).items():
            if rname in ("fromNode", "toNode"):
                rel_groups.update(getattr(d, "belongsToGroup", None) or [])
        if "topology" not in rel_groups:
            continue
        for aid, ent in entities.items():
            if str(aid) in result:
                continue
            edata = getattr(ent, "data", {}) or {}
            fb = edata.get("fromNode") or edata.get("node_from")
            tb = edata.get("toNode") or edata.get("node_to")
            if isinstance(fb, list):
                fb = fb[0] if fb else None
            if isinstance(tb, list):
                tb = tb[0] if tb else None
            if fb and tb:
                result[str(aid)] = (str(fb), str(tb))
    return result


def export_matpower_case(model: CesdmModel, *, base_mva: float = 100.0) -> dict[str, Any]:
    """Build a MATPOWER case dictionary from a CESDM model.

    Returns a dictionary with ``version``, ``baseMVA``, ``bus``, ``gen``,
    ``branch`` and ``gencost`` keys. Rows follow the MATPOWER case format.
    """
    buses = model.entities.get("ElectricalBus") or {}
    provisional_bus_ids = sorted(buses.keys())
    provisional_numbers = {bid: i + 1 for i, bid in enumerate(provisional_bus_ids)}
    bus_number = {bid: _matpower_number_from_bus_id(model, bid, provisional_numbers[bid]) for bid in provisional_bus_ids}
    used_numbers: set[int] = set()
    for bid in provisional_bus_ids:
        number = int(bus_number[bid])
        if number < 1 or number in used_numbers:
            number = max(used_numbers or {0}) + 1
            bus_number[bid] = number
        used_numbers.add(number)
    bus_ids = sorted(provisional_bus_ids, key=lambda bid: (bus_number[bid], bid))

    bus_pf = _view_by_asset(model, "ElectricalBus.PowerFlowView")
    sp_bus = _single_port_bus(model)
    tp_bus = _two_port_buses(model)
    gen_pf = _view_by_asset(model, "Generator.PowerFlowView")
    dem_pf = _view_by_asset(model, "Demand.PowerFlowView")
    shunt_pf = _view_by_asset(model, "Shunt.PowerFlowView")
    line_pf = _view_by_asset(model, "TransmissionLine.PowerFlowView")
    transformer_pf = _view_by_asset(model, "Transformer.PowerFlowView")

    # Aggregate demand per bus.
    pd_qd = {bid: [0.0, 0.0] for bid in bus_ids}
    for did in (model.entities.get("DemandUnit") or {}):
        bid = sp_bus.get(did)
        if bid not in pd_qd:
            continue
        pf = dem_pf.get(did)
        if pf is not None:
            data = getattr(pf, "data", {}) or {}
            pd_qd[bid][0] += _float(data.get("active_power_demand"), 0.0)
            pd_qd[bid][1] += _float(data.get("reactive_power_demand"), 0.0)

    # Aggregate static shunts per bus. MATPOWER stores shunts in the bus
    # matrix as Gs and Bs [MW/MVAr at V=1.0 p.u.]. Keep them separate from
    # ordinary demand Pd/Qd.
    gs_bs = {bid: [0.0, 0.0] for bid in bus_ids}
    for sid in (model.entities.get("ShuntUnit") or {}):
        bid = sp_bus.get(sid)
        if bid not in gs_bs:
            continue
        pf = shunt_pf.get(sid)
        if pf is not None:
            data = getattr(pf, "data", {}) or {}
            gs_bs[bid][0] += _float(data.get("active_power_injection"), _float(data.get("active_power_demand"), 0.0))
            gs_bs[bid][1] += _float(data.get("reactive_power_injection"), _float(data.get("reactive_power_demand"), 0.0))

    # Determine generator buses; first generator bus becomes slack if no explicit slack.
    gen_asset_classes = [
        "GenerationUnit", "HydroGenerationUnit",
        "WindGenerationUnit", "SolarGenerationUnit", "ThermalGenerationUnit",
    ]
    gen_assets: list[str] = []
    for cls in gen_asset_classes:
        gen_assets.extend(sorted((model.entities.get(cls) or {}).keys(), key=lambda eid: _sort_key_with_optional_index(model, eid)))
    gen_buses = {sp_bus[g] for g in gen_assets if sp_bus.get(g) in bus_number}

    gen_pf_by_bus: dict[str, list[dict[str, Any]]] = {bid: [] for bid in bus_ids}
    for gid in gen_assets:
        bid = sp_bus.get(gid)
        if bid in gen_pf_by_bus:
            pf_ent = gen_pf.get(gid)
            pf_data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
            gen_pf_by_bus[bid].append(pf_data)

    bus_rows = []
    explicit_slack = None
    for bid in bus_ids:
        pf_ent = bus_pf.get(bid)
        bus_pf_data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
        bus_gen_pf = gen_pf_by_bus.get(bid, [])
        bus_type_str = str(_raw(bus_pf_data.get("powerflow_bus_type"), "") or "").lower()
        controlling_pf = bus_gen_pf[0] if bus_gen_pf else bus_pf_data
        if bus_type_str == "slack":
            btype = 3
            explicit_slack = bid
        elif bus_type_str == "pv" or bid in gen_buses:
            btype = 2
        else:
            btype = 1
        pd, qd = pd_qd.get(bid, [0.0, 0.0])
        gs, bs = gs_bs.get(bid, [0.0, 0.0])
        bdata = getattr(buses[bid], "data", {}) or {}
        base_kv = _float(bdata.get("nominal_voltage"), 0.0)
        vm = _float(bus_pf_data.get("voltage_magnitude_setpoint"), _float(controlling_pf.get("voltage_magnitude_setpoint"), 1.0))
        va = _float(bus_pf_data.get("voltage_angle_setpoint"), _float(controlling_pf.get("voltage_angle_setpoint"), 0.0))
        area = _float(bdata.get("matpower_bus_area"), 1.0)
        zone = _float(bdata.get("matpower_zone"), 1.0)
        vmax = _float(bdata.get("matpower_vmax"), _float(bus_pf_data.get("matpower_vmax"), 1.1))
        vmin = _float(bdata.get("matpower_vmin"), _float(bus_pf_data.get("matpower_vmin"), 0.9))
        bus_rows.append([bus_number[bid], btype, pd, qd, gs, bs, area, vm, va, base_kv, zone, vmax, vmin])

    if explicit_slack is None and bus_rows:
        # Prefer first generator bus; otherwise first exported bus number.
        slack_num = bus_number[sorted(gen_buses)[0]] if gen_buses else bus_rows[0][0]
        for row in bus_rows:
            if row[0] == slack_num:
                row[1] = 3
                break

    gen_rows = []
    gencost_rows = []
    for gid in gen_assets:
        bid = sp_bus.get(gid)
        if bid not in bus_number:
            continue
        pf_ent = gen_pf.get(gid)
        pf_data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
        # Dispatch data (nominal_power_capacity, ...) lives directly on
        # the generation asset itself -- every gen_asset_classes entry
        # is a GenerationUnit subclass, so it always carries
        # dispatch-group data by construction.
        gen_cls = model.entity_class(gid)
        dv_data = getattr(model.entities[gen_cls][gid], "data", {}) or {} if gen_cls else {}
        pg = _float(pf_data.get("active_power_setpoint"), 0.0)
        qg = _float(pf_data.get("reactive_power_setpoint"), 0.0)
        pmax = _float(dv_data.get("maximum_power_output"), _float(dv_data.get("nominal_power_capacity"), abs(pg) if pg else base_mva))
        pmin = _float(dv_data.get("minimum_power_output"), 0.0)
        vg = _float(pf_data.get("voltage_magnitude_setpoint"), 1.0)
        qmax = _float(
            pf_data.get("maximum_reactive_power_output"),
            _float(dv_data.get("maximum_reactive_power_output"), 999.0),
        )
        qmin = _float(
            pf_data.get("minimum_reactive_power_output"),
            _float(dv_data.get("minimum_reactive_power_output"), -999.0),
        )
        mbase = _float(pf_data.get("matpower_mbase"), base_mva)
        status = int(_float(pf_data.get("matpower_gen_status"), 1.0))
        gen_row = [bus_number[bid], pg, qg, qmax, qmin, vg, mbase, status, pmax, pmin]
        extra = pf_data.get("matpower_gen_row_extra", [])
        if isinstance(extra, (list, tuple)):
            gen_row.extend(float(x) for x in extra)
        gen_rows.append(gen_row)
        # Quadratic gencost placeholder: 2 startup shutdown n c2 c1 c0
        gencost_rows.append([2, 0, 0, 3, 0, 0, 0])

    branch_rows = []

    def _append_branch_row(asset_id: str, pf_index: dict[str, Any], *, is_transformer: bool) -> None:
        if asset_id not in tp_bus:
            return
        fb, tb = tp_bus[asset_id]
        if fb not in bus_number or tb not in bus_number:
            return
        pf_ent = pf_index.get(asset_id)
        data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
        if any(k in data for k in ("matpower_r", "matpower_x", "matpower_b")):
            r_pu = _float(data.get("matpower_r"), 0.0)
            x_pu = _float(data.get("matpower_x"), 0.0)
            b_pu = _float(data.get("matpower_b"), 0.0)
        else:
            r_pu, x_pu, b_pu = _branch_rx_b_to_matpower_pu(
                model=model,
                data=data,
                from_bus=fb,
                base_mva=float(base_mva),
            )
        rate_a = _float(data.get("matpower_rate_a"), _float(data.get("thermal_capacity_rating"), 0.0))
        rate_b = _float(data.get("matpower_rate_b"), rate_a)
        rate_c = _float(data.get("matpower_rate_c"), rate_a)
        angmin = _float(data.get("matpower_angmin"), -360.0)
        angmax = _float(data.get("matpower_angmax"), 360.0)
        tap = _float(data.get("tap_ratio"), 1.0)
        shift = _float(data.get("phase_shift_angle"), 0.0)
        if not is_transformer:
            tap = 0.0  # MATPOWER convention: 0 means ordinary line / nominal ratio 1
            shift = 0.0
        elif abs(tap) <= 1e-12:
            tap = 1.0
        branch_rows.append([
            bus_number[fb], bus_number[tb],
            r_pu, x_pu, b_pu,
            rate_a, rate_b, rate_c,
            tap, shift, int(_float(data.get("matpower_branch_status"), 1.0)), angmin, angmax,
        ])

    branch_assets: list[tuple[str, dict[str, Any], bool]] = []
    branch_assets.extend((lid, line_pf, False) for lid in (model.entities.get("TransmissionLine") or {}).keys())
    branch_assets.extend((tid, transformer_pf, True) for tid in (model.entities.get("Transformer") or {}).keys())
    for asset_id, pf_index, is_transformer in sorted(branch_assets, key=lambda item: _sort_key_with_optional_index(model, item[0])):
        _append_branch_row(asset_id, pf_index, is_transformer=is_transformer)

    return {
        "version": "2",
        "baseMVA": float(base_mva),
        "bus": bus_rows,
        "gen": gen_rows,
        "branch": branch_rows,
        "gencost": gencost_rows,
        "bus_lookup": bus_number,
    }


def write_matpower_case(case: dict[str, Any], path: str | Path, *, function_name: str = "case_cesdm") -> Path:
    """Write a MATPOWER ``.m`` case file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    def _matrix(rows):
        import numpy as np

        if rows is None:
            return ""

        arr = np.asarray(rows)

        if arr.size == 0:
            return ""

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        return "\n".join(
            "\t" + "\t".join(f"{float(v):.10g}" for v in row) + ";"
            for row in arr
        )
    text = f"function mpc = {function_name}\n"
    text += "%MATPOWER case generated from CESDM.\n"
    text += "mpc.version = '2';\n"
    text += f"mpc.baseMVA = {float(case.get('baseMVA', 100.0)):.10g};\n\n"
    text += "%% bus data\n% bus_i type Pd Qd Gs Bs area Vm Va baseKV zone Vmax Vmin\n"
    text += "mpc.bus = [\n" + _matrix(case.get("bus", [])) + "\n];\n\n"
    text += "%% generator data\n% bus Pg Qg Qmax Qmin Vg mBase status Pmax Pmin\n"
    text += "mpc.gen = [\n" + _matrix(case.get("gen", [])) + "\n];\n\n"
    text += "%% branch data\n% fbus tbus r x b rateA rateB rateC ratio angle status angmin angmax\n"
    text += "mpc.branch = [\n" + _matrix(case.get("branch", [])) + "\n];\n\n"
    text += "%% generator cost data\n% 2 startup shutdown n c2 c1 c0\n"
    text += "mpc.gencost = [\n" + _matrix(case.get("gencost", [])) + "\n];\n"
    p.write_text(text, encoding="utf-8")
    return p


def verify_matpower_export(case: dict[str, Any], *, expected_buses: int | None = None,
                           expected_branches: int | None = None,
                           min_generators: int = 0) -> dict[str, Any]:
    """Run simple structural checks on a MATPOWER case dictionary."""
    errors = []
    if expected_buses is not None and len(case.get("bus", [])) != expected_buses:
        errors.append(f"Expected {expected_buses} buses, got {len(case.get('bus', []))}.")
    if expected_branches is not None and len(case.get("branch", [])) != expected_branches:
        errors.append(f"Expected {expected_branches} branches, got {len(case.get('branch', []))}.")
    if len(case.get("gen", [])) < min_generators:
        errors.append(f"Expected at least {min_generators} generators, got {len(case.get('gen', []))}.")

    bus_numbers = {int(row[0]) for row in case.get("bus", [])}
    if not any(int(row[1]) == 3 for row in case.get("bus", [])):
        errors.append("MATPOWER case has no slack/reference bus (type 3).")
    for row in case.get("gen", []):
        if int(row[0]) not in bus_numbers:
            errors.append(f"Generator references missing bus {row[0]}.")
    for row in case.get("branch", []):
        if int(row[0]) not in bus_numbers or int(row[1]) not in bus_numbers:
            errors.append(f"Branch references missing bus {row[0]} -> {row[1]}.")
    return {"ok": not errors, "errors": errors}


__all__ = ["export_matpower_case", "write_matpower_case", "verify_matpower_export"]
