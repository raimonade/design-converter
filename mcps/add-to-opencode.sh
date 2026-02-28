#!/bin/bash
# Quick add DesignDev MCPs to OpenCode config

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$HOME/.config/opencode/mcp-servers.json"

echo "🔧 Adding DesignDev MCPs to OpenCode..."
echo ""

# Create config directory if it doesn't exist
mkdir -p "$(dirname "$CONFIG_FILE")"

# Check if config already exists
if [ -f "$CONFIG_FILE" ]; then
    echo "Existing config found, backing up..."
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%s)"
fi

# Create the MCP config
cat > "$CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "figma-developer": {
      "command": "npx",
      "args": ["-y", "figma-developer-mcp"],
      "env": {
        "FIGMA_API_KEY": "figd_nw5LS6LoK7taqLFyvLcbXxe2KCtPtjj5KKhOr1mC"
      }
    },
    "figma-console": {
      "command": "npx",
      "args": ["-y", "southleft/figma-console-mcp"],
      "env": {
        "FIGMA_API_KEY": "figd_nw5LS6LoK7taqLFyvLcbXxe2KCtPtjj5KKhOr1mC"
      }
    },
    "claude-talk-to-figma": {
      "command": "npx",
      "args": ["-y", "arinspunk/claude-talk-to-figma-mcp"],
      "env": {
        "FIGMA_API_KEY": "figd_nw5LS6LoK7taqLFyvLcbXxe2KCtPtjj5KKhOr1mC"
      }
    }
  }
}
EOF

echo "✅ MCP config created at: $CONFIG_FILE"
echo ""
echo "Restart OpenCode to load the new MCPs."
echo ""
echo "To verify installation, run:"
echo "  npx -y figma-developer-mcp --help"
