# Planet Phase

[![GitHub release](https://img.shields.io/github/v/release/hajoku61/planet_phase.svg)](https://github.com/hajoku61/planet_phase/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub stars](https://img.shields.io/github/stars/hajoku61/planet_phase.svg?style=social)](https://github.com/hajoku61/planet_phase/stargazers)
[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](
  https://my.home-assistant.io/redirect/hacs_repository/?owner=hajoku61&repository=planet_phase&category=integration
)


**Planet Phase** A custom integration to display the current phase of the planets in the solar system. The focus is on the Sun and the Moon.

## Available Planets

- sun
- moon
- mars
- venus
- jupiter
- saturn
- uranus
- mercury
- neptune
- pluto

## Features

- Adjustable query time for each planet.
- Main sensor query only with attributes.
- Special individual sensors.


## Installation

### Install via HACS

Click below to open the repository in HACS:

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hajoku61&repository=planet_phase&category=integration)

### Manual Installation

Copy the integration into your Home Assistant `custom_components` directory:

```text
config/
└── custom_components/
    └── planet_phase/
Then restart Home Assistant.
```

### After Installation

```text
Restart Home Assistant
Go to Settings → Devices & Services
Click Add Integration
Search for "Planet Phase"
Follow the setup flow in the UI
```
