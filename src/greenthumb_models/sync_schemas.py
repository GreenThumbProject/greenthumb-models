"""Pydantic DTOs for passing device configuration between layers.

These are pure Pydantic models (not SQLModel tables). They decouple the
hardware layer (DeviceManager, Sensor, Actuator) from SQLModel so that:
  - DeviceManager.init_from_config() never touches the database directly.
  - Cloud sync can deserialise JSON into these DTOs and push them to the Pi
    without a local DB write.
  - Unit tests can build a DeviceConfig without a real PostgreSQL session.

Build a DeviceConfig from the local DB with:
    from config_builder import build_config_from_db
    config = build_config_from_db(session, device_id)

Typical usage in lifespan:
    config = build_config_from_db(session, device_id)
    device_manager = DeviceManager(id=device_id)
    device_manager.init_from_config(config)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# =============================================================================
# SENSOR
# =============================================================================

class CapabilityConfig(BaseModel):
    """One variable that a sensor can measure."""
    id_variable:   int
    # snake_case name matching the key used in Sensor.read_data() dicts
    # e.g. "light_intensity", "temperature", "humidity"
    variable_name: str
    min_range:     Optional[float] = None
    max_range:     Optional[float] = None


class SensorConfig(BaseModel):
    """Configuration for a single device sensor."""
    id_device_sensor: int
    id_sensor_model:  int
    # Used to look up the correct class in SENSOR_REGISTRY
    # e.g. "TSL2561", "BMP280", "AHT10"
    model_name:       str
    port_address:     str
    capabilities:     List[CapabilityConfig]


# =============================================================================
# ACTUATOR
# =============================================================================

class ActuatorConfig(BaseModel):
    """Configuration for a single device actuator."""
    id_device_actuator: int
    id_actuator_model:  int
    # Registry key, e.g. "RGB_LED", "CAMERA", "WATER_PUMP"
    actuator_type:      str
    # Used to look up the correct class in ACTUATOR_REGISTRY
    # e.g. "3PIN RGB LED", "WebCam Redragon Hitman"
    model_name:         str
    # Human-readable label from device_actuator.name (e.g. "Greenhouse Camera")
    name:               Optional[str] = None
    # Instance-specific config (GPIO pins, camera source, etc.)
    instance_config:    Dict[str, Any]
    # Model-level specs shared by all instances of this model
    model_config_json:  Dict[str, Any] = {}


# =============================================================================
# THRESHOLD
# =============================================================================

class ThresholdConfig(BaseModel):
    """Environmental limit for automated monitoring / control.

    ``is_default_phase`` mirrors ``growth_phase.is_default`` on the linked
    growth phase. When True the threshold applies throughout the entire
    cultivation regardless of which phase is currently active (it references
    the 'All Phases' sentinel). The controller uses this flag in Task 2 to
    apply phase-aware threshold filtering.
    """
    id_threshold:       int
    id_cultivation:     int
    id_variable:        int
    id_growth_phase:    int
    # True  → "All Phases" sentinel (growth_phase.is_default = TRUE)
    # False → phase-specific threshold
    is_default_phase:   bool
    min_value:          Optional[float] = None
    max_value:          Optional[float] = None
    target_value:       Optional[float] = None
    # None = monitoring-only (no actuator wired up yet)
    id_actuator_action: Optional[int]   = None
    is_active:          bool            = True


# =============================================================================
# ACTIVE PHASE
# =============================================================================

class ActivePhaseInfo(BaseModel):
    """The cultivation phase that is currently active (ended_at IS NULL).

    Populated from the ``cultivation_phase`` table at startup. The controller
    uses ``id_growth_phase`` to select which non-default thresholds apply.
    """
    id_cultivation_phase: int
    id_cultivation:       int
    id_growth_phase:      int
    started_at:           datetime


# =============================================================================
# DEVICE CONFIG  (top-level DTO)
# =============================================================================

class DeviceConfig(BaseModel):
    """Complete hardware + cultivation configuration for one Pi device.

    This is the single object passed to ``DeviceManager.init_from_config()``.
    It contains everything the device manager needs to bring up all sensors
    and actuators without touching the database again.
    """
    id_device:    int
    name:         str
    # "LOW" | "MEDIUM" | "HIGH"
    device_mode:  str

    sensors:      List[SensorConfig]
    actuators:    List[ActuatorConfig]
    # All active thresholds for the active cultivation
    thresholds:   List[ThresholdConfig]
    # None if no active cultivation phase exists
    active_phase: Optional[ActivePhaseInfo] = None
