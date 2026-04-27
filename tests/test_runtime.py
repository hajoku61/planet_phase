"""Test sensor for simple integration."""

from typing import TYPE_CHECKING
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.planet_phase.const import DOMAIN
from custom_components.planet_phase.const import PlanetStateKey
from custom_components.planet_phase.runtime import delete_planet_device_runtime
from custom_components.planet_phase.runtime import delete_planet_entities_runtime

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_delete_planet_runtime(hass: HomeAssistant) -> None:
    """Testet, ob ein Planeten Device korrekt aus der Registry gelöscht werden."""
    # 1. Setup: Entry & Device/Entity in Registry anlegen
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="test_id")
    entry.add_to_hass(hass)

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, f"test_id_{DOMAIN}_mars")})

    # 2. Löschfunktion aufrufen
    await delete_planet_device_runtime(hass, entry, "mars")

    # 3. Verify
    assert dev_reg.async_get(device.id) is None


async def test_delete_planet_entities_runtime_success(hass: HomeAssistant) -> None:
    """Testet, ob Entitäten eines Planeten korrekt aus der Registry gelöscht werden."""
    # 1. Setup: Registrierung vorbereiten
    # Manueller Setup des Entries
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="test_entry_123")
    entry.add_to_hass(hass)  # Wichtig, damit die Registry den Entry kennt

    ent_reg = er.async_get(hass)
    planet = "mars"
    target_prefix = f"{entry.entry_id}_{DOMAIN}_{planet}"
    # Erstelle eine Test-Entität in der Registry (z.B. den Main Sensor)
    main_sensor_uid = f"{target_prefix}_{PlanetStateKey.MAIN_STATE}"
    entry_main = ent_reg.async_get_or_create("sensor", DOMAIN, main_sensor_uid, config_entry=entry)

    # Erstelle eine weitere Entität (z.B. einen State Sensor)
    state_sensor_uid = f"{target_prefix}_azimuth"
    entry_state = ent_reg.async_get_or_create("sensor", DOMAIN, state_sensor_uid, config_entry=entry)

    # 2. Ausführung: Wir simulieren, dass die Sensoren deaktiviert wurden
    # Wir müssen den API-Client mocken, da deine Funktion dort nachschaut
    with (
        patch("custom_components.planet_phase.api.PlanetPhaseApiClient.is_mainsensor_active", return_value=False),
        patch("custom_components.planet_phase.api.PlanetPhaseApiClient.is_statesensors_active", return_value=False),
    ):
        await delete_planet_entities_runtime(hass, entry, planet)

    # 3. Überprüfung: Sind die Entitäten aus der Registry verschwunden?
    assert ent_reg.async_get(entry_main.entity_id) is None
    assert ent_reg.async_get(entry_state.entity_id) is None
