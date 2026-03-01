#!/usr/bin/env bash
# ============================================================================
# design-convert.sh — Convert designs between Figma, Paper Design, and Pencil
# ============================================================================
# Usage:
#   design-convert.sh SOURCE DEST [OPTIONS]
#   design-convert.sh --list SOURCE [OPTIONS]
#   design-convert.sh --info SOURCE [OPTIONS]
#
# Examples:
#   design-convert.sh figma:ABC123 paper:
#   design-convert.sh figma:ABC123/1:2 pencil: --dry-run --verbose
#   design-convert.sh paper:TO-0 figma: --figma-mode=script
#   design-convert.sh --list figma:ABC123 --json
#   design-convert.sh --info paper:
#   design-convert.sh  (interactive mode)

set -euo pipefail

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve: cli/bin/ → ../../services/design-converter
if command -v realpath &>/dev/null; then
    SVC_ROOT="$(realpath "${SCRIPT_DIR}/../../services/design-converter")"
else
    SVC_ROOT="${SCRIPT_DIR}/../../services/design-converter"
fi
CONVERTER="${SVC_ROOT}/converter.py"

# ── colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── exit codes ────────────────────────────────────────────────────────────────
EXIT_SUCCESS=0
EXIT_ERROR=1
EXIT_NOT_CONNECTED=2

# ── defaults ──────────────────────────────────────────────────────────────────
INTERACTIVE=true
SOURCE=""
DEST=""
LIST_MODE=false
INFO_MODE=false
DRY_RUN=false
OUTPUT_JSON=false
VERBOSE=false
PARENT_ID=""
REPLACE_ID=""
FIGMA_WRITER_MODE="script"
BRIDGE_PORT="9224"
HTTP_BRIDGE_PORT="9223"
FIGMA_TOKEN=""
OUTPUT_DIR=""

# ── logging ───────────────────────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_verbose() { [[ "$VERBOSE" == true ]] && echo -e "  ${CYAN}›${NC} $1" || true; }

# ── help ──────────────────────────────────────────────────────────────────────
show_help() {
    cat <<'HELPEOF'

design-convert.sh — Convert designs between Figma, Paper Design, and Pencil

USAGE
  design-convert.sh SOURCE DEST [OPTIONS]
  design-convert.sh --list SOURCE [OPTIONS]
  design-convert.sh --info SOURCE [OPTIONS]
  design-convert.sh                         (interactive mode)

SPEC FORMAT
  figma:FILE_KEY                whole Figma file
  figma:FILE_KEY/NODE_ID        specific Figma node
  https://www.figma.com/...     Figma URL (auto-detected)
  paper:                        first Paper artboard
  paper:NODE_ID                 specific Paper node (e.g. paper:TO-0)
  pencil:                       active Pencil file
  pencil:NODE_ID                specific Pencil node

OPTIONS
  --list              List nodes in SOURCE (no conversion)
  --info              Show file/document info for SOURCE
  --parent-id=ID      Parent node ID in destination
  --replace-id=ID     Replace existing destination node
  --dry-run           Read source only; do not write
  --json              Machine-readable JSON output
  --verbose, -v       Print detailed progress
  --figma-mode=MODE   FigmaWriter mode: script|bridge|http  (default: script)
                        script — saves a .js file to paste into Figma Console
                        bridge — starts WebSocket server for Desktop Bridge plugin
                        http   — uses HTTP bridge server (requires figma-bridge-server)
  --bridge-port=N     WebSocket bridge port (default: 9224)
  --http-bridge-port=N HTTP bridge port for http mode (default: 9223)
  --figma-token=TOK   Figma API token (overrides FIGMA_API_KEY env var)
  --output-dir=DIR    Directory for script-mode .js files (default: CWD)
  --help, -h          Show this help

EXAMPLES
  # Figma file → Paper Design (interactive placement)
  design-convert.sh figma:ABC123xyz paper:

  # Specific Figma node → Pencil, dry-run with verbose output
  design-convert.sh figma:ABC123xyz/1:2 pencil: --dry-run --verbose

  # Paper artboard → Figma (generates .js script)
  design-convert.sh paper:TO-0 figma: --figma-mode=script

  # List all artboards in a Paper Design file
  design-convert.sh --list paper: --json

  # Info about a Figma file
  design-convert.sh --info figma:ABC123xyz

EXIT CODES
  0   Success
  1   Error (bad arguments, conversion failure)
  2   Connection failure (tool not running or not reachable)

CONNECTION SETUP
  Paper Design  : Paper.app must be running (MCP on port 29979)
  Pencil.dev    : Pencil.app must be running (MCP auto-detected on 19000-19009)
  Figma         : Set FIGMA_API_KEY env var or use --figma-token

HELPEOF
}

