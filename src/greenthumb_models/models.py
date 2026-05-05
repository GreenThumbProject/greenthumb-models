# models.py
"""SQLModel table definitions and Pydantic Create/Read/Update schemas.

Covers all tables defined in rasp5/db/01_schema.sql. Keep these two files in
sync: every column in the SQL must have a corresponding Field here, and vice
versa.

Table tiers (see architecture_analysis.md):
  Tier 0  — app_user
  Tier 1  — unit, variable, plant_species, growth_phase,
             sensor_model, actuator_model
  Tier 2  — device, device_sensor, sensor_capability,
             device_actuator, cultivation, threshold
  Tier 3  — measurement, cultivation_phase, photo, actuator_log
  Pi-only — sync_metadata
"""
import uuid
from typing import Optional, List
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field, Relationship
from dotenv import load_dotenv
import os

load_dotenv()

IS_CLOUD = os.getenv("IS_CLOUD")



# =============================================================================
# ENUMS
# =============================================================================

class DeviceMode(str, Enum):
    """Operating mode of a device. Maps to `device_mode_enum` in PostgreSQL."""
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


# =============================================================================
# TIER 0: APP USER
# =============================================================================

class AppUser(SQLModel, table=True):
    """User account. Source of truth lives in the Cloud; synced to Pi read-only.

    Table: app_user (note: 'user' is a PostgreSQL reserved word).
    """
    __tablename__ = "app_user"

    id_user:    uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    name:       str              = Field(description="Display name")
    email:      str              = Field(description="Unique email address")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)

    # Relationships
    devices: List["Device"] = Relationship(back_populates="user")


class AppUserBase(SQLModel):
    name:  str
    email: str

class AppUserCreate(AppUserBase):
    pass

class AppUserRead(AppUserBase):
    id_user:    uuid.UUID
    created_at: Optional[datetime] = None

class AppUserUpdate(SQLModel):
    name:  Optional[str] = None
    email: Optional[str] = None


# =============================================================================
# TIER 1: GLOBAL CATALOG
# =============================================================================

# -------------------- UNIT --------------------

class Unit(SQLModel, table=True):
    """Physical measurement unit (°C, lux, %, hPa, …). Table: unit."""
    id_unit: Optional[int] = Field(default=None, primary_key=True)
    symbol:  str            = Field(description="Unit symbol, e.g. '°C'")
    name:    str            = Field(description="Unit full name, e.g. 'Celsius'")

    variables: List["Variable"] = Relationship(back_populates="default_unit")


class UnitBase(SQLModel):
    symbol: str
    name:   str

class UnitCreate(UnitBase):
    pass

class UnitRead(UnitBase):
    id_unit: int

class UnitUpdate(SQLModel):
    symbol: Optional[str] = None
    name:   Optional[str] = None


# -------------------- VARIABLE --------------------

class Variable(SQLModel, table=True):
    """Measurable environmental quantity (Temperature, Humidity, …). Table: variable."""
    id_variable:     Optional[int] = Field(default=None, primary_key=True)
    name:            str            = Field(description="Variable name")
    description:     Optional[str]  = Field(default=None)
    default_unit_id: int            = Field(foreign_key="unit.id_unit")

    default_unit:  Optional[Unit]              = Relationship(back_populates="variables")
    capabilities:  List["SensorCapability"]    = Relationship(back_populates="variable")
    measurements:  List["Measurement"]         = Relationship(back_populates="variable")


class VariableBase(SQLModel):
    name:            str
    description:     Optional[str] = None
    default_unit_id: int

class VariableCreate(VariableBase):
    pass

class VariableRead(VariableBase):
    id_variable: int

class VariableUpdate(SQLModel):
    name:            Optional[str] = None
    description:     Optional[str] = None
    default_unit_id: Optional[int] = None


# -------------------- PLANT SPECIES --------------------

