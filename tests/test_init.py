"""Test sensor for simple integration."""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from unittest.mock import patch

from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.planet_phase import async_reload_entry
from custom_components.planet_phase import async_setup_entry
from custom_components.planet_phase import async_unload_entry
from custom_components.planet_phase.const import DOMAIN
from custom_components.planet_phase.const import PlanetConfigKey

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_setup_unload_and_reload_entry(hass: HomeAssistant) -> None:
    """Testet das vollständige Setup und Unload der Integration."""
    # 1. Setup: Test-Daten für den Config Entry
    entry_data = {
        "sun": {
            PlanetConfigKey.ACTIVE: True,
            PlanetConfigKey.MAIN_SENSOR: True,
            PlanetConfigKey.STATE_SENSORS: True,
            PlanetConfigKey.UPDATE_INTERVAL: 600,
        }
    }
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data, entry_id="test_id", unique_id="planet_unique_123")
    entry.add_to_hass(hass)

    # 2. Mocks vorbereiten
    mock_integration = MagicMock()
    mock_integration.domain = DOMAIN

    # Wir patchen dort, wo die Funktionen/Klassen von der Integration verwendet werden
    with (
        patch("custom_components.planet_phase.runtime.async_get_loaded_integration", return_value=mock_integration),
        patch("custom_components.planet_phase.api.PlanetPhaseApiClient.update_config") as mock_api_update,
        patch("custom_components.planet_phase.runtime.PlanetPhaseDataUpdateCoordinator.async_config_entry_first_refresh", return_value=None),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=True) as mock_forward,
    ):
        # 3. Setup ausführen
        assert await async_setup_entry(hass, entry) is True
        await hass.async_block_till_done()

        # Überprüfen, ob die API mit den richtigen Werten initialisiert wurde
        mock_api_update.assert_called_with("sun", enable=True, main_active=True, states_active=True, update_interval=600)

        # Überprüfen, ob die Sensor-Plattform geladen wurde
        mock_forward.assert_called_once_with(entry, [Platform.SENSOR])

    # 4. Test Unload (Entfernen der Integration)
    with patch("homeassistant.config_entries.ConfigEntries.async_unload_platforms", return_value=True) as mock_unload:
        assert await async_unload_entry(hass, entry) is True
        await hass.async_block_till_done()

        # Sicherstellen, dass die Plattformen auch wieder entladen wurden
        mock_unload.assert_called_once_with(entry, [Platform.SENSOR])


async def test_async_reload_entry(hass: HomeAssistant) -> None:
    """Testet den Reload-Mechanismus bei Konfigurationsänderung."""
    # Einfacher Entry für den Reload-Test
    entry = MockConfigEntry(domain=DOMAIN, data={"sun": {PlanetConfigKey.ACTIVE: True}}, entry_id="test_reload")
    entry.add_to_hass(hass)

    # Wir patchen den internen HA-Reload Aufruf
    with (
        patch("homeassistant.config_entries.ConfigEntries.async_reload") as mock_reload,
        patch("custom_components.planet_phase.api.PlanetPhaseApiClient.get_active_planets", return_value=["sun"]),
    ):
        await async_reload_entry(hass, entry)

        # Verifizieren, dass der Reload bei Home Assistant angefordert wurde
        mock_reload.assert_called_once_with(entry.entry_id)
