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
from ..Models.PressureAdvanceTowerModel import PressureAdvanceTowerModel
from ..Postprocessing import PressureAdvanceTower_PostProcessing

Resources.addSearchPath(
    os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..'),'Resources')
)  # Plugin translation file import
catalog = i18nCatalog("autotowers")


class PressureAdvanceTowerController(ControllerBase):
    _qmlFilename = 'PressureAdvanceTowerDialog.qml'
    _criticalPropertiesTable = {
        'adaptive_layer_height_enabled': (ControllerBase.ContainerId.GLOBAL_CONTAINER_STACK, False),
        'layer_height': (ControllerBase.ContainerId.GLOBAL_CONTAINER_STACK, 0.3),
        'retraction_enable': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, True),
        'meshfix_union_all_remove_holes': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, False),
        'cool_min_temperature': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
        'speed_print': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 100),
        'infill_sparse_density': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
        'scarf_joint_seam_length': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
    }

    def __init__(self, guiDir, stlDir, loadStlCallback, generateStlCallback, pluginName):
        dataModel = PressureAdvanceTowerModel(stlDir=stlDir)
        super().__init__(name="Pressure Advance Tower", guiDir=guiDir, loadStlCallback=loadStlCallback, generateStlCallback=generateStlCallback, qmlFilename=self._qmlFilename, criticalPropertiesTable=self._criticalPropertiesTable, dataModel=dataModel, pluginName=pluginName)
        self._dialog = None

    def generate(self, customizable):
        import os
        qmlFilePath = os.path.join(self._guiDir, self._qmlFilename)
        from cura.CuraApplication import CuraApplication
        self._dialog = CuraApplication.getInstance().createQmlComponent(qmlFilePath, {'controller': self, 'dataModel': self._dataModel, 'enableCustom': customizable})
        self._dialog.show()

    @pyqtSlot()
    def dialogAccepted(self):
        ''' This method is called by the dialog when the "Generate" button is clicked '''
        if self._dataModel.presetSelected:
            self._loadPresetPressureAdvanceTower()
        else:
            self._generateCustomPressureAdvanceTower()
        if self._dialog:
            self._dialog.close()

    @pyqtSlot()
    def dialogRejected(self):
        if self._dialog:
            self._dialog.close()

    def postProcess(self, gcode, enable_lcd_messages=False, enable_advanced_gcode_comments=True):
        # Retrieve the user K start and step values from the data model
        start_k = getattr(self._dataModel, "startKStr", None)
        k_step = getattr(self._dataModel, "kChangeStr", None)
        return PressureAdvanceTower_PostProcessing.execute(
            gcode,
            start_k_str=start_k,
            k_change_str=k_step,
            enable_lcd_messages=enable_lcd_messages,
            enable_advanced_gcode_comments=enable_advanced_gcode_comments
        )

    def _loadPresetPressureAdvanceTower(self):
        stlFilePath = self._dataModel.presetFilePath
        towerName = f'Preset {self._dataModel.presetName}'
        self._loadStlCallback(self, towerName, stlFilePath, self.postProcess)

    def _generateCustomPressureAdvanceTower(self):
        # No custom generation logic needed for now (no OpenSCAD)
        self._loadPresetPressureAdvanceTower()
