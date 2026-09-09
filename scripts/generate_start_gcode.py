#!/usr/bin/env python3
"""
generate_start_gcode.py - Standalone Start/End GCode Expression Builder for AddiSlice

This script programmatically builds the Python expression strings used in Cura printer
definition files for machine_start_gcode and machine_end_gcode. These expressions use
Cura's replacement tag syntax: {setting_name, extruder_nr}

The generated expressions are compatible with Cura's GcodeStartEndFormatter class
(plugins/CuraEngineBackend/StartSliceJob.py) which evaluates them at slice time.

Usage:
    # Interactive mode (prompts for configuration):
    python scripts/generate_start_gcode.py

    # Generate for a specific printer definition:
    python scripts/generate_start_gcode.py --printer penrose_600_idex

    # Generate IDEX with barrel heater and pellet purge:
    python scripts/generate_start_gcode.py --type idex --barrel --pellet --name "Penrose 600 IDEX"

    # Generate single extruder with barrel heater:
    python scripts/generate_start_gcode.py --type single --barrel --pellet --name "Penrose 600"

    # Write directly to a printer definition JSON file:
    python scripts/generate_start_gcode.py --type idex --barrel --pellet --name "Penrose 600 IDEX" \
        --write resources/definitions/penrose_600_idex.def.json

    # Dry-run: show what would be generated without writing:
    python scripts/generate_start_gcode.py --type idex --barrel --pellet --name "My Printer" --dry-run

Architecture Notes:
    - IDEX start gcode uses "value" (Python expression) because it needs print_mode conditionals
    - Single extruder start gcode uses "default_value" (plain string with replacement tags)
    - End gcode always uses "default_value" (plain string)
    - Temperature replacement tags: {setting_name, extruder_nr} for IDEX, {setting_name} for single
    - The GcodeStartEndFormatter regex:
      r"{(?P<condition>if|else|elif|endif)?\\s*(?P<expression>.*?)\\s*(?:,\\s*(?P<extruder_nr_expr>.*))?\\s*}(?P<end_of_line>\\n?)"

Author: AddiPrint
"""

import argparse
import ast
import json
import os
import sys
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration Data Classes
# ---------------------------------------------------------------------------

class PrinterType(Enum):
    SINGLE = "single"
    IDEX = "idex"


class ExtruderType(Enum):
    FILAMENT = "filament"
    PELLET = "pellet"


@dataclass
class PrinterConfig:
    """Configuration for generating start/end gcode."""
    name: str = "My Printer"
    printer_type: PrinterType = PrinterType.SINGLE
    extruder_type: ExtruderType = ExtruderType.FILAMENT
    has_barrel_heater: bool = False
    has_heated_bed: bool = True

    # Gcode features
    include_header_comments: bool = True
    include_homing: bool = True
    include_bed_leveling: bool = True
    include_purge: bool = True
    include_melody: bool = False  # End-of-print melody

    # Single-mode tool binding — for one-head-at-a-time definitions that live
    # on an IDEX frame (e.g. Penrose 600 IDEX Choosable, where the idle
    # carriage parks and only one head prints).
    # tool_index: firmware tool this definition drives (0=left, 1=right).
    #             Heater commands (M104/M109 T<n>, H<n>) and tool select use it.
    # park_purge: purge off-bed at the tool's park side (same mechanics and
    #             positions as the dual-IDEX purge) instead of an on-bed line.
    # idex_frame: physical frame is IDEX — end gcode switches off BOTH nozzle
    #             heaters (plus the frame's H0 barrel defensively) and homes
    #             X/Y only, like the dual-IDEX end gcode.
    tool_index: int = 0
    park_purge: bool = False
    idex_frame: bool = False

    # center_purge: draw the on-bed purge line centered on the bed front
    # (X centered on machine_width/2 at Y0) instead of starting at the X0
    # corner. Emitted as {machine_width / 2 +- offset} replacement tags so the
    # line stays centered even if the definition's bed size changes. Avoids
    # edge/side complications (clips, docks, off-glass zones).
    center_purge: bool = False

    # Purge parameters (for pellet extruders)
    purge_height: float = 0.4
    purge_stages: list = field(default_factory=lambda: [
        {"distance": 30, "extrude": 5, "speed": 300},   # slow purge
        {"distance": 30, "extrude": 5, "speed": 500},   # medium purge
        {"distance": 40, "extrude": 5, "speed": 800},   # fast purge
    ])
    wipe_offset: float = 5.0
    wipe_height: float = 0.1

    # Filament purge parameters
    filament_purge_stages: list = field(default_factory=lambda: [
        {"distance": 15, "extrude": 2.5, "speed": 500},
        {"distance": 10, "extrude": 2.5, "speed": 650},
        {"distance": 10, "extrude": 2.5, "speed": 800},
    ])

    # IDEX off-bed purge positions (derived from Klipper config)
    # X: outside build area at each tool's park side
    # Y: near position_min (-10), front edge of machine travel
    # Klipper stepper_y position_min: -10, Y=-5 gives 5mm safety margin
    idex_purge_t0_x: float = -20.0
    idex_purge_t0_y: float = -5.0
    idex_purge_t1_x: float = 620.0
    idex_purge_t1_y: float = -5.0

    # IDEX pellet purge stages (Y-direction movement with cumulative extrusion)
    # Each stage: y_travel (mm of Y movement), extrude (mm of material), speed (mm/min)
    # Total extrusion: 1000mm for full barrel/melt-zone priming
    idex_pellet_purge_stages: list = field(default_factory=lambda: [
        {"y_travel": 30, "extrude": 150, "speed": 300},   # Phase 1: Slow prime
        {"y_travel": 30, "extrude": 200, "speed": 500},   # Phase 2: Medium purge
        {"y_travel": 40, "extrude": 300, "speed": 800},   # Phase 3: Fast purge
        {"y_travel": 40, "extrude": 350, "speed": 1000},  # Phase 4: Full speed
    ])  # Total: 1000mm extrusion over 140mm Y travel
    idex_purge_z: float = 3.0         # Z height during off-bed purge
    idex_purge_travel_z: float = 5.0  # Z height for travel moves around purge

    # Off-bed park purge stages for a FILAMENT head on an IDEX frame
    # (filament needs a short prime, not the 1000mm pellet barrel purge)
    idex_filament_purge_stages: list = field(default_factory=lambda: [
        {"y_travel": 15, "extrude": 5, "speed": 300},   # slow prime
        {"y_travel": 15, "extrude": 5, "speed": 500},   # medium purge
        {"y_travel": 10, "extrude": 5, "speed": 800},   # fast purge
    ])


