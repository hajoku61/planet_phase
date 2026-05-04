"""Planets API Client."""

from __future__ import annotations

import copy
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any
from zoneinfo import ZoneInfo

import ephem
from homeassistant.util import dt as dt_util

from .const import LOGGER
from .const import UPDATE_INTERVAL
from .const import PlanetConfigKey
from .const import PlanetStateKey

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# As documented in wikipedia: https://en.wikipedia.org/wiki/Twilight
# sun is:
# > 10° above horizon
DEF_DAY = 10
PHASE_DAY = "DAY"
# 0°-10° above horizon, sun low on horizon
DEF_SMALL_DAY = 0
PHASE_SMALL_DAY = "SMALL_DAY"
# -6°-0° - objects visible
DEF_TWILIGHT = -6
PHASE_TWILIGHT = "TWILIGHT"
# -12°-6° - horizon visible
DEF_NAUTICAL_TWILIGHT = -12
PHASE_NAUTICAL_TWILIGHT = "NAUTICAL_TWILIGHT"
# -18°-12° - some stars not visible
DEF_ASTRONOMICAL_TWILIGHT = -18
PHASE_ASTRONOMICAL_TWILIGHT = "ASTRONOMICAL_TWILIGHT"
# < -18° of horizon - all stars visible
PHASE_NIGHT = "NIGHT"

# 1. Phase über ein Mapping bestimmen
# (Absteigend sortiert nach Schwellenwert)
sun_thresholds = [
    (DEF_DAY, PHASE_DAY),
    (DEF_SMALL_DAY, PHASE_SMALL_DAY),
    (DEF_TWILIGHT, PHASE_TWILIGHT),
    (DEF_NAUTICAL_TWILIGHT, PHASE_NAUTICAL_TWILIGHT),
    (DEF_ASTRONOMICAL_TWILIGHT, PHASE_ASTRONOMICAL_TWILIGHT),
]

sun_phases = {
    "NIGHT": {"name": "night"},
    "MORNING_ASTRONOMICAL_TWILIGHT": {"name": "morning_astronomical_twilight"},
    "MORNING_NAUTICAL_TWILIGHT": {"name": "morning_nautical_twilight"},
    "MORNING_TWILIGHT": {"name": "morning_twilight"},
    "MORNING_SMALL_DAY": {"name": "morning_small_day"},
    "DAY": {"name": "day"},
    "EVENING_SMALL_DAY": {"name": "evening_small_day"},
    "EVENING_TWILIGHT": {"name": "evening_twilight"},
    "EVENING_NAUTICAL_TWILIGHT": {"name": "evening_nautical_twilight"},
    "EVENING_ASTRONOMICAL_TWILIGHT": {"name": "evening_astronomical_twilight"},
}

# Konstanten für die Mond Schwellenwerte
THRESHOLD_NEW = 1.0
THRESHOLD_FULL = 99.0
QUARTER_LOW = 48.0
QUARTER_HIGH = 52.0
HALF_MARK = 50.0  # Die 50% Grenze für Sichel vs. Dreiviertel

moon_phases_saves = {
    "MOON_NEW_MOON": {"name": "new_moon", "icon": "🌑"},  # Neumond
    "MOON_WAXING_CRESCENT": {"name": "waxing_crescent", "icon": "🌒"},  # zunehmender Sichelmond - Phase < 50
    "MOON_FIRST_QUARTER": {"name": "first_quarter", "icon": "🌓"},  # erstes Viertel - Phase ~ 50
    "MOON_WAXING_GIBBOUS": {"name": "waxing_gibbous", "icon": "🌔"},  # zunehmender Mond - Phase > 50
    "MOON_FULL_MOON": {"name": "full_moon", "icon": "🌕"},  # Vollmond
    "MOON_WANING_GIBBOUS": {"name": "waning_gibbous", "icon": "🌖"},  # abnehmender Mond - Phase > 50
    "MOON_LAST_QUARTER": {"name": "last_quarter", "icon": "🌗"},  # letztes Viertel - Phase ~ 50
    "MOON_WANING_CRESCENT": {"name": "waning_crescent", "icon": "🌘"},  # abnehmender Sichelmond - Phase < 50
}

moon_states = {
    "WAXING": "waxing",  # zunehmender Mond - Phase < 50
    "WANING": "waning",  # abnehmender Mond - Phase > 50
}

