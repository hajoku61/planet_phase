"""Test sensor for simple integration."""

import pytest

from custom_components.planet_phase.api import ICON_THEMES
from custom_components.planet_phase.api import moon_phases
from custom_components.planet_phase.const import PlanetStateKey


def get_icon(planet: str, key: str, state_value: str | None = None) -> str:
    """Repliziert die Logik der Icon-Zuweisung für Tests."""
    # 1. Mondphasen-Speziallogik
    if key == PlanetStateKey.PHASE and state_value in moon_phases:
        return moon_phases[state_value]["icon"]
    # 2. Theme-Logik
    theme = ICON_THEMES.get(planet.lower(), ICON_THEMES["default"])
    # 3. Key-Suche mit Fallback-Kette
    return theme.get(key, theme.get("default", ICON_THEMES["default"]["default"]))


# --- PYTEST TESTCASES ---


@pytest.mark.parametrize(
    ("planet", "key", "state", "expected"),
    [
        ("sun", PlanetStateKey.TODAY_RISING, None, "mdi:weather-sunset-up"),  # Korrektes Mapping
        ("sun", PlanetStateKey.UNKNOWN, None, "mdi:weather-sunny"),  # Sun Fallback
        ("moon", PlanetStateKey.PHASE, "MOON_NEW_MOON", "mdi:moon-new"),  # Mondphase Dynamisch
        ("moon", PlanetStateKey.ALTITUDE, None, "mdi:angle-acute"),  # Moon Fallback
        ("mars", PlanetStateKey.TODAY_RISING, None, "mdi:star-check-outline"),  # Globaler Fallback
    ],
)
def test_icon_logic(planet: str, key: str, state: str, expected: str) -> None:
    """Prüft die Kernlogik der Icon-Zuweisung."""
    assert get_icon(planet, key, state) == expected


def test_mdi_prefix_validation() -> None:
    """Validiert, dass JEDES definierte Icon mit 'mdi:' beginnt."""
    # Sammle alle Icons aus allen Datenstrukturen
    all_icons = []
    for theme in ICON_THEMES.values():
        all_icons.extend(theme.values())
    all_icons.extend(phase["icon"] for phase in moon_phases.values())

    for icon in all_icons:
        assert icon.startswith("mdi:"), f"Icon '{icon}' hat kein gültiges MDI-Präfix!"


def test_theme_consistency() -> None:
    """Prüft, ob die Pflicht-Themes vorhanden sind."""
    assert "sun" in ICON_THEMES
    assert "moon" in ICON_THEMES
    assert "default" in ICON_THEMES


@pytest.mark.parametrize("phase_key", moon_phases.keys())
def test_all_moon_phases_have_icons(phase_key: str) -> None:
    """Stellt sicher, dass jede definierte Mondphase ein MDI-Icon hat."""
    icon = moon_phases[phase_key]["icon"]
    assert icon.startswith("mdi:")
    assert len(icon) > 4  # noqa: PLR2004


# Testet JEDEN Enum-Key für Sonne und Mond
@pytest.mark.parametrize("planet", ["sun", "moon"])
@pytest.mark.parametrize("key", list(PlanetStateKey))
def test_all_enum_keys_have_icons(planet: str, key: str) -> None:
    """Prüft, ob alle Enum-Keys ein Icon zurückliefern und dass es korrekt formatiert ist."""
    icon = get_icon(planet, key)
    assert icon.startswith("mdi:"), f"Fehler bei {planet} - {key}: {icon}"
    # Wir prüfen, ob es nicht der absolute Notfall-Fallback ist,
    # außer es ist ein Key, den wir absichtlich nicht definiert haben.
    if key not in [PlanetStateKey.MAIN_STATE, PlanetStateKey.PLANET_NAME]:
        assert icon != "mdi:star-outline" or planet == "default", f"Key {key} nutzt globalen Fallback!"


