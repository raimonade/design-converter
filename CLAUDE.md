# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

**DesignDev** is a unified workspace for design tooling across Figma, Pencil.dev, and Paper Design System. It contains MCP servers, Figma plugins, CLI tools, a Python design-conversion service, and AI skills — all wired together to support AI-assisted design workflows.

---

## Development Commands

### AI Designer Plugin (`plugins/ai-designer/`)
```bash
npm run dev      # Watch plugin + UI (Preact/Vite)
npm run build    # Production build
npm run proxy    # Start LLM proxy on port 11435
npm run test     # Run plugin tests
```

### Figma Console MCP (`mcps/figma-console/`)
```bash
npm run dev:local        # Local development
npm run build:local      # Compile TypeScript → dist/local.js
npm run build:cloudflare # Compile for Cloudflare Workers
npm run test             # Jest test suite
npm run lint:fix         # Biome linting + auto-fix
```

### Claude Talk to Figma MCP (`mcps/claude-talk-to-figma/`)
```bash
npm run build            # Compile via tsup
npm run dev              # Watch + rebuild
npm run test             # Jest tests
npm run test:integration # Integration tests
```

### CLI Tools (`cli/bin/`)
```bash
# Add to PATH first:
export PATH="$HOME/Projects Parent Folder/DesignDev/cli/bin:$PATH"

figma-tokens.sh --preset=shadcn --export=css
figma-analyze.sh --type=colors --json
figma-workflow-runner.sh design-system
figma-smoke-test.sh --quick
```
Exit codes for all CLI tools: `0` success, `1` error, `2` not connected to Figma.

### Design Converter Service (`services/design-converter/`)
```python
from adapters.figma import FigmaReader
from adapters.paper import PaperWriter

tree = FigmaReader().read_node(file_key="abc123")
PaperWriter().write_node(tree, output_path="./output")
```

### UI-UX-Pro-Max Skills (`skills/ui-ux-pro-max/`)
```bash
python3 skills/ui-ux-pro-max/scripts/search.py "SaaS dashboard" --design-system
```

### MCP Setup
```bash
./mcps/add-to-opencode.sh   # Add all MCPs to OpenCode
```

---

## Architecture

### Three MCP Servers

| MCP | Location | Capability |
|-----|----------|------------|
| `figma-console` | `mcps/figma-console/` | 56+ tools, FULL CRUD via Desktop Bridge WebSocket |
| `claude-talk-to-figma` | `mcps/claude-talk-to-figma/` | Claude-optimized, accessibility audit tools |
| `official` | `mcps/official/` | Official Figma MCP, read-only, Dev Mode |

All CRUD MCPs depend on the **Desktop Bridge Plugin** (`plugins/desktop-bridge/`) installed in Figma. Communication is over WebSocket on ports 9223–9232 with auto-fallback.

### Plugin Architecture

- **AI Designer** (`plugins/ai-designer/`): TypeScript + Preact + Vite + Tailwind CSS. Two layers: `src/plugin/` (sandbox worker running in Figma) and `src/ui/` (iframe Preact app). Communicates over `figma.ui.postMessage`.
- **Desktop Bridge** (`plugins/desktop-bridge/`): Vanilla JS plugin. Acts as WebSocket bridge between MCP servers and Figma's plugin API.

### Design Converter — IR Pattern

The Python service in `services/design-converter/` uses an **Intermediate Representation** (UNNode tree) to convert between tools:

```
Figma ←→ UNNode (IR) ←→ Paper
              ↕
           Pencil
```

All adapters implement `BaseReader.read_node()` → UNNode and `BaseWriter.write_node()` ← UNNode. The IR is defined in `ir/nodes.py` (UNNode, NodeType, UNColor, UNTextStyle, UNLayout).

**FigmaWriter** (`adapters/figma/writer.py`) emits Figma Plugin API JavaScript IIFEs. Two modes:
- `mode="script"` (default) — saves a `.js` file to paste into Figma ▶ Plugins ▶ Console
- `mode="bridge"` — starts a pure-Python RFC 6455 WebSocket server on port 9224; Desktop Bridge plugin must connect there

