#!/bin/bash
# ============================================================
# Figma Token Extraction Script
# Location: ~/.config/opencode/bin/figma-tokens.sh
# Purpose: Extract and convert Figma design tokens to code
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURATION
# ============================================================

OPENCODE_DIR="${HOME}/.config/opencode"
PRESET=""
EXPORT_FORMAT=""
INTERACTIVE=true
FIGMA_FILE_KEY=""
VERBOSE=false

# Exit codes
EXIT_SUCCESS=0
EXIT_ERROR=1
EXIT_NOT_CONNECTED=2

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Supported presets and formats
VALID_PRESETS=("shadcn" "tailwind" "raw" "custom")
VALID_FORMATS=("css" "scss" "json" "tailwind")

# ============================================================
# LOGGING
# ============================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "  ${CYAN}>${NC} $1"
    fi
}

# ============================================================
# ARGUMENT PARSING
# ============================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --preset=*)
                PRESET="${1#*=}"
                INTERACTIVE=false
                shift
                ;;
            --export=*)
                EXPORT_FORMAT="${1#*=}"
                INTERACTIVE=false
                shift
                ;;
            --file=*)
                FIGMA_FILE_KEY="${1#*=}"
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit $EXIT_SUCCESS
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit $EXIT_ERROR
                ;;
        esac
    done
}

show_help() {
    cat << 'HELPEOF'
Figma Token Extraction v1.0.0

Extract design tokens from Figma files and convert them to code-ready formats.

Usage: figma-tokens.sh [OPTIONS]

Options:
  --preset=NAME     Token preset: shadcn, tailwind, raw, custom
  --export=FORMAT   Export format: css, scss, json, tailwind
  --file=KEY        Figma file key (overrides MCP discovery)
  --verbose, -v     Show detailed output
  --help, -h        Show this help

Presets:
  shadcn      Extract tokens mapped to shadcn/ui CSS variables
  tailwind    Extract tokens mapped to Tailwind config values
  raw         Extract all tokens without transformation
  custom      Interactive token selection and mapping

Export Formats:
  css         CSS custom properties (:root { --color-primary: ... })
  scss        SCSS variables ($color-primary: ...)
  json        JSON token file (Design Tokens Community Group format)
  tailwind    Tailwind CSS config (theme.extend values)

Exit Codes:
  0  Success
  1  Error (invalid arguments, extraction failure)
  2  Not connected (Figma MCP unavailable)

Examples:
  figma-tokens.sh                              # Interactive mode
  figma-tokens.sh --preset=shadcn --export=css # Non-interactive
  figma-tokens.sh --preset=tailwind --export=tailwind --verbose
  figma-tokens.sh --preset=raw --export=json --file=abc123
HELPEOF
}

# ============================================================
# VALIDATION
# ============================================================

validate_preset() {
    local preset="$1"
    for valid in "${VALID_PRESETS[@]}"; do
        if [[ "$preset" == "$valid" ]]; then
            return 0
        fi
    done
    log_error "Invalid preset: $preset"
    log_info "Valid presets: ${VALID_PRESETS[*]}"
    return 1
}

validate_format() {
    local format="$1"
    for valid in "${VALID_FORMATS[@]}"; do
        if [[ "$format" == "$valid" ]]; then
            return 0
        fi
    done
    log_error "Invalid export format: $format"
    log_info "Valid formats: ${VALID_FORMATS[*]}"
    return 1
}

# ============================================================
# CONNECTION CHECK
# ============================================================

check_figma_connection() {
    log_info "Checking Figma MCP connection..."

    # Check if Composio/MCP Figma tool is available
    if command -v composio &>/dev/null; then
        log_verbose "Composio CLI found"
        if composio apps list 2>/dev/null | grep -qi "figma"; then
            log_success "Figma connection verified via Composio"
            return $EXIT_SUCCESS
        fi
    fi

    # Check for MCP server config referencing Figma
    local mcp_config="${HOME}/.claude.json"
    if [[ -f "$mcp_config" ]] && grep -qi "figma" "$mcp_config" 2>/dev/null; then
        log_success "Figma MCP server configured"
        return $EXIT_SUCCESS
    fi

    # Check alternative MCP config locations
    for config_path in "${HOME}/.config/claude/claude_desktop_config.json" "${HOME}/.cursor/mcp.json"; do
        if [[ -f "$config_path" ]] && grep -qi "figma" "$config_path" 2>/dev/null; then
            log_success "Figma MCP found in $config_path"
            return $EXIT_SUCCESS
        fi
    done

    log_error "Figma MCP connection not found"
    log_info "Configure Figma access via Composio or MCP server settings"
    return $EXIT_NOT_CONNECTED
}

