# Design Converter

A Python service for converting designs between Figma, Paper Design, and Pencil.dev using a universal intermediate representation (IR).

## Quick Start

```bash
# Convert a Figma file to Paper
python3 converter.py figma:ABC123 paper:

# Dry-run (read only, no write)
python3 converter.py figma:ABC123 pencil: --dry-run --verbose

# List nodes in a source
python3 converter.py --list figma:ABC123

# Export design tokens
python3 converter.py figma:ABC123 --export-tokens tokens.json
```

## Architecture

```
                    +------------------+
                    |   DesignConverter|
                    |   (converter.py) |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
      +-------v-------+             +-------v-------+
      |   BaseReader  |             |   BaseWriter  |
      |  (adapters/)  |             |  (adapters/)  |
      +-------+-------+             +-------+-------+
              |                             |
   +----------+----------+       +----------+----------+
   |          |          |       |          |          |
+--v--+   +---v---+   +--v--+ +--v--+   +---v---+   +--v--+
|Figma|   | Paper |   |Pencil| |Figma|   | Paper |   |Pencil|
+-----+   +-------+   +------+ +-----+   +-------+   +------+
   |          |          |         |          |          |
   +----------+----------+---------+----------+----------+
                             |
                    +--------v---------+
                    |      UNNode      |
                    |  (ir/nodes.py)  |
                    |  Intermediate   |
                    |  Representation |
                    +------------------+
```

**Conversion Flow:**
1. Parse source/destination specs (`figma:ABC123`, `paper:TO-0`, etc.)
2. Connect to source tool via Reader adapter
3. Read the node tree into UNNode IR
4. Connect to destination tool via Writer adapter
5. Write the UNNode tree to destination
6. Return result with node count, output path/ID, timing

## Spec Format

| Format | Description |
|--------|-------------|
| `figma:FILE_KEY` | Whole Figma file |
| `figma:FILE_KEY/NODE_ID` | Specific Figma node |
| `https://www.figma.com/design/...` | Figma URL (auto-parsed) |
| `paper:` | First Paper artboard |
| `paper:NODE_ID` | Specific Paper node |
| `pencil:` | Active Pencil file |
| `pencil:NODE_ID` | Specific Pencil node |

## CLI Usage

```
python3 converter.py [SOURCE] [DEST] [OPTIONS]

Actions:
  --list              List available nodes in SOURCE
  --info              Show file/document info for SOURCE

Conversion Options:
  --parent-id ID      Parent node ID in destination
  --replace-id ID     Replace existing node with this ID
  --dry-run           Read source only; do not write

Output:
  --json              Machine-readable JSON output
  --verbose, -v       Print progress messages

Figma Writer:
  --figma-writer-mode {script,bridge,http}
                      script: save .js file (default)
                      bridge: start WebSocket server on port 9224
                      http: connect to existing bridge on port 9223
  --bridge-port PORT  WebSocket port (default: 9224)
  --figma-token TOKEN Figma API token

Token Export:
  --export-tokens FILE
                      Extract DTCG design tokens to JSON file

Exit Codes:
  0  Success
  1  General error
  2  Connection failure (tool not running)
```

### Examples

```bash
# Basic conversion
python3 converter.py figma:ABC123 paper:
python3 converter.py paper:TO-0 pencil:
python3 converter.py pencil: figma:

# Specific node conversion
python3 converter.py figma:ABC123/1:2 paper: --verbose

# Dry-run to inspect source
python3 converter.py figma:ABC123 pencil: --dry-run --json

# Export tokens from any source
python3 converter.py figma:ABC123 --export-tokens design-tokens.json

# Figma script mode (generates .js to paste in Figma console)
python3 converter.py paper:TO-0 figma: --figma-writer-mode=script

# List nodes in a Figma file
python3 converter.py --list figma:ABC123 --json

# Get file info
python3 converter.py --info paper:
```

## Python API

```python
from converter import DesignConverter

# Initialize
conv = DesignConverter(
    figma_token="figd_xxx",  # Optional, uses FIGMA_API_KEY env var
    figma_writer_mode="script",  # "script" | "bridge" | "http"
)

# Convert between tools
result = conv.convert("figma:ABC123", "paper:")
print(result.success)      # True/False
print(result.node_count)   # Number of nodes converted
print(result.output)       # Destination node ID or file path
print(result.elapsed_ms)   # Duration in milliseconds

# Dry-run (read only)
result = conv.convert("figma:ABC123", "paper:", dry_run=True)

# Read node tree directly
tree = conv.read_node("figma:ABC123/1:2")
for node in tree.walk():
    print(f"{node.type.value}: {node.name}")

# List available nodes
nodes = conv.list_nodes("paper:")
for n in nodes:
    print(f"{n['id']}: {n['name']}")

# Get file info
info = conv.get_info("figma:ABC123")
print(info['fileName'], info['nodeCount'])
```

