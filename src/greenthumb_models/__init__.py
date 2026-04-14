"""Shared SQLModel table definitions and Pydantic DTOs for GreenThumb.

Install this package on any service that needs to interact with GreenThumb
data — both the Pi (alongside greenthumb-rpi5) and any Cloud microservice.

Hardware drivers live in the separate ``greenthumb-rpi5`` package.
"""
from greenthumb_models.models import (
    # Enums
    DeviceMode,

    # Tier 0
    AppUser, AppUserCreate, AppUserRead, AppUserUpdate,

    # Tier 1 — global catalog
    Unit, UnitCreate, UnitRead, UnitUpdate,
    Variable, VariableCreate, VariableRead, VariableUpdate,
    PlantSpecies, PlantSpeciesCreate, PlantSpeciesRead, PlantSpeciesUpdate,
    GrowthPhase, GrowthPhaseCreate, GrowthPhaseRead, GrowthPhaseUpdate,
    SensorModel, SensorModelCreate, SensorModelRead, SensorModelUpdate,
    ActuatorModel, ActuatorModelCreate, ActuatorModelRead, ActuatorModelUpdate,

    # Tier 2 — device configuration
    Device, DeviceCreate, DeviceRead, DeviceUpdate,
    DeviceSensor, DeviceSensorCreate, DeviceSensorRead, DeviceSensorUpdate,
    SensorCapability, SensorCapabilityCreate, SensorCapabilityRead, SensorCapabilityUpdate,
    DeviceActuator, DeviceActuatorCreate, DeviceActuatorRead, DeviceActuatorUpdate,
    Cultivation, CultivationCreate, CultivationRead, CultivationUpdate,
    Threshold, ThresholdCreate, ThresholdRead, ThresholdUpdate,

    # Tier 3 — operational data
    Measurement, MeasurementCreate, MeasurementRead, MeasurementUpdate,
    CultivationPhase, CultivationPhaseCreate, CultivationPhaseRead, CultivationPhaseUpdate,
    Photo, PhotoCreate, PhotoRead, PhotoUpdate,
    ActuatorLog, ActuatorLogCreate, ActuatorLogRead,

    # Pi-only
    SyncMetadata, SyncMetadataCreate, SyncMetadataRead, SyncMetadataUpdate,
)
from greenthumb_models.sync_schemas import (
    CapabilityConfig,
    SensorConfig,
    ActuatorConfig,
    ThresholdConfig,
    ActivePhaseInfo,
    DeviceConfig,
)

__all__ = [
    # Enums
    "DeviceMode",

    # Tier 0
    "AppUser", "AppUserCreate", "AppUserRead", "AppUserUpdate",

    # Tier 1
    "Unit", "UnitCreate", "UnitRead", "UnitUpdate",
    "Variable", "VariableCreate", "VariableRead", "VariableUpdate",
    "PlantSpecies", "PlantSpeciesCreate", "PlantSpeciesRead", "PlantSpeciesUpdate",
    "GrowthPhase", "GrowthPhaseCreate", "GrowthPhaseRead", "GrowthPhaseUpdate",
    "SensorModel", "SensorModelCreate", "SensorModelRead", "SensorModelUpdate",
    "ActuatorModel", "ActuatorModelCreate", "ActuatorModelRead", "ActuatorModelUpdate",

    # Tier 2
    "Device", "DeviceCreate", "DeviceRead", "DeviceUpdate",
    "DeviceSensor", "DeviceSensorCreate", "DeviceSensorRead", "DeviceSensorUpdate",
    "SensorCapability", "SensorCapabilityCreate", "SensorCapabilityRead", "SensorCapabilityUpdate",
    "DeviceActuator", "DeviceActuatorCreate", "DeviceActuatorRead", "DeviceActuatorUpdate",
    "Cultivation", "CultivationCreate", "CultivationRead", "CultivationUpdate",
    "Threshold", "ThresholdCreate", "ThresholdRead", "ThresholdUpdate",

    # Tier 3
    "Measurement", "MeasurementCreate", "MeasurementRead", "MeasurementUpdate",
    "CultivationPhase", "CultivationPhaseCreate", "CultivationPhaseRead", "CultivationPhaseUpdate",
    "Photo", "PhotoCreate", "PhotoRead", "PhotoUpdate",
    "ActuatorLog", "ActuatorLogCreate", "ActuatorLogRead",

    # Pi-only
    "SyncMetadata", "SyncMetadataCreate", "SyncMetadataRead", "SyncMetadataUpdate",

    # DTOs
    "CapabilityConfig",
    "SensorConfig",
    "ActuatorConfig",
    "ThresholdConfig",
    "ActivePhaseInfo",
    "DeviceConfig",
]
