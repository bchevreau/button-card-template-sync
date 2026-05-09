"""Diagnostic sensors for Button Card Template Sync."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .runtime import entry_runtime, entry_signal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for one config entry."""
    async_add_entities(
        [
            ButtonCardTemplateSyncStatusSensor(hass, entry),
            ButtonCardTemplateSyncTemplateCountSensor(hass, entry),
            ButtonCardTemplateSyncLastSyncSensor(hass, entry),
        ]
    )


class ButtonCardTemplateSyncSensorBase(SensorEntity):
    """Base sensor for entry runtime data."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, key: str, name: str
    ) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
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
    def _last_result(self) -> dict[str, Any] | None:
        result = entry_runtime(self.hass, self.entry.entry_id).get("last_result")
        return result if isinstance(result, dict) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        result = self._last_result
        if not result:
            return {
                "target_dashboard": self.entry.options.get("target_dashboard")
                or self.entry.data.get("target_dashboard"),
                "template_folder": self.entry.options.get("template_folder")
                or self.entry.data.get("template_folder"),
            }

        return {
            "target_dashboard": result.get("target_dashboard"),
            "template_folder": result.get("template_folder"),
            "dry_run": result.get("dry_run"),
            "wrote": result.get("wrote"),
            "backup_ref": result.get("backup_ref"),
            "digest": result.get("digest"),
            "changed_keys": result.get("changed_keys"),
            "preserved_key_count": result.get("preserved_key_count"),
            "preserved_keys": result.get("preserved_keys"),
            "unexpected_changed_keys": result.get("unexpected_changed_keys"),
            "views_unchanged": result.get("views_unchanged"),
            "kiosk_mode_unchanged": result.get("kiosk_mode_unchanged"),
            "templates_added_count": result.get("templates_added_count"),
            "templates_removed_count": result.get("templates_removed_count"),
            "templates_changed_count": result.get("templates_changed_count"),
            "backup_count": result.get("backup_count"),
            "error": result.get("error"),
            **self._auto_sync_attributes,
        }

    @property
    def _auto_sync_attributes(self) -> dict[str, Any]:
        state = entry_runtime(self.hass, self.entry.entry_id).get("auto_sync_state")
        if not isinstance(state, dict):
            return {}
        return {
            "auto_sync_enabled": state.get("enabled"),
            "last_folder_signature": state.get("last_folder_signature"),
            "last_folder_file_count": state.get("last_folder_file_count"),
            "pending_change_detected": state.get("pending_change_detected"),
            "pending_signature": state.get("pending_signature"),
            "stable_seen_count": state.get("stable_seen_count"),
            "last_auto_sync_reason": state.get("last_auto_sync_reason"),
        }


class ButtonCardTemplateSyncStatusSensor(ButtonCardTemplateSyncSensorBase):
    """Last sync status."""

    _attr_icon = "mdi:list-status"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, "status", "Status")

    @property
    def native_value(self) -> str:
        result = self._last_result
        if not result:
            return "Never"
        if not result.get("success"):
            return "Error"
        if result.get("wrote"):
            return "Synced"
        if result.get("dry_run"):
            return "Dry run OK"
        return "OK"


class ButtonCardTemplateSyncTemplateCountSensor(ButtonCardTemplateSyncSensorBase):
    """Last merged template count."""

    _attr_icon = "mdi:format-list-numbered"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, "template_count", "Template count")

    @property
    def native_value(self) -> int | None:
        result = self._last_result
        if not result:
            return None
        value = result.get("template_count_after") or result.get("template_count")
        return int(value) if value is not None else None


class ButtonCardTemplateSyncLastSyncSensor(ButtonCardTemplateSyncSensorBase):
    """Timestamp of the last sync or dry-run."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sync"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, "last_sync", "Last sync")

    @property
    def native_value(self) -> datetime | None:
        result = self._last_result
        if not result or not result.get("completed_at"):
            return None
        return dt_util.parse_datetime(result["completed_at"])