class PlantSpecies(SQLModel, table=True):
    """Plant type catalog entry. Table: plant_species."""
    __tablename__ = "plant_species"

    id_plant_species: Optional[int] = Field(default=None, primary_key=True)
    name:             str            = Field(description="Common name")
    scientific_name:  Optional[str]  = Field(default=None)

    cultivations:  List["Cultivation"]  = Relationship(back_populates="plant_species")
    growth_phases: List["GrowthPhase"]  = Relationship(back_populates="plant_species")


class PlantSpeciesBase(SQLModel):
    name:            str
    scientific_name: Optional[str] = None

class PlantSpeciesCreate(PlantSpeciesBase):
    pass

class PlantSpeciesRead(PlantSpeciesBase):
    id_plant_species: int

class PlantSpeciesUpdate(SQLModel):
    name:            Optional[str] = None
    scientific_name: Optional[str] = None


# -------------------- GROWTH PHASE --------------------

class GrowthPhase(SQLModel, table=True):
    """Species-level growth phase template (Seedling, Vegetative, …).

    The row with is_default=True (name='All Phases', phase_order=0) is a
    sentinel used by thresholds that apply throughout the entire cultivation.

    Table: growth_phase.
    """
    __tablename__ = "growth_phase"

    id_growth_phase:       Optional[int] = Field(default=None, primary_key=True)
    id_plant_species:      int            = Field(foreign_key="plant_species.id_plant_species")
    name:                  str            = Field(description="Phase name, e.g. 'Vegetative'")
    phase_order:           int            = Field(description="Sequence within the species (0 = All Phases sentinel)")
    description:           Optional[str]  = Field(default=None)
    typical_duration_days: Optional[int]  = Field(default=None)
    is_default:            bool           = Field(default=False, description="TRUE = applies to all phases (sentinel)")

    plant_species:      Optional[PlantSpecies]      = Relationship(back_populates="growth_phases")
    thresholds:         List["Threshold"]            = Relationship(back_populates="growth_phase")
    cultivation_phases: List["CultivationPhase"]     = Relationship(back_populates="growth_phase")


class GrowthPhaseBase(SQLModel):
    id_plant_species:      int
    name:                  str
    phase_order:           int
    description:           Optional[str] = None
    typical_duration_days: Optional[int] = None
    is_default:            bool          = False

class GrowthPhaseCreate(GrowthPhaseBase):
    pass

class GrowthPhaseRead(GrowthPhaseBase):
    id_growth_phase: int

class GrowthPhaseUpdate(SQLModel):
    name:                  Optional[str]  = None
    phase_order:           Optional[int]  = None
    description:           Optional[str]  = None
    typical_duration_days: Optional[int]  = None
    is_default:            Optional[bool] = None


# -------------------- SENSOR MODEL --------------------

class SensorModel(SQLModel, table=True):
    """Hardware sensor type (TSL2561, BMP280, AHT10). Table: sensor_model."""
    __tablename__ = "sensor_model"

    id_sensor_model: Optional[int] = Field(default=None, primary_key=True)
    model_name:      str            = Field(description="Model identifier used for registry lookup")
    manufacturer:    Optional[str]  = Field(default=None)

    device_sensors: List["DeviceSensor"]    = Relationship(back_populates="sensor_model")
    capabilities:   List["SensorCapability"] = Relationship(back_populates="sensor_model")


class SensorModelBase(SQLModel):
    model_name:   str
    manufacturer: Optional[str] = None

class SensorModelCreate(SensorModelBase):
    pass

class SensorModelRead(SensorModelBase):
    id_sensor_model: int

class SensorModelUpdate(SQLModel):
    model_name:   Optional[str] = None
    manufacturer: Optional[str] = None


# -------------------- ACTUATOR MODEL --------------------

