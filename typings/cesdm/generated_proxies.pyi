from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable
from cesdm.proxy import EntityProxy, FlatGroupViewProxy
from cesdm.default_library import *

class BoilerUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None
    fixed_operating_cost: float | None

class BoilerUnitDispatchProxy(FlatGroupViewProxy):
    thermal_efficiency: float | None
    nominal_thermal_power_capacity: float | None
    minimum_load: float | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    variable_operating_cost: float | None

class BoilerUnitTechnicalProxy(FlatGroupViewProxy):
    thermal_efficiency: float | None

class BoilerUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atFuelNode(self) -> NetworkNodeProxy | None: ...
    @atFuelNode.setter
    def atFuelNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class CHPUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None
    fixed_operating_cost: float | None

class CHPUnitDispatchProxy(FlatGroupViewProxy):
    nominal_electrical_power_capacity: float | None
    nominal_thermal_power_capacity: float | None
    electrical_efficiency: float | None
    thermal_efficiency: float | None
    minimum_load: float | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    variable_operating_cost: float | None

class CHPUnitTechnicalProxy(FlatGroupViewProxy):
    electrical_efficiency: float | None
    thermal_efficiency: float | None
    total_efficiency: float | None
    power_to_heat_ratio: float | None

class CHPUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atFuelNode(self) -> NetworkNodeProxy | None: ...
    @atFuelNode.setter
    def atFuelNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class ControllerAVRAC1ADynamicsProxy(FlatGroupViewProxy):
    AVR_Tr: float | None
    AVR_AC1A_Ka: float | None
    AVR_AC1A_Ta: float | None
    AVR_AC1A_Tb: float | None
    AVR_AC1A_Tc: float | None
    AVR_AC1A_Ke: float | None
    AVR_AC1A_Te: float | None
    AVR_AC1A_Kf: float | None
    AVR_AC1A_Tf: float | None
    AVR_AC1A_Kc: float | None
    AVR_AC1A_Kd: float | None
    AVR_Va_min: float | None
    AVR_Va_max: float | None
    AVR_Efd_min: float | None
    AVR_Efd_max: float | None

class ControllerAVRIEEET1DynamicsProxy(FlatGroupViewProxy):
    AVR_Tr: float | None
    AVR_IEEET1_Ka: float | None
    AVR_IEEET1_Ta: float | None
    AVR_IEEET1_Ke: float | None
    AVR_IEEET1_Te: float | None
    AVR_IEEET1_Kf: float | None
    AVR_IEEET1_Tf: float | None
    AVR_Vr_min: float | None
    AVR_Vr_max: float | None
    AVR_Efd_min: float | None
    AVR_Efd_max: float | None

class ControllerAVRSEXSDynamicsProxy(FlatGroupViewProxy):
    AVR_SEXS_Ka: float | None
    AVR_SEXS_Ta: float | None
    AVR_Efd_min: float | None
    AVR_Efd_max: float | None

class ControllerAVRST1ADynamicsProxy(FlatGroupViewProxy):
    AVR_Tr: float | None
    AVR_ST1A_Ka: float | None
    AVR_ST1A_Ta: float | None
    AVR_ST1A_Tb: float | None
    AVR_ST1A_Tc: float | None
    AVR_ST1A_Kl: float | None
    AVR_Va_min: float | None
    AVR_Va_max: float | None
    AVR_Efd_min: float | None
    AVR_Efd_max: float | None

class ControllerGOVGGOV1DynamicsProxy(FlatGroupViewProxy):
    GOV_GGOV1_R: float | None
    GOV_GGOV1_Tpelec: float | None
    GOV_GGOV1_Kpgov: float | None
    GOV_GGOV1_Kigov: float | None
    GOV_GGOV1_Kdgov: float | None
    GOV_GGOV1_Tdgov: float | None
    GOV_GGOV1_Tact: float | None
    GOV_GGOV1_T3: float | None
    GOV_GGOV1_Ropen: float | None
    GOV_GGOV1_Rclose: float | None
    GOV_GGOV1_Kimw: float | None
    GOV_GGOV1_Aset: float | None
    GOV_GGOV1_Ka: float | None
    GOV_GGOV1_Ta: float | None
    GOV_Db: float | None
    GOV_Pmax: float | None
    GOV_Pmin: float | None

class ControllerGOVHYGOVDynamicsProxy(FlatGroupViewProxy):
    GOV_HYGOV_R: float | None
    GOV_HYGOV_r: float | None
    GOV_HYGOV_Tr: float | None
    GOV_HYGOV_Tf: float | None
    GOV_HYGOV_Tg: float | None
    GOV_HYGOV_Tw: float | None
    GOV_HYGOV_At: float | None
    GOV_HYGOV_Dturb: float | None
    GOV_HYGOV_qNL: float | None
    GOV_Pmax: float | None
    GOV_Pmin: float | None

class ControllerGOVIEEEG1DynamicsProxy(FlatGroupViewProxy):
    GOV_IEEEG1_R: float | None
    GOV_IEEEG1_T1: float | None
    GOV_IEEEG1_T2: float | None
    GOV_IEEEG1_T3: float | None
    GOV_Db: float | None
    GOV_Pmax: float | None
    GOV_Pmin: float | None

class ControllerPSSPSS2ADynamicsProxy(FlatGroupViewProxy):
    PSS_PSS2A_Ks1: float | None
    PSS_PSS2A_Ks2: float | None
    PSS_PSS2A_T6: float | None
    PSS_PSS2A_T7: float | None
    PSS_PSS2A_T8: float | None
    PSS_PSS2A_T9: float | None
    PSS_PSS2A_M: int | None
    PSS_PSS2A_N: int | None
    PSS_PSS2A_Tw1: float | None
    PSS_PSS2A_Tw2: float | None
    PSS_PSS2A_Tw3: float | None
    PSS_PSS2A_T1: float | None
    PSS_PSS2A_T2: float | None
    PSS_PSS2A_T3: float | None
    PSS_PSS2A_T4: float | None
    PSS_Vs_max: float | None
    PSS_Vs_min: float | None

class ControllerPSSPSS2BDynamicsProxy(FlatGroupViewProxy):
    PSS_PSS2B_Ks1: float | None
    PSS_PSS2B_Ks2: float | None
    PSS_PSS2B_Ks3: float | None
    PSS_PSS2B_T6: float | None
    PSS_PSS2B_T7: float | None
    PSS_PSS2B_T8: float | None
    PSS_PSS2B_T9: float | None
    PSS_PSS2B_M: int | None
    PSS_PSS2B_N: int | None
    PSS_PSS2B_Tw1: float | None
    PSS_PSS2B_Tw2: float | None
    PSS_PSS2B_Tw3: float | None
    PSS_PSS2B_Tw4: float | None
    PSS_PSS2B_T1: float | None
    PSS_PSS2B_T2: float | None
    PSS_PSS2B_T3: float | None
    PSS_PSS2B_T4: float | None
    PSS_Vs_max: float | None
    PSS_Vs_min: float | None

class ControllerPSSSTAB1DynamicsProxy(FlatGroupViewProxy):
    PSS_STAB1_Kstab: float | None
    PSS_STAB1_Tw: float | None
    PSS_STAB1_T1: float | None
    PSS_STAB1_T2: float | None
    PSS_STAB1_T3: float | None
    PSS_STAB1_T4: float | None
    PSS_Vs_max: float | None
    PSS_Vs_min: float | None

class ConversionPortDispatchProxy(FlatGroupViewProxy):
    @property
    def hasFlowCoefficientProfile(self) -> ProfileProxy | None: ...
    @hasFlowCoefficientProfile.setter
    def hasFlowCoefficientProfile(self, value: ProfileProxy | str) -> None: ...

class DemandUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class DemandUnitDispatchProxy(FlatGroupViewProxy):
    annual_energy_demand: float | None
    maximum_energy_demand: float | None
    demand_type: str | None
    is_demand_flexible: bool | None
    flexibility_time_resolution: float | None
    flexibility_window_time_start: float | None
    flexibility_window_time_end: float | None
    maximum_upward_adjustment: float | None
    maximum_downward_adjustment: float | None
    value_of_lost_load: float | None
    variable_operating_cost: float | None
    @property
    def hasDemandProfile(self) -> ProfileProxy | None: ...
    @hasDemandProfile.setter
    def hasDemandProfile(self, value: ProfileProxy | str) -> None: ...

class DemandUnitPowerFlowProxy(FlatGroupViewProxy):
    active_power_demand: float | None
    reactive_power_demand: float | None
    power_factor: float | None

class DemandUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class DynamicMachineModelTypeSynchronousDynamicsProxy(FlatGroupViewProxy):
    machine_model_order: str | None
    inertia_constant: float | None
    damping_coefficient: float | None
    d_axis_synchronous_reactance: float | None
    q_axis_synchronous_reactance: float | None
    d_axis_transient_reactance: float | None
    q_axis_transient_reactance: float | None
    d_axis_transient_open_circuit_time_constant: float | None
    q_axis_transient_open_circuit_time_constant: float | None
    d_axis_subtransient_reactance: float | None
    q_axis_subtransient_reactance: float | None
    d_axis_subtransient_open_circuit_time_constant: float | None
    q_axis_subtransient_open_circuit_time_constant: float | None
    armature_resistance: float | None
    stator_leakage_reactance: float | None

class ElectricalBusPowerFlowProxy(FlatGroupViewProxy):
    powerflow_bus_type: str | None
    voltage_magnitude_setpoint: float | None
    voltage_angle_setpoint: float | None

class ElectricalBusSpatialProxy(FlatGroupViewProxy):
    latitude: float | None
    longitude: float | None
    elevation: float | None
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...

class ElectrolyserUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None
    fixed_operating_cost: float | None

class ElectrolyserUnitDispatchProxy(FlatGroupViewProxy):
    energy_conversion_efficiency: float | None
    nominal_electrical_power_capacity: float | None
    minimum_load: float | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    variable_operating_cost: float | None

class ElectrolyserUnitTechnicalProxy(FlatGroupViewProxy):
    energy_conversion_efficiency: float | None

class ElectrolyserUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHydrogenNode(self) -> HydrogenBusProxy | None: ...
    @atHydrogenNode.setter
    def atHydrogenNode(self, value: HydrogenBusProxy | str) -> None: ...

class ExternalSupplyCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class ExternalSupplyDispatchProxy(FlatGroupViewProxy):
    supply_price: float | None
    supply_capacity: float | None
    is_slack: bool | None

class ExternalSupplyTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class FuelCellUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None
    fixed_operating_cost: float | None

class FuelCellUnitDispatchProxy(FlatGroupViewProxy):
    electrical_efficiency: float | None
    thermal_efficiency: float | None
    nominal_electrical_power_capacity: float | None
    nominal_thermal_power_capacity: float | None
    minimum_load: float | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    variable_operating_cost: float | None

class FuelCellUnitTechnicalProxy(FlatGroupViewProxy):
    electrical_efficiency: float | None
    thermal_efficiency: float | None
    power_to_heat_ratio: float | None

class FuelCellUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atHydrogenNode(self) -> HydrogenBusProxy | None: ...
    @atHydrogenNode.setter
    def atHydrogenNode(self, value: HydrogenBusProxy | str) -> None: ...
    @property
    def atFuelNode(self) -> NetworkNodeProxy | None: ...
    @atFuelNode.setter
    def atFuelNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class GasBusSpatialProxy(FlatGroupViewProxy):
    latitude: float | None
    longitude: float | None
    elevation: float | None
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...

class GenerationUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class GenerationUnitDispatchProxy(FlatGroupViewProxy):
    generator_technology_type: str | None
    nominal_power_capacity: float | None
    minimum_generation: float | None
    maximum_generation: float | None
    variable_operating_cost: float | None
    fixed_operating_cost: float | None
    energy_conversion_efficiency: float | None
    annual_resource_potential: float | None
    dispatch_type: str | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...

class GenerationUnitDynamicsProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class GenerationUnitPowerFlowProxy(FlatGroupViewProxy):
    voltage_magnitude_setpoint: float | None
    voltage_angle_setpoint: float | None
    active_power_setpoint: float | None
    reactive_power_setpoint: float | None
    maximum_active_power_output: float | None
    minimum_active_power_output: float | None
    maximum_reactive_power_output: float | None
    minimum_reactive_power_output: float | None

class GenerationUnitTechnicalProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None

class GenerationUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class GenericConversionUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class GenericConversionUnitDispatchProxy(FlatGroupViewProxy):
    nominal_power_capacity: float | None
    @property
    def referencePort(self) -> ConversionPortProxy | None: ...
    @referencePort.setter
    def referencePort(self, value: ConversionPortProxy | str) -> None: ...

class GenericInterconnectorCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class GenericInterconnectorPowerFlowProxy(FlatGroupViewProxy):
    maximum_power_flow_from_to: float | None
    maximum_power_flow_to_from: float | None

class GenericInterconnectorTopologyProxy(FlatGroupViewProxy):
    from_switch_closed: bool | None
    to_switch_closed: bool | None
    @property
    def fromNode(self) -> NetworkNodeProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def toNode(self) -> NetworkNodeProxy | None: ...
    @toNode.setter
    def toNode(self, value: NetworkNodeProxy | str) -> None: ...

class HVDCLinkCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class HVDCLinkDispatchProxy(FlatGroupViewProxy):
    max_flow: float | None
    variable_operating_cost: float | None

class HVDCLinkPowerFlowProxy(FlatGroupViewProxy):
    converter_technology: str | None
    dc_voltage_kv: float | None
    active_power_setpoint_from_to: float | None
    p_min_hvdc: float | None
    converter_loss_coefficient: float | None
    converter_rating_from: float | None
    converter_rating_to: float | None
    max_flow: float | None

class HVDCLinkTopologyProxy(FlatGroupViewProxy):
    from_switch_closed: bool | None
    to_switch_closed: bool | None
    @property
    def fromNode(self) -> ElectricalBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def toNode(self) -> ElectricalBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: ElectricalBusProxy | str) -> None: ...

class HeatBusSpatialProxy(FlatGroupViewProxy):
    latitude: float | None
    longitude: float | None
    elevation: float | None
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...

class HeatPumpUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None
    fixed_operating_cost: float | None

class HeatPumpUnitDispatchProxy(FlatGroupViewProxy):
    coefficient_of_performance: float | None
    nominal_thermal_power_capacity: float | None
    nominal_electrical_power_capacity: float | None
    minimum_load: float | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    variable_operating_cost: float | None

class HeatPumpUnitTechnicalProxy(FlatGroupViewProxy):
    coefficient_of_performance: float | None

class HeatPumpUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class HydraulicStorageUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class HydraulicStorageUnitDispatchProxy(FlatGroupViewProxy):
    energy_storage_capacity: float | None
    annual_natural_inflow_energy: float | None
    @property
    def hasNaturalInflowProfile(self) -> ProfileProxy | None: ...
    @hasNaturalInflowProfile.setter
    def hasNaturalInflowProfile(self, value: ProfileProxy | str) -> None: ...

class HydroGenerationUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class HydroGenerationUnitDispatchProxy(FlatGroupViewProxy):
    generator_technology_type: str | None
    nominal_power_capacity: float | None
    minimum_generation: float | None
    maximum_generation: float | None
    variable_operating_cost: float | None
    fixed_operating_cost: float | None
    energy_conversion_efficiency: float | None
    annual_resource_potential: float | None
    dispatch_type: str | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    hydro_machine_kind: str | None
    turbine_efficiency: float | None
    maximum_pumping_power: float | None
    pumping_efficiency: float | None
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...

class HydroGenerationUnitDynamicsProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class HydroGenerationUnitPowerFlowProxy(FlatGroupViewProxy):
    voltage_magnitude_setpoint: float | None
    voltage_angle_setpoint: float | None
    active_power_setpoint: float | None
    reactive_power_setpoint: float | None
    maximum_active_power_output: float | None
    minimum_active_power_output: float | None
    maximum_reactive_power_output: float | None
    minimum_reactive_power_output: float | None

class HydroGenerationUnitTechnicalProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None

class HydroGenerationUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class HydrogenBusSpatialProxy(FlatGroupViewProxy):
    latitude: float | None
    longitude: float | None
    elevation: float | None
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...

class ShuntUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class ShuntUnitPowerFlowProxy(FlatGroupViewProxy):
    active_power_injection: float | None
    reactive_power_injection: float | None

class ShuntUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class SolarGenerationUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class SolarGenerationUnitDispatchProxy(FlatGroupViewProxy):
    generator_technology_type: str | None
    nominal_power_capacity: float | None
    minimum_generation: float | None
    maximum_generation: float | None
    variable_operating_cost: float | None
    fixed_operating_cost: float | None
    energy_conversion_efficiency: float | None
    annual_resource_potential: float | None
    dispatch_type: str | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...

class SolarGenerationUnitDynamicsProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class SolarGenerationUnitPowerFlowProxy(FlatGroupViewProxy):
    voltage_magnitude_setpoint: float | None
    voltage_angle_setpoint: float | None
    active_power_setpoint: float | None
    reactive_power_setpoint: float | None
    maximum_active_power_output: float | None
    minimum_active_power_output: float | None
    maximum_reactive_power_output: float | None
    minimum_reactive_power_output: float | None

class SolarGenerationUnitTechnicalProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    tilt_angle: float | None
    azimuth_angle: float | None
    tracking_type: str | None
    panel_technology: str | None

class SolarGenerationUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class StorageUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class StorageUnitDispatchProxy(FlatGroupViewProxy):
    nominal_power_capacity: float | None
    energy_storage_capacity: float | None
    charging_efficiency: float | None
    discharging_efficiency: float | None
    self_discharge_rate: float | None
    minimum_state_of_charge: float | None
    maximum_state_of_charge: float | None
    initial_state_of_charge: float | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    variable_operating_cost: float | None
    charging_variable_operating_cost: float | None
    maximum_charging_power: float | None
    maximum_discharging_power: float | None
    storage_technology_type: str | None

class StorageUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class ThermalGenerationUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class ThermalGenerationUnitDispatchProxy(FlatGroupViewProxy):
    generator_technology_type: str | None
    nominal_power_capacity: float | None
    minimum_generation: float | None
    maximum_generation: float | None
    variable_operating_cost: float | None
    fixed_operating_cost: float | None
    energy_conversion_efficiency: float | None
    annual_resource_potential: float | None
    dispatch_type: str | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    minimum_up_time: float | None
    minimum_down_time: float | None
    hot_start_cost: float | None
    cold_start_cost: float | None
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...

class ThermalGenerationUnitDynamicsProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class ThermalGenerationUnitPowerFlowProxy(FlatGroupViewProxy):
    voltage_magnitude_setpoint: float | None
    voltage_angle_setpoint: float | None
    active_power_setpoint: float | None
    reactive_power_setpoint: float | None
    maximum_active_power_output: float | None
    minimum_active_power_output: float | None
    maximum_reactive_power_output: float | None
    minimum_reactive_power_output: float | None

class ThermalGenerationUnitTechnicalProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    cooling_type: str | None
    reactor_type: str | None
    thermal_capacity: float | None

class ThermalGenerationUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class TransformerCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class TransformerPowerFlowProxy(FlatGroupViewProxy):
    rated_primary_voltage: float | None
    rated_secondary_voltage: float | None
    short_circuit_voltage_in_percentage: float | None
    thermal_capacity_rating: float | None
    tap_ratio: float | None
    phase_shift_angle: float | None

class TransformerTopologyProxy(FlatGroupViewProxy):
    from_switch_closed: bool | None
    to_switch_closed: bool | None
    @property
    def fromNode(self) -> ElectricalBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def toNode(self) -> ElectricalBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: ElectricalBusProxy | str) -> None: ...

class TransmissionLineCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class TransmissionLinePowerFlowProxy(FlatGroupViewProxy):
    series_resistance_per_km: float | None
    series_reactance_per_km: float | None
    shunt_susceptance_per_km: float | None
    line_length: float | None
    parallel_circuit_count: int | None
    thermal_capacity_rating: float | None

class TransmissionLineTopologyProxy(FlatGroupViewProxy):
    from_switch_closed: bool | None
    to_switch_closed: bool | None
    @property
    def fromNode(self) -> ElectricalBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def toNode(self) -> ElectricalBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: ElectricalBusProxy | str) -> None: ...

class WindGenerationUnitCapacityExpansionProxy(FlatGroupViewProxy):
    commissioning_year: int | None
    commission_date: datetime | None
    retrofit_date: datetime | None
    retirement_date: datetime | None

class WindGenerationUnitDispatchProxy(FlatGroupViewProxy):
    generator_technology_type: str | None
    nominal_power_capacity: float | None
    minimum_generation: float | None
    maximum_generation: float | None
    variable_operating_cost: float | None
    fixed_operating_cost: float | None
    energy_conversion_efficiency: float | None
    annual_resource_potential: float | None
    dispatch_type: str | None
    maximum_ramp_rate_up: float | None
    maximum_ramp_rate_down: float | None
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...

class WindGenerationUnitDynamicsProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class WindGenerationUnitPowerFlowProxy(FlatGroupViewProxy):
    voltage_magnitude_setpoint: float | None
    voltage_angle_setpoint: float | None
    active_power_setpoint: float | None
    reactive_power_setpoint: float | None
    maximum_active_power_output: float | None
    minimum_active_power_output: float | None
    maximum_reactive_power_output: float | None
    minimum_reactive_power_output: float | None

class WindGenerationUnitTechnicalProxy(FlatGroupViewProxy):
    rated_voltage: float | None
    rated_apparent_power: float | None
    hub_height: float | None
    rotor_diameter: float | None
    installation_type: str | None
    number_of_turbines: int | None

class WindGenerationUnitTopologyProxy(FlatGroupViewProxy):
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class BoilerUnitProxy(EntityProxy):
    capacity_expansion: BoilerUnitCapacityExpansionProxy
    dispatch: BoilerUnitDispatchProxy
    technical: BoilerUnitTechnicalProxy
    topology: BoilerUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    thermal_efficiency: float | None
    """Ratio of useful heat output to fuel (or other input) energy for a compact ConversionUnit such as CHPUnit, BoilerUnit, or FuelCellUnit. Unit: fraction."""
    nominal_thermal_power_capacity: float | None
    """Maximum useful heat output of a compact ConversionUnit such as CHPUnit, HeatPumpUnit, BoilerUnit, or FuelCellUnit (when heat is modelled). Unit: MW."""
    minimum_load: float | None
    """Minimum stable operating load as a fraction of nominal electrical power. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    @property
    def hasTechnology(self) -> ConverterTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: ConverterTypeProxy | str) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasHeatOutputCarrier(self) -> CarrierProxy | None: ...
    @hasHeatOutputCarrier.setter
    def hasHeatOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def atFuelNode(self) -> NetworkNodeProxy | None: ...
    @atFuelNode.setter
    def atFuelNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class CHPUnitProxy(EntityProxy):
    capacity_expansion: CHPUnitCapacityExpansionProxy
    dispatch: CHPUnitDispatchProxy
    technical: CHPUnitTechnicalProxy
    topology: CHPUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    nominal_electrical_power_capacity: float | None
    """Maximum electrical power (output or input rating) of a compact ConversionUnit such as CHPUnit, FuelCellUnit, HeatPumpUnit, or ElectrolyserUnit. Unit: MW."""
    nominal_thermal_power_capacity: float | None
    """Maximum useful heat output of a compact ConversionUnit such as CHPUnit, HeatPumpUnit, BoilerUnit, or FuelCellUnit (when heat is modelled). Unit: MW."""
    electrical_efficiency: float | None
    """Ratio of electrical energy output to fuel (or other input) energy for a compact ConversionUnit such as CHPUnit or FuelCellUnit. Unit: fraction."""
    thermal_efficiency: float | None
    """Ratio of useful heat output to fuel (or other input) energy for a compact ConversionUnit such as CHPUnit, BoilerUnit, or FuelCellUnit. Unit: fraction."""
    total_efficiency: float | None
    """Combined useful electrical and thermal output divided by fuel energy input. Unit: fraction."""
    power_to_heat_ratio: float | None
    """Ratio of electrical output to useful heat output of a compact ConversionUnit such as CHPUnit or FuelCellUnit. Unit: fraction."""
    minimum_load: float | None
    """Minimum stable operating load as a fraction of nominal electrical power. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    @property
    def hasTechnology(self) -> ConverterTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: ConverterTypeProxy | str) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasElectricityOutputCarrier(self) -> CarrierProxy | None: ...
    @hasElectricityOutputCarrier.setter
    def hasElectricityOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasHeatOutputCarrier(self) -> CarrierProxy | None: ...
    @hasHeatOutputCarrier.setter
    def hasHeatOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def atFuelNode(self) -> NetworkNodeProxy | None: ...
    @atFuelNode.setter
    def atFuelNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class CarrierProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    co2_emission_intensity: float | None
    """Mass of CO₂ emitted per unit of energy delivered by the carrier, expressed in tCO₂/MWh. Used for carbon accounting, emission constraint modelling, and environmental impact assessment. Unit: tCO2/MWh."""
    energy_carrier_cost: float | None
    """The monetary cost of the energy carrier per unit of energy, expressed in MU/MWh. Includes production, delivery, and variable operational costs, used for economic dispatch and optimization. Unit: MU/MWh."""
    carrier_group: str | None
    """High-level classification group of the carrier. Used for cross-carrier aggregation, reporting, and domain assignment. Network node types exist for electricity/gas/heat/hydrogen (ElectricalBus, GasBus, HeatBus, HydrogenBus). Group value "water" remains for carrier/resource labelling; hydro water balance uses HydraulicStorageUnit, not a WaterBus node."""
    carrier_type: str | None
    """Carrier category label (electricity, gas, heat, …) for classification or import mapping."""
    is_primary_fuel: bool | None
    """Indicates whether this carrier is a primary fuel that enters the system from outside the modelled boundary (e.g., natural gas, coal, crude oil). Mutually exclusive with is_secondary_fuel."""
    is_secondary_fuel: bool | None
    """Indicates whether this carrier is a secondary or derived fuel produced within the modelled system (e.g., hydrogen from electrolysis, synthetic methane). Mutually exclusive with is_primary_fuel."""

class CarrierDomainProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def hasCarrier(self) -> CarrierProxy: ...
    @hasCarrier.setter
    def hasCarrier(self, value: CarrierProxy | str) -> None: ...

class ControllerProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerAVRProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerAVRAC1AProxy(EntityProxy):
    dynamics: ControllerAVRAC1ADynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    AVR_Tr: float | None
    """Terminal voltage transducer / filter time constant [s]. Common to IEEET1, AC1A, ST1A. Typical: 0.01–0.05 s. Unit: s."""
    AVR_AC1A_Ka: float | None
    """Regulator gain [pu]. IEEE Std 421.5-2016, AC1A. Unit: pu."""
    AVR_AC1A_Ta: float | None
    """Regulator lag time constant [s]. AC1A. Unit: s."""
    AVR_AC1A_Tb: float | None
    """Transient gain reduction (TGR) lag time constant [s]. AC1A. Unit: s."""
    AVR_AC1A_Tc: float | None
    """Transient gain reduction (TGR) lead time constant [s]. AC1A. Unit: s."""
    AVR_AC1A_Ke: float | None
    """Self-excitation constant [pu]. AC1A. Unit: pu."""
    AVR_AC1A_Te: float | None
    """Exciter field circuit time constant [s]. AC1A. Unit: s."""
    AVR_AC1A_Kf: float | None
    """Stabilising rate-feedback gain [pu]. AC1A. Unit: pu."""
    AVR_AC1A_Tf: float | None
    """Stabilising feedback time constant [s]. AC1A. Unit: s."""
    AVR_AC1A_Kc: float | None
    """Rectifier voltage drop factor accounting for commutation [pu]. AC1A. Unit: pu."""
    AVR_AC1A_Kd: float | None
    """d-axis generator reaction to exciter demagnetising factor [pu]. AC1A. Unit: pu."""
    AVR_Va_min: float | None
    """Lower limit on voltage regulator output before the exciter block [pu]. Unit: pu."""
    AVR_Va_max: float | None
    """Upper limit on voltage regulator output before the exciter block [pu]. Unit: pu."""
    AVR_Efd_min: float | None
    """Minimum field voltage limit [pu on machine air-gap base]. Prevents field reversal under leading power factor operation. Unit: pu."""
    AVR_Efd_max: float | None
    """Ceiling field voltage limit [pu on machine air-gap base]. Represents AVR forcing capability (typically 3–6 pu). Unit: pu."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerAVRIEEET1Proxy(EntityProxy):
    dynamics: ControllerAVRIEEET1DynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    AVR_Tr: float | None
    """Terminal voltage transducer / filter time constant [s]. Common to IEEET1, AC1A, ST1A. Typical: 0.01–0.05 s. Unit: s."""
    AVR_IEEET1_Ka: float | None
    """Regulator gain [pu]. IEEE Std 421.5-2016, IEEET1. Unit: pu."""
    AVR_IEEET1_Ta: float | None
    """Regulator lag time constant [s]. IEEET1. Unit: s."""
    AVR_IEEET1_Ke: float | None
    """Self-excitation constant of the DC exciter [pu]. IEEET1. Unit: pu."""
    AVR_IEEET1_Te: float | None
    """Exciter field circuit time constant [s]. IEEET1. Unit: s."""
    AVR_IEEET1_Kf: float | None
    """Exciter stabilising rate-feedback gain [pu]. IEEET1. Unit: pu."""
    AVR_IEEET1_Tf: float | None
    """Exciter stabilising feedback filter time constant [s]. IEEET1. Unit: s."""
    AVR_Vr_min: float | None
    """Lower limit on the internal regulator reference signal [pu]. IEEET1. Unit: pu."""
    AVR_Vr_max: float | None
    """Upper limit on the internal regulator reference signal [pu]. IEEET1. Unit: pu."""
    AVR_Efd_min: float | None
    """Minimum field voltage limit [pu on machine air-gap base]. Prevents field reversal under leading power factor operation. Unit: pu."""
    AVR_Efd_max: float | None
    """Ceiling field voltage limit [pu on machine air-gap base]. Represents AVR forcing capability (typically 3–6 pu). Unit: pu."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerAVRSEXSProxy(EntityProxy):
    dynamics: ControllerAVRSEXSDynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    AVR_SEXS_Ka: float | None
    """Regulator forward gain [pu]. Efd = Ka/(1+s·Ta) · (Vref − Vt + Vs). Unit: pu."""
    AVR_SEXS_Ta: float | None
    """First-order regulator lag time constant [s]. Unit: s."""
    AVR_Efd_min: float | None
    """Minimum field voltage limit [pu on machine air-gap base]. Prevents field reversal under leading power factor operation. Unit: pu."""
    AVR_Efd_max: float | None
    """Ceiling field voltage limit [pu on machine air-gap base]. Represents AVR forcing capability (typically 3–6 pu). Unit: pu."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerAVRST1AProxy(EntityProxy):
    dynamics: ControllerAVRST1ADynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    AVR_Tr: float | None
    """Terminal voltage transducer / filter time constant [s]. Common to IEEET1, AC1A, ST1A. Typical: 0.01–0.05 s. Unit: s."""
    AVR_ST1A_Ka: float | None
    """Regulator gain [pu]. IEEE Std 421.5-2016, ST1A. Unit: pu."""
    AVR_ST1A_Ta: float | None
    """Regulator lag time constant [s]. ST1A. Unit: s."""
    AVR_ST1A_Tb: float | None
    """Transient gain reduction lag time constant [s]. ST1A. Unit: s."""
    AVR_ST1A_Tc: float | None
    """Transient gain reduction lead time constant [s]. ST1A. Unit: s."""
    AVR_ST1A_Kl: float | None
    """Gain applied when regulator input is below threshold [pu]. ST1A. Typically 0 (disabled). Unit: pu."""
    AVR_Va_min: float | None
    """Lower limit on voltage regulator output before the exciter block [pu]. Unit: pu."""
    AVR_Va_max: float | None
    """Upper limit on voltage regulator output before the exciter block [pu]. Unit: pu."""
    AVR_Efd_min: float | None
    """Minimum field voltage limit [pu on machine air-gap base]. Prevents field reversal under leading power factor operation. Unit: pu."""
    AVR_Efd_max: float | None
    """Ceiling field voltage limit [pu on machine air-gap base]. Represents AVR forcing capability (typically 3–6 pu). Unit: pu."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerGOVProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerGOVGGOV1Proxy(EntityProxy):
    dynamics: ControllerGOVGGOV1DynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    GOV_GGOV1_R: float | None
    """Permanent speed droop [pu]. GGOV1. Unit: pu."""
    GOV_GGOV1_Tpelec: float | None
    """Electrical power measurement filter time constant [s]. GGOV1. Unit: s."""
    GOV_GGOV1_Kpgov: float | None
    """Speed governor proportional gain [pu]. GGOV1. Unit: pu."""
    GOV_GGOV1_Kigov: float | None
    """Speed governor integral gain [pu/s]. GGOV1. Unit: pu."""
    GOV_GGOV1_Kdgov: float | None
    """Speed governor derivative gain [pu·s]. GGOV1. Unit: pu."""
    GOV_GGOV1_Tdgov: float | None
    """Derivative controller filter time constant [s]. GGOV1. Unit: s."""
    GOV_GGOV1_Tact: float | None
    """Valve/gate actuator time constant [s]. GGOV1. Unit: s."""
    GOV_GGOV1_T3: float | None
    """Combustor / turbine delay time constant [s]. GGOV1. Unit: s."""
    GOV_GGOV1_Ropen: float | None
    """Maximum valve opening rate [pu/s]. GGOV1. Unit: pu/s."""
    GOV_GGOV1_Rclose: float | None
    """Maximum valve closing rate [pu/s] (negative). GGOV1. Unit: pu/s."""
    GOV_GGOV1_Kimw: float | None
    """Load control / power error integration gain [pu/s]. GGOV1. Set to 0 to disable droop reset. Unit: pu."""
    GOV_GGOV1_Aset: float | None
    """Acceleration limiter setpoint [pu/s]. GGOV1. Unit: pu/s."""
    GOV_GGOV1_Ka: float | None
    """Acceleration limiter proportional gain [pu]. GGOV1. Unit: pu."""
    GOV_GGOV1_Ta: float | None
    """Acceleration limiter filter time constant [s]. GGOV1. Unit: s."""
    GOV_Db: float | None
    """Speed error deadband around rated frequency [pu]. Governor does not respond within ±Db. Common to IEEEG1, GGOV1. Unit: pu."""
    GOV_Pmax: float | None
    """Maximum mechanical power from the prime mover [MW on machine base]. Unit: MW."""
    GOV_Pmin: float | None
    """Minimum mechanical power from the prime mover [MW on machine base]. Unit: MW."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerGOVHYGOVProxy(EntityProxy):
    dynamics: ControllerGOVHYGOVDynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    GOV_HYGOV_R: float | None
    """Permanent (steady-state) speed droop [pu]. HYGOV. Unit: pu."""
    GOV_HYGOV_r: float | None
    """Temporary droop [pu]. HYGOV. Provides faster transient response than permanent droop R before decaying via dashpot Tr. Unit: pu."""
    GOV_HYGOV_Tr: float | None
    """Dashpot (temporary droop) reset time constant [s]. HYGOV. Unit: s."""
    GOV_HYGOV_Tf: float | None
    """Pilot valve and gate servo time constant [s]. HYGOV. Unit: s."""
    GOV_HYGOV_Tg: float | None
    """Main gate (penstock flow) time constant [s]. HYGOV. Unit: s."""
    GOV_HYGOV_Tw: float | None
    """Water column (penstock) starting time constant [s]. HYGOV. Tw = L·Q0 / (g·H0·A). Unit: s."""
    GOV_HYGOV_At: float | None
    """Turbine gain factor [pu]. HYGOV. Ratio of full-gate power to rated power at rated head. Unit: pu."""
    GOV_HYGOV_Dturb: float | None
    """Turbine self-regulation factor [pu power / pu speed]. HYGOV. Unit: pu."""
    GOV_HYGOV_qNL: float | None
    """No-load water flow at rated head [pu of rated flow]. HYGOV. Unit: pu."""
    GOV_Pmax: float | None
    """Maximum mechanical power from the prime mover [MW on machine base]. Unit: MW."""
    GOV_Pmin: float | None
    """Minimum mechanical power from the prime mover [MW on machine base]. Unit: MW."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerGOVIEEEG1Proxy(EntityProxy):
    dynamics: ControllerGOVIEEEG1DynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    GOV_IEEEG1_R: float | None
    """Permanent speed droop [pu]. 0.05 = 5 % droop. IEEEG1. Unit: pu."""
    GOV_IEEEG1_T1: float | None
    """First lag time constant of the governor control loop [s]. IEEEG1. Unit: s."""
    GOV_IEEEG1_T2: float | None
    """Lead time constant of the governor lead-lag compensator [s]. IEEEG1. Set to 0 for pure lag. Unit: s."""
    GOV_IEEEG1_T3: float | None
    """Steam chest / prime mover time constant [s]. IEEEG1. Unit: s."""
    GOV_Db: float | None
    """Speed error deadband around rated frequency [pu]. Governor does not respond within ±Db. Common to IEEEG1, GGOV1. Unit: pu."""
    GOV_Pmax: float | None
    """Maximum mechanical power from the prime mover [MW on machine base]. Unit: MW."""
    GOV_Pmin: float | None
    """Minimum mechanical power from the prime mover [MW on machine base]. Unit: MW."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerPSSProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerPSSPSS2AProxy(EntityProxy):
    dynamics: ControllerPSSPSS2ADynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    PSS_PSS2A_Ks1: float | None
    """Gain of the speed signal path [pu]. PSS2A. Unit: pu."""
    PSS_PSS2A_Ks2: float | None
    """Gain of the integral-of-accelerating-power path [pu]. PSS2A. Unit: pu."""
    PSS_PSS2A_T6: float | None
    """Rotor speed transducer filter time constant [s]. PSS2A. Unit: s."""
    PSS_PSS2A_T7: float | None
    """Active power transducer filter time constant [s]. PSS2A. Unit: s."""
    PSS_PSS2A_T8: float | None
    """Ramp-tracking filter numerator time constant [s]. PSS2A. Unit: s."""
    PSS_PSS2A_T9: float | None
    """Ramp-tracking filter denominator time constant [s]. PSS2A. Unit: s."""
    PSS_PSS2A_M: int | None
    """Integer order M of ramp-tracking numerator (1+s·T8)^M. PSS2A: M=5."""
    PSS_PSS2A_N: int | None
    """Integer order N of ramp-tracking denominator (1+s·T9)^N. PSS2A: N=1."""
    PSS_PSS2A_Tw1: float | None
    """First washout time constant on speed signal path [s]. PSS2A. Unit: s."""
    PSS_PSS2A_Tw2: float | None
    """Second washout time constant on speed signal path [s]. PSS2A. Unit: s."""
    PSS_PSS2A_Tw3: float | None
    """Washout time constant on integral-of-power path [s]. PSS2A. Unit: s."""
    PSS_PSS2A_T1: float | None
    """First lead-lag stage numerator time constant [s]. PSS2A. Unit: s."""
    PSS_PSS2A_T2: float | None
    """First lead-lag stage denominator time constant [s]. PSS2A. Unit: s."""
    PSS_PSS2A_T3: float | None
    """Second lead-lag stage numerator time constant [s]. PSS2A. Unit: s."""
    PSS_PSS2A_T4: float | None
    """Second lead-lag stage denominator time constant [s]. PSS2A. Unit: s."""
    PSS_Vs_max: float | None
    """Upper saturation limit on PSS supplementary voltage output [pu]. Injected at AVR summing junction. Typical: 0.05–0.15 pu. Unit: pu."""
    PSS_Vs_min: float | None
    """Lower saturation limit on PSS supplementary voltage output [pu]. Unit: pu."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerPSSPSS2BProxy(EntityProxy):
    dynamics: ControllerPSSPSS2BDynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    PSS_PSS2B_Ks1: float | None
    """Gain of the speed signal path [pu]. PSS2B. Unit: pu."""
    PSS_PSS2B_Ks2: float | None
    """Gain of the integral-of-accelerating-power path [pu]. PSS2B. Unit: pu."""
    PSS_PSS2B_Ks3: float | None
    """Gain of the additional third signal path [pu]. PSS2B only. Unit: pu."""
    PSS_PSS2B_T6: float | None
    """Rotor speed transducer filter time constant [s]. PSS2B. Unit: s."""
    PSS_PSS2B_T7: float | None
    """Active power transducer filter time constant [s]. PSS2B. Unit: s."""
    PSS_PSS2B_T8: float | None
    """Ramp-tracking filter numerator time constant [s]. PSS2B. Unit: s."""
    PSS_PSS2B_T9: float | None
    """Ramp-tracking filter denominator time constant [s]. PSS2B. Unit: s."""
    PSS_PSS2B_M: int | None
    """Integer order M of ramp-tracking numerator (1+s·T8)^M. PSS2B."""
    PSS_PSS2B_N: int | None
    """Integer order N of ramp-tracking denominator (1+s·T9)^N. PSS2B."""
    PSS_PSS2B_Tw1: float | None
    """First washout time constant on speed path [s]. PSS2B. Unit: s."""
    PSS_PSS2B_Tw2: float | None
    """Second washout time constant on speed path [s]. PSS2B. Unit: s."""
    PSS_PSS2B_Tw3: float | None
    """Washout on integral-of-power path [s]. PSS2B. Unit: s."""
    PSS_PSS2B_Tw4: float | None
    """Additional washout time constant [s]. PSS2B only. Unit: s."""
    PSS_PSS2B_T1: float | None
    """First lead-lag stage numerator time constant [s]. PSS2B. Unit: s."""
    PSS_PSS2B_T2: float | None
    """First lead-lag stage denominator time constant [s]. PSS2B. Unit: s."""
    PSS_PSS2B_T3: float | None
    """Second lead-lag stage numerator time constant [s]. PSS2B. Unit: s."""
    PSS_PSS2B_T4: float | None
    """Second lead-lag stage denominator time constant [s]. PSS2B. Unit: s."""
    PSS_Vs_max: float | None
    """Upper saturation limit on PSS supplementary voltage output [pu]. Injected at AVR summing junction. Typical: 0.05–0.15 pu. Unit: pu."""
    PSS_Vs_min: float | None
    """Lower saturation limit on PSS supplementary voltage output [pu]. Unit: pu."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ControllerPSSSTAB1Proxy(EntityProxy):
    dynamics: ControllerPSSSTAB1DynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    PSS_STAB1_Kstab: float | None
    """PSS forward path gain [pu]. STAB1 / PSS1A. Unit: pu."""
    PSS_STAB1_Tw: float | None
    """Washout high-pass filter time constant [s]. STAB1. Removes DC and low-frequency components. Typical: 5–20 s. Unit: s."""
    PSS_STAB1_T1: float | None
    """First lead-lag stage numerator time constant [s]. STAB1. Unit: s."""
    PSS_STAB1_T2: float | None
    """First lead-lag stage denominator time constant [s]. STAB1. Unit: s."""
    PSS_STAB1_T3: float | None
    """Second lead-lag stage numerator time constant [s]. STAB1. Unit: s."""
    PSS_STAB1_T4: float | None
    """Second lead-lag stage denominator time constant [s]. STAB1. Unit: s."""
    PSS_Vs_max: float | None
    """Upper saturation limit on PSS supplementary voltage output [pu]. Injected at AVR summing junction. Typical: 0.05–0.15 pu. Unit: pu."""
    PSS_Vs_min: float | None
    """Lower saturation limit on PSS supplementary voltage output [pu]. Unit: pu."""
    @property
    def controlsGenerationUnit(self) -> GenerationUnitProxy: ...
    @controlsGenerationUnit.setter
    def controlsGenerationUnit(self, value: GenerationUnitProxy | str) -> None: ...

class ConversionPortProxy(EntityProxy):
    dispatch: ConversionPortDispatchProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    port_direction: str
    """Flow direction at a ConversionPort. input — carrier is consumed/withdrawn at this port output — carrier is produced/injected at this port bidirectional — carrier can flow in either direction (e.g. reversible heat pump, V2G)"""
    flow_coefficient: float
    """Signed flow ratio of a ConversionPort relative to the unit's reference port (reference port = 1.0)."""
    minimum_flow_fraction: float | None
    """Minimum allowed flow at this port as a fraction of the product flow_coefficient × reference_port_flow. Used to express minimum part-load ratios or technical minimum generation constraints at the port level."""
    maximum_flow_fraction: float | None
    """Maximum allowed flow at this port as a fraction of the product flow_coefficient × reference_port_flow. Values greater than 1.0 express short-term overload capability beyond the rated coefficient."""
    maximum_output_power: float | None
    """Upper bound on instantaneous output power for the asset in dispatch or technical limits."""
    @property
    def belongsToUnit(self) -> ConversionUnitProxy: ...
    @belongsToUnit.setter
    def belongsToUnit(self, value: ConversionUnitProxy | str) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasCarrier(self) -> CarrierProxy: ...
    @hasCarrier.setter
    def hasCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasFlowCoefficientProfile(self) -> ProfileProxy | None: ...
    @hasFlowCoefficientProfile.setter
    def hasFlowCoefficientProfile(self, value: ProfileProxy | str) -> None: ...

class ConversionUnitProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    @property
    def hasTechnology(self) -> ConverterTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: ConverterTypeProxy | str) -> None: ...

class ConverterTypeProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    investment_cost: float | None
    """Overnight investment cost of the technology per unit of installed capacity or per unit, depending on the modeling convention. Used together with technical_lifetime and discount_rate for annualized cost calculations. Unit: MU/kW, MU/MW, MU/unit."""
    technical_lifetime: float | None
    """Technical lifetime of the asset in years. Unit: years."""
    discount_rate: float | None
    """Discount rate applied to investment and cost streams associated with this technology, expressed as a fraction between 0 and 1 (e.g. 0.03 for 3%). May override a global discount rate defined at the Energy System Model level. Unit: fraction."""
    salvage_fraction_value: float | None
    """Fraction of the original investment value that is recovered as salvage at the end of the planning horizon, expressed as a fraction between 0 and 1. Used for partial lifetime treatment when the technology lifetime extends beyond the modeled period. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    minimum_up_time: float | None
    """Minimum number of hours a unit must remain online once started. Used in unit commitment models. Unit: h."""
    minimum_down_time: float | None
    """Minimum number of hours a unit must remain offline after shutdown. Used in unit commitment models. Unit: h."""
    hot_start_cost: float | None
    """Cost incurred to restart a generator that has been recently offline (hot state), expressed in monitary units. Reflects fuel and operational overhead. Unit: MU."""
    cold_start_cost: float | None
    """Cost incurred to restart a generator that has been offline for a long period (cold state), expressed in MU. Usually higher than hot start due to additional operational procedures. Unit: MU."""
    ramping_cost_increase: float | None
    """The cost associated with increasing output power, expressed in MU/MW or MU/MW/min. Used in dispatch optimisation to represent wear, thermal cycling, or operational penalties for fast upward ramping. Unit: MU/MW."""
    ramping_cost_decrease: float | None
    """The cost associated with reducing output power or reducing charging rate, expressed in MonetaryUnits/MW or MonetaryUnits/MW/min. Represents operational constraints or efficiency penalties during ramp-down."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    comment: str | None
    """Optional comment/notes."""
    net_electrical_efficiency: float | None
    """Net electrical efficiency is the ratio of the net electrical energy output of the CHP plant to the total fuel energy input under defined operating conditions. It quantifies the plant’s effectiveness in converting input fuel energy into electricity. Unit: fraction."""
    net_thermal_efficiency: float | None
    """Net thermal efficiency is the ratio of the useful thermal energy output of the CHP plant to the total fuel energy input. It represents the portion of input fuel energy recovered as usable heat. Unit: fraction."""
    rated_electrical_power_capacity: float | None
    """Electrical power capacity is the maximum continuous electrical output a device can deliver under specified conditions, typically expressed in kilowatts (kW) or megawatts (MW). Unit: MW."""
    rated_thermal_output_capacity: float | None
    """Thermal power capacity is the maximum useful thermal power that a device can deliver (as steam, hot water, or process heat) to an external heat network or process under defined operation. Unit: MW."""
    economic_lifetime: float | None
    """Economic/depreciation lifetime of the asset in years. Unit: years."""

