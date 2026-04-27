"""DataUpdateCoordinator for planet_phase."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .const import LOGGER
from .const import UPDATE_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import PlanetPhaseApiClient
    from .data import PlanetPhaseConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class PlanetPhaseDataUpdateCoordinator(DataUpdateCoordinator[tuple[dict[str, Any], dict[str, Any]]]):
    """Generelle Klasse für Planeten-Daten (Sonne, Mond, etc.)."""

    config_entry: PlanetPhaseConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: PlanetPhaseApiClient,  # <-- Den Client hier übergeben
        planet_name: str,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{planet_name}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        self.planet_name = planet_name

    async def _async_update_data(self) -> Any:
        """Update data via den zugewiesenen Client."""
        # Hier nutzt du jetzt den lokalen Client, egal ob Sonne oder Mond
        return await self.client.async_get_data(self.planet_name)

    async def async_set_update_interval(self, interval: int) -> None:
        """Dynamisch das Update-Intervall anpassen."""
        self.update_interval = timedelta(seconds=interval)
        # await self.async_refresh()
