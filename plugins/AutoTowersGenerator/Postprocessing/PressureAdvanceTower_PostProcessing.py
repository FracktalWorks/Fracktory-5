# Post-processing for Pressure Advance Tower
# Inserts M900 K=... at every layer change
__version__ = '3.2'

from UM.Logger import Logger
from . import PostProcessingCommon as Common

def execute(gcode, start_k_str=None, k_change_str=None, **kwargs):
    Logger.log('d', f'PressureAdvanceTower_PostProcessing: called with start_k_str={start_k_str}, k_change_str={k_change_str}')
    try:
        start_k = float(start_k_str) if start_k_str is not None else 0.0
    except Exception:
        start_k = 0.0
    try:
        k_change = float(k_change_str) if k_change_str is not None else 0.005
    except Exception:
        k_change = 0.005

    # Document the settings in the g-code (like TempTower)
    gcode[0] += f'; Pressure Advance Tower post-processing script version {__version__}\n'
    gcode[0] += f'; Starting K = {start_k}\n'
    gcode[0] += f'; K step = {k_change}\n'

    # Get layer_height and initial_layer_height from printer settings
    from UM.Application import Application
    try:
        machine_manager = Application.getInstance().getMachineManager()
        active_machine = machine_manager.activeMachine
        layer_height = float(active_machine.getProperty('layer_height', 'value'))
    except Exception:
        layer_height = 0.3  # fallback
    try:
        initial_layer_height = float(active_machine.getProperty('initial_layer_height', 'value'))
    except Exception:
        initial_layer_height = layer_height  # fallback

    # Use Common.LayerEnumerate for robust layer handling
    layer_number = -1
    for line_index, line, lines, start_of_new_section in Common.LayerEnumerate(gcode, 0, 0, layer_height, layer_height, False):
        if ';LAYER:' in line:
            # Try to extract the layer number, fallback to increment
            try:
                layer_number = int(line.split(':')[1].strip())
            except Exception:
                layer_number += 1
            measured_height = (layer_number * layer_height ) + initial_layer_height
            k_value = start_k + (measured_height * k_change)
            Logger.log('d', f'PressureAdvanceTower_PostProcessing: inserting M900 K={k_value:.5f} at layer {layer_number}')
            lines.insert(line_index + 1, f'; --- Pressure Advance Tower: Set K to {k_value:.5f} at layer {layer_number} (Z={measured_height:.2f}mm) ---')
            lines.insert(line_index + 2, f'M900 K={k_value:.5f}')

    return gcode
