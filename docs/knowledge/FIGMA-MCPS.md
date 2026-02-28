# FIGMA-MCPS.md - Figma MCP Integration Guide

> **DesignDev MCP Suite** - Maximum Fidelity + Full Potential
> 
> This workspace integrates the most powerful Figma MCP tools for complete AI ↔ Figma workflows.

---

## Philosophy

We prioritize **capability over popularity**. Our goal: Give AI agents FULL access to everything in Figma - read, write, study, create, debug.

| Tool | Capability | Tools | Why |
|------|-----------|-------|-----|
| **figma-console** | FULL CRUD | 56+ | Variables, creation, debugging, docs |
| **claude-talk-to-figma** | Full R/W | ~40 | Accessibility, Claude-optimized |
| **Official Figma MCP** | Read + Code Gen | ~12 | Code Connect (unique) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DesignDev MCP Suite                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              LOCAL MODE (RECOMMENDED)                │   │
│  │   NPX → Local MCP → WebSocket → Desktop Bridge    │   │
│  │   ✅ 56+ tools  ✅ Full CRUD  ✅ Variables FREE   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              REMOTE MODE (OPTIONAL)                  │   │
│  │   OAuth → Cloudflare → Figma API                  │   │
│  │   ⚠️ 21 tools only  ⚠️ Read-only                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP Comparison

### figma-console (Primary - Maximum Capability)

**Stars:** 691 | **Focus:** Full-stack design operations

| Aspect | Details |
|--------|---------|
| **Mode** | Local (NPX/Git) - RECOMMENDED |
| **Tools** | 56+ |
| **Variables** | Full CRUD (no Enterprise needed!) |
| **Design Creation** | ✅ Full |
| **Console Debugging** | ✅ Real-time |
| **Design-Code Parity** | ✅ |
| **Documentation** | ✅ Auto-generate |

**Install:**
```bash
# NPX (recommended)
npx -y figma-console-mcp@latest

 clone# Or for development
git clone https://github.com/southleft/figma-console-mcp.git
```

**Desktop Bridge Plugin Required:**
1. Open Figma Desktop
2. Plugins → Development → Import plugin from manifest
3. Select `figma-desktop-bridge/manifest.json`

**Configuration:**
```json
{
  "mcpServers": {
    "figma-console": {
      "command": "npx",
      "args": ["-y", "figma-console-mcp@latest"],
      "env": {
        "FIGMA_ACCESS_TOKEN": "figd_YOUR_TOKEN",
        "ENABLE_MCP_APPS": "true"
      }
    }
  }
}
```

---

### claude-talk-to-figma (Secondary - Claude Optimization)

**Stars:** 433 | **Focus:** Claude-first + Accessibility

| Aspect | Details |
|--------|---------|
| **Mode** | Local |
| **Tools** | ~40 |
| **Unique Features** | Accessibility audits, bulk updates |
| **Figma Account** | Works with FREE accounts! |

**Install:**
```bash
git clone https://github.com/arinspunk/claude-talk-to-figma-mcp.git
cd claude-talk-to-figma-mcp
npm install
```

**Start WebSocket Server:**
```bash
bun run socket  # or npm run socket
```

**Install Figma Plugin:**
1. Plugins → Development → Import from manifest
2. Select `src/claude_mcp_plugin/manifest.json`

**Connect:**
```
Connect to Figma, channel {channel-ID}
```

---

### Official Figma MCP (Optional - Code Connect)

**Stars:** 288 | **Focus:** Code generation + Code Connect

| Aspect | Details |
|--------|---------|
| **Mode** | Remote (no setup) |
| **Tools** | ~12 |
| **Unique Features** | Code Connect, web→Figma, FigJam |
| **Requirement** | Figma Professional + Dev Mode |

**Install (Remote - No Setup):**
```bash
# Claude Code
claude mcp add --transport http figma https://mcp.figma.com/mcp

# VS Code
{
  "servers": {
    "figma": {
      "type": "http",
      "url": "https://mcp.figma.com/mcp"
    }
  }
}
```

**Install (Cursor):**
```
/plugin-add figma
```

---

## Mode Comparison

### Local Mode (NPX) - RECOMMENDED

```
Claude → Local MCP → WebSocket → Desktop Bridge Plugin → Figma
```

| Feature | Local Mode |
|---------|-----------|
| Tool Count | 56+ |
| Create Designs | ✅ |
| Variables | ✅ Free (no Enterprise!) |
| Console Debugging | ✅ Real-time |
| Component Descriptions | ✅ Reliable |
| Setup Complexity | ⚠️ Token + Plugin |

### Remote Mode (SSE)

```
Claude → Cloudflare Workers → Figma API
```

| Feature | Remote Mode |
|---------|-----------|
| Tool Count | 21 |
| Create Designs | ❌ |
| Variables | ❌ Enterprise only |
| Console Debugging | ⚠️ Limited |
| Component Descriptions | ⚠️ Buggy |
| Setup Complexity | ✅ Zero |

