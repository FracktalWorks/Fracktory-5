# Copyright (c) 2025 AddiPrint
# NozzleMaterialInfo is released under the terms of the LGPLv3 or higher.

from . import NozzleMaterialInfoPlugin

def getMetaData():
    return {}

def register(app):
    return {"extension": NozzleMaterialInfoPlugin.NozzleMaterialInfoPlugin()}