# ============================================================
# INTERACTIVE MODE
# ============================================================

run_interactive() {
    echo ""
    echo "Figma Token Extraction - Interactive Mode"
    echo "=========================================="
    echo ""

    # Select preset
    echo "Select a token preset:"
    echo "  1) shadcn   - shadcn/ui CSS variable mapping"
    echo "  2) tailwind - Tailwind config value mapping"
    echo "  3) raw      - All tokens without transformation"
    echo "  4) custom   - Interactive token selection"
    echo ""
    read -rp "Preset [1-4]: " preset_choice

    case "$preset_choice" in
        1) PRESET="shadcn" ;;
        2) PRESET="tailwind" ;;
        3) PRESET="raw" ;;
        4) PRESET="custom" ;;
        *)
            log_error "Invalid choice: $preset_choice"
            exit $EXIT_ERROR
            ;;
    esac

    # Select export format
    echo ""
    echo "Select export format:"
    echo "  1) css      - CSS custom properties"
    echo "  2) scss     - SCSS variables"
    echo "  3) json     - JSON (DTCG format)"
    echo "  4) tailwind - Tailwind config"
    echo ""
    read -rp "Format [1-4]: " format_choice

    case "$format_choice" in
        1) EXPORT_FORMAT="css" ;;
        2) EXPORT_FORMAT="scss" ;;
        3) EXPORT_FORMAT="json" ;;
        4) EXPORT_FORMAT="tailwind" ;;
        *)
            log_error "Invalid choice: $format_choice"
            exit $EXIT_ERROR
            ;;
    esac

    echo ""
    log_info "Selected: preset=$PRESET, format=$EXPORT_FORMAT"
}

# ============================================================
# TOKEN EXTRACTION
# ============================================================

extract_tokens() {
    local preset="$1"
    local format="$2"

    log_info "Extracting tokens with preset=$preset, format=$format"
    log_verbose "This will invoke Figma MCP tools via the AI agent"

    echo ""
    echo "Token Extraction Plan"
    echo "---------------------"

    case "$preset" in
        shadcn)
            echo "  1. Read Figma variables (colors, spacing, radius, fonts)"
            echo "  2. Map to shadcn/ui CSS variable names (--background, --foreground, etc.)"
            echo "  3. Generate light + dark theme tokens"
            echo "  4. Export as $format"
            ;;
        tailwind)
            echo "  1. Read Figma variables (colors, spacing, typography)"
            echo "  2. Map to Tailwind theme keys (colors.*, spacing.*, fontSize.*)"
            echo "  3. Include DEFAULT + extended values"
            echo "  4. Export as $format"
            ;;
        raw)
            echo "  1. Read all Figma local variables and styles"
            echo "  2. Preserve original naming and hierarchy"
            echo "  3. Include metadata (scopes, descriptions)"
            echo "  4. Export as $format"
            ;;
        custom)
            echo "  1. List available Figma variable collections"
            echo "  2. Prompt for collection/group selection"
            echo "  3. Apply custom name mapping (if provided)"
            echo "  4. Export as $format"
            ;;
    esac

    echo ""
    echo "MCP Tool Calls Required:"
    echo "  - FIGMA_GET_FILE_STYLES: Retrieve design styles"
    echo "  - FIGMA_GET_LOCAL_VARIABLES: Retrieve variable collections"
    echo ""

    if [[ -n "$FIGMA_FILE_KEY" ]]; then
        log_info "Using file key: $FIGMA_FILE_KEY"
    else
        log_info "File key will be discovered from current project context"
    fi

    log_success "Token extraction plan ready"
    log_info "Execute this script from within an AI agent session to run MCP calls"
}

# ============================================================
# MAIN
# ============================================================

main() {
    parse_args "$@"

    echo "Figma Token Extraction v1.0.0"
    echo "=============================="

    # Check connection
    check_figma_connection || exit $?

    # Interactive or non-interactive mode
    if [[ "$INTERACTIVE" == true ]]; then
        run_interactive
    else
        # Validate provided arguments
        if [[ -n "$PRESET" ]]; then
            validate_preset "$PRESET" || exit $EXIT_ERROR
        else
            log_error "Non-interactive mode requires --preset"
            exit $EXIT_ERROR
        fi

        if [[ -n "$EXPORT_FORMAT" ]]; then
            validate_format "$EXPORT_FORMAT" || exit $EXIT_ERROR
        else
            log_error "Non-interactive mode requires --export"
            exit $EXIT_ERROR
        fi
    fi

    # Run extraction
    extract_tokens "$PRESET" "$EXPORT_FORMAT"

    exit $EXIT_SUCCESS
}

main "$@"