moon_phases = {
    "MOON_NEW_MOON": {"name": "new_moon", "icon": "mdi:moon-new"},  # Neumond
    "MOON_WAXING_CRESCENT": {"name": "waxing_crescent", "icon": "mdi:moon-waxing-crescent"},  # zunehmender Sichelmond - Phase < 50
    "MOON_FIRST_QUARTER": {"name": "first_quarter", "icon": "mdi:moon-first-quarter"},  # erstes Viertel - Phase ~ 50
    "MOON_WAXING_GIBBOUS": {"name": "waxing_gibbous", "icon": "mdi:moon-waxing-gibbous"},  # zunehmender Mond - Phase > 50
    "MOON_FULL_MOON": {"name": "full_moon", "icon": "mdi:moon-full"},  # Vollmond
    "MOON_WANING_GIBBOUS": {"name": "waning_gibbous", "icon": "mdi:moon-waning-gibbous"},  # abnehmender Mond - Phase > 50
    "MOON_LAST_QUARTER": {"name": "last_quarter", "icon": "mdi:moon-last-quarter"},  # letztes Viertel - Phase ~ 50
    "MOON_WANING_CRESCENT": {"name": "waning_crescent", "icon": "mdi:moon-waning-crescent"},  # abnehmender Sichelmond - Phase < 50
}

# Spezifische Icons für Sonne und Mond kombiniert mit dem Event
ICON_THEMES = {
    "sun": {
        PlanetStateKey.TODAY_RISING: "mdi:weather-sunset-up",  # Klassischer Sonnenaufgang
        PlanetStateKey.NEXT_RISING: "mdi:weather-sunset-up",  # Klassischer Sonnenaufgang
        PlanetStateKey.PREVIOUS_RISING: "mdi:weather-sunset-up",  # Klassischer Sonnenaufgang
        PlanetStateKey.TODAY_SETTING: "mdi:weather-sunset-down",  # Klassischer Sonnenuntergang
        PlanetStateKey.NEXT_SETTING: "mdi:weather-sunset-down",  # Klassischer Sonnenuntergang
        PlanetStateKey.PREVIOUS_SETTING: "mdi:weather-sunset-down",  # Klassischer Sonnenuntergang
        PlanetStateKey.NEXT_TRANSIT: "mdi:sun-clock",  # Höchster Sonnenstand
        PlanetStateKey.ALTITUDE: "mdi:angle-acute",  # Icon für Sonnenhöhe
        PlanetStateKey.AZIMUTH: "mdi:compass-outline",  # Icon für Sonnenazimut
        PlanetStateKey.TODAY_ABOVE_HORIZON_TIME: "mdi:timer-sand",  # Sonne über dem Horizont
        PlanetStateKey.NEXT_VERNAL_EQUINOX: "mdi:flower-tulip",  # Frühlingsanfang
        PlanetStateKey.NEXT_SUMMER_SOLSTICE: "mdi:weather-sunny",  # Sommeranfang
        PlanetStateKey.NEXT_AUTUMNAL_EQUINOX: "mdi:leaf",  # Herbstanfang
        PlanetStateKey.NEXT_WINTER_SOLSTICE: "mdi:weather-snowy-heavy",  # Winteranfang
        PlanetStateKey.DISTANCE: "mdi:map-marker-distance",
        PlanetStateKey.NEXT_ANTITRANSIT: "mdi:weather-night",
        PlanetStateKey.MEASUREMENT_LOCAL_TIME: "mdi:clock-outline",
        "above_horizon_up": "mdi:weather-sunset-up",  # Sonne über dem Horizont
        "above_horizon_down": "mdi:weather-sunset-down",  # Sonne über dem Horizont
        "below_horizon_up": "mdi:weather-moonset-up",  # Sonne unter dem Horizont
        "below_horizon_down": "mdi:weather-moonset-down",  # Sonne unter dem Horizont
        "default": "mdi:weather-sunny",  # Standard-Icon für Sonne
    },
    "moon": {
        PlanetStateKey.TODAY_RISING: "mdi:weather-moonset-up",  # Mond geht auf
        PlanetStateKey.NEXT_RISING: "mdi:weather-moonset-up",  # Mond geht auf
        PlanetStateKey.PREVIOUS_RISING: "mdi:weather-moonset-up",  # Mond geht auf
        PlanetStateKey.TODAY_SETTING: "mdi:weather-moonset-down",  # Mond geht unter
        PlanetStateKey.NEXT_SETTING: "mdi:weather-moonset-down",  # Mond geht unter
        PlanetStateKey.PREVIOUS_SETTING: "mdi:weather-moonset-down",  # Mond geht unter
        PlanetStateKey.NEXT_TRANSIT: "mdi:moon-full",  # Höchster Mondstand
        PlanetStateKey.ALTITUDE: "mdi:angle-acute",  # Icon für Mondhöhe
        PlanetStateKey.AZIMUTH: "mdi:compass-outline",  # Icon für Mondazimut
        PlanetStateKey.TODAY_ABOVE_HORIZON_TIME: "mdi:timer-sand",  # Mond über dem Horizont
        PlanetStateKey.MOON_NEXT_NEWMOON: "mdi:moon-new",  # Neumond
        PlanetStateKey.MOON_NEXT_FULLMOON: "mdi:moon-full",  # Vollmond
        PlanetStateKey.STATE: "mdi:information-outline",
        PlanetStateKey.DISTANCE: "mdi:map-marker-distance",
        PlanetStateKey.NEXT_ANTITRANSIT: "mdi:minus-circle-outline",
        PlanetStateKey.MEASUREMENT_LOCAL_TIME: "mdi:clock-outline",
        "above_horizon_up": "mdi:weather-sunset-up",  # Sonne über dem Horizont
        "above_horizon_down": "mdi:weather-sunset-down",  # Sonne über dem Horizont
        "below_horizon_up": "mdi:weather-moonset-up",  # Sonne unter dem Horizont
        "below_horizon_down": "mdi:weather-moonset-down",  # Sonne unter dem Horizont
        "default": "mdi:moon-full",  # Standard-Icon für Mond
    },
    "default": {
        PlanetStateKey.TODAY_RISING: "mdi:star-check-outline",  # Standard-Icon für Aufgang
        PlanetStateKey.NEXT_RISING: "mdi:star-check-outline",  # Standard-Icon für Aufgang
        PlanetStateKey.PREVIOUS_RISING: "mdi:star-check-outline",  # Standard-Icon für Aufgang
        PlanetStateKey.TODAY_SETTING: "mdi:star-check",  # Standard-Icon für Untergang
        PlanetStateKey.NEXT_SETTING: "mdi:star-check",  # Standard-Icon für Untergang
        PlanetStateKey.PREVIOUS_SETTING: "mdi:star-check",  # Standard-Icon für Untergang
        PlanetStateKey.NEXT_TRANSIT: "mdi:star-outline",  # Standard-Icon für Transit
        PlanetStateKey.ALTITUDE: "mdi:angle-acute",  # Standard-Icon für Höhe
        PlanetStateKey.AZIMUTH: "mdi:compass-outline",  # Standard-Icon für Azimut
        PlanetStateKey.TODAY_ABOVE_HORIZON_TIME: "mdi:timer-sand",  # Standard-Icon für über dem Horizont
        PlanetStateKey.DISTANCE: "mdi:map-marker-distance",
        PlanetStateKey.NEXT_ANTITRANSIT: "mdi:minus-circle-outline",
        PlanetStateKey.MEASUREMENT_LOCAL_TIME: "mdi:clock-outline",
        "above_horizon_up": "mdi:star-outline",  # Standard-Icon für über dem Horizont
        "above_horizon_down": "mdi:star-outline",  # Standard-Icon für über dem Horizont
        "below_horizon_up": "mdi:star",  # Standard-Icon für unter dem Horizont
        "below_horizon_down": "mdi:star",  # Standard-Icon für unter dem Horizont
        "default": "mdi:star-outline",  # Standard-Icon für alle anderen Fälle
    },
}
STAR_ASCENDING = "ascending"  # Aufsteigend (steigend) - Planet gewinnt an Höhe
STAR_DESCENDING = "descending"  # Absteigend (fallend) - Planet verliert an Höhe

