# Copyright (c) 2025 AddiPrint
# NozzleMaterialInfo is released under the terms of the LGPLv3 or higher.

from typing import Optional, Dict, Any

try:
    from PyQt6.QtCore import QObject
    PYQT_VERSION = 6
except ImportError:
    from PyQt5.QtCore import QObject
    PYQT_VERSION = 5

from UM.Application import Application
from UM.Extension import Extension
from UM.Logger import Logger
from UM.i18n import i18nCatalog

from cura.CuraApplication import CuraApplication
from cura.Settings.ExtruderManager import ExtruderManager

i18n_catalog = i18nCatalog("cura")


class NozzleMaterialInfoPlugin(QObject, Extension):
    """Plugin that adds nozzle and material information to the start of G-code files."""
    
    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Extension.__init__(self)
        
        self._application = CuraApplication.getInstance()
        
        # Connect to the writeStarted signal like PostProcessingPlugin does
        try:
            output_device_manager = Application.getInstance().getOutputDeviceManager()
            if hasattr(output_device_manager, 'writeStarted'):
                output_device_manager.writeStarted.connect(self._onWriteStarted)
            else:
                Logger.log("w", "NozzleMaterialInfo: OutputDeviceManager has no writeStarted signal")
        except Exception as e:
            Logger.log("e", f"NozzleMaterialInfo: Error connecting to signals: {e}")
    
    def _onWriteStarted(self, output_device):
        """Called when writing (saving/exporting) G-code starts."""
        try:
            self._addNozzleMaterialInfo()
        except Exception as e:
            Logger.log("e", f"NozzleMaterialInfo plugin error: {str(e)}")
            import traceback
            Logger.log("e", f"NozzleMaterialInfo traceback: {traceback.format_exc()}")
    
    def _addNozzleMaterialInfo(self):
        """Adds nozzle and material information to the start of the G-code."""
        scene = self._application.getController().getScene()
        
        # Get the G-code dict from the scene
        if not hasattr(scene, "gcode_dict"):
            Logger.log("w", "NozzleMaterialInfo: No G-code found in scene")
            return
        
        gcode_dict = getattr(scene, "gcode_dict")
        if not gcode_dict:
            Logger.log("w", "NozzleMaterialInfo: G-code dict is empty")
            return
        
        # Get the active build plate
        build_plate_number = self._application.getMultiBuildPlateModel().activeBuildPlate
        if build_plate_number not in gcode_dict:
            Logger.log("w", f"NozzleMaterialInfo: No G-code found for active build plate {build_plate_number}")
            return
        
        # Get nozzle and material information
        header_info = self._generateHeaderInfo()
        if not header_info:
            Logger.log("w", "NozzleMaterialInfo: Could not generate header information")
            return
        
        # Get the G-code for this build plate
        gcode_list = gcode_dict[build_plate_number]
        if not gcode_list or len(gcode_list) == 0:
            Logger.log("w", "NozzleMaterialInfo: G-code list is empty")
            return
        
        # Prepend the header information to the first layer
        original_gcode = gcode_list[0]
        modified_gcode = header_info + "\n" + original_gcode
        gcode_list[0] = modified_gcode
        
        # Update the scene's G-code
        gcode_dict[build_plate_number] = gcode_list
        setattr(scene, "gcode_dict", gcode_dict)
        
        Logger.log("i", "NozzleMaterialInfo: Successfully added header information to G-code")
    
    def _generateHeaderInfo(self) -> Optional[str]:
        """Generates the header information string with nozzle and material data."""
        extruder_manager = ExtruderManager.getInstance()
        if not extruder_manager:
            Logger.log("w", "NozzleMaterialInfo: Could not get ExtruderManager instance")
            return None
        
        # Get active extruder stacks
        extruder_stacks = extruder_manager.getActiveExtruderStacks()
        if not extruder_stacks:
            Logger.log("w", "NozzleMaterialInfo: No active extruder stacks found")
            return None
        
        header_lines = [";file data begin"]
        
        # Process each extruder (T0, T1, etc.)
        for i, extruder_stack in enumerate(extruder_stacks):
            if not extruder_stack.isEnabled:
                continue
                
            # Get nozzle size
            nozzle_size = self._getNozzleSize(extruder_stack)
            header_lines.append(f";nozzle_t{i}={nozzle_size}")
            
            # Get material info
            material_info = self._getMaterialInfo(extruder_stack)
            header_lines.append(f";material_t{i}={material_info}")
        
        # Ensure we always show T0 and T1, filling missing ones with N/A
        enabled_extruders = [i for i, stack in enumerate(extruder_stacks) if stack.isEnabled]
        
        # Fill in missing T0 if no extruders are enabled or T0 is missing
        if 0 not in enabled_extruders:
            header_lines.insert(-1, ";nozzle_t0=N/A")
            header_lines.insert(-1, ";material_t0=N/A")
        
        # Fill in missing T1 if we don't have a second extruder
        if 1 not in enabled_extruders:
            header_lines.insert(-1, ";nozzle_t1=N/A")
            header_lines.insert(-1, ";material_t1=N/A")
        
        header_lines.append(";file data end")
        
        return "\n".join(header_lines)
    
    def _getNozzleSize(self, extruder_stack) -> str:
        """Gets the nozzle size for the given extruder stack."""
        try:
            # Try to get machine_nozzle_size setting
            nozzle_size = extruder_stack.getProperty("machine_nozzle_size", "value")
            if nozzle_size is not None:
                return f"{nozzle_size:.1f}"
            
            # Fallback: try to get it from variant metadata  
            variant_container = extruder_stack.variant
            if variant_container and hasattr(variant_container, 'getMetaDataEntry'):
                variant_nozzle_size = variant_container.getMetaDataEntry("machine_nozzle_size")
                if variant_nozzle_size is not None:
                    return f"{float(variant_nozzle_size):.1f}"
                    
        except Exception as e:
            Logger.log("w", f"Error getting nozzle size: {e}")
        
        return "unknown"
    
    def _getMaterialInfo(self, extruder_stack) -> str:
        """Gets the material information for the given extruder stack."""
        try:
            material_container = extruder_stack.material
            if not material_container or not hasattr(material_container, 'getMetaDataEntry'):
                return "unknown"
            
            # Get brand and material name
            brand = material_container.getMetaDataEntry("brand", "")
            material_name = material_container.getMetaDataEntry("name", "")
            material_type = material_container.getMetaDataEntry("material", "")
            
            # Create a descriptive material string
            if brand and material_name:
                return f"{brand} {material_name}"
            elif material_name:
                return material_name
            elif material_type:
                return material_type
            else:
                return "unknown"
                
        except Exception as e:
            Logger.log("w", f"Error getting material info: {e}")
            return "unknown"