# ---------------------------------------------------------------------------
# Template Tag Helpers
# ---------------------------------------------------------------------------

def nozzle_temp_tag(extruder_nr: int) -> str:
    """
    Generate a nozzle temperature replacement tag that handles the layer_0 fallback.

    If material_print_temperature_layer_0 is 0 (unset), falls back to material_print_temperature.
    This matches the pattern used in base_addiprint_idex_printer.def.json.

    Returns a Python expression fragment like:
        ("S{material_print_temperature, 0}" if extruderValue(0, 'material_print_temperature_layer_0') == 0
         else "S{material_print_temperature_layer_0, 0}")
    """
    n = extruder_nr
    return (
        f'("S{{material_print_temperature, {n}}}" '
        f"if extruderValue({n}, 'material_print_temperature_layer_0') == 0 "
        f'else "S{{material_print_temperature_layer_0, {n}}}")'
    )


def barrel_temp_tag(extruder_nr: int) -> str:
    """
    Generate a barrel heater temperature replacement tag.

    Barrel temperature uses material_barrel_temperature_layer_0 directly
    (it always resolves through the fallback chain in fdmprinter.def.json).

    Returns a string like: S{material_barrel_temperature_layer_0, 0}
    """
    return f"S{{material_barrel_temperature_layer_0, {extruder_nr}}}"


def nozzle_temp_tag_simple() -> str:
    """For single extruder printers: S{material_print_temperature_layer_0}"""
    return "S{material_print_temperature_layer_0}"


def barrel_temp_tag_simple() -> str:
    """For single extruder printers: S{material_barrel_temperature_layer_0}"""
    return "S{material_barrel_temperature_layer_0}"


# ---------------------------------------------------------------------------
# IDEX Heating Block Builders (for Python expression mode)
# ---------------------------------------------------------------------------

def _build_idex_heat_block_single(extruder_nr: int, has_barrel: bool) -> str:
    """
    Build heating commands for singleT0 or singleT1 mode.

    Pattern:
      M104 TN S{temp}    ;Heat nozzle N
      M104 HN S{barrel}  ;Heat barrel N  (if has_barrel)
      M190 S{bed}        ;Wait for bed
      M109 TN S{temp}    ;Wait for nozzle N
      M109 HN S{barrel}  ;Wait for barrel N  (if has_barrel)
    """
    n = extruder_nr
    nt = nozzle_temp_tag(n)
    lines = []
    lines.append(f'"M104 T{n} " + {nt} + "\\t;Heat nozzle {n}\\n"')
    if has_barrel:
        lines.append(f'"M104 H{n} {barrel_temp_tag(n)}\\t;Heat barrel {n}\\n"')
    lines.append('"M190 S{material_bed_temperature_layer_0} \\t;Wait until bed temperature reached\\n"')
    lines.append(f'"M109 T{n} " + {nt} + "\\t;Wait for nozzle {n}\\n"')
    if has_barrel:
        lines.append(f'"M109 H{n} {barrel_temp_tag(n)}\\t;Wait for barrel {n}\\n"')
    return " + ".join(lines)


def _build_idex_heat_block_dual(has_barrel: bool) -> str:
    """
    Build heating commands for dual mode.

    Pattern: Heat both → wait bed → wait each head (nozzle+barrel paired)
    Nozzle and barrel waits are grouped per extruder head to avoid
    thermal runaway from temperature differentials in the same head.
    """
    nt0 = nozzle_temp_tag(0)
    nt1 = nozzle_temp_tag(1)
    lines = []
    # Start heating both heads
    lines.append(f'"M104 T0 " + {nt0} + "\\t;Heat nozzle 0\\n"')
    if has_barrel:
        lines.append(f'"M104 H0 {barrel_temp_tag(0)}\\t;Heat barrel 0\\n"')
    lines.append(f'"M104 T1 " + {nt1} + "\\t;Heat nozzle 1\\n"')
    if has_barrel:
        lines.append(f'"M104 H1 {barrel_temp_tag(1)}\\t;Heat barrel 1\\n"')
    # Wait for bed
    lines.append('"M190 S{material_bed_temperature_layer_0} \\t;Wait until bed temperature reached\\n"')
    # Wait per head: nozzle + barrel paired (avoids thermal runaway)
    lines.append(f'"M109 T0 " + {nt0} + "\\t;Wait for nozzle 0\\n"')
    if has_barrel:
        lines.append(f'"M109 H0 {barrel_temp_tag(0)}\\t;Wait for barrel 0\\n"')
    lines.append(f'"M109 T1 " + {nt1} + "\\t;Wait for nozzle 1\\n"')
    if has_barrel:
        lines.append(f'"M109 H1 {barrel_temp_tag(1)}\\t;Wait for barrel 1\\n"')
    return " + ".join(lines)


