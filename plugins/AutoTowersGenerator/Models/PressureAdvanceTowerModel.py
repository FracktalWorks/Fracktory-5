from .ModelBase import ModelBase
from UM.i18n import i18nCatalog
from PyQt6.QtCore import pyqtSignal, pyqtProperty

catalog = i18nCatalog("autotowers")

class PressureAdvanceTowerModel(ModelBase):
    """
    Model for Pressure Advance Tower
    Slicer requirements:
    - Layer height: 0.3mm
    - Infill: 0%
    - Print speed: 100mm/s
    - Scarf seams: disabled
    """

    # The available pressure advance tower presets
    _presetsTable = [
        {'name': catalog.i18nc("@model", "Pressure Advance Tower - Default"), 'filename': 'Pressure Advance Tower.stl', 'start k': '0.00', 'k change': '0.02'},
    ]

    presetsModelChanged = pyqtSignal()

    @pyqtProperty(list, notify=presetsModelChanged)
    def presetsModel(self):
        return self._presetsTable

    _presetIndex = 0
    presetIndexChanged = pyqtSignal()

    def setPresetIndex(self, value)->None:
        self._presetIndex = int(value)
        self.presetIndexChanged.emit()

    @pyqtProperty(int, notify=presetIndexChanged, fset=setPresetIndex)
    def presetIndex(self)->int:
        return self._presetIndex

    @pyqtProperty(bool, notify=presetIndexChanged)
    def presetSelected(self)->bool:
        return self._presetIndex < len(self._presetsTable)

    @pyqtProperty(str, notify=presetIndexChanged)
    def presetName(self)->str:
        return self._presetsTable[self.presetIndex]['name']

    @pyqtProperty(str, notify=presetIndexChanged)
    def presetFileName(self)->str:
        return self._presetsTable[self.presetIndex]['filename']

    @pyqtProperty(str, notify=presetIndexChanged)
    def presetFilePath(self)->str:
        return self._buildStlFilePath(self.presetFileName)

    @pyqtProperty(str, notify=presetIndexChanged)
    def presetStartKStr(self)->str:
        return self._presetsTable[self.presetIndex]['start k']

    @pyqtProperty(float, notify=presetIndexChanged)
    def presetStartK(self)->float:
        return float(self.presetStartKStr)

    @pyqtProperty(str, notify=presetIndexChanged)
    def presetKChangeStr(self)->str:
        return self._presetsTable[self.presetIndex]['k change']

    @pyqtProperty(float, notify=presetIndexChanged)
    def presetKChange(self)->float:
        return float(self.presetKChangeStr)

    # The icon to display on the dialog
    dialogIconChanged = pyqtSignal()

    @pyqtProperty(str, notify=dialogIconChanged)
    def dialogIcon(self)->str:
        return 'pressureadvance_icon.png'

    # The starting K value for the tower
    _startKStr = '0.00'
    startKStrChanged = pyqtSignal()
    def setStartKStr(self, value)->None:
        self._startKStr = value
        self.startKStrChanged.emit()
    @pyqtProperty(str, notify=startKStrChanged, fset=setStartKStr)
    def startKStr(self)->str:
        if self.presetSelected:
            return self.presetStartKStr
        else:
            return self._startKStr
    @pyqtProperty(float, notify=startKStrChanged)
    def startK(self)->float:
        return float(self.startKStr)

    # The amount to change K between tower sections
    _kChangeStr = '0.02'
    kChangeStrChanged = pyqtSignal()
    def setKChangeStr(self, value)->None:
        self._kChangeStr = value
        self.kChangeStrChanged.emit()
    @pyqtProperty(str, notify=kChangeStrChanged, fset=setKChangeStr)
    def kChangeStr(self)->str:
        if self.presetSelected:
            return self.presetKChangeStr
        else:
            return self._kChangeStr
    @pyqtProperty(float, notify=kChangeStrChanged)
    def kChange(self)->float:
        return float(self.kChangeStr)

    # The label to add to the tower
    _towerLabel = 'K'
    towerLabelChanged = pyqtSignal()
    def setTowerLabel(self, value)->None:
        self._towerLabel = value
        self.towerLabelChanged.emit()
    @pyqtProperty(str, notify=towerLabelChanged, fset=setTowerLabel)
    def towerLabel(self)->str:
        return self._towerLabel

    # The description to carve up the side of the tower
    _towerDescription = 'PRESSURE ADV'
    towerDescriptionChanged = pyqtSignal()
    def setTowerDescription(self, value)->None:
        self._towerDescription = value
        self.towerDescriptionChanged.emit()
    @pyqtProperty(str, notify=towerDescriptionChanged, fset=setTowerDescription)
    def towerDescription(self)->str:
        return self._towerDescription

    def __init__(self, stlDir):
        super().__init__(stlDir=stlDir)
