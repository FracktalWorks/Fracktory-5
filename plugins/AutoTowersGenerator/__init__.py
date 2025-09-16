from . import AutoTowersGenerator as MaterialCalibration

def getMetaData():
    return {}

def register(app):
    return { 'extension' : MaterialCalibration.MaterialCalibration() }
