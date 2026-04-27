"""Test sensor for simple integration."""

from typing import TYPE_CHECKING
from unittest.mock import patch

from homeassistant import data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.planet_phase.const import DOMAIN
from custom_components.planet_phase.const import PlanetConfigKey

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from syrupy.assertion import SnapshotAssertion


def flow_result_to_dict(result: dict) -> dict:
    """Konvertiert Flow-Resultate so, dass sie für Snapshots stabil sind."""
    if not result or "data_schema" not in result or result["data_schema"] is None:
        return result

    clean_result = dict(result)
    schema = result["data_schema"].schema
    serializable_schema = {}

    for key, value in schema.items():
        # Extrahiert den Key-Namen (behandelt vol.Required/vol.Optional)
        key_name = str(key.schema if hasattr(key, "schema") else key)

        # Selektoren in Dicts umwandeln, sonst String-Repräsentation ohne Speicheradresse
        if hasattr(value, "as_dict"):
            serializable_schema[key_name] = value.as_dict()
        else:
            # Falls es kein Selector ist, nehmen wir den Typnamen statt der Instanz mit Adresse
            serializable_schema[key_name] = value.__class__.__name__

    clean_result["data_schema"] = serializable_schema
    return clean_result


async def test_full_config_flow(hass: HomeAssistant, snapshot: SnapshotAssertion) -> None:
    """Testet den kompletten Flow von der Auswahl bis zum Erstellen des Entries."""
    # 1. Schritt: User Step (Planeten auswählen)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    # Snapshot prüft das Planeten-Auswahl-Schema
    # assert result == snapshot(name="user_form")
    assert flow_result_to_dict(result) == snapshot(name="user_form")

    # 2. Schritt: Planeten auswählen (z.B. Mars & Venus)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"active_planets": ["sun", "moon", "mars", "venus"]},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "configure_sensors"
    # Snapshot prüft das dynamisch generierte Sensor-Schema für Mars & Venus
    # assert result == snapshot(name="sensor_config_form")
    assert flow_result_to_dict(result) == snapshot(name="sensor_config_form")

    # 3. Schritt: Sensoren konfigurieren & Entry erstellen
    with patch("custom_components.planet_phase.async_setup_entry", return_value=True) as mock_setup:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "mars_sensors": ["main", "state"],
                "mars_update_interval": 60,
                "venus_sensors": ["main"],
                "venus_update_interval": 300,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    # Das 'data'-Feld enthält nun das Resultat von ConfigBuilder.build_final_config
    assert result["data"] == snapshot(name="final_config_data")

    assert len(mock_setup.mock_calls) == 1


async def test_reconfigure_flow(hass: HomeAssistant, snapshot: SnapshotAssertion) -> None:
    """Testet den Reconfigure Flow."""
    # 1. Setup: Bestehender Entry mit validen Daten
    entry = MockConfigEntry(domain=DOMAIN, data={"mars": {PlanetConfigKey.ACTIVE: True, PlanetConfigKey.UPDATE_INTERVAL: 60}}, unique_id="123")
    entry.add_to_hass(hass)

    # 2. Init Reconfigure
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id})

    assert result["step_id"] == "reconfigure"
    assert flow_result_to_dict(result) == snapshot(name="reconfigure_form")

    # 3. Planeten-Auswahl ändern (Jupiter statt Mars)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"active_planets": ["jupiter"]},
    )

    # Da dein SchemaBuilder danach den Sensor-Step vorsieht:
    assert result["step_id"] == "configure_sensors"

    # 4. Sensoren für Jupiter konfigurieren
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "jupiter_sensors": ["main"],
            "jupiter_update_interval": 120,
        },
    )

    # 5. Abschluss prüfen
    # Bei Reconfigure ist der Typ meist ABORT (mit reconfigure_successful)
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    # Jetzt sind die Daten im Entry aktualisiert
    assert entry.data["jupiter"][PlanetConfigKey.UPDATE_INTERVAL] == 120  # noqa: PLR2004
    # Mars sollte nun nicht mehr aktiv sein (je nach deiner build_final_config Logik)
    assert "mars" not in entry.data or not entry.data["mars"].get(PlanetConfigKey.ACTIVE)


async def test_reconfigure_flow_success(hass: HomeAssistant, snapshot: SnapshotAssertion) -> None:  # noqa: ARG001
    """Testet den kompletten Reconfigure Flow bis zum Speichern."""
    # Start-Konfiguration
    old_data = {"mars": {PlanetConfigKey.ACTIVE: True, PlanetConfigKey.MAIN_SENSOR: True}}
    entry = MockConfigEntry(domain=DOMAIN, data=old_data, unique_id="planet_123")
    entry.add_to_hass(hass)

    # Init Reconfigure
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id})

    # 1. Planeten-Auswahl ändern (Mars weg, Venus her)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"active_planets": ["venus"]},
    )

    # 2. Sensoren für Venus konfigurieren
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "venus_sensors": ["main", "state"],
            "venus_update_interval": 120,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    # Prüfen, ob die Daten im Entry wirklich aktualisiert wurden
    assert entry.data["venus"][PlanetConfigKey.UPDATE_INTERVAL] == 120  # noqa: PLR2004
    assert "mars" not in entry.data or not entry.data["mars"][PlanetConfigKey.ACTIVE]
