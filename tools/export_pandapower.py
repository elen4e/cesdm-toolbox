"""CESDM -> pandapower exporter.

This module exports the common CESDM power-flow core to a pandapower ``net``:

* ``ElectricalBus`` -> ``net.bus``
* ``DemandUnit`` + ``Demand.PowerFlowView`` -> ``net.load``
* generation assets + ``Generator.PowerFlowView`` -> ``net.gen``
* slack bus view -> ``net.ext_grid``
* ``TransmissionLine`` + ``TransmissionLine.PowerFlowView`` -> ``net.line``

The mapping is intentionally conservative. It preserves topology and common
power-flow values. Rich CESDM semantics that do not exist in pandapower remain
in the CESDM model and are not represented in the exported net.
"""

from __future__ import annotations

from typing import Any
import math

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
    """Return the unit string exactly as stored on the CESDM attribute."""
    if isinstance(value, dict):
        return str(value.get("unit", "") or "").strip()
    return ""


def _is_per_unit(value: Any) -> bool:
    u = _unit(value).replace(" ", "").replace("_", "-")
    return u in {"pu", "p.u.", "p.u", "per-unit", "perunit", "pu/km"}


def _name(model: CesdmModel, class_name: str, entity_id: str, default: str) -> str:
    ent = (model.entities.get(class_name) or {}).get(entity_id)
    data = getattr(ent, "data", {}) if ent is not None else {}
    return str(_raw(data.get("name"), default) or default)


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


