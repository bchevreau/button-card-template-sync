"""Config numbers for Button Card Template Sync."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BACKUP_RETENTION_COUNT,
    CONF_POLL_INTERVAL_SECONDS,
    DEFAULT_BACKUP_RETENTION_COUNT,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DOMAIN,
)
from .runtime import entry_signal, update_entry_option


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up config numbers for one config entry."""
    async_add_entities(
        [
            ButtonCardTemplateSyncPollIntervalNumber(hass, entry),
            ButtonCardTemplateSyncBackupRetentionNumber(hass, entry),
        ]
    )


class ButtonCardTemplateSyncPollIntervalNumber(NumberEntity):
    """Poll interval option."""

    _attr_has_entity_name = True
    _attr_name = "Poll interval"
    _attr_icon = "mdi:clock-fast"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False
    _attr_native_min_value = 1
    _attr_native_max_value = 3600
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "s"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{CONF_POLL_INTERVAL_SECONDS}"
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
    def native_value(self) -> int:
        """Return current poll interval."""
        return int(
            self.entry.options.get(
                CONF_POLL_INTERVAL_SECONDS,
                self.entry.data.get(
                    CONF_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS
                ),
            )
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set poll interval."""
        update_entry_option(
            self.hass, self.entry, CONF_POLL_INTERVAL_SECONDS, int(value)
        )


class ButtonCardTemplateSyncBackupRetentionNumber(NumberEntity):
    """Backup retention count option."""

    _attr_has_entity_name = True
    _attr_name = "Backup retention"
    _attr_icon = "mdi:archive-clock"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False
    _attr_native_min_value = 1
    _attr_native_max_value = 250
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "backups"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{CONF_BACKUP_RETENTION_COUNT}"
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
    def native_value(self) -> int:
        """Return current backup retention count."""
        return int(
            self.entry.options.get(
                CONF_BACKUP_RETENTION_COUNT,
                self.entry.data.get(
                    CONF_BACKUP_RETENTION_COUNT, DEFAULT_BACKUP_RETENTION_COUNT
                ),
            )
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set backup retention count."""
        update_entry_option(
            self.hass, self.entry, CONF_BACKUP_RETENTION_COUNT, int(value)
        )