class DemandUnitProxy(EntityProxy):
    capacity_expansion: DemandUnitCapacityExpansionProxy
    dispatch: DemandUnitDispatchProxy
    power_flow: DemandUnitPowerFlowProxy
    topology: DemandUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    annual_energy_demand: float | None
    """The total amount of energy required by the load over an entire year, expressed in MWh/year. It is used to scale demand time series or to validate consumption totals for modelling scenarios. Unit: MWh/year."""
    maximum_energy_demand: float | None
    """Maximum energy demand by the load over an entire year, expressed in MW. Unit: MW."""
    demand_type: str | None
    """Demand category or sector label for a DemandUnit (industrial, residential, …)."""
    is_demand_flexible: bool | None
    """Boolean indicator specifying whether the load can be shifted, curtailed, rescheduled, or otherwise managed during operation. If false, demand must be met as defined by the demand profile."""
    flexibility_time_resolution: float | None
    """The smallest allowable time granularity for shifting, adjusting, or rescheduling the load demand. Typically corresponds to the dispatch interval (e.g., 15 min, 1 h). Unit: h, min."""
    flexibility_window_time_start: float | None
    """The beginning of the time interval during which the load is allowed to shift or modify its consumption, expressed as a timestamp or model time index. Unit: Timestamp / time index."""
    flexibility_window_time_end: float | None
    """The end of the time interval during which flexibility actions are permitted. Outside this window the demand must strictly follow its profile. Unit: Timestamp / time index."""
    maximum_upward_adjustment: float | None
    """The maximum amount of incremental upward deviation from the nominal load that is allowed at any given time, expressed in kW or MW. Represents demand increase or load activation flexibility. Unit: kW, MW."""
    maximum_downward_adjustment: float | None
    """The maximum allowable reduction from the nominal load, expressed in kW or MW. Represents demand reduction, curtailment potential, or flexibility for load shedding. Unit: kW, MW."""
    value_of_lost_load: float | None
    """The economic cost (MU/MWh) assigned to unserved energy demand, representing the penalty for not meeting the load. This parameter quantifies the societal and economic impact of supply interruptions and is heavily used in adequacy and reliability studies. Unit: MU/MWh."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    active_power_demand: float | None
    """The instantaneous active power consumed by the demand entity. Active power represents the real electrical power required to perform useful work and is typically expressed in MW. Unit: MW."""
    reactive_power_demand: float | None
    """The instantaneous reactive power consumed by the demand entity. Reactive power represents the non-working power required for maintaining electric and magnetic fields in AC systems and is typically expressed in MVAr. Unit: MVAr."""
    power_factor: float | None
    """Ratio between active power and apparent power associated with the demand entity. The power factor characterizes the efficiency of electrical power utilization and indicates the phase shift between voltage and current in AC systems. Unit: pu."""
    @property
    def hasCarrier(self) -> CarrierProxy | None: ...
    @hasCarrier.setter
    def hasCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasDemandProfile(self) -> ProfileProxy | None: ...
    @hasDemandProfile.setter
    def hasDemandProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class DemandUnitDispatchResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    total_served_energy: float | None
    """Total energy actually served to demand over the horizon [MWh]. Unit: MWh."""
    total_curtailed_energy: float | None
    """Total unserved energy (curtailed demand) over the horizon [MWh]. Unit: MWh."""
    curtailment_rate: float | None
    """Fraction of demanded energy that was curtailed. curtailed_energy / total_demanded_energy [-]."""
    total_variable_cost: float | None
    """Total variable operating cost over the horizon [MU]. Unit: MU."""
    @property
    def reportsOn(self) -> DemandUnitProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: DemandUnitProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DispatchRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DispatchRunRecordProxy | str) -> None: ...
    @property
    def hasServedDemandProfile(self) -> ProfileProxy | None: ...
    @hasServedDemandProfile.setter
    def hasServedDemandProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasCurtailedDemandProfile(self) -> ProfileProxy | None: ...
    @hasCurtailedDemandProfile.setter
    def hasCurtailedDemandProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasDemandDualProfile(self) -> ProfileProxy | None: ...
    @hasDemandDualProfile.setter
    def hasDemandDualProfile(self, value: ProfileProxy | str) -> None: ...

class DispatchResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def reportsOn(self) -> EnergyAssetInstanceNetworkNodeProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: EnergyAssetInstanceNetworkNodeProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DispatchRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DispatchRunRecordProxy | str) -> None: ...

class DispatchRunRecordProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    run_timestamp: datetime | None
    """ISO-8601 datetime when this optimisation run was executed."""
    solver_name: str | None
    """Name of the solver used (e.g. HiGHS, Gurobi, CPLEX)."""
    solver_status: str | None
    """Solver termination status."""
    objective_value: float | None
    """Total system cost (objective function value) [MU]. Unit: MU."""
    optimality_gap: float | None
    """Relative MIP gap at solver termination. (UB - LB) / UB [-]."""
    solve_time_seconds: float | None
    """Wall-clock solver time in seconds. Unit: s."""
    scenario_year: int | None
    """Planning or operational reference year of the scenario."""
    co2_price: float | None
    """CO2 Price is a monetary value assigned to each tonne of carbon dioxide (or CO₂-equivalent) emitted within an energy system. It represents the cost of emitting greenhouse gases and is used to internalize the environmental and societal damages associated with climate change. Unit: MU/tCO2, CHF/tCO2."""
    @property
    def hasInputRun(self) -> RunRecordProxy | None: ...
    @hasInputRun.setter
    def hasInputRun(self, value: RunRecordProxy | str) -> None: ...
    @property
    def hasTimestampSeries(self) -> TimestampSeriesProxy: ...
    @hasTimestampSeries.setter
    def hasTimestampSeries(self, value: TimestampSeriesProxy | str) -> None: ...

class DynamicMachineModelTypeProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""

class DynamicMachineModelTypeSynchronousProxy(EntityProxy):
    dynamics: DynamicMachineModelTypeSynchronousDynamicsProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    machine_model_order: str | None
    """Dynamic model order identifier used in the simulation."""
    inertia_constant: float | None
    """Stored kinetic energy at rated speed / rated MVA [s]. H = ½·J·ω₀² / Sn. Governs dω/dt = (Pm − Pe) / (2H). Unit: s."""
    damping_coefficient: float | None
    """Damping torque proportional to speed deviation (pu torque / pu speed). Dimensionless. Typical range 0–3; default 0. Unit: pu."""
    d_axis_synchronous_reactance: float | None
    """Direct-axis synchronous reactance [pu on machine base]. Steady-state d-axis air-gap impedance. Typical range 1.0–2.0 pu. Unit: pu."""
    q_axis_synchronous_reactance: float | None
    """Quadrature-axis synchronous reactance [pu on machine base]. Unit: pu."""
    d_axis_transient_reactance: float | None
    """Direct-axis transient reactance [pu on machine base]. Unit: pu."""
    q_axis_transient_reactance: float | None
    """Quadrature-axis transient reactance [pu on machine base]. Unit: pu."""
    d_axis_transient_open_circuit_time_constant: float | None
    """Direct-axis transient open-circuit time constant [s]. Unit: s."""
    q_axis_transient_open_circuit_time_constant: float | None
    """Quadrature-axis transient open-circuit time constant [s]. Unit: s."""
    d_axis_subtransient_reactance: float | None
    """Direct-axis subtransient reactance [pu on machine base]. Governs first-cycle behaviour after a disturbance. Unit: pu."""
    q_axis_subtransient_reactance: float | None
    """Quadrature-axis subtransient reactance [pu on machine base]. Unit: pu."""
    d_axis_subtransient_open_circuit_time_constant: float | None
    """Direct-axis subtransient open-circuit time constant [s]. Unit: s."""
    q_axis_subtransient_open_circuit_time_constant: float | None
    """Quadrature-axis subtransient open-circuit time constant [s]. Unit: s."""
    armature_resistance: float | None
    """Armature (stator) resistance [pu on machine base]. Typically 0.002–0.005 pu; often neglected in simplified models. Unit: pu."""
    stator_leakage_reactance: float | None
    """Stator leakage reactance [pu on machine base]. Unit: pu."""

class DynamicResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def reportsOn(self) -> EnergyAssetInstanceNetworkNodeProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: EnergyAssetInstanceNetworkNodeProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DynamicRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DynamicRunRecordProxy | str) -> None: ...

class DynamicRunRecordProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    run_timestamp: datetime | None
    """ISO-8601 datetime when this optimisation run was executed."""
    solver_name: str | None
    """Name of the solver used (e.g. HiGHS, Gurobi, CPLEX)."""
    solve_time_seconds: float | None
    """Wall-clock solver time in seconds. Unit: s."""
    integration_method: str | None
    """Numerical integration scheme used for the time-domain simulation (e.g. trapezoidal, RK4)."""
    simulation_timestep_seconds: float | None
    """Fixed integration timestep of the dynamic simulation [s]. Unit: s."""
    simulation_duration_seconds: float | None
    """Total simulated time span of the dynamic run [s]. Unit: s."""
    @property
    def hasInputRun(self) -> RunRecordProxy | None: ...
    @hasInputRun.setter
    def hasInputRun(self, value: RunRecordProxy | str) -> None: ...

class ElectricalBusProxy(EntityProxy):
    power_flow: ElectricalBusPowerFlowProxy
    spatial: ElectricalBusSpatialProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    latitude: float | None
    """Geographical latitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    longitude: float | None
    """Geographical longitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    elevation: float | None
    """Elevation of the entity above mean sea level, expressed in metres. Relevant for climate-adjusted performance modelling and topographic network studies. Unit: m."""
    nominal_voltage: float | None
    """Rated line-to-line voltage of the network node or branch under normal operating conditions, expressed in kV. Unit: kV."""
    powerflow_bus_type: str | None
    """AC power-flow bus classification (PQ, PV, slack, …) used by the load-flow formulation."""
    voltage_magnitude_setpoint: float | None
    """The target voltage magnitude maintained by the generator at its connected network node during the power flow analysis. This value is commonly used for PV bus modelling and voltage regulation studies and is typically expressed in per unit. Unit: pu."""
    voltage_angle_setpoint: float | None
    """The voltage phase angle associated with the generator bus within the power flow solution. The voltage angle represents the phase displacement of the bus voltage relative to the system reference angle and is typically expressed in degrees. Unit: deg."""
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...
    @property
    def belongsToCarrierDomain(self) -> CarrierDomainProxy: ...
    @belongsToCarrierDomain.setter
    def belongsToCarrierDomain(self, value: CarrierDomainProxy | CarrierDomainId) -> None: ...

class ElectricalBusPowerFlowResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    voltage_magnitude: float | None
    """Bus voltage magnitude from a single power-flow snapshot [pu]. Unit: pu."""
    voltage_angle: float | None
    """Bus voltage angle from a single power-flow snapshot, relative to the slack bus [deg]. Unit: deg."""
    net_active_power_injection: float | None
    """Net active power injection at the bus as solved by the power flow [MW]. Unit: MW."""
    net_reactive_power_injection: float | None
    """Net reactive power injection at the bus as solved by the power flow [MVAr]. Unit: MVAr."""
    average_voltage_magnitude: float | None
    """Time-averaged bus voltage magnitude over the power-flow run [pu]. Unit: pu."""
    min_voltage_magnitude: float | None
    """Minimum bus voltage magnitude observed over the power-flow run [pu]. Unit: pu."""
    max_voltage_magnitude: float | None
    """Maximum bus voltage magnitude observed over the power-flow run [pu]. Unit: pu."""
    @property
    def reportsOn(self) -> ElectricalBusProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> PowerFlowRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: PowerFlowRunRecordProxy | str) -> None: ...
    @property
    def hasVoltageMagnitudeProfile(self) -> ProfileProxy | None: ...
    @hasVoltageMagnitudeProfile.setter
    def hasVoltageMagnitudeProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasVoltageAngleProfile(self) -> ProfileProxy | None: ...
    @hasVoltageAngleProfile.setter
    def hasVoltageAngleProfile(self, value: ProfileProxy | str) -> None: ...

class ElectricityTransmissionProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    @property
    def fromNode(self) -> ElectricalBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def toNode(self) -> ElectricalBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class ElectrolyserUnitProxy(EntityProxy):
    capacity_expansion: ElectrolyserUnitCapacityExpansionProxy
    dispatch: ElectrolyserUnitDispatchProxy
    technical: ElectrolyserUnitTechnicalProxy
    topology: ElectrolyserUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    nominal_electrical_power_capacity: float | None
    """Maximum electrical power (output or input rating) of a compact ConversionUnit such as CHPUnit, FuelCellUnit, HeatPumpUnit, or ElectrolyserUnit. Unit: MW."""
    minimum_load: float | None
    """Minimum stable operating load as a fraction of nominal electrical power. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    @property
    def hasTechnology(self) -> ConverterTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: ConverterTypeProxy | str) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasHydrogenOutputCarrier(self) -> CarrierProxy | None: ...
    @hasHydrogenOutputCarrier.setter
    def hasHydrogenOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHydrogenNode(self) -> HydrogenBusProxy | None: ...
    @atHydrogenNode.setter
    def atHydrogenNode(self, value: HydrogenBusProxy | str) -> None: ...

class EnergyAssetInstanceProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""

class EnergySystemModelProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    base_mva: float | None
    """The system-wide apparent power base used for per-unit calculations. All per-unit quantities are referenced to this base power. Unit: MW."""
    co2_price: float | None
    """CO2 Price is a monetary value assigned to each tonne of carbon dioxide (or CO₂-equivalent) emitted within an energy system. It represents the cost of emitting greenhouse gases and is used to internalize the environmental and societal damages associated with climate change. Unit: MU/tCO2, CHF/tCO2."""

class EnergyTechnologyTypeProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    investment_cost: float | None
    """Overnight investment cost of the technology per unit of installed capacity or per unit, depending on the modeling convention. Used together with technical_lifetime and discount_rate for annualized cost calculations. Unit: MU/kW, MU/MW, MU/unit."""
    technical_lifetime: float | None
    """Technical lifetime of the asset in years. Unit: years."""
    discount_rate: float | None
    """Discount rate applied to investment and cost streams associated with this technology, expressed as a fraction between 0 and 1 (e.g. 0.03 for 3%). May override a global discount rate defined at the Energy System Model level. Unit: fraction."""
    salvage_fraction_value: float | None
    """Fraction of the original investment value that is recovered as salvage at the end of the planning horizon, expressed as a fraction between 0 and 1. Used for partial lifetime treatment when the technology lifetime extends beyond the modeled period. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    minimum_up_time: float | None
    """Minimum number of hours a unit must remain online once started. Used in unit commitment models. Unit: h."""
    minimum_down_time: float | None
    """Minimum number of hours a unit must remain offline after shutdown. Used in unit commitment models. Unit: h."""
    hot_start_cost: float | None
    """Cost incurred to restart a generator that has been recently offline (hot state), expressed in monitary units. Reflects fuel and operational overhead. Unit: MU."""
    cold_start_cost: float | None
    """Cost incurred to restart a generator that has been offline for a long period (cold state), expressed in MU. Usually higher than hot start due to additional operational procedures. Unit: MU."""
    ramping_cost_increase: float | None
    """The cost associated with increasing output power, expressed in MU/MW or MU/MW/min. Used in dispatch optimisation to represent wear, thermal cycling, or operational penalties for fast upward ramping. Unit: MU/MW."""
    ramping_cost_decrease: float | None
    """The cost associated with reducing output power or reducing charging rate, expressed in MonetaryUnits/MW or MonetaryUnits/MW/min. Represents operational constraints or efficiency penalties during ramp-down."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    comment: str | None
    """Optional comment/notes."""

