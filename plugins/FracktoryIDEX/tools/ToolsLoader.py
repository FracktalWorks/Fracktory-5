
from UM.Tool import Tool
from UM.Logger import Logger
from UM.Application import Application


from .print_modes import PrintModesPlugin

class ToolsLoader(Tool):

    def __init__(self):
        super().__init__()
        self.print_modes = PrintModesPlugin.PrintModesPlugin()
        Application.getInstance().globalContainerStackChanged.connect(self._updateEnabled)

    def _updateEnabled(self):
        global_container_stack = Application.getInstance().getGlobalContainerStack()
        if global_container_stack:
            if global_container_stack.getProperty("is_idex", "value"):
                plugin_visibility = True
                Application.getInstance().getController().toolEnabledChanged.emit(self._plugin_id, plugin_visibility)
                Logger.info("IDEX Tool Enabled")
            else:
                plugin_visibility = False
                Application.getInstance().getController().toolEnabledChanged.emit(self._plugin_id, plugin_visibility)
                Logger.info("IDEX Tool Disabled")
