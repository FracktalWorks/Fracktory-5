# Copyright (c) 2025 Vijay Raghav Varada
# The AutoPrimeTowerSizePlugin is released under the terms of the AGPLv3 or higher.

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("AutoPrimeTowerSizePlugin")

from .AutoPrimeTowerSize import AutoPrimeTowerSizePlugin

def getMetaData():
    return {}

def register(app):
    return {"extension": AutoPrimeTowerSizePlugin()}
