"""Skill companion tool: diff the effective (inheritance-merged) definition
overrides of two printers, so every setting delta between a new machine and
its reference machine is an explicit, reviewable list.

Merges each printer's `overrides` down its full `inherits` chain (per-key,
child property wins) and prints keys whose merged property dict differs.
Start/end g-code are skipped by default (compare those by regenerating via
scripts/generate_start_gcode.py instead).

Usage (from the repo root):
  python .claude/skills/printer-configuration/diff_definition_settings.py \
      penrose_600_swappable_fdm dragon_700 [--gcode]
"""
import json
import os
import sys

DEFS = os.path.join(os.getcwd(), "resources", "definitions")


def merged_overrides(name):
    chain = []
    cur, seen = name, set()
    while cur and cur not in seen:
        seen.add(cur)
        path = os.path.join(DEFS, cur + ".def.json")
        if not os.path.isfile(path):
            sys.exit(f"No such definition: {path}")
        with open(path, encoding="utf-8") as f:
            parsed = json.load(f)
        chain.append(parsed)
        cur = parsed.get("inherits")
    merged = {}
    for parsed in reversed(chain):
        for key, props in parsed.get("overrides", {}).items():
            merged.setdefault(key, {}).update(props)
    return merged


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 2:
        sys.exit(__doc__)
    skip = () if "--gcode" in sys.argv else ("machine_start_gcode", "machine_end_gcode")
    a_name, b_name = args
    a, b = merged_overrides(a_name), merged_overrides(b_name)
    print(f"=== {a_name}  vs  {b_name} ===")
    n = 0
    for key in sorted(set(a) | set(b)):
        if key in skip:
            continue
        va, vb = a.get(key), b.get(key)
        if va != vb:
            n += 1
            print(f"  {key}")
            print(f"    {a_name[:28]:28s}: {json.dumps(va)[:160]}")
            print(f"    {b_name[:28]:28s}: {json.dumps(vb)[:160]}")
    print(f"\n{n} differing keys" + (" (g-code skipped)" if skip else ""))


if __name__ == "__main__":
    main()
