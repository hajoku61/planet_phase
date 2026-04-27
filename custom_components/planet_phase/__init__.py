"""
Custom integration to integrate planet_phase with Home Assistant.

For more details about this integration, please refer to
https://github.com/hajoku61/planet_phase
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .api import PlanetPhaseApiClient
from .const import LOGGER
from .const import UPDATE_INTERVAL
from .const import PlanetConfigKey
from .runtime import add_planet_runtime
from .runtime import delete_planet_device_runtime
from .runtime import delete_planet_entities_runtime
from .runtime import init_planet_runtime

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import PlanetPhaseConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlanetPhaseConfigEntry,
) -> bool:
    """Set up planet_phase from a config entry."""
    # entry.data enthält z.B. {"sun": {"active": True}, "mars": {"active": True}}
    config_entry_data = entry.data

    # In runtime_data speichern
    await init_planet_runtime(hass, entry)

    for name, config in config_entry_data.items():
        # 1. Prüfen, ob config ein Dictionary ist und nicht leer {}
        if not isinstance(config, dict) or not config:
            LOGGER.debug("Überspringe %s: Keine Konfigurationsdaten gefunden.", name)
            continue

        # .get() mit leerem Dict als Default verhindert KeyErrors bei config["active"]
        # config = config_entry_data.get(name, {})

        # Status in der API setzen
        is_active = config.get(PlanetConfigKey.ACTIVE, False)
        update_interval = config.get(PlanetConfigKey.UPDATE_INTERVAL, UPDATE_INTERVAL)

        # Config Daten in PlanetPhaseApiClient setzen (damit sie auch in coordinator/api verfügbar sind)
        # Die Flags kompakt einsammeln
        api_settings = {
            "enable": is_active,
            "main_active": config.get(PlanetConfigKey.MAIN_SENSOR, False),
            "states_active": config.get(PlanetConfigKey.STATE_SENSORS, False),
            "update_interval": update_interval,
        }
        PlanetPhaseApiClient.update_config(name, **api_settings)

        if is_active:
            coordinator = await add_planet_runtime(hass, entry, name)
            await coordinator.async_set_update_interval(update_interval)
            # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
            await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: PlanetPhaseConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: PlanetPhaseConfigEntry,
) -> None:
    """Reload config entry."""
    config_entry_data = entry.data

    for name in PlanetPhaseApiClient.get_active_planets():
        # for name, config in config_entry_data.items():
        # .get() mit leerem Dict als Default verhindert KeyErrors bei config["active"]
        config = config_entry_data.get(name, {})

        # 1. API-Status aktualisieren
        api_settings = {
            "enable": config.get(PlanetConfigKey.ACTIVE, False),
            "main_active": config.get(PlanetConfigKey.MAIN_SENSOR, False),
            "states_active": config.get(PlanetConfigKey.STATE_SENSORS, False),
            "update_interval": config.get(PlanetConfigKey.UPDATE_INTERVAL, UPDATE_INTERVAL),
        }
        PlanetPhaseApiClient.update_config(name, **api_settings)

        # 2. Prüfen, ob der Planet operativ sein soll (Aktiv + Sensoren vorhanden)
        is_active = api_settings["enable"]
        has_any_sensor = api_settings["main_active"] or api_settings["states_active"]

        if is_active and has_any_sensor:
            # Planeten-Entities neu laden / hinzufügen
            await delete_planet_entities_runtime(hass, entry, name)
            coordinator = await add_planet_runtime(hass, entry, name)
            await coordinator.async_set_update_interval(api_settings["update_interval"])
        else:
            # Planet deaktivieren oder aufräumen, da keine Sensoren gewählt
            await delete_planet_device_runtime(hass, entry, name)
            PlanetPhaseApiClient.reset_to_defaults(name)
            # Defaults zurück in die Config schreiben
            new_planet_config = PlanetPhaseApiClient.get_config(name)
            new_data = {**entry.data, name: new_planet_config}

            # 3. Persistent speichern (triggert ggf. intern den nötigen Reload)
            hass.config_entries.async_update_entry(entry, data=new_data)

    # WICHTIG: Entferne 'await hass.config_entries.async_reload(entry.entry_id)'
    # hier, um eine Endlosschleife zu verhindern!
    await hass.config_entries.async_reload(entry.entry_id)


# async def async_remove_config_entry_device(
#    hass: HomeAssistant, entry: PlanetPhaseConfigEntry, device_entry: dr.DeviceEntry
# ) -> bool:
#    """Wird aufgerufen, um zu entscheiden, ob ein Gerät gelöscht werden darf."""
#    # 1. Hier kannst du Logik einbauen (z.B. prüfen, ob das Gerät noch aktiv ist)
#    # 2. Wenn du True zurückgibst, löscht HA das Gerät aus der Registry.
#    return True
