"""Test sensor for simple integration."""

from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.planet_phase.api import PLANET_MAP_DEFAULT
from custom_components.planet_phase.const import DOMAIN
from custom_components.planet_phase.const import PlanetConfigKey
from custom_components.planet_phase.const import PlanetStateKey
from custom_components.planet_phase.coordinator import PlanetPhaseDataUpdateCoordinator

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from syrupy.assertion import SnapshotAssertion


async def _get_test_states(hass: HomeAssistant, snapshot: SnapshotAssertion) -> None:
    """Test sensor."""
    planets = [
        "sun",
        "moon",
        "mars",
        "venus",
        "jupiter",
        "saturn",
        "uranus",
        "mercury",
        "neptune",
        "pluto",
    ]
    active_planets = {
        planet: {
            **PLANET_MAP_DEFAULT[planet],
            PlanetConfigKey.ACTIVE: True,
            PlanetConfigKey.MAIN_SENSOR: True,
            PlanetConfigKey.STATE_SENSORS: True,
        }
        for planet in planets
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**active_planets},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinators = entry.runtime_data.coordinators
    assert set(planets) <= set(coordinators)

    for planet in planets:
        coordinator = coordinators[planet]
        assert isinstance(coordinator, PlanetPhaseDataUpdateCoordinator), f"Coordinator für {planet} hat den falschen Typ"
        assert coordinator.last_update_success is True, f"Update-Fehler bei {planet}"
        assert coordinator.data is not None, f"Keine Daten für {planet} vorhanden"

    state_keys = [
        PlanetStateKey.MAIN_STATE,
        PlanetStateKey.TODAY_RISING,
        PlanetStateKey.TODAY_SETTING,
        PlanetStateKey.NEXT_RISING,
        PlanetStateKey.NEXT_SETTING,
        PlanetStateKey.PREVIOUS_RISING,
        PlanetStateKey.PREVIOUS_SETTING,
        PlanetStateKey.TODAY_ABOVE_HORIZON_TIME,
        PlanetStateKey.ALTITUDE,
        PlanetStateKey.AZIMUTH,
        PlanetStateKey.DISTANCE,
    ]

    for planet in planets:
        for state_key in state_keys:
            entity_id = f"sensor.{DOMAIN}_{planet}_{state_key}"
            assert hass.states.get(entity_id) == snapshot(name=entity_id)

    special_state_keys = {
        "sun": [
            PlanetStateKey.SUN_PHASE,
            PlanetStateKey.NEXT_VERNAL_EQUINOX,
            PlanetStateKey.NEXT_SUMMER_SOLSTICE,
            PlanetStateKey.NEXT_AUTUMNAL_EQUINOX,
            PlanetStateKey.NEXT_WINTER_SOLSTICE,
        ],
        "moon": [
            PlanetStateKey.MOON_PHASE,
            PlanetStateKey.MOON_NEXT_NEWMOON,
            PlanetStateKey.MOON_NEXT_FULLMOON,
        ],
    }

    for planet, extra_keys in special_state_keys.items():
        for state_key in extra_keys:
            entity_id = f"sensor.{DOMAIN}_{planet}_{state_key}"
            assert hass.states.get(entity_id) == snapshot(name=entity_id)


@pytest.mark.asyncio
async def test_sensor_without_config(hass: HomeAssistant, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
    """Test sensor."""
    local_now = datetime(2000, 1, 1, 1, 1, 1, tzinfo=ZoneInfo("Europe/Berlin"))
    freezer.move_to(local_now)

    # Verwende async_update für alle Werte gleichzeitig
    await hass.config.async_update(latitude=None, longitude=None, elevation=None, time_zone=None)

    # Warte, bis die Konfigurationsänderung verarbeitet wurde
    await hass.async_block_till_done()

    await _get_test_states(hass, snapshot)


@pytest.mark.parametrize(
    ("test_time", "description"),
    [
        (datetime(2025, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("Europe/Berlin")), "last_second_2025"),
        (datetime(2026, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")), "first_second_2026"),
    ],
)
@pytest.mark.asyncio
async def test_sensor_time_transitions(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion, test_time: datetime, description: str
) -> None:
    """Test sensor states at different time points."""
    # Zeit einfrieren
    freezer.move_to(test_time)

    # 2. Sensor initialisieren
    # Verwende async_update für alle Werte gleichzeitig
    await hass.config.async_update(latitude=48.69413582658938, longitude=9.418473690748216, elevation=295, time_zone="Europe/Berlin")

    # Warte, bis die Konfigurationsänderung verarbeitet wurde
    await hass.async_block_till_done()

    # Snapshot wird für jeden Parameter separat gespeichert
    await _get_test_states(hass, snapshot(name=description))
