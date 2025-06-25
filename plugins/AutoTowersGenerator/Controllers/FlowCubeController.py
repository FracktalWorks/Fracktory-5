# Import the correct version of PyQt
try:
    from PyQt6.QtCore import QObject, pyqtSlot
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSlot

import os
from UM.i18n import i18nCatalog
from UM.Resources import Resources
from .ControllerBase import ControllerBase
from ..Models.ModelBase import ModelBase

Resources.addSearchPath(
    os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..'),'Resources')
)
catalog = i18nCatalog("autotowers")

class FlowCubeModel(ModelBase):
    pass

class FlowCubeController(ControllerBase):
    _qmlFilename = 'FlowCubeDialog.qml'
    # Use the _criticalPropertiesTable from PressureAdvanceTowerController
    _criticalPropertiesTable = {
        'adaptive_layer_height_enabled': (ControllerBase.ContainerId.GLOBAL_CONTAINER_STACK, False),
        'magic_spiralize': (ControllerBase.ContainerId.GLOBAL_CONTAINER_STACK, True),
        'layer_height': (ControllerBase.ContainerId.GLOBAL_CONTAINER_STACK, 0.2),
        'top_thickness': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0),
        'bottom_thickness': (ControllerBase.ContainerId.ACTIVE_EXTRUDER_STACK, 0.3),
    }

    def __init__(self, guiDir, stlDir, loadStlCallback, generateStlCallback, pluginName):
        dataModel = FlowCubeModel(stlDir=stlDir)
        super().__init__(name=catalog.i18nc("@test", "Flow Cube"), guiDir=guiDir, loadStlCallback=loadStlCallback, generateStlCallback=generateStlCallback, qmlFilename=self._qmlFilename, criticalPropertiesTable=self._criticalPropertiesTable, dataModel=dataModel, pluginName=pluginName)
        self._dialog = None

    def generate(self, customizable):
        import os
        qmlFilePath = os.path.join(self._guiDir, self._qmlFilename)
        from cura.CuraApplication import CuraApplication
        self._dialog = CuraApplication.getInstance().createQmlComponent(qmlFilePath, {'controller': self, 'dataModel': self._dataModel, 'enableCustom': customizable})
        self._dialog.show()

    @pyqtSlot()
    def dialogAccepted(self):
        # Just drop the STL on the bed, no post-processing
        stl_path = os.path.join(self._dataModel._stlDir, 'Flow Cube.stl')
        self._loadStlCallback(self, 'Flow Cube', stl_path, None)
        if self._dialog:
            self._dialog.close()

    @pyqtSlot()
    def dialogRejected(self):
        if self._dialog:
            self._dialog.close()
