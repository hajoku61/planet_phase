"""PlanetPhaseEntity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PlanetPhaseDataUpdateCoordinator


class PlanetPhaseEntity(CoordinatorEntity[PlanetPhaseDataUpdateCoordinator]):
    """PlanetPhaseEntity class."""

    _attr_has_entity_name = True
    _attr_attribution = DOMAIN

    def __init__(self, coordinator: PlanetPhaseDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{coordinator.name}"
        self._attr_device_info = DeviceInfo(
            translation_key=coordinator.name,
            name=coordinator.name,
            identifiers={
                (coordinator.config_entry.domain, self._attr_unique_id),
            },
            entry_type=DeviceEntryType.SERVICE,
        )

    # @property
    # def anslation_key(self) -> str | None:
    #    """Translation key for all sensors."""
    #    planet = self.coordinator.planet_name
    #    if planet in ["sun", "moon"]:
    #        return f"{planet}_{self.entity_description.key}"
    #    return self.entity_description.key

    # @property
    # def name(self) -> str | None:
    #    """Return None so that translation_key is used for the name."""
    #    ##return None
    #    return self.entity_description.key
