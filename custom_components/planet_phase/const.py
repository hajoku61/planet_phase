"""Constants for planet_phase."""

from enum import StrEnum
from logging import Logger
from logging import getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "planet_phase"

DEFAULT_NAME = "Planet Phase"

# in seconds
UPDATE_INTERVAL = 60 * 15


class PlanetStateKey(StrEnum):
    """Erweiterte Klasse zur Beschreibung von Planeten-Phasen und Icons."""

    MAIN_STATE = "main_state"
    MAIN_MOVE = "main_move"

    PLANET_NAME = "planet_name"  # Neu: Name des Planeten für Icon-Logik

    # Rising / Setting
    TODAY_RISING = "today_rising"
    TODAY_SETTING = "today_setting"

    NEXT_RISING = "next_rising"
    NEXT_SETTING = "next_setting"

    PREVIOUS_RISING = "previous_rising"
    PREVIOUS_SETTING = "previous_setting"

    # Transit / Horizon
    NEXT_TRANSIT = "next_transit"
    NEXT_ANTITRANSIT = "next_antitransit"

    TODAY_ABOVE_HORIZON_TIME = "today_above_horizon_time"

    # Measurement & Position
    MEASUREMENT_LOCAL_TIME = "measurement_local_time"
    MEASUREMENT_UTC_TIME = "measurement_utc_time"
    ALTITUDE = "altitude"
    AZIMUTH = "azimuth"
    HOUR_ANGLE = "hour_angle"
    DISTANCE = "distance"
    Iillumination = "illumination"

    # Sun Seasons
    NEXT_VERNAL_EQUINOX = "next_vernal_equinox"
    NEXT_SUMMER_SOLSTICE = "next_summer_solstice"
    NEXT_AUTUMNAL_EQUINOX = "next_autumnal_equinox"
    NEXT_WINTER_SOLSTICE = "next_winter_solstice"

    # Sun / Moon Specific
    STATE = "state"
    PHASE = "phase"

    # Moon Specific
    MOON_NEXT_NEWMOON = "next_new_moon"
    MOON_NEXT_FULLMOON = "next_full_moon"

    UNKNOWN = "unknown_key"


class PlanetConfigKey(StrEnum):
    """Klasse zur Beschreibung von Planeten-Konfigurationen."""

    ACTIVE = "active"
    MAIN_SENSOR = "MainSensor"
    STATE_SENSORS = "StateSensors"
    UPDATE_INTERVAL = "UpdateInterval"
