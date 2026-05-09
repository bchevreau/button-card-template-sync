"""Button Card Template Sync integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import config_validation as cv

from .autosync import async_stop_auto_sync, async_update_auto_sync
from .const import DOMAIN, PLATFORMS, SERVICE_CLEAR_BACKUPS, SERVICE_SYNC_TEMPLATES
from .naming import entry_title_from_entry
from .runtime import async_clear_backups_for_entry, async_run_entry_sync

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SYNC_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Optional("dry_run"): cv.boolean,
        vol.Optional("backup"): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration and register services."""
    hass.data.setdefault(DOMAIN, {})

    def _matching_entries(entry_id: str | None) -> list[ConfigEntry]:
        return [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry_id is None or entry.entry_id == entry_id
        ]

    async def handle_sync_templates(call: ServiceCall) -> ServiceResponse:
        entry_id = call.data.get("entry_id")
        dry_run = call.data.get("dry_run")
        backup = call.data.get("backup")

        entries = _matching_entries(entry_id)
        if entry_id is not None and not entries:
            return {
                "success": False,
                "results": [],
                "error": f"Config entry not found: {entry_id}",
            }

        results = []
        for entry in entries:
            result = await async_run_entry_sync(
                hass,
                entry,
                dry_run_override=dry_run,
                backup_override=backup,
            )
            results.append(result)

        return {
            "success": all(result["success"] for result in results),
            "results": results,
        }

    async def handle_clear_backups(call: ServiceCall) -> ServiceResponse:
        entry_id = call.data.get("entry_id")
        entries = _matching_entries(entry_id)
        if entry_id is not None and not entries:
            return {
                "success": False,
                "results": [],
                "error": f"Config entry not found: {entry_id}",
            }

        results = [
            await async_clear_backups_for_entry(hass, entry) for entry in entries
        ]

        return {
            "success": all(result["success"] for result in results),
            "results": results,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_TEMPLATES,
        handle_sync_templates,
        schema=SERVICE_SYNC_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_BACKUPS,
        handle_clear_backups,
        schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    preferred_title = entry_title_from_entry(entry)
    if preferred_title != entry.title:
        hass.config_entries.async_update_entry(entry, title=preferred_title)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "entry": entry,
        "last_result": None,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_update_auto_sync(hass, entry)
    _LOGGER.debug("Loaded Button Card Template Sync entry %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await async_stop_auto_sync(hass, entry)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False
    hass.data.setdefault(DOMAIN, {}).pop(entry.entry_id, None)
    return True
