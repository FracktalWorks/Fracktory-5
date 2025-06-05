# Post-processing for Ringing Tower
# Inserts M593 F=... or M493 A=.../B=... at every layer change to sweep input shaping frequency
__version__ = '1.0'

from UM.Logger import Logger
from . import PostProcessingCommon as Common

def execute(gcode, start_f_str=None, end_f_str=None, gcode_type=None, **kwargs):
    Logger.log('d', f'RingingTower_PostProcessing: called with start_f_str={start_f_str}, end_f_str={end_f_str}, gcode_type={gcode_type}')
    try:
        start_f = float(start_f_str) if start_f_str is not None else 15.0
    except Exception:
        start_f = 15.0
    try:
        end_f = float(end_f_str) if end_f_str is not None else 60.0
    except Exception:
        end_f = 60.0
    # Always use input shaping (M593)
    gcode_type = 'is'

    # Document the settings in the g-code
    gcode[0] += f'; Ringing Tower post-processing script version {__version__}\n'
    gcode[0] += f'; Start frequency = {start_f} Hz\n'
    gcode[0] += f'; End frequency = {end_f} Hz\n'
    gcode[0] += f'; G-code type = {gcode_type}\n'

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
    max_layer = None
    # First, try to find the max layer from the gcode
    for line in gcode[0].split('\n'):
        if line.startswith(';LAYER_COUNT:'):
            try:
                max_layer = int(line.split(':')[1].strip())
            except Exception:
                pass
            break
    if max_layer is None:
        # fallback: estimate from gcode
        max_layer = 100

    for line_index, line, lines, start_of_new_section in Common.LayerEnumerate(gcode, 0, 0, layer_height, layer_height, False):
        if ';LAYER:' in line:
            try:
                layer_number = int(line.split(':')[1].strip())
            except Exception:
                layer_number += 1
            # Frequency sweep logic: start at start_f, end at end_f, from layer 2 to max_layer-1
            if layer_number < 2:
                hz = 0
            else:
                hz = start_f + (end_f - start_f) * (layer_number - 2) / max(1, (max_layer - 3))
            lines.insert(line_index + 1, f'; --- Ringing Tower: Set Input Shaping to {hz:.2f} Hz at layer {layer_number} ---')
            lines.insert(line_index + 2, f'M593 F{hz:.2f} ;(Hz) Input Shaping Test')

    return gcode
