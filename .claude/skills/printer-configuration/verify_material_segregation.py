"""Skill companion tool: prove filament/pellet material segregation.

For every printer definition x every material, resolve the printer's inherited
`exclude_materials` metadata and apply the SAME check Cura uses at material-tree
build time (MachineNode.isExcludedMaterialBaseFile -> substring match). Then
assert:
  * pellet printers admit ONLY pellet materials
  * filament printers admit NO pellet materials

Classification is by material id substring `_pellet`. A printer is treated as a
pellet machine if its resolved metadata sets machine_barrel_heater true OR its
id contains 'pellet' OR it prefers a _pellet material; everything else is a
filament machine. Run from the repo root:
  venv/Scripts/python .claude/skills/printer-configuration/verify_material_segregation.py
Exit 0 = segregation holds in both directions.
"""
import glob
import json
import os
import sys

REPO = os.getcwd()
if not os.path.isdir(os.path.join(REPO, "resources", "definitions")):
    sys.exit("Run from the Fracktory-5 repo root.")

DEFS = os.path.join(REPO, "resources", "definitions")
MATS = os.path.join(REPO, "resources", "materials")


def resolved_metadata(name):
    """Walk the inherits chain leaf->root, applying per-key override (child
    wins) exactly like DefinitionContainer.deserializeMetadata."""
    chain = []
    cur = name
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        path = os.path.join(DEFS, cur + ".def.json")
        if not os.path.isfile(path):
            break
        with open(path, encoding="utf-8") as f:
            parsed = json.load(f)
        chain.append(parsed)
        cur = parsed.get("inherits")
    merged = {}
    overrides = {}
    for parsed in reversed(chain):  # root first, leaf last (leaf overrides)
        merged.update(parsed.get("metadata", {}))
        overrides.update(parsed.get("overrides", {}))
    merged["id"] = name
    # machine_barrel_heater is a setting (in overrides), not metadata; surface
    # its resolved default_value as the physical pellet discriminator.
    bh = overrides.get("machine_barrel_heater", {})
    merged["_barrel_heater"] = bool(bh.get("default_value", False))
    return merged


def is_excluded(exclude_materials, material_id):
    for pat in exclude_materials:
        if pat in material_id:
            return True
    return False


def material_base_files():
    """Return {base_file_id: is_pellet} for every shipped material."""
    out = {}
    for path in glob.glob(os.path.join(MATS, "**", "*.fdm_material"),
                          recursive=True):
        base = os.path.basename(path)
        if base.endswith(".xml.fdm_material"):
            mid = base[:-len(".xml.fdm_material")]
        else:
            mid = base[:-len(".fdm_material")]
        out[mid] = "_pellet" in mid
    return out


materials = material_base_files()
pellet_ids = {m for m, p in materials.items() if p}
filament_ids = {m for m, p in materials.items() if not p}

failures = []
summary = []
for path in sorted(glob.glob(os.path.join(DEFS, "*.def.json"))):
    name = os.path.basename(path)[:-len(".def.json")]
    if name in ("fdmprinter", "fdmextruder"):
        continue
    md = resolved_metadata(name)
    if not md.get("visible", False):
        continue  # only ship-facing printers matter for the guarantee
    excl = md.get("exclude_materials", [])
    admitted = {m for m in materials if not is_excluded(excl, m)}

    # Classify the PRINTER independently of preferred_material (so we can then
    # assert preferred_material is correct, without circularity). The physical
    # discriminator is the pellet-extruder barrel heater.
    is_pellet_printer = (
        md.get("_barrel_heater", False)
        or md.get("quality_definition") == "penrose_pellet_quality"
    )
    kind = "PELLET" if is_pellet_printer else "filament"

    # 1. Tree admission: no wrong-class material may enter the material tree.
    if is_pellet_printer:
        leaked = admitted & filament_ids
        if leaked:
            failures.append(f"{name} (pellet) admits filament: {sorted(leaked)[:5]}")
        if not (admitted & pellet_ids):
            failures.append(f"{name} (pellet) admits NO pellet materials")
    else:
        leaked = admitted & pellet_ids
        if leaked:
            failures.append(f"{name} (filament) admits pellet: {sorted(leaked)}")

    # 2. Boot material: the material shown when the printer opens must be
    #    admitted AND the correct class (this is "no pellets on a filament
    #    printer, and the reverse").
    pref = md.get("preferred_material", "")
    if pref:
        if is_excluded(excl, pref):
            failures.append(f"{name} preferred_material '{pref}' is excluded "
                            f"-> would fall back unpredictably")
        pref_is_pellet = "_pellet" in pref
        if pref_is_pellet != is_pellet_printer:
            failures.append(f"{name} ({kind}) preferred_material '{pref}' is "
                            f"the wrong class")
    else:
        failures.append(f"{name} has no preferred_material (boot material "
                        f"class not guaranteed)")

    summary.append(f"  {name:24s} {kind:8s} exclude={excl} "
                   f"admits {len(admitted & pellet_ids)}P/{len(admitted & filament_ids)}F "
                   f"boot={pref}")

print(f"Materials: {len(pellet_ids)} pellet, {len(filament_ids)} filament")
print("\n".join(summary))
print()
if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: pellet<->filament material segregation holds for every visible printer")