**`converter.py`** — main orchestrator with `ConvertSpec`, `ConvertResult`, `DesignConverter`, and embedded argparse CLI.
**`cli/bin/design-convert.sh`** — bash entry-point following the same patterns as `figma-tokens.sh`; supports interactive mode, `--list`, `--info`, `--dry-run`, `--json`.

---

## MCP Connection Details

### Paper Design MCP (`localhost:29979`)
- **Protocol**: HTTP SSE (JSON-RPC over Server-Sent Events)
- **Headers required**: `Content-Type: application/json`, `Accept: application/json, text/event-stream`
- **Session**: send `initialize` first, capture `mcp-session-id` from response headers, include it in all subsequent requests
- **Server name**: `paper-desktop v0.1.4`
- **Note**: Background agents CANNOT access Paper MCP — must use main Claude session

```bash
# Test connection
curl -s -X POST http://127.0.0.1:29979/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
```

### Pencil.dev MCP
- **Binary**: `~/.cursor/extensions/highagency.pencildev-0.6.28-universal/out/mcp-server-darwin-arm64`
- **Default**: stdio JSON-RPC
- **HTTP mode**: `mcp-server-darwin-arm64 --app desktop --http --http-port 19002`
- **Auto-detects port**: `PencilClient` probes ports 19000–19009
- **Wallet2.pen location**: `/Users/william/Projects Parent Folder/Pencil.dev-Designs/Wallet2.pen`

### Desktop Bridge WebSocket Protocol
- **figma-console MCP** acts as the **SERVER** (port 9223)
- **Desktop Bridge Figma plugin** is the **CLIENT** (connects to MCP's port)
- **FigmaWriter bridge mode** runs its OWN server on port 9224 — plugin must be reconfigured

```json
// Request:
{"id": "ws_1_1234567890", "method": "EXECUTE_CODE", "params": {"code": "...", "timeout": 30000}}
// Response:
{"id": "ws_1_1234567890", "result": {"success": true, "nodeId": "..."}}
```

### Knowledge Base

`docs/knowledge/` contains 9 Markdown guides intended as **LLM context injection** for design tasks (token system, component architecture, variable system, generation guidelines, etc.). Read these when working on Figma plugin or MCP tool logic.

---

## Key Conventions

- **TypeScript** for all MCP servers and plugin code. `figma-console` uses Biome for linting (not ESLint).
- **Python** for design-converter and skills. No framework — pure stdlib + requests.
- **Bash** for CLI tools in `cli/bin/` — all support `--help`, `--dry-run`, and interactive mode.
- MCP configs live at `mcps/mcp-config.json`. When adding new MCP servers, register them there.
- `.pen` files (Pencil) are **encrypted binary** — use the `pencil` MCP tools, never read with file tools.

## Design Converter — Documentation Rule

**Whenever any file inside `services/design-converter/` is modified, update both HTML references:**
1. `services/design-converter/docs/UNNODE_DEEP_DIVE.html` — standalone reference
2. `dashboards/figma-tools.html` (IR Reference tab) — the same sections, same content

Files that trigger a doc update:
- `ir/nodes.py` — new fields, enums, dataclasses, factory functions, serialisation
- `adapters/figma/`, `adapters/paper/`, `adapters/pencil/` — reader/writer/client changes
- `utils/` — new utilities or changed signatures
- `converter.py` — new CLI flags, new public methods

Which HTML sections to edit:
| Change | Sections to update |
|--------|-------------------|
| New UNNode field | §2 deep dive, Appendix B field reference |
| New/changed enum | §2 deep dive, Appendix C enum reference |
| New factory function | §2.10 factory helpers |
| Serialisation change | §2.11 serialisation |
| Adapter bug fix / new feature | §7 roadmap (mark phase complete), §8 implementation guide |
| New gap closed | §6 gap analysis (mark resolved), §7 roadmap |
| New CLI flag | §8 implementation guide |

Edit only the sections relevant to the change. Keep Appendix D changelog updated.
