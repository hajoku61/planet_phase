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


async def _get_test_states(hass: HomeAssistant, snapshot: SnapshotAssertion, expected_state: str) -> None:
    """Test sensor."""
    # Liste aller zu prüfenden Himmelskörper
    planets = ["sun"]
    active_planets = {}
    for planet in planets:
        # Kopiere das Dict aus PLANET_MAP_DEFAULT und setze ACTIVE auf True
        active_planets[planet] = {
            **PLANET_MAP_DEFAULT[planet],
            PlanetConfigKey.ACTIVE: True,
            PlanetConfigKey.MAIN_SENSOR: True,
            PlanetConfigKey.STATE_SENSORS: True,
        }

    # MockConfigEntry mit den aktiven Planeten-Konfigurationen
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**active_planets},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Validierung der Koordinatoren in runtime_data
    # (Angenommen, dein Data-Objekt hat ein Attribut 'coordinators')
    coordinators = entry.runtime_data.coordinators

    # Instanz-Typ prüfen
    for planet in planets:
        assert isinstance(coordinators[planet], PlanetPhaseDataUpdateCoordinator), f"Coordinator für {planet} hat den falschen Typ"

    # Initialen Datenstatus prüfen (falls gewünscht)
    # Prüft, ob der Coordinator bereits erfolgreich Daten geholt hat
    for planet in planets:
        coordinator = coordinators[planet]
        assert coordinator.last_update_success is True, f"Update-Fehler bei {planet}"
        assert coordinator.data is not None, f"Keine Daten für {planet} vorhanden"

    # Prüfen, ob Daten in cooridinator (nicht None)
    for planet in planets:
        assert planet in coordinators, f"{planet} fehlt in den Coordinators"

    # Zugriff auf die spezifischen Koordinatoren aus runtime_data
    for planet in planets:
        coordinator = entry.runtime_data.coordinators[planet]
        # Prüfen, ob Daten vorhanden sind und das Update erfolgreich war
        assert coordinator.data is not None, f"Keine Daten für {planet} gefunden"
        # Überprüfen, ob der letzte Update-Zyklus erfolgreich war
        assert coordinator.last_update_success is True, f"Update für {planet} fehlgeschlagen"

    # Sensor Main Daten prüfen (hier kannst du spezifische Werte oder Strukturen validieren, je nach dem, was dein Snapshot enthält)
    for planet in planets:
        # Den State-Key für den Hauptstatus abrufen
        entity_id = f"sensor.{DOMAIN}_{planet}_{PlanetStateKey.MAIN_STATE}"
        state = hass.states.get(entity_id)
        # Snapshot-Vergleich
        assert state == snapshot(name=f"{planet}_{PlanetStateKey.MAIN_STATE}")

        entity_id = f"sensor.{DOMAIN}_{planet}_{PlanetStateKey.PHASE}"
        state = hass.states.get(entity_id)
        assert state == snapshot(name=entity_id)

        assert state is not None, f"Entity {entity_id} not found"
        assert state.state == expected_state, (
            f"Erwarteter Zustand '{expected_state}' für {planet} ist nicht korrekt, tatsächlicher Zustand: '{state.state}'"
        )


@pytest.mark.parametrize(
    ("test_time", "description", "expected_state"),
    [
        (datetime(2025, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("Europe/Berlin")), "last_second_2025", "night"),
        (datetime(2026, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")), "first_second_2026", "night"),
        (datetime(2026, 1, 1, 1, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")), "first_hour_2026_to_check_localtime", "night"),
        (datetime(2026, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")), "midday_new_year", "day"),
        (datetime(2025, 3, 30, 1, 59, tzinfo=ZoneInfo("Europe/Berlin")), "dst_spring", "night"),
        (datetime(2025, 10, 26, 2, 30, tzinfo=ZoneInfo("Europe/Berlin")), "dst_autumn", "night"),
        # Sommersonnenwende: Teste den spätesten Sonnenuntergang
        (datetime(2025, 6, 21, 21, 25, tzinfo=ZoneInfo("Europe/Berlin")), "just_before_sunset_summer", "evening_small_day"),
        (datetime(2025, 6, 21, 21, 27, tzinfo=ZoneInfo("Europe/Berlin")), "just_after_sunset_summer", "evening_twilight"),
        # Wintersonnenwende: Teste die bürgerliche Dämmerung morgens
        (datetime(2025, 12, 21, 7, 33, tzinfo=ZoneInfo("Europe/Berlin")), "before_civil_dawn_winter", "morning_nautical_twilight"),
        (datetime(2025, 12, 21, 7, 35, tzinfo=ZoneInfo("Europe/Berlin")), "after_civil_dawn_winter", "morning_twilight"),
        # Zeitumstellung: Teste den Übergang (2:00 -> 3:00 Uhr)
        (datetime(2025, 3, 30, 1, 59, tzinfo=ZoneInfo("Europe/Berlin")), "dst_spring_jump", "night"),
        # Frühester Sonnenaufgang (Sommer)
        (datetime(2025, 6, 16, 5, 20, tzinfo=ZoneInfo("Europe/Berlin")), "just_before_earliest_sunrise", "morning_twilight"),
        (datetime(2025, 6, 16, 5, 22, tzinfo=ZoneInfo("Europe/Berlin")), "just_after_earliest_sunrise", "morning_small_day"),
        # Frühester Sonnenuntergang (Winter)
        (datetime(2025, 12, 11, 16, 24, tzinfo=ZoneInfo("Europe/Berlin")), "just_before_earliest_sunset", "evening_small_day"),
        (datetime(2025, 12, 11, 16, 26, tzinfo=ZoneInfo("Europe/Berlin")), "just_after_earliest_sunset", "evening_twilight"),
        # Jahreswechsel (Überlauf-Test)
        (datetime(2025, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("Europe/Berlin")), "year_overflow_last_sec", "night"),
    ],
    # ids=lambda x: x if isinstance(x, str) else "",
)
@pytest.mark.asyncio
async def test_sensor_time_transitions(  # noqa: PLR0913
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion, test_time: datetime, description: str, expected_state: str
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
    await _get_test_states(hass, snapshot(name=description), expected_state)
