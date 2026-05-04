"""Sensor platform for sun_phase."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import DEGREE
from homeassistant.const import EntityCategory

from .api import PlanetPhaseApiClient
from .api import moon_phases
from .api import sun_phases
from .const import LOGGER
from .const import PlanetStateKey
from .entity import PlanetPhaseEntity

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PlanetPhaseDataUpdateCoordinator
    from .data import PlanetPhaseConfigEntry


ENTITY_DESCRIPTIONS_PLANET_PHASE = (
    SensorEntityDescription(
        key=PlanetStateKey.MAIN_STATE,
        name=PlanetStateKey.MAIN_STATE,
    ),
)

ENTITY_DESCRIPTIONS_PLANET_PHASE_SENSORS = (
    SensorEntityDescription(
        key=PlanetStateKey.TODAY_RISING,
        name=PlanetStateKey.TODAY_RISING,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.TODAY_SETTING,
        name=PlanetStateKey.TODAY_SETTING,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.NEXT_RISING,
        name=PlanetStateKey.NEXT_RISING,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.NEXT_SETTING,
        name=PlanetStateKey.NEXT_SETTING,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.PREVIOUS_RISING,
        name=PlanetStateKey.PREVIOUS_RISING,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.PREVIOUS_SETTING,
        name=PlanetStateKey.PREVIOUS_SETTING,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.NEXT_TRANSIT,
        name=PlanetStateKey.NEXT_TRANSIT,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.TODAY_ABOVE_HORIZON_TIME,
        name=PlanetStateKey.TODAY_ABOVE_HORIZON_TIME,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.ALTITUDE,
        name=PlanetStateKey.ALTITUDE,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        native_unit_of_measurement=DEGREE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.AZIMUTH,
        name=PlanetStateKey.AZIMUTH,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        native_unit_of_measurement=DEGREE,
        suggested_display_precision=2,
    ),
)

ENTITY_DESCRIPTIONS_PLANET_PHASE_SUN_SENSORS = (
    SensorEntityDescription(
        key=PlanetStateKey.NEXT_VERNAL_EQUINOX,
        name=PlanetStateKey.NEXT_VERNAL_EQUINOX,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.NEXT_SUMMER_SOLSTICE,
        name=PlanetStateKey.NEXT_SUMMER_SOLSTICE,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.NEXT_AUTUMNAL_EQUINOX,
        name=PlanetStateKey.NEXT_AUTUMNAL_EQUINOX,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.NEXT_WINTER_SOLSTICE,
        name=PlanetStateKey.NEXT_WINTER_SOLSTICE,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.PHASE,
        name=PlanetStateKey.PHASE,
        device_class=SensorDeviceClass.ENUM,
        options=[phase["name"] for phase in sun_phases.values()],
    ),
)

ENTITY_DESCRIPTIONS_PLANET_PHASE_MOON_SENSORS = (
    SensorEntityDescription(
        key=PlanetStateKey.MOON_NEXT_NEWMOON,
        name=PlanetStateKey.MOON_NEXT_NEWMOON,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.MOON_NEXT_FULLMOON,
        name=PlanetStateKey.MOON_NEXT_FULLMOON,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=PlanetStateKey.PHASE,
        name=PlanetStateKey.PHASE,
        device_class=SensorDeviceClass.ENUM,
        options=[phase["name"] for phase in moon_phases.values()],
    ),
)


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry-for-a-platform
async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: PlanetPhaseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # check if planet is active
    for name in PlanetPhaseApiClient.get_active_planets():
        ## main sensor (nur wenn MainSensor aktiv)
        if PlanetPhaseApiClient.is_mainsensor_active(name):
            coordinator = entry.runtime_data.coordinators.get(name)
            if coordinator is not None:
                async_add_entities(
                    PlanetPhaseMainSensor(
                        coordinator=coordinator,
                        entity_description=entity_description,
                    )
                    for entity_description in ENTITY_DESCRIPTIONS_PLANET_PHASE
                )
            else:
                LOGGER.error(f"{name} - Koordinator wurde nicht gefunden!")

        ## planet state sensors (nur wenn StateSensors aktiv)
        if PlanetPhaseApiClient.is_statesensors_active(name):
            coordinator = entry.runtime_data.coordinators.get(name)
            if coordinator is not None:
                async_add_entities(
                    PlanetPhaseSensors(
                        coordinator=coordinator,
                        entity_description=entity_description,
                    )
                    for entity_description in ENTITY_DESCRIPTIONS_PLANET_PHASE_SENSORS
                )
                if name == "sun":  # Mond-spezifische Sensoren nur für die Sonne
                    async_add_entities(
                        PlanetPhaseSensors(
                            coordinator=coordinator,
                            entity_description=entity_description,
                        )
                        for entity_description in ENTITY_DESCRIPTIONS_PLANET_PHASE_SUN_SENSORS
                    )
                elif name == "moon":  # Mond-spezifische Sensoren nur für den Mond
                    async_add_entities(
                        PlanetPhaseSensors(
                            coordinator=coordinator,
                            entity_description=entity_description,
                        )
                        for entity_description in ENTITY_DESCRIPTIONS_PLANET_PHASE_MOON_SENSORS
                    )
            else:
                LOGGER.error(f"{name} - Koordinator wurde nicht gefunden!")


class PlanetPhaseMainSensor(PlanetPhaseEntity, SensorEntity):
    """planet_phase Sensor class."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PlanetPhaseDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        # 1. Unique ID
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"

        # 2. Hier erzwingst du die ID (z.B. sensor.sun_today_rising)
        # Das 'sensor' Präfix muss hier explizit mit rein!
        self.entity_id = f"sensor.{coordinator.config_entry.domain}_{coordinator.planet_name}_{entity_description.key}"

        # 3. Den translation_key für den Friendly Name in der UI
        # planet = self.coordinator.planet_name
        # if planet in ["sun", "moon"]:
        #    self._attr_translation_key = f"{planet}_{entity_description.key}"
        # else:
        #    self._attr_translation_key = entity_description.key
        self._attr_translation_key = entity_description.key

        # Falls du SICHER gehen willst, dass ohne Übersetzung nicht der Key erscheint:

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        phase_data, phase_icon = self.coordinator.data
        self.icon = phase_icon.get(self.entity_description.key)  # Icon basierend auf der aktuellen Phase setzen
        return f"{phase_data.get(self.entity_description.key)}_{phase_data.get(PlanetStateKey.MAIN_MOVE)}"

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes of the sensor."""
        return self.coordinator.data[0]  # phase_data


class PlanetPhaseSensors(PlanetPhaseEntity, SensorEntity):
    """planet_phase Sensor class."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PlanetPhaseDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        # 1. Unique ID
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"

        # 2. Hier erzwingst du die ID (z.B. sensor.sun_today_rising)
        # Das 'sensor' Präfix muss hier explizit mit rein!
        self.entity_id = f"sensor.{coordinator.config_entry.domain}_{coordinator.planet_name}_{entity_description.key}"

        # 3. Den translation_key für den Friendly Name in der UI
        planet = self.coordinator.planet_name
        if planet in ["sun", "moon"]:
            self._attr_translation_key = f"{planet}_{entity_description.key}"
        else:
            self._attr_translation_key = entity_description.key

        # Falls du SICHER gehen willst, dass ohne Übersetzung nicht der Key erscheint:

    @property
    def native_value(self) -> datetime | None:
        """Return the native value of the sensor."""
        phase_data, phase_icon = self.coordinator.data
        self.icon = phase_icon.get(self.entity_description.key)  # Icon basierend auf der aktuellen Phase setzen
        return phase_data.get(self.entity_description.key)
