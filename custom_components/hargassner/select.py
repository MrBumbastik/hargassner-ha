"""Select entities for Hargassner option parameters."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HargassnerCoordinator
from .entity_base import HargassnerEntity

_LOGGER = logging.getLogger(__name__)

# (widget_prefix, param_key, translation_key)
# The translated, human-readable labels for each option live in
# strings.json / translations/*.json under entity.select.<translation_key>.state.
SELECT_CONFIGS = [
    ("HEATING_CIRCUIT", "mode", "circuit_mode"),
    ("HEATING_CIRCUIT", "pool_heating", "pool_heating_mode"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hargassner select entities."""
    coordinator: HargassnerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[HargassnerSelectEntity] = []

    if not coordinator.data:
        return

    for widget_key, widget_data in coordinator.data.items():
        if not isinstance(widget_data, dict) or "widget_type" not in widget_data:
            continue

        widget_type = widget_data["widget_type"]
        widget_name = widget_data["widget_name"]
        parameters = widget_data.get("parameters", {})

        for prefix, param_key, translation_key in SELECT_CONFIGS:
            if not widget_type.startswith(prefix):
                continue
            param = parameters.get(param_key)
            if not isinstance(param, dict):
                continue
            if not param.get("resource") or not param.get("options"):
                continue

            entities.append(
                HargassnerSelectEntity(
                    coordinator=coordinator,
                    widget_key=widget_key,
                    param_key=param_key,
                    widget_name=widget_name,
                    translation_key=translation_key,
                )
            )

    async_add_entities(entities)


class HargassnerSelectEntity(HargassnerEntity, SelectEntity):
    """Select entity for a Hargassner option parameter.

    Options and current_option expose the raw API values (e.g. "MODE_OFF").
    The human-readable labels are resolved by Home Assistant from
    entity.select.<translation_key>.state in strings.json/translations.
    """

    def __init__(
        self,
        coordinator: HargassnerCoordinator,
        widget_key: str,
        param_key: str,
        widget_name: str,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator, widget_key, param_key, f"select_{widget_key}_{param_key}")
        self._attr_translation_key = translation_key
        self._attr_translation_placeholders = {"widget_name": widget_name}

    @property
    def options(self) -> list[str]:
        param = self._get_parameter()
        if param:
            return param.get("options", [])
        return []

    @property
    def current_option(self) -> str | None:
        param = self._get_parameter()
        if param:
            return param.get("value")
        return None

    async def async_select_option(self, option: str) -> None:
        resource = self._get_resource()
        if resource:
            await self.coordinator.async_patch_value(resource, option)