STAR_ABOVE_HORIZON = "above_horizon"
STAR_BELOW_HORIZON = "below_horizon"

# Error messages
ERROR_INVALID_PLANET = "Planet does not exist in PLANET_MAP"


# Standard-Konfiguration der Planeten (unveränderlich)
def _p(
    cls: type,
    *,
    active: bool = False,
    main: bool = True,
    state: bool = False,
    interval: int = UPDATE_INTERVAL,
) -> dict[str, Any]:
    """Planets Helper class."""
    return {
        "class": cls,
        PlanetConfigKey.ACTIVE: active,
        PlanetConfigKey.MAIN_SENSOR: main,
        PlanetConfigKey.STATE_SENSORS: state,
        PlanetConfigKey.UPDATE_INTERVAL: interval,
    }


PLANET_MAP_DEFAULT = {
    "sun": _p(ephem.Sun, active=True, state=True, interval=60),
    "moon": _p(ephem.Moon, state=True, interval=60),
    "mars": _p(ephem.Mars),
    "venus": _p(ephem.Venus),
    "jupiter": _p(ephem.Jupiter),
    "saturn": _p(ephem.Saturn),
    "uranus": _p(ephem.Uranus),
    "mercury": _p(ephem.Mercury),
    "neptune": _p(ephem.Neptune),
    "pluto": _p(ephem.Pluto),
}


