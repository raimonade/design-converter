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
#XT|# ├── mcps/
#RR|# │   ├── figma-console/        # Figma Console MCP (56+ tools, FULL CRUD)
#PH|# │   ├── claude-talk-to-figma/  # Claude-first Figma MCP
#PV|# │   ├── official/             # Official Figma MCP
#KM|# │   ├── desktop-bridge/       # Desktop Bridge MCP
#JK|# │   └── shared/               # Shared utilities
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
├── services/               # Backend services
│   └── design-converter/  # Design format converter (Figma/Paper/Pencil)
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
#TQ|```
#QM|## MCP Servers
#VB|
#BQ|DesignDev includes 3 Figma MCP servers for full design workflow integration:
#BV|
#BB|### figma-console (`mcps/figma-console/`)
#HV|
#HV|**56+ tools, FULL CRUD access** via Desktop Bridge Plugin.
#SB|
#BS|**Features:**
#XZ|- Read/write Figma files
#JB|- Variables and design tokens management
#XZ|- Component creation and modification
#JB|- Real-time bidirectional communication
#BV|
#BQ|**Setup:**
#BV|```bash
#BV|cd mcps/figma-console
#BV|npm install
#BV|# Install Desktop Bridge Plugin in Figma
#BV|```
#BT|
#BK|### claude-talk-to-figma (`mcps/claude-talk-to-figma/`)
#PQ|
#BC|Claude-first optimization with accessibility features.
#BS|
#XB|**Features:**
#BS|- Optimized for Claude AI interactions
#XB|- Accessibility linting and audit tools
#BS|- Semantic variable extraction
#BV|
#BQ|**Setup:**
#BV|```bash
#BV|cd mcps/claude-talk-to-figma
#BV|npm install
#BV|```
#BS|
#MM|### Official Figma MCP (`mcps/official/`)
#QM|
#QM|Official Figma MCP server with Dev Mode integration.
#BV|
#BM|**Features:**
#MM|- Read-only file access
#BN|- Dev Mode and Code Connect
#BM|- Style extraction
#BK|
#BQ|**Setup:**
#BV|```bash
#BV|cd mcps/official
#BV|npm install
#BV|```
#BQ|
#QM|### Quick Add to OpenCode
#BV|
#BV|```bash
#BV|./mcps/add-to-opencode.sh
#BV|```
#BQ|
#QM|---

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

## Design Converter — Documentation Rule

**Whenever any file inside `services/design-converter/` is modified, update BOTH HTML references:**
1. `services/design-converter/docs/UNNODE_DEEP_DIVE.html` — standalone reference
2. `dashboards/figma-tools.html` (IR Reference tab) — same sections, same content

This is a standing rule for all agents and sessions.

What triggers an HTML update and which sections to touch:

| Change type | Sections to update |
|-------------|-------------------|
| New `UNNode` field | §2 deep dive, Appendix B field reference |
| New or changed enum | §2 deep dive, Appendix C enum reference |
| New factory function | §2.10 factory helpers |
| `un_node_to_dict` / `un_node_from_dict` changes | §2.11 serialisation |
| Adapter bug fix or new feature | §7 roadmap (mark phase complete), §8 guide |
| Gap closed (G1–G10) | §6 gap analysis, §7 roadmap |
| New CLI flag on `converter.py` | §8 implementation guide |
| New adapter (new design tool) | §1 executive summary, §4 competitive landscape, §8 adapter pattern |

Edit only the sections relevant to the change. Keep the changelog table (Appendix D) updated.

---

## Design Converter Service

### Overview

The **design-converter** service (`services/design-converter/`) provides a unified translation layer that converts designs between Figma, Paper Design, and Pencil.dev using a common Intermediate Representation (UNNode tree).

**Architecture:**
```
Figma ←→ UNNode (IR) ←→ Paper
         ↕
      Pencil
```

### Structure

```
services/design-converter/
├── ir/                    # Intermediate Representation
│   ├── __init__.py
│   └── nodes.py           # UNNode, NodeType, UNColor, UNTextStyle
│
├── adapters/             # Design tool adapters
│   ├── base.py           # BaseReader, BaseWriter interfaces
│   ├── figma/           # Figma adapter
│   │   ├── client.py     # FigmaClient (REST API)
│   │   ├── reader.py     # FigmaReader (Figma → UNNode)
│   │   └── writer.py     # FigmaWriter (UNNode → Figma) [TODO]
│   ├── paper/           # Paper adapter
│   │   ├── client.py     # PaperClient (MCP JSON-RPC)
│   │   ├── reader.py     # PaperReader (JSX → UNNode)
│   │   └── writer.py     # PaperWriter (UNNode → HTML)
│   └── pencil/          # Pencil adapter
│       ├── client.py     # PencilClient (HTTP REST)
│       ├── reader.py    # PencilReader (Pencil → UNNode)
│       └── writer.py     # PencilWriter (UNNode → Pencil)
│
└── utils/               # Shared utilities
    ├── color.py         # Color conversion (hex, rgb, hsl, Figma)
    ├── css.py          # CSS generation utilities
    ├── svg.py           # SVG parsing utilities
    └── jsx_parser.py   # JSX/React parsing utilities
```

### Intermediate Representation (UNNode)

The IR is defined in `ir/nodes.py`:

- **UNNode** - Core node with type, children, style properties
- **NodeType** - Enum of supported node types (FRAME, TEXT, RECTANGLE, ELLIPSE, etc.)
- **UNColor** - Color with r, g, b, a channels
- **UNTextStyle** - Text properties (fontFamily, fontSize, fontWeight, etc.)
- **UNLayout** - Layout properties (flexDirection, justifyContent, alignItems, etc.)

### Adapters

Each adapter follows the same interface pattern:

**BaseReader** - Read from design tool → UNNode tree
```python
from adapters.base import BaseReader

class FigmaReader(BaseReader):
    tool_name = "figma"
    
    def read_node(self, file_key: str, node_id: str = "") -> UNNode:
        # Calls FigmaClient.get_file() or get_file_nodes()
        # Converts via _figma_node_to_unnode() recursive function
```

**BaseWriter** - Write UNNode tree → design tool
```python
from adapters.base import BaseWriter

class FigmaWriter(BaseWriter):
    tool_name = "figma"
    
    def write_node(self, unnode: UNNode, file_key: str, parent_id: str = "") -> str:
        # Converts UNNode → Figma API JSON
        # Uses FigmaClient for REST API calls
```

### MCP Connections

- **Paper Design MCP**: `http://127.0.0.1:29979` (HTTP JSON-RPC)
- **Pencil.dev MCP**: HTTP mode (`--http --http-port 8080`)
- **Figma**: REST API + Desktop Bridge MCP

### Usage

```python
# Convert Figma to Paper
from adapters.figma import FigmaReader
from adapters.paper import PaperWriter

figma_reader = FigmaReader()
paper_writer = PaperWriter()

# Read from Figma
unnode_tree = figma_reader.read_node(file_key="abc123", node_id="")

# Write to Paper
paper_writer.write_node(unnode_tree, output_path="./output")
```

### Current Status

| Component | Status |
|-----------|--------|
| IR (nodes.py) | ✅ Complete |
| Base Adapter Interface | ✅ Complete |
| Paper Adapter | ✅ Complete |
| Pencil Adapter | ✅ Complete |
| Figma Reader | ✅ Complete |
| Figma Writer | ✅ Complete |
| Main Converter (`converter.py`) | ✅ Complete |
| CLI Integration (`cli/bin/design-convert.sh`) | ✅ Complete |