### Using Adapters Directly

```python
from adapters.figma import FigmaReader, FigmaWriter
from adapters.paper import PaperReader, PaperWriter
from adapters.pencil import PencilReader, PencilWriter

# Read from Figma
with FigmaReader(token="figd_xxx") as reader:
    tree = reader.read_node("FILE_KEY", "NODE_ID")

# Write to Paper
with PaperWriter() as writer:
    node_id = writer.write_node(tree, parent_id="TO-0")

# Read from Pencil
with PencilReader() as reader:
    tree = reader.read_node("frame123")

# Write to Figma (script mode)
writer = FigmaWriter(mode="script", output_dir="./output")
writer.connect()
js_path = writer.write_node(tree)  # Returns path to .js file
writer.disconnect()
# Paste the .js file contents into Figma > Plugins > Development > Console
```

### Building Nodes Programmatically

```python
from ir import (
    UNNode, NodeType, UNColor, UNPadding, UNCornerRadius,
    LayoutMode, JustifyContent, AlignItems, UNSize,
    make_frame, make_text, make_rect, make_solid_fill, make_shadow
)

# Using factory functions
card = make_frame(
    "Card",
    width=320,
    height=200,
    fill_color="#FFFFFF",
    layout=LayoutMode.VERTICAL,
    gap=12,
    padding=UNPadding.all(16),
    corner_radius=12,
)
card.add_effect(make_shadow(color="#00000020", offset_y=4, blur=12))

title = make_text("Title", "Welcome", font_size=24, font_weight="700", color="#1A1A1A")
card.add_child(title)

# Using UNNode directly
rect = UNNode(
    type=NodeType.RECTANGLE,
    name="Box",
    width=UNSize.fixed(100),
    height=UNSize.fixed(100),
    corner_radius=UNCornerRadius.all(8),
)
rect.fills.append(make_solid_fill("#3B82F6"))
```

## Intermediate Representation (IR)

The `ir/nodes.py` module defines the Universal Node Tree (UNT) - a tool-agnostic representation modeled after Figma's node architecture.

### Core Types

| Type | Description |
|------|-------------|
| `UNNode` | Universal node (frame, text, rectangle, etc.) |
| `UNColor` | RGBA color (0.0-1.0 floats) |
| `UNFill` | Solid, gradient, or image fill |
| `UNStroke` | Stroke with fill, thickness, alignment |
| `UNEffect` | Drop shadow or blur |
| `UNSize` | Size with fixed/hug/fill mode |
| `UNPadding` | 4-sided padding |
| `UNCornerRadius` | 4-corner radii |
| `UNTextStyle` | Typography properties |
| `UNTextRun` | Rich text style override |
| `UNVariableBinding` | Design token binding |

### Node Types

| NodeType | Description |
|----------|-------------|
| `FRAME` | Container with optional flex layout |
| `TEXT` | Text content with style |
| `RECTANGLE` | Solid rectangle |
| `ELLIPSE` | Circle or ellipse |
| `PATH` | Vector path (SVG geometry) |
| `LINE` | Straight line |
| `GROUP` | Non-layout group |
| `IMAGE` | Raster image |
| `COMPONENT` | Figma component definition |
| `INSTANCE` | Figma component instance |

### Layout System

The IR uses flexbox-inspired layout matching all three tools:

```python
node.layout = LayoutMode.HORIZONTAL  # or VERTICAL, NONE
node.gap = 8.0                       # Spacing between children
node.padding = UNPadding.all(16)     # Inner padding
node.justify_content = JustifyContent.START  # Main axis
node.align_items = AlignItems.STRETCH        # Cross axis
node.width = UNSize.fill()           # Fill parent
node.height = UNSize.hug()           # Fit content
```

## MCP Connection Details

### Paper Design MCP

- **URL**: `http://127.0.0.1:29979/mcp`
- **Protocol**: HTTP SSE (JSON-RPC over Server-Sent Events)
- **Headers**: `Content-Type: application/json`, `Accept: application/json, text/event-stream`
- **Session**: Send `initialize`, capture `mcp-session-id` from response headers

