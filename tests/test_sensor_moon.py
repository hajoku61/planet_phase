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


async def _get_test_states(hass: HomeAssistant, snapshot: SnapshotAssertion, expected_phase: str) -> None:
    """Test sensor."""
    # Liste aller zu prüfenden Himmelskörper
    planets = ["moon"]
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
        assert state.state == expected_phase, (
            f"Erwarteter Zustand '{expected_phase}' für {planet} ist nicht korrekt, tatsächlicher Zustand: '{state.state}'"
        )


@pytest.mark.parametrize(
    ("test_time", "expected_phase"),
    [
        # 1. Neumond (p < 1.0)
        (datetime(2025, 1, 29, 12, 35, tzinfo=ZoneInfo("UTC")), "new_moon"),
        # 2. Zunehmende Sichel (is_waxing=True, p < 50.0)
        (datetime(2025, 2, 2, 12, 0, tzinfo=ZoneInfo("UTC")), "waxing_crescent"),
        # 3. Erstes Viertel / Halbmond (is_waxing=True, 48.0 <= p <= 52.0)
        (datetime(2025, 3, 6, 16, 30, tzinfo=ZoneInfo("UTC")), "first_quarter"),
        # 4. Zunehmender Dreiviertel (is_waxing=True, p > 52.0)
        (datetime(2025, 3, 10, 12, 0, tzinfo=ZoneInfo("UTC")), "waxing_gibbous"),
        # 5. Vollmond (p > 99.0)
        (datetime(2025, 5, 12, 17, 0, tzinfo=ZoneInfo("UTC")), "full_moon"),
        # 6. Abnehmender Dreiviertel (is_waxing=False, p > 52.0)
        (datetime(2025, 5, 18, 12, 0, tzinfo=ZoneInfo("UTC")), "waning_gibbous"),
        # 7. Letztes Viertel / Halbmond (is_waxing=False, 48.0 <= p <= 52.0)
        (datetime(2025, 5, 20, 12, 0, tzinfo=ZoneInfo("UTC")), "last_quarter"),
        # 8. Abnehmende Sichel (is_waxing=False, p < 48.0)
        (datetime(2025, 5, 23, 12, 0, tzinfo=ZoneInfo("UTC")), "waning_crescent"),
    ],
)
@pytest.mark.asyncio
async def test_sensor_time_transitions(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion, test_time: datetime, expected_phase: str
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
    await _get_test_states(hass, snapshot, expected_phase)
