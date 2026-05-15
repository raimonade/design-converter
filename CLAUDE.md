# CLAUDE.md

## What This Repo Is

**paper-figma** — bidirectional converter between Paper Design and Figma. Reads Paper's design tree via MCP, generates Figma Plugin API JavaScript, pushes via a persistent WebSocket bridge.

## Development Commands

```bash
# Start persistent bridge server (once, stays running)
.venv/bin/python3 services/design-converter/adapters/figma/bridge_server.py --port 9223

# Convert specific artboard
.venv/bin/python3 paper_to_figma.py --artboard 1J3-0

# Dry run (generate JS without pushing)
.venv/bin/python3 paper_to_figma.py --artboard 1J3-0 --dry-run --output /tmp/hero.js

# Convert all artboards
.venv/bin/python3 paper_to_figma.py
```

## Architecture

```
paper_to_figma.py          # CLI entry point
ptf/                       # converter package
  mcp_client.py            # Paper MCP HTTP client (SSE)
  tree.py                  # TreeNode, build_tree, attach_styles, fetch_images
  parsers.py               # CSS parsers, font/color mapping
  codegen.py               # FigmaCodeGen: TreeNode → Figma Plugin API JS
services/design-converter/ # IR layer (UNNode) + adapters for bidirectional conversion
  adapters/figma/
    bridge_server.py       # persistent HTTP+WS bridge to Figma plugin
    writer.py              # UNNode → Figma JS (IR-based path)
    reader.py              # Figma REST → UNNode
  adapters/paper/
    reader.py              # Paper MCP → UNNode
    writer.py              # UNNode → Paper HTML
  ir/nodes.py              # UNNode intermediate representation
```

## MCP Connection

### Paper Design MCP (`localhost:29979`)
- Protocol: HTTP SSE (JSON-RPC over Server-Sent Events)
- Headers: `Content-Type: application/json`, `Accept: application/json, text/event-stream`
- Session: send `initialize` first, capture `mcp-session-id`

### Desktop Bridge WebSocket
- Bridge server listens on port 9223 (HTTP + WebSocket)
- Desktop Bridge Figma plugin connects as WebSocket client
- HTTP clients POST to `/execute` with `{"code": "..."}`

## Key Conventions

- Python, pure stdlib + requests
- `ptf/` is the primary converter package (no dependency on `services/`)
- `services/design-converter/` is the IR-based path for bidirectional work
- Generated `.js` files go in `output-v2/` (gitignored)
