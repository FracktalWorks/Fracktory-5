---
name: printer-configuration
description: Fleet-wide runbook for configuring Fracktal printers in Fracktory-5 — printers, settings, nozzle variants, quality profiles, materials, intents, and how settings surface in the frontend UI. Use when editing anything under resources/ (definitions, extruders, variants, quality, materials, intent, setting_visibility) for any printer (Julia, Dragon, Twin Dragon, Volterra, Snowflake, Penrose pellet), or when adding/changing a setting and verifying how it displays.
---

# Printer Configuration (all Fracktal printers)

Internal skill. Deep reference: `docs/agents.md` (read the relevant section
before editing). This is the operational path.

## Architecture in 30 seconds

- Inheritance: `fdmprinter` → `base_fracktal_printer` (single) →
  `base_fracktal_dual_printer` → `base_fracktal_idex_printer`; leaf printer
  defs are thin (build volume, feedrates, names). Bases carry the tuning
  philosophy. Override as close to the leaf as possible.
- Two quality namespaces: `base_fracktal_printer` (all filament printers,
  variants "Model X.X mm", global types micro/high/normal/low/coarse/…)
  and `penrose_pellet_quality` (Penrose 600 + IDEX, variants "Pellet X.X mm",
  types `pellet_020`…`pellet_240`).
- Value resolution per stack (cura/Settings/CuraContainerStack.py:406):
  User → QualityChanges → Intent → Quality → Material → Variant →
  DefinitionChanges → Definition. `resolve` collapses per-extruder values on
  the global stack (GlobalStack.getProperty); `limit_to_extruder` redirects;
  non-`settable_per_extruder` settings delegate extruder→global.

## Where does the change go?

| Change | Home |
|---|---|
| One machine, all nozzles/materials | `resources/definitions/<printer>.def.json` `overrides` |
| Whole family (all filament / all IDEX) | the matching `base_fracktal_*.def.json` |
| Per-nozzle (nozzle size, flow limit, heat-zone, first-layer height) | `resources/variants/fracktalworks/<Printer>/*.inst.cfg` `[values]` |
| Per-material (temps, cooling, density) | `resources/materials/<brand>/*.xml.fdm_material` |
| Per-quality layer height (global) or per-material tweak (stub) | `resources/quality/<namespace>/…` |
| Engineering/Visual/Draft picks (Recommended mode) | `resources/intent/base_fracktal_printer/…` (filament only) |
| New user-facing setting | `fdmprinter.def.json` (+ XML map in `plugins/XmlMaterialProfile/XmlMaterialProfile.py` if material-settable); family-internal settings may live in a base def (`bridge_over_support`, `print_mode`) |
| Which settings are visible by default | `resources/setting_visibility/{basic,advanced,expert}.cfg` |

## Hard rules (violations fail silently)

1. `"value"` = evaluated Python expression; `"default_value"` = literal,
   NEVER evaluated (Uranium SettingDefinition: value is Function,
   default_value is Any). A formula in `default_value` is dead code.
   Known instance: `material_barrel_temperature` in both Penrose defs.
2. Constraint fields (`maximum_value` etc.) are expression strings: `"480"`.
3. Quality-stub metadata must match exactly: `definition` = the
   `quality_definition`, `variant` = variant `name` field, `material` =
   material `base_file`. Any mismatch → Cura silently shows ALL global
   quality types. Global profiles need `global_quality = True`.
4. One `quality_type` = one global `layer_height`; per-nozzle layer heights =
   different quality-type subsets (stubs), never different heights per nozzle.
5. `exclude_materials` is substring matching on material id, applied at
   material-tree build time in `cura/Machines/VariantNode.py:63,134` (excluded
   materials never enter the tree, so they can't appear in menus OR be loaded
   from a saved config — Cura falls back to a same-class material). Filament
   printers exclude `_pellet` (inherited from `base_fracktal_printer`); pellet
   (Penrose) printers exclude `["_175", "generic_"]` (their own per-key
   override). This is what keeps filament out of pellet machines and pellets
   out of filament machines — verify with
   `verify_material_segregation.py` after any material or `exclude_materials`
   change. New materials MUST carry the class-marking substring in their id
   (`_pellet` for pellet, `_175` for filament) or the guard can't see them.
   The physical pellet discriminator is `machine_barrel_heater` (an override,
   not metadata).
6. IDEX `machine_start_gcode` is a `"value"` expression branching on
   `print_mode`; single-extruder uses `"default_value"` plain string.
   Regenerate via `python scripts/generate_start_gcode.py --printer <id>
   --write <def>`; never hand-edit the expression. Nozzle waits (`M109 T<n>`)
   and barrel waits (`M109 H<n>`) must stay paired per head.
7. Per-extruder-capable temperature settings need
   `"settable_per_extruder": true`; shared display values need a `resolve`.
8. `machine_extruder_trains` ids must equal extruder filenames minus
   `.def.json`.
9. New `.inst.cfg` files: `setting_version = 23` (matches the shipped fleet;
   app is 24 and auto-upgrades on load — don't mix versions).
10. Pellet printers: coasting is the ooze strategy (retraction ≤ 2 mm,
    `retraction_combing_max_distance = 0`); scale geometry settings with
    `machine_nozzle_size`.

## How a setting reaches the UI (for "why isn't it showing?")

1. Definition nesting decides its category: a custom setting appears under
   the category it's nested in within the `settings` block (e.g.
   `print_mode` under `dual`).