def _build_idex_heat_block_mirror_dup(has_barrel: bool) -> str:
    """
    Build heating commands for mirror/duplication mode.

    In mirror/duplication, both extruders use T0's temperature settings
    (since the same material and settings are mirrored/duplicated).
    """
    nt0 = nozzle_temp_tag(0)
    lines = []
    # Heat both to T0's temperature
    lines.append(f'"M104 T0 " + {nt0} + "\\t;Heat nozzle 0\\n"')
    if has_barrel:
        lines.append(f'"M104 H0 {barrel_temp_tag(0)}\\t;Heat barrel 0\\n"')
    lines.append(f'"M104 T1 " + {nt0} + "\\t;Heat nozzle 1\\n"')
    if has_barrel:
        lines.append(f'"M104 H1 {barrel_temp_tag(0)}\\t;Heat barrel 1\\n"')
    # Wait for bed
    lines.append('"M190 S{material_bed_temperature_layer_0} \\t;Wait until bed temperature reached\\n"')
    # Wait per head: nozzle + barrel paired (avoids thermal runaway)
    lines.append(f'"M109 T0 " + {nt0} + "\\t;Wait for nozzle 0\\n"')
    if has_barrel:
        lines.append(f'"M109 H0 {barrel_temp_tag(0)}\\t;Wait for barrel 0\\n"')
    lines.append(f'"M109 T1 " + {nt0} + "\\t;Wait for nozzle 1\\n"')
    if has_barrel:
        lines.append(f'"M109 H1 {barrel_temp_tag(0)}\\t;Wait for barrel 1\\n"')
    return " + ".join(lines)


# ---------------------------------------------------------------------------
# IDEX Off-Bed Pellet Purge Builder
# ---------------------------------------------------------------------------

def _fnum(v: float) -> str:
    """Format a number for gcode: use int if whole number, else float."""
    return str(int(v)) if v == int(v) else str(v)


def _build_idex_pellet_purge(tool_nr: int, config) -> str:
    """
    Build off-bed purge gcode for a single IDEX pellet extruder tool.

    The purge happens at the tool's dedicated off-bed position (outside the
    build area). Material is extruded while moving in the Y direction to
    spread it out and prevent buildup at one spot. The purged material drops
    off the edge since there's no bed under the nozzle.

    Purge positions come from Klipper's PRINTER_VARIABLES:
      T0: X=-20 Y=10  (left of bed, near T0 park/pause position)
      T1: X=620 Y=10  (right of bed, near T1 park/pause position)

    Args:
        tool_nr: 0 or 1
        config: PrinterConfig with purge positions and stages

    Returns:
        str: Gcode lines joined with \\n escape sequences (for embedding
             in a Python expression string that Cura evaluates at slice time)
    """
    if tool_nr == 0:
        px, py = config.idex_purge_t0_x, config.idex_purge_t0_y
    else:
        px, py = config.idex_purge_t1_x, config.idex_purge_t1_y

    stages = config.idex_pellet_purge_stages
    pz = config.idex_purge_z
    tz = config.idex_purge_travel_z
    total_extrude = sum(s["extrude"] for s in stages)

    speed_labels = ["Slow prime", "Medium purge", "Fast purge", "Full speed"]

    lines = []
    lines.append(f"; --- T{tool_nr} Pellet Purge (off-bed X={_fnum(px)} Y={_fnum(py)}) ---")
    lines.append(f"T{tool_nr}")
    lines.append(f"G0 X{_fnum(px)} Y{_fnum(py)} Z{_fnum(tz)} F10000\\t;Move to T{tool_nr} purge position")
    lines.append(f"G0 Z{_fnum(pz)} F500\\t;Lower to purge height")
    lines.append("G92 E0\\t;Reset extruder")

    cum_y = py
    cum_e = 0
    for i, stage in enumerate(stages):
        cum_y += stage["y_travel"]
        cum_e += stage["extrude"]
        label = speed_labels[min(i, len(speed_labels) - 1)]
        lines.append(
            f"G1 Y{_fnum(cum_y)} E{_fnum(cum_e)} F{stage['speed']}"
            f"\\t;Phase {i + 1}: {label} ({stage['extrude']}mm)"
        )

    lines.append("G92 E0\\t;Reset extruder")
    lines.append(f"G0 Z{_fnum(tz)} F500\\t;Raise Z")

    return "\\n".join(lines) + "\\n"


def _center_x_tag(offset: float) -> str:
    """
    Replacement tag for an X coordinate relative to the bed center.

    Returns e.g. "{machine_width / 2 - 17.5}", "{machine_width / 2 + 12.5}"
    or "{machine_width / 2}". Evaluated by Cura's GcodeStartEndFormatter at
    slice time, so the purge line stays centered whatever the bed width is.
    """
    if offset == 0:
        return "{machine_width / 2}"
    sign = "+" if offset > 0 else "-"
    return f"{{machine_width / 2 {sign} {_fnum(abs(offset))}}}"