---

## Tool Categories (figma-console - 56 Tools)

### Navigation & Status (2)
- `figma_navigate` - Open Figma URLs
- `figma_get_status` - Check connection

### Console Debugging (4)
- `figma_get_console_logs` - Retrieve logs
- `figma_watch_console` - Real-time streaming
- `figma_clear_console` - Clear buffer
- `figma_reload_plugin` - Reload page

### Visual Debugging (1)
- `figma_take_screenshot` - Capture UI

### Design System Extraction (7)
- `figma_get_variables` - Design tokens
- `figma_get_component` - Component data
- `figma_get_component_for_development` - + image
- `figma_get_component_image` - Just image
- `figma_get_styles` - Color/text/effect styles
- `figma_get_file_data` - Full structure
- `figma_get_file_for_plugin` - Optimized

### Design Creation (3)
- `figma_execute` - **Power tool**: Run any Figma API code
- `figma_arrange_component_set` - Organize variants
- `figma_set_description` - Document components

### Variable Management (11)
- `figma_create_variable_collection`
- `figma_create_variable`
- `figma_update_variable`
- `figma_rename_variable`
- `figma_delete_variable`
- `figma_delete_variable_collection`
- `figma_add_mode`
- `figma_rename_mode`
- `figma_batch_create_variables`
- `figma_batch_update_variables`
- `figma_setup_design_tokens`

### Component Management (6)
- `figma_search_components`
- `figma_get_component_details`
- `figma_instantiate_component`
- `figma_set_instance_properties`
- `figma_get_design_system_summary`
- `figma_generate_component_doc`

### Variable & Mode (5)
- `figma_get_variables`
- `figma_browse_tokens`
- `figma_batch_create_variables`
- `figma_batch_update_variables`
- `figma_setup_design_tokens`

---

## Setup Instructions

### Step 1: Get Figma Token

1. Go to [Manage personal access tokens](https://help.figma.com/hc/en-us/articles/8085703771159-Manage-personal-access-tokens)
2. Create new token: `figma-console-mcp`
3. Copy token (starts with `figd_`)

### Step 2: Install Desktop Bridge Plugin

```bash
# Clone figma-console
git clone https://github.com/southleft/figma-console-mcp.git

# The plugin is at:
# figma-console-mcp/figma-desktop-bridge/manifest.json
```

In Figma Desktop:
1. Plugins → Development → Import plugin from manifest
2. Select the manifest.json

### Step 3: Configure MCP

Add to your MCP config:

```json
{
  "mcpServers": {
    "figma-console": {
      "command": "npx",
      "args": ["-y", "figma-console-mcp@latest"],
      "env": {
        "FIGMA_ACCESS_TOKEN": "figd_YOUR_TOKEN"
      }
    }
  }
}
```

### Step 4: Test Connection

```bash
# In your AI client:
Check Figma status
```

Should show: Connection status with active WebSocket transport

---

## Usage Examples

### Read Figma Data
```
Get design variables from https://figma.com/design/abc123
Extract color styles and show CSS exports
Get the Button component with visual reference
```

### Create Designs
```
Create a success notification card with checkmark icon
Design a button component with hover states
Build a navigation bar with logo and menu
```

### Manage Variables
```
Create a color collection "Brand Colors" with Light/Dark modes
Add primary color variable #3B82F6 for Light, #60A5FA for Dark
Rename "Default" mode to "Light Theme"
```

### Debug
```
Show me console errors from my plugin
Take screenshot of current canvas
Watch console for 30 seconds
```

---

## Troubleshooting

### "Failed to connect to Figma Desktop"
- Install Desktop Bridge Plugin
- Run the plugin in your Figma file

### "Variables cache empty"
- Close and reopen Desktop Bridge plugin

### "No plugin UI found"
- Make sure Desktop Bridge is running in your file

---

## Alternative: Remote Mode (Limited)

If you just need read-only access:

```bash
# Add to MCP config:
{
  "mcpServers": {
    "figma-remote": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://figma-console-mcp.southleft.com/sse"]
    }
  }
}
```

⚠️ **Warning:** Only 21 tools available, cannot create designs.

---

## Resources

- [figma-console-mcp GitHub](https://github.com/southleft/figma-console-mcp)
- [claude-talk-to-figma-mcp GitHub](https://github.com/arinspunk/claude-talk-to-figma-mcp)
- [Official Figma MCP Guide](https://github.com/figma/mcp-server-guide)
- [Mode Comparison](https://github.com/southleft/figma-console-mcp/blob/main/docs/mode-comparison.md)

---

## Version

**DesignDev MCP Suite v1.0.0**
- Created: 2026-02-28
- Focus: Maximum capability for AI ↔ Figma workflows
