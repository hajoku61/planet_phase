"""Custom types for planet_phase."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import PlanetPhaseApiClient
    from .coordinator import PlanetPhaseDataUpdateCoordinator


type PlanetPhaseConfigEntry = ConfigEntry[PlanetPhaseData]


@dataclass
class PlanetPhaseData:
    """Data for the planet_phase integration."""

    integration: Integration
    client: PlanetPhaseApiClient

    # Nutze Dictionaries, um zur Laufzeit beliebig zu erweitern
    coordinators: dict[str, PlanetPhaseDataUpdateCoordinator] = field(default_factory=dict)
