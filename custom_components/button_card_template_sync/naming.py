"""Naming helpers for Button Card Template Sync."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .const import CONF_TARGET_DASHBOARD, NAME

BCTS_SUFFIX = "BCTS"


def dashboard_to_title(dashboard: str) -> str:
    """Convert a dashboard id/url path into a human-readable BCTS title."""
    words = dashboard.replace("_", "-").split("-")
    title = " ".join(word.capitalize() for word in words if word)
    return f"{title or 'Dashboard'} {BCTS_SUFFIX}"


def entry_title_from_input(name: str | None, target_dashboard: str) -> str:
    """Return a config entry title, deriving it from dashboard when defaulted."""
    cleaned = (name or "").strip()
    if not cleaned or cleaned == NAME:
        return dashboard_to_title(target_dashboard)
    return cleaned


def entry_title_from_entry(entry: ConfigEntry) -> str:
    """Return the preferred display title for an existing config entry."""
    if entry.title != NAME:
        return entry.title
    target_dashboard = entry.options.get(CONF_TARGET_DASHBOARD) or entry.data.get(
        CONF_TARGET_DASHBOARD
    )
    if isinstance(target_dashboard, str):
        return dashboard_to_title(target_dashboard)
    return NAME