def _build_park_purge_single(config: "PrinterConfig") -> list:
    """
    Off-bed park-side purge for a single-mode definition on an IDEX frame.

    Same mechanics and positions as _build_idex_pellet_purge (select the tool,
    Y-sweep extrusion at the tool's park side, off the bed edge), but emitted
    as plain gcode lines for a "default_value" string rather than as an
    escaped Python-expression fragment. Pellet heads use the full barrel
    purge stages; filament heads use the short prime stages.

    Returns:
        list: plain gcode lines
    """
    t = config.tool_index
    if t == 0:
        px, py = config.idex_purge_t0_x, config.idex_purge_t0_y
    else:
        px, py = config.idex_purge_t1_x, config.idex_purge_t1_y

    if config.extruder_type == ExtruderType.PELLET:
        stages = config.idex_pellet_purge_stages
        what = "Pellet"
    else:
        stages = config.idex_filament_purge_stages
        what = "Filament"
    pz = config.idex_purge_z
    tz = config.idex_purge_travel_z
    speed_labels = ["Slow prime", "Medium purge", "Fast purge", "Full speed"]

    lines = []
    lines.append(f"; --- T{t} {what} Purge (off-bed X={_fnum(px)} Y={_fnum(py)}) ---")
    lines.append(f"T{t} ;select tool {t}")
    lines.append(f"G0 X{_fnum(px)} Y{_fnum(py)} Z{_fnum(tz)} F10000 ;move to T{t} purge position")
    lines.append(f"G0 Z{_fnum(pz)} F500 ;lower to purge height")
    lines.append("G92 E0 ;reset extruder")

    cum_y = py
    cum_e = 0
    for i, stage in enumerate(stages):
        cum_y += stage["y_travel"]
        cum_e += stage["extrude"]
        label = speed_labels[min(i, len(speed_labels) - 1)]
        lines.append(
            f"G1 Y{_fnum(cum_y)} E{_fnum(cum_e)} F{stage['speed']}"
            f" ;phase {i + 1}: {label} ({stage['extrude']}mm)"
        )

    lines.append("G92 E0 ;reset extruder")
    lines.append(f"G0 Z{_fnum(tz)} F500 ;raise Z")
    return lines


# ---------------------------------------------------------------------------
# Start GCode Expression Builder
# ---------------------------------------------------------------------------

def build_start_gcode_idex(config: PrinterConfig) -> str:
    """
    Build the complete machine_start_gcode Python expression for an IDEX printer.

    This generates a Python expression (string) that goes into the "value" field
    of machine_start_gcode in the printer definition JSON. Cura evaluates this
    expression at slice time, substituting print_mode and extruderValue() calls.

    The expression structure (pellet IDEX):
      header_comments + bed_heat +
      (singleT1_block if print_mode == 'singleT1' else '') +
      (singleT0_block if print_mode == 'singleT0' else '') +
      (dual_block if print_mode == 'dual' else '') +
      (mirror_dup_block if print_mode == 'mirror' or 'duplication' else '') +
      homing + bed_level +
      (t0_purge if print_mode != 'singleT1' else '') +
      (t1_purge if print_mode != 'singleT0' else '') +
      (tool_select) + print_mode_gcode + final_setup

    For filament IDEX, the original order is preserved:
      ...heating... + homing + print_mode_gcode + bed_level + on_bed_purge

    Returns:
        str: A Python expression string suitable for json.dump into a .def.json file
    """
    parts = []

    # --- Header comments ---
    if config.include_header_comments:
        header = (
            f"';Machine Model: {{machine_name}}\\n"
            f";Nozzle Size: T0 ' + str(extruderValue(0, 'machine_nozzle_size')) + ' T1 ' + str(extruderValue(1, 'machine_nozzle_size')) + '\\n"
            f";Sliced at: {{day}} {{date}} {{time}}\\n"
            f";Print mode: {{print_mode}}\\n"
            f";--- {config.name} "
        )
        if config.extruder_type == ExtruderType.PELLET:
            header += "Pellet Extruder "
        header += "Start GCode ---\\n"

        # Bed heating (always start heating bed first)
        if config.has_heated_bed:
            header += "M140 S{material_bed_temperature_layer_0} \\t;Heat build surface\\n'"
        else:
            header += "'"

        parts.append(header)

    # --- Print mode conditional heating blocks ---
    # singleT1: only heat extruder 1
    single_t1 = _build_idex_heat_block_single(1, config.has_barrel_heater)
    parts.append(f'({single_t1} if print_mode == \'singleT1\' else \'\')')

    # singleT0: only heat extruder 0
    single_t0 = _build_idex_heat_block_single(0, config.has_barrel_heater)
    parts.append(f'({single_t0} if print_mode == \'singleT0\' else \'\')')

    # dual: heat both extruders with independent temperatures
    dual = _build_idex_heat_block_dual(config.has_barrel_heater)
    parts.append(f'({dual} if print_mode == \'dual\' else \'\')')

    # mirror/duplication: heat both to T0's temperature
    mirror_dup = _build_idex_heat_block_mirror_dup(config.has_barrel_heater)
    parts.append(f'({mirror_dup} if print_mode == \'mirror\' or print_mode == \'duplication\' else \'\')')

    # --- Common gcode after heating ---
    # For pellet IDEX: homing → bed level → per-tool purge → print_mode_gcode
    # For filament IDEX: homing → print_mode_gcode → bed level → on-bed purge
    # Pellet IDEX purges at off-bed positions per-tool, which requires independent
    # mode (default after homing), so {print_mode_gcode} must come AFTER purge.
    is_pellet_idex = (config.extruder_type == ExtruderType.PELLET)

    common = ""
    if config.include_homing:
        common += (
            "G21 \\t\\t;metric values\\n"
            "G90 \\t\\t;absolute positioning\\n"
            "M107 \\t\\t;start with the fan off\\n"
            "G28 Z0 \\t\\t;move Z to min endstops\\n"
            "G28 X0 Y0 \\t;move X/Y to min endstops\\n"
            "G1 X0 Y0 Z5 F5000 \\t;safety Z axis movement\\n"
        )

    if is_pellet_idex:
        # Pellet IDEX: bed level FIRST, then off-bed purge, then print_mode_gcode
        if config.include_bed_leveling:
            common += (
                "\\nG29 \\t;Auto Bed Level\\n"
                "M500 \\t;Save Bed Level\\n"
            )
        parts.append(f"'{common}'")

        # --- IDEX pellet purge at off-bed positions ---
        if config.include_purge:
            t0_purge = _build_idex_pellet_purge(0, config)
            t1_purge = _build_idex_pellet_purge(1, config)

            # T0 purge: active for all modes except singleT1
            parts.append(f'("\\n{t0_purge}" if print_mode != \'singleT1\' else "")')
            # T1 purge: active for all modes except singleT0
            parts.append(f'("\\n{t1_purge}" if print_mode != \'singleT0\' else "")')
            # Select starting tool after purge (T0 for all except singleT1)
            parts.append(f'("T0\\n" if print_mode != \'singleT1\' else "")')

        # print_mode_gcode comes AFTER purge (purge needs independent mode)
        post = (
            "\\n{print_mode_gcode}\\n"
            "G4 P1\\nG4 P2\\nG4 P3\\n"
            "\\nG1 X0 Y0 Z5 F5000\\t;Move to start position\\n"
            "G92 E0\\t;zero the extruded length\\n"
        )
        parts.append(f"'{post}'")

    else:
        # Filament IDEX: original order (print_mode_gcode → bed level → purge)
        common += (
            "\\n{print_mode_gcode}\\n"
            "G4 P1\\nG4 P2\\nG4 P3\\n"
        )
        if config.include_bed_leveling:
            common += (
                "\\nG29 \\t;Auto Bed Level\\n"
                "M500 \\t;Save Bed Level\\n"
            )
        parts.append(f"'{common}'")

        # --- Original on-bed purge for filament IDEX ---
        if config.include_purge:
            purge = "\\n"
            purge += "; Extrude purge line\\n"
            stages = config.filament_purge_stages

            purge += "G1 X0 Y0 F10000\\n"
            purge += "G92 E0 ;reset extruder position\\n"
            purge += f"G0 Z{config.purge_height} F500 ;move to purge height\\n"

            cumulative_x = 0
            for i, stage in enumerate(stages):
                speed_label = ["slow", "medium", "fast"][min(i, 2)]
                purge += f"G0 X{cumulative_x + stage['distance']} E{stage['extrude']} F{stage['speed']} ;{speed_label} purge\\n"
                purge += "G92 E0 ;reset extruder position\\n"
                cumulative_x += stage["distance"]

            # Wipe move
            purge += f"G0 X{{{cumulative_x} + {config.wipe_offset}}} Z{{{config.wipe_height}}} F{{8000}} ;wipe move close to bed\\n"
            purge += f"G0 X{{{cumulative_x} + {config.wipe_offset * 2}}} Z{config.purge_height} F{{8000}} ;wipe move away from bed\\n"
            purge += "G1 X0 Y0 Z3 F5000 \\t;safety Z axis movement\\n"
            purge += "G92 E0 ;zero the extruded length\\n"
            parts.append(f"'{purge}'")

    # Join all parts with " + "
    return " + ".join(parts)


