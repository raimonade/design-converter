#!/bin/bash
# DesignDev Figma MCP Setup Script
# Installs and configures all Figma MCP tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCPS_DIR="$SCRIPT_DIR/mcps"
FIGMA_API_KEY="figd_nw5LS6LoK7taqLFyvLcbXxe2KCtPtjj5KKhOr1mC"

echo "🎨 DesignDev Figma MCP Setup"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js first."
    exit 1
fi

print_status "Node.js version: $(node --version)"
echo ""

# Install Official Figma MCP
echo "Installing Official Figma MCP..."
cd "$MCPS_DIR"
if [ ! -d "official" ]; then
    git clone https://github.com/figma/mcp-server.git official
    cd official
    npm install --silent
    print_status "Official Figma MCP installed"
else
    cd official
    npm install --silent
    print_status "Official Figma MCP already exists, updated"
fi
echo ""

# Install figma-console MCP (NPX - Local Mode)
print_status "figma-console MCP available via NPX: southleft/figma-console-mcp"
echo ""

# Install claude-talk-to-figma MCP (NPX - Local Mode)
print_status "claude-talk-to-figma MCP available via NPX: arinspunk/claude-talk-to-figma-mcp"
echo ""

# Create Desktop Bridge Plugin setup
echo "Setting up Desktop Bridge Plugin..."
PLUGIN_DIR="$MCPS_DIR/desktop-bridge"
if [ ! -d "$PLUGIN_DIR" ]; then
    mkdir -p "$PLUGIN_DIR"
    print_status "Desktop Bridge Plugin directory created"
else
    print_status "Desktop Bridge Plugin directory exists"
fi
echo ""

# Copy API key to .env file
echo "Configuring API key..."
ENV_FILE="$SCRIPT_DIR/.env"
cat > "$ENV_FILE" << EOF
# DesignDev Figma MCP Configuration
FIGMA_API_KEY=$FIGMA_API_KEY_status "API key
EOF
print saved to .env"
echo ""

# Summary
echo "=============================="
echo "🎉 Setup Complete!"
echo ""
echo "Available MCPs:"
echo "  1. Official Figma MCP    - Read-only, Dev Mode integration"
echo "  2. figma-console         - 56+ tools, FULL CRUD (requires Desktop Bridge)"
echo "  3. claude-talk-to-figma  - Claude-first, accessibility features"
echo ""
echo "To use with OpenCode, add this to your MCP config:"
echo ""
cat "$MCPS_DIR/mcp-config.json"
echo ""
echo "For Desktop Bridge Plugin instructions, see:"
echo "  $MCPS_DIR/figma-console/docs/desktop-bridge.md"