class ActuatorModel(SQLModel, table=True):
    """Hardware actuator type (RGB_LED, CAMERA, …). Table: actuator_model."""
    __tablename__ = "actuator_model"

    id_actuator_model: Optional[int] = Field(default=None, primary_key=True)
    model_name:        str            = Field(description="Human-readable model name")
    actuator_type:     str            = Field(description="Registry key, e.g. 'RGB_LED'")
    manufacturer:      Optional[str]  = Field(default=None)
    model_config_json: dict           = Field(
        default_factory=dict,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict),
        description="Model-level hardware specs (voltage, max resolution, etc.)"
    )

    device_actuators: List["DeviceActuator"] = Relationship(back_populates="actuator_model")


class ActuatorModelBase(SQLModel):
    actuator_type:     str
    model_name:        str
    manufacturer:      Optional[str]  = None
    model_config_json: Optional[dict] = None

class ActuatorModelCreate(ActuatorModelBase):
    pass

class ActuatorModelRead(ActuatorModelBase):
    id_actuator_model: int

class ActuatorModelUpdate(SQLModel):
    actuator_type:     Optional[str]  = None
    model_name:        Optional[str]  = None
    manufacturer:      Optional[str]  = None
    model_config_json: Optional[dict] = None


# =============================================================================
# TIER 2: DEVICE CONFIGURATION
# =============================================================================

# -------------------- DEVICE --------------------

class Device(SQLModel, table=True):
    """Physical Raspberry Pi greenhouse device. Table: device.

    Pi-mutable fields: device_mode, is_dirty.
    When device_mode is changed locally, set is_dirty=True so the next sync
    pushes the change to the Cloud (last-write-wins via updated_at).
    """
    id_device:   Optional[int]       = Field(default=None, primary_key=True)
    name:        str                  = Field(description="Device display name")
    mac_address: Optional[str]        = Field(default=None)
    location:    Optional[str]        = Field(default=None)
    device_mode: DeviceMode           = Field(
        default=DeviceMode.MEDIUM,
        sa_column=Column(
            SAEnum(DeviceMode, name="device_mode_enum", create_type=False),
            nullable=False,
            server_default=DeviceMode.MEDIUM.value
        )
    )
    id_user:      Optional[uuid.UUID]  = Field(default=None, foreign_key="app_user.id_user")
    # Bearer token used by the Pi to authenticate with the Cloud API.
    # Generated by the cloud when a device is registered; never sent back in
    # read responses (excluded via DeviceRead / DeviceAdminRead).
    device_token: Optional[str]        = Field(default=None, description="Cloud API bearer token for this device")
    created_at:   Optional[datetime]   = Field(default_factory=datetime.now)
    updated_at:   Optional[datetime]   = Field(default_factory=datetime.now, description="Updated by DB trigger on every write")
    if not IS_CLOUD:
        is_dirty:     bool                 = Field(default=False, description="True when device_mode was changed locally and not yet synced")

    # Relationships
    user:             Optional["AppUser"]       = Relationship(back_populates="devices")
    device_sensors:   List["DeviceSensor"]      = Relationship(back_populates="device", sa_relationship_kwargs={"cascade": "all,delete-orphan"})
    device_actuators: List["DeviceActuator"]    = Relationship(back_populates="device", sa_relationship_kwargs={"cascade": "all,delete-orphan"})
    cultivations:     List["Cultivation"]       = Relationship(back_populates="device")
    photos:           List["Photo"]             = Relationship(back_populates="device")


class DeviceBase(SQLModel):
    name:        str
    mac_address: Optional[str]       = None
    location:    Optional[str]       = None
    device_mode: Optional[DeviceMode] = DeviceMode.MEDIUM
    id_user:     Optional[uuid.UUID]  = None

class DeviceCreate(DeviceBase):
    if not IS_CLOUD:
        is_dirty: Optional[bool] = False

class DeviceRead(DeviceBase):
    """Device read schema — device_token is intentionally excluded."""
    id_device:  int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DeviceAdminRead(DeviceRead):
    """Admin-only read schema that includes the device bearer token."""
    device_token: Optional[str] = None

class DeviceAdminUpdate(SQLModel):
    name:        Optional[str]       = None
    mac_address: Optional[str]       = None
    location:    Optional[str]       = None
    device_mode: Optional[DeviceMode] = None
    id_user:     Optional[uuid.UUID]  = None

