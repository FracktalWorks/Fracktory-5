# Nozzle Material Info Plugin

## Description

This Cura plugin automatically adds nozzle size and material information to the beginning of every sliced G-code file. The information is added as comments in a standardized format.

## Output Format

The plugin adds the following header to your G-code files:

```gcode
; file data begin
;nozzle_t0=0.4
;nozzle_t1=0.4
;material_t0=Ultimaker PLA
;material_t1=N/A
; file data end
```

## Features

- **Automatic**: Works automatically after slicing, no manual intervention required
- **Dual Extruder Support**: Shows information for both T0 and T1 extruders
- **Single Extruder Compatible**: Shows "N/A" for unused extruders
- **Material Information**: Displays brand and material name (e.g., "Ultimaker PLA")
- **Nozzle Size**: Shows nozzle diameter in millimeters

## Information Extracted

### Nozzle Size (T0/T1)
- Primary source: `machine_nozzle_size` setting from extruder stack
- Fallback: Variant container metadata
- Format: Decimal number (e.g., "0.4", "0.8")

### Material Information (T0/T1)
- Primary: Brand + Material Name (e.g., "Ultimaker PLA")
- Fallback: Material Name only
- Last resort: Material type
- Shows "N/A" if no material is loaded

## Installation

1. Copy the `NozzleMaterialInfo` folder to your Cura plugins directory:
   - Windows: `%APPDATA%\cura\<version>\plugins\`
   - macOS: `~/Library/Application Support/cura/<version>/plugins/`
   - Linux: `~/.local/share/cura/<version>/plugins/`

2. Restart Cura

3. The plugin will automatically start working - no configuration needed!

## Technical Details

- **Plugin Type**: Extension
- **Hook Point**: `slicingFinished` signal from backend
- **API Version**: 8
- **Dependencies**: Cura 5.x compatible

## Troubleshooting

Check the Cura log files if the plugin doesn't seem to be working. The plugin logs informational messages when it successfully adds the header information.

## License

Copyright (c) 2025 FracktalWorks
This plugin is released under the terms of the LGPLv3 or higher.