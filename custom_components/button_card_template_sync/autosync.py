"""Auto-sync polling tasks for Button Card Template Sync."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_AUTO_SYNC,
    CONF_POLL_INTERVAL_SECONDS,
    CONF_TEMPLATE_FOLDER,
    DEFAULT_AUTO_SYNC,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from .folder_signature import FolderSignature, compute_folder_signature
from .runtime import async_run_entry_sync, entry_runtime, entry_signal

_LOGGER = logging.getLogger(__name__)

AUTO_SYNC_TASK_KEY = "auto_sync_task"
AUTO_SYNC_STOP_KEY = "auto_sync_stop"
AUTO_SYNC_STATE_KEY = "auto_sync_state"
STABLE_POLLS_REQUIRED = 2


def _entry_option(entry: ConfigEntry, key: str, default: Any) -> Any:
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


def _auto_state(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    runtime = entry_runtime(hass, entry.entry_id)
    return runtime.setdefault(
        AUTO_SYNC_STATE_KEY,
        {
            "enabled": False,
            "last_folder_signature": None,
            "last_folder_file_count": None,
            "pending_change_detected": False,
            "pending_signature": None,
            "stable_seen_count": 0,
            "last_auto_sync_reason": None,
        },
    )


def _update_auto_state(
    hass: HomeAssistant,
    entry: ConfigEntry,
    **updates: Any,
) -> None:
    _auto_state(hass, entry).update(updates)
    async_dispatcher_send(hass, entry_signal(entry.entry_id))


async def _async_signature(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> FolderSignature:
    template_folder = _entry_option(entry, CONF_TEMPLATE_FOLDER, "")
    return await hass.async_add_executor_job(
        compute_folder_signature,
        template_folder,
        hass.config.config_dir,
    )


async def _auto_sync_loop(
    hass: HomeAssistant,
    entry: ConfigEntry,
    stop_event: asyncio.Event,
) -> None:
    """Poll one entry for stable template folder changes."""
    try:
        signature = await _async_signature(hass, entry)
        _update_auto_state(
            hass,
            entry,
            enabled=True,
            last_folder_signature=signature.digest,
            last_folder_file_count=signature.file_count,
            pending_change_detected=False,
            pending_signature=None,
            stable_seen_count=0,
            last_auto_sync_reason="initialized",
        )
    except Exception as err:  # noqa: BLE001
        _update_auto_state(
            hass,
            entry,
            enabled=True,
            last_auto_sync_reason=f"initial signature error: {err}",
        )

    while not stop_event.is_set():
        interval = int(
            _entry_option(
                entry, CONF_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS
            )
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(interval, 1))
            break
        except TimeoutError:
            pass

        state = _auto_state(hass, entry)
        try:
            signature = await _async_signature(hass, entry)
        except Exception as err:  # noqa: BLE001
            _update_auto_state(
                hass,
                entry,
                last_auto_sync_reason=f"signature error: {err}",
            )
            continue

        last_signature = state.get("last_folder_signature")
        pending_signature = state.get("pending_signature")

        if signature.digest == last_signature and not pending_signature:
            _update_auto_state(
                hass,
                entry,
                last_folder_file_count=signature.file_count,
                pending_change_detected=False,
                stable_seen_count=0,
                last_auto_sync_reason="no change",
            )
            continue

        if signature.digest != pending_signature:
            _update_auto_state(
                hass,
                entry,
                last_folder_file_count=signature.file_count,
                pending_change_detected=True,
                pending_signature=signature.digest,
                stable_seen_count=1,
                last_auto_sync_reason="change detected",
            )
            continue

        stable_seen_count = int(state.get("stable_seen_count") or 0) + 1
        if stable_seen_count < STABLE_POLLS_REQUIRED:
            _update_auto_state(
                hass,
                entry,
                stable_seen_count=stable_seen_count,
                last_auto_sync_reason="waiting for stable change",
            )
            continue

        _update_auto_state(
            hass,
            entry,
            stable_seen_count=stable_seen_count,
            last_auto_sync_reason="stable change, syncing",
        )
        result = await async_run_entry_sync(hass, entry)
        if result.get("success"):
            _update_auto_state(
                hass,
                entry,
                last_folder_signature=signature.digest,
                last_folder_file_count=signature.file_count,
                pending_change_detected=False,
                pending_signature=None,
                stable_seen_count=0,
                last_auto_sync_reason="synced",
            )
        else:
            _update_auto_state(
                hass,
                entry,
                stable_seen_count=0,
                last_auto_sync_reason="sync failed",
            )


async def async_update_auto_sync(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Start, stop, or restart auto-sync for an entry based on current options."""
    await async_stop_auto_sync(hass, entry)
    enabled = bool(_entry_option(entry, CONF_AUTO_SYNC, DEFAULT_AUTO_SYNC))
    if not enabled:
        _update_auto_state(
            hass,
            entry,
            enabled=False,
            pending_change_detected=False,
            pending_signature=None,
            stable_seen_count=0,
            last_auto_sync_reason="disabled",
        )
        return

    stop_event = asyncio.Event()
    task = hass.async_create_task(_auto_sync_loop(hass, entry, stop_event))
    runtime = entry_runtime(hass, entry.entry_id)
    runtime[AUTO_SYNC_STOP_KEY] = stop_event
    runtime[AUTO_SYNC_TASK_KEY] = task
    _LOGGER.debug("Started auto-sync task for %s", entry.entry_id)


async def async_stop_auto_sync(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Stop the auto-sync task for an entry if it exists."""
    runtime = entry_runtime(hass, entry.entry_id)
    stop_event = runtime.pop(AUTO_SYNC_STOP_KEY, None)
    task = runtime.pop(AUTO_SYNC_TASK_KEY, None)
    if isinstance(stop_event, asyncio.Event):
        stop_event.set()
    if isinstance(task, asyncio.Task):
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    state = runtime.get(AUTO_SYNC_STATE_KEY)
    if isinstance(state, dict):
        state["enabled"] = False