# ── argument parsing ───────────────────────────────────────────────────────────
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit $EXIT_SUCCESS
                ;;
            --list|-l)
                LIST_MODE=true
                INTERACTIVE=false
                shift
                ;;
            --info|-i)
                INFO_MODE=true
                INTERACTIVE=false
                shift
                ;;
            --source=*)
                SOURCE="${1#*=}"
                INTERACTIVE=false
                shift
                ;;
            --dest=*)
                DEST="${1#*=}"
                INTERACTIVE=false
                shift
                ;;
            --parent-id=*)
                PARENT_ID="${1#*=}"
                shift
                ;;
            --replace-id=*)
                REPLACE_ID="${1#*=}"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                INTERACTIVE=false
                shift
                ;;
            --json)
                OUTPUT_JSON=true
                INTERACTIVE=false
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --figma-mode=*)
                FIGMA_WRITER_MODE="${1#*=}"
                shift
                ;;
            --bridge-port=*)
                BRIDGE_PORT="${1#*=}"
                shift
                ;;
            --http-bridge-port=*)
                HTTP_BRIDGE_PORT="${1#*=}"
                shift
                ;;
            --figma-token=*)
                FIGMA_TOKEN="${1#*=}"
                shift
                ;;
            --output-dir=*)
                OUTPUT_DIR="${1#*=}"
                shift
                ;;
            -*)
                log_error "Unknown option: $1"
                echo "Use --help for usage information." >&2
                exit $EXIT_ERROR
                ;;
            *)
                # Positional: first non-option = SOURCE, second = DEST
                if [[ -z "$SOURCE" ]]; then
                    SOURCE="$1"
                    INTERACTIVE=false
                elif [[ -z "$DEST" ]]; then
                    DEST="$1"
                else
                    log_error "Unexpected argument: $1"
                    exit $EXIT_ERROR
                fi
                shift
                ;;
        esac
    done
}

# ── validation ────────────────────────────────────────────────────────────────
check_python() {
    if ! command -v python3 &>/dev/null; then
        log_error "python3 not found. Please install Python 3.8 or later."
        exit $EXIT_ERROR
    fi

    local ver
    ver="$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 0)"
    if [[ "$ver" -lt 8 ]]; then
        local full_ver
        full_ver="$(python3 --version 2>&1)"
        log_error "Python 3.8+ required. Found: ${full_ver}"
        exit $EXIT_ERROR
    fi
    log_verbose "python3 $(python3 --version 2>&1 | awk '{print $2}')"
}

check_converter() {
    if [[ ! -f "$CONVERTER" ]]; then
        log_error "converter.py not found at: ${CONVERTER}"
        log_error "Repository may be incomplete. Expected: services/design-converter/converter.py"
        exit $EXIT_ERROR
    fi
    log_verbose "converter.py found at ${CONVERTER}"
}

validate_figma_mode() {
    case "$FIGMA_WRITER_MODE" in
        script|bridge|http) ;;
        *)
            log_error "Invalid --figma-mode value: '${FIGMA_WRITER_MODE}'"
            log_error "Valid values: script, bridge, http"
            exit $EXIT_ERROR
            ;;
    esac
}

