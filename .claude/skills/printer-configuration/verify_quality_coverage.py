"""Skill companion tool: prove every printer x variant x admitted-material
permutation resolves to a FILTERED set of quality profiles.

Statically mirrors cura/Machines/MaterialNode._loadAll's resolution chain:
  1. exact stub        (definition=quality_def, variant=name, material=base_file)
  2. brand+type stubs  (stubs of another material with same brand + type)
  3. type stubs        (stubs of another material with same type, any brand)
  4. GUID stubs        (stubs of a material sharing the GUID)
  5. global fallback   (ALL global quality types -> UNFILTERED: this is the
                        silent-failure mode; the checker FAILS on it)

Also asserts each printer's preferred variant exists and its preferred
quality type is available for the boot (preferred) material on that variant.

Run from the repo root:
  venv/Scripts/python .claude/skills/printer-configuration/verify_quality_coverage.py
Exit 0 = every permutation is usable and properly filtered.
"""
import configparser
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET

REPO = os.getcwd()
if not os.path.isdir(os.path.join(REPO, "resources", "definitions")):
    sys.exit("Run from the AddiSlice repo root.")

DEFS = os.path.join(REPO, "resources", "definitions")
MATS = os.path.join(REPO, "resources", "materials")
QUAL = os.path.join(REPO, "resources", "quality")
VARS = os.path.join(REPO, "resources", "variants")
NS = {"m": "http://www.ultimaker.com/material"}


def resolved_metadata(name):
    chain = []
    cur, seen = name, set()
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
    for parsed in reversed(chain):
        merged.update(parsed.get("metadata", {}))
    return merged


def load_materials():
    """{base_file: {brand, type, guid}} for every shipped material."""
    out = {}
    for path in glob.glob(os.path.join(MATS, "**", "*.fdm_material"), recursive=True):
        base = os.path.basename(path)
        mid = base[:-len(".xml.fdm_material")] if base.endswith(".xml.fdm_material") \
            else base[:-len(".fdm_material")]
        try:
            root = ET.parse(path).getroot()
            meta = root.find("m:metadata", NS)
            name = meta.find("m:name", NS)
            out[mid] = {
                "brand": name.findtext("m:brand", "", NS),
                "type": name.findtext("m:material", "", NS),
                "guid": meta.findtext("m:GUID", "", NS),
            }
        except Exception as e:
            print(f"WARN: cannot parse material {base}: {e}")
    return out


bom_failures = []


def load_quality_containers():
    """Per quality_definition: globals {quality_type} and stubs
    {(variant, material): {quality_type}}."""
    globals_by_def = {}
    stubs_by_def = {}
    for path in glob.glob(os.path.join(QUAL, "**", "*.inst.cfg"), recursive=True):
        with open(path, "rb") as fb:
            if fb.read(3) == b"\xef\xbb\xbf":
                # BOM breaks stdlib configparser -> version-upgrade path risk
                bom_failures.append(os.path.relpath(path, REPO))
        cp = configparser.ConfigParser(interpolation=None)
        try:
            cp.read(path, encoding="utf-8-sig")
            d = cp["general"]["definition"]
            md = cp["metadata"]
            qt = md.get("quality_type", "")
            if md.get("global_quality", "False") != "False":
                globals_by_def.setdefault(d, set()).add(qt)
            else:
                key = (md.get("variant", ""), md.get("material", ""))
                stubs_by_def.setdefault(d, {}).setdefault(key, set()).add(qt)
        except Exception as e:
            print(f"WARN: cannot parse quality {os.path.basename(path)}: {e}")
    return globals_by_def, stubs_by_def


def load_variants():
    """{definition: [variant names]}"""
    out = {}
    for path in glob.glob(os.path.join(VARS, "**", "*.inst.cfg"), recursive=True):
        with open(path, "rb") as fb:
            if fb.read(3) == b"\xef\xbb\xbf":
                bom_failures.append(os.path.relpath(path, REPO))
        cp = configparser.ConfigParser(interpolation=None)
        try:
            cp.read(path, encoding="utf-8-sig")
            out.setdefault(cp["general"]["definition"], []).append(cp["general"]["name"])
        except Exception as e:
            print(f"WARN: cannot parse variant {os.path.basename(path)}: {e}")
    return out


