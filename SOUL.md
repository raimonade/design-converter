# DesignDev — Project Identity

**Purpose:** Unified design development workspace for Figma, Pencil, and Paper design tools.

**Vision:** Single source of truth for all design-related development, automation, and knowledge.

---

## Core Beliefs

1. **Everything in one place** — No scattered configs or duplicated knowledge
2. **Design is engineering** — Tools, CLI, MCPs are as important as the designs themselves
3. **Automation first** — If you do it twice, script it
4. **Knowledge compounds** — Every lesson learned should be documented
5. **Integration over isolation** — All tools should work together

---

## What We Build

### Plugins
- **AI Designer** (`plugins/ai-designer/`) — AI-powered Figma plugin with multi-model support (GLM-5, Kimi, GPT-4o)
- **Desktop Bridge** (`plugins/desktop-bridge/`) — MCP bridge plugin for Figma Console integration

### MCP Servers
- **figma-console** (`mcps/figma-console/`) — 56+ tools, full CRUD via Desktop Bridge WebSocket
- **claude-talk-to-figma** (`mcps/claude-talk-to-figma/`) — Claude-optimized, accessibility audit tools
- **official** (`mcps/official/`) — Official Figma MCP, read-only, Dev Mode integration

### CLI Tools (`cli/bin/`)
- **figma-tokens.sh** — Extract design tokens (CSS / JSON / Tailwind)
- **figma-analyze.sh** — Analyze Figma files for colors, typography, components
- **figma-workflow-runner.sh** — Run predefined design workflows
- **figma-smoke-test.sh** — E2E test suite
- **design-convert.sh** — Convert designs between Figma / Paper / Pencil

### Design Converter Service (`services/design-converter/`)
Python service providing a unified translation layer between Figma, Paper, and Pencil.dev:
```
Figma ←→ UNNode (IR) ←→ Paper
              ↕
           Pencil
```
- **IR**: `ir/nodes.py` — UNNode dataclass tree, all enums, factory helpers, serialisation
- **Adapters**: Figma (REST read + Plugin JS write), Paper (MCP JSON-RPC), Pencil (HTTP REST)
- **Utils**: `utils/tokens.py` — W3C DTCG 2025.10 design token export

### Skills
- **UI-UX-Pro-Max** (`skills/ui-ux-pro-max/`) — Design intelligence with 13 CSV databases
- **Will-Designer** (`skills/will-designer/`) — Designer-specialized agent

### Dashboards
- **figma-tools.html** (`dashboards/figma-tools.html`) — Primary workspace dashboard
  - Dashboard tab: MCP server status, tool catalog, search
  - IR Reference tab: Complete UNNode deep dive documentation

### Knowledge Base (`docs/knowledge/`)
9 Markdown guides for LLM context injection: token system, component architecture, variable system, generation guidelines, and more.

---

## Architecture

```
User Input
    │
    ▼
┌──────────────────────────────────────────────┐
│                DesignDev Tools                │
├────────────┬────────────┬────────────────────┤
│  CLI (bash)│  MCP Servers│  Skills           │
│  figma-*   │  figma-     │  ui-ux-pro-max    │
│  design-   │  console    │  will-designer    │
│  convert   │  claude-    │                   │
│            │  talk       │                   │
│            │  official   │                   │
└────────────┴────────────┴────────────────────┘
    │              │                │
    ▼              ▼                ▼
┌──────────────────────────────────────────────┐
│            Design Converter IR               │
│  Figma ↔ UNNode ↔ Paper | Pencil            │
└──────────────────────────────────────────────┘
    │              │
    ▼              ▼
┌──────────────────────────────────────────────┐
│           Design Outputs                      │
├─────────────────────┬────────────────────────┤
│ Plugins (Figma)     │ Designs (Pencil/Paper) │
│ ai-designer         │ .pen files             │
│ desktop-bridge      │ paper designs          │
└─────────────────────┴────────────────────────┘
```

---

## Supported Tools

| Tool | Purpose | Integration |
|------|---------|-------------|
| Figma | Design source | Plugin + MCP + REST API |
| Pencil.dev | Design editor | .pen files + HTTP MCP |
| Paper | Design system | MCP JSON-RPC |
| Claude | AI generation | MCP + CLI |

---

## Workflows

### Design-to-Code
1. Design in Figma
2. AI Designer generates components
3. Extract tokens via CLI (`figma-tokens.sh`)
4. Export to CSS/Tailwind/JSON
5. Integrate into codebase

### Cross-tool Conversion
1. Read design from Figma → UNNode IR
2. Write UNNode IR → Paper / Pencil.dev
3. Or reverse: read Pencil → write Figma Plugin JS

### DTCG Token Export
1. `design-convert.sh --export-tokens tokens.json --source figma`
2. Apply tokens via CSS vars or Style Dictionary

---

## Anti-Patterns

- **Scattered configs** — All config in this repo
- **Duplicated knowledge** — Single source of truth
- **Manual processes** — Automate everything
- **Isolated tools** — Integrate deeply
- **Forgotten learnings** — Document everything

---

## Key Rules

### Documentation Rule (design-converter)
Whenever any file in `services/design-converter/` is modified, update:
1. `services/design-converter/docs/UNNODE_DEEP_DIVE.html` — standalone reference
2. The IR Reference tab in `dashboards/figma-tools.html` (§ that changed)

See `CLAUDE.md` and `AGENTS.md` for the full lookup table.

---

## Success Metrics

- All tools accessible from single CLI
- 100% reproducible design-to-code workflows
- Zero manual token extraction
- Integrated design converter with full round-trip fidelity

---

**Last Updated:** 2026-03-01
**Version:** 1.1.0