```bash
# Test connection
curl -s -X POST http://127.0.0.1:29979/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
```

### Pencil.dev MCP

- **Binary**: `~/.cursor/extensions/highagency.pencildev-*/out/mcp-server-darwin-arm64`
- **Default**: stdio JSON-RPC
- **HTTP mode**: `mcp-server-darwin-arm64 --app desktop --http --http-port 19002`
- **Auto-detect**: PencilClient probes ports 19000-19009

### Figma

- **API**: REST API (`api.figma.com`) for reading
- **Writing**: Two modes:
  1. **Script mode** (default): Generates `.js` file to paste into Figma Plugin Console
  2. **Bridge mode**: WebSocket server (port 9224) for live connection via Desktop Bridge plugin

## Project Structure

```
services/design-converter/
    converter.py           # Main orchestrator + CLI
    ir/
        __init__.py        # Public exports
        nodes.py           # UNNode + all types + factories
    adapters/
        base.py            # BaseReader, BaseWriter, exceptions
        figma/
            __init__.py
            client.py      # Figma REST API client
            reader.py      # Figma -> UNNode
            writer.py      # UNNode -> Figma JS
        paper/
            __init__.py
            client.py      # Paper MCP HTTP client
            reader.py      # Paper -> UNNode
            writer.py      # UNNode -> Paper
        pencil/
            __init__.py
            client.py      # Pencil MCP HTTP client
            reader.py      # Pencil -> UNNode
            writer.py      # UNNode -> Pencil
    utils/
        __init__.py
        color.py           # Color utilities
        css.py             # CSS parsing/generation
        svg.py             # SVG path utilities
        tokens.py          # DTCG token extraction
    tests/
        test_ir_nodes.py
        test_figma_reader.py
        test_figma_writer.py
        test_bridge_server.py
        test_e2e.py
        test_tokens.py
    docs/
        UNNODE_DEEP_DIVE.md   # IR reference
        ANALYSIS_REPORT.md    # Implementation analysis
```

## Troubleshooting

### Connection Failures (Exit Code 2)

| Tool | Symptoms | Solution |
|------|----------|----------|
| **Paper** | `Connection refused` on port 29979 | Open Paper Design Desktop app |
| **Pencil** | No MCP server found on ports 19000-19009 | Open Pencil.dev extension in Cursor/VS Code |
| **Figma** | `401 Unauthorized` | Set `FIGMA_API_KEY` env var or pass `--figma-token` |

### Figma Writing

**Script Mode** generates a `.js` file:
1. Run converter with `--figma-writer-mode=script`
2. Open Figma file
3. Go to Plugins > Development > Console (or create a temporary plugin)
4. Paste the generated JavaScript and run

**Bridge Mode** requires the Desktop Bridge plugin:
1. Install the Desktop Bridge plugin in Figma
2. Run converter with `--figma-writer-mode=bridge`
3. Plugin connects to port 9224 automatically

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Node not found` | Invalid node ID | Use `--list` to see valid IDs |
| `Connection refused` | Tool not running | Open the design tool first |
| `Rate limited` | Figma API quota exceeded | Wait and retry (auto-retry built in) |
| `Invalid hex color` | Malformed color string | Use `#RRGGBB` or `#RRGGBBAA` format |

### Debug Mode

```bash
# Verbose output
python3 converter.py figma:ABC123 paper: --verbose

# JSON output for parsing
python3 converter.py figma:ABC123 paper: --json 2>/dev/null | jq '.'
```

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests (146 tests)
python3 -m pytest

# Run specific test file
python3 -m pytest tests/test_ir_nodes.py -v

# Run with coverage
python3 -m pytest --cov=. tests/
```

## Token Extraction

Extract W3C DTCG design tokens from any design:

```python
from utils.tokens import extract_tokens, export_tokens_json, tokens_to_css_vars

# Extract tokens from UNNode tree
tokens = extract_tokens(root)

# Export to JSON file
counts = export_tokens_json(root, "tokens.json")

# Generate CSS custom properties
css = tokens_to_css_vars(tokens)
```

Supported token types: color, typography, shadow, dimension.

## Documentation

- [UNNODE_DEEP_DIVE.md](docs/UNNODE_DEEP_DIVE.md) - IR field reference
- [ANALYSIS_REPORT.md](docs/ANALYSIS_REPORT.md) - Implementation analysis

## License

MIT
