<p align="center">
  <img src="custom_components/button_card_template_sync/brand/logo@2x.png" alt="Button Card Template Sync logo" width="300">
</p>

<p align="center">
  <a href="https://github.com/bchevreau/button-card-template-sync/releases"><img src="https://img.shields.io/github/v/release/bchevreau/button-card-template-sync?include_prereleases&label=version" alt="Latest release"></a>
  <a href="https://github.com/bchevreau/button-card-template-sync/blob/main/LICENSE"><img src="https://img.shields.io/github/license/bchevreau/button-card-template-sync" alt="License"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2026.3.2%2B-18BCF2" alt="Home Assistant 2026.3.2 or newer">
  <img src="https://img.shields.io/badge/HACS-Custom-41BDF5" alt="HACS custom repository">
</p>

<!--
Future badge ideas, useful after the repo is public and beta releases/actions are active:

[![Validate](https://github.com/bchevreau/button-card-template-sync/actions/workflows/validate.yml/badge.svg)](https://github.com/bchevreau/button-card-template-sync/actions/workflows/validate.yml)
[![Tests](https://github.com/bchevreau/button-card-template-sync/actions/workflows/tests.yml/badge.svg)](https://github.com/bchevreau/button-card-template-sync/actions/workflows/tests.yml)
[![GitHub downloads](https://img.shields.io/github/downloads/bchevreau/button-card-template-sync/total?label=downloads)](https://github.com/bchevreau/button-card-template-sync/releases)
[![GitHub stars](https://img.shields.io/github/stars/bchevreau/button-card-template-sync?style=flat&label=stars)](https://github.com/bchevreau/button-card-template-sync/stargazers)
-->

# Button Card Template Sync

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bchevreau&repository=button-card-template-sync&category=integration)

Keep `custom:button-card` templates in YAML, while keeping your Lovelace
dashboards editable in the Home Assistant UI.

Button Card Template Sync reads a folder of separate, individual button-card template files, merges
them deterministically, validates inheritance, and writes the result to the
top-level `button_card_templates` key of a storage-mode / UI dashboard.

It is built for people who like to edit their dashboards in the UI, but prefer their shared
button-card templates neatly organised into files where they can be reviewed, copied, backed up,
and versioned.

## Highlights

- UI setup through Settings > Devices & services with a single entry per dashboard and template folder merge.
- One sync entry per template folder with its target UI dashboard.
- Manual sync button and `button_card_template_sync.sync_templates` service.
- Dry-run "safe" mode by default, so validation can run without writing anything.
- Backup-before-write system using Home Assistant Store under
  `.storage/button_card_template_sync`.
- Clear-backups button/service and bounded backup retention.
- Diagnostic sensors for status, template count, last sync time, and auto-sync
  state.
- Optional auto-sync schedule with polling and stability debounce: track changes in your templates folder, BTCS handles the rest!
- Guardrails for duplicate YAML keys, duplicate template names, missing
  inheritance references, inheritance cycles, and unexpected dashboard changes.

## Safety Model

This integration is intentionally conservative because it writes to a dashboard.

On every sync, it:

1. Reads YAML files directly inside the configured template folder.
1. Validates the merged template map and inheritance graph.
1. Loads the target storage dashboard through Home Assistant runtime objects.
1. Builds a patched dashboard config in memory.
1. Verifies that only the top-level `button_card_templates` key would change.
1. Creates and verifies a backup before real writes, unless backup is disabled.
1. Saves through Home Assistant's dashboard storage object.
1. Reloads the saved dashboard and verifies every other top-level key is still
   unchanged.

That last check covers `views`, `kiosk_mode`, themes, layout settings, and
future Home Assistant dashboard keys.

## Installation

### HACS

This repository is still under review from HACS. Once approved, add it
as a custom repository:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bchevreau&repository=https%3A%2F%2Fgithub.com%2Fbchevreau%2Fbutton-card-template-sync&category=integration)

Manual HACS steps:

1. Open HACS > Integrations.
1. Choose Custom repositories.
1. Add `https://github.com/bchevreau/button-card-template-sync`.
1. Select category `Integration`.
1. Download Button Card Template Sync.
1. Restart Home Assistant.

### Manual

Copy this folder:

```text
custom_components/button_card_template_sync
```

to:

```text
<home_assistant_config>/custom_components/button_card_template_sync
```

Then restart Home Assistant.

## Requirements

- Home Assistant 2026.3.2 or newer.
- HACS 2.0.5 or newer, if installing through HACS.
- A storage-mode (UI) Lovelace dashboard.
- [`custom:button-card`](https://github.com/custom-cards/button-card) installed
  separately if your dashboard uses button-card cards.

This integration does not install button-card itself.

## Setup

1. Create or locate an existing button-card templates folder inside your Home Assistant config directory, for
   example `button_card_templates`.
1. Put one or more `.yaml` or `.yml` template files directly inside that folder.
1. [![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=button_card_template_sync) or go to Settings > Devices & services > Add integration.
1. Search for Button Card Template Sync or click 
1. Pick the template folder and target storage-mode dashboard.
1. Keep Dry run enabled for the first sync.

Version 1 reads YAML files directly in the configured folder. It does not scan
nested subfolders.

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

On sync, the merged mapping is written to:

```yaml
button_card_templates:
  ...
```

## Entities

Each sync entry comes fully-packed with Home Assistant management entities:

- Buttons: Sync (launch a manual sync), Clear backups (delete all stored backups)
- Switches: Dry run (turn on safe mode), Auto-sync (track changes to the folder automatically), Backup before write (copy your dashboard each time before running the sync)
- Numbers: Poll interval (adjust the frequency of the changes' tracking system), Backup retention (how many total backup copies are saved)
- Sensors: **Status** of the last sync, **Template count** last merged, **Last sync** timestamp

## Services

### `button_card_template_sync.sync_templates`

Runs one or all configured sync entries and returns a response.

Optional fields:

- `entry_id`: limit the run to one config entry; leave out to process all configured dashboards
- `dry_run`: one-call override for the entry dry-run setting; options: `true` or `false`; leave out for current setting.
- `backup`: override the entry backup setting; options: `true` or `false`; leave out to use the entry setting.

### `button_card_template_sync.clear_backups`

Clears stored dashboard backups for one entry or all entries.

Optional fields:

- `entry_id`: limit cleanup to one config entry; leave out to clear backups for all configured entries.

## Backups

Backups are created only for real writes when backup-before-write is enabled.
They are stored with Home Assistant's storage helper under
`.storage/button_card_template_sync` and indexed per config entry.

The backup retention number controls how many backups are kept for each entry.
Backups are not stored inside `custom_components`, so HACS updates will not
remove them.

## Auto-Sync

Auto-sync is disabled by default.

When enabled, the integration polls the configured template folder, waits until
a changed folder signature is stable across consecutive polls, and then runs
the same sync path as a manual sync. Dry-run, backup, validation, and post-write
verification rules still apply.

## Beta Status

This project is still in Beta. Please be gentle and let us know if you find bugs or issues!

Recommended safe first workflow:

- Start with a test dashboard (Optionally use the raw configuration editor to copy-paste your entire content into a duplicate).
- Keep Dry run enabled until diagnostics look right and run a few things. Status should change to "Dry run OK" if everything went well.
- Keep Backup before write enabled before you turn Dry run off.
- Use Auto-sync only after a successful manual sync is proven.
