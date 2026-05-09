"""Runtime state helpers for Button Card Template Sync."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .backup import async_backup_count, async_clear_entry_backups
from .const import (
    CONF_AUTO_SYNC,
    CONF_POLL_INTERVAL_SECONDS,
    DOMAIN,
    SIGNAL_ENTRY_UPDATED,
)
from .sync import async_sync_entry, sync_result_to_dict


def entry_signal(entry_id: str) -> str:
    """Return the dispatcher signal for an entry."""
    return f"{SIGNAL_ENTRY_UPDATED}_{entry_id}"


def entry_runtime(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    """Return runtime data for a config entry."""
    return hass.data.setdefault(DOMAIN, {}).setdefault(entry_id, {})


async def async_run_entry_sync(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    dry_run_override: bool | None = None,
    backup_override: bool | None = None,
) -> dict[str, Any]:
    """Run sync, store the result for entities, and notify listeners."""
    result = await async_sync_entry(
        hass,
        entry,
        dry_run_override=dry_run_override,
        backup_override=backup_override,
    )
    result_dict = sync_result_to_dict(result)
    result_dict["backup_count"] = await async_backup_count(hass, entry.entry_id)
    entry_runtime(hass, entry.entry_id)["last_result"] = result_dict
    async_dispatcher_send(hass, entry_signal(entry.entry_id))
    return result_dict


def update_entry_option(
    hass: HomeAssistant,
    entry: ConfigEntry,
    key: str,
    value: Any,
) -> None:
    """Update one config entry option and notify entities."""
    options = {**entry.options, key: value}
    hass.config_entries.async_update_entry(entry, options=options)
    async_dispatcher_send(hass, entry_signal(entry.entry_id))
    if key in {CONF_AUTO_SYNC, CONF_POLL_INTERVAL_SECONDS}:
        from .autosync import async_update_auto_sync

        hass.async_create_task(async_update_auto_sync(hass, entry))


async def async_clear_backups_for_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Clear backups for one config entry and update runtime state."""
    removed = await async_clear_entry_backups(hass, entry.entry_id)
    runtime = entry_runtime(hass, entry.entry_id)
    last_result = runtime.get("last_result")
    if isinstance(last_result, dict):
        last_result = {**last_result, "backup_count": 0}
        runtime["last_result"] = last_result
    async_dispatcher_send(hass, entry_signal(entry.entry_id))
    return {
        "entry_id": entry.entry_id,
        "success": True,
        "removed_backups": removed,
        "backup_count": 0,
    }
