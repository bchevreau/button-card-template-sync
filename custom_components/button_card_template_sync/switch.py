"""Config switches for Button Card Template Sync."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_AUTO_SYNC,
    CONF_BACKUP_BEFORE_WRITE,
    CONF_DRY_RUN,
    DEFAULT_AUTO_SYNC,
    DEFAULT_BACKUP_BEFORE_WRITE,
    DEFAULT_DRY_RUN,
    DOMAIN,
)
from .runtime import entry_signal, update_entry_option


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up config switches for one config entry."""
    async_add_entities(
        [
            ButtonCardTemplateSyncOptionSwitch(
                hass,
                entry,
                key=CONF_DRY_RUN,
                name="Dry run",
                icon="mdi:checkbox-marked-circle-outline",
                default=DEFAULT_DRY_RUN,
            ),
            ButtonCardTemplateSyncOptionSwitch(
                hass,
                entry,
                key=CONF_AUTO_SYNC,
                name="Auto-sync",
                icon="mdi:auto-mode",
                default=DEFAULT_AUTO_SYNC,
            ),
            ButtonCardTemplateSyncOptionSwitch(
                hass,
                entry,
                key=CONF_BACKUP_BEFORE_WRITE,
                name="Backup before write",
                icon="mdi:backup-restore",
                default=DEFAULT_BACKUP_BEFORE_WRITE,
            ),
        ]
    )


class ButtonCardTemplateSyncOptionSwitch(SwitchEntity):
    """Switch backed by a config entry option."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        key: str,
        name: str,
        icon: str,
        default: bool,
        extra_attributes: dict[str, Any] | None = None,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.key = key
        self.default = default
        self._extra_attributes = extra_attributes or {}
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Button Card Template Sync",
        }

    async def async_added_to_hass(self) -> None:
        """Register update dispatcher."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                entry_signal(self.entry.entry_id),
                self._handle_entry_update,
            )
        )

    @callback
    def _handle_entry_update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return switch state."""
        return bool(
            self.entry.options.get(
                self.key, self.entry.data.get(self.key, self.default)
            )
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return self._extra_attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the option."""
        update_entry_option(self.hass, self.entry, self.key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the option."""
        update_entry_option(self.hass, self.entry, self.key, False)