class DeviceUpdate(DeviceAdminUpdate):
    if not IS_CLOUD:
        is_dirty:    Optional[bool]       = None


# -------------------- DEVICE SENSOR --------------------

class DeviceSensor(SQLModel, table=True):
    """Sensor instance installed on a device. Table: device_sensor."""
    __tablename__ = "device_sensor"

    id_device_sensor: Optional[int] = Field(default=None, primary_key=True)
    id_device:        int            = Field(foreign_key="device.id_device")
    id_sensor_model:  int            = Field(foreign_key="sensor_model.id_sensor_model")
    port_address:     Optional[str]  = Field(default=None, description="I2C address, e.g. '0x29'")
    is_active:        Optional[bool] = Field(default=True)
    installed_at:     Optional[datetime] = Field(default_factory=datetime.now)
    updated_at:       Optional[datetime] = Field(default_factory=datetime.now)

    device:       Optional[Device]      = Relationship(back_populates="device_sensors")
    sensor_model: Optional[SensorModel] = Relationship(back_populates="device_sensors")
    measurements: List["Measurement"]   = Relationship(back_populates="device_sensor")


class DeviceSensorBase(SQLModel):
    id_device:       int
    id_sensor_model: int
    port_address:    Optional[str]  = None
    is_active:       Optional[bool] = True

class DeviceSensorCreate(DeviceSensorBase):
    pass

class DeviceSensorRead(DeviceSensorBase):
    id_device_sensor: int
    installed_at:     Optional[datetime] = None
    updated_at:       Optional[datetime] = None

class DeviceSensorUpdate(SQLModel):
    id_device:       Optional[int]  = None
    id_sensor_model: Optional[int]  = None
    port_address:    Optional[str]  = None
    is_active:       Optional[bool] = None


# -------------------- SENSOR CAPABILITY --------------------

class SensorCapability(SQLModel, table=True):
    """What variables a sensor model can measure. Composite PK. Table: sensor_capability."""
    __tablename__ = "sensor_capability"

    id_sensor_model: int            = Field(foreign_key="sensor_model.id_sensor_model", primary_key=True)
    id_variable:     int            = Field(foreign_key="variable.id_variable",         primary_key=True)
    precision:       Optional[float] = Field(default=None)
    accuracy:        Optional[float] = Field(default=None, description="Measurement accuracy (±)")
    min_range:       Optional[float] = Field(default=None)
    max_range:       Optional[float] = Field(default=None)

    sensor_model: Optional[SensorModel] = Relationship(back_populates="capabilities")
    variable:     Optional[Variable]    = Relationship(back_populates="capabilities")


class SensorCapabilityBase(SQLModel):
    id_sensor_model: int
    id_variable:     int
    precision:       Optional[float] = None
    accuracy:        Optional[float] = None
    min_range:       Optional[float] = None
    max_range:       Optional[float] = None

class SensorCapabilityCreate(SensorCapabilityBase):
    pass

class SensorCapabilityRead(SensorCapabilityBase):
    pass

class SensorCapabilityUpdate(SQLModel):
    precision: Optional[float] = None
    accuracy:  Optional[float] = None
    min_range: Optional[float] = None
    max_range: Optional[float] = None


# -------------------- DEVICE ACTUATOR --------------------

class DeviceActuator(SQLModel, table=True):
    """Actuator instance installed on a device. Table: device_actuator."""
    __tablename__ = "device_actuator"

    id_device_actuator: Optional[int] = Field(default=None, primary_key=True)
    id_device:          int            = Field(foreign_key="device.id_device")
    id_actuator_model:  int            = Field(foreign_key="actuator_model.id_actuator_model")
    instance_config:    dict           = Field(
        default_factory=dict,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict),
        description="Instance-specific config, e.g. {\"pins\": {\"r\": 17, ...}}"
    )
    name:         Optional[str]      = Field(default=None)
    is_active:    Optional[bool]     = Field(default=True)
    installed_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at:   Optional[datetime] = Field(default_factory=datetime.now)

    device:         Optional["Device"]         = Relationship(back_populates="device_actuators")
    actuator_model: Optional[ActuatorModel]    = Relationship(back_populates="device_actuators")
    photos:         List["Photo"]              = Relationship(back_populates="device_actuator")
    actuator_logs:  List["ActuatorLog"]        = Relationship(back_populates="device_actuator")


