"""Number entities for writable Hargassner parameters."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .coordinator import HargassnerCoordinator
from .entity_base import HargassnerEntity

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class HargassnerNumberDescription(NumberEntityDescription):
    widget_prefix: str = ""

NUMBER_DESCRIPTIONS: list[HargassnerNumberDescription] = [
    HargassnerNumberDescription(
        key="room_temperature_heating", translation_key="room_temperature_heating", widget_prefix="HEATING_CIRCUIT",
        device_class=NumberDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=14.0, native_max_value=26.0, native_step=0.5, mode=NumberMode.BOX,
    ),
    HargassnerNumberDescription(
        key="room_temperature_reduction", translation_key="room_temperature_reduction", widget_prefix="HEATING_CIRCUIT",
        device_class=NumberDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=8.0, native_max_value=24.0, native_step=0.5, mode=NumberMode.BOX,
    ),
    HargassnerNumberDescription(
        key="deactivation_limit_heating", translation_key="deactivation_limit_heating", widget_prefix="HEATING_CIRCUIT",
        device_class=NumberDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.0, native_max_value=50.0, native_step=1.0, mode=NumberMode.BOX,
    ),
    HargassnerNumberDescription(
        key="deactivation_limit_reduction_day", translation_key="deactivation_limit_reduction_day", widget_prefix="HEATING_CIRCUIT",
        device_class=NumberDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-40.0, native_max_value=50.0, native_step=1.0, mode=NumberMode.BOX,
    ),
    HargassnerNumberDescription(
        key="deactivation_limit_reduction_night", translation_key="deactivation_limit_reduction_night", widget_prefix="HEATING_CIRCUIT",
        device_class=NumberDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-40.0, native_max_value=50.0, native_step=1.0, mode=NumberMode.BOX,
    ),
    HargassnerNumberDescription(
        key="steepness", translation_key="steepness", widget_prefix="HEATING_CIRCUIT",
        native_unit_of_measurement="", native_min_value=0.2, native_max_value=3.5, native_step=0.05,
        mode=NumberMode.SLIDER, icon="mdi:slope-uphill",
    ),
    HargassnerNumberDescription(
        key="fuel_stock", translation_key="fuel_stock", widget_prefix="HEATER",
        native_unit_of_measurement="kg", native_min_value=0.0, native_max_value=32000.0,
        native_step=1.0, mode=NumberMode.BOX, icon="mdi:sack",
    ),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: HargassnerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    if not coordinator.data:
        return
    for widget_key, widget_data in coordinator.data.items():
        if not isinstance(widget_data, dict) or "widget_type" not in widget_data:
            continue
        widget_type = widget_data["widget_type"]
        widget_name = widget_data["widget_name"]
        parameters = widget_data.get("parameters", {})
        for description in NUMBER_DESCRIPTIONS:
            if not widget_type.startswith(description.widget_prefix):
                continue
            param = parameters.get(description.key)
            if not isinstance(param, dict) or not param.get("resource"):
                continue
            # Use API min/max/step if available
            desc = HargassnerNumberDescription(
                key=description.key, translation_key=description.translation_key, widget_prefix=description.widget_prefix,
                device_class=description.device_class,
                native_unit_of_measurement=description.native_unit_of_measurement,
                native_min_value=float(param.get("min", description.native_min_value)),
                native_max_value=float(param.get("max", description.native_max_value)),
                native_step=float(param.get("step", description.native_step)),
                mode=description.mode, icon=description.icon,
            )
            entities.append(HargassnerNumberEntity(coordinator, widget_key, description.key, widget_name, desc))
    async_add_entities(entities)

class HargassnerNumberEntity(HargassnerEntity, NumberEntity):
    entity_description: HargassnerNumberDescription

    def __init__(self, coordinator, widget_key, param_key, widget_name, description):
        super().__init__(coordinator, widget_key, param_key, f"number_{widget_key}_{description.key}")
        self.entity_description = description
        self._attr_translation_placeholders = {"widget_name": widget_name}

    @property
    def native_value(self):
        param = self._get_parameter()
        if isinstance(param, dict):
            val = param.get("value")
            if val is not None:
                try: return float(val)
                except: pass
        return None

    async def async_set_native_value(self, value: float) -> None:
        resource = self._get_resource()
        if resource:
            await self.coordinator.async_patch_value(resource, value)
