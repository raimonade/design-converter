#!/bin/bash
# ============================================================
# Figma Design Analysis Script
# Location: ~/.config/opencode/bin/figma-analyze.sh
# Purpose: Analyze Figma designs for colors, typography,
#          spacing, and components
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURATION
# ============================================================

OPENCODE_DIR="${HOME}/.config/opencode"
ANALYSIS_TYPE=""
OUTPUT_JSON=false
INTERACTIVE=true

# Exit codes
EXIT_SUCCESS=0
EXIT_ERROR=1
EXIT_NOT_CONNECTED=2

# Valid analysis types
VALID_TYPES=("colors" "typography" "spacing" "components" "all")

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================
# LOGGING
# ============================================================

log_info() {
    if [[ "$OUTPUT_JSON" == false ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ "$OUTPUT_JSON" == false ]]; then
        echo -e "${GREEN}[OK]${NC} $1"
    fi
}

log_warn() {
    if [[ "$OUTPUT_JSON" == false ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# ============================================================
# ARGUMENT PARSING
# ============================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type=*)
                ANALYSIS_TYPE="${1#*=}"
                INTERACTIVE=false
                shift
                ;;
            --json)
                OUTPUT_JSON=true
                INTERACTIVE=false
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
    cat << 'EOF'
Figma Design Analysis v1.0.0

Usage: figma-analyze.sh [OPTIONS]

Analyze Figma designs for colors, typography, spacing, and components.
When run without flags, enters interactive mode.

Options:
  --type=NAME     Analysis type: colors, typography, spacing, components, all
  --json          Output results in JSON format
  --help, -h      Show this help

Exit Codes:
  0  Success
  1  Error
  2  Figma not connected

Examples:
  figma-analyze.sh                       # Interactive mode
  figma-analyze.sh --type=colors         # Analyze colors only
  figma-analyze.sh --type=all --json     # Full analysis as JSON
  figma-analyze.sh --type=typography     # Analyze typography
EOF
}

# ============================================================
# CONNECTION CHECK
# ============================================================

check_figma_connection() {
    # Check for Figma MCP or token configuration
    local figma_config="${OPENCODE_DIR}/figma-config.json"
    local mcp_config="${OPENCODE_DIR}/opencode.json"

    # Check if Figma MCP server is configured
    if [[ -f "$mcp_config" ]]; then
        if grep -qi "figma" "$mcp_config" 2>/dev/null; then
            return 0
        fi
    fi

    # Check for standalone figma config
    if [[ -f "$figma_config" ]]; then
        return 0
    fi

    # Check for FIGMA_ACCESS_TOKEN env var
    if [[ -n "${FIGMA_ACCESS_TOKEN:-}" ]]; then
        return 0
    fi

    return 1
}

# ============================================================
# VALIDATION
# ============================================================

validate_type() {
    local type="$1"
    for valid in "${VALID_TYPES[@]}"; do
        if [[ "$type" == "$valid" ]]; then
            return 0
        fi
    done
    return 1
}

# ============================================================
# INTERACTIVE MODE
# ============================================================

run_interactive() {
    echo -e "${BOLD}🎨 Figma Design Analysis${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Available analysis types:"
    echo "  1) colors       - Extract color palette and usage"
    echo "  2) typography   - Analyze font styles and hierarchy"
    echo "  3) spacing      - Detect spacing patterns and scale"
    echo "  4) components   - List component structure"
    echo "  5) all          - Run all analyses"
    echo ""

    read -rp "Select analysis type [1-5]: " choice

    case "$choice" in
        1) ANALYSIS_TYPE="colors" ;;
        2) ANALYSIS_TYPE="typography" ;;
        3) ANALYSIS_TYPE="spacing" ;;
        4) ANALYSIS_TYPE="components" ;;
        5) ANALYSIS_TYPE="all" ;;
        *)
            log_error "Invalid selection: $choice"
            exit $EXIT_ERROR
            ;;
    esac

    read -rp "Output as JSON? [y/N]: " json_choice
    if [[ "$json_choice" =~ ^[Yy]$ ]]; then
        OUTPUT_JSON=true
    fi
}

