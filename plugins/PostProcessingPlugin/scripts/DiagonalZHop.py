# DiagonalZHop
"""
DiagonalZHop for 3D prints.

Diagonal Z Hop

Author: 5axes
Version: 0.2

Note : https://github.com/Ultimaker/Cura/issues/15583
"""

import re #To perform the search

from ..Script import Script

from UM.Application import Application
from UM.Logger import Logger
from UM.Message import Message
from UM.i18n import i18nCatalog

catalog = i18nCatalog("cura")

__version__ = '0.2'
       
class DiagonalZHop(Script):
    def getSettingDataString(self):
        return """{
            "name": "Diagonal Z Hop",
            "key": "DiagonalZHop",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "extruder_nb":
                {
                    "label": "Extruder Id",
                    "description": "Define extruder Id in case of multi extruders",
                    "unit": "",
                    "type": "int",
                    "default_value": 1
                }
            }
        }"""

## -----------------------------------------------------------------------------
#
#  Main Prog
#
## -----------------------------------------------------------------------------
    def execute(self, data):
        
        extruder_id  = self.getSettingValueByKey("extruder_nb")
        extruder_id = extruder_id -1

        #   machine_extruder_count
        extruder_count=Application.getInstance().getGlobalContainerStack().getProperty("machine_extruder_count", "value")
        extruder_count = extruder_count-1
        if extruder_id>extruder_count :
            extruder_id=extruder_count

        extrud = Application.getInstance().getGlobalContainerStack().extruderList
        
        # Get the Cura retraction_hop and speed_z_hop as Zhop parameter
        retraction_hop = float(extrud[extruder_id].getProperty("retraction_hop", "value"))
        speed_z_hop = int(extrud[extruder_id].getProperty("speed_z_hop", "value"))
        speed_z_hop = speed_z_hop * 60

        # Check if Z hop is desactivated
        retraction_hop_enabled= extrud[extruder_id].getProperty("retraction_hop_enabled", "value")
        if retraction_hop_enabled == False:
            #
            Logger.log('d', 'Mode Z Hop must be activated !')
            Message(catalog.i18nc("@message", "Mode Z Hop must be activated !"), title = catalog.i18nc("@info:title", "Post Processing")).show()
            return data
            
        current_z = 0.0
        for layer_index, layer in enumerate(data):
            lines = layer.split("\n")
            
            for line_index, currentLine in enumerate(lines):
                # Track current Z position using regex to extract Z value
                if currentLine.startswith("G0") or currentLine.startswith("G1"):
                    z_match = re.search(r"Z(\d+\.?\d*)", currentLine)
                    if z_match:
                        new_z = float(z_match.group(1))
                        
                # Detect Z hop movements (G1 commands that only move in Z direction)
                if currentLine.startswith("G1") and "Z" in currentLine and not "X" in currentLine and not "Y" in currentLine:
                    z_match = re.search(r"Z(\d+\.?\d*)", currentLine)
                    if z_match:
                        new_z = float(z_match.group(1))
                        # Only comment out upward Z movements (actual hops)
                        if new_z > current_z:
                            lines[line_index] = ";" + currentLine + " ; Modified by DiagonalZhop"
                        current_z = new_z
                
                # Also track Z position from normal movement commands
                elif (currentLine.startswith("G0") or currentLine.startswith("G1")) and "Z" in currentLine:
                    z_match = re.search(r"Z(\d+\.?\d*)", currentLine)
                    if z_match:
                        current_z = float(z_match.group(1))

                #
                # end of analysis
                #

            final_lines = "\n".join(lines)
            data[layer_index] = final_lines
        return data
