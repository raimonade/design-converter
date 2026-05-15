# paper-figma

Bidirectional converter between [Paper Design](https://paper.design) and Figma.

Reads Paper's design tree via MCP, generates Figma Plugin API JavaScript, and pushes to Figma via a persistent WebSocket bridge.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install requests
```

## Usage

### 1. Start the bridge server (once)

```bash
.venv/bin/python3 services/design-converter/adapters/figma/bridge_server.py --port 9223
```

Then connect the Desktop Bridge plugin in Figma to port 9223. The server stays running — no reconnection needed between runs.

### 2. Convert artboards

```bash
# Convert a specific artboard
.venv/bin/python3 paper_to_figma.py --artboard 1J3-0

# Convert all artboards
.venv/bin/python3 paper_to_figma.py

# Dry run (output JS without pushing)
.venv/bin/python3 paper_to_figma.py --artboard 1J3-0 --dry-run --output /tmp/hero.js
```

## Architecture

```
Paper MCP (localhost:29979)
    ↓ get_children, get_computed_styles, get_screenshot
ptf/ (Python)
    ↓ TreeNode → Figma Plugin API JavaScript
Bridge Server (HTTP POST /execute)
    ↓ WebSocket
Desktop Bridge Plugin → Figma
```

### Modules

| Module | Purpose |
|--------|---------|
| `ptf/mcp_client.py` | Paper MCP HTTP client (SSE parsing) |
| `ptf/tree.py` | TreeNode builder, style attachment, image fetching |
| `ptf/parsers.py` | CSS value parsers, font/color mapping |
| `ptf/codegen.py` | Figma Plugin API JS code generator |
| `bridge_server.py` | Persistent HTTP+WebSocket bridge to Figma |

### Features

- Auto-layout mapping (CSS flex → Figma auto-layout)
- Font family/weight mapping (Geist → Inter)
- Background images embedded as base64
- SVG nodes exported as raster images via Paper MCP
- Box shadows, border radius, borders/strokes
- Proper child sizing (stretch, grow, shrink)

## IR Layer

`services/design-converter/` contains an intermediate representation (UNNode) for bidirectional conversion. This is the foundation for future Figma→Paper support.
