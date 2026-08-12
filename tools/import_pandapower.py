"""pandapower -> CESDM importer.

This module implements a pragmatic first mapping from a pandapower ``net``
object into a CESDM model. It focuses on the power-flow core that is common to
pandapower, MATPOWER and CESDM:

* buses -> ElectricalBus
* loads -> DemandUnit, atNode and power-flow attributes held directly on it
* gen/sgen/ext_grid -> generation-like assets, same flattened pattern
* lines -> TransmissionLine, fromNode/toNode and power-flow attributes
  held directly on it
* trafos -> Transformer, same flattened pattern

The importer intentionally keeps the mapping conservative. It stores values only
when the corresponding CESDM attribute/relation exists in the loaded schemas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cesdm_toolbox import CesdmModel, build_model_from_yaml


def _get(row: Any, name: str, default=None):
    """Safe accessor for pandas Series-like rows."""
    try:
        value = row.get(name, default)
    except AttributeError:
        value = getattr(row, name, default)
    try:
        # pandas NA values should behave like missing values here
        import pandas as pd  # type: ignore
        if pd.isna(value):
            return default
    except Exception:
        pass
    return value


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    try:
        import pandas as pd  # type: ignore
        if pd.isna(value):
            return default
    except Exception:
        pass
    return bool(value)


def _bus_id(idx: Any) -> str:
    return f"pp.bus.{idx}"


def _ensure_basics(model: CesdmModel, *, region_id: str, region_name: str) -> None:
    """Create common domain entities used by the importer."""
    model.ensure_carrier("carrier.electricity", name="Electricity")
    model.ensure_carrier("carrier.natural_gas", name="Natural gas")
    model.ensure_entity(class_name="CarrierDomain", entity_id="domain.electricity", name="Electricity domain")
    model.add_relation_if_allowed("domain.electricity", "hasCarrier", "carrier.electricity")
    model.ensure_entity(class_name="GeographicalRegion", entity_id=region_id, name=region_name)


def import_pandapower_net(
    net: Any,
    *,
    schema_dir: str | Path = "schemas/cesdm",
    model: CesdmModel | None = None,
    region_id: str = "region.default",
    region_name: str = "Default region",
    frequency_hz: float | None = None,
) -> CesdmModel:
    """Import a pandapower network object into a CESDM model.

    Parameters
    ----------
    net:
        pandapower network object.
    schema_dir:
        CESDM schema directory. Used only if ``model`` is not supplied.
    model:
        Existing CESDM model to populate. If omitted, a new model is created.
    region_id, region_name:
        Default geographical region assigned to buses.

    Returns
    -------
    CesdmModel
        The populated CESDM model.
    """
    if model is None:
        model = build_model_from_yaml(schema_dir)

    # pandapower stores line charging as capacitance c_nf_per_km.
    # CESDM stores shunt_susceptance_per_km [microS/km], so conversion
    # requires the network frequency: B = 2*pi*f*C. Prefer net.f_hz.
    if frequency_hz is None:
        frequency_hz = float(getattr(net, "f_hz", 50.0) or 50.0)

    _ensure_basics(model, region_id=region_id, region_name=region_name)

    # ------------------------------------------------------------------
    # Buses
    # ------------------------------------------------------------------
    for idx, row in net.bus.iterrows():
        in_service = _bool(_get(row, "in_service", True), True)
        if not in_service:
            continue
        vn_kv = _get(row, "vn_kv")
        bus_type = str(_get(row, "type", "b") or "b")
        model.add_entity(entity_class="ElectricalBus", entity_id=_bus_id(idx))
        if vn_kv is not None:
            model.add_attribute(_bus_id(idx), "nominal_voltage", float(vn_kv))
        model.add_relation_if_allowed(_bus_id(idx), "belongsToGeographicalRegion", region_id)
        model.add_relation_if_allowed(_bus_id(idx), "belongsToCarrierDomain", "domain.electricity")
        ent = model.entities["ElectricalBus"][_bus_id(idx)]
        if _get(row, "name") not in (None, ""):
            model.set_attribute_if_allowed(_bus_id(idx), "name", str(_get(row, "name")))
        # Preserve pandapower type if the schema has a suitable field in future.
        model.set_attribute_if_allowed(_bus_id(idx), "pandapower_bus_type", bus_type)

    # Optional bus geodata
    if hasattr(net, "bus_geodata") and net.bus_geodata is not None and not net.bus_geodata.empty:
        for idx, row in net.bus_geodata.iterrows():
            bid = _bus_id(idx)
            if not model.has_entity(bid):
                continue
            x = _get(row, "x")
            y = _get(row, "y")
            if x is not None or y is not None:
                model.set_attribute_if_allowed(bid, "longitude", float(x) if x is not None else None)
                model.set_attribute_if_allowed(bid, "latitude", float(y) if y is not None else None)

    # ------------------------------------------------------------------
    # Loads
    # ------------------------------------------------------------------
    if hasattr(net, "load") and net.load is not None:
        for idx, row in net.load.iterrows():
            if not _bool(_get(row, "in_service", True), True):
                continue
            bus = _get(row, "bus")
            if bus is None or not model.has_entity(_bus_id(bus)):
                continue
            p_mw = float(_get(row, "p_mw", 0.0) or 0.0)
            q_mvar = float(_get(row, "q_mvar", 0.0) or 0.0)
            did = f"pp.load.{idx}"
            model.add_entity(entity_class="DemandUnit", entity_id=did)
            model.add_relation(did, "atNode", _bus_id(bus))
            model.ensure_carrier("carrier.electricity")
            model.add_relation_if_allowed(did, "hasInputCarrier", "carrier.electricity")
            if _get(row, "name") not in (None, ""):
                model.set_attribute_if_allowed(did, "name", str(_get(row, "name")))
            model.set_attribute_if_allowed(did, "active_power_demand", p_mw, unit="MW")
            model.set_attribute_if_allowed(did, "reactive_power_demand", q_mvar, unit="MVAr")

    # ------------------------------------------------------------------
    # Static shunts
    # ------------------------------------------------------------------
    if hasattr(net, "shunt") and net.shunt is not None:
        for idx, row in net.shunt.iterrows():
            if not _bool(_get(row, "in_service", True), True):
                continue
            bus = _get(row, "bus")
            if bus is None or not model.has_entity(_bus_id(bus)):
                continue
            sid = f"pp.shunt.{idx}"
            p_mw = float(_get(row, "p_mw", 0.0) or 0.0)
            # pandapower shunt q_mvar follows a load-oriented sign convention.
            # CESDM stores reactive_power_injection using the MATPOWER Bs convention:
            # positive means reactive injection at V = 1.0 p.u.
            q_mvar = -float(_get(row, "q_mvar", 0.0) or 0.0)
            model.ensure_entity(class_name="ShuntUnit", entity_id=sid)
            if _get(row, "name") not in (None, ""):
                model.set_attribute_if_allowed(sid, "name", str(_get(row, "name")))
            model.connect_single_port(sid, _bus_id(bus))
            model.set_attribute_if_allowed(sid, "active_power_injection", p_mw, unit="MW")
            model.set_attribute_if_allowed(sid, "reactive_power_injection", q_mvar, unit="MVAr")

    # ------------------------------------------------------------------
    # Generators: gen, sgen, ext_grid
    # ------------------------------------------------------------------
    def _add_generator(kind: str, idx: Any, row: Any, *, slack: bool = False) -> None:
        if not _bool(_get(row, "in_service", True), True):
            return
        bus = _get(row, "bus")
        if bus is None or not model.has_entity(_bus_id(bus)):
            return
        p_mw = float(_get(row, "p_mw", 0.0) or 0.0)
        q_mvar = float(_get(row, "q_mvar", 0.0) or 0.0)
        max_p = _get(row, "max_p_mw", None)
        min_p = _get(row, "min_p_mw", None)
        max_q = _get(row, "max_q_mvar", None)
        min_q = _get(row, "min_q_mvar", None)
        # If no explicit max exists, use current p as a conservative nominal value.
        nominal = float(max_p) if max_p is not None else abs(p_mw)
        gid = f"pp.{kind}.{idx}"
        tech = "Generation.ExternalGrid" if slack else "Generation.Generic.Pandapower"
        model.add_entity(entity_class="GenerationUnit", entity_id=gid)
        model.set_technology(gid, tech, technology_class="GeneratorType")
        model.ensure_carrier("carrier.electricity")
        model.add_relation_if_allowed(gid, "hasOutputCarrier", "carrier.electricity")
        model.add_relation(gid, "atNode", _bus_id(bus))
        if nominal > 0:
            model.set_attribute_if_allowed(gid, "nominal_power_capacity", nominal)
        if _get(row, "name") not in (None, ""):
            model.set_attribute_if_allowed(gid, "name", str(_get(row, "name")))
        # PQ/PV/slack is a bus classification (ElectricalBus), not a generator attr.
        powerflow_bus_type = "slack" if slack else ("PV" if kind == "gen" else "PQ")
        model.set_attribute_if_allowed(_bus_id(bus), "powerflow_bus_type", powerflow_bus_type)
        model.set_attribute_if_allowed(gid, "active_power_setpoint", p_mw, unit="MW")
        model.set_attribute_if_allowed(gid, "reactive_power_setpoint", q_mvar, unit="MVAr")
        model.set_attribute_if_allowed(gid, "maximum_reactive_power_output", (float(max_q), "MVAr") if max_q is not None else None)
        model.set_attribute_if_allowed(gid, "minimum_reactive_power_output", (float(min_q), "MVAr") if min_q is not None else None)
        model.set_attribute_if_allowed(gid, "voltage_magnitude_setpoint", float(_get(row, "vm_pu", 1.0) or 1.0))
        dv = gid
        if dv:
            if max_p is not None:
                model.set_attribute_if_allowed(dv, "maximum_power_output", float(max_p), unit="MW")
            if min_p is not None:
                model.set_attribute_if_allowed(dv, "minimum_power_output", float(min_p), unit="MW")

    if hasattr(net, "gen") and net.gen is not None:
        for idx, row in net.gen.iterrows():
            _add_generator("gen", idx, row)

    if hasattr(net, "sgen") and net.sgen is not None:
        for idx, row in net.sgen.iterrows():
            _add_generator("sgen", idx, row)

    if hasattr(net, "ext_grid") and net.ext_grid is not None:
        for idx, row in net.ext_grid.iterrows():
            # pandapower ext_grid has no p_mw/q_mvar before running PF. Represent as slack source.
            _add_generator("ext_grid", idx, row, slack=True)
            # The slack designation and voltage setpoints now live on
            # Generator.PowerFlowView, not ElectricalBus.PowerFlowView.

    # ------------------------------------------------------------------
    # Lines
    # ------------------------------------------------------------------
    if hasattr(net, "line") and net.line is not None:
        for idx, row in net.line.iterrows():
            if not _bool(_get(row, "in_service", True), True):
                continue
            fb = _get(row, "from_bus")
            tb = _get(row, "to_bus")
            if fb is None or tb is None:
                continue
            if not model.has_entity(_bus_id(fb)) or not model.has_entity(_bus_id(tb)):
                continue
            lid = f"pp.line.{idx}"
            model.add_entity(entity_class="TransmissionLine", entity_id=lid)
            model.add_relation(lid, "fromNode", _bus_id(fb))
            model.add_relation(lid, "toNode", _bus_id(tb))
            if _get(row, "name") not in (None, ""):
                model.set_attribute_if_allowed(lid, "name", str(_get(row, "name")))
            pfv = lid
            if pfv:
                model.set_attribute_if_allowed(pfv, "line_length", _get(row, "length_km"), unit="km")
                model.set_attribute_if_allowed(pfv, "series_resistance_per_km", _get(row, "r_ohm_per_km"), unit="Ohm/km")
                model.set_attribute_if_allowed(pfv, "series_reactance_per_km", _get(row, "x_ohm_per_km"), unit="Ohm/km")
                # pandapower stores line charging as capacitance [nF/km].
                # CESDM stores shunt *susceptance*, not capacitance. Convert
                # C [nF/km] -> B [microS/km] using B = 2*pi*f*C.
                try:
                    import math
                    c_nf_per_km = float(_get(row, "c_nf_per_km") or 0.0)
                    b_micro_s_per_km = 2.0 * math.pi * float(frequency_hz) * c_nf_per_km * 1e-9 * 1e6
                except Exception:
                    b_micro_s_per_km = 0.0
                model.set_attribute_if_allowed(pfv, "shunt_susceptance_per_km", b_micro_s_per_km, unit="microS/km")
                model.set_attribute_if_allowed(pfv, "line_parameter_basis", "physical")
                model.set_attribute_if_allowed(pfv, "parallel_circuit_count", _get(row, "parallel"))
                max_i_ka = _get(row, "max_i_ka")
                vn_kv = None
                try:
                    vn_kv = float(net.bus.loc[fb, "vn_kv"])
                except Exception:
                    pass
                if max_i_ka is not None and vn_kv is not None:
                    # Approximate three-phase thermal rating: sqrt(3)*V[kV]*I[kA] = MVA
                    import math
                    rating = math.sqrt(3.0) * float(vn_kv) * float(max_i_ka)
                    model.set_attribute_if_allowed(pfv, "thermal_capacity_rating", rating, unit="MVA")


    # ------------------------------------------------------------------
    # Transformers
    # ------------------------------------------------------------------
    if hasattr(net, "trafo") and net.trafo is not None:
        for idx, row in net.trafo.iterrows():
            if not _bool(_get(row, "in_service", True), True):
                continue
            hv_bus = _get(row, "hv_bus")
            lv_bus = _get(row, "lv_bus")
            if hv_bus is None or lv_bus is None:
                continue
            if not model.has_entity(_bus_id(hv_bus)) or not model.has_entity(_bus_id(lv_bus)):
                continue
            tid = f"pp.trafo.{idx}"
            model.ensure_entity(class_name="Transformer", entity_id=tid)
            model.connect_two_port(tid, _bus_id(hv_bus), _bus_id(lv_bus))
            if _get(row, "name") not in (None, ""):
                model.set_attribute_if_allowed(tid, "name", str(_get(row, "name")))
            pfv = tid
            sn_mva = float(_get(row, "sn_mva", 0.0) or 0.0)
            vn_hv_kv = float(_get(row, "vn_hv_kv", 0.0) or 0.0)
            vn_lv_kv = float(_get(row, "vn_lv_kv", 0.0) or 0.0)
            vk_percent = float(_get(row, "vk_percent", 0.0) or 0.0)
            vkr_percent = float(_get(row, "vkr_percent", 0.0) or 0.0)
            z_base_ohm = (vn_hv_kv * vn_hv_kv) / sn_mva if sn_mva > 0 and vn_hv_kv > 0 else 1.0
            r_ohm = (vkr_percent / 100.0) * z_base_ohm
            x_pu_sq = max((vk_percent / 100.0) ** 2 - (vkr_percent / 100.0) ** 2, 0.0)
            x_ohm = (x_pu_sq ** 0.5) * z_base_ohm
            tap_pos = float(_get(row, "tap_pos", 0.0) or 0.0)
            tap_step_percent = float(_get(row, "tap_step_percent", 0.0) or 0.0)
            tap_ratio = 1.0 + tap_pos * tap_step_percent / 100.0
            shift = float(_get(row, "shift_degree", 0.0) or 0.0)
            model.set_attribute_if_allowed(pfv, "line_length", 1.0, unit="km")
            model.set_attribute_if_allowed(pfv, "series_resistance_per_km", r_ohm, unit="Ohm/km")
            model.set_attribute_if_allowed(pfv, "series_reactance_per_km", x_ohm, unit="Ohm/km")
            model.set_attribute_if_allowed(pfv, "shunt_susceptance_per_km", 0.0, unit="microS/km")
            model.set_attribute_if_allowed(pfv, "line_parameter_basis", "physical")
            model.set_attribute_if_allowed(pfv, "thermal_capacity_rating", sn_mva, unit="MVA")
            model.set_attribute_if_allowed(pfv, "rated_primary_voltage", vn_hv_kv, unit="kV")
            model.set_attribute_if_allowed(pfv, "rated_secondary_voltage", vn_lv_kv, unit="kV")
            model.set_attribute_if_allowed(pfv, "short_circuit_voltage_in_percentage", vk_percent, unit="percent")
            model.set_attribute_if_allowed(pfv, "tap_ratio", tap_ratio)
            model.set_attribute_if_allowed(pfv, "phase_shift_angle", shift, unit="degree")

    return model


__all__ = ["import_pandapower_net"]