def is_excluded(excl, mid):
    return any(pat in mid for pat in excl)


def resolve_qualities(qdef, variant, mat_id, materials, stubs, globals_):
    """Return (resolution_step, {quality_type}) mirroring MaterialNode._loadAll."""
    per_def_stubs = stubs.get(qdef, {})
    exact = per_def_stubs.get((variant, mat_id))
    if exact:
        return "exact", exact
    me = materials[mat_id]
    # brand + type
    same_brand = {m for m, info in materials.items()
                  if info["type"] == me["type"] and info["brand"] == me["brand"]}
    found = set()
    for m in same_brand:
        found |= per_def_stubs.get((variant, m), set())
    if found:
        return "brand+type", found
    # type, any brand
    same_type = {m for m, info in materials.items() if info["type"] == me["type"]}
    for m in same_type:
        found |= per_def_stubs.get((variant, m), set())
    if found:
        return "type", found
    # GUID
    same_guid = {m for m, info in materials.items() if info["guid"] == me["guid"]}
    for m in same_guid:
        found |= per_def_stubs.get((variant, m), set())
    if found:
        return "guid", found
    return "GLOBAL-FALLBACK", globals_.get(qdef, set())


materials = load_materials()
globals_by_def, stubs_by_def = load_quality_containers()
variants_by_def = load_variants()

failures = []
for f in bom_failures:
    failures.append(f"UTF-8 BOM in {f} (breaks configparser/version-upgrade)")
for path in sorted(glob.glob(os.path.join(DEFS, "*.def.json"))):
    name = os.path.basename(path)[:-len(".def.json")]
    if name in ("fdmprinter", "fdmextruder"):
        continue
    md = resolved_metadata(name)
    if not md.get("visible", False):
        continue
    qdef = md.get("quality_definition", name)
    excl = md.get("exclude_materials", [])
    variants = variants_by_def.get(name, [])
    admitted = [m for m in materials if not is_excluded(excl, m)]

    if not variants:
        failures.append(f"{name}: NO variants found")
        continue

    counts = {"exact": 0, "brand+type": 0, "type": 0, "guid": 0}
    for variant in variants:
        for mat in admitted:
            step, qtypes = resolve_qualities(qdef, variant, mat, materials,
                                             stubs_by_def, globals_by_def)
            if step == "GLOBAL-FALLBACK":
                # Runtime nuance: for has_variants machines Cura's last resort
                # queries globals WITH a variant= constraint, which matches
                # nothing -> empty_quality (material unusable). Either way this
                # permutation is broken; fail it.
                failures.append(f"{name} / {variant} / {mat}: no stub coverage "
                                f"(runtime: empty/unfiltered qualities)")
            elif not qtypes:
                failures.append(f"{name} / {variant} / {mat}: NO qualities at all")
            else:
                counts[step] += 1

    # Boot permutation: preferred variant + material + quality type
    pv = md.get("preferred_variant_name", "")
    pm = md.get("preferred_material", "")
    pq = md.get("preferred_quality_type", "")
    if pv not in variants:
        failures.append(f"{name}: preferred variant '{pv}' has no variant file")
    elif pm in materials and not is_excluded(excl, pm):
        step, qtypes = resolve_qualities(qdef, pv, pm, materials,
                                         stubs_by_def, globals_by_def)
        if pq not in qtypes:
            failures.append(f"{name}: preferred quality '{pq}' not available "
                            f"for boot combo ({pv} x {pm}; got {sorted(qtypes)})")
    else:
        failures.append(f"{name}: preferred material '{pm}' missing or excluded")

    total = sum(counts.values())
    print(f"  {name:36s} {len(variants)}var x {len(admitted)}mat = {total} combos "
          f"(exact {counts['exact']}, brand {counts['brand+type']}, "
          f"type {counts['type']}, guid {counts['guid']})")

print()
if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: every printer x variant x material permutation resolves to a "
      "filtered quality set, and every boot combo has its preferred quality")
