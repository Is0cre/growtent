# Growtent Monorepo 🌱

This repo contains all Raspberry Pi grow tent automation projects.

## Structure
- **controller/** – Original modular Python controller (GPIO, BME680, logging, automation)
- **flask-app/** – Flask web UI + RPi HQ camera timelapse
- **tent-cli/** – Terminal dashboard version
- **systemd/** – Unit files to run services
- **scripts/** – Deploy/maintenance scripts
- **docs/** – Documentation & guides
- **hardware/** – Schematics, wiring, BOM
- **configs/** – Environment configs

## Usage
Clone and explore:
```bash
git clone git@github.com:Is0cre/growtent.git
cd growtent
