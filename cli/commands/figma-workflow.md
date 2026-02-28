# /figma-workflow - Figma Tool Orchestration

**Purpose**: Orchestrate Figma design-to-code workflows via MCP tools and CLI commands
**Source**: ~/.config/opencode/command/figma-workflow.md

---

## What This Skill Does

The `/figma-workflow` command provides agent-executable instructions for all Figma tool operations. It covers 7 actions with exact MCP tool calls and CLI commands for each.

---

## Usage

```
/figma-workflow [ACTION]
```

**Actions**: `status`, `connect`, `tokens`, `analyze`, `lint`, `export`, `workflow`

---

## Preflight (Run Before Any Action)

Before executing ANY action below, run the preflight check:

```bash
bash ~/.config/opencode/bin/figma-preflight.sh
```

If preflight fails, resolve the reported issues before proceeding. If the script does not exist, manually verify:

1. **Node.js**: `node --version` (must return v18+)
2. **Figma CLI**: Verify MCP server is configured
3. **Environment**: `FIGMA_FILE_URL` is set (if required by the action)

---

## Action: status

### Agent Instructions

**Purpose**: Check Figma connection status and environment readiness.

**Execution Order**:
1. Call MCP tool to retrieve document info
2. Fall back to CLI if MCP unavailable

**MCP Tool Calls**:
```
get_document()
```
- Returns: Document name, page list, node count
- Success: Document metadata returned means Figma is connected
- Failure: Tool error or timeout means Figma is not connected

**CLI Commands (Fallback)**:
```bash
bash ~/.config/opencode/bin/figma-preflight.sh
```

**Error Handling**:
- If MCP tool returns error: report "Figma not connected" and suggest running `connect` action
- Exit code `2` = not connected

**Expected Output**:
- Connected: Document name, page count, connection confirmed
- Not connected: Error message with remediation steps

---

## Action: connect

### Agent Instructions

**Purpose**: Establish connection to a Figma file for subsequent operations.

**Execution Order**:
1. Verify environment variables are set
2. Call MCP tool to load the document
3. Confirm connection by retrieving document structure

**MCP Tool Calls**:
```
get_document()
get_selection()
```

**CLI Commands**:
```bash
echo "${FIGMA_FILE_URL:?Error: FIGMA_FILE_URL not set}"
bash ~/.config/opencode/bin/figma-preflight.sh
```

**Error Handling**:
- If `FIGMA_FILE_URL` is not set: prompt user for the Figma file URL
- If MCP server is not running: instruct user to start the Figma AI Designer plugin
- If connection fails: exit code `2`, suggest checking Figma plugin status

**Expected Output**:
- Success: "Connected to [Document Name] with [N] pages, [M] components"
- Failure: Specific error with remediation steps

---

## Action: tokens

### Agent Instructions

**Purpose**: Extract design tokens (colors, spacing, typography) from the connected Figma file.

**Execution Order**:
1. Verify Figma connection (call `get_document()`)
2. Retrieve variables with specified preset
3. Set up design tokens in the target format
4. Export tokens to the specified format

**MCP Tool Calls**:
```
get_document()
figma_get_variables({ format: "full" })
figma_get_variables({ format: "full", namePattern: "^semantic" })
figma_setup_design_tokens({
  collectionName: "Design System",
  modes: ["Light", "Dark"],
  tokens: [...]
})
create_variable_collection(name: "Tokens")
create_color_variable(name: "primary", collection: "Tokens", light: "#3b82f6", dark: "#60a5fa")
```

**CLI Commands**:
```bash
bash ~/.config/opencode/bin/figma-tokens.sh --preset=shadcn --export=css
bash ~/.config/opencode/bin/figma-tokens.sh --preset=tailwind --export=json
bash ~/.config/opencode/bin/figma-tokens.sh
bash ~/.config/opencode/bin/figma-tokens.sh --help
```

