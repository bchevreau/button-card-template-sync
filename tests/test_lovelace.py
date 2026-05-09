"""Tests for Lovelace dashboard patch helpers."""

from __future__ import annotations

from button_card_template_sync.lovelace import (
    build_patched_dashboard_config,
    changed_top_level_keys,
    changed_top_level_keys_except,
    unchanged_top_level_keys_except,
)


def test_build_patched_dashboard_config_only_replaces_templates() -> None:
    """Patch only the button_card_templates top-level key."""
    current = {
        "kiosk_mode": {"hide_header": True},
        "views": [{"title": "Home"}],
        "theme": "tablet",
        "button_card_templates": {"old": {"show_icon": False}},
    }
    templates = {"base": {"show_icon": True}}

    patched = build_patched_dashboard_config(current, templates)

    assert patched == {
        "kiosk_mode": {"hide_header": True},
        "views": [{"title": "Home"}],
        "theme": "tablet",
        "button_card_templates": {"base": {"show_icon": True}},
    }
    assert current["button_card_templates"] == {"old": {"show_icon": False}}
    assert list(patched)[-1] == "button_card_templates"
    assert changed_top_level_keys(current, patched) == ["button_card_templates"]


def test_build_patched_dashboard_config_deep_copies_dashboard() -> None:
    """Mutating the patched config must not mutate the original dashboard."""
    current = {"views": [{"title": "Home"}]}
    patched = build_patched_dashboard_config(current, {"base": {}})

    patched["views"][0]["title"] = "Changed"

    assert current["views"] == [{"title": "Home"}]


def test_changed_top_level_keys_reports_added_removed_and_changed() -> None:
    """Report changed top-level keys deterministically."""
    before = {"b": 1, "a": 1, "removed": True}
    after = {"b": 2, "a": 1, "added": True}

    assert changed_top_level_keys(before, after) == ["added", "b", "removed"]


def test_top_level_key_helpers_ignore_allowed_template_key() -> None:
    """Detect only unexpected top-level changes outside button-card templates."""
    before = {
        "views": [{"title": "Home"}],
        "kiosk_mode": {"hide_header": True},
        "theme": "tablet",
        "button_card_templates": {"old": {}},
    }
    after = {
        "views": [{"title": "Home"}],
        "kiosk_mode": {"hide_header": True},
        "theme": "tablet",
        "button_card_templates": {"new": {}},
    }

    assert (
        changed_top_level_keys_except(
            before,
            after,
            "button_card_templates",
        )
        == []
    )
    assert unchanged_top_level_keys_except(
        before,
        after,
        "button_card_templates",
    ) == ["kiosk_mode", "theme", "views"]