class DeviceActuatorBase(SQLModel):
    id_device:         int
    id_actuator_model: int
    instance_config:   dict
    name:              Optional[str]  = None
    is_active:         Optional[bool] = True

class DeviceActuatorCreate(DeviceActuatorBase):
    pass

class DeviceActuatorRead(DeviceActuatorBase):
    id_device_actuator: int
    installed_at:       Optional[datetime] = None
    updated_at:         Optional[datetime] = None

class DeviceActuatorUpdate(SQLModel):
    id_device:         Optional[int]  = None
    id_actuator_model: Optional[int]  = None
    instance_config:   Optional[dict] = None
    name:              Optional[str]  = None
    is_active:         Optional[bool] = None


# -------------------- CULTIVATION --------------------

class Cultivation(SQLModel, table=True):
    """A grow cycle linking a device to a plant species. Table: cultivation."""
    id_cultivation:   Optional[int] = Field(default=None, primary_key=True)
    id_device:        int            = Field(foreign_key="device.id_device")
    id_plant_species: int            = Field(foreign_key="plant_species.id_plant_species")
    start_date:       datetime       = Field(default_factory=datetime.now)
    end_date:         Optional[datetime] = Field(default=None, description="NULL = active cultivation")
    notes:            Optional[str]  = Field(default=None)
    updated_at:       Optional[datetime] = Field(default_factory=datetime.now)

    device:             Optional[Device]          = Relationship(back_populates="cultivations")
    plant_species:      Optional[PlantSpecies]    = Relationship(back_populates="cultivations")
    thresholds:         List["Threshold"]         = Relationship(back_populates="cultivation")
    cultivation_phases: List["CultivationPhase"]  = Relationship(back_populates="cultivation")
    photos:             List["Photo"]             = Relationship(back_populates="cultivation")


class CultivationBase(SQLModel):
    id_device:        int
    id_plant_species: int
    start_date:       datetime       = Field(default_factory=datetime.now)
    end_date:         Optional[datetime] = None
    notes:            Optional[str]  = Field(default=None)

class CultivationCreate(CultivationBase):
    pass

class CultivationRead(CultivationBase):
    id_cultivation: int
    updated_at:     Optional[datetime] = None

class CultivationUpdate(SQLModel):
    id_device:        Optional[int]      = None
    id_plant_species: Optional[int]      = None
    start_date:       Optional[datetime] = None
    end_date:         Optional[datetime] = None
    notes:            Optional[str]      = None


# -------------------- THRESHOLD --------------------

class Threshold(SQLModel, table=True):
    """Environmental control limit for a cultivation × variable × phase.

    id_growth_phase is always set: use the species' is_default=True phase
    (All Phases) for thresholds that apply to the entire cultivation.

    Pi-mutable fields: min_value, max_value, target_value, is_active.
    Set is_dirty=True on any local write; cleared after sync.

    Table: threshold.
    """
    __table_args__ = (
        UniqueConstraint("id_cultivation", "id_variable", "id_growth_phase", name="uix_threshold"),
    )

    id_threshold:      Optional[int] = Field(default=None, primary_key=True)
    id_cultivation:    int            = Field(foreign_key="cultivation.id_cultivation")
    id_variable:       int            = Field(foreign_key="variable.id_variable")
    id_growth_phase:   int            = Field(foreign_key="growth_phase.id_growth_phase", description="References 'All Phases' (is_default=True) for cultivation-wide thresholds")
    min_value:         Optional[float] = Field(default=None)
    max_value:         Optional[float] = Field(default=None)
    target_value:      Optional[float] = Field(default=None)
    id_actuator_action: Optional[int]  = Field(default=None, foreign_key="device_actuator.id_device_actuator", description="NULL = monitoring-only")
    is_active:         bool            = Field(default=True)
    updated_at:        Optional[datetime] = Field(default_factory=datetime.now)
    if not IS_CLOUD:
        is_dirty:          bool            = Field(default=False, description="True when a Pi-mutable field was changed locally and not yet synced")

    cultivation:    Optional[Cultivation]    = Relationship(back_populates="thresholds")
    variable:       Optional[Variable]       = Relationship()
    growth_phase:   Optional[GrowthPhase]    = Relationship(back_populates="thresholds")
    actuator_action: Optional[DeviceActuator] = Relationship()