# Testet die Spezial-Strings für den Horizont-Status
@pytest.mark.parametrize("horizon_key", ["above_horizon_up", "above_horizon_down", "below_horizon_up", "below_horizon_down"])
def test_horizon_special_icons(horizon_key: str) -> None:
    """Prüft, ob alle Spezial-Icons für den Horizont-Status definiert sind und korrekt zugeordnet werden."""
    for p in ["sun", "moon", "default"]:
        icon = ICON_THEMES[p].get(horizon_key)
        assert icon is not None, f"Spezial-Key {horizon_key} fehlt in {p}"
        assert icon.startswith("mdi:")


@pytest.mark.parametrize("theme_name", ["sun", "moon", "default"])
def test_theme_completeness(theme_name: str) -> None:
    """Prüft, ob alle kritischen Keys in jedem Theme vorhanden sind."""
    theme = ICON_THEMES[theme_name]
    required_keys = [PlanetStateKey.DISTANCE, PlanetStateKey.NEXT_ANTITRANSIT, PlanetStateKey.MEASUREMENT_LOCAL_TIME, "above_horizon_up", "default"]
    for key in required_keys:
        assert key in theme, f"Key '{key}' fehlt im Theme '{theme_name}'!"


def test_mdi_format() -> None:
    """Prüft alle Icons auf das korrekte mdi: Präfix."""
    for theme in ICON_THEMES.values():
        for icon in theme.values():
            assert icon.startswith("mdi:"), f"Ungültiges Icon-Format: {icon}"


@pytest.mark.parametrize(
    ("planet", "key", "expected"),
    [
        ("sun", PlanetStateKey.TODAY_RISING, "mdi:weather-sunset-up"),
        ("sun", PlanetStateKey.NEXT_TRANSIT, "mdi:sun-clock"),
        ("sun", PlanetStateKey.DISTANCE, "mdi:map-marker-distance"),
        ("moon", PlanetStateKey.MOON_NEXT_NEWMOON, "mdi:moon-new"),
        ("moon", PlanetStateKey.NEXT_ANTITRANSIT, "mdi:minus-circle-outline"),
        ("mars", PlanetStateKey.TODAY_RISING, "mdi:star-check-outline"),  # Fallback
    ],
)
def test_static_icon_mapping(planet: str, key: str, expected: str) -> None:
    """Prüft das Mapping von vordefinierten Keys."""
    assert get_icon(planet, key) == expected


@pytest.mark.parametrize(("phase_key", "expected_icon"), [(k, v["icon"]) for k, v in moon_phases.items()])
def test_dynamic_moon_phases(phase_key: str, expected_icon: str) -> None:
    """Prüft alle 8 dynamischen Mondphasen-Icons."""
    assert get_icon("moon", PlanetStateKey.PHASE, phase_key) == expected_icon


@pytest.mark.parametrize(
    ("planet", "horizon_key"),
    [
        ("sun", "above_horizon_up"),
        ("sun", "below_horizon_up"),
        ("moon", "below_horizon_down"),
    ],
)
def test_special_horizon_keys(planet: str, horizon_key: str) -> None:
    """Prüft die Spezial-Keys für den Horizont-Status."""
    icon = get_icon(planet, horizon_key)
    assert icon.startswith("mdi:")
    assert icon == ICON_THEMES[planet][horizon_key]


def test_mdi_prefix_on_all_icons() -> None:
    """Stellt sicher, dass kein Icon den mdi: Präfix vergessen hat."""
    for theme in ICON_THEMES.values():
        for icon in theme.values():
            assert icon.startswith("mdi:")


def test_default_fallbacks() -> None:
    """Prüft, ob nicht definierte Keys sauber auf den Planeten-Default fallen."""
    # 'unknown' ist nicht in 'sun' definiert, sollte 'default' von 'sun' liefern
    assert get_icon("sun", "unknown") == "mdi:weather-sunny"
    # Planet 'jupiter' existiert nicht, sollte globalen 'star-check-outline' liefern
    assert get_icon("jupiter", PlanetStateKey.TODAY_RISING) == "mdi:star-check-outline"
