# Import the correct version of PyQt
try:
    from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, pyqtProperty
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, pyqtProperty

import os

from UM.Logger import Logger
from UM.i18n import i18nCatalog
from UM.Resources import Resources

from .ControllerBase import ControllerBase
from ..Models.RingingTowerModel import RingingTowerModel
from ..Postprocessing import RingingTower_PostProcessing

Resources.addSearchPath(
    os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..'),'Resources')
)  # Plugin translation file import
catalog = i18nCatalog("autotowers")

class RingingTowerController(ControllerBase):
    _qmlFilename = 'RingingTowerDialog.qml'
    _criticalPropertiesTable = {
        'adaptive_layer_height_enabled': (ControllerBase.ContainerId.GLOBAL_CONTAINER_STACK, False),
        'layer_height': (ControllerBase.ContainerId.GLOBAL_CONTAINER_STACK, 0.2),
        'retraction_enable': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, True),
        'meshfix_union_all_remove_holes': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, False),
        'cool_min_layer_time': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
        'speed_print': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 100),
        'infill_sparse_density': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
        'scarf_joint_seam_length': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
        'wall_line_count': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 1),
        'top_thickness': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
        'bottom_thickness': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0.2),
    }

    def __init__(self, guiDir, stlDir, loadStlCallback, generateStlCallback, pluginName):
        dataModel = RingingTowerModel(stlDir=stlDir)
        super().__init__(name="Ringing Tower", guiDir=guiDir, loadStlCallback=loadStlCallback, generateStlCallback=generateStlCallback, qmlFilename=self._qmlFilename, criticalPropertiesTable=self._criticalPropertiesTable, dataModel=dataModel, pluginName=pluginName)
        self._dialog = None

    def generate(self, customizable):
        import os
        qmlFilePath = os.path.join(self._guiDir, self._qmlFilename)
        from cura.CuraApplication import CuraApplication
        self._dialog = CuraApplication.getInstance().createQmlComponent(qmlFilePath, {'controller': self, 'dataModel': self._dataModel, 'enableCustom': customizable})
        self._dialog.show()

    @pyqtSlot()
    def dialogAccepted(self):
        if self._dataModel.presetSelected:
            self._loadPresetRingingTower()
        else:
            self._generateCustomRingingTower()
        if self._dialog:
            self._dialog.close()

    @pyqtSlot()
    def dialogRejected(self):
        if self._dialog:
            self._dialog.close()

    def postProcess(self, gcode, enable_lcd_messages=False, enable_advanced_gcode_comments=True):
        start_f_str = self._dataModel.startFStr
        end_f_str = self._dataModel.endFStr
        # Always use input shaping
        gcode_type = 'is'
        return RingingTower_PostProcessing.execute(
            gcode=gcode,
            start_f_str=start_f_str,
            end_f_str=end_f_str,
            gcode_type=gcode_type,
            enable_lcd_messages=enable_lcd_messages,
            enable_advanced_gcode_comments=enable_advanced_gcode_comments
        )

    def _loadPresetRingingTower(self):
        stlFilePath = self._dataModel.presetFilePath
        towerName = f'Preset {self._dataModel.presetName}'
        self._loadStlCallback(self, towerName, stlFilePath, self.postProcess)

    def _generateCustomRingingTower(self):
        self._loadPresetRingingTower()