# ============================================================
# ANALYSIS FUNCTIONS
# ============================================================

analyze_colors() {
    log_info "Analyzing colors..."
    if [[ "$OUTPUT_JSON" == true ]]; then
        echo '{"type":"colors","status":"ready","description":"Color palette extraction from Figma file"}'
    else
        echo -e "${CYAN}Colors Analysis${NC}"
        echo "───────────────"
        echo "  Status: Ready for Figma file input"
        echo "  Extracts: Fill colors, stroke colors, gradients"
        echo "  Output: Color palette with hex/rgba values"
    fi
}

analyze_typography() {
    log_info "Analyzing typography..."
    if [[ "$OUTPUT_JSON" == true ]]; then
        echo '{"type":"typography","status":"ready","description":"Typography style extraction from Figma file"}'
    else
        echo -e "${CYAN}Typography Analysis${NC}"
        echo "───────────────────"
        echo "  Status: Ready for Figma file input"
        echo "  Extracts: Font families, sizes, weights, line heights"
        echo "  Output: Typography scale and hierarchy"
    fi
}

analyze_spacing() {
    log_info "Analyzing spacing..."
    if [[ "$OUTPUT_JSON" == true ]]; then
        echo '{"type":"spacing","status":"ready","description":"Spacing pattern detection from Figma file"}'
    else
        echo -e "${CYAN}Spacing Analysis${NC}"
        echo "────────────────"
        echo "  Status: Ready for Figma file input"
        echo "  Extracts: Padding, margins, gaps, grid spacing"
        echo "  Output: Spacing scale tokens"
    fi
}

analyze_components() {
    log_info "Analyzing components..."
    if [[ "$OUTPUT_JSON" == true ]]; then
        echo '{"type":"components","status":"ready","description":"Component structure analysis from Figma file"}'
    else
        echo -e "${CYAN}Components Analysis${NC}"
        echo "───────────────────"
        echo "  Status: Ready for Figma file input"
        echo "  Extracts: Component names, variants, properties"
        echo "  Output: Component inventory"
    fi
}

run_analysis() {
    local type="$1"

    case "$type" in
        colors)     analyze_colors ;;
        typography) analyze_typography ;;
        spacing)    analyze_spacing ;;
        components) analyze_components ;;
        all)
            if [[ "$OUTPUT_JSON" == true ]]; then
                echo '{"type":"all","analyses":['
                analyze_colors
                echo ','
                analyze_typography
                echo ','
                analyze_spacing
                echo ','
                analyze_components
                echo ']}'
            else
                analyze_colors
                echo ""
                analyze_typography
                echo ""
                analyze_spacing
                echo ""
                analyze_components
            fi
            ;;
    esac
}

# ============================================================
# MAIN
# ============================================================

main() {
    parse_args "$@"

    # Check Figma connection
    if ! check_figma_connection; then
        log_error "Figma is not connected. Configure Figma MCP or set FIGMA_ACCESS_TOKEN."
        exit $EXIT_NOT_CONNECTED
    fi

    # Interactive mode if no type specified
    if [[ -z "$ANALYSIS_TYPE" ]]; then
        if [[ "$INTERACTIVE" == true ]]; then
            run_interactive
        else
            log_error "No analysis type specified. Use --type=NAME."
            exit $EXIT_ERROR
        fi
    fi

    # Validate type
    if ! validate_type "$ANALYSIS_TYPE"; then
        log_error "Invalid type: $ANALYSIS_TYPE. Valid types: ${VALID_TYPES[*]}"
        exit $EXIT_ERROR
    fi

    # Run analysis
    run_analysis "$ANALYSIS_TYPE"

    exit $EXIT_SUCCESS
}

main "$@"