class ExternalSupplyProxy(EntityProxy):
    capacity_expansion: ExternalSupplyCapacityExpansionProxy
    dispatch: ExternalSupplyDispatchProxy
    topology: ExternalSupplyTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    supply_price: float | None
    """Marginal price at which the external supply injects energy into the system [MU/MWh]. Acts as the cost signal for the slack source in economic dispatch and market clearing. Set to 0 for a free slack (e.g. reference bus in a power flow). Set to a large positive value (e.g. value_of_lost_load) to represent an emergency import of last resort. Unit: MU/MWh."""
    supply_capacity: float | None
    """Maximum power the external supply can inject [MW]. When absent or null the supply is treated as uncapacitated (true slack — unlimited injection). Set an explicit value to model a capacity-limited import connection such as a cross-border cable. Unit: MW."""
    is_slack: bool | None
    """Boolean flag indicating that this ExternalSupply acts as the system slack / reference node. Exactly one ExternalSupply per connected island should have is_slack = true. When true, the supply absorbs all active power imbalances and the connected bus is treated as the angle reference in AC power flow (bus type = slack)."""
    @property
    def hasOutputCarrier(self) -> CarrierProxy | None: ...
    @hasOutputCarrier.setter
    def hasOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class FuelCellUnitProxy(EntityProxy):
    capacity_expansion: FuelCellUnitCapacityExpansionProxy
    dispatch: FuelCellUnitDispatchProxy
    technical: FuelCellUnitTechnicalProxy
    topology: FuelCellUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    electrical_efficiency: float | None
    """Ratio of electrical energy output to fuel (or other input) energy for a compact ConversionUnit such as CHPUnit or FuelCellUnit. Unit: fraction."""
    thermal_efficiency: float | None
    """Ratio of useful heat output to fuel (or other input) energy for a compact ConversionUnit such as CHPUnit, BoilerUnit, or FuelCellUnit. Unit: fraction."""
    nominal_electrical_power_capacity: float | None
    """Maximum electrical power (output or input rating) of a compact ConversionUnit such as CHPUnit, FuelCellUnit, HeatPumpUnit, or ElectrolyserUnit. Unit: MW."""
    nominal_thermal_power_capacity: float | None
    """Maximum useful heat output of a compact ConversionUnit such as CHPUnit, HeatPumpUnit, BoilerUnit, or FuelCellUnit (when heat is modelled). Unit: MW."""
    power_to_heat_ratio: float | None
    """Ratio of electrical output to useful heat output of a compact ConversionUnit such as CHPUnit or FuelCellUnit. Unit: fraction."""
    minimum_load: float | None
    """Minimum stable operating load as a fraction of nominal electrical power. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    @property
    def hasTechnology(self) -> ConverterTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: ConverterTypeProxy | str) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasElectricityOutputCarrier(self) -> CarrierProxy | None: ...
    @hasElectricityOutputCarrier.setter
    def hasElectricityOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasHeatOutputCarrier(self) -> CarrierProxy | None: ...
    @hasHeatOutputCarrier.setter
    def hasHeatOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def atHydrogenNode(self) -> HydrogenBusProxy | None: ...
    @atHydrogenNode.setter
    def atHydrogenNode(self, value: HydrogenBusProxy | str) -> None: ...
    @property
    def atFuelNode(self) -> NetworkNodeProxy | None: ...
    @atFuelNode.setter
    def atFuelNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class GasBusProxy(EntityProxy):
    spatial: GasBusSpatialProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    latitude: float | None
    """Geographical latitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    longitude: float | None
    """Geographical longitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    elevation: float | None
    """Elevation of the entity above mean sea level, expressed in metres. Relevant for climate-adjusted performance modelling and topographic network studies. Unit: m."""
    nominal_pressure: float | None
    """Nominal operating pressure at a gas, hydrogen, or water Bus, expressed in bar (gauge). Defines the reference pressure level of the carrier domain at this node and is used for hydraulic network calculations and compressor/pump modelling. Unit: bar."""
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...
    @property
    def belongsToCarrierDomain(self) -> CarrierDomainProxy: ...
    @belongsToCarrierDomain.setter
    def belongsToCarrierDomain(self, value: CarrierDomainProxy | CarrierDomainId) -> None: ...

class GasTransmissionProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    @property
    def fromNode(self) -> GasBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: GasBusProxy | str) -> None: ...
    @property
    def toNode(self) -> GasBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: GasBusProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class GenerationUnitProxy(EntityProxy):
    capacity_expansion: GenerationUnitCapacityExpansionProxy
    dispatch: GenerationUnitDispatchProxy
    dynamics: GenerationUnitDynamicsProxy
    power_flow: GenerationUnitPowerFlowProxy
    technical: GenerationUnitTechnicalProxy
    topology: GenerationUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    rated_voltage: float | None
    """Rated line-to-line terminal voltage of the deployed generation unit [kV]. Together with rated_apparent_power, defines the machine-specific impedance base. Unit: kV."""
    rated_apparent_power: float | None
    """Rated apparent power of the deployed generation unit [MVA]. Defines the machine-specific per-unit power base used with a linked DynamicMachineModelType. Unit: MVA."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    minimum_generation: float | None
    """The minimum active power output that the generation entity can continuously produce while remaining in stable operation. This value represents the lower operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    maximum_generation: float | None
    """The maximum active power output that the generation entity can produce under normal operating conditions. This value represents the upper operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    annual_resource_potential: float | None
    """Specifies the total annually available quantity of a resource or carrier that can be utilized, harvested, extracted, or converted by the represented entity under the assumptions of the associated scenario or resource representation. Unit: MWh/year."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    voltage_magnitude_setpoint: float | None
    """The target voltage magnitude maintained by the generator at its connected network node during the power flow analysis. This value is commonly used for PV bus modelling and voltage regulation studies and is typically expressed in per unit. Unit: pu."""
    voltage_angle_setpoint: float | None
    """The voltage phase angle associated with the generator bus within the power flow solution. The voltage angle represents the phase displacement of the bus voltage relative to the system reference angle and is typically expressed in degrees. Unit: deg."""
    active_power_setpoint: float | None
    """The target active power output assigned to the generator within the power flow calculation. This value defines the scheduled real power injection of the generator into the electrical network and is typically expressed in MW. Unit: MW."""
    reactive_power_setpoint: float | None
    """The target reactive power output assigned to the generator within the power flow calculation. This value defines the scheduled reactive power injection used for voltage support and reactive power balancing in the electrical network and is typically expressed in MVAr. Unit: MVAr."""
    maximum_active_power_output: float | None
    """Maximum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MW. Unit: MW."""
    minimum_active_power_output: float | None
    """Minimum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MW. Unit: MW."""
    maximum_reactive_power_output: float | None
    """Maximum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MVAr. Unit: MVAr."""
    minimum_reactive_power_output: float | None
    """Minimum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MVAr. Unit: MVAr."""
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> GeneratorTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: GeneratorTypeProxy | GeneratorTypeId) -> None: ...
    @property
    def hasInputResource(self) -> NaturalResourceProxy | None: ...
    @hasInputResource.setter
    def hasInputResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasOutputCarrier(self) -> CarrierProxy | None: ...
    @hasOutputCarrier.setter
    def hasOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class GenerationUnitDispatchResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    total_generation: float | None
    """Total energy generated over the optimisation horizon [MWh]. Unit: MWh."""
    capacity_factor: float | None
    """Ratio of actual generation to maximum possible generation over the horizon. sum(p(t)) / (P_max * T) [-]."""
    full_load_hours: float | None
    """Equivalent full-load hours of operation. total_generation / nominal_power_capacity [h]. Unit: h."""
    total_variable_cost: float | None
    """Total variable operating cost over the horizon [MU]. Unit: MU."""
    total_start_cost: float | None
    """Total startup cost over the horizon [MU]. Unit: MU."""
    co2_emissions: float | None
    """Total CO2 emissions over the horizon [tCO2]. sum(p(t) * dt * emission_factor). Unit: tCO2."""
    @property
    def reportsOn(self) -> GenerationUnitProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: GenerationUnitProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DispatchRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DispatchRunRecordProxy | str) -> None: ...
    @property
    def hasDispatchProfile(self) -> ProfileProxy | None: ...
    @hasDispatchProfile.setter
    def hasDispatchProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasCommitmentProfile(self) -> ProfileProxy | None: ...
    @hasCommitmentProfile.setter
    def hasCommitmentProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasStartupProfile(self) -> ProfileProxy | None: ...
    @hasStartupProfile.setter
    def hasStartupProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasShutdownProfile(self) -> ProfileProxy | None: ...
    @hasShutdownProfile.setter
    def hasShutdownProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasReducedCostProfile(self) -> ProfileProxy | None: ...
    @hasReducedCostProfile.setter
    def hasReducedCostProfile(self, value: ProfileProxy | str) -> None: ...

class GenerationUnitDynamicResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    max_rotor_angle_deviation: float | None
    """Maximum rotor-angle deviation from the pre-disturbance operating point during the simulation [deg]. Unit: deg."""
    max_speed_deviation: float | None
    """Maximum rotor speed deviation from nominal during the simulation [pu]. Unit: pu."""
    settling_time_seconds: float | None
    """Time after the disturbance for oscillations to settle within a defined band, or null if the run did not settle [s]. Unit: s."""
    remained_stable: bool | None
    """Whether the machine remained in synchronism for the full simulated duration."""
    @property
    def reportsOn(self) -> GenerationUnitProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: GenerationUnitProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DynamicRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DynamicRunRecordProxy | str) -> None: ...
    @property
    def hasRotorAngleProfile(self) -> ProfileProxy | None: ...
    @hasRotorAngleProfile.setter
    def hasRotorAngleProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasSpeedDeviationProfile(self) -> ProfileProxy | None: ...
    @hasSpeedDeviationProfile.setter
    def hasSpeedDeviationProfile(self, value: ProfileProxy | str) -> None: ...

class GenerationUnitPowerFlowResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    active_power_output: float | None
    """Active power output at the generator as solved by the power flow [MW]. Typically an input at PV/PQ buses (equal to the dispatch setpoint) but solved by the power flow at the slack bus, to balance system losses. Unit: MW."""
    reactive_power_output: float | None
    """Reactive power output at the generator as solved by the power flow [MVAr]. Solved (not an input) at PV/slack buses, to hold the bus voltage setpoint. Unit: MVAr."""
    @property
    def reportsOn(self) -> GenerationUnitProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: GenerationUnitProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> PowerFlowRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: PowerFlowRunRecordProxy | str) -> None: ...
    @property
    def hasActivePowerOutputProfile(self) -> ProfileProxy | None: ...
    @hasActivePowerOutputProfile.setter
    def hasActivePowerOutputProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasReactivePowerOutputProfile(self) -> ProfileProxy | None: ...
    @hasReactivePowerOutputProfile.setter
    def hasReactivePowerOutputProfile(self, value: ProfileProxy | str) -> None: ...

class GeneratorTypeProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    investment_cost: float | None
    """Overnight investment cost of the technology per unit of installed capacity or per unit, depending on the modeling convention. Used together with technical_lifetime and discount_rate for annualized cost calculations. Unit: MU/kW, MU/MW, MU/unit."""
    technical_lifetime: float | None
    """Technical lifetime of the asset in years. Unit: years."""
    discount_rate: float | None
    """Discount rate applied to investment and cost streams associated with this technology, expressed as a fraction between 0 and 1 (e.g. 0.03 for 3%). May override a global discount rate defined at the Energy System Model level. Unit: fraction."""
    salvage_fraction_value: float | None
    """Fraction of the original investment value that is recovered as salvage at the end of the planning horizon, expressed as a fraction between 0 and 1. Used for partial lifetime treatment when the technology lifetime extends beyond the modeled period. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    minimum_up_time: float | None
    """Minimum number of hours a unit must remain online once started. Used in unit commitment models. Unit: h."""
    minimum_down_time: float | None
    """Minimum number of hours a unit must remain offline after shutdown. Used in unit commitment models. Unit: h."""
    hot_start_cost: float | None
    """Cost incurred to restart a generator that has been recently offline (hot state), expressed in monitary units. Reflects fuel and operational overhead. Unit: MU."""
    cold_start_cost: float | None
    """Cost incurred to restart a generator that has been offline for a long period (cold state), expressed in MU. Usually higher than hot start due to additional operational procedures. Unit: MU."""
    ramping_cost_increase: float | None
    """The cost associated with increasing output power, expressed in MU/MW or MU/MW/min. Used in dispatch optimisation to represent wear, thermal cycling, or operational penalties for fast upward ramping. Unit: MU/MW."""
    ramping_cost_decrease: float | None
    """The cost associated with reducing output power or reducing charging rate, expressed in MonetaryUnits/MW or MonetaryUnits/MW/min. Represents operational constraints or efficiency penalties during ramp-down."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    comment: str | None
    """Optional comment/notes."""
    economic_lifetime: float | None
    """Economic/depreciation lifetime of the asset in years. Unit: years."""
    co2_emission_factor: float | None
    """Direct CO₂ emissions per unit of electrical output [tCO₂ / MWh_el]. For fuel-based generators this is fuel_co2_intensity / efficiency. Unit: tCO2/MWh."""
    fuel_consumption_rate: float | None
    """Fuel input per unit of electrical output [MWh_fuel / MWh_el], equal to 1 / energy_conversion_efficiency."""
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasInputResource(self) -> NaturalResourceProxy | None: ...
    @hasInputResource.setter
    def hasInputResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def hasOutputCarrier(self) -> CarrierProxy | None: ...
    @hasOutputCarrier.setter
    def hasOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...

class GenericConversionUnitProxy(EntityProxy):
    capacity_expansion: GenericConversionUnitCapacityExpansionProxy
    dispatch: GenericConversionUnitDispatchProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    @property
    def hasTechnology(self) -> ConverterTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: ConverterTypeProxy | str) -> None: ...
    @property
    def referencePort(self) -> ConversionPortProxy | None: ...
    @referencePort.setter
    def referencePort(self, value: ConversionPortProxy | str) -> None: ...

class GenericInterconnectorProxy(EntityProxy):
    capacity_expansion: GenericInterconnectorCapacityExpansionProxy
    power_flow: GenericInterconnectorPowerFlowProxy
    topology: GenericInterconnectorTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    maximum_power_flow_from_to: float | None
    """Maximum power flow in the direction from node 1 to node 2, used for asymmetric capacity limits (e.g., NTC interconnectors). Unit: MW."""
    maximum_power_flow_to_from: float | None
    """Maximum power flow in the direction from node 2 to node 1, used for asymmetric capacity limits (e.g., NTC interconnectors). Unit: MW."""
    @property
    def fromNode(self) -> NetworkNodeProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def toNode(self) -> NetworkNodeProxy | None: ...
    @toNode.setter
    def toNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class GeographicalRegionProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    region_level: str | None
    """Administrative / statistical level of a GeographicalRegion: country (ISO / NUTS 0), nuts1, nuts2, nuts3, or other custom regions."""
    nuts_code: str | None
    """Official NUTS code for the region when region_level is country/nuts1/nuts2/nuts3 (e.g. CH, CH0, CH01, CH011). Empty for non-NUTS custom regions."""
    iso_country_code: str | None
    """ISO 3166-1 alpha-2 country code associated with the region (e.g. CH, DE). For NUTS regions this is typically the two-letter country prefix (with EL→GR and UK→GB remapping applied where relevant)."""
    @property
    def isSubRegionOf(self) -> GeographicalRegionProxy | None: ...
    @isSubRegionOf.setter
    def isSubRegionOf(self, value: GeographicalRegionProxy | str) -> None: ...

class HVDCLinkProxy(EntityProxy):
    capacity_expansion: HVDCLinkCapacityExpansionProxy
    dispatch: HVDCLinkDispatchProxy
    power_flow: HVDCLinkPowerFlowProxy
    topology: HVDCLinkTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    converter_technology: str | None
    """HVDC converter technology classification, e.g. LCC or VSC."""
    dc_voltage_kv: float | None
    """Nominal DC pole-to-pole voltage of the HVDC link [kV]. Unit: kV."""
    active_power_setpoint_from_to: float | None
    """Operator-set active power transfer on the HVDC link [MW]. Positive = fromNode → toNode. Unit: MW."""
    p_min_hvdc: float | None
    """Minimum active power [MW]. Negative = reverse direction allowed. Unit: MW."""
    converter_loss_coefficient: float | None
    """Fractional converter losses as proportion of transferred power [pu]. Unit: pu."""
    converter_rating_from: float | None
    """Apparent power rating of the converter station at the fromNode end. Unit: MVA."""
    converter_rating_to: float | None
    """Apparent power rating of the converter station at the toNode end. Unit: MVA."""
    max_flow: float | None
    """Maximum carrier flow permitted through a branch or interconnector without violating operational limits, expressed in MW (power) or the appropriate flow unit for the carrier. Unit: MW."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    @property
    def fromNode(self) -> ElectricalBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def toNode(self) -> ElectricalBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class HeatBusProxy(EntityProxy):
    spatial: HeatBusSpatialProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    latitude: float | None
    """Geographical latitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    longitude: float | None
    """Geographical longitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    elevation: float | None
    """Elevation of the entity above mean sea level, expressed in metres. Relevant for climate-adjusted performance modelling and topographic network studies. Unit: m."""
    nominal_temperature: float | None
    """Nominal supply temperature at a heat network Bus, expressed in degrees Celsius. Defines the reference temperature of the heat carrier at this node and is used for thermal network flow calculations and heat exchanger modelling. Unit: degC."""
    nominal_pressure: float | None
    """Nominal operating pressure at a gas, hydrogen, or water Bus, expressed in bar (gauge). Defines the reference pressure level of the carrier domain at this node and is used for hydraulic network calculations and compressor/pump modelling. Unit: bar."""
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...
    @property
    def belongsToCarrierDomain(self) -> CarrierDomainProxy: ...
    @belongsToCarrierDomain.setter
    def belongsToCarrierDomain(self, value: CarrierDomainProxy | CarrierDomainId) -> None: ...

