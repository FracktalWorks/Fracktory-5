"""Skill companion tool: load every printer definition through the real
Uranium loader (from dist/Fracktory) and report deserialization problems the
static printer-linter cannot see — e.g. overrides silently dropped because a
key has stray whitespace or references a nonexistent setting.

Run from the repo root:  venv/Scripts/python .claude/skills/printer-configuration/verify_definitions_load.py
Exit code 0 = all definitions load cleanly.
"""
import glob
import os
import sys

REPO = os.getcwd()
if not os.path.isdir(os.path.join(REPO, "resources", "definitions")):
    sys.exit("Run from the Fracktory-5 repo root.")
sys.path.insert(0, os.path.join(REPO, "dist", "Fracktory"))

from UM.Resources import Resources
Resources.addSearchPath(os.path.join(REPO, "resources"))

from UM.VersionUpgradeManager import VersionUpgradeManager


class _NoUpgrade:
    def updateFilesData(self, *args, **kwargs):
        return None


VersionUpgradeManager._VersionUpgradeManager__instance = _NoUpgrade()

from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.SettingDefinition import (SettingDefinition,
                                           DefinitionPropertyType,
                                           toIntConversion)
from UM.Settings.Validator import Validator
from UM import Logger as LoggerModule

# Mirror cura/CuraApplication.py:407-430 registrations
SettingDefinition.addSupportedProperty("settable_per_mesh", DefinitionPropertyType.Any, default=True)
SettingDefinition.addSupportedProperty("settable_per_extruder", DefinitionPropertyType.Any, default=True)
SettingDefinition.addSupportedProperty("settable_per_meshgroup", DefinitionPropertyType.Any, default=True)
SettingDefinition.addSupportedProperty("settable_globally", DefinitionPropertyType.Any, default=True)
SettingDefinition.addSupportedProperty("limit_to_extruder", DefinitionPropertyType.Function, default="-1")
SettingDefinition.addSupportedProperty("resolve", DefinitionPropertyType.Function, default=None)
SettingDefinition.addSettingType("extruder", None, toIntConversion, Validator)
SettingDefinition.addSettingType("optional_extruder", None, toIntConversion, None)
SettingDefinition.addSettingType("[int]", None, str, None)

captured = []
_orig_log = LoggerModule.Logger.log


def capture_log(level, message, *args):
    if level in ("w", "e", "c"):
        captured.append((level, message % args if args else message))
    return _orig_log(level, message, *args)


LoggerModule.Logger.log = staticmethod(capture_log)

DEFS = os.path.join(REPO, "resources", "definitions")
failed = []
for path in sorted(glob.glob(os.path.join(DEFS, "*.def.json"))):
    name = os.path.basename(path)[:-len(".def.json")]
    if name in ("fdmprinter", "fdmextruder"):
        continue
    captured.clear()
    container = DefinitionContainer(name)
    try:
        with open(path, encoding="utf-8") as f:
            container.deserialize(f.read(), file_name=path)
    except Exception as e:  # any load failure is a finding, keep going
        failed.append((name, f"EXCEPTION: {e}"))
        continue
    for lvl, msg in captured:
        if "Unable to override" in msg or lvl in ("e", "c"):
            failed.append((name, msg))

if failed:
    for name, msg in failed:
        print(f"ISSUE {name}: {msg}")
    sys.exit(1)
print("PASS: all definitions load cleanly, no dropped overrides")
