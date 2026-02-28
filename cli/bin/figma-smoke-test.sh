#!/bin/bash
# ============================================================
# Figma Smoke Test Script
# Location: ~/.config/opencode/bin/figma-smoke-test.sh
# Purpose: End-to-end validation of the Figma tooling suite
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURATION
# ============================================================

OPENCODE_DIR="${HOME}/.config/opencode"
QUICK_MODE=false
SKIP_CLEANUP=false
TOTAL_STEPS=7
PASS_COUNT=0
FAIL_COUNT=0
START_TIME=""
TEMP_FILES=()

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================
# LOGGING
# ============================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS_COUNT++)) || true
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++)) || true
}

# ============================================================
# ARGUMENT PARSING
# ============================================================

show_help() {
    cat << EOF
Figma Smoke Test — End-to-end validation of the Figma tooling suite

Usage: figma-smoke-test.sh [OPTIONS]

Options:
  --quick          Run only steps 1-3 (connectivity check only)
  --skip-cleanup   Skip step 7 cleanup
  --help, -h       Show this help message

Test Steps:
  1. Verify Node.js installed
  2. Verify Figma CLI installed
  3. Verify Figma connection (5s timeout)
  4. Test tokens extraction (figma-tokens.sh --help)
  5. Test analyze command (figma-analyze.sh --help)
  6. Test workflow runner (figma-workflow-runner.sh --list)
  7. Cleanup and summary

Exit Codes:
  0  All tests passed
  1  One or more tests failed
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_MODE=true
                TOTAL_STEPS=3
                shift
                ;;
            --skip-cleanup)
                SKIP_CLEANUP=true
                shift
                ;;
            --help|-h)
                show_help
                ;;
            *)
                echo "Unknown option: $1" >&2
                echo "Use --help for usage information" >&2
                exit 1
                ;;
        esac
    done
}

# ============================================================
# TEST STEPS
# ============================================================

run_step() {
    local step_num="$1"
    local step_name="$2"
    local step_start
    step_start=$(date +%s)

    log_info "Step ${step_num}/${TOTAL_STEPS}: ${step_name}"

    if eval "test_step_${step_num}"; then
        local step_end
        step_end=$(date +%s)
        log_pass "${step_name} ($((step_end - step_start))s)"
    else
        local step_end
        step_end=$(date +%s)
        log_fail "${step_name} ($((step_end - step_start))s)"
    fi
}

test_step_1() {
    # Verify Node.js installed
    if command -v node &>/dev/null; then
        local version
        version=$(node --version 2>/dev/null)
        log_info "  Node.js version: ${version}"
        return 0
    fi
    return 1
}

test_step_2() {
    # Verify Figma CLI installed
    if command -v figma &>/dev/null; then
        log_info "  Figma CLI found at: $(command -v figma)"
        return 0
    fi
    if command -v npx &>/dev/null && npx figma --version &>/dev/null 2>&1; then
        log_info "  Figma CLI available via npx"
        return 0
    fi
    return 1
}

test_step_3() {
    # Verify Figma connection (5s timeout)
    if command -v curl &>/dev/null; then
        if curl -s --max-time 5 -o /dev/null -w "%{http_code}" https://api.figma.com/v1/me 2>/dev/null | grep -qE '^[0-9]+$'; then
            log_info "  Figma API reachable"
            return 0
        fi
    fi
    return 1
}

test_step_4() {
    # Test tokens extraction
    local script="${OPENCODE_DIR}/bin/figma-tokens.sh"
    if [[ -x "$script" ]] && bash "$script" --help &>/dev/null; then
        log_info "  figma-tokens.sh --help: exit 0"
        return 0
    fi
    return 1
}

test_step_5() {
    # Test analyze command
    local script="${OPENCODE_DIR}/bin/figma-analyze.sh"
    if [[ -x "$script" ]] && bash "$script" --help &>/dev/null; then
        log_info "  figma-analyze.sh --help: exit 0"
        return 0
    fi
    return 1
}

test_step_6() {
    # Test workflow runner
    local script="${OPENCODE_DIR}/bin/figma-workflow-runner.sh"
    if [[ -x "$script" ]] && bash "$script" --list &>/dev/null 2>&1; then
        log_info "  figma-workflow-runner.sh --list: listed workflows"
        return 0
    fi
    return 1
}

# ============================================================
# CLEANUP & SUMMARY
# ============================================================

do_cleanup() {
    if [[ "$SKIP_CLEANUP" == true ]]; then
        log_info "Cleanup skipped (--skip-cleanup)"
        return
    fi
    for f in "${TEMP_FILES[@]}"; do
        [[ -f "$f" ]] && rm -f "$f"
    done
}

print_summary() {
    local end_time
    end_time=$(date +%s)
    local elapsed=$((end_time - START_TIME))

    echo ""
    echo "=== Figma Smoke Test Results ==="
    echo "Passed: ${PASS_COUNT}/${TOTAL_STEPS} | Failed: ${FAIL_COUNT}/${TOTAL_STEPS} | Total time: ${elapsed}s"
    echo ""
}

# ============================================================
# MAIN
# ============================================================

main() {
    parse_args "$@"

    START_TIME=$(date +%s)

    echo "Figma Smoke Test v1.0.0"
    echo "================================="
    echo ""

    # Steps 1-3 (always run)
    run_step 1 "Verify Node.js installed"
    run_step 2 "Verify Figma CLI installed"
    run_step 3 "Verify Figma connection"

    # Steps 4-7 (skip in quick mode)
    if [[ "$QUICK_MODE" == false ]]; then
        run_step 4 "Test tokens extraction"
        run_step 5 "Test analyze command"
        run_step 6 "Test workflow runner"

        # Step 7: Cleanup
        log_info "Step 7/${TOTAL_STEPS}: Cleanup and summary"
        do_cleanup
    fi

    print_summary

    if [[ "$FAIL_COUNT" -gt 0 ]]; then
        exit 1
    fi
    exit 0
}

main "$@"