class HeatPumpUnitProxy(EntityProxy):
    capacity_expansion: HeatPumpUnitCapacityExpansionProxy
    dispatch: HeatPumpUnitDispatchProxy
    technical: HeatPumpUnitTechnicalProxy
    topology: HeatPumpUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    coefficient_of_performance: float | None
    """Ratio of useful heat output to electrical energy input for a heat pump (COP). Values greater than 1 are typical; not constrained to the unit interval."""
    nominal_thermal_power_capacity: float | None
    """Maximum useful heat output of a compact ConversionUnit such as CHPUnit, HeatPumpUnit, BoilerUnit, or FuelCellUnit (when heat is modelled). Unit: MW."""
    nominal_electrical_power_capacity: float | None
    """Maximum electrical power (output or input rating) of a compact ConversionUnit such as CHPUnit, FuelCellUnit, HeatPumpUnit, or ElectrolyserUnit. Unit: MW."""
    minimum_load: float | None
    """Minimum stable operating load as a fraction of nominal electrical power. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    @property
    def hasTechnology(self) -> ConverterTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: ConverterTypeProxy | str) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasHeatOutputCarrier(self) -> CarrierProxy | None: ...
    @hasHeatOutputCarrier.setter
    def hasHeatOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def atElectricityNode(self) -> ElectricalBusProxy | None: ...
    @atElectricityNode.setter
    def atElectricityNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def atHeatNode(self) -> HeatBusProxy | None: ...
    @atHeatNode.setter
    def atHeatNode(self, value: HeatBusProxy | str) -> None: ...

class HeatTransmissionProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    @property
    def fromNode(self) -> HeatBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: HeatBusProxy | str) -> None: ...
    @property
    def toNode(self) -> HeatBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: HeatBusProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class HydraulicStorageUnitProxy(EntityProxy):
    capacity_expansion: HydraulicStorageUnitCapacityExpansionProxy
    dispatch: HydraulicStorageUnitDispatchProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    energy_storage_capacity: float | None
    """Maximum net energy or storage medium volume that can be stored and subsequently released under defined operating conditions, expressed as the difference between maximum and minimum allowable state of charge. Use MWh for energy-equivalent storage models and m3 for reservoir water-volume models. Unit: MWh, m3."""
    annual_natural_inflow_energy: float | None
    """Total natural inflow received by a storage asset over one year. Used as the scaling factor when converting a normalised inflow profile (as_normalized_annual_energy) to absolute hourly inflow values in dispatch optimisation models. Unit: MWh/year."""
    @property
    def storesCarrier(self) -> CarrierProxy | None: ...
    @storesCarrier.setter
    def storesCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def storesResource(self) -> NaturalResourceProxy | None: ...
    @storesResource.setter
    def storesResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def hasNaturalInflowProfile(self) -> ProfileProxy | None: ...
    @hasNaturalInflowProfile.setter
    def hasNaturalInflowProfile(self, value: ProfileProxy | str) -> None: ...

class HydroGenerationUnitProxy(EntityProxy):
    capacity_expansion: HydroGenerationUnitCapacityExpansionProxy
    dispatch: HydroGenerationUnitDispatchProxy
    dynamics: HydroGenerationUnitDynamicsProxy
    power_flow: HydroGenerationUnitPowerFlowProxy
    technical: HydroGenerationUnitTechnicalProxy
    topology: HydroGenerationUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    rated_voltage: float | None
    """Rated line-to-line terminal voltage of the deployed generation unit [kV]. Together with rated_apparent_power, defines the machine-specific impedance base. Unit: kV."""
    rated_apparent_power: float | None
    """Rated apparent power of the deployed generation unit [MVA]. Defines the machine-specific per-unit power base used with a linked DynamicMachineModelType. Unit: MVA."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    minimum_generation: float | None
    """The minimum active power output that the generation entity can continuously produce while remaining in stable operation. This value represents the lower operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    maximum_generation: float | None
    """The maximum active power output that the generation entity can produce under normal operating conditions. This value represents the upper operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    annual_resource_potential: float | None
    """Specifies the total annually available quantity of a resource or carrier that can be utilized, harvested, extracted, or converted by the represented entity under the assumptions of the associated scenario or resource representation. Unit: MWh/year."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    voltage_magnitude_setpoint: float | None
    """The target voltage magnitude maintained by the generator at its connected network node during the power flow analysis. This value is commonly used for PV bus modelling and voltage regulation studies and is typically expressed in per unit. Unit: pu."""
    voltage_angle_setpoint: float | None
    """The voltage phase angle associated with the generator bus within the power flow solution. The voltage angle represents the phase displacement of the bus voltage relative to the system reference angle and is typically expressed in degrees. Unit: deg."""
    active_power_setpoint: float | None
    """The target active power output assigned to the generator within the power flow calculation. This value defines the scheduled real power injection of the generator into the electrical network and is typically expressed in MW. Unit: MW."""
    reactive_power_setpoint: float | None
    """The target reactive power output assigned to the generator within the power flow calculation. This value defines the scheduled reactive power injection used for voltage support and reactive power balancing in the electrical network and is typically expressed in MVAr. Unit: MVAr."""
    maximum_active_power_output: float | None
    """Maximum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MW. Unit: MW."""
    minimum_active_power_output: float | None
    """Minimum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MW. Unit: MW."""
    maximum_reactive_power_output: float | None
    """Maximum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MVAr. Unit: MVAr."""
    minimum_reactive_power_output: float | None
    """Minimum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MVAr. Unit: MVAr."""
    hydraulic_head: float | None
    """Net hydraulic head available at the turbine under design conditions. Determines the theoretical power output together with flow rate and turbine efficiency. Instance-specific: depends on reservoir level and tailwater. Unit: m."""
    turbine_type: str | None
    """Hydro turbine family (Francis, Kaplan, Pelton, …) for a HydroGenerationUnit."""
    hydro_machine_kind: str | None
    """Hydro machine class for dispatch: turbine = generation-only; pump = pump-only (consumes electricity to move water); reversible = pump-turbine that can operate in both modes. Distinct from turbine_type (Francis/Kaplan/…) and GeneratorType."""
    turbine_efficiency: float | None
    """The fraction of hydraulic energy converted into useful electrical output by the turbine or turbine-generator set, expressed as a value between 0 and 1. Applies to HydroGenerationUnit and avoids storage-discharge semantics. Unit: fraction."""
    maximum_pumping_power: float | None
    """Maximum electrical power consumed during pumping operation [MW]. May differ from the turbine generation capacity in ternary or quaternary configurations. Only relevant for phs_closed_loop and phs_open_loop. Unit: MW."""
    pumping_efficiency: float | None
    """Pumping efficiency of a HydroGenerationUnit (electrical energy in → hydraulic energy stored). Distinct from charging_efficiency on battery-style StorageUnit. Unit: pu."""
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> GeneratorTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: GeneratorTypeProxy | GeneratorTypeId) -> None: ...
    @property
    def hasInputResource(self) -> NaturalResourceProxy | None: ...
    @hasInputResource.setter
    def hasInputResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasOutputCarrier(self) -> CarrierProxy | None: ...
    @hasOutputCarrier.setter
    def hasOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...
    @property
    def drawsFromHydraulicStorage(self) -> list[HydraulicStorageUnitProxy] | None: ...
    @drawsFromHydraulicStorage.setter
    def drawsFromHydraulicStorage(self, value: Iterable[HydraulicStorageUnitProxy | str]) -> None: ...
    @property
    def dischargesToHydraulicStorage(self) -> HydraulicStorageUnitProxy | None: ...
    @dischargesToHydraulicStorage.setter
    def dischargesToHydraulicStorage(self, value: HydraulicStorageUnitProxy | str) -> None: ...

class HydrogenBusProxy(EntityProxy):
    spatial: HydrogenBusSpatialProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    latitude: float | None
    """Geographical latitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    longitude: float | None
    """Geographical longitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    elevation: float | None
    """Elevation of the entity above mean sea level, expressed in metres. Relevant for climate-adjusted performance modelling and topographic network studies. Unit: m."""
    nominal_pressure: float | None
    """Nominal operating pressure at a gas, hydrogen, or water Bus, expressed in bar (gauge). Defines the reference pressure level of the carrier domain at this node and is used for hydraulic network calculations and compressor/pump modelling. Unit: bar."""
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...
    @property
    def belongsToCarrierDomain(self) -> CarrierDomainProxy: ...
    @belongsToCarrierDomain.setter
    def belongsToCarrierDomain(self, value: CarrierDomainProxy | CarrierDomainId) -> None: ...

class MarketZoneProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    market_zone_code: str
    """Short market / bidding-zone identifier as used in ENTSO-E or national market models (e.g. CH, DE_LU, IT-North, NO1)."""
    eic_code: str | None
    """Optional Energy Identification Code (EIC) for the market area or control area when available from ENTSO-E transparency sources."""
    @property
    def coversRegion(self) -> list[GeographicalRegionProxy] | None: ...
    @coversRegion.setter
    def coversRegion(self, value: Iterable[GeographicalRegionProxy | str]) -> None: ...
    @property
    def hasCarrier(self) -> CarrierProxy | None: ...
    @hasCarrier.setter
    def hasCarrier(self, value: CarrierProxy | CarrierId) -> None: ...

class NaturalResourceProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    resource_group: str | None
    """Broad group of a NaturalResource."""
    resource_type: str | None
    """Natural-resource category (wind, solar, hydro inflow, …)."""
    natural_resource_unit: str | None
    """Canonical physical unit used when the resource is represented as an absolute quantity or rate."""

class NetworkNodeProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    latitude: float | None
    """Geographical latitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    longitude: float | None
    """Geographical longitude of the entity, expressed in decimal degrees. Used for spatial modelling, renewable resource assessment, and GIS-based visualisation. Unit: deg."""
    elevation: float | None
    """Elevation of the entity above mean sea level, expressed in metres. Relevant for climate-adjusted performance modelling and topographic network studies. Unit: m."""
    @property
    def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ...
    @belongsToGeographicalRegion.setter
    def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ...
    @property
    def belongsToMarketZone(self) -> MarketZoneProxy | None: ...
    @belongsToMarketZone.setter
    def belongsToMarketZone(self, value: MarketZoneProxy | str) -> None: ...
    @property
    def belongsToCarrierDomain(self) -> CarrierDomainProxy: ...
    @belongsToCarrierDomain.setter
    def belongsToCarrierDomain(self, value: CarrierDomainProxy | CarrierDomainId) -> None: ...

class NetworkNodeDispatchResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    average_nodal_price: float | None
    """Time-weighted average nodal electricity price [MU/MWh]. Unit: MU/MWh."""
    min_nodal_price: float | None
    """Minimum nodal electricity price over the horizon [MU/MWh]. Unit: MU/MWh."""
    max_nodal_price: float | None
    """Maximum nodal electricity price over the horizon [MU/MWh]. Unit: MU/MWh."""
    @property
    def reportsOn(self) -> NetworkNodeProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DispatchRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DispatchRunRecordProxy | str) -> None: ...
    @property
    def hasNodalPriceProfile(self) -> ProfileProxy | None: ...
    @hasNodalPriceProfile.setter
    def hasNodalPriceProfile(self, value: ProfileProxy | str) -> None: ...

class PortProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""

class PowerFlowResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def reportsOn(self) -> EnergyAssetInstanceNetworkNodeProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: EnergyAssetInstanceNetworkNodeProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> PowerFlowRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: PowerFlowRunRecordProxy | str) -> None: ...

class PowerFlowRunRecordProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    run_timestamp: datetime | None
    """ISO-8601 datetime when this optimisation run was executed."""
    solver_name: str | None
    """Name of the solver used (e.g. HiGHS, Gurobi, CPLEX)."""
    solve_time_seconds: float | None
    """Wall-clock solver time in seconds. Unit: s."""
    converged: bool | None
    """Whether the power-flow solver reached a converged solution."""
    iteration_count: int | None
    """Number of iterations the power-flow solver took to converge (or reach its iteration limit)."""
    convergence_tolerance: float | None
    """Mismatch tolerance the power-flow solver was configured to converge to [pu]."""
    @property
    def hasInputRun(self) -> RunRecordProxy | None: ...
    @hasInputRun.setter
    def hasInputRun(self, value: RunRecordProxy | str) -> None: ...
    @property
    def hasTimestampSeries(self) -> TimestampSeriesProxy | None: ...
    @hasTimestampSeries.setter
    def hasTimestampSeries(self, value: TimestampSeriesProxy | str) -> None: ...

class ProfileProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    profile_type: str
    """How profile samples are interpreted (absolute SI, capacity factor, or normalized annual energy)."""
    profile_unit: str | None
    """SI unit of the profile values. Only meaningful for as_SI profiles (e.g. "MW", "MWh", "m3/s"). Dimensionless profiles (capacity factor and normalized annual energy) should leave this blank or set it to "pu" (per unit)."""
    data_reference: str
    """Internal HDF5 path identifying the numeric payload for this profile, formatted as "/profiles/<entity_id>" (e.g. "/profiles/profile.demand.electricity.at00"). The values dataset at this path contains a float64 array of length equal to the referenced TimestampSeries length. This attribute is the bridge between the YAML entity store and the HDF5 data store."""
    @property
    def hasTimestampSeries(self) -> TimestampSeriesProxy: ...
    @hasTimestampSeries.setter
    def hasTimestampSeries(self, value: TimestampSeriesProxy | str) -> None: ...

class ResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    @property
    def reportsOn(self) -> EnergyAssetInstanceNetworkNodeProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: EnergyAssetInstanceNetworkNodeProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> RunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: RunRecordProxy | str) -> None: ...

class RunRecordProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    run_timestamp: datetime | None
    """ISO-8601 datetime when this optimisation run was executed."""
    @property
    def hasInputRun(self) -> RunRecordProxy | None: ...
    @hasInputRun.setter
    def hasInputRun(self, value: RunRecordProxy | str) -> None: ...

class SemanticEntityProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""

