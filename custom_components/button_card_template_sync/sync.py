"""Sync orchestration for Button Card Template Sync."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .backup import async_create_dashboard_backup
from .const import (
    CONF_BACKUP_BEFORE_WRITE,
    CONF_BACKUP_RETENTION_COUNT,
    CONF_DRY_RUN,
    CONF_TARGET_DASHBOARD,
    CONF_TEMPLATE_FOLDER,
    DEFAULT_BACKUP_BEFORE_WRITE,
    DEFAULT_BACKUP_RETENTION_COUNT,
    DEFAULT_DRY_RUN,
)
from .errors import TemplateSyncError
from .lovelace import (
    async_load_dashboard_config,
    build_patched_dashboard_config,
    changed_top_level_keys,
    changed_top_level_keys_except,
    unchanged_top_level_keys_except,
)
from .merge import merge_template_folder


@dataclass(frozen=True)
class SyncResult:
    """Result returned by a sync operation."""

    entry_id: str
    success: bool
    dry_run: bool
    target_dashboard: str
    template_folder: str
    template_count: int = 0
    template_names: list[str] | None = None
    digest: str | None = None
    changed_keys: list[str] | None = None
    before_key_order: list[str] | None = None
    after_key_order: list[str] | None = None
    preserved_key_count: int | None = None
    preserved_keys: list[str] | None = None
    unexpected_changed_keys: list[str] | None = None
    views_unchanged: bool | None = None
    kiosk_mode_unchanged: bool | None = None
    backup_ref: str | None = None
    has_button_card_templates_after: bool | None = None
    template_count_after: int | None = None
    templates_added_count: int | None = None
    templates_removed_count: int | None = None
    templates_changed_count: int | None = None
    backup_count: int | None = None
    completed_at: str | None = None
    wrote: bool = False
    error: str | None = None


def _entry_option(entry: ConfigEntry, key: str, default: Any) -> Any:
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


async def async_sync_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    dry_run_override: bool | None = None,
    backup_override: bool | None = None,
) -> SyncResult:
    """Sync one config entry."""
    target_dashboard = _entry_option(entry, CONF_TARGET_DASHBOARD, "")
    template_folder = _entry_option(entry, CONF_TEMPLATE_FOLDER, "")
    dry_run = (
        dry_run_override
        if dry_run_override is not None
        else bool(_entry_option(entry, CONF_DRY_RUN, DEFAULT_DRY_RUN))
    )
    backup_before_write = (
        backup_override
        if backup_override is not None
        else bool(
            _entry_option(entry, CONF_BACKUP_BEFORE_WRITE, DEFAULT_BACKUP_BEFORE_WRITE)
        )
    )
    backup_retention_count = int(
        _entry_option(
            entry, CONF_BACKUP_RETENTION_COUNT, DEFAULT_BACKUP_RETENTION_COUNT
        )
    )

    try:
        merge = await hass.async_add_executor_job(
            merge_template_folder,
            template_folder,
            hass.config.config_dir,
        )
        dashboard, current_config = await async_load_dashboard_config(
            hass, target_dashboard
        )
        existing_templates = current_config.get("button_card_templates")
        if not isinstance(existing_templates, dict):
            existing_templates = {}
        patched_config = build_patched_dashboard_config(current_config, merge.templates)
        changed_keys = changed_top_level_keys(current_config, patched_config)
        unexpected_changed_keys = changed_top_level_keys_except(
            current_config,
            patched_config,
            "button_card_templates",
        )
        preserved_keys = unchanged_top_level_keys_except(
            current_config,
            patched_config,
            "button_card_templates",
        )
        views_unchanged = current_config.get("views") == patched_config.get("views")
        kiosk_mode_unchanged = current_config.get("kiosk_mode") == patched_config.get(
            "kiosk_mode"
        )
        templates_added = set(merge.templates) - set(existing_templates)
        templates_removed = set(existing_templates) - set(merge.templates)
        templates_changed = {
            name
            for name in set(merge.templates) & set(existing_templates)
            if merge.templates[name] != existing_templates[name]
        }

        if unexpected_changed_keys:
            raise TemplateSyncError(
                f"Unexpected changed top-level keys: {unexpected_changed_keys}"
            )

        backup_ref = None
        wrote = False
        if not dry_run:
            dashboard_config = getattr(dashboard, "config", {}) or {}
            dashboard_url_path = dashboard_config.get("url_path", target_dashboard)
            if backup_before_write:
                backup_ref = await async_create_dashboard_backup(
                    hass,
                    entry_id=entry.entry_id,
                    dashboard_url_path=dashboard_url_path,
                    template_folder=template_folder,
                    config=current_config,
                    retention_count=backup_retention_count,
                )
            await dashboard.async_save(patched_config)
            _dashboard_after, saved_config = await async_load_dashboard_config(
                hass, target_dashboard
            )
            post_write_changed_keys = changed_top_level_keys_except(
                current_config,
                saved_config,
                "button_card_templates",
            )
            if post_write_changed_keys:
                raise TemplateSyncError(
                    "Post-write verification failed: "
                    f"unexpected top-level keys changed: {post_write_changed_keys}"
                )
            wrote = True

        return SyncResult(
            entry_id=entry.entry_id,
            success=True,
            dry_run=dry_run,
            target_dashboard=target_dashboard,
            template_folder=template_folder,
            template_count=len(merge.templates),
            template_names=sorted(merge.templates),
            digest=merge.digest,
            changed_keys=changed_keys,
            before_key_order=list(current_config.keys()),
            after_key_order=list(patched_config.keys()),
            preserved_key_count=len(preserved_keys),
            preserved_keys=preserved_keys,
            unexpected_changed_keys=unexpected_changed_keys,
            views_unchanged=views_unchanged,
            kiosk_mode_unchanged=kiosk_mode_unchanged,
            backup_ref=backup_ref,
            has_button_card_templates_after="button_card_templates" in patched_config,
            template_count_after=len(patched_config.get("button_card_templates", {})),
            templates_added_count=len(templates_added),
            templates_removed_count=len(templates_removed),
            templates_changed_count=len(templates_changed),
            backup_count=None,
            completed_at=datetime.now(UTC).isoformat(),
            wrote=wrote,
        )
    except Exception as err:  # noqa: BLE001 - service response should contain error
        return SyncResult(
            entry_id=entry.entry_id,
            success=False,
            dry_run=dry_run,
            target_dashboard=target_dashboard,
            template_folder=template_folder,
            completed_at=datetime.now(UTC).isoformat(),
            error=str(err),
        )


def sync_result_to_dict(result: SyncResult) -> dict[str, Any]:
    """Convert a sync result to a service response dictionary."""
    return asdict(result)