class ThresholdBase(SQLModel):
    id_cultivation:     int
    id_variable:        int
    id_growth_phase:    int
    min_value:          Optional[float] = None
    max_value:          Optional[float] = None
    target_value:       Optional[float] = None
    id_actuator_action: Optional[int]   = None
    is_active:          bool            = True

class ThresholdCreate(ThresholdBase):
    if not IS_CLOUD:
        is_dirty: Optional[bool] = False

class ThresholdRead(ThresholdBase):
    id_threshold: int
    updated_at:   Optional[datetime] = None

class ThresholdUpdate(SQLModel):
    id_cultivation:     Optional[int]   = None
    id_variable:        Optional[int]   = None
    id_growth_phase:    Optional[int]   = None
    min_value:          Optional[float] = None
    max_value:          Optional[float] = None
    target_value:       Optional[float] = None
    id_actuator_action: Optional[int]   = None
    is_active:          Optional[bool]  = None
    if not IS_CLOUD:
        is_dirty: Optional[bool] = None


# =============================================================================
# TIER 3: OPERATIONAL DATA
# =============================================================================

# -------------------- MEASUREMENT --------------------

class Measurement(SQLModel, table=True):
    """Single sensor reading persisted by the background task. Table: measurement.

    is_synced=False marks rows not yet pushed to the Cloud. The background sync
    task selects WHERE is_synced=FALSE, batches them, and marks them True on
    a successful POST to /sync/devices/{id}/measurements.
    """
    id_measurement:   Optional[int] = Field(default=None, primary_key=True)
    collected_at:     datetime       = Field(default_factory=datetime.now)
    value:            float          = Field(description="Numeric reading value")
    id_device_sensor: int            = Field(foreign_key="device_sensor.id_device_sensor")
    id_variable:      int            = Field(foreign_key="variable.id_variable")
    if not IS_CLOUD:
        is_synced:        bool           = Field(default=False, description="False until pushed to Cloud")

    device_sensor: Optional[DeviceSensor] = Relationship(back_populates="measurements")
    variable:      Optional[Variable]     = Relationship(back_populates="measurements")


class MeasurementBase(SQLModel):
    value:            float
    id_device_sensor: int
    id_variable:      int

class MeasurementCreate(MeasurementBase):
    if not IS_CLOUD:
        is_synced: Optional[bool] = False

class MeasurementRead(MeasurementBase):
    id_measurement: int
    collected_at:   Optional[datetime] = None
    if not IS_CLOUD:
        is_synced:      bool               = False

class MeasurementUpdate(SQLModel):
    collected_at:     Optional[datetime] = None
    value:            Optional[float]    = None
    id_device_sensor: Optional[int]      = None
    id_variable:      Optional[int]      = None
    if not IS_CLOUD:
        is_synced:        Optional[bool]     = None


# -------------------- CULTIVATION PHASE --------------------