**Error Handling**:
- If not connected: exit code `2`, run `connect` action first
- If invalid preset: exit code `1`, show valid presets (shadcn, tailwind, raw, custom)
- If invalid export format: exit code `1`, show valid formats (css, scss, json, tailwind)
- If no variables found: report empty result, suggest checking Figma file has variables defined

**Expected Output**:
- Token extraction summary: count of colors, spacing, typography tokens found
- Exported file path or formatted output in the requested format

---

## Action: analyze

### Agent Instructions

**Purpose**: Analyze design properties (colors, typography, spacing, components) from the Figma file.

**Execution Order**:
1. Verify Figma connection (call `get_document()`)
2. Retrieve document structure
3. Analyze the specified property type
4. Format and return results

**MCP Tool Calls**:
```
get_document()
get_components()
figma_get_variables({ format: "full" })
get_selection()
```

**CLI Commands**:
```bash
bash ~/.config/opencode/bin/figma-analyze.sh --type=colors
bash ~/.config/opencode/bin/figma-analyze.sh --type=typography
bash ~/.config/opencode/bin/figma-analyze.sh --type=spacing
bash ~/.config/opencode/bin/figma-analyze.sh --type=components
bash ~/.config/opencode/bin/figma-analyze.sh --type=all
bash ~/.config/opencode/bin/figma-analyze.sh --type=colors --json
bash ~/.config/opencode/bin/figma-analyze.sh
bash ~/.config/opencode/bin/figma-analyze.sh --help
```

**Error Handling**:
- If not connected: exit code `2`, run `connect` action first
- If invalid type: exit code `1`, show valid types (colors, typography, spacing, components, all)
- If analysis returns empty: report "No [type] properties found in document"

**Expected Output**:
- Human-readable: Categorized list of design properties with values
- JSON mode: Structured JSON object with analysis results

---

## Action: lint

### Agent Instructions

**Purpose**: Run design linting checks (accessibility, consistency, naming conventions).

**Execution Order**:
1. Verify Figma connection (call `get_document()`)
2. Retrieve document structure and components
3. Run lint checks against the specified preset
4. Report violations with severity levels

**MCP Tool Calls**:
```
get_document()
get_components()
figma_get_variables({ format: "full" })
get_selection()
```

Lint checks are performed by the agent by analyzing the retrieved data:
- **Accessibility**: Check color contrast ratios (WCAG AA/AAA), text sizes, touch targets
- **Consistency**: Check for similar-but-different colors, inconsistent spacing, naming patterns
- **Naming**: Check layer naming conventions, component naming structure

**CLI Commands**:
```bash
bash ~/.config/opencode/bin/figma-workflow-runner.sh --dry-run a11y-audit
bash ~/.config/opencode/bin/figma-workflow-runner.sh a11y-audit
bash ~/.config/opencode/bin/figma-analyze.sh --type=colors --json
```

**Error Handling**:
- If not connected: exit code `2`, run `connect` action first
- If no violations found: report "All checks passed" with summary
- If lint errors found: list violations grouped by severity (error, warning, info)

**Expected Output**:
- Lint report: violation count by severity, grouped by check type
- Per-violation: element name, issue description, suggested fix

---

## Action: export

### Agent Instructions

**Purpose**: Export design assets as production-ready code (CSS, Tailwind, JSX).

**Execution Order**:
1. Verify Figma connection (call `get_document()`)
2. Get current selection or target nodes
3. Export in the requested format
4. Write or display the exported code

**MCP Tool Calls**:
```
get_document()
get_selection()
get_components()
figma_get_variables({ format: "full" })
```

The agent generates export output by converting retrieved Figma data:
- **CSS**: Convert variables to CSS custom properties
- **Tailwind**: Convert to tailwind.config.js theme extension
- **JSX**: Convert components to React JSX component code

**CLI Commands**:
```bash
figma export css --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"
figma export tailwind --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"
figma export-jsx --url "$FIGMA_FILE_URL" --node-id "$FIGMA_NODE_ID"
bash ~/.config/opencode/bin/figma-workflow-runner.sh code-export
bash ~/.config/opencode/bin/figma-workflow-runner.sh --dry-run code-export
bash ~/.config/opencode/bin/figma-tokens.sh --preset=shadcn --export=css
bash ~/.config/opencode/bin/figma-tokens.sh --preset=tailwind --export=tailwind
```

