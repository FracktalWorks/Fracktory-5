---
applyTo: '**'
---

# Fracktory-5 Agent Memory

## Project Overview
- **Fracktory-5**: Cura fork (v5.9.11) by Fracktal Works for their 3D printers
- **Repository**: `C:\Users\VijayRaghavVarada\Documents\Github\Fracktory-5`
- **Branch**: Fracktory-5.9

## Key Documentation
- `docs/agents.md` — Comprehensive AI agent guide for printer creation and management
- `scripts/generate_start_gcode.py` — Reusable start/end gcode expression builder

## Printers Created
- **Penrose 600 IDEX** (pellet extruder, barrel heater, IDEX dual)
  - Definition: `resources/definitions/penrose_600_idex.def.json`
  - Extruders: `resources/extruders/penrose_600_idex_extruder_0.def.json`, `_1.def.json`
  - Variants: `resources/variants/fracktalworks/Penrose 600 IDEX/` (0.6, 0.8, 1.0, 1.5, 2.0, 3.0mm)
- **Penrose 600** (pellet extruder, barrel heater, single extruder)
  - Definition: `resources/definitions/penrose_600.def.json`

## Custom Settings Added to fdmprinter.def.json
- `machine_barrel_heater` bool (machine_settings, after machine_ring_heater)
- `default_material_barrel_temperature` (hidden, material section, after ring_heater_power)
- `material_barrel_temperature` (visible, 70% nozzle temp formula, max 480)
- `material_barrel_temperature_layer_0` (first layer override)
- XML mapping: `"barrel temperature"` -> `"default_material_barrel_temperature"` in XmlMaterialProfile.py

## Key Patterns
- IDEX start gcode uses `"value"` (Python expression) with `print_mode` conditionals
- Single extruder start gcode uses `"default_value"` (plain string with replacement tags)
- Barrel heater temp formula: `default_material_barrel_temperature if default_material_barrel_temperature > 0 else max(round(material_print_temperature * 0.7), 120)`
- Always disable temp prepend when providing custom start gcode
- Mirror/duplication modes use T0's temperature for both extruders
- **Pellet IDEX purge order**: Homing → G29 → per-tool off-bed purge → {print_mode_gcode}
  - `{print_mode_gcode}` MUST come AFTER purge (mirror/dup link carriages, preventing independent purge)
- **IDEX purge positions** (from Klipper config, stepper_y position_min: -10):
  - T0: X=-20 Y=-10 (off-bed left, front edge)
  - T1: X=620 Y=-10 (off-bed right, front edge)
  - 220mm extrusion per tool (4 phases: 50+50+60+60mm)
- **Klipper firmware configs**: `FracktalWorks/PenroseControlCenter` repo, `octoprint_PenroseControlCenter/firmware/`
  - `PRINTER_PENROSE_600.cfg` — IDEX config, PRINTER_VARIABLES (purge positions, bed size, fan names)
  - `CORE_GCODE_MACROS.cfg` — Marlin-compatible G-codes (M104, M109, M218, M500, etc.)
  - `BASE_PENROSE.cfg` — Common hardware (steppers, MCU pins, heaters)

## User Preferences
- Prefers comprehensive documentation
- Wants reusable tooling (scripts) for repeatable tasks
- Values validation and testing of generated code