class CultivationPhase(SQLModel, table=True):
    """Records which growth phase a cultivation is currently in.

    ended_at=NULL means this is the active phase. A partial unique index in the
    DB enforces at most one active phase per cultivation at a time.

    Table: cultivation_phase.
    """
    __tablename__ = "cultivation_phase"

    id_cultivation_phase: Optional[int] = Field(default=None, primary_key=True)
    id_cultivation:       int            = Field(foreign_key="cultivation.id_cultivation")
    id_growth_phase:      int            = Field(foreign_key="growth_phase.id_growth_phase")
    started_at:           datetime       = Field(description="When this phase began")
    ended_at:             Optional[datetime] = Field(default=None, description="NULL = currently active phase")
    detected_by:          str            = Field(default="manual", description="'manual' | 'cv' | 'ml'")
    notes:                Optional[str]  = Field(default=None)

    cultivation:  Optional[Cultivation]  = Relationship(back_populates="cultivation_phases")
    growth_phase: Optional[GrowthPhase]  = Relationship(back_populates="cultivation_phases")


class CultivationPhaseBase(SQLModel):
    id_cultivation:  int
    id_growth_phase: int
    started_at:      datetime
    ended_at:        Optional[datetime] = None
    detected_by:     str                = "manual"
    notes:           Optional[str]      = None

class CultivationPhaseCreate(CultivationPhaseBase):
    pass

class CultivationPhaseRead(CultivationPhaseBase):
    id_cultivation_phase: int

class CultivationPhaseUpdate(SQLModel):
    ended_at:    Optional[datetime] = None
    detected_by: Optional[str]      = None
    notes:       Optional[str]      = None


# -------------------- PHOTO --------------------

class Photo(SQLModel, table=True):
    """Metadata for a captured plant photo. Table: photo.

    File naming convention (enforced by application):
        {timestamp}_{device_id}_{actuator_id}.jpg

    id_device_actuator identifies which camera captured the photo, supporting
    future multi-camera setups.

    is_synced=False until the file is uploaded to Supabase Storage and
    cloud_url is populated.
    """
    id_photo:           Optional[int] = Field(default=None, primary_key=True)
    id_device:          int            = Field(foreign_key="device.id_device")
    id_device_actuator: int            = Field(foreign_key="device_actuator.id_device_actuator", description="Camera that captured this photo")
    id_cultivation:     Optional[int]  = Field(default=None, foreign_key="cultivation.id_cultivation")
    captured_at:        datetime       = Field(description="Timestamp of capture (also used in filename)")
    file_path:          Optional[str]  = Field(default=None, description="Local disk path, e.g. /data/photos/...")
    cloud_url:          Optional[str]  = Field(default=None, description="Supabase Storage URL after successful upload")
    file_size_bytes:    Optional[int]  = Field(default=None)
    width:              Optional[int]  = Field(default=None)
    height:             Optional[int]  = Field(default=None)
    if not IS_CLOUD:
        is_synced:          bool           = Field(default=False, description="False until uploaded to Supabase Storage")

    device:          Optional[Device]         = Relationship(back_populates="photos")
    device_actuator: Optional[DeviceActuator] = Relationship(back_populates="photos")
    cultivation:     Optional[Cultivation]    = Relationship(back_populates="photos")


class PhotoBase(SQLModel):
    id_device:          int
    id_device_actuator: int
    id_cultivation:     Optional[int]      = None
    captured_at:        datetime
    file_path:          Optional[str]      = None
    cloud_url:          Optional[str]      = None
    file_size_bytes:    Optional[int]      = None
    width:              Optional[int]      = None
    height:             Optional[int]      = None

class PhotoCreate(PhotoBase):
    if not IS_CLOUD:
        is_synced: Optional[bool] = False

class PhotoRead(PhotoBase):
    id_photo:  int
    if not IS_CLOUD:
        is_synced: bool = False

class PhotoUpdate(SQLModel):
    cloud_url:       Optional[str]  = None
    file_size_bytes: Optional[int]  = None
    width:           Optional[int]  = None
    height:          Optional[int]  = None
    if not IS_CLOUD:
        is_synced:       Optional[bool] = None


# -------------------- ACTUATOR LOG --------------------

