# Copyright (c) 2025
# The PostProcessingPlugin is released under the terms of the LGPLv3 or higher.

# This script is designed for pellet extruder 3D printers.
# It inserts a MIX_HOPPER G-code command after every configured amount
# of extrusion (default 1000mm) to mix the pellets in the hopper.

from ..Script import Script
from UM.Application import Application

from typing import List


class MixHopper(Script):
    """Inserts MIX_HOPPER G-code periodically based on extrusion distance.

    Designed for pellet extruder 3D printers to keep hopper material mixed.
    """

    def getSettingDataString(self) -> str:
        return """{
            "name": "Mix Hopper (Pellet Extruder)",
            "key": "MixHopper",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "enabled":
                {
                    "label": "Enable",
                    "description": "Enable or disable the Mix Hopper script.",
                    "type": "bool",
                    "default_value": true
                },
                "extrusion_interval":
                {
                    "label": "Extrusion Interval",
                    "description": "Insert MIX_HOPPER command after this many millimeters of extrusion.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 2000.0,
                    "minimum_value": 100,
                    "enabled": "enabled"
                },
                "mix_gcode":
                {
                    "label": "Mix G-code Command",
                    "description": "The G-code command to send for mixing the hopper.",
                    "type": "str",
                    "default_value": "MIX_HOPPER",
                    "enabled": "enabled"
                }
            }
        }"""

    def execute(self, data: List[str]) -> List[str]:
        if not self.getSettingValueByKey("enabled"):
            return data

        extrusion_interval = self.getSettingValueByKey("extrusion_interval")
        mix_gcode = self.getSettingValueByKey("mix_gcode")

        relative_extrusion = Application.getInstance().getGlobalContainerStack().getProperty(
            "relative_extrusion", "value"
        )

        cumulative_extrusion = 0.0
        last_e = 0.0
        next_threshold = extrusion_interval

        for layer_index, layer in enumerate(data):
            lines = layer.split("\n")
            new_lines = []

            for line in lines:
                # Skip comments and empty lines for extrusion tracking
                stripped = line.strip()
                if stripped.startswith(";") or stripped == "":
                    new_lines.append(line)
                    continue

                # Only track G0/G1 moves
                if not (stripped.startswith("G0 ") or stripped.startswith("G1 ") or
                        stripped.startswith("G0\t") or stripped.startswith("G1\t")):
                    # Check for relative/absolute extrusion mode switches
                    if stripped == "M82":
                        relative_extrusion = False
                    elif stripped == "M83":
                        relative_extrusion = True
                    # Reset E tracking on G92 E
                    elif stripped.startswith("G92"):
                        e_val = self.getValue(stripped, "E", None)
                        if e_val is not None:
                            last_e = e_val
                    new_lines.append(line)
                    continue

                e_value = self.getValue(stripped, "E", None)
                if e_value is not None:
                    if relative_extrusion:
                        extrusion_delta = e_value
                    else:
                        extrusion_delta = e_value - last_e
                        last_e = e_value

                    # Only count positive extrusion (not retractions)
                    if extrusion_delta > 0:
                        cumulative_extrusion += extrusion_delta

                new_lines.append(line)

                # Check if we crossed the threshold
                if cumulative_extrusion >= next_threshold:
                    new_lines.append(f"{mix_gcode} ; Mix hopper at {cumulative_extrusion:.1f}mm extrusion")
                    next_threshold += extrusion_interval

            data[layer_index] = "\n".join(new_lines)

        return data
