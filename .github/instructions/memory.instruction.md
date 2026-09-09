---
applyTo: '**'
---

# AddiSlice Agent Memory

## Project Overview
- **AddiSlice**: Cura fork (v5.9.12) by AddiPrint for their 3D printers
- **Repository**: `C:\Users\VijayRaghavVarada\Documents\Github\AddiSlice`
- **Branch**: AddiSlice-5.9

## Key Documentation
- `docs/agents.md` — Comprehensive AI agent guide for printer creation and management (includes Quality Profile System, Material System, Start/End GCode, Common Pitfalls)
- `scripts/generate_start_gcode.py` — Reusable start/end gcode expression builder

## Printers Created
- **Penrose 600 IDEX** (pellet extruder, barrel heater, IDEX dual)
  - Definition: `resources/definitions/penrose_600_idex.def.json`
  - Quality Definition: `resources/definitions/penrose_pellet_quality.def.json`
  - Extruders: `resources/extruders/penrose_600_idex_extruder_0.def.json`, `_1.def.json`
  - Variants: `resources/variants/addiprint/Penrose 600 IDEX/` (0.6, 0.8, 1.0, 1.5, 2.0, 3.0mm)
  - Quality Profiles: `resources/quality/penrose_pellet_quality/` (82 files: 10 globals + 72 variant+material stubs)
  - Pellet Materials: `resources/materials/AddiPrint Pellet/` (4 files: PLA, ABS, TPU 95A, Nylon)
  - Preferred defaults: nozzle=0.6mm, material=addiprint_pla_pellet, quality_type=pellet_030
- **Penrose 600** (pellet extruder, barrel heater, single extruder)
  - Definition: `resources/definitions/penrose_600.def.json`

## Quality Profile System
- **Resolution chain**: MachineNode → VariantNode → MaterialNode → QualityNode (see `docs/agents.md` for full details)
- **quality_definition**: `penrose_pellet_quality` (used as namespace for quality searches)
- **Global profiles** (10): Define layer_height, require `global_quality = True`
- **Variant+material stubs** (72): Control availability per nozzle+material, require `material` metadata field
- **Nozzle subsets**: Each nozzle has 3 quality types (e.g., 0.6mm → pellet_020/030/050)
- **Availability intersection**: If variant/material lookup fails → ALL global types shown (no filtering)
- **Quality types**: pellet_020, pellet_030, pellet_040, pellet_050, pellet_060, pellet_080, pellet_100, pellet_120, pellet_160, pellet_240

## Material System
- **Pellet materials**: `addiprint_pla_pellet`, `addiprint_abs_pellet`, `addiprint_tpu95a_pellet`, `addiprint_nylon_pellet`
- **exclude_materials**: `["_175", "generic_"]` — substring match blocks filament and generic materials
- **Material XML location**: `resources/materials/AddiPrint Pellet/`
- **Quality stubs** reference these via `material` metadata (must match base_file of material XML)

## Custom Settings Added to fdmprinter.def.json
- `machine_barrel_heater` bool (machine_settings, after machine_ring_heater)
- `default_material_barrel_temperature` (hidden, material section, after ring_heater_power)
- `material_barrel_temperature` (visible, 70% nozzle temp formula, max 480)
- `material_barrel_temperature_layer_0` (first layer override)
- XML mapping: `"barrel temperature"` -> `"default_material_barrel_temperature"` in XmlMaterialProfile.py

## Pellet Extrusion Optimization (Penrose 600 IDEX)
Settings tuned for screw-based pellet extrusion (25 overrides in penrose_600_idex.def.json):
- **Retraction**: enabled at 2mm / 50mm/s (both retract and prime) — small pressure relief, not full retract
- **Coasting**: enabled, volume = nozzle³ × 1.5, speed 80%, min_volume = coasting_volume × 10
- **Bridge**: wall_coast=100%, wall/skin flow reduced 20% (material_flow * 0.80)
- **Speed uniformity**: wall/topbottom at 90% of print_speed (vs filament 75-80%) to reduce screw flow fluctuation
- **Combing**: all + max_distance=0 (unlimited combing, never trigger retraction during combing)
- **Travel**: avoid_supports=true, avoid_distance = nozzle × 1.5
- **Cooling**: min_layer_time=10s, min_speed=max(15, print*0.25)
- **Flow acceleration**: reduced ~50% vs filament (screw inertia)
- **Z-seam**: corner=inner (hide ooze blobs at inner corners)
- **Wipe**: wall_0_wipe_dist = nozzle × 2 (Dyze Pulsar: "at least line width")
- **Mesh tolerance**: scales with nozzle size (deviation=nozzle*0.04, resolution=nozzle*0.8)
- **IDEX dual**: prime_tower_size=40 (up from 30), switch_extruder_extra_prime=nozzle×3
- Sources: Dyze Design Pulsar docs, 3DMag pellet guide, CNC Kitchen extrusion width study

## Key Patterns
- IDEX start gcode uses `"value"` (Python expression) with `print_mode` conditionals
- Single extruder start gcode uses `"default_value"` (plain string with replacement tags)
- Barrel heater temp formula: `default_material_barrel_temperature if default_material_barrel_temperature > 0 else max(round(material_print_temperature * 0.7), 120)`
- Always disable temp prepend when providing custom start gcode
- Mirror/duplication modes use T0's temperature for both extruders
- **Pellet IDEX purge order**: Homing → G29 → per-tool off-bed purge → {print_mode_gcode}
  - `{print_mode_gcode}` MUST come AFTER purge (mirror/dup link carriages, preventing independent purge)
- **IDEX purge positions** (from Klipper config, stepper_y position_min: -10, 5mm safety margin):
  - T0: X=-20 Y=-5 (off-bed left, front edge, 5mm margin from Y min)
  - T1: X=620 Y=-5 (off-bed right, front edge, 5mm margin from Y min)
  - 1000mm extrusion per tool (4 phases: 150+200+300+350mm at varied speeds)
  - 140mm Y travel during purge (Y=-5 to Y=135)
- **Klipper axis limits**: X T0 [-85,600], X T1 [0,640], Y [-10,605], Z [0,625]
- **Klipper firmware configs**: `AddiPrint/PenroseControlCenter` repo, `octoprint_PenroseControlCenter/firmware/`
  - `PRINTER_PENROSE_600.cfg` — IDEX config, PRINTER_VARIABLES (purge positions, bed size, fan names)
  - `CORE_GCODE_MACROS.cfg` — Marlin-compatible G-codes (M104, M109, M218, M500, etc.)
  - `BASE_PENROSE.cfg` — Common hardware (steppers, MCU pins, heaters)

## User Preferences
- Prefers comprehensive documentation
- Wants reusable tooling (scripts) for repeatable tasks
- Values validation and testing of generated code
