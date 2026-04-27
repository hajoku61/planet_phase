"""Helper functions for config flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.helpers.selector import NumberSelector
from homeassistant.helpers.selector import NumberSelectorConfig
from homeassistant.helpers.selector import NumberSelectorMode
from homeassistant.helpers.selector import SelectSelector
from homeassistant.helpers.selector import SelectSelectorConfig
from homeassistant.helpers.selector import SelectSelectorMode

from .api import PLANET_MAP_DEFAULT
from .api import PlanetPhaseApiClient
from .const import UPDATE_INTERVAL
from .const import PlanetConfigKey


class SchemaBuilder:
    """Build schemas for config flow."""

    @staticmethod
    def get_planet_selection_schema() -> vol.Schema:
        """Get planet selection schema."""
        current_config = PlanetPhaseApiClient.get_config()
        default_selection = [slug for slug, data in current_config.items() if data.get(PlanetConfigKey.ACTIVE)]

        return vol.Schema(
            {
                vol.Required("active_planets", default=default_selection): SelectSelector(
                    SelectSelectorConfig(
                        options=list(PLANET_MAP_DEFAULT.keys()),
                        multiple=True,
                        translation_key="active_planets",
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=False,
                    )
                )
            }
        )

    @staticmethod
    def build_sensor_schema(selected_planets: list[str]) -> vol.Schema:
        """Build sensor configuration schema."""
        schema_dict: dict[Any, Any] = {}
        # Einmalig laden statt in der Schleife
        current_config = PlanetPhaseApiClient.get_config()

        for planet_name in selected_planets:
            planet_config = current_config.get(planet_name, {})
            default_sensors = ConfigBuilder.get_default_sensors(planet_config)

            # 1. Sensor-Auswahl pro Planet
            schema_dict[vol.Optional(f"{planet_name}_sensors", default=default_sensors)] = SelectSelector(
                SelectSelectorConfig(
                    options=["main", "state"],
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                    sort=False,
                    translation_key="planet_sensors",  # Dies ist der Anker für das JSON
                )
            )
            # 2. Update Intervall hinzufügen (z.B. 1 bis 3600 Sekunden)
            schema_dict[
                vol.Optional(
                    f"{planet_name}_update_interval",
                    default=planet_config.get(PlanetConfigKey.UPDATE_INTERVAL, UPDATE_INTERVAL),
                )
            ] = NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=3600,
                    unit_of_measurement="seconds",
                    mode=NumberSelectorMode.BOX,
                    translation_key="planet_update_interval",  # Dies ist der Anker für das JSON
                )
            )

        return vol.Schema(schema_dict)


class ConfigBuilder:
    """Build configuration for config flow."""

    @staticmethod
    def get_default_sensors(planet_config: dict) -> list[str]:
        """Get default sensors for a planet."""
        default_sensors = []
        if planet_config.get(PlanetConfigKey.MAIN_SENSOR, False):
            default_sensors.append("main")
        if planet_config.get(PlanetConfigKey.STATE_SENSORS, False):
            default_sensors.append("state")
        return default_sensors

    @staticmethod
    def build_final_config(selected_planets: list[str], user_input: dict[str, Any]) -> dict:
        """Build final configuration."""
        final_config = {}

        # Active planets with their sensor settings
        for planet_name in selected_planets:
            selected_sensors = user_input.get(f"{planet_name}_sensors", [])
            selected_update_interval = user_input.get(f"{planet_name}_update_interval", UPDATE_INTERVAL)
            final_config[planet_name] = {
                PlanetConfigKey.ACTIVE: True,
                PlanetConfigKey.MAIN_SENSOR: "main" in selected_sensors,
                PlanetConfigKey.STATE_SENSORS: "state" in selected_sensors,
                PlanetConfigKey.UPDATE_INTERVAL: selected_update_interval,
            }

        # Inactive planets
        """
        for planet_name in PLANET_MAP_DEFAULT:
            if planet_name not in selected_planets:
                final_config[planet_name] = {
                    PlanetConfigKey.ACTIVE: False,
                    PlanetConfigKey.MAIN_SENSOR: False,
                    PlanetConfigKey.STATE_SENSORS: False,
                    PlanetConfigKey.UPDATE_INTERVAL: UPDATE_INTERVAL,
                }
        """
        return final_config
