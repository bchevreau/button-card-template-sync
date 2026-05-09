"""Buttons for Button Card Template Sync."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .runtime import async_clear_backups_for_entry, async_run_entry_sync


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons for one config entry."""
    async_add_entities(
        [
            ButtonCardTemplateSyncRunButton(hass, entry),
            ButtonCardTemplateSyncClearBackupsButton(hass, entry),
        ]
    )


class ButtonCardTemplateSyncRunButton(ButtonEntity):
    """Run sync using the entry's configured dry-run and backup options."""

    _attr_has_entity_name = True
    _attr_name = "Sync"
    _attr_icon = "mdi:sync"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_run_sync"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Button Card Template Sync",
        }

    async def async_press(self) -> None:
        """Run sync with the entry's configured settings."""
        await async_run_entry_sync(self.hass, self.entry)


class ButtonCardTemplateSyncClearBackupsButton(ButtonEntity):
    """Clear backups for this entry."""

    _attr_has_entity_name = True
    _attr_name = "Clear backups"
    _attr_icon = "mdi:delete-clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_clear_backups"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Button Card Template Sync",
        }

    async def async_press(self) -> None:
        """Clear backups for this entry."""
        await async_clear_backups_for_entry(self.hass, self.entry)
