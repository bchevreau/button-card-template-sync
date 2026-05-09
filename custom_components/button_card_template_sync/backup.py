"""Backup helpers for Button Card Template Sync."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    BACKUP_INDEX_STORE_KEY,
    BACKUP_STORE_PREFIX,
    BACKUP_STORE_VERSION,
)
from .errors import TemplateSyncError


def _index_store(hass: HomeAssistant) -> Store:
    """Return the Home Assistant storage helper for the backup index."""
    return Store(hass, BACKUP_STORE_VERSION, BACKUP_INDEX_STORE_KEY)


def _backup_store(hass: HomeAssistant, backup_id: str) -> Store:
    """Return the Home Assistant storage helper for one dashboard backup."""
    return Store(hass, BACKUP_STORE_VERSION, f"{BACKUP_STORE_PREFIX}/{backup_id}")


def _safe_dashboard_name(dashboard_url_path: str) -> str:
    """Return a storage-key-safe dashboard name."""
    return "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in dashboard_url_path
    )


async def async_create_dashboard_backup(
    hass: HomeAssistant,
    *,
    entry_id: str,
    dashboard_url_path: str,
    template_folder: str,
    config: dict[str, Any],
    retention_count: int,
) -> str:
    """Create and verify a dashboard backup through Home Assistant storage."""
    now = datetime.now(UTC)
    safe_dashboard = _safe_dashboard_name(dashboard_url_path)
    backup_id = f"{safe_dashboard}_{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    backup = {
        "id": backup_id,
        "entry_id": entry_id,
        "dashboard_url_path": dashboard_url_path,
        "template_folder": template_folder,
        "created_at": now.isoformat(),
        "config": config,
    }

    backup_store = _backup_store(hass, backup_id)
    await backup_store.async_save(backup)

    saved_backup = await backup_store.async_load()
    if not isinstance(saved_backup, dict) or saved_backup.get("id") != backup_id:
        raise TemplateSyncError("Backup verification failed after saving")

    index_store = _index_store(hass)
    index_data = await index_store.async_load() or {}
    backups = index_data.get("backups", [])
    if not isinstance(backups, list):
        raise TemplateSyncError("Backup index is malformed: backups must be a list")

    backups.append(
        {
            "id": backup_id,
            "entry_id": entry_id,
            "dashboard_url_path": dashboard_url_path,
            "template_folder": template_folder,
            "created_at": now.isoformat(),
            "store_key": f"{BACKUP_STORE_PREFIX}/{backup_id}",
        }
    )

    entry_backups = [
        item
        for item in backups
        if isinstance(item, dict) and item.get("entry_id") == entry_id
    ]
    entry_removed = (
        entry_backups[:-retention_count] if len(entry_backups) > retention_count else []
    )
    removed_ids = {
        item["id"] for item in entry_removed if isinstance(item.get("id"), str)
    }
    backups = [
        item
        for item in backups
        if not (isinstance(item, dict) and item.get("id") in removed_ids)
    ]

    for item in entry_removed:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            await _backup_store(hass, item["id"]).async_remove()

    await index_store.async_save({"backups": backups})
    return f"store:{BACKUP_STORE_PREFIX}/{backup_id}"


async def async_backup_count(hass: HomeAssistant, entry_id: str) -> int:
    """Return the number of indexed backups for one entry."""
    index_data = await _index_store(hass).async_load() or {}
    backups = index_data.get("backups", [])
    if not isinstance(backups, list):
        return 0
    return sum(
        1
        for item in backups
        if isinstance(item, dict) and item.get("entry_id") == entry_id
    )


async def async_clear_entry_backups(hass: HomeAssistant, entry_id: str) -> int:
    """Clear all backups belonging to one config entry."""
    index_store = _index_store(hass)
    index_data = await index_store.async_load() or {}
    backups = index_data.get("backups", [])
    if not isinstance(backups, list):
        raise TemplateSyncError("Backup index is malformed: backups must be a list")

    removed = [
        item
        for item in backups
        if isinstance(item, dict) and item.get("entry_id") == entry_id
    ]
    kept = [
        item
        for item in backups
        if not (isinstance(item, dict) and item.get("entry_id") == entry_id)
    ]

    for item in removed:
        if isinstance(item.get("id"), str):
            await _backup_store(hass, item["id"]).async_remove()

    await index_store.async_save({"backups": kept})
    return len(removed)
