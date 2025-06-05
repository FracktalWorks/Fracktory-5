from .ModelBase import ModelBase
from UM.i18n import i18nCatalog
from PyQt6.QtCore import pyqtSignal, pyqtProperty

catalog = i18nCatalog("autotowers")

class RingingTowerModel(ModelBase):
    """
    Model for Ringing Tower
    Slicer requirements:
    - Layer height: 0.3mm
    - Infill: 0%
    - Print speed: 100mm/s
    - Scarf seams: disabled
    """

    _presetsTable = [
        {'name': catalog.i18nc("@model", "Ringing Tower - Default"), 'filename': 'Ringing Tower.stl', 'start f': '15', 'end f': '60'},
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
    def presetStartFStr(self)->str:
        return self._presetsTable[self.presetIndex]['start f']

    @pyqtProperty(str, notify=presetIndexChanged)
    def presetEndFStr(self)->str:
        return self._presetsTable[self.presetIndex]['end f']

    @pyqtProperty(str, notify=presetIndexChanged)
    def presetGcodeType(self)->str:
        return 'is'  # Always use input shaping

    dialogIconChanged = pyqtSignal()

    @pyqtProperty(str, notify=dialogIconChanged)
    def dialogIcon(self)->str:
        return 'ringing_icon.png'

    _startFStr = '15'
    startFStrChanged = pyqtSignal()
    def setStartFStr(self, value)->None:
        self._startFStr = value
        self.startFStrChanged.emit()
    @pyqtProperty(str, notify=startFStrChanged, fset=setStartFStr)
    def startFStr(self)->str:
        return self._startFStr

    _endFStr = '60'
    endFStrChanged = pyqtSignal()
    def setEndFStr(self, value)->None:
        self._endFStr = value
        self.endFStrChanged.emit()
    @pyqtProperty(str, notify=endFStrChanged, fset=setEndFStr)
    def endFStr(self)->str:
        return self._endFStr

    _gcodeType = 'is'
    gcodeTypeChanged = pyqtSignal()
    def setGcodeType(self, value)->None:
        self._gcodeType = 'is'  # Always force input shaping
        self.gcodeTypeChanged.emit()
    @pyqtProperty(str, notify=gcodeTypeChanged, fset=setGcodeType)
    def gcodeType(self)->str:
        return 'is'

    def __init__(self, stlDir):
        super().__init__(stlDir=stlDir)