def build_start_gcode_single(config: PrinterConfig) -> str:
    """
    Build the machine_start_gcode default_value for a single-extruder printer.

    Single extruder printers use a plain string with {replacement_tags}
    in the "default_value" field (not a Python expression).

    Returns:
        str: A gcode string with replacement tags, suitable for "default_value"
    """
    lines = []

    if config.include_header_comments:
        lines.append(f";Machine Model: {{machine_name}}")
        lines.append(";Nozzle Size: {machine_nozzle_size}")
        lines.append(";Sliced at: {day} {date} {time}")
        lines.append(f";--- {config.name} ", )
        if config.extruder_type == ExtruderType.PELLET:
            lines[-1] += "Pellet Extruder "
        lines[-1] += "Start GCode ---"

    # Heating sequence (T<n>/H<n> follow tool_index for IDEX-frame single mode)
    t = config.tool_index
    if config.has_heated_bed:
        lines.append("M140 S{material_bed_temperature_layer_0} \t;Heat build surface")
    lines.append(f"M104 T{t} S{{material_print_temperature_layer_0}} \t;Heat nozzle")
    if config.has_barrel_heater:
        lines.append(f"M104 H{t} S{{material_barrel_temperature_layer_0}} \t;Heat barrel")
    if config.has_heated_bed:
        lines.append("M190 S{material_bed_temperature_layer_0} \t;Wait for bed temperature")
    lines.append(f"M109 T{t} S{{material_print_temperature_layer_0}} \t;Wait for nozzle temperature")
    if config.has_barrel_heater:
        lines.append(f"M109 H{t} S{{material_barrel_temperature_layer_0}} \t;Wait for barrel temperature")

    # Homing and setup
    if config.include_homing:
        lines.append("G21 ;metric values")
        lines.append("M107 ;fan off")
        if config.idex_frame:
            lines.append("G90 ;absolute positioning")
            lines.append("G28 Z0 ;move Z to min endstops")
            lines.append("G28 X0 Y0 ;move X/Y to min endstops")
            lines.append("G1 X0 Y0 Z5 F5000 ;safety Z axis movement")
        else:
            lines.append("G28 ;home all axes")
            lines.append("M420 S1 ;restore bed level mesh")
            lines.append("G90 ;absolute positioning")
            lines.append("G1 X0 Y0 Z5 F5000 ;move nozzle up 5mm for safe homing")

    if config.include_bed_leveling:
        lines.append("G29 ;auto bed leveling")
        lines.append("M500 ;save settings")

    lines.append("M82 ;set extruder to absolute mode")
    lines.append("M107 ;start with the fan off")

    # On-bed purge geometry (also needed for the pre-purge travel move)
    on_bed_stages = (config.purge_stages if config.extruder_type == ExtruderType.PELLET
                     else config.filament_purge_stages)
    purge_length = sum(s["distance"] for s in on_bed_stages)

    if config.park_purge:
        pass  # park purge block below handles its own travel
    elif config.center_purge and config.include_purge:
        # IDEX-frame single-mode definitions must select their tool before
        # any travel (heaters were already addressed via T<n> commands).
        if config.idex_frame:
            lines.append(f"T{config.tool_index} ;select tool {config.tool_index}")
        lines.append(
            f"G1 X{_center_x_tag(-purge_length / 2)} Y0 Z15.0 F5000"
            " ;move to purge start (front center of bed)"
        )
    else:
        lines.append("G1 X0 Y0 Z15.0 F5000 ;move the platform down 15mm")

    # Purge sequence
    if config.include_purge and config.park_purge:
        # Off-bed park-side purge (IDEX frame, one active head)
        lines.append("")
        lines.extend(_build_park_purge_single(config))
    elif config.include_purge:
        lines.append("")
        if config.extruder_type == ExtruderType.PELLET:
            lines.append("; Pellet extruder purge sequence")
        else:
            lines.append("; Extrude purge line")
        stages = on_bed_stages

        lines.append("G92 E0 ;reset extruder position")
        lines.append(f"G0 Z{config.purge_height} F500 ;move to purge height")

        cumulative_x = 0
        for i, stage in enumerate(stages):
            speed_label = ["slow", "medium", "fast"][min(i, 2)]
            end = cumulative_x + stage["distance"]
            x_str = _center_x_tag(end - purge_length / 2) if config.center_purge else str(end)
            lines.append(f"G0 X{x_str} E{stage['extrude']} F{stage['speed']} ;{speed_label} purge")
            lines.append("G92 E0 ;reset extruder position")
            cumulative_x = end

        if config.center_purge:
            wipe_1 = _center_x_tag(purge_length / 2 + config.wipe_offset)
            wipe_2 = _center_x_tag(purge_length / 2 + config.wipe_offset * 2)
            lines.append(f"G0 X{wipe_1} Z{{{config.wipe_height}}} F{{8000}} ;wipe move close to bed")
            lines.append(f"G0 X{wipe_2} Z{config.purge_height} F{{8000}} ;wipe move away from bed")
        else:
            lines.append(f"G0 X{{{cumulative_x} + {config.wipe_offset}}} Z{{{config.wipe_height}}} F{{8000}} ;wipe move close to bed")
            lines.append(f"G0 X{{{cumulative_x} + {config.wipe_offset * 2}}} Z{config.purge_height} F{{8000}} ;wipe move away from bed")

    lines.append("")
    lines.append("G92 E0 ;zero the extruded length")
    lines.append("M117 Printing...")

    # Optional melody
    if config.include_melody:
        lines.append("")
        lines.append("M300 S880 P166")
        lines.append("M300 S0 P166")
        lines.append("M300 S880 P166")
        lines.append("M300 S1318 P166")
        lines.append("M300 S1567 P166")
        lines.append("M300 S0 P166")

    return "\n".join(lines) + "\n"


