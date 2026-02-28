# Official Figma MCP Server

## Overview

Official Figma MCP server from Figma's official team. Provides core Figma file access with Dev Mode integration.

## Repository

**GitHub**: https://github.com/figma/mcp-server-guide

## Features

- **File Access**: Read Figma files, pages, frames, components
- **Dev Mode Integration**: Access code connect, specifications
- **Style Extraction**: Colors, typography, effects
- **Component Information**: Get component details and variants

## Limitations (vs Local Mode)

- Remote SSE mode only: ~12 tools
- Read-only operations
- Variables API requires Enterprise plan

## Installation

```bash
# Clone the repository
cd /Users/william/Projects\ Parent\ Folder/DesignDev/mcps/
git clone https://github.com/figma/mcp-server.git official
cd official
npm install
```

## Configuration

### Option 1: Environment Variable (Recommended)

Add to your MCP config:

```json
{
  "figma": {
    "command": "npx",
    "args": ["-y", "@figma/mcp-server"],
    "env": {
      "FIGMA_API_KEY": "figd_nw5LS6LoK7taqLFyvLcbXxe2KCtPtjj5KKhOr1mC"
    }
  }
}
```

### Option 2: Direct Path

```json
{
  "figma": {
    "command": "/Users/william/Projects Parent Folder/DesignDev/mcps/official/bin/figma-mcp-server",
    "env": {
      "FIGMA_API_KEY": "figd_nw5LS6LoK7taqLFyvLcbXxe2KCtPtjj5KKhOr1mC"
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_file` | Get full Figma file structure |
| `get_file_nodes` | Get specific nodes by ID |
| `get_images` | Export nodes as images |
| `get_styles` | Get all styles in file |
| `get_components` | Get all components |
| `get_team_components` | Get team library components |

## Usage Notes

- Works with Figma Professional plan
- Rate limited by Figma API (per-minute limits)
- Best for: Reading file structure, extracting styles, component info
- Not for: Creating/modifying files (use figma-console for that)
