# Skill Observation Log

Observations captured during task-oriented work. Each entry identifies a
potential skill improvement or new skill opportunity.

**Status key:** OPEN = not yet actioned | ACTIONED = skill updated/created |
DECLINED = user decided not to pursue

---

## 2026-07-23

### Observation 1: Created pellet-printer-tuning internal skill

**Status:** ACTIONED — skill created at `.claude/skills/pellet-printer-tuning/SKILL.md`
**Date:** 2026-07-23
**Session context:** Building repo navigation knowledge for Fracktory-5 ahead of Penrose pellet settings changes
**Skill:** New skill candidate: pellet-printer-tuning
**Type:** internal
**Phase/Area:** resources/ editing workflow

**Issue:** Editing Penrose pellet printer settings is a recurring, structured
task (decide the layer: definition vs variant vs material vs quality; obey
silent-failure metadata rules; verify with printer-linter + in-app). The
knowledge lived only in the long `docs/agents.md`; no fast operational
runbook existed.

**Suggested improvement:** Internal project skill distilling the
where-does-this-setting-go decision table, the hard rules that fail silently,
and the verification checklist. Done; checked into the repo so it is
readable from Claude Code (VS Code + cloud) and as plain docs from Copilot.

**Principle:** When an authoritative reference doc exceeds what fits in
working attention, distill a decision-table runbook skill that routes back to
the reference — the skill handles the 90% path, the doc handles depth.

### Observation 2: pellet-printer-tuning superseded by fleet-wide printer-configuration

**Status:** ACTIONED — `.claude/skills/printer-configuration/SKILL.md` created; pellet skill removed
**Date:** 2026-07-23
**Session context:** User asked for skills covering ALL printers, materials,
settings, nozzles, and how settings display on the frontend — not just the
Penrose pellet stack.
**Skill:** printer-configuration
**Type:** internal
**Phase/Area:** skill scoping

**Issue:** The first skill (pellet-printer-tuning) was scoped to the printer
the immediate task targeted. The user's actual need was fleet-wide
configuration competence including the settings→frontend pipeline. Two
overlapping skills would drift, so the pellet skill was folded into the
fleet-wide one (with a pellet-specific rules section) and deleted.

**Suggested improvement:** Done — single skill with an architecture summary,
where-does-the-change-go table, silent-failure rules, UI-display checklist,
verification steps, and a known-open-issues list.

**Principle:** Scope a skill to the recurring capability the user needs, not
to the first task instance; when a narrower skill is subsumed, delete it
rather than letting two copies drift.

### Observation 3: Runtime-load verification promoted into the skill

**Status:** ACTIONED — `verify_definitions_load.py` added as printer-configuration skill companion; verify step updated
**Date:** 2026-07-23
**Session context:** Fixing the errors found during fleet mapping; while
verifying the barrel-temp fix through the real Uranium loader, an incidental
"Unable to override setting support_xy_distance" warning exposed a fourth bug
(trailing space in a JSON override key) that printer-linter does not detect.
**Skill:** printer-configuration
**Type:** internal
**Phase/Area:** Verify checklist

**Issue:** Static linting (printer-linter) missed a whitespace-damaged
override key that Uranium silently drops at load time — the override had been
dead on all dual/IDEX printers. Only loading definitions through the real
DefinitionContainer surfaces this class of failure.

**Suggested improvement:** Done — the ad-hoc verification harness was
generalized into a repo-relative companion script inside the skill directory
and added to the skill's verify checklist. Long-term home for a static
equivalent is a new printer-linter diagnostic (respecting the scripts/ vs
printer-linter/ ownership boundary in AGENTS.md).

**Principle:** When a one-off verification harness catches a real bug class,
promote it into the relevant skill as a runnable companion tool instead of
letting it die in the scratchpad; place permanent CI-grade versions in the
architecturally-correct owner per the repo contract.

### Observation 4: Dual-mode-printer pattern belongs in the skill

**Status:** ACTIONED — documented in docs/agents.md + printer-configuration skill knowledge
**Date:** 2026-07-23
**Session context:** User asked to model two Penrose products that each run
pellet OR filament (manual head swap / IDEX park-one-carriage), switchable.
**Skill:** printer-configuration
**Type:** internal
**Phase/Area:** architecture / new-printer creation

**Issue:** Cura cannot represent "one machine, runtime pellet/filament toggle"
because exclude_materials + quality_definition + machine_barrel_heater
(settable_per_extruder:false) are all fixed per definition at load. The clean
model is a PAIR of single-extruder definitions per product over shared hidden
bases, with quality REUSED via variant-name+material stub keys (zero new
quality files). This is a reusable pattern, not a one-off.

**Suggested improvement:** Captured in docs/agents.md ("Dual-mode printers").
Consider adding a short cross-reference in the skill's "Where does the change
go?" table so the pattern is discoverable when someone models the next
swappable/multi-head printer.

**Principle:** When the data model can't express a requested runtime toggle,
the fix is usually to split into multiple static definitions and reuse the
shared substrate (here: quality stubs keyed on variant+material, not machine),
not to force a toggle the framework will silently break.

### Observation 5: Permutation coverage checker instantly repaid its cost

**Status:** ACTIONED — verify_quality_coverage.py added as skill companion; 5 bug classes fixed
**Date:** 2026-07-23
**Session context:** "Ensure all permutations and combinations are fully
usable" for the new dual-mode Penrose printers.
**Skill:** printer-configuration
**Type:** internal
**Phase/Area:** Verify checklist

**Issue:** A static checker that mirrors MaterialNode._loadAll's fallback
chain (exact→brand+type→type→GUID→global, failing on unfiltered-global) found,
on first run: 25 UTF-8-BOM'd quality files (tolerated by FastConfigParser but
fatal to the stdlib-configparser version-upgrade path), an invalid boot
quality (pellet_030 has no stub for the default 1.5 mm nozzle) on all four
pellet defs, a variant-name mismatch disabling filtering for a whole nozzle
(volterra "Model 1 mm"), a corrupted stub (stray line), and two generic
materials (ASA/CPE) that never had stub coverage anywhere.

**Suggested improvement:** Done — checker added to the skill's verify list
with BOM detection built in. Key subtlety worth remembering: parser-tolerance
differences (FastConfigParser vs stdlib configparser) mean "the app loads it
today" does not prove the file is well-formed for every code path that reads
it.

**Principle:** When the requirement is "all permutations work", enumerate the
permutation space mechanically against the real resolution algorithm — spot
checks and per-file linting systematically miss cross-file key-matching bugs.

### Observation 6: Parity-diff tool for "machine X should work like machine Y" reviews

**Status:** ACTIONED — `diff_definition_settings.py` added as skill companion; verify checklist updated
**Date:** 2026-07-23
**Session context:** Comprehensive pre-hardware review of the Penrose filament
machines, which "should work like a Dragon 3D printer".
**Skill:** printer-configuration
**Type:** internal
**Phase/Area:** Verify checklist / review workflow

**Issue:** "Works like machine Y" claims were being reviewed by reading defs
side by side. A trivial script that merges each printer's overrides down its
inherits chain and diffs the result turned the claim into an 18-key list where
every delta had to be classifiable (frame kinematics / intentional process
choice / cosmetic) — instantly separating intentional TD600-derived speeds
from Dragon-700-only tweaks like `speed_roofing`.

**Suggested improvement:** Done — promoted the scratchpad script into the
skill directory with a usage line in the verify checklist.

**Principle:** Turn equivalence claims ("behaves like X") into mechanical
diffs of the effective merged configuration; a reviewable delta list forces
every difference to be explained rather than overlooked.
