#!/usr/bin/env bash
# ============================================================
# Figma Workflow Runner
# Location: ~/.config/opencode/bin/figma-workflow-runner.sh
# Orchestrates multi-step Figma tool workflows
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURATION
# ============================================================

DRY_RUN=false
FIGMA_FILE_URL="${FIGMA_FILE_URL:-}"
FIGMA_NODE_ID="${FIGMA_NODE_ID:-}"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================
# WORKFLOW METADATA
# ============================================================

get_workflow_description() {
    case "$1" in
        design-system)      echo "Extract a full design system: tokens, colors, typography, and CSS export" ;;
        component-library)  echo "Search, render, and export components as React/JSX" ;;
        a11y-audit)         echo "Run accessibility checks on colors, contrast, and typography" ;;
        code-export)        echo "Export production-ready CSS, Tailwind, and JSX from selections" ;;
        *)                  return 1 ;;
    esac
}

ALL_WORKFLOWS="design-system component-library a11y-audit code-export"

# ============================================================
# STEP DEFINITIONS
# Returns tab-separated: label\tcommand
# ============================================================

get_workflow_steps() {
    case "$1" in
        design-system)
            echo 'Connect to Figma file	figma connect --url "$FIGMA_FILE_URL"'
            echo 'Extract design tokens (shadcn format)	figma tokens shadcn --url "$FIGMA_FILE_URL"'
            echo 'Visualize token hierarchy	figma visualize --url "$FIGMA_FILE_URL" --type tokens'
            echo 'Analyze color palette	figma analyze colors --url "$FIGMA_FILE_URL"'
            echo 'Export CSS variables	figma export css --url "$FIGMA_FILE_URL"'
            ;;
        component-library)
            echo 'Connect to Figma file	figma connect --url "$FIGMA_FILE_URL"'
            echo 'Search for components	figma search --url "$FIGMA_FILE_URL" --query "components"'
            echo 'Render component previews	figma render --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"'
            echo 'Convert to React components	figma to-component --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"'
            echo 'Export JSX code	figma export-jsx --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"'
            ;;
        a11y-audit)
            echo 'Connect to Figma file	figma connect --url "$FIGMA_FILE_URL"'
            echo 'Lint for accessibility issues	figma lint --url "$FIGMA_FILE_URL" --preset accessibility'
            echo 'Analyze color contrast	figma analyze colors --url "$FIGMA_FILE_URL"'
            echo 'Analyze typography scale	figma analyze typography --url "$FIGMA_FILE_URL"'
            ;;
        code-export)
            echo 'Connect to Figma file	figma connect --url "$FIGMA_FILE_URL"'
            echo 'Export CSS variables	figma export css --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"'
            echo 'Export Tailwind config	figma export tailwind --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"'
            echo 'Export JSX from selection	figma export-jsx --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID" --selection'
            ;;
    esac
}

# ============================================================
# CORE FUNCTIONS
# ============================================================

run_workflow() {
    local workflow="$1"
    local step_num=0
    local total_steps

    total_steps=$(get_workflow_steps "$workflow" | wc -l | tr -d ' ')
    local description
    description=$(get_workflow_description "$workflow")

    echo -e "${BOLD}${BLUE}================================================${NC}"
    echo -e "${BOLD}  Workflow: ${CYAN}${workflow}${NC}"
    echo -e "${BOLD}  ${description}${NC}"
    echo -e "${BOLD}${BLUE}================================================${NC}"
    echo ""

    while IFS=$'\t' read -r label cmd; do
        step_num=$((step_num + 1))

        echo -e "${BOLD}[Step ${step_num}/${total_steps}]${NC} ${CYAN}${label}${NC}"

        if $DRY_RUN; then
            echo -e "  ${YELLOW}(dry-run)${NC} ${cmd}"
        else
            echo -e "  ${GREEN}Running:${NC} ${cmd}"
            if ! eval "$cmd" 2>&1; then
                echo -e "  ${RED}ERROR: Step ${step_num} failed${NC}"
                return 1
            fi
            echo -e "  ${GREEN}Done${NC}"
        fi
        echo ""
    done < <(get_workflow_steps "$workflow")

    if $DRY_RUN; then
        echo -e "${YELLOW}Dry run complete. No commands were executed.${NC}"
    else
        echo -e "${GREEN}${BOLD}Workflow '${workflow}' completed successfully!${NC}"
    fi
}

list_workflows() {
    echo -e "${BOLD}Available Figma Workflows:${NC}"
    echo ""
    for workflow in $ALL_WORKFLOWS; do
        local desc
        desc=$(get_workflow_description "$workflow")
        echo -e "  ${CYAN}${workflow}${NC}"
        echo -e "    ${desc}"
        echo ""
    done
    echo -e "Usage: figma-workflow-runner.sh [OPTIONS] <workflow>"
    echo -e "Run with ${YELLOW}--dry-run${NC} to preview steps without executing."
}

show_help() {
    cat << 'EOF'
Figma Workflow Runner v1.0.0

Usage: figma-workflow-runner.sh [OPTIONS] <workflow>

Workflows:
  design-system       Extract tokens, colors, typography, and CSS
  component-library   Search, render, and export components as JSX
  a11y-audit          Accessibility audit: contrast, typography, lint
  code-export         Export CSS, Tailwind config, and JSX

Options:
  --help, -h          Show this help
  --list              List available workflows with descriptions
  --dry-run           Preview workflow steps without executing

Environment Variables:
  FIGMA_FILE_URL      Figma file URL to operate on
  FIGMA_NODE_ID       Figma node ID for component selection

Examples:
  figma-workflow-runner.sh --list
  figma-workflow-runner.sh --dry-run design-system
  FIGMA_FILE_URL="https://figma.com/file/abc" figma-workflow-runner.sh design-system
EOF
}

# ============================================================
# ARGUMENT PARSING
# ============================================================

parse_args() {
    local workflow=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --list)
                list_workflows
                exit 0
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -*)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
            *)
                workflow="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$workflow" ]]; then
        echo -e "${RED}Error: No workflow specified${NC}"
        echo ""
        list_workflows
        exit 1
    fi

    if ! get_workflow_description "$workflow" > /dev/null 2>&1; then
        echo -e "${RED}Error: Unknown workflow '${workflow}'${NC}"
        echo ""
        list_workflows
        exit 1
    fi

    run_workflow "$workflow"
}

# ============================================================
# MAIN
# ============================================================

parse_args "$@"
