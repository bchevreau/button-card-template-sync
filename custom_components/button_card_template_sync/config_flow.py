"""Config flow for Button Card Template Sync."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_AUTO_SYNC,
    CONF_BACKUP_BEFORE_WRITE,
    CONF_BACKUP_RETENTION_COUNT,
    CONF_DRY_RUN,
    CONF_POLL_INTERVAL_SECONDS,
    CONF_TARGET_DASHBOARD,
    CONF_TEMPLATE_FOLDER,
    DEFAULT_AUTO_SYNC,
    DEFAULT_BACKUP_BEFORE_WRITE,
    DEFAULT_BACKUP_RETENTION_COUNT,
    DEFAULT_DRY_RUN,
    DEFAULT_NAME,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_TARGET_DASHBOARD,
    DEFAULT_TEMPLATE_FOLDER,
    DOMAIN,
)
from .errors import TemplateSyncError
from .lovelace import list_storage_dashboards
from .merge import resolve_config_path
from .naming import entry_title_from_input


def _dashboard_options(hass) -> list[str]:
    dashboards = list_storage_dashboards(hass)
    return [dashboard.url_path for dashboard in dashboards]


def _schema(hass, defaults: dict[str, Any]) -> vol.Schema:
    dashboard_options = _dashboard_options(hass)
    target_default = defaults.get(CONF_TARGET_DASHBOARD, DEFAULT_TARGET_DASHBOARD)
    if not target_default and dashboard_options:
        target_default = dashboard_options[0]
    target_selector = (
        SelectSelector(
            SelectSelectorConfig(
                options=dashboard_options,
                mode=SelectSelectorMode.DROPDOWN,
                custom_value=True,
            )
        )
        if dashboard_options
        else TextSelector()
    )

    return vol.Schema(
        {
            vol.Optional(
                "name", default=defaults.get("name", DEFAULT_NAME)
            ): TextSelector(),
            vol.Required(
                CONF_TEMPLATE_FOLDER,
                default=defaults.get(CONF_TEMPLATE_FOLDER, DEFAULT_TEMPLATE_FOLDER),
            ): TextSelector(),
            vol.Required(
                CONF_TARGET_DASHBOARD,
                default=target_default,
            ): target_selector,
            vol.Required(
                CONF_DRY_RUN,
                default=defaults.get(CONF_DRY_RUN, DEFAULT_DRY_RUN),
            ): BooleanSelector(),
            vol.Required(
                CONF_BACKUP_BEFORE_WRITE,
                default=defaults.get(
                    CONF_BACKUP_BEFORE_WRITE, DEFAULT_BACKUP_BEFORE_WRITE
                ),
            ): BooleanSelector(),
            vol.Required(
                CONF_BACKUP_RETENTION_COUNT,
                default=defaults.get(
                    CONF_BACKUP_RETENTION_COUNT, DEFAULT_BACKUP_RETENTION_COUNT
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=250,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_AUTO_SYNC,
                default=defaults.get(CONF_AUTO_SYNC, DEFAULT_AUTO_SYNC),
            ): BooleanSelector(),
            vol.Required(
                CONF_POLL_INTERVAL_SECONDS,
                default=defaults.get(
                    CONF_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=3600,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _validate_input(hass, user_input: dict[str, Any]) -> None:
    if not user_input.get(CONF_TEMPLATE_FOLDER):
        raise TemplateSyncError("folder_not_found")
    if not user_input.get(CONF_TARGET_DASHBOARD):
        raise TemplateSyncError("dashboard_not_found")
    resolve_config_path(user_input[CONF_TEMPLATE_FOLDER], hass.config.config_dir)
    dashboards = _dashboard_options(hass)
    if dashboards and user_input[CONF_TARGET_DASHBOARD] not in dashboards:
        raise TemplateSyncError("dashboard_not_found")


class ButtonCardTemplateSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                _validate_input(self.hass, user_input)
            except TemplateSyncError as err:
                errors["base"] = str(err)
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                name = user_input.pop("name", DEFAULT_NAME)
                title = entry_title_from_input(name, user_input[CONF_TARGET_DASHBOARD])
                await self.async_set_unique_id(
                    f"{user_input[CONF_TARGET_DASHBOARD]}::{user_input[CONF_TEMPLATE_FOLDER]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass, {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Create the options flow."""
        return ButtonCardTemplateSyncOptionsFlow()


class ButtonCardTemplateSyncOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                _validate_input(self.hass, user_input)
            except TemplateSyncError as err:
                errors["base"] = str(err)
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                name = user_input.pop("name", None)
                if name:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=entry_title_from_input(
                            name, user_input[CONF_TARGET_DASHBOARD]
                        ),
                    )
                return self.async_create_entry(data=user_input)

        defaults = {
            **self.config_entry.data,
            **self.config_entry.options,
            "name": self.config_entry.title,
        }
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, defaults),
            errors=errors,
        )
