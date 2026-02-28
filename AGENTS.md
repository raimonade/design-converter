# DesignDev

> **Unified Design Development Workspace** - CLI tools, MCPs, plugins, and documentation for Figma/Pencil/Paper design workflows.

---

## Overview

DesignDev consolidates ALL design-related development into one repository:
- **Figma Plugins** (AI Designer, Desktop Bridge)
- **CLI Tools** (tokens, analyze, workflows)
- **MCP Servers** (Figma Console, Desktop Bridge)
- **Design Files** (Paper, Pencil)
- **Skills** (UI-UX-Pro-Max, Will-Designer)
- **Documentation** (knowledge, learnings, handoffs)

---

## Structure

```
DesignDev/
├── plugins/
│   ├── ai-designer/          # AI-powered Figma plugin
│   │   ├── src/plugin/       # Plugin sandbox code
│   │   ├── src/ui/           # Preact UI
│   │   ├── proxy/            # LLM proxy (port 11435)
│   │   ├── service-manager/  # Service orchestrator
│   │   └── tokens/           # Design token exports
│   │
│   └── desktop-bridge/       # MCP Bridge plugin
│       ├── code.js           # Main plugin (77KB)
│       ├── ui.html           # Plugin UI (41KB)
│       └── design-system-builder.js
│
├── cli/
│   ├── bin/                  # Shell scripts
│   │   ├── figma-tokens.sh   # Extract design tokens
│   │   ├── figma-analyze.sh  # Analyze Figma files
│   │   ├── figma-workflow-runner.sh  # Run workflows
│   │   └── figma-smoke-test.sh  # E2E tests
│   │
│   └── commands/             # Slash commands
│       └── figma-workflow.md # Agent instructions
│
├── mcps/
│   ├── figma-console/        # Figma Console MCP
│   ├── desktop-bridge/       # Desktop Bridge MCP
│   └── shared/               # Shared utilities
│
├── designs/
│   ├── paper/                # Paper design system
│   │   ├── PAPER_DESIGN_LEARNINGS.md
│   │   └── WALLET_V2_WORKFLOW_MAP.md
│   │
│   └── pencil/               # Pencil.dev designs
│       └── .pen files/
│
├── docs/
│   ├── knowledge/            # LLM knowledge base
│   │   ├── COMPONENT-ARCHITECTURE.md
│   │   ├── DESIGN-SYSTEM-PATTERNS.md
│   │   ├── FIGMA-PLUGIN-API.md
│   │   ├── FIGMA-VARIABLES.md
│   │   ├── LLM-GENERATION-GUIDELINES.md
│   │   ├── TEXT-COMPONENTS.md
│   │   └── TOKEN-SYSTEM.md
│   │
│   ├── learnings/            # Project learnings
│   └── handoffs/             # Design handoff templates
│
├── skills/
│   ├── ui-ux-pro-max/        # Design intelligence
│   └── will-designer/        # Designer agent
│
└── dashboards/
    └── figma-tools.html      # Status dashboard
```

---

## Quick Start

### CLI Tools

```bash
# Add to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$HOME/Projects Parent Folder/DesignDev/cli/bin:$PATH"

# Extract tokens
figma-tokens.sh --preset=shadcn --export=css

# Analyze file
figma-analyze.sh --type=colors --json

# Run workflow
figma-workflow-runner.sh design-system

# Run tests
figma-smoke-test.sh --quick
```

### Plugin Development

```bash
# AI Designer
cd plugins/ai-designer
npm install
npm run dev

# Desktop Bridge
cd plugins/desktop-bridge
# Load in Figma: Plugins > Development > Import plugin from manifest
```

### MCP Development

```bash
# Figma Console MCP
cd mcps/figma-console
npm run dev
```

---

## Plugins

### AI Designer (`plugins/ai-designer/`)

AI-powered Figma plugin with multi-model support (GLM-5, Kimi, GPT-4o).

**Features:**
- Generate designs from text prompts
- Create design systems with semantic variables
- Export tokens to CSS/JSON/Tailwind
- UI-UX-Pro-Max design intelligence

**Commands:**
```bash
npm run dev      # Development
npm run build    # Production build
npm run proxy    # Start LLM proxy
```

### Desktop Bridge (`plugins/desktop-bridge/`)

MCP Bridge plugin for Figma Console integration.

**Features:**
- WebSocket connection to MCP servers
- Real-time bidirectional communication
- Design system builder

---

## CLI Tools

### figma-tokens.sh
Extract design tokens from Figma files.

```bash
figma-tokens.sh                    # Interactive mode
figma-tokens.sh --preset=shadcn    # shadcn/ui format
figma-tokens.sh --preset=tailwind  # Tailwind format
figma-tokens.sh --export=css       # CSS output
figma-tokens.sh --export=json      # JSON output
```

### figma-analyze.sh
Analyze Figma files for components and styles.

```bash
figma-analyze.sh                    # Interactive mode
figma-analyze.sh --type=colors      # Color analysis
figma-analyze.sh --type=typography  # Typography analysis
figma-analyze.sh --type=all --json  # Full analysis as JSON
```

### figma-workflow-runner.sh
Run predefined design workflows.

```bash
figma-workflow-runner.sh --list              # List workflows
figma-workflow-runner.sh --dry-run design-system  # Preview
figma-workflow-runner.sh design-system       # Execute
```

**Workflows:**
| Template | Steps | Description |
|----------|-------|-------------|
| design-system | 5 | connect → tokens → visualize → analyze → export |
| component-library | 5 | connect → search → render → to-component → export |
| a11y-audit | 4 | connect → lint accessibility → analyze → typography |
| code-export | 4 | connect → export css → export tailwind → export jsx |

### figma-smoke-test.sh
E2E test suite for Figma tools.

```bash
figma-smoke-test.sh            # Full test (7 steps)
figma-smoke-test.sh --quick    # Quick test (3 steps)
figma-smoke-test.sh --skip-cleanup  # Skip cleanup
```

---

## Skills

### UI-UX-Pro-Max (`skills/ui-ux-pro-max/`)

Design intelligence with 13 CSV databases:
- Styles (67 UI styles)
- Colors (96 palettes)
- Typography (57 pairings)
- Products, Charts, Icons, Landing pages
- Stack guidelines (13 frameworks)

**Usage:**
```bash
python3 skills/ui-ux-pro-max/scripts/search.py "SaaS dashboard" --design-system
```

### Will-Designer (`skills/will-designer/`)

Design-specialized agent for instant UI/UX recommendations.

---

## Knowledge Base

Located in `docs/knowledge/`:
- **COMPONENT-ARCHITECTURE.md** - Figma component patterns
- **DESIGN-SYSTEM-PATTERNS.md** - Design system best practices
- **FIGMA-PLUGIN-API.md** - Plugin API reference
- **FIGMA-VARIABLES.md** - Variable system guide
- **LLM-GENERATION-GUIDELINES.md** - AI generation rules
- **TEXT-COMPONENTS.md** - Typography components
- **TOKEN-SYSTEM.md** - Design token architecture

---

## Exit Codes

All CLI tools use consistent exit codes:
- `0` = Success
- `1` = Error
- `2` = Not connected to Figma

---

## Related Repositories

| Repo | Purpose |
|------|---------|
| **DesignDev** | This repo - all design tools |
| **Paper** | Paper design system |
| **Pencil.dev** | Pencil editor and designs |

---

## Version

**DesignDev v1.0.0**
- Created: 2026-02-28
- Consolidated from: figma-ai-designer, Figma-AI-Plugin, Paper-design, CLI tools

---

## License

MIT