class ShuntUnitProxy(EntityProxy):
    capacity_expansion: ShuntUnitCapacityExpansionProxy
    power_flow: ShuntUnitPowerFlowProxy
    topology: ShuntUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    active_power_injection: float | None
    """Active power component of a static shunt element at nominal voltage, expressed in MW. For MATPOWER this maps to the bus Gs column at V = 1.0 p.u.; for pandapower this maps to net.shunt p_mw. Unit: MW."""
    reactive_power_injection: float | None
    """Reactive power injection of a static shunt element at nominal voltage, expressed in MVAr. This follows the MATPOWER bus Bs convention: positive values inject reactive power at V = 1.0 p.u. When exchanging with pandapower, whose shunt q_mvar uses the opposite load-oriented sign convention, the importer/exporter converts the sign. Unit: MVAr."""
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class SolarGenerationUnitProxy(EntityProxy):
    capacity_expansion: SolarGenerationUnitCapacityExpansionProxy
    dispatch: SolarGenerationUnitDispatchProxy
    dynamics: SolarGenerationUnitDynamicsProxy
    power_flow: SolarGenerationUnitPowerFlowProxy
    technical: SolarGenerationUnitTechnicalProxy
    topology: SolarGenerationUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    rated_voltage: float | None
    """Rated line-to-line terminal voltage of the deployed generation unit [kV]. Together with rated_apparent_power, defines the machine-specific impedance base. Unit: kV."""
    rated_apparent_power: float | None
    """Rated apparent power of the deployed generation unit [MVA]. Defines the machine-specific per-unit power base used with a linked DynamicMachineModelType. Unit: MVA."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    minimum_generation: float | None
    """The minimum active power output that the generation entity can continuously produce while remaining in stable operation. This value represents the lower operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    maximum_generation: float | None
    """The maximum active power output that the generation entity can produce under normal operating conditions. This value represents the upper operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    annual_resource_potential: float | None
    """Specifies the total annually available quantity of a resource or carrier that can be utilized, harvested, extracted, or converted by the represented entity under the assumptions of the associated scenario or resource representation. Unit: MWh/year."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    voltage_magnitude_setpoint: float | None
    """The target voltage magnitude maintained by the generator at its connected network node during the power flow analysis. This value is commonly used for PV bus modelling and voltage regulation studies and is typically expressed in per unit. Unit: pu."""
    voltage_angle_setpoint: float | None
    """The voltage phase angle associated with the generator bus within the power flow solution. The voltage angle represents the phase displacement of the bus voltage relative to the system reference angle and is typically expressed in degrees. Unit: deg."""
    active_power_setpoint: float | None
    """The target active power output assigned to the generator within the power flow calculation. This value defines the scheduled real power injection of the generator into the electrical network and is typically expressed in MW. Unit: MW."""
    reactive_power_setpoint: float | None
    """The target reactive power output assigned to the generator within the power flow calculation. This value defines the scheduled reactive power injection used for voltage support and reactive power balancing in the electrical network and is typically expressed in MVAr. Unit: MVAr."""
    maximum_active_power_output: float | None
    """Maximum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MW. Unit: MW."""
    minimum_active_power_output: float | None
    """Minimum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MW. Unit: MW."""
    maximum_reactive_power_output: float | None
    """Maximum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MVAr. Unit: MVAr."""
    minimum_reactive_power_output: float | None
    """Minimum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MVAr. Unit: MVAr."""
    tilt_angle: float | None
    """Tilt angle of the solar panels relative to the horizontal plane. 0° = horizontal, 90° = vertical. Optimal value depends on latitude and tracking system. Instance-specific. Unit: deg."""
    azimuth_angle: float | None
    """Azimuth orientation of the solar panels. Measured clockwise from north: 0° = north, 90° = east, 180° = south, 270° = west. 180° (south-facing) is optimal in the northern hemisphere. Unit: deg."""
    tracking_type: str | None
    """Tracking system of the solar installation. Fixed systems have no moving parts. Single-axis trackers follow the sun east-west. Dual-axis trackers follow both elevation and azimuth. Allowed values: fixed, single_axis, dual_axis."""
    panel_technology: str | None
    """Photovoltaic cell technology or solar thermal technology type. Determines efficiency, degradation rate, and temperature coefficient. Allowed values: monocrystalline, polycrystalline, thin_film, csp."""
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> GeneratorTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: GeneratorTypeProxy | GeneratorTypeId) -> None: ...
    @property
    def hasInputResource(self) -> NaturalResourceProxy | None: ...
    @hasInputResource.setter
    def hasInputResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasOutputCarrier(self) -> CarrierProxy | None: ...
    @hasOutputCarrier.setter
    def hasOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class StorageTypeProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    investment_cost: float | None
    """Overnight investment cost of the technology per unit of installed capacity or per unit, depending on the modeling convention. Used together with technical_lifetime and discount_rate for annualized cost calculations. Unit: MU/kW, MU/MW, MU/unit."""
    technical_lifetime: float | None
    """Technical lifetime of the asset in years. Unit: years."""
    discount_rate: float | None
    """Discount rate applied to investment and cost streams associated with this technology, expressed as a fraction between 0 and 1 (e.g. 0.03 for 3%). May override a global discount rate defined at the Energy System Model level. Unit: fraction."""
    salvage_fraction_value: float | None
    """Fraction of the original investment value that is recovered as salvage at the end of the planning horizon, expressed as a fraction between 0 and 1. Used for partial lifetime treatment when the technology lifetime extends beyond the modeled period. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    minimum_up_time: float | None
    """Minimum number of hours a unit must remain online once started. Used in unit commitment models. Unit: h."""
    minimum_down_time: float | None
    """Minimum number of hours a unit must remain offline after shutdown. Used in unit commitment models. Unit: h."""
    hot_start_cost: float | None
    """Cost incurred to restart a generator that has been recently offline (hot state), expressed in monitary units. Reflects fuel and operational overhead. Unit: MU."""
    cold_start_cost: float | None
    """Cost incurred to restart a generator that has been offline for a long period (cold state), expressed in MU. Usually higher than hot start due to additional operational procedures. Unit: MU."""
    ramping_cost_increase: float | None
    """The cost associated with increasing output power, expressed in MU/MW or MU/MW/min. Used in dispatch optimisation to represent wear, thermal cycling, or operational penalties for fast upward ramping. Unit: MU/MW."""
    ramping_cost_decrease: float | None
    """The cost associated with reducing output power or reducing charging rate, expressed in MonetaryUnits/MW or MonetaryUnits/MW/min. Represents operational constraints or efficiency penalties during ramp-down."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    comment: str | None
    """Optional comment/notes."""
    energy_storage_capacity: float | None
    """Maximum net energy or storage medium volume that can be stored and subsequently released under defined operating conditions, expressed as the difference between maximum and minimum allowable state of charge. Use MWh for energy-equivalent storage models and m3 for reservoir water-volume models. Unit: MWh, m3."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    charging_efficiency: float | None
    """The fraction of input energy that is successfully stored during the charging process, expressed as a value between 0 and 1. Accounts for losses in power electronics, conversion stages, and internal storage mechanisms. Unit: fraction."""
    discharging_efficiency: float | None
    """The fraction of stored energy that can be delivered as useful output during the discharging process, expressed as a value between 0 and 1. Represents conversion losses, internal resistance, and inverter losses. Unit: fraction."""
    self_discharge_rate: float | None
    """Fraction of stored energy lost per time step due to self-discharge. Unit: fraction."""
    minimum_state_of_charge: float | None
    """Minimum allowed state of charge, usually expressed as a fraction between 0 and 1 Unit: fraction."""
    maximum_state_of_charge: float | None
    """Maximum allowed state of charge, usually expressed as a fraction between 0 and 1. Unit: fraction."""
    maximum_required_units: int | None
    """Maximum number of discrete technology units that may be installed, representing site or policy constraints on deployment. Unit: unit."""
    minimum_required_units: int | None
    """Minimum number of discrete technology units that must be installed, representing modular build constraints or policy minimums. Unit: unit."""
    unit_nominal_size: float | None
    """Nominal capacity of a single technology unit (MW or MWh depending on type). Combined with minimum/maximum required units to define total installable capacity range. Unit: MW, MWh."""
    economic_lifetime: float | None
    """Economic/depreciation lifetime of the asset in years. Unit: years."""
    storage_technology_type: str | None
    """Storage technology category when no StorageType library entity is referenced."""
    @property
    def hasCarrier(self) -> CarrierProxy | None: ...
    @hasCarrier.setter
    def hasCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def storesResource(self) -> NaturalResourceProxy | None: ...
    @storesResource.setter
    def storesResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...

class StorageUnitProxy(EntityProxy):
    capacity_expansion: StorageUnitCapacityExpansionProxy
    dispatch: StorageUnitDispatchProxy
    topology: StorageUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    energy_storage_capacity: float | None
    """Maximum net energy or storage medium volume that can be stored and subsequently released under defined operating conditions, expressed as the difference between maximum and minimum allowable state of charge. Use MWh for energy-equivalent storage models and m3 for reservoir water-volume models. Unit: MWh, m3."""
    charging_efficiency: float | None
    """The fraction of input energy that is successfully stored during the charging process, expressed as a value between 0 and 1. Accounts for losses in power electronics, conversion stages, and internal storage mechanisms. Unit: fraction."""
    discharging_efficiency: float | None
    """The fraction of stored energy that can be delivered as useful output during the discharging process, expressed as a value between 0 and 1. Represents conversion losses, internal resistance, and inverter losses. Unit: fraction."""
    self_discharge_rate: float | None
    """Fraction of stored energy lost per time step due to self-discharge. Unit: fraction."""
    minimum_state_of_charge: float | None
    """Minimum allowed state of charge, usually expressed as a fraction between 0 and 1 Unit: fraction."""
    maximum_state_of_charge: float | None
    """Maximum allowed state of charge, usually expressed as a fraction between 0 and 1. Unit: fraction."""
    initial_state_of_charge: float | None
    """Initial state of charge at the beginning of the optimization horizon, expressed as a fraction between 0 and 1. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    charging_variable_operating_cost: float | None
    """Marginal cost incurred per MWh of energy absorbed during the charging process, expressed in MU/MWh. Unit: MU/MWh."""
    maximum_charging_power: float | None
    """Upper limit on instantaneous power intake during charging, constrained by converter size and thermal limits (MW). Unit: MW."""
    maximum_discharging_power: float | None
    """Upper limit on instantaneous power output during discharging or generation, constrained by turbine/converter size and operating limits (MW). Unit: MW."""
    storage_technology_type: str | None
    """Storage technology category when no StorageType library entity is referenced."""
    @property
    def hasTechnology(self) -> StorageTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: StorageTypeProxy | StorageTypeId) -> None: ...
    @property
    def storesCarrier(self) -> CarrierProxy | None: ...
    @storesCarrier.setter
    def storesCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def storesResource(self) -> NaturalResourceProxy | None: ...
    @storesResource.setter
    def storesResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...

class StorageUnitDispatchResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    total_discharge_energy: float | None
    """Total energy discharged from storage over the horizon [MWh]. Unit: MWh."""
    total_charge_energy: float | None
    """Total energy charged into storage over the horizon [MWh]. Unit: MWh."""
    storage_cycles: float | None
    """Number of equivalent full charge/discharge cycles completed over the optimisation horizon [-]."""
    average_round_trip_efficiency: float | None
    """Realised round-trip efficiency over the horizon: total_discharge / total_charge [-]."""
    @property
    def reportsOn(self) -> StorageUnitProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: StorageUnitProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DispatchRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DispatchRunRecordProxy | str) -> None: ...
    @property
    def hasDischargeProfile(self) -> ProfileProxy | None: ...
    @hasDischargeProfile.setter
    def hasDischargeProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasChargeProfile(self) -> ProfileProxy | None: ...
    @hasChargeProfile.setter
    def hasChargeProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasStateOfChargeProfile(self) -> ProfileProxy | None: ...
    @hasStateOfChargeProfile.setter
    def hasStateOfChargeProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasDischargeDualProfile(self) -> ProfileProxy | None: ...
    @hasDischargeDualProfile.setter
    def hasDischargeDualProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasChargeDualProfile(self) -> ProfileProxy | None: ...
    @hasChargeDualProfile.setter
    def hasChargeDualProfile(self, value: ProfileProxy | str) -> None: ...

class SystemAssetProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""

class ThermalGenerationUnitProxy(EntityProxy):
    capacity_expansion: ThermalGenerationUnitCapacityExpansionProxy
    dispatch: ThermalGenerationUnitDispatchProxy
    dynamics: ThermalGenerationUnitDynamicsProxy
    power_flow: ThermalGenerationUnitPowerFlowProxy
    technical: ThermalGenerationUnitTechnicalProxy
    topology: ThermalGenerationUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    rated_voltage: float | None
    """Rated line-to-line terminal voltage of the deployed generation unit [kV]. Together with rated_apparent_power, defines the machine-specific impedance base. Unit: kV."""
    rated_apparent_power: float | None
    """Rated apparent power of the deployed generation unit [MVA]. Defines the machine-specific per-unit power base used with a linked DynamicMachineModelType. Unit: MVA."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    minimum_generation: float | None
    """The minimum active power output that the generation entity can continuously produce while remaining in stable operation. This value represents the lower operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    maximum_generation: float | None
    """The maximum active power output that the generation entity can produce under normal operating conditions. This value represents the upper operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    annual_resource_potential: float | None
    """Specifies the total annually available quantity of a resource or carrier that can be utilized, harvested, extracted, or converted by the represented entity under the assumptions of the associated scenario or resource representation. Unit: MWh/year."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    voltage_magnitude_setpoint: float | None
    """The target voltage magnitude maintained by the generator at its connected network node during the power flow analysis. This value is commonly used for PV bus modelling and voltage regulation studies and is typically expressed in per unit. Unit: pu."""
    voltage_angle_setpoint: float | None
    """The voltage phase angle associated with the generator bus within the power flow solution. The voltage angle represents the phase displacement of the bus voltage relative to the system reference angle and is typically expressed in degrees. Unit: deg."""
    active_power_setpoint: float | None
    """The target active power output assigned to the generator within the power flow calculation. This value defines the scheduled real power injection of the generator into the electrical network and is typically expressed in MW. Unit: MW."""
    reactive_power_setpoint: float | None
    """The target reactive power output assigned to the generator within the power flow calculation. This value defines the scheduled reactive power injection used for voltage support and reactive power balancing in the electrical network and is typically expressed in MVAr. Unit: MVAr."""
    maximum_active_power_output: float | None
    """Maximum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MW. Unit: MW."""
    minimum_active_power_output: float | None
    """Minimum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MW. Unit: MW."""
    maximum_reactive_power_output: float | None
    """Maximum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MVAr. Unit: MVAr."""
    minimum_reactive_power_output: float | None
    """Minimum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MVAr. Unit: MVAr."""
    cooling_type: str | None
    """Cooling system type for a thermal plant (once-through, tower, air, …)."""
    reactor_type: str | None
    """Nuclear reactor technology type. Determines neutron spectrum, coolant, moderator, fuel cycle, and safety characteristics. PWR: pressurised water reactor (most common globally). BWR: boiling water reactor. PHWR: pressurised heavy-water reactor (e.g. CANDU). SMR: small modular reactor (<300 MWe). Allowed values: PWR, BWR, PHWR, SMR."""
    thermal_capacity: float | None
    """Gross thermal power output of the nuclear reactor core under rated conditions. The electrical output is thermal_capacity multiplied by the net electrical efficiency. Relevant for thermal discharge licensing and fuel management. Unit: MW_th."""
    minimum_up_time: float | None
    """Minimum number of hours a unit must remain online once started. Used in unit commitment models. Unit: h."""
    minimum_down_time: float | None
    """Minimum number of hours a unit must remain offline after shutdown. Used in unit commitment models. Unit: h."""
    hot_start_cost: float | None
    """Cost incurred to restart a generator that has been recently offline (hot state), expressed in monitary units. Reflects fuel and operational overhead. Unit: MU."""
    cold_start_cost: float | None
    """Cost incurred to restart a generator that has been offline for a long period (cold state), expressed in MU. Usually higher than hot start due to additional operational procedures. Unit: MU."""
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> GeneratorTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: GeneratorTypeProxy | GeneratorTypeId) -> None: ...
    @property
    def hasInputResource(self) -> NaturalResourceProxy | None: ...
    @hasInputResource.setter
    def hasInputResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasOutputCarrier(self) -> CarrierProxy | None: ...
    @hasOutputCarrier.setter
    def hasOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...

class TimestampSeriesProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    start_datetime: str
    """ISO 8601 datetime string marking the first timestep of the series (e.g. "2009-01-01T00:00:00"). Combined with resolution and length this fully defines the time axis without storing the full array."""
    resolution: str
    """ISO 8601 duration string defining the uniform step size between consecutive timesteps (e.g. "PT1H" for hourly, "PT15M" for quarter-hourly, "P1D" for daily). All timesteps within one TimestampSeries are assumed to have equal duration."""
    length: int
    """Total number of timesteps in the series. Must equal the length of the values array stored in the HDF5 file for every Profile that references this TimestampSeries."""
    timezone: str | None
    """IANA timezone identifier for the series (e.g. "UTC", "Europe/Zurich"). Used when converting between local time and epoch timestamps. Defaults to UTC if not specified."""

class TransformerProxy(EntityProxy):
    capacity_expansion: TransformerCapacityExpansionProxy
    power_flow: TransformerPowerFlowProxy
    topology: TransformerTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    rated_primary_voltage: float | None
    """Rated line-to-line voltage on the primary (high-voltage) winding of a power transformer, expressed in kV. Used to define the voltage transformation ratio and for per-unit system normalisation in power flow calculations. Unit: kV."""
    rated_secondary_voltage: float | None
    """Rated line-to-line voltage on the secondary (low-voltage) winding of a power transformer, expressed in kV. Combined with rated_primary_voltage this defines the nominal transformation ratio. Unit: kV."""
    short_circuit_voltage_in_percentage: float | None
    """Short-circuit voltage of a transformer expressed as a percentage of rated voltage (%). Determines the transformer's series reactance in per-unit: x_pu = short_circuit_voltage_in_percentage / 100. Used directly in power flow and fault analysis calculations. Unit: %."""
    thermal_capacity_rating: float | None
    """Maximum continuous apparent power the branch can carry without exceeding thermal limits, expressed in MVA. Unit: MVA."""
    tap_ratio: float | None
    """Off-nominal transformer tap ratio. In MATPOWER, a value of 0 or 1 indicates no off-nominal tap; values different from 1 represent transformer branch behaviour."""
    phase_shift_angle: float | None
    """Transformer phase-shift angle in degrees. Maps to the MATPOWER branch angle column and pandapower transformer shift_degree where applicable. Unit: deg."""
    @property
    def fromNode(self) -> ElectricalBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def toNode(self) -> ElectricalBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class TransmissionElementProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    @property
    def fromNode(self) -> NetworkNodeProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def toNode(self) -> NetworkNodeProxy | None: ...
    @toNode.setter
    def toNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class TransmissionElementDispatchResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    total_flow_1_to_2: float | None
    """Total energy flow in the 1→2 direction over the horizon [MWh]. Unit: MWh."""
    total_flow_2_to_1: float | None
    """Total energy flow in the 2→1 direction over the horizon [MWh]. Unit: MWh."""
    congestion_hours: int | None
    """Number of hours the line/interconnector was at its thermal limit. Unit: h."""
    total_congestion_rent: float | None
    """Total congestion rent collected over the horizon (shadow price × flow) [MU]. Unit: MU."""
    @property
    def reportsOn(self) -> GenericInterconnectorTransmissionLineTransformerHVDCLinkProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: GenericInterconnectorTransmissionLineTransformerHVDCLinkProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> DispatchRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: DispatchRunRecordProxy | str) -> None: ...
    @property
    def hasFlowProfile(self) -> ProfileProxy | None: ...
    @hasFlowProfile.setter
    def hasFlowProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasShadowPriceProfile(self) -> ProfileProxy | None: ...
    @hasShadowPriceProfile.setter
    def hasShadowPriceProfile(self, value: ProfileProxy | str) -> None: ...

class TransmissionElementPowerFlowResultProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    active_power_flow_from: float | None
    """Active power flow into the branch at its "from" end, from a single power-flow snapshot [MW]. Unit: MW."""
    reactive_power_flow_from: float | None
    """Reactive power flow into the branch at its "from" end, from a single power-flow snapshot [MVAr]. Unit: MVAr."""
    active_power_flow_to: float | None
    """Active power flow into the branch at its "to" end, from a single power-flow snapshot [MW]. Unit: MW."""
    reactive_power_flow_to: float | None
    """Reactive power flow into the branch at its "to" end, from a single power-flow snapshot [MVAr]. Unit: MVAr."""
    active_power_loss: float | None
    """Instantaneous active power loss on the branch, from a single power-flow snapshot [MW]. Unit: MW."""
    reactive_power_loss: float | None
    """Instantaneous reactive power loss (or generation, for a line's charging) on the branch, from a single power-flow snapshot [MVAr]. Unit: MVAr."""
    current_magnitude: float | None
    """Branch current magnitude from a single power-flow snapshot [kA]. Unit: kA."""
    loading_percent: float | None
    """Thermal loading relative to rated capacity from a single power-flow snapshot [%]. Unit: %."""
    average_loading_percent: float | None
    """Time-averaged thermal loading relative to rated capacity [%]. Unit: %."""
    max_loading_percent: float | None
    """Maximum thermal loading relative to rated capacity observed over the power-flow run [%]. Unit: %."""
    total_active_power_loss: float | None
    """Total active-power loss on the element, integrated over the power-flow run. Unit: MWh."""
    @property
    def reportsOn(self) -> TransmissionLineTransformerHVDCLinkGenericInterconnectorProxy: ...
    @reportsOn.setter
    def reportsOn(self, value: TransmissionLineTransformerHVDCLinkGenericInterconnectorProxy | str) -> None: ...
    @property
    def hasRunRecord(self) -> PowerFlowRunRecordProxy: ...
    @hasRunRecord.setter
    def hasRunRecord(self, value: PowerFlowRunRecordProxy | str) -> None: ...
    @property
    def hasLoadingProfile(self) -> ProfileProxy | None: ...
    @hasLoadingProfile.setter
    def hasLoadingProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def hasActivePowerLossProfile(self) -> ProfileProxy | None: ...
    @hasActivePowerLossProfile.setter
    def hasActivePowerLossProfile(self, value: ProfileProxy | str) -> None: ...

class TransmissionLineProxy(EntityProxy):
    capacity_expansion: TransmissionLineCapacityExpansionProxy
    power_flow: TransmissionLinePowerFlowProxy
    topology: TransmissionLineTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    from_switch_closed: bool | None
    """Boolean indicating whether the breaker at the from-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    to_switch_closed: bool | None
    """Boolean indicating whether the breaker at the to-end of the branch is closed (true = connected, false = disconnected). Used in contingency and outage modelling."""
    series_resistance_per_km: float | None
    """Series resistance of the branch per unit length. This is the real component of the series impedance and represents resistive conductor losses, expressed in ohm per kilometre (Ohm/km). Unit: Ohm/km."""
    series_reactance_per_km: float | None
    """Series reactance of the branch per unit length. This is the imaginary component of the series impedance and represents inductive behaviour relevant for power-flow and voltage calculations, expressed in ohm per kilometre (Ohm/km). Unit: Ohm/km."""
    shunt_susceptance_per_km: float | None
    """Shunt susceptance of the branch per unit length. This is the imaginary component of the shunt admittance, not the shunt capacitance. It represents capacitive charging behaviour and is expressed in micro-siemens per kilometre (microS/km). Unit: microS/km."""
    line_length: float | None
    """Physical length of the transmission or pipeline element, expressed in kilometres. Used to scale per-unit-length electrical or hydraulic parameters. Unit: km."""
    parallel_circuit_count: int | None
    """Number of identical circuits run in parallel between the same endpoints. Increases total capacity and reduces effective impedance."""
    thermal_capacity_rating: float | None
    """Maximum continuous apparent power the branch can carry without exceeding thermal limits, expressed in MVA. Unit: MVA."""
    @property
    def fromNode(self) -> ElectricalBusProxy | None: ...
    @fromNode.setter
    def fromNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def toNode(self) -> ElectricalBusProxy | None: ...
    @toNode.setter
    def toNode(self, value: ElectricalBusProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> TransmissionTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: TransmissionTypeProxy | str) -> None: ...

class TransmissionTypeProxy(EntityProxy):
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    investment_cost: float | None
    """Overnight investment cost of the technology per unit of installed capacity or per unit, depending on the modeling convention. Used together with technical_lifetime and discount_rate for annualized cost calculations. Unit: MU/kW, MU/MW, MU/unit."""
    technical_lifetime: float | None
    """Technical lifetime of the asset in years. Unit: years."""
    discount_rate: float | None
    """Discount rate applied to investment and cost streams associated with this technology, expressed as a fraction between 0 and 1 (e.g. 0.03 for 3%). May override a global discount rate defined at the Energy System Model level. Unit: fraction."""
    salvage_fraction_value: float | None
    """Fraction of the original investment value that is recovered as salvage at the end of the planning horizon, expressed as a fraction between 0 and 1. Used for partial lifetime treatment when the technology lifetime extends beyond the modeled period. Unit: fraction."""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    minimum_up_time: float | None
    """Minimum number of hours a unit must remain online once started. Used in unit commitment models. Unit: h."""
    minimum_down_time: float | None
    """Minimum number of hours a unit must remain offline after shutdown. Used in unit commitment models. Unit: h."""
    hot_start_cost: float | None
    """Cost incurred to restart a generator that has been recently offline (hot state), expressed in monitary units. Reflects fuel and operational overhead. Unit: MU."""
    cold_start_cost: float | None
    """Cost incurred to restart a generator that has been offline for a long period (cold state), expressed in MU. Usually higher than hot start due to additional operational procedures. Unit: MU."""
    ramping_cost_increase: float | None
    """The cost associated with increasing output power, expressed in MU/MW or MU/MW/min. Used in dispatch optimisation to represent wear, thermal cycling, or operational penalties for fast upward ramping. Unit: MU/MW."""
    ramping_cost_decrease: float | None
    """The cost associated with reducing output power or reducing charging rate, expressed in MonetaryUnits/MW or MonetaryUnits/MW/min. Represents operational constraints or efficiency penalties during ramp-down."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    comment: str | None
    """Optional comment/notes."""
    line_length: float | None
    """Physical length of the transmission or pipeline element, expressed in kilometres. Used to scale per-unit-length electrical or hydraulic parameters. Unit: km."""
    series_resistance_per_km: float | None
    """Series resistance of the branch per unit length. This is the real component of the series impedance and represents resistive conductor losses, expressed in ohm per kilometre (Ohm/km). Unit: Ohm/km."""
    series_reactance_per_km: float | None
    """Series reactance of the branch per unit length. This is the imaginary component of the series impedance and represents inductive behaviour relevant for power-flow and voltage calculations, expressed in ohm per kilometre (Ohm/km). Unit: Ohm/km."""
    shunt_susceptance_per_km: float | None
    """Shunt susceptance of the branch per unit length. This is the imaginary component of the shunt admittance, not the shunt capacitance. It represents capacitive charging behaviour and is expressed in micro-siemens per kilometre (microS/km). Unit: microS/km."""
    thermal_capacity_rating: float | None
    """Maximum continuous apparent power the branch can carry without exceeding thermal limits, expressed in MVA. Unit: MVA."""
    parallel_circuit_count: int | None
    """Number of identical circuits run in parallel between the same endpoints. Increases total capacity and reduces effective impedance."""
    @property
    def hasCarrier(self) -> CarrierProxy: ...
    @hasCarrier.setter
    def hasCarrier(self, value: CarrierProxy | str) -> None: ...

class WindGenerationUnitProxy(EntityProxy):
    capacity_expansion: WindGenerationUnitCapacityExpansionProxy
    dispatch: WindGenerationUnitDispatchProxy
    dynamics: WindGenerationUnitDynamicsProxy
    power_flow: WindGenerationUnitPowerFlowProxy
    technical: WindGenerationUnitTechnicalProxy
    topology: WindGenerationUnitTopologyProxy
    name: str | None
    """Descriptive name."""
    long_name: str | None
    """Long description"""
    description: str | None
    """Textual description providing additional semantic, contextual, or explanatory information about the entity."""
    commissioning_year: int | None
    """Year in which the generation unit was first commissioned and became commercially operational. Instance-specific: determines actual age, real efficiency relative to nameplate, and remaining technical lifetime. Distinct from commission_date (which carries the full date) — year alone is sufficient for most planning and ageing models."""
    commission_date: datetime | None
    """The date when the generator was first commissioned and became operational. Used for lifecycle, availability, and depreciation modeling. Unit: date."""
    retrofit_date: datetime | None
    """Date of major upgrade or efficiency retrofit. Impacts operational efficiency, lifetime extension, and emission calculations. Unit: date."""
    retirement_date: datetime | None
    """Planned or actual date when the generator is permanently retired from service. Used for asset replacement planning and system expansion studies. Unit: date."""
    rated_voltage: float | None
    """Rated line-to-line terminal voltage of the deployed generation unit [kV]. Together with rated_apparent_power, defines the machine-specific impedance base. Unit: kV."""
    rated_apparent_power: float | None
    """Rated apparent power of the deployed generation unit [MVA]. Defines the machine-specific per-unit power base used with a linked DynamicMachineModelType. Unit: MVA."""
    generator_technology_type: str | None
    """Generation technology category when no GeneratorType library entity is referenced."""
    nominal_power_capacity: float | None
    """Maximum instantaneous power that the conversion unit can deliver or absorb, in MW. Defines operational limits for dispatch. Unit: MW."""
    minimum_generation: float | None
    """The minimum active power output that the generation entity can continuously produce while remaining in stable operation. This value represents the lower operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    maximum_generation: float | None
    """The maximum active power output that the generation entity can produce under normal operating conditions. This value represents the upper operational dispatch limit of the generator and is typically expressed in MW. Unit: MW."""
    variable_operating_cost: float | None
    """Marginal operating cost per unit of output (or throughput) used in dispatch optimisation. Unit: MU/MWh."""
    fixed_operating_cost: float | None
    """Fixed operation and maintenance (O&M) cost associated with the technology, typically expressed per year and per unit of installed capacity or per unit of technology. Covers costs that do not depend on energy production. Unit: MU/year, MU/(kW/year), MU/(MW/year), MU/unit."""
    energy_conversion_efficiency: float | None
    """Ratio of useful output energy to input energy, expressed as a fraction (0–1). Determines efficiency of energy conversion processes. Unit: fraction."""
    annual_resource_potential: float | None
    """Specifies the total annually available quantity of a resource or carrier that can be utilized, harvested, extracted, or converted by the represented entity under the assumptions of the associated scenario or resource representation. Unit: MWh/year."""
    dispatch_type: str | None
    """Dispatch classification of a generation technology: "dispatchable" — operator can choose output (thermal, hydro reservoir) "nondispatchable" — output bounded by external resource (wind, solar, RoR) "must_run" — must generate at minimum level (nuclear baseload, CHP)"""
    maximum_ramp_rate_up: float | None
    """The maximum increase in output power per unit time, typically expressed in kW/s or MW/min. Represents the upward operational flexibility of the asset (a generator ramping up, or a storage device discharging faster). Unit: %/h."""
    maximum_ramp_rate_down: float | None
    """The maximum percentage decrease in output power per unit time during ramp-down operations. Expressed as %/min or %/s, capturing the asset's downward operational flexibility (a generator ramping down, or a storage device changing its charging/discharging rate). Unit: %/h."""
    voltage_magnitude_setpoint: float | None
    """The target voltage magnitude maintained by the generator at its connected network node during the power flow analysis. This value is commonly used for PV bus modelling and voltage regulation studies and is typically expressed in per unit. Unit: pu."""
    voltage_angle_setpoint: float | None
    """The voltage phase angle associated with the generator bus within the power flow solution. The voltage angle represents the phase displacement of the bus voltage relative to the system reference angle and is typically expressed in degrees. Unit: deg."""
    active_power_setpoint: float | None
    """The target active power output assigned to the generator within the power flow calculation. This value defines the scheduled real power injection of the generator into the electrical network and is typically expressed in MW. Unit: MW."""
    reactive_power_setpoint: float | None
    """The target reactive power output assigned to the generator within the power flow calculation. This value defines the scheduled reactive power injection used for voltage support and reactive power balancing in the electrical network and is typically expressed in MVAr. Unit: MVAr."""
    maximum_active_power_output: float | None
    """Maximum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MW. Unit: MW."""
    minimum_active_power_output: float | None
    """Minimum active power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MW. Unit: MW."""
    maximum_reactive_power_output: float | None
    """Maximum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMAX and is expressed in MVAr. Unit: MVAr."""
    minimum_reactive_power_output: float | None
    """Minimum reactive power output of a generator in power-flow or OPF formulations. This corresponds to MATPOWER QMIN and is expressed in MVAr. Unit: MVAr."""
    hub_height: float | None
    """Height of the wind turbine hub above ground level. Determines the wind speed at rotor height via the wind shear profile, and therefore directly affects annual energy yield. Instance-specific: two turbines of the same type may have different hub heights depending on site conditions. Unit: m."""
    rotor_diameter: float | None
    """Diameter of the wind turbine rotor. Together with hub_height, determines the swept area and the rated power curve. Instance-specific. Unit: m."""
    installation_type: str | None
    """Installation category of the wind turbine. Determines foundation type, accessibility, and O&M cost profile. Allowed values: onshore, offshore, floating_offshore."""
    number_of_turbines: int | None
    """Number of individual wind turbines within this GenerationUnit (wind farm). Used to derive per-turbine statistics and wake-loss modelling."""
    @property
    def usesDynamicModelType(self) -> DynamicMachineModelTypeProxy | None: ...
    @usesDynamicModelType.setter
    def usesDynamicModelType(self, value: DynamicMachineModelTypeProxy | str) -> None: ...
    @property
    def hasTechnology(self) -> GeneratorTypeProxy | None: ...
    @hasTechnology.setter
    def hasTechnology(self, value: GeneratorTypeProxy | GeneratorTypeId) -> None: ...
    @property
    def hasInputResource(self) -> NaturalResourceProxy | None: ...
    @hasInputResource.setter
    def hasInputResource(self, value: NaturalResourceProxy | NaturalResourceId) -> None: ...
    @property
    def hasInputCarrier(self) -> CarrierProxy | None: ...
    @hasInputCarrier.setter
    def hasInputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasOutputCarrier(self) -> CarrierProxy | None: ...
    @hasOutputCarrier.setter
    def hasOutputCarrier(self, value: CarrierProxy | CarrierId) -> None: ...
    @property
    def hasAvailabilityProfile(self) -> ProfileProxy | None: ...
    @hasAvailabilityProfile.setter
    def hasAvailabilityProfile(self, value: ProfileProxy | str) -> None: ...
    @property
    def atNode(self) -> NetworkNodeProxy | None: ...
    @atNode.setter
    def atNode(self, value: NetworkNodeProxy | str) -> None: ...
    @property
    def hasAutomaticVoltageRegulator(self) -> ControllerAVRProxy | None: ...
    @hasAutomaticVoltageRegulator.setter
    def hasAutomaticVoltageRegulator(self, value: ControllerAVRProxy | str) -> None: ...
    @property
    def hasTurbineGovernor(self) -> ControllerGOVProxy | None: ...
    @hasTurbineGovernor.setter
    def hasTurbineGovernor(self, value: ControllerGOVProxy | str) -> None: ...
    @property
    def hasPowerSystemStabilizer(self) -> ControllerPSSProxy | None: ...
    @hasPowerSystemStabilizer.setter
    def hasPowerSystemStabilizer(self, value: ControllerPSSProxy | str) -> None: ...
