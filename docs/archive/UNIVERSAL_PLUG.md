# Universal Design Plug - Architecture

## Overview

The design-converter now supports a **universal plug architecture** that enables seamless conversion between Figma, Paper Design, and Pencil.dev. All three platforms are now symmetric:

| Platform | Read | Write | Protocol |
|----------|------|-------|----------|
| **Paper** | ✅ HTTP | ✅ HTTP | `localhost:29979` |
| **Pencil** | ✅ MCP | ✅ MCP | MCP tools (`batch_design`) |
| **Figma** | ✅ REST | ✅ HTTP | `localhost:9223` (via bridge) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Design Converter                            │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    UNNode (IR)                           │   │
│   │  Universal Node Tree - represents any design element     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│   │  Figma   │         │  Paper   │         │  Pencil  │       │
│   │ Adapter  │         │ Adapter  │         │ Adapter  │       │
│   └────┬─────┘         └────┬─────┘         └────┬─────┘       │
└────────┼────────────────────┼────────────────────┼─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Figma       │  │  Paper Design   │  │   Pencil.dev    │
│                 │  │                 │  │                 │
│ ┌─────────────┐ │  │                 │  │                 │
│ │ HTTP Bridge │ │  │  HTTP :29979    │  │  MCP Tools      │
│ │ Server      │ │  │                 │  │                 │
│ │ :9223       │ │  │                 │  │                 │
│ └──────┬──────┘ │  │                 │  │                 │
│        │        │  │                 │  │                 │
│ ┌──────▼──────┐ │  │                 │  │                 │
│ │ Desktop     │ │  │                 │  │                 │
│ │ Bridge      │ │  │                 │  │                 │
│ │ Plugin      │ │  │                 │  │                 │
│ └─────────────┘ │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Figma Write Modes

FigmaWriter now supports three modes:

### 1. `mode="script"` (default)
- Generates a `.js` file
- User pastes into Figma ▶ Plugins ▶ Console
- No setup required
- Manual step

### 2. `mode="bridge"`
- Starts a WebSocket server on port 9224
- Desktop Bridge plugin connects to it
- Live execution
- Requires plugin reconfiguration

### 3. `mode="http"` (recommended)
- Uses HTTP bridge server (`figma-bridge-server`)
- Any client can POST to `localhost:9223/execute`
- Symmetric with Paper (HTTP 29979)
- Requires bridge server running

## Setup

### 1. Start the HTTP Bridge Server

```bash
# Start the bridge server (one-time setup)
figma-bridge-server --daemon

# Check status
figma-bridge-server --status

# Stop if needed
figma-bridge-server --stop
```

### 2. Connect Desktop Bridge Plugin

The Desktop Bridge plugin in Figma will automatically discover and connect to the bridge server on port 9223.

1. Open Figma
2. Run: `Plugins > Development > Figma Desktop Bridge`
3. Plugin auto-connects to port 9223

### 3. Use the Converter

```bash
# Paper → Figma (via HTTP bridge)
design-convert.sh paper:TO-0 figma: --figma-mode=http

# Pencil → Figma
design-convert.sh pencil:rfBGm figma: --figma-mode=http

# Figma → Paper (no bridge needed for reads)
design-convert.sh figma:ABC123 paper:

# Figma → Pencil
design-convert.sh figma:ABC123 pencil:
```

## HTTP Bridge API

The bridge server exposes a simple HTTP API:

### Health Check
```bash
curl http://localhost:9223/health
# {"status":"ok","plugin_connected":true,"port":9223}
```

### Execute Code
```bash
curl -X POST http://localhost:9223/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "figma.notify(\"Hello!\")", "timeout": 5000}'
# {"success":true,"result":{}}
```

### Create Rectangle
```bash
curl -X POST http://localhost:9223/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "(async()=>{const n=figma.createRectangle();figma.currentPage.appendChild(n);n.resize(200,150);n.fills=[{type:\"SOLID\",color:{r:1,g:0,b:0,a:1}}];return{success:true,nodeId:n.id};})()",
    "timeout": 10000
  }'
```

## Python API

```python
from design_converter.adapters.figma.http_bridge import FigmaBridgeClient
from design_converter.adapters.figma.writer import FigmaWriter
from design_converter.ir.nodes import make_rect

# Direct HTTP bridge usage
client = FigmaBridgeClient()
if client.is_connected():
    result = client.create_rectangle(100, 100, 200, 150, fill_color="#FF0000")
    print(f"Created: {result.node_id}")

# Via FigmaWriter
rect = make_rect("Red Box", x=100, y=100, width=200, height=150, fill_color="#FF0000")
writer = FigmaWriter(mode="http")
writer.connect()  # Verifies bridge is connected
node_id = writer.write_node(rect)
print(f"Created in Figma: {node_id}")
```

## Files

| File | Purpose |
|------|---------|
| `adapters/figma/http_bridge.py` | HTTP client for bridge server |
| `design_converter/adapters/figma/bridge_server.py` | Standalone HTTP+WebSocket bridge |
| `adapters/figma/writer.py` | FigmaWriter with `mode="http"` |
| `cli/bin/figma-bridge-server` | CLI to start/stop bridge |
| `cli/bin/design-convert.sh` | Updated with `--figma-mode=http` |

## Troubleshooting

### "HTTP bridge not connected"
- Start the bridge: `figma-bridge-server --daemon`
- Check if running: `figma-bridge-server --status`

### "Plugin not connected"
- Open Figma Desktop Bridge plugin
- Plugin should auto-connect to port 9223
- Check bridge status shows `plugin_connected: true`

### "Port already in use"
- Another MCP instance may be running on port 9223
- Kill it: `pkill -f figma-console-mcp`
- Restart bridge: `figma-bridge-server --stop && figma-bridge-server --daemon`