class PlanetPhaseApiClient:
    """Planets API Client."""

    # Arbeitskopie der Planeten-Konfiguration (kann zur Laufzeit geändert werden)
    # Wird mit einer tiefen Kopie der Standard-Werte initialisiert
    # PLANET_MAP: dict[str, dict[str, Any]] = {
    #    name: config.copy() for name, config in PLANET_MAP_DEFAULT.items()
    # }
    PLANET_MAP: dict[str, dict[str, Any]] | None = None  # Startet als None, wird bei Bedarf initialisiert

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API Client with location and planet configuration."""
        # Initialisierung der PLANET_MAP
        self._ensure_initialized()

        # Location-Daten aus Home Assistant-Konfiguration
        self.location_data = {
            "latitude": hass.config.latitude or 0,
            "longitude": hass.config.longitude or 0,
            "elevation": hass.config.elevation or 0,
            "timezone": hass.config.time_zone or "Europe/Berlin",
        }

        # Observer konfigurieren
        self.ephem = SimpleNamespace()
        self.ephem.observer = ephem.Observer()
        self.ephem.observer.lat = str(self.location_data["latitude"])
        self.ephem.observer.lon = str(self.location_data["longitude"])
        self.ephem.observer.elevation = self.location_data["elevation"]

        # Planetendaten initialisieren
        self.planet_phase_data: dict[str, Any] = {}
        self.planet_phase_data_icon: dict[str, Any] = {}  # Separates Dict für Icons
        self.planet_name: str
        self.measurement_date: datetime

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Stellt sicher, dass die Arbeitskopie existiert."""
        if cls.PLANET_MAP is None:
            # deepcopy ist hier Pflicht, da PLANET_MAP_DEFAULT verschachtelt ist
            cls.PLANET_MAP = copy.deepcopy(PLANET_MAP_DEFAULT)

    @classmethod
    def reinitialize(cls) -> None:
        """Initialisiert PLANET_MAP komplett neu von PLANET_MAP_DEFAULT."""
        cls.PLANET_MAP = copy.deepcopy(PLANET_MAP_DEFAULT)
        LOGGER.debug("PLANET_MAP reinitialisiert")

    @classmethod
    def reset_to_defaults(cls, planet_name: str | None = None) -> None:
        """Setzt alle oder einen spezifischen Planeten auf Standard-Werte zurück."""
        cls._ensure_initialized()

        current_map = cls.PLANET_MAP or {}
        # Fall 1: Nur einen spezifischen Planeten zurücksetzen
        if planet_name:
            if planet_name in PLANET_MAP_DEFAULT:
                current_map[planet_name] = PLANET_MAP_DEFAULT[planet_name].copy()
                LOGGER.debug("Planet '%s' auf Standard-Werte zurückgesetzt", planet_name)
            else:
                LOGGER.warning("Planet '%s' nicht in Standard-Konfiguration gefunden", planet_name)
        # Fall 2: Alle Planeten zurücksetzen
        else:
            for p_name, default_config in PLANET_MAP_DEFAULT.items():
                current_map[p_name] = default_config.copy()
            LOGGER.debug("Alle Planeten in PLANET_MAP auf Standard-Werte zurückgesetzt")

    @classmethod
    def get_config(cls, planet_name: str | None = None) -> dict[str, dict[str, Any]]:
        """Gibt die Konfiguration für einen spezifischen oder alle Planeten zurück."""
        cls._ensure_initialized()

        # Der Type-Checker ist nun sicher, dass wir ein Dict haben
        current_map = cls.PLANET_MAP or {}

        # Hilfsfunktion für die Standard-Struktur
        def _get_planet_defaults(data: dict) -> dict:
            return {
                PlanetConfigKey.ACTIVE: data.get(PlanetConfigKey.ACTIVE, False),
                PlanetConfigKey.MAIN_SENSOR: data.get(PlanetConfigKey.MAIN_SENSOR, False),
                PlanetConfigKey.STATE_SENSORS: data.get(PlanetConfigKey.STATE_SENSORS, False),
                PlanetConfigKey.UPDATE_INTERVAL: data.get(PlanetConfigKey.UPDATE_INTERVAL, UPDATE_INTERVAL),
            }

        # Fall 1: Konfiguration für ALLE Planeten
        if planet_name is None:
            return {name: _get_planet_defaults(config) for name, config in current_map.items()}
        # Fall 2: Konfiguration für einen SPEZIFISCHEN Planeten
        name = planet_name.lower()
        config = current_map.get(name, {})
        return _get_planet_defaults(config)

    @classmethod
    def update_config(
        cls,
        planet_name: str,
        *,
        enable: bool = False,
        main_active: bool = False,
        states_active: bool = False,
        update_interval: int = UPDATE_INTERVAL,
    ) -> None:
        """Aktualisiert die Konfiguration eines Planeten."""
        # Hier die Logik zum Speichern/Setzen der Werte
        cls.set_planet_active(planet_name, enable=enable)
        cls.set_mainsensor_active(planet_name, enable=main_active)
        cls.set_statesensors_active(planet_name, enable=states_active)
        cls.set_update_interval(planet_name, interval=update_interval)

    @classmethod
    def get_active_planets(cls) -> dict[str, dict[str, Any]]:
        """Gibt nur die Einträge zurück, bei denen 'active' auf True steht."""
        return cls._filter_config_by_flag(PlanetConfigKey.ACTIVE)

    @classmethod
    def get_active_mainsensors(cls) -> dict[str, dict[str, Any]]:
        """Gibt nur die Einträge zurück, bei denen 'MainSensor' auf True steht."""
        return cls._filter_config_by_flag(PlanetConfigKey.MAIN_SENSOR)

    @classmethod
    def get_active_statesensors(cls) -> dict[str, dict[str, Any]]:
        """Gibt nur die Einträge zurück, bei denen 'StateSensors' auf True steht."""
        return cls._filter_config_by_flag(PlanetConfigKey.STATE_SENSORS)

    @classmethod
    def _filter_config_by_flag(cls, flag: str, *, target_value: bool = True) -> dict[str, dict[str, Any]]:
        """Hilfsmethode: Filtert Planeten nach einem bestimmten Flag."""
        cls._ensure_initialized()
        # Der Type-Checker ist nun sicher, dass wir ein Dict haben
        if cls.PLANET_MAP is None:
            return {}  # Fallback, sollte theoretisch nie erreicht werden
        return {name: config for name, config in cls.PLANET_MAP.items() if config.get(flag, False) == target_value}

    @classmethod
    def is_planet_active(cls, planet_name: str) -> bool:
        """Prüft, ob ein Planet existiert und aktiv ist."""
        return cls._is_flag_active(planet_name, PlanetConfigKey.ACTIVE)

    @classmethod
    def is_mainsensor_active(cls, planet_name: str) -> bool:
        """Prüft, ob ein Planet als MainSensor aktiv ist."""
        return cls._is_flag_active(planet_name, PlanetConfigKey.MAIN_SENSOR)

    @classmethod
    def is_statesensors_active(cls, planet_name: str) -> bool:
        """Prüft, ob ein Planet als StateSensor aktiv ist."""
        return cls._is_flag_active(planet_name, PlanetConfigKey.STATE_SENSORS)

    @classmethod
    def _is_flag_active(cls, planet_name: str, flag: str) -> bool:
        """Hilfsmethode: Prüft, ob ein spezifisches Flag für einen Planeten aktiv ist."""
        cls._ensure_initialized()
        # Sicherstellen, dass PLANET_MAP existiert (für den Type-Checker)
        current_map = cls.PLANET_MAP or {}
        # Hol dir die Konfiguration des Planeten (None, falls nicht vorhanden)
        config = current_map.get(planet_name.lower())
        # Wenn config existiert, gib den Wert des Flags zurück (Default: False)
        return bool(config and config.get(flag, False))

    @classmethod
    def set_planet_active(cls, planet_name: str, *, enable: bool) -> None:
        """Aktiviert oder deaktiviert einen Planeten zur Laufzeit."""
        cls._set_flag_active(planet_name, PlanetConfigKey.ACTIVE, value=enable)

    @classmethod
    def set_mainsensor_active(cls, planet_name: str, *, enable: bool) -> None:
        """Aktiviert oder deaktiviert einen MainSensor zur Laufzeit."""
        cls._set_flag_active(planet_name, PlanetConfigKey.MAIN_SENSOR, value=enable)

    @classmethod
    def set_statesensors_active(cls, planet_name: str, *, enable: bool) -> None:
        """Aktiviert oder deaktiviert einen StateSensors zur Laufzeit."""
        cls._set_flag_active(planet_name, PlanetConfigKey.STATE_SENSORS, value=enable)

    @classmethod
    def set_update_interval(cls, planet_name: str, interval: int) -> None:
        """Setzt das Update-Intervall für einen Planeten zur Laufzeit."""
        cls._set_flag_active(planet_name, PlanetConfigKey.UPDATE_INTERVAL, value=interval)

    @classmethod
    def _set_flag_active(cls, planet_name: str, key: str, *, value: Any) -> None:
        """Ändert einen Parameter eines Planeten oder Sensor zur Laufzeit."""
        cls._ensure_initialized()
        # Sicherstellen, dass PLANET_MAP existiert (für den Type-Checker)
        current_map = cls.PLANET_MAP or {}
        name = planet_name.lower()
        if name not in current_map:
            LOGGER.error(ERROR_INVALID_PLANET)
            return
        # Wert setzen
        current_map[name][key] = value

    #
    #
    # hier werden die Planeten Daten zyklisch berechnet
    #
    async def async_get_data(self, planet_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get data from the API."""
        self._calc_data(planet_name)
        return self.planet_phase_data, self.planet_phase_data_icon

    #
    # Unterfunktionen von _calc_data_ethem
    #
    # current time zone
    def _get_zone(self) -> ZoneInfo:
        """Gibt die Zeitzone zurück."""
        return ZoneInfo(self.location_data["timezone"])

    # calculate local time
    def _get_localtime_ephem(self, timefunc: Any) -> datetime:
        """Konvertiert ephem-Zeit in lokale Zeit."""
        return ephem.to_timezone(timefunc, self._get_zone())

    # calculate utc time
    def _get_utctime_ephem(self, timefunc: Any) -> datetime:
        """Konvertiert in UTC Zeit."""
        return ephem.to_timezone(timefunc, ZoneInfo("UTC"))

    # update planet data
    def _update_planetdata(self, key: str, value: Any) -> None:
        """Schreibt Daten in das interne Dictionary."""
        self.planet_phase_data[key] = value

    # update planet data icon
    def _update_planetdata_icon(self, key: str, value: Any) -> None:
        """Schreibt Daten in das interne Dictionary."""
        self.planet_phase_data_icon[key] = value

    # get planet data
    def _get_planetdata(self, key: str) -> Any:
        """Holt Daten aus dem internen Dictionary."""
        return self.planet_phase_data[key]

    def _get_icon_for_any_key(self, planet_name: str, key: PlanetStateKey | str) -> str:
        """Bestimmt das MDI-Icon direkt über den Enum-Key oder einen Fallback."""
        # 1. Theme wählen (kleingeschriebener Name für 'sun', 'moon', etc.)
        theme = ICON_THEMES.get(planet_name.lower(), ICON_THEMES.get("default", {}))

        # 2. Icon aus dem Mapping holen
        # Wir suchen erst nach dem exakten Key, dann nach dem Default des Themes
        icon = theme.get(key) or theme.get("default", "mdi:help-circle")

        # 3. Rückgabe als garantierter String (Linter & Type-Check Fix)
        return str(icon)

    def _update_icon_field(self, event_key: PlanetStateKey, planet_name: str) -> None:
        # Icon bestimmen
        icon = self._get_icon_for_any_key(planet_name, event_key)

        # Dynamisch im Enum nachschlagen und Wert setzen
        if hasattr(PlanetStateKey, event_key.name):
            self._update_planetdata_icon(event_key, icon)

    # init planet data
    def _init_planet_and_data(self, planet_name: str) -> Any:
        # here is my ephem class
        # myplanet = self.planet

        # 1. Fallback auf leeres Dict, falls PLANET_MAP noch None ist
        self._ensure_initialized()
        current_config = self.PLANET_MAP or {}

        # Planetendaten vorbereiten (Kopie um Manipulation zu vermeiden)
        self.planet_phase_data = self.location_data.copy()
        self.planet_phase_data_icon: dict[str, Any] = {}  # Separates Dict für Icons

        # Planet Name merken (für spätere Verwendung in Icon-Logik)
        self.planet_phase_data[PlanetStateKey.PLANET_NAME] = planet_name.lower()
        self.planet_name = planet_name.lower()

        # Planet initialisieren
        planet_info = current_config[planet_name.lower()]
        # Initialisiert die ephem-Klasse
        return planet_info["class"]()

    # hier werden die Planeten Daten zyklisch berechnet
    # die Berechnung basiert auf der ephem-Bibliothek und berücksichtigt die aktuelle Zeit, die Position des Beobachters
    #  und die spezifischen Eigenschaften des Planeten.
    def _calc_data(self, planet_name: str) -> Any:
        """Calc data from the API."""
        myplanet_ephem = self._init_planet_and_data(planet_name)

        # Aktuelle Zeit in der lokalen HA-Zeitzone (Timezone-aware)
        self.measurement_date = dt_util.now()

        # Aktuelle ephem Zeit mit Zeitzone
        self.ephem.observer.date = self.measurement_date
        # Berechnung der Planetenpositionen durchführen (aktualisiert die Attribute des Planeten-Objekts)
        myplanet_ephem.compute(self.ephem.observer)
        # current measurement time
        current_date = ephem.Date(self.ephem.observer.date)

        self._update_planetdata(PlanetStateKey.MEASUREMENT_LOCAL_TIME, self._get_localtime_ephem(current_date))
        self._update_planetdata(PlanetStateKey.MEASUREMENT_UTC_TIME, self._get_utctime_ephem(current_date))

        # 1. Basis-Positionsdaten
        self._update_basic_positions_ephem(myplanet_ephem)

        # 2. Transite und Auf-/Untergänge
        self._update_event_times_ephem(myplanet_ephem)

        # check of ascending or descending
        # 3. Status (Aufsteigend/Absteigend) und Phasen
        self._update_status_and_phase_ephem(myplanet_ephem, current_date)

        # 4. Berechnet Auf-/Untergang und Tageslänge für den heutigen Tag
        self._calc_daily_stats_ephem(myplanet_ephem)

        # 5. Spezielle Sonnen-Daten (nur berechnen, wenn das Objekt die Sonne ist)
        if isinstance(myplanet_ephem, ephem.Sun):
            self._update_astronomical_sun_seasons_ephem()

        if isinstance(myplanet_ephem, ephem.Moon):
            self._update_moon_phase_direction(current_date)

    def _update_basic_positions_ephem(self, myplanet: Any) -> None:
        # Calculate Planet Altitude
        self._update_planetdata(PlanetStateKey.ALTITUDE, (myplanet.alt / ephem.degree))
        self._update_icon_field(PlanetStateKey.ALTITUDE, self.planet_name)
        # Calculate Planet Azimuth
        self._update_planetdata(PlanetStateKey.AZIMUTH, (myplanet.az / ephem.degree))
        self._update_icon_field(PlanetStateKey.AZIMUTH, self.planet_name)
        # Calculate current Planet - Earth distance
        self._update_planetdata(PlanetStateKey.DISTANCE, myplanet.earth_distance * ephem.meters_per_au)
        # Calculate Planet Hour Angle
        self._update_planetdata(PlanetStateKey.HOUR_ANGLE, (myplanet.ha / ephem.degree))
        # Calculate Planet Iillumination
        self._update_planetdata(PlanetStateKey.Iillumination, myplanet.phase)

    def _update_event_times_ephem(self, myplanet: Any) -> None:
        """Berechnet Auf-/Untergangszeiten mit Fehlerbehandlung (Polartage)."""
        # Lokale Kopien erstellen
        temp_planet = copy.copy(myplanet)  # Planet kopieren
        temp_obs = copy.copy(self.ephem.observer)

        for event in [
            PlanetStateKey.NEXT_TRANSIT,
            PlanetStateKey.NEXT_ANTITRANSIT,
            PlanetStateKey.PREVIOUS_RISING,
            PlanetStateKey.PREVIOUS_SETTING,
            PlanetStateKey.NEXT_RISING,
            PlanetStateKey.NEXT_SETTING,
        ]:
            # Icon bestimmen
            self._update_icon_field(event, self.planet_name)

            try:
                res = getattr(temp_obs, event)(temp_planet)
                self._update_planetdata(event, self._get_localtime_ephem(res))
            except ephem.NeverUpError, ephem.AlwaysUpError:
                self._update_planetdata(event, None)

    def _get_current_sun_phase(self, altitude_deg: float, is_rising: Any) -> str:
        # 1. Basis-Phase über Schwellenwerte finden
        base_phase = PHASE_NIGHT
        for limit, phase in sun_thresholds:
            if altitude_deg >= limit:
                base_phase = phase
                break

        # 2. Ausnahmen für Tag und Nacht (kein Präfix)
        if base_phase in [PHASE_DAY, PHASE_NIGHT]:
            return sun_phases[base_phase]["name"]

        # 3. Präfix für Dämmerungsphasen bestimmen
        direction = "MORNING" if is_rising else "EVENING"
        phase_key = f"{direction}_{base_phase}"

        return sun_phases[phase_key]["name"]

    def _update_status_and_phase_ephem(self, myplanet: Any, current_date: Any) -> None:
        """Berechnet, ob der Planet steigt und in welcher Phase er ist."""
        # Lokale Kopien erstellen
        temp_planet = copy.copy(myplanet)  # Planet kopieren
        temp_obs = copy.copy(self.ephem.observer)

        alt1 = temp_planet.alt
        temp_obs.date = ephem.Date(current_date + ephem.minute)
        temp_planet.compute(temp_obs)
        ascending = temp_planet.alt > alt1

        self._update_planetdata(PlanetStateKey.MAIN_MOVE, STAR_ASCENDING if ascending else STAR_DESCENDING)

        # Phase und Icon
        altitude_deg = alt1 / ephem.degree
        selected_phase = STAR_ABOVE_HORIZON if altitude_deg > 0 else STAR_BELOW_HORIZON
        self._update_planetdata(PlanetStateKey.MAIN_STATE, selected_phase)
        direction = "up" if ascending else "down"
        iconkey = f"{selected_phase}_{direction}"
        self._update_planetdata_icon(PlanetStateKey.MAIN_STATE, self._get_icon_for_any_key(self.planet_name, iconkey))

        if isinstance(myplanet, ephem.Sun):
            current_phase = self._get_current_sun_phase(altitude_deg, ascending)
            self._update_planetdata(PlanetStateKey.PHASE, current_phase)
            self._update_planetdata_icon(PlanetStateKey.PHASE, self._get_icon_for_any_key(self.planet_name, iconkey))

    def _calc_daily_stats_ephem(self, myplanet: Any) -> None:
        """Berechnet Auf-/Untergang und Tageslänge für den heutigen Tag."""
        # Lokale Kopien erstellen
        temp_planet = copy.copy(myplanet)  # Planet kopieren
        temp_obs = copy.copy(self.ephem.observer)

        # 1. Start des heutigen Tages in lokaler Zeit finden
        now_local = dt_util.now()
        today_midnight = dt_util.start_of_local_day(now_local)

        # Observer auf Mitternacht setzen (ephem erwartet UTC)
        temp_obs.date = ephem.Date(today_midnight)

        try:
            # Nächsten Aufgang ab Mitternacht finden
            rise = temp_obs.next_rising(temp_planet)
            # Den DAZUGEHÖRIGEN Untergang finden (start=rise ist entscheidend!)
            setting = temp_obs.next_setting(temp_planet, start=rise)

            # Daten speichern
            self._update_planetdata(PlanetStateKey.TODAY_RISING, self._get_localtime_ephem(rise))
            self._update_icon_field(PlanetStateKey.TODAY_RISING, self.planet_name)
            self._update_planetdata(PlanetStateKey.TODAY_SETTING, self._get_localtime_ephem(setting))
            self._update_icon_field(PlanetStateKey.TODAY_SETTING, self.planet_name)

            # Tageslänge berechnen: ephem-Differenz ist in Tagen -> * 86400 für Sekunden
            daydiff_seconds = (setting - rise) * 86400
            self._update_planetdata(
                PlanetStateKey.TODAY_ABOVE_HORIZON_TIME,
                str(timedelta(seconds=int(daydiff_seconds))),
            )
            self._update_icon_field(PlanetStateKey.TODAY_ABOVE_HORIZON_TIME, self.planet_name)

        except ephem.NeverUpError, ephem.AlwaysUpError:
            # Fallback für Polartage/nächte
            self._update_planetdata(PlanetStateKey.TODAY_RISING, "N/A")
            self._update_planetdata(PlanetStateKey.TODAY_SETTING, "N/A")
            self._update_planetdata(PlanetStateKey.TODAY_ABOVE_HORIZON_TIME, "00:00:00")

    def _update_astronomical_sun_seasons_ephem(self) -> None:
        """Berechnet Äquinoktien und Sonnenwenden."""
        # Lokale Kopien erstellen
        obs_date = self.ephem.observer.date

        self._update_planetdata(
            PlanetStateKey.NEXT_VERNAL_EQUINOX,
            self._get_localtime_ephem(ephem.next_vernal_equinox(obs_date)),
        )
        self._update_icon_field(PlanetStateKey.NEXT_VERNAL_EQUINOX, self.planet_name)
        self._update_planetdata(
            PlanetStateKey.NEXT_SUMMER_SOLSTICE,
            self._get_localtime_ephem(ephem.next_summer_solstice(obs_date)),
        )
        self._update_icon_field(PlanetStateKey.NEXT_SUMMER_SOLSTICE, self.planet_name)
        self._update_planetdata(
            PlanetStateKey.NEXT_AUTUMNAL_EQUINOX,
            self._get_localtime_ephem(ephem.next_autumnal_equinox(obs_date)),
        )
        self._update_icon_field(PlanetStateKey.NEXT_AUTUMNAL_EQUINOX, self.planet_name)
        self._update_planetdata(
            PlanetStateKey.NEXT_WINTER_SOLSTICE,
            self._get_localtime_ephem(ephem.next_winter_solstice(obs_date)),
        )
        self._update_icon_field(PlanetStateKey.NEXT_WINTER_SOLSTICE, self.planet_name)

    def _update_moon_phase_direction(self, current_date: Any = None) -> None:
        obs_date = current_date

        # Zeitpunkte der nächsten Hauptphasen
        next_full = ephem.next_full_moon(obs_date)
        next_new = ephem.next_new_moon(obs_date)

        # Richtung bestimmen
        is_waxing = next_full < next_new
        mstate = moon_states["WAXING"] if is_waxing else moon_states["WANING"]

        # Mond-Objekt für Beleuchtung laden
        m = ephem.Moon()
        m.compute(obs_date)
        p = m.phase  # 0 bis 100

        # p = Beleuchtung in % (0-100)
        # is_waxing = True (zunehmend), False (abnehmend)
        if p < THRESHOLD_NEW:
            key = "MOON_NEW_MOON"
        elif p > THRESHOLD_FULL:
            key = "MOON_FULL_MOON"
        elif QUARTER_LOW <= p <= QUARTER_HIGH:
            key = "MOON_FIRST_QUARTER" if is_waxing else "MOON_LAST_QUARTER"
        elif is_waxing:
            key = "MOON_WAXING_CRESCENT" if p < HALF_MARK else "MOON_WAXING_GIBBOUS"
        else:
            key = "MOON_WANING_GIBBOUS" if p > HALF_MARK else "MOON_WANING_CRESCENT"

        self._update_planetdata(PlanetStateKey.PHASE, moon_phases[key]["name"])
        ###self._update_planetdata(PlanetStateKey.MOON_ICON, moon_phases[key]["icon"])
        self._update_planetdata_icon(PlanetStateKey.PHASE, moon_phases[key]["icon"])
        self._update_planetdata(PlanetStateKey.STATE, mstate)
        self._update_planetdata(PlanetStateKey.MOON_NEXT_FULLMOON, self._get_localtime_ephem(next_full))
        self._update_icon_field(PlanetStateKey.MOON_NEXT_FULLMOON, self.planet_name)
        self._update_planetdata(PlanetStateKey.MOON_NEXT_NEWMOON, self._get_localtime_ephem(next_new))
        self._update_icon_field(PlanetStateKey.MOON_NEXT_NEWMOON, self.planet_name)