def export_pandapower_net(
    model: CesdmModel,
    *,
    name: str = "CESDM export",
    base_mva: float = 100.0,
    line_values_are_pu: bool = False,
    frequency_hz: float = 50.0,
):
    """Export a CESDM model to a pandapower network object.

    Parameters
    ----------
    model:
        CESDM model to export.
    name:
        Name of the created pandapower network.
    base_mva:
        System base power. Used when converting MATPOWER-style per-unit line
        impedances to pandapower line parameters.
    line_values_are_pu:
        If True, values stored on ``TransmissionLine.PowerFlowView`` as
        ``series_resistance_per_km`` and ``series_reactance_per_km`` are
        interpreted as MATPOWER per-unit branch values on the system base and
        converted to Ohm for pandapower. This is useful for
        ``MATPOWER -> CESDM -> pandapower`` roundtrips.
    frequency_hz:
        Network frequency used when converting between CESDM shunt
        susceptance [microS/km] and pandapower capacitance [nF/km].
        MATPOWER conversion itself does not use frequency because MATPOWER
        BR_B is already a susceptance in per-unit.
    """
    try:
        import pandapower as pp  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "pandapower is required for CESDM -> pandapower export. "
            "Install it with: pip install -e \".[pandapower]\""
        ) from exc

    net = pp.create_empty_network(name=name, sn_mva=float(base_mva), f_hz=float(frequency_hz))

    buses = model.entities.get("ElectricalBus") or {}
    bus_pf = _view_by_asset(model, "ElectricalBus.PowerFlowView")
    sp_bus = _single_port_bus(model)
    tp_bus = _two_port_buses(model)
    gen_pf = _view_by_asset(model, "Generator.PowerFlowView")
    dem_pf = _view_by_asset(model, "Demand.PowerFlowView")
    shunt_pf = _view_by_asset(model, "Shunt.PowerFlowView")
    line_pf = _view_by_asset(model, "TransmissionLine.PowerFlowView")
    transformer_pf = _view_by_asset(model, "Transformer.PowerFlowView")

    # Buses.
    pp_bus_index: dict[str, int] = {}
    for bid in sorted(buses.keys()):
        bdata = getattr(buses[bid], "data", {}) or {}
        vn_kv = _float(bdata.get("nominal_voltage"), 110.0)
        pp_idx = pp.create_bus(net, vn_kv=vn_kv if vn_kv > 0 else 110.0, name=_name(model, "ElectricalBus", bid, bid))
        pp_bus_index[bid] = int(pp_idx)

    # Slack / external grid. PQ/PV/slack lives on ElectricalBus; generator
    # setpoints (vm/va) still come from the connected GenerationUnit.
    slack_generators: list[tuple[str, str, dict[str, Any]]] = []
    gen_asset_classes = [
        "GenerationUnit", "HydroGenerationUnit",
        "WindGenerationUnit", "SolarGenerationUnit", "ThermalGenerationUnit",
    ]
    for cls in gen_asset_classes:
        for gid in sorted((model.entities.get(cls) or {}).keys()):
            bid = sp_bus.get(gid)
            if bid not in pp_bus_index:
                continue
            bus_ent = buses.get(bid)
            bus_data = getattr(bus_ent, "data", {}) if bus_ent is not None else {}
            if str(_raw(bus_data.get("powerflow_bus_type"), "") or "").lower() != "slack":
                continue
            pf_ent = gen_pf.get(gid)
            pf_data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
            slack_generators.append((gid, bid, pf_data))

    if slack_generators:
        for gid, bid, pf_data in slack_generators:
            pp.create_ext_grid(
                net,
                bus=pp_bus_index[bid],
                vm_pu=_float(pf_data.get("voltage_magnitude_setpoint"), 1.0),
                va_degree=_float(pf_data.get("voltage_angle_setpoint"), 0.0),
                name=gid,
            )
    elif pp_bus_index:
        first_bid = sorted(pp_bus_index.keys())[0]
        pp.create_ext_grid(net, bus=pp_bus_index[first_bid], vm_pu=1.0, va_degree=0.0, name="Default slack")

    # Demands.
    for did in sorted((model.entities.get("DemandUnit") or {}).keys()):
        bid = sp_bus.get(did)
        if bid not in pp_bus_index:
            continue
        pf_ent = dem_pf.get(did)
        data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
        p_mw = _float(data.get("active_power_demand"), 0.0)
        q_mvar = _float(data.get("reactive_power_demand"), 0.0)
        pp.create_load(net, bus=pp_bus_index[bid], p_mw=p_mw, q_mvar=q_mvar, name=did)

    # Static shunts.
    for sid in sorted((model.entities.get("ShuntUnit") or {}).keys()):
        bid = sp_bus.get(sid)
        if bid not in pp_bus_index:
            continue
        pf_ent = shunt_pf.get(sid)
        data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
        p_mw = _float(data.get("active_power_injection"), _float(data.get("active_power_demand"), 0.0))
        # CESDM reactive_power_injection uses MATPOWER Bs convention
        # (positive = reactive injection). Pandapower q_mvar is load-oriented,
        # so the sign is inverted on export.
        q_mvar = -_float(data.get("reactive_power_injection"), _float(data.get("reactive_power_demand"), 0.0))
        pp.create_shunt(
            net,
            bus=pp_bus_index[bid],
            p_mw=p_mw,
            q_mvar=q_mvar,
            name=sid,
        )

    # Generators.
    for cls in gen_asset_classes:
        for gid in sorted((model.entities.get(cls) or {}).keys()):
            bid = sp_bus.get(gid)
            if bid not in pp_bus_index:
                continue
            pf_ent = gen_pf.get(gid)
            pf_data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
            # Dispatch data (nominal_power_capacity, ...) lives directly
            # on the generation asset itself -- every gen_asset_classes
            # entry is a GenerationUnit subclass, so it always carries
            # dispatch-group data by construction.
            dv_data = getattr(model.entities[cls][gid], "data", {}) or {}
            # Do not drop slack generation units here: ext_grid provides the
            # voltage-angle reference, while the Generator row preserves the
            # original CESDM/MATPOWER generator asset and keeps structural
            # round-trips from losing one generator.
            p_mw = _float(pf_data.get("active_power_setpoint"), 0.0)
            vm_pu = _float(pf_data.get("voltage_magnitude_setpoint"), 1.0)
            max_p = _float(dv_data.get("maximum_power_output"), _float(dv_data.get("nominal_power_capacity"), max(abs(p_mw), 0.0)))
            min_p = _float(dv_data.get("minimum_power_output"), 0.0)
            max_q = _float(pf_data.get("maximum_reactive_power_output"), _float(dv_data.get("maximum_reactive_power_output"), 999.0))
            min_q = _float(pf_data.get("minimum_reactive_power_output"), _float(dv_data.get("minimum_reactive_power_output"), -999.0))
            pp.create_gen(
                net,
                bus=pp_bus_index[bid],
                p_mw=p_mw,
                vm_pu=vm_pu,
                min_p_mw=min_p,
                max_p_mw=max_p if max_p > 0 else None,
                min_q_mvar=min_q,
                max_q_mvar=max_q,
                name=gid,
            )

    # Lines.
    #
    # CESDM line parameters are physical quantities:
    #
    #   series_resistance_per_km      [Ohm/km]
    #   series_reactance_per_km       [Ohm/km]
    #   shunt_susceptance_per_km      [microS/km]
    #
    # pandapower expects:
    #
    #   r_ohm_per_km                  [Ohm/km]
    #   x_ohm_per_km                  [Ohm/km]
    #   c_nf_per_km                   [nF/km]
    #
    # Therefore only the shunt term needs frequency-dependent conversion:
    #
    #   B [S/km] = 2*pi*f*C [F/km]
    #
    # Some old CESDM files may still contain MATPOWER-style per-unit values.
    # Those are detected via line_parameter_basis="per_unit" or unit="pu".
    for lid in sorted((model.entities.get("TransmissionLine") or {}).keys()):
        if lid not in tp_bus:
            continue
        fb, tb = tp_bus[lid]
        if fb not in pp_bus_index or tb not in pp_bus_index:
            continue

        pf_ent = line_pf.get(lid)
        data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}

        length_km = _float(data.get("line_length"), 1.0)
        if length_km <= 0:
            length_km = 1.0

        r_raw = data.get("series_resistance_per_km")
        x_raw = data.get("series_reactance_per_km")
        b_raw = data.get("shunt_susceptance_per_km")

        r_ohm_per_km = _float(r_raw, 0.0)
        x_ohm_per_km = _float(x_raw, 0.0001)
        b_microS_per_km = _float(b_raw, 0.0)

        rate_mva = _float(data.get("thermal_capacity_rating"), 0.0)

        try:
            vn_kv = float(net.bus.loc[pp_bus_index[fb], "vn_kv"])
        except Exception:
            vn_kv = 110.0

        # IMPORTANT:
        #
        # CESDM's current canonical semantics are physical line parameters:
        #
        #   series_resistance_per_km      [Ohm/km]
        #   series_reactance_per_km       [Ohm/km]
        #   shunt_susceptance_per_km      [microS/km]
        #
        # Therefore the exporter must NOT automatically reinterpret these
        # values as MATPOWER per-unit values based on metadata such as
        # line_parameter_basis="per_unit" or unit="pu". Some older intermediate
        # files may still contain such metadata even after the values have
        # already been converted to physical units. Auto-detecting pu here can
        # therefore multiply Ohm/km values by Zbase a second time.
        #
        # Per-unit conversion is only enabled explicitly via
        # line_values_are_pu=True.
        values_are_pu = bool(line_values_are_pu)

        if values_are_pu:
            # Legacy / explicit MATPOWER-style mode:
            #
            #   r_raw, x_raw = total branch impedance in pu
            #   b_raw        = total branch charging susceptance in pu
            #
            # Convert to pandapower physical line quantities.
            z_base_ohm = (vn_kv * vn_kv) / float(base_mva or 100.0) if vn_kv > 0 else 1.0

            r_ohm_per_km = (r_ohm_per_km * z_base_ohm) / length_km
            x_ohm_per_km = (x_ohm_per_km * z_base_ohm) / length_km

            b_total_siemens = b_microS_per_km / z_base_ohm
            c_nf_per_km = (
                b_total_siemens / (2.0 * math.pi * float(frequency_hz)) * 1e9 / length_km
                if float(frequency_hz) > 0
                else 0.0
            )
        else:
            # Current CESDM semantics:
            #
            #   r_ohm_per_km and x_ohm_per_km are already pandapower-ready.
            #   b_microS_per_km is susceptance, not capacitance.
            #
            # Convert microS/km -> S/km -> F/km -> nF/km.
            c_nf_per_km = (
                b_microS_per_km * 1e-6 / (2.0 * math.pi * float(frequency_hz)) * 1e9
                if float(frequency_hz) > 0
                else 0.0
            )

        # If rating [MVA] is available, approximate max_i_ka = S/(sqrt(3)*V).
        max_i_ka = 1.0
        if rate_mva > 0 and vn_kv > 0:
            max_i_ka = rate_mva / (math.sqrt(3.0) * vn_kv)

        pp.create_line_from_parameters(
            net,
            from_bus=pp_bus_index[fb],
            to_bus=pp_bus_index[tb],
            length_km=length_km,
            r_ohm_per_km=r_ohm_per_km,
            x_ohm_per_km=x_ohm_per_km if abs(x_ohm_per_km) > 0 else 0.0001,
            c_nf_per_km=c_nf_per_km,
            max_i_ka=max_i_ka if max_i_ka > 0 else 1.0,
            name=lid,
        )


    # Transformers.
    for tid in sorted((model.entities.get("Transformer") or {}).keys()):
        if tid not in tp_bus:
            continue
        hv, lv = tp_bus[tid]
        if hv not in pp_bus_index or lv not in pp_bus_index:
            continue
        pf_ent = transformer_pf.get(tid)
        data = getattr(pf_ent, "data", {}) if pf_ent is not None else {}
        sn_mva = _float(data.get("thermal_capacity_rating"), float(base_mva))
        vn_hv_kv = _float(data.get("rated_primary_voltage"), float(net.bus.loc[pp_bus_index[hv], "vn_kv"]))
        vn_lv_kv = _float(data.get("rated_secondary_voltage"), float(net.bus.loc[pp_bus_index[lv], "vn_kv"]))
        r_ohm = _float(data.get("series_resistance_per_km"), 0.0) * max(_float(data.get("line_length"), 1.0), 1e-12)
        x_ohm = _float(data.get("series_reactance_per_km"), 0.0) * max(_float(data.get("line_length"), 1.0), 1e-12)
        z_base_ohm = (vn_hv_kv * vn_hv_kv) / sn_mva if sn_mva > 0 and vn_hv_kv > 0 else 1.0
        vkr_percent = (r_ohm / z_base_ohm) * 100.0
        vk_percent = ((r_ohm / z_base_ohm) ** 2 + (x_ohm / z_base_ohm) ** 2) ** 0.5 * 100.0
        tap_ratio = _float(data.get("tap_ratio"), 1.0)
        shift = _float(data.get("phase_shift_angle"), 0.0)
        pp.create_transformer_from_parameters(
            net,
            hv_bus=pp_bus_index[hv],
            lv_bus=pp_bus_index[lv],
            sn_mva=sn_mva if sn_mva > 0 else float(base_mva),
            vn_hv_kv=vn_hv_kv if vn_hv_kv > 0 else float(net.bus.loc[pp_bus_index[hv], "vn_kv"]),
            vn_lv_kv=vn_lv_kv if vn_lv_kv > 0 else float(net.bus.loc[pp_bus_index[lv], "vn_kv"]),
            vk_percent=vk_percent if vk_percent > 0 else 0.01,
            vkr_percent=vkr_percent,
            pfe_kw=0.0,
            i0_percent=0.0,
            shift_degree=shift,
            tap_pos=0.0,
            tap_neutral=0.0,
            tap_step_percent=(tap_ratio - 1.0) * 100.0,
            name=tid,
        )

    return net