class ActuatorLog(SQLModel, table=True):
    """Append-only log of every actuator action. Table: actuator_log.

    Logged by the controller after every command_actuator() call.
    triggered_by: 'controller' | 'manual' | 'threshold'
    """
    __tablename__ = "actuator_log"

    id_log:             Optional[int] = Field(default=None, primary_key=True)
    id_device_actuator: int            = Field(foreign_key="device_actuator.id_device_actuator")
    action_at:          datetime       = Field(default_factory=datetime.now)
    action:             str            = Field(description="'activate' | 'deactivate' | 'command'")
    payload:            Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=True),
        description="Command payload, e.g. {\"duty_cycle\": 100}"
    )
    triggered_by: str = Field(default="controller", description="'controller' | 'manual' | 'threshold'")

    device_actuator: Optional[DeviceActuator] = Relationship(back_populates="actuator_logs")


class ActuatorLogBase(SQLModel):
    id_device_actuator: int
    action:             str
    payload:            Optional[dict] = None
    triggered_by:       str            = "controller"

class ActuatorLogCreate(ActuatorLogBase):
    pass

class ActuatorLogRead(ActuatorLogBase):
    id_log:    int
    action_at: datetime


# =============================================================================
# PI-ONLY: SYNC METADATA
# =============================================================================

class SyncMetadata(SQLModel, table=True):
    """Key-value store for Pi sync state. Table: sync_metadata.

    Never pushed to the Cloud. Known keys:
      'last_config_sync' — ISO timestamp of last successful config pull
      'last_data_push'   — ISO timestamp of last successful measurement push
    """
    __tablename__ = "sync_metadata"

    key:        str      = Field(primary_key=True, description="Metadata key")
    value:      str      = Field(description="Metadata value (usually an ISO timestamp)")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)


class SyncMetadataBase(SQLModel):
    key:   str
    value: str

class SyncMetadataCreate(SyncMetadataBase):
    pass

class SyncMetadataRead(SyncMetadataBase):
    updated_at: Optional[datetime] = None

class SyncMetadataUpdate(SQLModel):
    value: Optional[str] = None


# =============================================================================
# MODEL REBUILD
# Resolves forward references in SQLModel/Pydantic v2 relationships.
# =============================================================================

for cls in [
    # Table models
    AppUser, Unit, Variable, PlantSpecies, GrowthPhase,
    SensorModel, ActuatorModel,
    Device, DeviceSensor, SensorCapability, DeviceActuator,
    Cultivation, Threshold,
    Measurement, CultivationPhase, Photo, ActuatorLog,
    SyncMetadata,
    # Create/Read/Update schemas
    AppUserCreate, AppUserRead, AppUserUpdate,
    UnitCreate, UnitRead, UnitUpdate,
    VariableCreate, VariableRead, VariableUpdate,
    PlantSpeciesCreate, PlantSpeciesRead, PlantSpeciesUpdate,
    GrowthPhaseCreate, GrowthPhaseRead, GrowthPhaseUpdate,
    SensorModelCreate, SensorModelRead, SensorModelUpdate,
    ActuatorModelCreate, ActuatorModelRead, ActuatorModelUpdate,
    DeviceCreate, DeviceRead, DeviceAdminRead, DeviceUpdate,
    DeviceSensorCreate, DeviceSensorRead, DeviceSensorUpdate,
    SensorCapabilityCreate, SensorCapabilityRead, SensorCapabilityUpdate,
    DeviceActuatorCreate, DeviceActuatorRead, DeviceActuatorUpdate,
    CultivationCreate, CultivationRead, CultivationUpdate,
    ThresholdCreate, ThresholdRead, ThresholdUpdate,
    MeasurementCreate, MeasurementRead, MeasurementUpdate,
    CultivationPhaseCreate, CultivationPhaseRead, CultivationPhaseUpdate,
    PhotoCreate, PhotoRead, PhotoUpdate,
    ActuatorLogCreate, ActuatorLogRead,
    SyncMetadataCreate, SyncMetadataRead, SyncMetadataUpdate,
]:
    try:
        cls.model_rebuild()
    except Exception:
        pass
