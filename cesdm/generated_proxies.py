"""AUTO-GENERATED CESDM proxy subclasses.

Do not edit manually. Run ``cesdm-generate-api`` after schema changes.
"""
from __future__ import annotations

from cesdm.proxy import EntityProxy

class SemanticEntityProxy(EntityProxy):
    """Proxy for CESDM entity class ``SemanticEntity``."""
    pass

class SystemAssetProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``SystemAsset``."""
    pass

class EnergyAssetInstanceProxy(SystemAssetProxy):
    """Proxy for CESDM entity class ``EnergyAssetInstance``."""
    pass

class ConversionUnitProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``ConversionUnit``."""
    pass

class BoilerUnitProxy(ConversionUnitProxy):
    """Proxy for CESDM entity class ``BoilerUnit``."""
    pass

class CHPUnitProxy(ConversionUnitProxy):
    """Proxy for CESDM entity class ``CHPUnit``."""
    pass

class CarrierProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``Carrier``."""
    pass

class CarrierDomainProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``CarrierDomain``."""
    pass

class ControllerProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``Controller``."""
    pass

class ControllerAVRProxy(ControllerProxy):
    """Proxy for CESDM entity class ``Controller.AVR``."""
    pass

class ControllerAVRAC1AProxy(ControllerAVRProxy):
    """Proxy for CESDM entity class ``Controller.AVR.AC1A``."""
    pass

class ControllerAVRIEEET1Proxy(ControllerAVRProxy):
    """Proxy for CESDM entity class ``Controller.AVR.IEEET1``."""
    pass

class ControllerAVRSEXSProxy(ControllerAVRProxy):
    """Proxy for CESDM entity class ``Controller.AVR.SEXS``."""
    pass

class ControllerAVRST1AProxy(ControllerAVRProxy):
    """Proxy for CESDM entity class ``Controller.AVR.ST1A``."""
    pass

class ControllerGOVProxy(ControllerProxy):
    """Proxy for CESDM entity class ``Controller.GOV``."""
    pass

class ControllerGOVGGOV1Proxy(ControllerGOVProxy):
    """Proxy for CESDM entity class ``Controller.GOV.GGOV1``."""
    pass

class ControllerGOVHYGOVProxy(ControllerGOVProxy):
    """Proxy for CESDM entity class ``Controller.GOV.HYGOV``."""
    pass

class ControllerGOVIEEEG1Proxy(ControllerGOVProxy):
    """Proxy for CESDM entity class ``Controller.GOV.IEEEG1``."""
    pass

class ControllerPSSProxy(ControllerProxy):
    """Proxy for CESDM entity class ``Controller.PSS``."""
    pass

class ControllerPSSPSS2AProxy(ControllerPSSProxy):
    """Proxy for CESDM entity class ``Controller.PSS.PSS2A``."""
    pass

class ControllerPSSPSS2BProxy(ControllerPSSProxy):
    """Proxy for CESDM entity class ``Controller.PSS.PSS2B``."""
    pass

class ControllerPSSSTAB1Proxy(ControllerPSSProxy):
    """Proxy for CESDM entity class ``Controller.PSS.STAB1``."""
    pass

class PortProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``Port``."""
    pass

class ConversionPortProxy(PortProxy):
    """Proxy for CESDM entity class ``ConversionPort``."""
    pass

class EnergyTechnologyTypeProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``EnergyTechnologyType``."""
    pass

class ConverterTypeProxy(EnergyTechnologyTypeProxy):
    """Proxy for CESDM entity class ``ConverterType``."""
    pass

class DemandUnitProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``DemandUnit``."""
    pass

class ResultProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``Result``."""
    pass

class DispatchResultProxy(ResultProxy):
    """Proxy for CESDM entity class ``DispatchResult``."""
    pass

class DemandUnitDispatchResultProxy(DispatchResultProxy):
    """Proxy for CESDM entity class ``DemandUnit.DispatchResult``."""
    pass

class RunRecordProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``RunRecord``."""
    pass

class DispatchRunRecordProxy(RunRecordProxy):
    """Proxy for CESDM entity class ``DispatchRunRecord``."""
    pass

class DynamicMachineModelTypeProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``DynamicMachineModelType``."""
    pass

class DynamicMachineModelTypeSynchronousProxy(DynamicMachineModelTypeProxy):
    """Proxy for CESDM entity class ``DynamicMachineModelType.Synchronous``."""
    pass

class DynamicResultProxy(ResultProxy):
    """Proxy for CESDM entity class ``DynamicResult``."""
    pass

class DynamicRunRecordProxy(RunRecordProxy):
    """Proxy for CESDM entity class ``DynamicRunRecord``."""
    pass

class NetworkNodeProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``NetworkNode``."""
    pass

class ElectricalBusProxy(NetworkNodeProxy):
    """Proxy for CESDM entity class ``ElectricalBus``."""
    pass

class PowerFlowResultProxy(ResultProxy):
    """Proxy for CESDM entity class ``PowerFlowResult``."""
    pass

class ElectricalBusPowerFlowResultProxy(PowerFlowResultProxy):
    """Proxy for CESDM entity class ``ElectricalBus.PowerFlowResult``."""
    pass

class TransmissionElementProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``TransmissionElement``."""
    pass

class ElectricityTransmissionProxy(TransmissionElementProxy):
    """Proxy for CESDM entity class ``ElectricityTransmission``."""
    pass

class ElectrolyserUnitProxy(ConversionUnitProxy):
    """Proxy for CESDM entity class ``ElectrolyserUnit``."""
    pass

class EnergySystemModelProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``EnergySystemModel``."""
    pass

class ExternalSupplyProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``ExternalSupply``."""
    pass

class FuelCellUnitProxy(ConversionUnitProxy):
    """Proxy for CESDM entity class ``FuelCellUnit``."""
    pass

class GasBusProxy(NetworkNodeProxy):
    """Proxy for CESDM entity class ``GasBus``."""
    pass

class GasTransmissionProxy(TransmissionElementProxy):
    """Proxy for CESDM entity class ``GasTransmission``."""
    pass

class GenerationUnitProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``GenerationUnit``."""
    pass

class GenerationUnitDispatchResultProxy(DispatchResultProxy):
    """Proxy for CESDM entity class ``GenerationUnit.DispatchResult``."""
    pass

class GenerationUnitDynamicResultProxy(DynamicResultProxy):
    """Proxy for CESDM entity class ``GenerationUnit.DynamicResult``."""
    pass

class GenerationUnitPowerFlowResultProxy(PowerFlowResultProxy):
    """Proxy for CESDM entity class ``GenerationUnit.PowerFlowResult``."""
    pass

class GeneratorTypeProxy(EnergyTechnologyTypeProxy):
    """Proxy for CESDM entity class ``GeneratorType``."""
    pass

class GenericConversionUnitProxy(ConversionUnitProxy):
    """Proxy for CESDM entity class ``GenericConversionUnit``."""
    pass

class GenericInterconnectorProxy(TransmissionElementProxy):
    """Proxy for CESDM entity class ``GenericInterconnector``."""
    pass

class GeographicalRegionProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``GeographicalRegion``."""
    pass

class HVDCLinkProxy(ElectricityTransmissionProxy):
    """Proxy for CESDM entity class ``HVDCLink``."""
    pass

class HeatBusProxy(NetworkNodeProxy):
    """Proxy for CESDM entity class ``HeatBus``."""
    pass

class HeatPumpUnitProxy(ConversionUnitProxy):
    """Proxy for CESDM entity class ``HeatPumpUnit``."""
    pass

class HeatTransmissionProxy(TransmissionElementProxy):
    """Proxy for CESDM entity class ``HeatTransmission``."""
    pass

class HydraulicStorageUnitProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``HydraulicStorageUnit``."""
    pass

class HydroGenerationUnitProxy(GenerationUnitProxy):
    """Proxy for CESDM entity class ``HydroGenerationUnit``."""
    pass

class HydrogenBusProxy(NetworkNodeProxy):
    """Proxy for CESDM entity class ``HydrogenBus``."""
    pass

class MarketZoneProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``MarketZone``."""
    pass

class NaturalResourceProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``NaturalResource``."""
    pass

class NetworkNodeDispatchResultProxy(DispatchResultProxy):
    """Proxy for CESDM entity class ``NetworkNode.DispatchResult``."""
    pass

class PowerFlowRunRecordProxy(RunRecordProxy):
    """Proxy for CESDM entity class ``PowerFlowRunRecord``."""
    pass

class ProfileProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``Profile``."""
    pass

class ShuntUnitProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``ShuntUnit``."""
    pass

class SolarGenerationUnitProxy(GenerationUnitProxy):
    """Proxy for CESDM entity class ``SolarGenerationUnit``."""
    pass

class StorageTypeProxy(EnergyTechnologyTypeProxy):
    """Proxy for CESDM entity class ``StorageType``."""
    pass

class StorageUnitProxy(EnergyAssetInstanceProxy):
    """Proxy for CESDM entity class ``StorageUnit``."""
    pass

class StorageUnitDispatchResultProxy(DispatchResultProxy):
    """Proxy for CESDM entity class ``StorageUnit.DispatchResult``."""
    pass

class ThermalGenerationUnitProxy(GenerationUnitProxy):
    """Proxy for CESDM entity class ``ThermalGenerationUnit``."""
    pass

class TimestampSeriesProxy(SemanticEntityProxy):
    """Proxy for CESDM entity class ``TimestampSeries``."""
    pass

class TransformerProxy(ElectricityTransmissionProxy):
    """Proxy for CESDM entity class ``Transformer``."""
    pass

class TransmissionElementDispatchResultProxy(DispatchResultProxy):
    """Proxy for CESDM entity class ``TransmissionElement.DispatchResult``."""
    pass

class TransmissionElementPowerFlowResultProxy(PowerFlowResultProxy):
    """Proxy for CESDM entity class ``TransmissionElement.PowerFlowResult``."""
    pass

class TransmissionLineProxy(ElectricityTransmissionProxy):
    """Proxy for CESDM entity class ``TransmissionLine``."""
    pass

class TransmissionTypeProxy(EnergyTechnologyTypeProxy):
    """Proxy for CESDM entity class ``TransmissionType``."""
    pass

class WindGenerationUnitProxy(GenerationUnitProxy):
    """Proxy for CESDM entity class ``WindGenerationUnit``."""
    pass
