"""Home Assistant Lovelace dashboard adapter."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

from .errors import TemplateSyncError


@dataclass(frozen=True)
class DashboardRef:
    """Resolved Lovelace dashboard reference."""

    key: str | None
    dashboard_id: str | None
    url_path: str
    title: str
    mode: str


def _lovelace_constants() -> tuple[str, str]:
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
    except ImportError as err:
        raise TemplateSyncError("Lovelace constants are unavailable") from err
    return LOVELACE_DATA, MODE_STORAGE


def list_storage_dashboards(hass: HomeAssistant) -> list[DashboardRef]:
    """List loaded storage-mode dashboards."""
    lovelace_data_key, mode_storage = _lovelace_constants()
    lovelace_data = hass.data.get(lovelace_data_key)
    if lovelace_data is None or not hasattr(lovelace_data, "dashboards"):
        return []

    dashboards: list[DashboardRef] = []
    for key, dashboard in lovelace_data.dashboards.items():
        config = getattr(dashboard, "config", None) or {}
        mode = getattr(dashboard, "mode", None)
        if mode != mode_storage or not config:
            continue
        url_path = config.get("url_path") or key
        if not isinstance(url_path, str):
            continue
        dashboards.append(
            DashboardRef(
                key=key,
                dashboard_id=config.get("id"),
                url_path=url_path,
                title=config.get("title", url_path),
                mode=mode,
            )
        )
    return sorted(dashboards, key=lambda item: item.url_path)


def resolve_dashboard(hass: HomeAssistant, dashboard_lookup: str):
    """Resolve a loaded storage-mode dashboard by URL path, ID, or title."""
    lovelace_data_key, mode_storage = _lovelace_constants()
    lovelace_data = hass.data.get(lovelace_data_key)
    if lovelace_data is None or not hasattr(lovelace_data, "dashboards"):
        raise TemplateSyncError("Lovelace dashboard data is not loaded")

    matches = []
    for key, dashboard in lovelace_data.dashboards.items():
        config = getattr(dashboard, "config", None) or {}
        lookup_values = {
            value
            for value in (
                key,
                config.get("id"),
                config.get("url_path"),
                config.get("title"),
            )
            if isinstance(value, str)
        }
        if dashboard_lookup in lookup_values:
            matches.append(dashboard)

    if not matches:
        raise TemplateSyncError(f"Target dashboard not found: {dashboard_lookup}")
    if len(matches) > 1:
        raise TemplateSyncError(
            f"Target dashboard lookup is ambiguous: {dashboard_lookup}"
        )

    dashboard = matches[0]
    if getattr(dashboard, "mode", None) != mode_storage:
        raise TemplateSyncError(
            f"Target dashboard is not storage mode: {dashboard_lookup}"
        )
    if not hasattr(dashboard, "async_load") or not hasattr(dashboard, "async_save"):
        raise TemplateSyncError("Target dashboard does not expose load/save methods")
    return dashboard


async def async_load_dashboard_config(
    hass: HomeAssistant, dashboard_lookup: str
) -> tuple[Any, dict[str, Any]]:
    """Load a storage dashboard config through Home Assistant runtime objects."""
    dashboard = resolve_dashboard(hass, dashboard_lookup)
    config = await dashboard.async_load(True)
    if not isinstance(config, dict):
        raise TemplateSyncError(
            f"Dashboard config must be a mapping: {dashboard_lookup}"
        )
    return dashboard, config


def build_patched_dashboard_config(
    current_config: dict[str, Any],
    templates: dict[str, Any],
) -> dict[str, Any]:
    """Return a patched dashboard config with templates appended as final key."""
    patched_config = copy.deepcopy(current_config)
    if "button_card_templates" in patched_config:
        del patched_config["button_card_templates"]
    patched_config["button_card_templates"] = templates
    return patched_config


def changed_top_level_keys(
    before_config: dict[str, Any],
    after_config: dict[str, Any],
) -> list[str]:
    """Return changed top-level keys between two dashboard configs."""
    sentinel = object()
    return [
        key
        for key in sorted(set(before_config) | set(after_config))
        if before_config.get(key, sentinel) != after_config.get(key, sentinel)
    ]