**Error Handling**:
- If not connected: exit code `2`, run `connect` action first
- If no selection and no node ID: prompt user to select elements or provide `FIGMA_NODE_ID`
- If export format unsupported: exit code `1`, show supported formats
- If empty export: report "No exportable content found in selection"

**Expected Output**:
- Generated code in the requested format (CSS, Tailwind config, or JSX)
- File path if written to disk, or inline code block if displayed

---

## Action: workflow

### Agent Instructions

**Purpose**: Execute a predefined multi-step workflow (meta-action that chains other actions).

**Execution Order**:
1. Verify Figma connection (preflight)
2. List or select target workflow
3. Execute each step sequentially with progress indicators
4. Report results per step and final summary

**Available Definitions**:

| Name | Steps | Description |
|------|-------|-------------|
| `design-system` | 5 | connect, tokens shadcn, visualize, analyze colors, export css |
| `component-library` | 5 | connect, search, render, to-component, export-jsx |
| `a11y-audit` | 4 | connect, lint accessibility, analyze colors, analyze typography |
| `code-export` | 4 | connect, export css, export tailwind, export-jsx |

**MCP Tool Calls** (varies by definition, example for `design-system`):
```
# Step 1: Connect
get_document()

# Step 2: Extract tokens
figma_get_variables({ format: "full" })
figma_setup_design_tokens({ collectionName: "Design System", modes: ["Light", "Dark"], tokens: [...] })

# Step 3: Visualize
get_components()

# Step 4: Analyze colors
figma_get_variables({ format: "full", namePattern: "color" })

# Step 5: Export CSS
figma_get_variables({ format: "full" })
```

**CLI Commands**:
```bash
bash ~/.config/opencode/bin/figma-workflow-runner.sh --list
bash ~/.config/opencode/bin/figma-workflow-runner.sh --dry-run design-system
bash ~/.config/opencode/bin/figma-workflow-runner.sh --dry-run component-library
bash ~/.config/opencode/bin/figma-workflow-runner.sh --dry-run a11y-audit
bash ~/.config/opencode/bin/figma-workflow-runner.sh --dry-run code-export
bash ~/.config/opencode/bin/figma-workflow-runner.sh design-system
bash ~/.config/opencode/bin/figma-workflow-runner.sh a11y-audit
bash ~/.config/opencode/bin/figma-workflow-runner.sh --help
```

**Error Handling**:
- If not connected: exit code `2`, run `connect` action first
- If invalid name: exit code `1`, show available options with `--list`
- If a step fails: stop execution, report which step failed with `[Step N/M] FAILED`, exit `1`
- If `--dry-run`: show all steps without executing, exit `0`

**Expected Output**:
- Per-step: `[Step N/M] description... DONE` or `FAILED`
- Final summary: "Completed: N/M steps succeeded"

---

## Chaining Multiple Actions

For complex design-to-code pipelines, chain multiple actions:

### Full Design System Pipeline
```
1. /figma-workflow status       -- Verify connection
2. /figma-workflow tokens       -- Extract design tokens
3. /figma-workflow analyze      -- Analyze design properties
4. /figma-workflow lint         -- Check accessibility
5. /figma-workflow export       -- Generate production code
```

### Quick Accessibility Check
```
1. /figma-workflow status       -- Verify connection
2. /figma-workflow lint         -- Run accessibility audit
```

### Component Export Pipeline
```
1. /figma-workflow connect      -- Connect to Figma file
2. /figma-workflow workflow     -- Run component-library definition
```

### Chaining Rules
- Always run `status` or `connect` first to verify connectivity
- If any step returns exit code `2`, stop and resolve connection
- If any step returns exit code `1`, investigate the error before continuing
- Use `--dry-run` on workflow actions to preview before executing

---

**Created**: 2026-02-27
**Version**: 2.0.0
