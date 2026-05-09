"""Errors for Button Card Template Sync."""

from __future__ import annotations


class TemplateSyncError(Exception):
    """Base error for template sync operations."""


class DuplicateKeyError(TemplateSyncError):
    """Raised when a YAML mapping contains duplicate keys."""
