"""Adds config flow for planet_phase."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries

from .api import PlanetPhaseApiClient
from .const import DEFAULT_NAME
from .const import DOMAIN
from .flow_helpers import ConfigBuilder
from .flow_helpers import SchemaBuilder


class PlanetPhaseFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for planet_phase."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self.selected_planets: list[str] = []
        self._user_input_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            # Reinitialisiere PLANET_MAP auf Standard-Werte
            # PlanetPhaseApiClient.reinitialize()
            self.selected_planets = user_input["active_planets"]
            return await self.async_step_configure_sensors()

        # Reinitialisiere PLANET_MAP auf Standard-Werte
        PlanetPhaseApiClient.reinitialize()
        return self.async_show_form(
            step_id="user",
            data_schema=SchemaBuilder.get_planet_selection_schema(),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration from the UI."""
        # Setze die aktuelle Auswahl als Default im Schema
        if user_input is not None:
            # Reinitialisiere PLANET_MAP auf Standard-Werte
            # PlanetPhaseApiClient.reinitialize()
            self.selected_planets = user_input["active_planets"]
            return await self.async_step_configure_sensors()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=SchemaBuilder.get_planet_selection_schema(),
        )

    async def async_step_configure_sensors(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Configure MainSensor and StateSensors for each selected planet."""
        if user_input is not None:
            final_config = ConfigBuilder.build_final_config(self.selected_planets, user_input)

            if self.source == config_entries.SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data=final_config)

            return self.async_create_entry(title=DEFAULT_NAME, data=final_config)

        data_schema = SchemaBuilder.build_sensor_schema(self.selected_planets)
        return self.async_show_form(
            step_id="configure_sensors",
            data_schema=data_schema,
            description_placeholders={"active_planets": ", ".join([p.capitalize() for p in self.selected_planets])},
        )
