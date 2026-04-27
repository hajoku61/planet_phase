"""Fixtures for testing."""

from typing import TYPE_CHECKING

import pytest
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations) -> None:  # noqa: ANN001, ARG001
    """Aktiviert Custom Integrations automatisch für alle Tests."""
    return