# ── interactive mode ──────────────────────────────────────────────────────────
run_interactive() {
    echo ""
    echo -e "${BOLD}Design Converter — Interactive Mode${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Action selection.
    echo -e "${CYAN}What would you like to do?${NC}"
    echo "  1) Convert between tools"
    echo "  2) List nodes in a source"
    echo "  3) Get info about a source"
    echo ""
    read -rp "Action [1-3]: " action_choice

    case "$action_choice" in
        2) LIST_MODE=true ;;
        3) INFO_MODE=true ;;
        1|"") ;;
        *)
            log_error "Invalid choice: $action_choice"
            exit $EXIT_ERROR
            ;;
    esac

    # Source tool.
    echo ""
    echo -e "${CYAN}Source tool:${NC}"
    echo "  1) Figma"
    echo "  2) Paper Design"
    echo "  3) Pencil.dev"
    echo ""
    read -rp "Source [1-3]: " src_tool_choice

    local src_tool
    case "$src_tool_choice" in
        1) src_tool="figma" ;;
        2) src_tool="paper" ;;
        3) src_tool="pencil" ;;
        *)
            log_error "Invalid choice: $src_tool_choice"
            exit $EXIT_ERROR
            ;;
    esac

    # Source ID / URL.
    if [[ "$src_tool" == "figma" ]]; then
        echo ""
        read -rp "Figma file key or URL (blank = use FIGMA_FILE_KEY env): " figma_input
        local figma_val="${figma_input:-${FIGMA_FILE_KEY:-}}"
        if [[ -z "$figma_val" ]]; then
            log_error "No Figma file key provided."
            exit $EXIT_ERROR
        fi
        # If it looks like a URL, use it directly; otherwise wrap it.
        if [[ "$figma_val" == http* ]]; then
            SOURCE="$figma_val"
        else
            read -rp "Figma node ID (blank = entire file): " figma_node
            if [[ -n "$figma_node" ]]; then
                SOURCE="figma:${figma_val}/${figma_node}"
            else
                SOURCE="figma:${figma_val}"
            fi
        fi
    else
        echo ""
        read -rp "${src_tool^} node ID (blank = first artboard): " src_id
        SOURCE="${src_tool}:${src_id}"
    fi

    log_verbose "Source spec: $SOURCE"

    # Destination (not needed for --list / --info).
    if [[ "$LIST_MODE" == false && "$INFO_MODE" == false ]]; then
        echo ""
        echo -e "${CYAN}Destination tool:${NC}"
        echo "  1) Figma"
        echo "  2) Paper Design"
        echo "  3) Pencil.dev"
        echo ""
        read -rp "Destination [1-3]: " dst_tool_choice

        local dst_tool
        case "$dst_tool_choice" in
            1) dst_tool="figma" ;;
            2) dst_tool="paper" ;;
            3) dst_tool="pencil" ;;
            *)
                log_error "Invalid choice: $dst_tool_choice"
                exit $EXIT_ERROR
                ;;
        esac

        read -rp "Destination node ID (blank = root/first artboard): " dst_id
        DEST="${dst_tool}:${dst_id}"
        log_verbose "Destination spec: $DEST"

        # Options.
        echo ""
        read -rp "Dry-run only (don't write)? [y/N]: " dry
        [[ "$dry" =~ ^[Yy]$ ]] && DRY_RUN=true

        if [[ "$dst_tool" == "figma" ]]; then
            echo ""
            echo "Figma writer mode:"
            echo "  1) script — save .js file to paste into Figma Console"
            echo "  2) bridge — execute live via Desktop Bridge plugin"
            read -rp "Mode [1-2, default=1]: " figma_mode_choice
            case "$figma_mode_choice" in
                2) FIGMA_WRITER_MODE="bridge" ;;
                *) FIGMA_WRITER_MODE="script" ;;
            esac
        fi
    fi

    echo ""
    read -rp "JSON output? [y/N]: " json_choice
    [[ "$json_choice" =~ ^[Yy]$ ]] && OUTPUT_JSON=true

    echo ""
}