def build_end_gcode(config: PrinterConfig) -> str:
    """
    Build the machine_end_gcode default_value string.

    Both IDEX and single extruder printers use "default_value" for end gcode
    (plain string, not a Python expression).

    Returns:
        str: End gcode string
    """
    lines = []

    # Header
    lines.append(f";--- {config.name} ", )
    if config.extruder_type == ExtruderType.PELLET:
        lines[-1] += "Pellet Extruder "
    lines[-1] += "End GCode ---"

    # Turn off heaters. On an IDEX frame (dual OR single-mode) switch off BOTH
    # nozzle heaters; the frame's H0 pellet barrel is switched off defensively
    # even from the filament definition, since the hardware always has it.
    t = config.tool_index
    on_idex_frame = config.printer_type == PrinterType.IDEX or config.idex_frame
    lines.append(f"M104 T{t} S0 ;nozzle {t} heater off")
    if on_idex_frame:
        lines.append(f"M104 T{1 - t} S0 ;nozzle {1 - t} heater off")
    if config.has_barrel_heater:
        lines.append(f"M104 H{t} S0 ;barrel heater {t} off")
        if config.printer_type == PrinterType.IDEX:
            lines.append(f"M104 H{1 - t} S0 ;barrel heater {1 - t} off")
    elif config.idex_frame:
        lines.append("M104 H0 S0 ;frame barrel heater off (defensive)")
    if config.has_heated_bed:
        lines.append("M140 S0 ;heated bed heater off")

    # Movement and shutdown
    lines.append("G91 ;relative positioning")
    if config.extruder_type == ExtruderType.FILAMENT:
        lines.append("G1 Z+0.5 E-5 Y+10 F12000 ;move Z up a bit and retract filament")
    else:
        lines.append("G1 Z+0.5 E-2 F3000 ;move Z up a bit and retract slightly")

    if on_idex_frame:
        lines.append("G28 X0 Y0 ;move X/Y to home")
    else:
        lines.append("G28 ;move to home")

    lines.append("M84 ;steppers off")
    lines.append("M107 ;fan off")
    lines.append("G90 ;absolute positioning")

    # Optional melody
    if config.include_melody:
        lines.append("")
        lines.append("M300 S0 P333")
        lines.append("M300 S880 P166")
        lines.append("M300 S880 P166")
        lines.append("M300 S1318 P166")
        lines.append("M300 S1567 P166")
        lines.append("M300 S0 P166")
        lines.append("M300 S880 P166")
        lines.append("M300 S0 P166")
        lines.append("M300 S880 P166")
        lines.append("M300 S0 P166")
        lines.append("M300 S880 P166")
        lines.append("M300 S0 P166")
        lines.append("M300 S1567 P166")
        lines.append("M300 S0 P166")
        lines.append("M300 S880 P166")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_expression(expression: str) -> tuple:
    """
    Validate a Python expression string by parsing it with ast.parse.

    IDEX start gcode uses Python expressions in "value" fields. These expressions
    must be valid Python that Cura can evaluate at slice time.

    Note: The expression references Cura-specific functions (extruderValue, print_mode)
    that won't be available at validation time, so we only check syntax.

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    try:
        ast.parse(expression, mode='eval')
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at offset {e.offset}: {e.msg}"


def validate_replacement_tags(gcode: str) -> list:
    """
    Check that all replacement tags in a gcode string are properly formed.

    Valid formats:
        {setting_name}
        {setting_name, extruder_nr}
        {if condition}...{endif}

    Returns:
        list: List of warning messages (empty if all tags are valid)
    """
    import re
    warnings = []
    # Find all {...} tags
    tags = re.findall(r'\{([^}]+)\}', gcode)
    known_settings = {
        'machine_name', 'machine_nozzle_size', 'day', 'date', 'time',
        'print_mode', 'print_mode_gcode',
        'material_print_temperature', 'material_print_temperature_layer_0',
        'material_bed_temperature_layer_0',
        'material_barrel_temperature_layer_0',
    }
    for tag in tags:
        tag = tag.strip()
        # Skip numeric expressions like "100 + 5"
        if any(c.isdigit() for c in tag) and any(op in tag for op in ['+', '-', '*', '/']):
            continue
        # Check if it's a known setting or setting,extruder pair
        parts = [p.strip() for p in tag.split(',')]
        setting_name = parts[0]
        if setting_name not in known_settings and not setting_name.startswith('if ') and setting_name not in ('else', 'elif', 'endif'):
            warnings.append(f"Unknown setting in tag: {{{tag}}}")
    return warnings


# ---------------------------------------------------------------------------
# JSON File Operations
# ---------------------------------------------------------------------------

def read_definition(filepath: str) -> dict:
    """Read a printer definition JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_definition(filepath: str, definition: dict):
    """
    Write a printer definition JSON file.

    Uses json.dump with indent=4 for consistent formatting.
    Note: This produces K&R style formatting (consistent with json.dump defaults).
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(definition, f, indent=4, ensure_ascii=False)
        f.write('\n')


def update_definition_gcode(filepath: str, start_gcode: str, end_gcode: str,
                             printer_type: PrinterType, dry_run: bool = False) -> bool:
    """
    Update machine_start_gcode and machine_end_gcode in a printer definition file.

    For IDEX printers: start_gcode goes into "value" (Python expression)
    For single extruder: start_gcode goes into "default_value" (plain string)
    End gcode always goes into "default_value".

    Args:
        filepath: Path to the .def.json file
        start_gcode: The generated start gcode expression/string
        end_gcode: The generated end gcode string
        printer_type: SINGLE or IDEX
        dry_run: If True, don't write, just validate

    Returns:
        bool: True if successful
    """
    definition = read_definition(filepath)

    if 'overrides' not in definition:
        definition['overrides'] = {}

    # Set start gcode
    if printer_type == PrinterType.IDEX:
        definition['overrides']['machine_start_gcode'] = {"value": start_gcode}
    else:
        definition['overrides']['machine_start_gcode'] = {"default_value": start_gcode}

    # Set end gcode
    definition['overrides']['machine_end_gcode'] = {"default_value": end_gcode}

    if dry_run:
        print(f"[DRY RUN] Would update: {filepath}")
        return True

    write_definition(filepath, definition)
    print(f"Updated: {filepath}")
    return True


# ---------------------------------------------------------------------------
# Preset Configurations
# ---------------------------------------------------------------------------

PRESETS = {
    "penrose_600_idex": PrinterConfig(
        name="Penrose 600 IDEX",
        printer_type=PrinterType.IDEX,
        extruder_type=ExtruderType.PELLET,
        has_barrel_heater=True,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=False,
    ),
    "penrose_600": PrinterConfig(
        name="Penrose 600",
        printer_type=PrinterType.SINGLE,
        extruder_type=ExtruderType.PELLET,
        has_barrel_heater=True,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=True,
    ),
    "base_idex_filament": PrinterConfig(
        name="IDEX Filament Printer",
        printer_type=PrinterType.IDEX,
        extruder_type=ExtruderType.FILAMENT,
        has_barrel_heater=False,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=False,
    ),
    "base_single_filament": PrinterConfig(
        name="Single Filament Printer",
        printer_type=PrinterType.SINGLE,
        extruder_type=ExtruderType.FILAMENT,
        has_barrel_heater=False,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=False,
    ),
    "penrose_600_swappable_pellet": PrinterConfig(
        name="Penrose 600 Swappable (Pellet)",
        printer_type=PrinterType.SINGLE,
        extruder_type=ExtruderType.PELLET,
        has_barrel_heater=True,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=True,
        center_purge=True,
    ),
    "penrose_600_swappable_fdm": PrinterConfig(
        name="Penrose 600 Swappable (Filament)",
        printer_type=PrinterType.SINGLE,
        extruder_type=ExtruderType.FILAMENT,
        has_barrel_heater=False,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=True,
        center_purge=True,
    ),
    "penrose_600_idex_choosable_pellet": PrinterConfig(
        name="Penrose 600 IDEX Choosable (Pellet)",
        printer_type=PrinterType.SINGLE,
        extruder_type=ExtruderType.PELLET,
        has_barrel_heater=True,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=False,
        tool_index=0,
        idex_frame=True,
        center_purge=True,
    ),
    "penrose_600_idex_choosable_fdm": PrinterConfig(
        name="Penrose 600 IDEX Choosable (Filament)",
        printer_type=PrinterType.SINGLE,
        extruder_type=ExtruderType.FILAMENT,
        has_barrel_heater=False,
        has_heated_bed=True,
        include_header_comments=True,
        include_homing=True,
        include_bed_leveling=True,
        include_purge=True,
        include_melody=False,
        tool_index=1,
        idex_frame=True,
        center_purge=True,
    ),
}


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def build_gcode(config: PrinterConfig) -> tuple:
    """
    Build both start and end gcode for the given configuration.

    Returns:
        tuple: (start_gcode: str, end_gcode: str)
    """
    if config.printer_type == PrinterType.IDEX:
        start_gcode = build_start_gcode_idex(config)
    else:
        start_gcode = build_start_gcode_single(config)

    end_gcode = build_end_gcode(config)
    return start_gcode, end_gcode


def main():
    parser = argparse.ArgumentParser(
        description="Generate start/end GCode expressions for AddiSlice printer definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s --printer penrose_600_idex
              %(prog)s --type idex --barrel --pellet --name "My IDEX Printer"
              %(prog)s --type single --name "My Printer" --write resources/definitions/my_printer.def.json
              %(prog)s --printer penrose_600_idex --dry-run

            Available presets: {presets}
        """.format(presets=", ".join(PRESETS.keys())))
    )

    # Preset or manual configuration
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--printer", choices=list(PRESETS.keys()),
                       help="Use a predefined printer configuration")
    group.add_argument("--type", choices=["single", "idex"],
                       help="Printer type (single extruder or IDEX)")

    # Manual configuration options
    parser.add_argument("--name", default="My Printer",
                       help="Printer name for gcode comments")
    parser.add_argument("--barrel", action="store_true",
                       help="Enable barrel heater support")
    parser.add_argument("--pellet", action="store_true",
                       help="Use pellet extruder purge sequence")
    parser.add_argument("--no-bed", action="store_true",
                       help="Disable heated bed")
    parser.add_argument("--no-purge", action="store_true",
                       help="Disable purge sequence")
    parser.add_argument("--no-leveling", action="store_true",
                       help="Disable auto bed leveling")
    parser.add_argument("--melody", action="store_true",
                       help="Add end-of-print melody")

    # Output options
    parser.add_argument("--write", metavar="FILE",
                       help="Write gcode to a printer definition JSON file")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show output without writing to file")
    parser.add_argument("--json", action="store_true",
                       help="Output as JSON (for programmatic use)")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate an existing printer definition file")

    args = parser.parse_args()

    # Build configuration
    if args.printer:
        config = PRESETS[args.printer]
    elif args.type:
        config = PrinterConfig(
            name=args.name,
            printer_type=PrinterType(args.type),
            extruder_type=ExtruderType.PELLET if args.pellet else ExtruderType.FILAMENT,
            has_barrel_heater=args.barrel,
            has_heated_bed=not args.no_bed,
            include_purge=not args.no_purge,
            include_bed_leveling=not args.no_leveling,
            include_melody=args.melody,
        )
    elif args.validate_only and args.write:
        # Validate existing file
        filepath = args.write
        try:
            definition = read_definition(filepath)
            overrides = definition.get('overrides', {})
            start = overrides.get('machine_start_gcode', {})

            if 'value' in start:
                is_valid, error = validate_expression(start['value'])
                if is_valid:
                    print(f"PASS: {filepath} - start gcode expression is valid Python")
                else:
                    print(f"FAIL: {filepath} - {error}")
                    sys.exit(1)
            elif 'default_value' in start:
                warnings = validate_replacement_tags(start['default_value'])
                if warnings:
                    for w in warnings:
                        print(f"WARNING: {w}")
                else:
                    print(f"PASS: {filepath} - start gcode tags look valid")
            else:
                print(f"INFO: {filepath} - no start gcode found in overrides")

        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        return
    else:
        # Interactive mode or show help
        parser.print_help()
        print("\n--- Quick examples ---")
        print("  python scripts/generate_start_gcode.py --printer penrose_600_idex")
        print("  python scripts/generate_start_gcode.py --type idex --barrel --pellet --name 'My Printer'")
        return

    # Generate gcode
    start_gcode, end_gcode = build_gcode(config)

    # Validate IDEX expressions
    if config.printer_type == PrinterType.IDEX:
        is_valid, error = validate_expression(start_gcode)
        if not is_valid:
            print(f"ERROR: Generated expression has syntax error: {error}", file=sys.stderr)
            print(f"\nExpression:\n{start_gcode}", file=sys.stderr)
            sys.exit(1)
        print("Validation: Start gcode expression is valid Python syntax")

    # Output
    if args.json:
        output = {
            "printer_type": config.printer_type.value,
            "start_gcode": {
                "field": "value" if config.printer_type == PrinterType.IDEX else "default_value",
                "content": start_gcode,
            },
            "end_gcode": {
                "field": "default_value",
                "content": end_gcode,
            }
        }
        print(json.dumps(output, indent=2))
    elif args.write:
        update_definition_gcode(
            args.write, start_gcode, end_gcode,
            config.printer_type, dry_run=args.dry_run
        )
    else:
        field_name = "value" if config.printer_type == PrinterType.IDEX else "default_value"
        print(f"\n{'='*60}")
        print(f"machine_start_gcode (\"{field_name}\"):")
        print(f"{'='*60}")
        print(start_gcode)
        print(f"\n{'='*60}")
        print(f"machine_end_gcode (\"default_value\"):")
        print(f"{'='*60}")
        print(end_gcode)

    if args.dry_run:
        print("\n[DRY RUN] No files were modified.")


if __name__ == "__main__":
    main()
