# AI Agent Guide: Printer Profile Creation & Management

> **Audience**: AI coding agents (GitHub Copilot, Cursor, etc.) working on the Fracktory-5 codebase.

This document provides comprehensive guidance for creating, editing, and maintaining 3D printer definitions in Fracktory (a Cura fork by Fracktal Works).

---

## Table of Contents

- [Quick Reference](#quick-reference)
- [Architecture Overview](#architecture-overview)
- [Printer Definition Inheritance Chain](#printer-definition-inheritance-chain)
- [Creating a New Printer](#creating-a-new-printer)
- [Quality Profile System](#quality-profile-system)
- [Material System](#material-system)
- [Start/End GCode Expressions](#startend-gcode-expressions)
- [Temperature Settings System](#temperature-settings-system)
- [Barrel Heater Integration](#barrel-heater-integration)
- [IDEX Printer Specifics](#idex-printer-specifics)
- [Variant Files](#variant-files)
- [Material XML Integration (XmlMaterialProfile)](#material-xml-integration-xmlmaterialprofile)
- [File Naming Conventions](#file-naming-conventions)
- [Pellet Extrusion Optimization](#pellet-extrusion-optimization)
- [Common Pitfalls](#common-pitfalls)

---

## Quick Reference

| Task | Key Files |
|------|-----------|
| Base settings for all printers | `resources/definitions/fdmprinter.def.json` |
| Fracktal base (single extruder) | `resources/definitions/base_fracktal_printer.def.json` |
| Fracktal base (dual extruder) | `resources/definitions/base_fracktal_dual_printer.def.json` |
| Fracktal base (IDEX) | `resources/definitions/base_fracktal_idex_printer.def.json` |
| Printer extruder definitions | `resources/extruders/<printer_id>_extruder_N.def.json` |
| Nozzle variants | `resources/variants/fracktalworks/<Printer Name>/*.inst.cfg` |
| Filament material XML profiles | `resources/materials/Fracktal Works/*.xml.fdm_material` |
| Pellet material XML profiles | `resources/materials/Fracktal Works Pellet/*.xml.fdm_material` |
| Quality profiles (global + stubs) | `resources/quality/<quality_definition>/` |
| Quality base definition | `resources/definitions/<quality_definition>.def.json` |
| GCode expression generator script | `scripts/generate_start_gcode.py` |
| GCode formatter (Cura engine) | `plugins/CuraEngineBackend/StartSliceJob.py` |
| XML material settings mapping | `plugins/XmlMaterialProfile/XmlMaterialProfile.py` |

---

## Architecture Overview

### Container Stack (Settings Resolution Order)

Cura evaluates settings using a hierarchical stack. Higher layers override lower layers:

```
7. USER OVERRIDES          <- Temporary user changes in UI
6. QUALITY PROFILE         <- resources/quality/
5. INTENT PROFILE          <- resources/intent/
4. MATERIAL PROFILE        <- resources/materials/
3. VARIANT PROFILE         <- resources/variants/
2. EXTRUDER DEFINITION     <- resources/extruders/
1. MACHINE DEFINITION      <- resources/definitions/
```

### Key Concepts

- **`default_value`**: Static value, cannot reference other settings (used for plain strings/numbers)
- **`value`**: Python expression, CAN reference other settings and use conditionals (evaluated at runtime)
- **`enabled`**: Controls visibility in UI (can be a Python expression)
- **`settable_per_extruder`**: If true, each extruder can have its own value

### Setting Value Types in fdmprinter.def.json

**IMPORTANT**: Constraint fields like `maximum_value`, `minimum_value`, `maximum_value_warning` in `fdmprinter.def.json` use **string** type even when they look numeric:
```json
"maximum_value": "480"       // Correct - string
"maximum_value": 480         // WRONG - will cause issues
```

This is because these values are treated as Python expressions by Cura and may reference other settings.

---

## Printer Definition Inheritance Chain

```
fdmprinter.def.json (root - all settings defined here)
  -> base_fracktal_printer.def.json (single extruder Fracktal base)
       -> penrose_600.def.json (specific printer)
       -> julia_advanced.def.json, dragon_400.def.json, ... (specific printers)
       -> base_fracktal_dual_printer.def.json (dual extruder base)
            -> julia_pro_dual.def.json, twin_dragon_*.def.json, volterra_dual.def.json
            -> base_fracktal_idex_printer.def.json (IDEX base)
                 -> penrose_600_idex.def.json (specific IDEX printer)
```

Note: `base_fracktal_dual_printer` inherits `base_fracktal_printer` (verified
in the file), so single-extruder base settings and metadata (e.g.
`exclude_materials`) flow to dual and IDEX machines too. Definition metadata
inheritance is per-key: a child key replaces the parent's value wholesale
(no list merging).

**Rule**: Override settings as close to the leaf (specific printer) as possible. Only add settings to `fdmprinter.def.json` if they are customer-facing and used in material profiles. Use base definitions for shared internal settings.

### Dual-mode printers (pellet OR filament) — use a definition PAIR

A physical printer that can run **either** a pellet head **or** a filament
head (whether swapped manually or by parking one IDEX carriage) cannot be one
Cura machine that toggles modes: `exclude_materials`, `quality_definition`,
and `machine_barrel_heater` are all fixed per definition at load
(`machine_barrel_heater` is `settable_per_extruder: false`, so a variant can't
flip it). Toggling would break material segregation.

Model each such product as a **pair of single-extruder definitions**, one per
mode, over shared hidden bases:

```
base_penrose_pellet.def.json (hidden; pellet slicing philosophy, inherits base_fracktal_printer)
  -> penrose_600_swappable_pellet.def.json          (visible)
  -> penrose_600_idex_choosable_pellet.def.json     (visible)
base_fracktal_printer.def.json
  -> penrose_600_swappable_fdm.def.json             (visible; filament tuning free)
  -> penrose_600_idex_choosable_fdm.def.json        (visible)
```

- The pellet leaves keep `exclude_materials: ["_175","generic_"]` +
  `quality_definition: penrose_pellet_quality`; the filament leaves inherit
  `exclude_materials: ["_pellet"]` + set `quality_definition:
  base_fracktal_printer`. Segregation then holds per entry (verify with
  `.claude/skills/printer-configuration/verify_material_segregation.py`).
- **Quality is reused, not duplicated**: stubs key on `variant` name +
  `material`, not on the machine id, so new variants named `Pellet X.X mm` /
  `Model X.X mm` reuse the existing `penrose_pellet_quality` /
  `base_fracktal_printer` stubs. Zero new quality files.
- The user "switches mode" by selecting the matching machine in Cura's
  printer list.
- IDEX-choosable leaves are modeled single-extruder (one active head); the
  idle carriage parks via firmware on tool select. Their g-code is generated
  by `scripts/generate_start_gcode.py` presets using the single-mode fields
  `tool_index` (0=left pellet, 1=right filament — drives `M104/M109 T<n>`,
  `H<n>`, and tool select), `center_purge` (on-bed purge line centered on the
  bed front — emitted as `{machine_width / 2 +- offset}` slice-time tags so
  it stays centered if the bed size changes; avoids side/dock complications),
  and `idex_frame` (IDEX homing; end g-code switches off BOTH nozzles plus
  the frame's H0 barrel defensively, homes X/Y only). All four dual-mode
  Penrose leaves use `center_purge`; the older `park_purge` field (off-bed
  purge at the tool's park side) remains available but unused by presets. Each choosable leaf also carries the
  static `machine_disallowed_areas` strip for the side its carriage cannot
  reach (pellet/T0 blocks the right strip, filament/T1 the left strip —
  copied from the IDEX base's singleT0/singleT1 branches). Filament process
  settings on the fdm leaves come from Twin Dragon 600 (speed_print 100,
  travel max(250,·), print-speed cap 120); frame kinematics stay Penrose.
- Verify with the three skill companions (definitions-load, material
  segregation, quality coverage) — see
  `.claude/skills/printer-configuration/`.

---

## Creating a New Printer

### Step-by-Step Checklist

#### 1. Create Printer Definition (`resources/definitions/<printer_id>.def.json`)

```json
{
    "version": 2,
    "name": "Human Readable Printer Name",
    "inherits": "base_fracktal_printer",   // or "base_fracktal_idex_printer"
    "id": "printer_id",
    "metadata": {
        "visible": true,
        "manufacturer": "Fracktal Works",
        "category": "Category Name",       // e.g., "Pellet Series", "FDM Series"
        "has_machine_materials": false,     // true if printer has specific materials
        "has_machine_quality": true,
        "has_materials": false,
        "has_variant_materials": false,
        "has_variants": true,
        "machine_variant_shortcode": "XX",  // Short code for variant naming
        "preferred_quality_type": "normal",
        "preferred_variant_name": "Model 0.4 mm",
        "quality_definition": "base_fracktal_printer",
        "variants_name": "Nozzle",
        "machine_extruder_trains": {
            "0": "printer_id_extruder_0"
            // "1": "printer_id_extruder_1"  // Add for IDEX
        }
    },
    "overrides": {
        "machine_name": { "default_value": "Human Readable Printer Name" },
        "machine_width": { "default_value": 300 },
        "machine_depth": { "default_value": 300 },
        "machine_height": { "default_value": 300 },
        // ... more settings ...
        "machine_start_gcode": { ... },
        "machine_end_gcode": { ... }
    }
}
```

#### 2. Create Extruder Definitions (`resources/extruders/<printer_id>_extruder_N.def.json`)

```json
{
    "version": 2,
    "name": "Printer Name Extruder N",
    "inherits": "base_fracktal_extruder_0",    // or base_fracktal_idex_extruder_N
    "metadata": {
        "machine": "printer_id",
        "position": "0"                         // "0" or "1"
    },
    "overrides": {
        "extruder_nr": { "default_value": 0 },
        "machine_nozzle_size": { "default_value": 0.4 }
    }
}
```

#### 3. Create Variant Files (`resources/variants/fracktalworks/<Printer Name>/`)

Use `Variant Creator.py` or create manually. See [Variant Files](#variant-files) section.

#### 4. Generate Start/End GCode

Use the `scripts/generate_start_gcode.py` script:

```bash
# For IDEX with barrel heater (pellet extruder):
python scripts/generate_start_gcode.py --type idex --barrel --pellet --name "My Printer"

# For single extruder with barrel heater:
python scripts/generate_start_gcode.py --type single --barrel --pellet --name "My Printer"

# For standard filament IDEX:
python scripts/generate_start_gcode.py --type idex --name "My Printer"

# Write directly to definition file:
python scripts/generate_start_gcode.py --printer penrose_600_idex --write resources/definitions/penrose_600_idex.def.json
```

#### 5. Required Overrides for Barrel Heater Printers

If the printer has a barrel heater, add these overrides:

```json
"machine_barrel_heater": { "default_value": true },
"material_barrel_temperature": {
    "value": "default_material_barrel_temperature if default_material_barrel_temperature > 0 else max(round(material_print_temperature * 0.7), 120)",
    "enabled": true
},
"material_barrel_temperature_layer_0": { "enabled": true }
```

#### 6. Required Overrides for Custom GCode Printers

When providing custom start gcode that handles heating, **always disable** Cura's automatic temperature prepend:

```json
"material_bed_temp_prepend": { "value": false },
"material_print_temp_prepend": { "value": false },
"material_print_temp_wait": { "value": false }
```

#### 7. Create Quality Profiles (if using custom quality_definition)

See the [Quality Profile System](#quality-profile-system) section for full details BEFORE attempting this step. Creating quality profiles incorrectly is the most error-prone part of printer setup.

#### 8. Create Pellet Materials (if using pellet extruders)

See the [Material System](#material-system) section. Create separate material profiles in `resources/materials/Fracktal Works Pellet/` and use `exclude_materials` to hide filament materials.

---

## Quality Profile System

### How Cura Resolves Quality Profiles

Understanding the quality resolution chain is **critical** for getting quality profiles to work correctly. The resolution follows a tree structure built at startup:

```
MachineNode (printer definition)
  ├── global_qualities: {quality_type: QualityNode}    ← 10 global profiles
  └── variants: {variant_name: VariantNode}
       └── materials: {base_file: MaterialNode}
            └── qualities: {container_id: QualityNode}  ← variant+material stubs
```

**Key code files:**
- `cura/Machines/MachineNode.py` — Loads variants + global qualities, `getQualityGroups()` determines availability
- `cura/Machines/VariantNode.py` — Loads materials under each variant
- `cura/Machines/MaterialNode.py` — Loads quality stubs matching `(definition, variant, material)`
- `cura/Machines/ContainerTree.py` — Entry point, `getCurrentQualityGroups()` called by UI

### Quality Resolution Flow

1. **MachineNode._loadAll()** finds variants by `definition = printer_id` and global qualities by `definition = quality_definition, global_quality = True`
2. **VariantNode._loadAll()** loads all materials (filtered by `exclude_materials`)
3. **MaterialNode._loadAll()** searches for quality stubs matching `(definition=quality_definition, variant=variant_name, material=base_file)`
4. **MachineNode.getQualityGroups()** intersects available quality types across all enabled extruders

### The Availability Intersection (Critical)

```python
# From MachineNode.getQualityGroups():
for extruder_nr, variant_name in enumerate(variant_names):
    material_base = material_bases[extruder_nr]
    if variant_name not in self.variants or material_base not in self.variants[variant_name].materials:
        # FALLBACK: Use ALL global qualities (every type becomes available!)
        qualities_per_type_per_extruder[extruder_nr] = self.global_qualities
    else:
        # Use the variant+material specific quality stubs
        qualities_per_type_per_extruder[extruder_nr] = {node.quality_type: node for node in ...}

# Then intersect across extruders:
available_quality_types = set(all_types)
for extruder_nr, qualities_per_type in enumerate(qualities_per_type_per_extruder):
    if extruder_enabled[extruder_nr]:
        available_quality_types.intersection_update(qualities_per_type.keys())
```

**Key insight**: If the variant/material lookup FAILS (material not found in the tree), Cura falls back to showing ALL global quality types for that extruder. This means:
- Missing a quality stub → all quality types show up (no filtering)
- Missing material in `exclude_materials` → filament materials pollute the dropdown

### Architecture of Quality Profiles

Quality profiles have two levels:

#### 1. Global Quality Profiles (define layer heights)

Located at `resources/quality/<quality_definition>/` (root level, not in subdirectories).

```ini
[general]
definition = penrose_pellet_quality   # Must match quality_definition in printer
name = Extra Fine - 0.3mm             # Display name in dropdown
version = 4

[metadata]
global_quality = True                 # REQUIRED: marks as global profile
quality_type = pellet_030             # Unique type identifier
setting_version = 23
type = quality
weight = 9                            # Sort order (higher = finer quality)

[values]
layer_height = 0.3                    # THE layer height for this quality type
```

**Rules:**
- Each `quality_type` has exactly ONE fixed `layer_height` — you cannot have different layer heights for the same quality_type across different nozzles
- `weight` controls sort order in the UI (higher number = appears higher/finer)
- `global_quality = True` is REQUIRED or the profile won't be found

#### 2. Variant+Material Quality Stubs (control availability)

Located at `resources/quality/<quality_definition>/<Material>/<Variant>/`.

```ini
[general]
definition = penrose_pellet_quality   # Must match quality_definition
name = Extra Fine - 0.3mm             # Display name (should match global)
version = 4

[metadata]
material = fracktal_pla_pellet        # REQUIRED: must match material base_file
quality_type = pellet_030             # Must match a global quality_type
setting_version = 23
type = quality
variant = Pellet 0.6 mm              # REQUIRED: must match variant name exactly
weight = 9

[values]
                                      # Usually empty! Stubs just provide availability
                                      # Add values here ONLY for per-material overrides
```

**Rules:**
- The `material` field is REQUIRED when the printer has `has_materials: true` + `has_variants: true`
- Without `material`, `MaterialNode._loadAll()` won't find it, causing fallback to all global types
- The `variant` must exactly match the variant `name` field (e.g., "Pellet 0.6 mm")
- Stubs do NOT need `[values]` entries — they just signal "this quality_type is available for this variant+material combo"
- Each nozzle variant should only have stubs for quality types that are PHYSICALLY POSSIBLE for that nozzle size

### Designing Quality Type Subsets Per Nozzle

Each nozzle can only print a range of layer heights (typically 30-80% of nozzle diameter). Design the global quality types as a superset, then create stubs only for the valid subset per nozzle:

```
Quality Type     Layer Height   0.6mm  0.8mm  1.0mm  1.5mm  2.0mm  3.0mm
─────────────────────────────────────────────────────────────────────────
pellet_020       0.2mm           ✓
pellet_030       0.3mm           ✓      ✓
pellet_040       0.4mm                         ✓
pellet_050       0.5mm           ✓      ✓
pellet_060       0.6mm                  ✓      ✓      ✓
pellet_080       0.8mm                         ✓             ✓
pellet_100       1.0mm                                ✓
pellet_120       1.2mm                                ✓      ✓      ✓
pellet_160       1.6mm                                       ✓      ✓
pellet_240       2.4mm                                              ✓
```

For each cell with ✓, create one stub per material. Total stubs = ✓ count × material count.

### Printer Definition Metadata for Quality

```json
{
    "metadata": {
        "has_machine_quality": true,          // REQUIRED: enables machine-specific quality
        "has_materials": true,                // REQUIRED: enables material-aware quality filtering
        "has_variants": true,                 // REQUIRED: enables variant-aware quality filtering
        "quality_definition": "penrose_pellet_quality",  // Namespace for quality searches
        "preferred_quality_type": "pellet_030",          // Default selection
        "preferred_material": "fracktal_pla_pellet",     // Default material
        "preferred_variant_name": "Pellet 0.6 mm"        // Default nozzle
    }
}
```

### Quality Definition File (`<quality_definition>.def.json`)

A thin definition file that serves as a namespace/lookup key for quality profiles. NOT a full printer definition.

```json
{
    "version": 2,
    "name": "Penrose Pellet Quality Base",
    "inherits": "fdmprinter",
    "metadata": {
        "author": "Fracktal Works",
        "file_formats": "text/x-gcode",
        "has_machine_quality": true,
        "has_variants": true,
        "variants_name": "Nozzle",
        "visible": false              // MUST be false - this is not a real printer
    },
    "overrides": {}
}
```

### Folder Structure Example

```
resources/quality/penrose_pellet_quality/
├── penrose_pellet_global_pellet_020.inst.cfg    (10 global profiles)
├── penrose_pellet_global_pellet_030.inst.cfg
├── ...
├── PLA/
│   ├── Pellet 0.6 mm/
│   │   ├── penrose_pellet_0.6_pla_pellet_020.inst.cfg
│   │   ├── penrose_pellet_0.6_pla_pellet_030.inst.cfg
│   │   └── penrose_pellet_0.6_pla_pellet_050.inst.cfg
│   ├── Pellet 0.8 mm/
│   │   └── ...
│   └── ...
├── ABS/
│   └── ...
├── TPU/
│   └── ...
└── Nylon/
    └── ...
```

> **Note**: The folder structure is for human organization only. Cura scans ALL `.inst.cfg` files recursively and loads them based on metadata, not path.

### Common Quality Profile Mistakes

1. **Missing `material` metadata in stubs** → Cura can't find stubs → falls back to ALL global types (no nozzle filtering)
2. **Missing `global_quality = True`** in global profiles → profiles won't be found as globals
3. **`has_materials: false`** in printer definition → entire material-aware filtering is bypassed, all nozzles see all quality types
4. **Wrong `definition`** in stub → doesn't match `quality_definition` → never found
5. **Wrong `variant` name** in stub → doesn't match the variant's `name` field → not loaded for that nozzle
6. **Trying to vary layer_height per nozzle in the same quality_type** → impossible, each quality_type has ONE global layer_height; use different quality_type subsets per nozzle instead

---

## Material System

### Filament vs Pellet Materials

For printers using non-standard feed stock (pellets, granules), create separate material profiles to avoid polluting the material dropdown with incompatible filament materials.

| Aspect | Filament Materials | Pellet Materials |
|--------|-------------------|-----------------|
| Folder | `resources/materials/Fracktal Works/` | `resources/materials/Fracktal Works Pellet/` |
| ID pattern | `fracktal_<type>_175` | `fracktal_<type>_pellet` |
| Example | `fracktal_pla_175` | `fracktal_pla_pellet` |
| Diameter | 1.75mm | 1.75mm (for Cura's volume calculations) |

### Filtering Materials Per Printer (`exclude_materials`)

Use `exclude_materials` in printer metadata to block unwanted materials by **substring matching** against `material["id"]`:

```json
"exclude_materials": ["_175", "generic_"]
```

The `isExcludedMaterialBaseFile()` method in `MachineNode.py` iterates through each pattern and returns `True` if ANY pattern is found **anywhere** in the material ID string. This is a substring check (`in`), not a regex.

**How it works:**
```python
def isExcludedMaterialBaseFile(self, material_base_file: str) -> bool:
    for exclude_material in self.exclude_materials:
        if exclude_material in material_base_file:   # substring match!
            return True
    return False
```

**Design pattern:** Give pellet materials IDs that DON'T contain the exclusion patterns:
- Filament IDs: `fracktal_pla_175` (contains `_175` → excluded)
- Generic IDs: `generic_pla_175` (contains `generic_` → excluded)
- Pellet IDs: `fracktal_pla_pellet` (contains neither → NOT excluded ✓)

### Material XML Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<fdmmaterial xmlns="http://www.ultimaker.com/material"
             xmlns:cura="http://www.ultimaker.com/cura" version="1.3">
    <metadata>
        <name>
            <brand>Fracktal Works</brand>
            <material>PLA</material>         <!-- Material type for fallback matching -->
            <color>Generic</color>
            <label>PLA Pellet</label>         <!-- Display name in UI -->
        </name>
        <GUID>unique-uuid-here</GUID>
        <reference_material_id>pla</reference_material_id>  <!-- Generic fallback ID -->
        <version>1</version>
        <color_code>#ffc934</color_code>
        <description>Material description</description>
        <adhesion_info>Build plate adhesion info</adhesion_info>
    </metadata>
    <properties>
        <density>1.24</density>
        <diameter>1.75</diameter>              <!-- Used for Cura volume calculations -->
    </properties>
    <settings>
        <setting key="print temperature">190</setting>
        <setting key="standby temperature">175</setting>
        <setting key="heated bed temperature">60</setting>
        <setting key="build volume temperature">30</setting>
        <!-- For barrel heater printers, add: -->
        <!-- <setting key="barrel temperature">133</setting> -->
        <setting key="adhesion tendency">0</setting>
        <setting key="surface energy">100</setting>
        <cura:setting key="cool_fan_speed">100</cura:setting>
    </settings>
</fdmmaterial>
```

### Quality Stubs Must Reference Correct Material IDs

Quality stubs' `material` metadata must match the material's `base_file` (typically the filename without `.xml.fdm_material`):

```ini
# In quality stub:
material = fracktal_pla_pellet    # Must match the material file's base_file

# The material file: fracktal_pla_pellet.xml.fdm_material
# Its base_file = "fracktal_pla_pellet"
```

---

## Start/End GCode Expressions

### How Replacement Tags Work

Cura's `GcodeStartEndFormatter` (in `plugins/CuraEngineBackend/StartSliceJob.py`) processes replacement tags in gcode strings at slice time.

**Regex pattern**: `r"{(?P<condition>if|else|elif|endif)?\s*(?P<expression>.*?)\s*(?:,\s*(?P<extruder_nr_expr>.*))?\s*}(?P<end_of_line>\n?)"`

#### Tag Formats

| Format | Description | Example |
|--------|-------------|---------|
| `{setting_name}` | Global setting value | `{material_bed_temperature_layer_0}` |
| `{setting_name, N}` | Setting value for extruder N | `{material_print_temperature, 0}` |
| `{if condition}...{endif}` | Conditional blocks | `{if layer_height > 0.3}...{endif}` |
| `{expression}` | Arbitrary Python expression | `{100 + 5}` |

### IDEX vs Single Extruder GCode

| Aspect | IDEX Printer | Single Extruder |
|--------|-------------|-----------------|
| Start gcode field | `"value"` (Python expression) | `"default_value"` (plain string) |
| Temperature tags | `{setting, extruder_nr}` | `{setting_name}` |
| Print mode handling | Conditional per mode | N/A |
| Expression type | String concatenation with ternaries | Static string with tags |

### IDEX Start GCode Expression Structure

```python
# The expression is a single Python string concatenation:
header_comments                     # Plain string with replacement tags
+ (singleT1_heating_block           # Conditional: only for singleT1 mode
   if print_mode == 'singleT1' else '')
+ (singleT0_heating_block           # Conditional: only for singleT0 mode
   if print_mode == 'singleT0' else '')
+ (dual_heating_block               # Conditional: only for dual mode
   if print_mode == 'dual' else '')
+ (mirror_dup_heating_block         # Conditional: mirror OR duplication mode
   if print_mode == 'mirror'
   or print_mode == 'duplication' else '')
+ homing_gcode                      # G21, G90, M107, G28, safety Z
+ bed_leveling                      # G29, M500 (BEFORE purge for pellet IDEX)
+ (t0_purge if mode != singleT1)    # Off-bed purge at T0 position (X=-20 Y=10)
+ (t1_purge if mode != singleT0)    # Off-bed purge at T1 position (X=620 Y=10)
+ (tool_select)                     # Select starting tool (T0 unless singleT1)
+ print_mode_gcode                  # {print_mode_gcode} AFTER purge
+ final_setup                       # G4 delays, G92 E0
```

> **Note**: For pellet IDEX printers, `{print_mode_gcode}` is placed AFTER the purge
> sequence because purging requires independent tool mode (the default after homing).
> Mirror/duplication modes (M605 S2/S3) link both carriages together, which would
> prevent independent per-tool purge movements.

### IDEX Purge Positions (Pellet Extruders)

Pellet extruders require significant purge volumes (≥200mm extrusion) to:
- Prime the pellet feed system
- Clear the long melt zone / barrel
- Purge any degraded material from the barrel

Purge positions are **outside the build area** at each tool's park/pause position
(from Klipper's `PRINTER_VARIABLES`):

| Tool | Purge X | Purge Y | Notes |
|------|---------|---------|-------|
| T0   | -20     | -5      | Left of bed, 5mm margin from Y position_min (-10) |
| T1   | 620     | -5      | Right of bed, 5mm margin from Y position_min (-10) |

The purge is done in 4 phases while moving in the Y direction to spread material:

| Phase | Y Travel | Extrusion | Speed    | Description |
|-------|----------|-----------|----------|-------------|
| 1     | 30mm     | 150mm     | 300mm/m  | Slow prime  |
| 2     | 30mm     | 200mm     | 500mm/m  | Medium purge|
| 3     | 40mm     | 300mm     | 800mm/m  | Fast purge  |
| 4     | 40mm     | 350mm     | 1000mm/m | Full speed  |
| **Total** | **140mm** | **1000mm** | — | Per tool |

Purge is **conditional** per print mode:
- **singleT0**: Only T0 purges
- **singleT1**: Only T1 purges
- **dual/mirror/duplication**: Both T0 and T1 purge sequentially

### Temperature Replacement Tag Pattern (IDEX)

The nozzle temperature tag handles the layer_0 fallback:

```python
# For extruder N:
("S{material_print_temperature, N}"
 if extruderValue(N, 'material_print_temperature_layer_0') == 0
 else "S{material_print_temperature_layer_0, N}")
```

This checks if `material_print_temperature_layer_0` is set for that extruder. If 0 (unset), it falls back to `material_print_temperature`.

### Heating Command Order

The barrel and nozzle are part of the same extrusion head, so their waits must be **paired per head** to avoid thermal runaway from temperature differentials:

1. **Start heating** all heaters simultaneously (M104 = set, don't wait)
2. **Wait for bed** first (M190 - bed is slowest)
3. **Wait for each extruder head** — nozzle then barrel, paired together:
   - `M109 T0` (wait nozzle 0), then `M109 H0` (wait barrel 0)
   - `M109 T1` (wait nozzle 1), then `M109 H1` (wait barrel 1)

> **Warning**: Do NOT group all nozzle waits before all barrel waits. This creates a dangerous temperature differential where nozzles sit at full temp while barrels are still cold, which can trigger thermal runaway in Klipper firmware.

### Mirror/Duplication Mode Temperature Rule

In mirror and duplication modes, **both extruders use T0's temperature settings** because both print the same geometry with the same material.

---

## Temperature Settings System

### Temperature Resolution Chain

```
Material XML "barrel temperature"
    -> XmlMaterialProfile.py maps to ->
default_material_barrel_temperature (hidden, settable_per_extruder)
    -> used as base value by ->
material_barrel_temperature (visible, editable, max 480)
    -> used as base value by ->
material_barrel_temperature_layer_0 (visible, first layer override)
```

### fdmprinter.def.json Temperature Settings

These settings are defined in `fdmprinter.def.json` under the `material` category:

| Setting | Type | Description | Max |
|---------|------|-------------|-----|
| `default_material_barrel_temperature` | hidden float | Set by material XML | - |
| `material_barrel_temperature` | visible float | User-editable barrel temp | 480 |
| `material_barrel_temperature_layer_0` | visible float | First layer barrel temp | 480 |

### Adding a New Temperature Setting to fdmprinter.def.json

Follow this pattern (from the barrel heater implementation):

1. Add a `machine_*` boolean capability to `machine_settings`:
   ```json
   "machine_barrel_heater": {
       "label": "Has Barrel Heater",
       "description": "...",
       "default_value": false,
       "type": "bool",
       "settable_per_extruder": false,
       "settable_per_mesh": false
   }
   ```

2. Add a hidden `default_material_*` setting (populated by material XML):
   ```json
   "default_material_barrel_temperature": {
       "label": "Default Barrel Temperature",
       "description": "...",
       "default_value": 0,
       "type": "float",
       "enabled": false,
       "settable_per_extruder": true
   }
   ```

3. Add a visible `material_*` setting (user-editable):
   ```json
   "material_barrel_temperature": {
       "label": "Barrel Temperature",
       "description": "...",
       "unit": "\u00b0C",
       "type": "float",
       "default_value": 0,
       "value": "default_material_barrel_temperature",
       "enabled": "machine_barrel_heater",
       "maximum_value": "480",
       "settable_per_extruder": true
   }
   ```

4. Add a layer_0 variant (first layer override):
   ```json
   "material_barrel_temperature_layer_0": {
       "label": "Barrel Temperature Initial Layer",
       "description": "...",
       "unit": "\u00b0C",
       "type": "float",
       "default_value": 0,
       "value": "material_barrel_temperature",
       "enabled": "machine_barrel_heater",
       "maximum_value": "480",
       "settable_per_extruder": true
   }
   ```

5. Add XML mapping in `plugins/XmlMaterialProfile/XmlMaterialProfile.py`:
   ```python
   __material_settings_setting_map = {
       ...
       "barrel temperature": "default_material_barrel_temperature",
       ...
   }
   ```

---

## Barrel Heater Integration

### GCode Commands

| Command | Description |
|---------|-------------|
| `M104 HN S{temp}` | Set barrel heater N temp (don't wait) |
| `M109 HN S{temp}` | Set barrel heater N temp and wait |
| `M104 HN S0` | Turn off barrel heater N |

Where N = 0 or 1 (corresponding to extruder number).

### Required Printer Definition Overrides

```json
"machine_barrel_heater": { "default_value": true },
"material_barrel_temperature": {
    "value": "default_material_barrel_temperature if default_material_barrel_temperature > 0 else max(round(material_print_temperature * 0.7), 120)",
    "enabled": true
},
"material_barrel_temperature_layer_0": { "enabled": true }
```

**Formula explanation**: If a material XML provides a barrel temperature, use it. Otherwise, default to 70% of nozzle temperature (minimum 120C).

---

## IDEX Printer Specifics

### Print Modes

| Mode | Value | Description | Temp Source |
|------|-------|-------------|-------------|
| Single 1 | `singleT0` | Only extruder 0 active | T0 settings |
| Single 2 | `singleT1` | Only extruder 1 active | T1 settings |
| Dual | `dual` | Both extruders, independent | T0 + T1 settings |
| Mirror | `mirror` | Both extruders, mirrored | T0 settings for both |
| Duplication | `duplication` | Both extruders, duplicated | T0 settings for both |

### IDEX Base Settings

The `base_fracktal_idex_printer.def.json` defines:
- `print_mode` enum setting (in `settings.dual.children`)
- `print_mode_gcode` derived setting (generates T0/T1/M605 commands)
- `is_idex` boolean (in `settings.machine_settings.children`)

### Key IDEX Overrides

```json
"prime_tower_enable": { "value": "True if print_mode == 'dual' else False" },
"adhesion_type": { "value": "'brim' if print_mode == 'dual' or ... else 'raft'" }
```

---

## Variant Files

### Location

`resources/variants/fracktalworks/<Printer Name>/printer_id_<variant_shortcode>_<size>.inst.cfg`

Example: `resources/variants/fracktalworks/Penrose 600 IDEX/penrose_600_idex_PE_1.5.inst.cfg`

### Format

```ini
[general]
name = Pellet 1.5 mm
version = 4
definition = penrose_600_idex

[metadata]
hardware_type = nozzle
setting_version = 23
type = variant

[values]
machine_nozzle_size = 1.5
```

### Common Nozzle Sizes

- **Filament**: 0.25, 0.4, 0.6, 0.8mm (Model/Volcano variants)
- **Pellet**: 0.6, 0.8, 1.0, 1.5, 2.0, 3.0mm

### Generation

Use `Variant Creator.py` at the repository root for automated variant generation, or create files manually following the format above.

---

## Material XML Integration (XmlMaterialProfile)

### XmlMaterialProfile Mapping

When adding new temperature settings that should be populated by material XML files, add the mapping in `plugins/XmlMaterialProfile/XmlMaterialProfile.py`:

```python
# In the __material_settings_setting_map dictionary:
__material_settings_setting_map = {
    "print temperature": "default_material_print_temperature",
    "heated bed temperature": "material_bed_temperature",
    "standby temperature": "material_standby_temperature",
    "build volume temperature": "build_volume_temperature",
    "barrel temperature": "default_material_barrel_temperature",
    # ... add new mappings here
}
```

The key (e.g., "barrel temperature") comes from the material XML `<setting>` element name.

---

## File Naming Conventions

| File Type | Convention | Example |
|-----------|-----------|---------|
| Printer definition | `<printer_id>.def.json` | `penrose_600_idex.def.json` |
| Extruder definition | `<printer_id>_extruder_N.def.json` | `penrose_600_idex_extruder_0.def.json` |
| Base extruder (IDEX) | `base_fracktal_idex_extruder_N.def.json` | `base_fracktal_idex_extruder_0.def.json` |
| Variant folder | `fracktalworks/<Printer Name>/` | `fracktalworks/Penrose 600 IDEX/` |
| Variant file | `<printer_id>_<shortcode>_<size>.inst.cfg` | `penrose_600_idex_PE_1.5.inst.cfg` |

**Printer ID**: lowercase, underscores, no spaces (e.g., `penrose_600_idex`)
**Printer Name**: Human-readable, used in UI and folder names (e.g., `Penrose 600 IDEX`)

---

## Pellet Extrusion Optimization

Pellet (screw-based) extruders have fundamentally different physics from filament extruders. Key differences that affect slicer settings:

1. **Screw inertia** — the screw cannot instantly change flow rate; sudden speed changes cause over/under-extrusion
2. **Limited retraction** — screw reversal is minimal (2-3mm max); coasting is the primary ooze strategy
3. **Larger nozzles** — typically 0.6-3.0mm; settings must scale with nozzle size
4. **Higher thermal mass** — thick beads need longer cooling; barrel heater adds another thermal zone

### Critical Settings for Pellet Printers

| Setting | Purpose | Recommended Formula |
|---------|---------|--------------------|
| `coasting_enable` | Primary ooze management (replaces retraction's role) | `true` |
| `coasting_volume` | Volume to stop extruding before path end | `round(machine_nozzle_size ** 3 * 1.5, 3)` |
| `coasting_speed` | Speed during coast phase (% of print speed) | `80` |
| `coasting_min_volume` | Min path volume to activate coasting | `round(coasting_volume * 10, 2)` |
| `bridge_wall_coast` | Coast before bridge walls (critical without retraction) | `100` (%) |
| `retraction_amount` | Small retraction for screw pressure relief | `2` mm |
| `retraction_speed` | Gentle retraction speed for screw | `50` mm/s |
| `retraction_combing` | Keep nozzle inside part to hide ooze | `'all'` |
| `retraction_combing_max_distance` | Never retract during combing (0 = unlimited) | `0` |

### Speed Uniformity for Screw Extruders

Screw extruders perform best with minimal speed variation. Keep wall/topbottom speeds close to print speed:

| Setting | Filament Default | Pellet Override | Rationale |
|---------|-----------------|-----------------|------------|
| `speed_wall` | `print * 0.75` | `min(round(speed_print * 0.9, 0), 150)` | Reduce speed gap from 25% to 10% |
| `speed_wall_0` | `wall * 0.75` | `min(round(speed_wall * 0.85, 0), 120)` | Outer wall: 15% slower than wall |
| `speed_topbottom` | `print * 0.8` | `min(round(speed_print * 0.9, 0), 150)` | Match wall speed |
| `max_flow_acceleration` | 0.4-2.0 | Reduced by ~50% (nozzle-scaled) | Screw has higher rotational inertia |

### Bridge Settings (No-Retraction Compensation)

Without effective retraction, bridges need reduced flow to prevent sagging:
- `bridge_wall_material_flow`: `round(material_flow * 0.80)` (20% reduction)
- `bridge_skin_material_flow`: `round(material_flow * 0.80)` (20% reduction)
- `bridge_wall_coast`: `100` (full coast before bridge — base_fracktal sets this to 0!)

### Nozzle-Scaled Settings

Many settings should scale with nozzle size for pellet printers:
- `wall_0_wipe_dist`: `machine_nozzle_size * 2` (per Dyze Pulsar: "at least line width")
- `travel_avoid_distance`: `machine_nozzle_size * 1.5` (larger clearance for ooze)
- `meshfix_maximum_deviation`: `max(0.02, machine_nozzle_size * 0.04)` (tolerance scales)
- `meshfix_maximum_resolution`: `max(0.5, machine_nozzle_size * 0.8)` (large nozzle doesn't need sub-nozzle resolution)
- `switch_extruder_extra_prime_amount`: `machine_nozzle_size * 3` (rebuild screw pressure after tool change)

### Sources
- Dyze Design Pulsar documentation: retraction prohibited, Z-lift required, wipe ≥ line width, keep speed uniform
- 3DMag pellet extrusion guide: bead geometry and thermal history dominate process planning
- CNC Kitchen: extrusion width 100-120% of nozzle diameter

---

## Common Pitfalls

### 1. Using `default_value` instead of `value` for IDEX start gcode
IDEX start gcode MUST use `"value"` (Python expression) because it needs `print_mode` conditionals. `"default_value"` is a plain string and cannot contain Python logic.

### 2. Forgetting to disable temperature prepend
If your start gcode handles heating, you MUST set:
```json
"material_bed_temp_prepend": { "value": false },
"material_print_temp_prepend": { "value": false },
"material_print_temp_wait": { "value": false }
```
Otherwise Cura will insert duplicate heating commands.

### 3. Using numeric types for constraint values
In fdmprinter.def.json, `maximum_value`, `minimum_value`, etc. MUST be strings:
```json
"maximum_value": "480"     // Correct
"maximum_value": 480       // Wrong
```

### 4. Forgetting settable_per_extruder for temperature settings
All temperature-related settings that can differ per extruder must have:
```json
"settable_per_extruder": true
```

### 5. Mirror/duplication mode using wrong temperature source
In mirror/duplication modes, both extruders must use **T0's temperature** (not their own), since they print the same geometry.

### 6. Not handling layer_0 temperature fallback
The nozzle temperature tag must check if `material_print_temperature_layer_0` is 0 (unset) and fall back to `material_print_temperature`. See the [Temperature Replacement Tag Pattern](#temperature-replacement-tag-pattern-idex).

### 7. JSON formatting after json.dump
When using `json.dump()` to write definition files, the output will be in K&R format (compact, not Cura's native indentation style). This is functionally correct but looks different from hand-crafted definitions. Both formats are valid.

### 8. Barrel heater GCode uses H prefix, not T
Nozzle commands: `M104 T0 S200` / `M109 T0 S200`
Barrel commands: `M104 H0 S350` / `M109 H0 S350`
Do NOT use `T` prefix for barrel heaters.

### 9. Metadata machine_extruder_trains must match extruder file IDs
The `"0": "penrose_600_idex_extruder_0"` in metadata must exactly match the extruder definition file without the `.def.json` extension.

### 10. Quality stubs missing `material` metadata field
When a printer has `has_materials: true` AND `has_variants: true`, quality stubs MUST include a `material` field matching the material's `base_file`. Without it, `MaterialNode._loadAll()` won't find the stubs, and Cura falls back to showing ALL global quality types (no nozzle filtering).

### 11. Setting `has_materials: false` in printer definition
This disables the entire material-aware quality filtering pipeline. ALL nozzles will see ALL quality types regardless of stubs. Always use `has_materials: true` for printers with quality profiles.

### 12. Wrong `quality_definition` or quality stub `definition` value
The printer's `quality_definition` metadata must match the `definition` field in ALL quality profile `.inst.cfg` files (both globals and stubs). A mismatch means profiles/stubs won't be found.

### 13. Variant name mismatch in quality stubs
The `variant` field in quality stubs must **exactly** match the variant file's `name` metadata (e.g., `Pellet 0.6 mm`). Even minor differences (case, spacing) will cause the stub to not be loaded for that nozzle.

### 14. Trying to use different layer heights for the same quality_type
Each `quality_type` has ONE global `layer_height`. You cannot have `pellet_030` mean 0.3mm for one nozzle and 0.35mm for another. Instead, create separate quality types (e.g., `pellet_030` and `pellet_035`).

### 15. Not enabling coasting for pellet extruders
`base_fracktal_printer` sets `bridge_wall_coast: 0` and `coasting_enable: false` — designed for filament. Pellet printers **must** override these since coasting is the primary ooze management tool when retraction is limited. Also remember `retraction_combing_max_distance` should be `0` (unlimited combing, no retraction during combing moves).

---

## Scripts Reference

### `scripts/generate_start_gcode.py`

Generates start/end gcode expressions for printer definitions.

```bash
# List available presets:
python scripts/generate_start_gcode.py --help

# Use preset:
python scripts/generate_start_gcode.py --printer penrose_600_idex

# Custom configuration:
python scripts/generate_start_gcode.py --type idex --barrel --pellet --name "My Printer"

# Write to definition file:
python scripts/generate_start_gcode.py --printer penrose_600_idex \
    --write resources/definitions/penrose_600_idex.def.json

# Validate existing file:
python scripts/generate_start_gcode.py --validate-only \
    --write resources/definitions/penrose_600_idex.def.json

# JSON output (for programmatic use):
python scripts/generate_start_gcode.py --printer penrose_600_idex --json
```

### `Variant Creator.py`

Interactive script for generating nozzle variant files. Run from the repository root.

### `resourcesRenamerUtility.py`

Utility for duplicating and renaming material profiles and related resources.

---

## Example: Creating a New Pellet IDEX Printer

Here is a complete checklist for creating a new pellet extruder IDEX printer similar to the Penrose 600 IDEX:

1. **Create definition**: `resources/definitions/my_printer_idex.def.json`
   - Set `"inherits": "base_fracktal_idex_printer"`
   - Set build volume, feedrates, acceleration from firmware config
   - Set `machine_barrel_heater`, temperature formula, temp prepend overrides

2. **Create extruders**: 
   - `resources/extruders/my_printer_idex_extruder_0.def.json`
   - `resources/extruders/my_printer_idex_extruder_1.def.json`

3. **Create variants**: `resources/variants/fracktalworks/My Printer IDEX/`
   - One `.inst.cfg` per nozzle size

4. **Generate gcode**:
   ```bash
   python scripts/generate_start_gcode.py --type idex --barrel --pellet \
       --name "My Printer IDEX" --write resources/definitions/my_printer_idex.def.json
   ```

5. **Add preset** to `scripts/generate_start_gcode.py` PRESETS dict for future re-generation

6. **Test**: Load in Fracktory, verify all print modes generate correct gcode