2. `enabled` expression gates the row (evaluated live —
   `resources/qml/Settings/SettingView.qml:231`); e.g. barrel settings show
   only when `machine_barrel_heater` is true.
3. Visibility preset gates it next: the setting key must be in
   `general/visible_settings` (fed by `resources/setting_visibility/*.cfg`
   via `SettingVisibilityPresetsModel`) unless the user searched or picked
   "All".
4. Widget = setting `type` (SettingView.qml:245): float/int/str→TextField,
   enum→ComboBox, bool→CheckBox, extruder→extruder selector.
5. Warning/error colors come from `minimum/maximum_value[_warning]` via
   Uranium `Validator.py` → orange (warning) / red (error) in
   `SettingTextField.qml`.
6. Recommended mode is hand-built QML
   (`resources/qml/PrintSetupSelector/Recommended/*`) bound to specific keys
   (`infill_sparse_density`, `support_enable`, `adhesion_type`, intents via
   `ActiveIntentQualitiesModel`); Custom mode embeds the full SettingView.
7. Dropdown menus (quality/material/nozzle) come from
   `cura/Machines/Models/*` keyed on container metadata — quality dropdown =
   `QualityProfilesDropDownMenuModel` (quality_type), nozzle =
   `NozzleModel` (hardware_type=nozzle variants), materials =
   `MaterialBrandsModel`/`BaseMaterialsModel` (brand/material/GUID).
8. IDEX print modes also surface as a toolbar Tool
   (`plugins/FracktoryIDEX/tools/print_modes/PrintModesPanel.qml`);
   `machine_disallowed_areas` in the IDEX base draws per-mode keep-out zones
   on the build plate.

## Verify (after every change)

1. `python printer-linter/src/terminal.py "<changed files>" --diagnose`
   AND `venv/Scripts/python .claude/skills/printer-configuration/verify_definitions_load.py`
   (loads every definition through the real Uranium loader — catches
   silently-dropped overrides, e.g. whitespace-damaged keys, which the static
   linter misses).
   After any material or `exclude_materials` change also run
   `venv/Scripts/python .claude/skills/printer-configuration/verify_material_segregation.py`
   (proves no printer admits a wrong-class material and every printer boots a
   same-class material).
   After any quality/variant/material change also run
   `venv/Scripts/python .claude/skills/printer-configuration/verify_quality_coverage.py`
   (statically mirrors MaterialNode._loadAll's fallback chain — exact stub →
   brand+type → type → GUID → global — and FAILS on any printer×variant×
   material permutation that lands on the unfiltered global fallback, on
   invalid boot combos, and on UTF-8 BOMs in .inst.cfg files, which break
   the stdlib-configparser version-upgrade path even though FastConfigParser
   tolerates them).
2. Metadata changes (quality/variant/material): launch the app; the quality
   dropdown must show the correct filtered subset per nozzle+material
   (all-types-shown = metadata key mismatch). Check the material menu has no
   pollution across filament/pellet families.
3. G-code changes: slice and inspect start/end blocks (IDEX: all five print
   modes — singleT0, singleT1, dual, mirror, duplication).
4. New settings: confirm category placement, visibility preset membership,
   widget type, and warning/error bounds in the UI.
5. DOX pass: update `resources/AGENTS.md` / `docs/agents.md` if a contract
   moved.

## Known open issues (fleet)

- Shipped profiles are `setting_version = 23` vs app 24 (auto-upgraded each
  load); intent files often have doubled `.inst.inst.cfg` extensions (still
  load). Fix only as a deliberate fleet-wide pass.
- Follow-up candidate: a printer-linter diagnostic for override keys that
  don't match any known setting (the static-analysis version of
  `verify_definitions_load.py`) — new rules belong in `printer-linter/`.
- Generic ASA/CPE materials are excluded fleet-wide (no quality stubs ever
  existed for them, so they showed unfiltered quality lists). Reverse by
  removing `generic_asa`/`generic_cpe` from `base_fracktal_printer`
  `exclude_materials` AND adding proper stub sets.

Fixed 2026-07-23 (in-app verification still pending): barrel-temp formula
moved `default_value`→`value` in both Penrose defs; `_pellet` added to
`exclude_materials` in `base_fracktal_printer` (inherited fleet-wide, Penrose
overrides keep their own list); `fracktal_cf-petg_175` filename space removed;
`support_xy_distance ` trailing-space key fixed in the dual base; UTF-8 BOMs
stripped from 25 pellet quality files (FastConfigParser tolerated them but the
stdlib-configparser version-upgrade path did not); stray `2` line removed from
the 0.8 mm breakaway-high stub; `volterra_300_alf` 1.0 variant renamed
`Model 1 mm`→`Model 1.0 mm` to match stubs (saved configs with the old name
fall back to the preferred variant once); pellet printers'
`preferred_quality_type` corrected `pellet_030`→`pellet_060` (0.3 mm has no
stub for the default Pellet 1.5 mm nozzle, so boot quality was arbitrary).