# ── connection guidance ───────────────────────────────────────────────────────
print_connection_guide() {
    local tool="${1:-}"
    echo ""
    echo -e "${YELLOW}Connection Guide${NC}"
    echo "────────────────"
    case "$tool" in
        *paper*)
            echo "  Paper Design MCP:"
            echo "    • Make sure Paper.app is running"
            echo "    • MCP listens on http://127.0.0.1:29979"
            ;;
        *pencil*)
            echo "  Pencil.dev MCP:"
            echo "    • Make sure Pencil.app is running"
            echo "    • MCP auto-detected on ports 19000–19009"
            ;;
        *figma*)
            echo "  Figma:"
            echo "    • Set FIGMA_API_KEY env var  (or use --figma-token)"
            echo "    • For bridge mode: Desktop Bridge plugin must be running in Figma"
            ;;
        *)
            echo "  Paper Design  : Paper.app must be running (MCP on port 29979)"
            echo "  Pencil.dev    : Pencil.app must be running (MCP auto-detected)"
            echo "  Figma         : Set FIGMA_API_KEY env var"
            ;;
    esac
    echo ""
}

# ── converter invocation ──────────────────────────────────────────────────────
run_converter() {
    local py_args=("$CONVERTER")

    # Modes.
    [[ "$LIST_MODE"   == true ]] && py_args+=("--list")
    [[ "$INFO_MODE"   == true ]] && py_args+=("--info")

    # Positionals.
    [[ -n "$SOURCE" ]] && py_args+=("$SOURCE")
    [[ -n "$DEST"   ]] && py_args+=("$DEST")

    # Options.
    [[ "$DRY_RUN"    == true ]] && py_args+=("--dry-run")
    [[ "$OUTPUT_JSON" == true ]] && py_args+=("--json")
    [[ "$VERBOSE"    == true ]] && py_args+=("--verbose")
    [[ -n "$PARENT_ID"  ]] && py_args+=("--parent-id=$PARENT_ID")
    [[ -n "$REPLACE_ID" ]] && py_args+=("--replace-id=$REPLACE_ID")
    [[ -n "$FIGMA_TOKEN"  ]] && py_args+=("--figma-token=$FIGMA_TOKEN")
    [[ -n "$OUTPUT_DIR"   ]] && py_args+=("--output-dir=$OUTPUT_DIR")
    py_args+=("--figma-writer-mode=$FIGMA_WRITER_MODE")
    py_args+=("--bridge-port=$BRIDGE_PORT")
    py_args+=("--http-bridge-port=$HTTP_BRIDGE_PORT")

    log_verbose "Running: PYTHONPATH=${SVC_ROOT} python3 ${py_args[*]}"

    local exit_code=0
    PYTHONPATH="$SVC_ROOT" python3 "${py_args[@]}" || exit_code=$?

    if [[ "$exit_code" -eq $EXIT_NOT_CONNECTED ]]; then
        # Suggest which tool needs attention.
        local affected=""
        [[ -n "$SOURCE" ]] && affected="$SOURCE"
        [[ -n "$DEST"   ]] && affected="${affected} ${DEST}"
        print_connection_guide "$affected"
    fi

    return "$exit_code"
}

# ── main ──────────────────────────────────────────────────────────────────────
main() {
    parse_args "$@"

    # Validation (always).
    check_python
    check_converter
    validate_figma_mode

    # Interactive mode when no source given.
    if [[ "$INTERACTIVE" == true ]]; then
        run_interactive
    fi

    # Require source at minimum.
    if [[ -z "$SOURCE" ]]; then
        log_error "No SOURCE specified."
        echo "Use --help for usage information." >&2
        exit $EXIT_ERROR
    fi

    # Require dest for conversion (not needed for --list / --info / --dry-run without dest).
    if [[ "$LIST_MODE" == false && "$INFO_MODE" == false && -z "$DEST" && "$DRY_RUN" == false ]]; then
        log_error "No DEST specified. Use --dry-run to read without writing."
        exit $EXIT_ERROR
    fi

    # Print header in non-JSON, non-verbose mode for human friendliness.
    if [[ "$OUTPUT_JSON" == false && "$VERBOSE" == false ]]; then
        if [[ "$LIST_MODE" == true ]]; then
            log_info "Listing nodes in: ${SOURCE}"
        elif [[ "$INFO_MODE" == true ]]; then
            log_info "Getting info for: ${SOURCE}"
        elif [[ "$DRY_RUN" == true ]]; then
            log_info "Dry-run: ${SOURCE}"
        else
            log_info "Converting: ${SOURCE}  →  ${DEST}"
        fi
    fi

    run_converter
}

main "$@"
