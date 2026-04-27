"""Runtime management for planets in the planet_phase integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_loaded_integration

from .api import PlanetPhaseApiClient
from .const import DOMAIN
from .const import LOGGER
from .const import PlanetStateKey
from .coordinator import PlanetPhaseDataUpdateCoordinator
from .data import PlanetPhaseData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import PlanetPhaseConfigEntry


async def init_planet_runtime(hass: HomeAssistant, entry: PlanetPhaseConfigEntry) -> None:
    """Init planet at runtime."""
    # Create client & coordinator
    client = PlanetPhaseApiClient(hass)

    # In runtime_data speichern (als Dictionary für dynamischen Zugriff)
    entry.runtime_data = PlanetPhaseData(
        integration=async_get_loaded_integration(hass, entry.domain),
        client=client,
        coordinators={},
    )


async def add_planet_runtime(hass: HomeAssistant, entry: PlanetPhaseConfigEntry, planet_name: str) -> PlanetPhaseDataUpdateCoordinator:
    """Add a new planet at runtime."""
    # Create coordinator
    coordinator = PlanetPhaseDataUpdateCoordinator(hass, entry.runtime_data.client, planet_name)
    entry.runtime_data.coordinators[planet_name] = coordinator

    return coordinator


async def delete_planet_device_runtime(hass: HomeAssistant, entry: PlanetPhaseConfigEntry, planet_name: str) -> None:
    """Delete a planet device at runtime."""
    # 1. Hol dir die Device Registry
    dev_reg = dr.async_get(hass)

    # 2. Finde alle Geräte, die zu diesem Config Entry gehören
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)

    for device_entry in devices:
        # Security check: identifiers present?
        if not device_entry.identifiers:
            continue

        # Sicherere Prüfung der Identifiers
        for domain, ident_value in device_entry.identifiers:
            # Planeten Device Schema
            device_id = f"{entry.entry_id}_{domain}_{planet_name}"
            if ident_value == device_id:
                LOGGER.info(f"Removing device: {device_entry.name}")
                dev_reg.async_remove_device(device_entry.id)
                break


async def delete_planet_entities_runtime(hass: HomeAssistant, entry: PlanetPhaseConfigEntry, planet_name: str) -> None:
    """Delete a planet entities at runtime."""
    # 1. Zugriff auf die Entity Registry holen
    ent_reg = er.async_get(hass)

    # 2. Alle Entitäten finden, die zu dieser Config Entry ID gehören
    entities = er.async_entries_for_config_entry(ent_reg, entry.entry_id)

    # Dein Präfix für den Abgleich
    target_prefix = f"{entry.entry_id}_{DOMAIN}_{planet_name}"

    for entity_entry in entities:
        if not entity_entry.unique_id:
            continue

        # Prüfen, ob die Entität zum gesuchten Planeten gehört
        if entity_entry.unique_id.startswith(target_prefix):
            should_remove = False

            # Logik für Main Sensor
            if entity_entry.unique_id == f"{target_prefix}_{PlanetStateKey.MAIN_STATE}":
                if not PlanetPhaseApiClient.is_mainsensor_active(planet_name):
                    should_remove = True

            # Logik für State Sensoren
            elif not PlanetPhaseApiClient.is_statesensors_active(planet_name):
                should_remove = True

            if should_remove:
                LOGGER.info(
                    "Removing entity: %s (ID: %s)",
                    entity_entry.unique_id,
                    entity_entry.entity_id,
                )

                # WICHTIG: Nutze entity_id, nicht unique_id zum Löschen
                ent_reg.async_remove(entity_entry.entity_id)
