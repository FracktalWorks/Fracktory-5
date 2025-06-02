# Copyright (c) 2023 5@xes
# Based on the TabPlus plugin  and licensed under LGPLv3 or higher.

from . import AntiWarpingTabs

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("spoonawreborn")

def getMetaData():
    _qml_file="qml/spoonawreborn.qml"

    return {
        "tool": {
            "name": i18n_catalog.i18nc("@label", "Anti-Warping Tabs"),
            "description": i18n_catalog.i18nc("@info:tooltip", "Add tabs to help prevent warping."),
            "icon": "tool_icon.svg",
            "tool_panel": _qml_file,
            "weight": 11
        }
    }

def register(app):
    return { "tool": AntiWarpingTabs.AntiWarpingTabs() }
