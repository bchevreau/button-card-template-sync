"""Constants for Button Card Template Sync."""

from __future__ import annotations

DOMAIN = "button_card_template_sync"
NAME = "Button Card Template Sync"
PLATFORMS = ["button", "number", "sensor", "switch"]

CONF_TEMPLATE_FOLDER = "template_folder"
CONF_TARGET_DASHBOARD = "target_dashboard"
CONF_DRY_RUN = "dry_run"
CONF_AUTO_SYNC = "auto_sync"
CONF_BACKUP_BEFORE_WRITE = "backup_before_write"
CONF_BACKUP_RETENTION_COUNT = "backup_retention_count"
CONF_POLL_INTERVAL_SECONDS = "poll_interval_seconds"

DEFAULT_NAME = ""
DEFAULT_TEMPLATE_FOLDER = ""
DEFAULT_TARGET_DASHBOARD = ""
DEFAULT_DRY_RUN = True
DEFAULT_AUTO_SYNC = False
DEFAULT_BACKUP_BEFORE_WRITE = True
DEFAULT_BACKUP_RETENTION_COUNT = 20
DEFAULT_POLL_INTERVAL_SECONDS = 30

SERVICE_SYNC_TEMPLATES = "sync_templates"
SERVICE_CLEAR_BACKUPS = "clear_backups"
SIGNAL_ENTRY_UPDATED = f"{DOMAIN}_entry_updated"

BACKUP_STORE_VERSION = 1
BACKUP_STORE_PREFIX = f"{DOMAIN}/backups"
BACKUP_INDEX_STORE_KEY = f"{DOMAIN}/backup_index"