def verify_pandapower_export(
    net: Any,
    *,
    expected_buses: int | None = None,
    expected_lines: int | None = None,
    expected_transformers: int | None = None,
    expected_shunts: int | None = None,
    min_generators: int = 0,
    min_loads: int = 0,
    min_ext_grids: int = 1,
) -> dict[str, Any]:
    """Run simple structural checks on an exported pandapower net."""
    errors: list[str] = []
    if expected_buses is not None and len(net.bus) != expected_buses:
        errors.append(f"Expected {expected_buses} buses, got {len(net.bus)}.")
    if expected_lines is not None and len(net.line) != expected_lines:
        errors.append(f"Expected {expected_lines} lines, got {len(net.line)}.")
    if expected_transformers is not None and hasattr(net, "trafo") and len(net.trafo) != expected_transformers:
        errors.append(f"Expected {expected_transformers} transformers, got {len(net.trafo)}.")
    if expected_shunts is not None and hasattr(net, "shunt") and len(net.shunt) != expected_shunts:
        errors.append(f"Expected {expected_shunts} shunts, got {len(net.shunt)}.")
    if hasattr(net, "gen") and len(net.gen) < min_generators:
        errors.append(f"Expected at least {min_generators} generators, got {len(net.gen)}.")
    if hasattr(net, "load") and len(net.load) < min_loads:
        errors.append(f"Expected at least {min_loads} loads, got {len(net.load)}.")
    if hasattr(net, "ext_grid") and len(net.ext_grid) < min_ext_grids:
        errors.append(f"Expected at least {min_ext_grids} ext_grid entries, got {len(net.ext_grid)}.")

    bus_ids = set(net.bus.index)
    for table_name in ("line", "trafo", "load", "gen", "ext_grid", "shunt"):
        table = getattr(net, table_name, None)
        if table is None:
            continue
        if table_name == "line":
            for idx, row in table.iterrows():
                if row.from_bus not in bus_ids or row.to_bus not in bus_ids:
                    errors.append(f"Line {idx} references a missing bus.")
        elif table_name == "trafo":
            for idx, row in table.iterrows():
                if row.hv_bus not in bus_ids or row.lv_bus not in bus_ids:
                    errors.append(f"Transformer {idx} references a missing bus.")
        elif "bus" in table.columns:
            for idx, row in table.iterrows():
                if row.bus not in bus_ids:
                    errors.append(f"{table_name} {idx} references missing bus {row.bus}.")
    return {"ok": not errors, "errors": errors}


__all__ = ["export_pandapower_net", "verify_pandapower_export"]
