# Button Card Template Sync

Button Card Template Sync is a Home Assistant custom integration that keeps
`custom:button-card` templates in YAML files and syncs them into a storage-mode
Lovelace dashboard.

It is intended for dashboards where the main dashboard is managed by Home
Assistant storage, but shared `button_card_templates` are easier to review,
reuse, and version as separate YAML files.

## Features

- Config flow setup from Settings > Devices & services.
- One sync entry per template folder and target storage dashboard.
- Manual sync button entity and `button_card_template_sync.sync_templates` service.
- Dry-run mode for validating the merge without writing the dashboard.
- Backup-before-write support using Home Assistant Store under
  `.storage/button_card_template_sync`.
- Backup retention and a clear-backups button/service.
- Diagnostic entities for status, template count, last sync time, and auto-sync
  state.
- Auto-sync polling with a stability debounce before writing changes.
- Guardrails that reject duplicate YAML keys, duplicate template names, missing
  template inheritance references, inheritance cycles, and unexpected dashboard
  top-level changes.

## Installation

### HACS

Until this repository is included as a default HACS repository, add it as a
custom repository:

1. In Home Assistant, open HACS > Integrations.
1. Choose Custom repositories.
1. Add `https://github.com/bchevreau/button-card-template-sync` as an Integration.
1. Install Button Card Template Sync.
1. Restart Home Assistant.

### Manual

Copy `custom_components/button_card_template_sync` into your Home Assistant
`custom_components` directory, then restart Home Assistant.

## Setup

1. Create a folder inside your Home Assistant config directory for template
   YAML files, for example `button_card_templates`.
1. Put one or more `.yaml` or `.yml` files directly inside that folder.
1. In Home Assistant, go to Settings > Devices & services > Add integration.
1. Search for Button Card Template Sync.
1. Select the template folder and the target storage-mode dashboard.

The template folder must be inside the Home Assistant config directory. Version
1 reads YAML files directly in that folder and does not scan nested folders.

Each YAML file should contain a top-level mapping of template names:

```yaml
base_card:
  show_icon: true
  show_name: true

room_light:
  template: base_card
  tap_action:
    action: toggle
```

On sync, the merged mapping is written to the target dashboard's top-level
`button_card_templates` key. Before and after real writes, every other
top-level dashboard key is verified unchanged so dashboard views, `kiosk_mode`,
themes, layout settings, and future Home Assistant keys are preserved.

## Entities

Each sync entry creates:

- Buttons: Sync, Clear backups
- Switches: Dry run, Auto-sync, Backup before write
- Numbers: Poll interval, Backup retention
- Sensors: Status, Template count, Last sync

## Services

### `button_card_template_sync.sync_templates`

Runs one or all configured sync entries and returns a response.

Optional fields:

- `entry_id`: limit the run to one config entry
- `dry_run`: override the entry dry-run setting
- `backup`: override the entry backup setting

### `button_card_template_sync.clear_backups`

Clears stored dashboard backups for one entry or all entries.

Optional fields:

- `entry_id`: limit cleanup to one config entry

## Backups

Backups are created only for real writes when backup-before-write is enabled.
They are stored with Home Assistant's storage helper under
`.storage/button_card_template_sync` and indexed per config entry. The backup
retention number controls how many backups are kept for each entry.

## HACS Readiness

This repository follows the HACS custom integration layout:

- `custom_components/button_card_template_sync`
- root `hacs.json`
- root `README.md`
- integration `manifest.json` with domain, version, documentation,
  issue tracker, and code owners

Before requesting inclusion in default HACS, create a GitHub release and submit
brand assets in `custom_components/button_card_template_sync/brand`.
