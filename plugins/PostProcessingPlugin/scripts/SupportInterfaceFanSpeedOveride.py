# Cura Post Processing Plugin Boilerplate
# Save this file in the Cura post processing scripts directory (e.g., C:\Program Files\Ultimaker Cura <version>\plugins\PostProcessingPlugin\scripts)

import re #To perform the search

from ..Script import Script

from UM.Application import Application
from UM.Logger import Logger
from UM.Message import Message
from UM.i18n import i18nCatalog


class SupportInterfaceFanSpeedOveride(Script):
    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """
        {
            "name": "Support Interface Fan Speed Override",
            "key": "SupportInterfaceFanSpeedOverride",
            "metadata": {},
            "version": 2,
            "settings": {
                "support_interface_fan_speed": {
                    "label": "Support Interface Fan Speed (%)",
                    "description": "Set the fan speed (0-100%) for support interface sections.",
                    "type": "int",
                    "default_value": 50,
                    "minimum_value": 0,
                    "maximum_value": 100
                },
                "support_fan_speed": {
                    "label": "Support Fan Speed (%)",
                    "description": "Set the fan speed (0-100%) for support sections (not interface).",
                    "type": "int",
                    "default_value": 50,
                    "minimum_value": 0,
                    "maximum_value": 100
                }
            }
        }
        """

    def execute(self, data):
        # 'data' is a list of G-code layers (each a string)
        support_interface_marker = ";TYPE:SUPPORT-INTERFACE"
        support_marker = ";TYPE:SUPPORT"
        type_marker = ";TYPE:"
        mesh_marker = ";MESH"
        m106_cmd = re.compile(r"M106 ?S(\d+)")
        custom_fan_speed_interface = int(self.getSettingValueByKey("support_interface_fan_speed"))
        custom_fan_speed_support = int(self.getSettingValueByKey("support_fan_speed"))
        custom_fan_speed_gcode_interface = f"M106 S{int(custom_fan_speed_interface * 255 / 100)}"
        custom_fan_speed_gcode_support = f"M106 S{int(custom_fan_speed_support * 255 / 100)}"

        in_support_interface = False
        in_support = False
        last_fan_speed_gcode = None

        for layer_index, layer in enumerate(data):
            lines = layer.split("\n")
            output_lines = []

            for line in lines:
                # Track last M106 before support interface/support
                m106_match = m106_cmd.match(line.strip())
                if m106_match and not in_support_interface and not in_support:
                    last_fan_speed_gcode = line.strip()

                # Detect start of support interface
                if (not in_support_interface) and (support_interface_marker in line):
                    in_support_interface = True
                    output_lines.append(line)
                    output_lines.append(f"; Set custom fan speed for support interface")
                    output_lines.append(f"; Added: {custom_fan_speed_gcode_interface}")
                    output_lines.append(custom_fan_speed_gcode_interface)
                    continue

                # Detect start of support (not interface)
                if (not in_support) and (support_marker in line) and (support_interface_marker not in line):
                    in_support = True
                    output_lines.append(line)
                    output_lines.append(f"; Set custom fan speed for support")
                    output_lines.append(f"; Added: {custom_fan_speed_gcode_support}")
                    output_lines.append(custom_fan_speed_gcode_support)
                    continue

                # Detect end of support interface
                if in_support_interface and (
                    ((type_marker in line) and (support_interface_marker not in line)) or (mesh_marker in line)
                ):
                    in_support_interface = False
                    if last_fan_speed_gcode:
                        output_lines.append(f"; Restore previous fan speed after support interface")
                        output_lines.append(f"; Restored: {last_fan_speed_gcode}")
                        output_lines.append(last_fan_speed_gcode)
                    else:
                        output_lines.append(f"; No previous fan speed found to restore after support interface")

                # Detect end of support (not interface)
                if in_support and (
                    ((type_marker in line) and (support_marker not in line)) or (mesh_marker in line)
                ):
                    in_support = False
                    if last_fan_speed_gcode:
                        output_lines.append(f"; Restore previous fan speed after support")
                        output_lines.append(f"; Restored: {last_fan_speed_gcode}")
                        output_lines.append(last_fan_speed_gcode)
                    else:
                        output_lines.append(f"; No previous fan speed found to restore after support")

                output_lines.append(line)

            data[layer_index] = "\n".join(output_lines)
        return data
