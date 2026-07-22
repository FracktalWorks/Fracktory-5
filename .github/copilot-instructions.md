## Read the repo contracts first

- `AGENTS.md` (repo root) is a binding work contract with per-directory
  children (`cura/`, `plugins/`, `resources/`, `scripts/`, `tests/`,
  `printer-linter/`). Read the chain from root down to every path you touch
  before editing.
- Printer/profile/material engineering (anything under `resources/`) is
  governed by `docs/agents.md` — the authoritative guide for the quality
  resolution chain, material XML, variants, and start/end g-code. The
  operational runbook for printer/material/quality/setting changes across the
  whole fleet (incl. how settings surface in the frontend UI) is
  `.claude/skills/printer-configuration/SKILL.md` — usable as plain
  documentation from any tool.
- After changing `resources/` files, run
  `python printer-linter/src/terminal.py "<files>" --diagnose` and verify
  profiles resolve in the app (correct quality list per nozzle+material).

## Terminal output — prefix noisy commands with `rtk`

`rtk` (Rust Token Killer) filters verbose command output before it reaches the
model, cutting ~60–90% of the tokens on common dev commands with no loss of the
signal (failures, diffs, status). In Claude Code a hook applies this
automatically; **in Copilot Chat you must write `rtk` yourself** because the
Chat host does not rewrite terminal commands.

When running any of these in the terminal, prefix the command with `rtk`:

- Tests: `rtk pytest ...`, `rtk jest ...`, `rtk vitest ...`, `rtk go test ...`
- Lint/type: `rtk ruff ...`, `rtk mypy ...`, `rtk tsc ...`, `rtk eslint ...`
- VCS: `rtk git status`, `rtk git diff`, `rtk git log`
- Infra: `rtk docker ...`, `rtk kubectl ...`, `rtk psql ...`

Do **not** use `rtk` for:

- `uv run ...` — `rtk` is a standalone binary, not a uv tool; run tests as bare
  `rtk pytest ...` (or `rtk pip ...`, which auto-detects uv), never `uv run rtk`.
- Reading files — prefer the Graphify MCP and the editor's file tools over
  `rtk read`; they give better, symbol-aware context.

If `rtk` is not installed (`rtk --version` fails), run commands normally.

## Code intelligence — use the Graphify MCP

A `graphify` MCP server is configured in `.vscode/mcp.json`, serving a
pre-indexed knowledge graph (`graphify-out/graph.json`) of the Python code,
printer `*.def.json` definitions, and docs — with typed, evidence-tagged edges.
Prefer one `graphify` query (query_graph / get_neighbors / shortest_path) over
a grep + read loop when locating code, tracing call paths, or checking a
change's blast radius. Rebuild after large changes with `graphify update .`.
Note: `.inst.cfg` profiles and material XML are NOT in the graph — use
grep/file search for those.

