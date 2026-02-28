# DesignDev — Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-03-01

### Design Converter — Phase 1 Complete

The design-converter service reaches production-ready status. All critical
field-name bugs fixed, rich text support added, DTCG token export shipped.

#### `ir/nodes.py`
- **Added** `locked: bool = False` field to `UNNode`
- **Added** `UNTextRun` dataclass — per-character style spans with `content`, `start`, `end`, `fill`, `font_family`, `font_size`, `font_weight`, `italic`, `underline`, `strikethrough`, `letter_spacing`, `text_transform`
- **Added** `__post_init__` validation on `UNTextRun` (start ≤ end, start ≥ 0)
- **Changed** `text_runs: List[Dict]` → `List[UNTextRun]` on `UNNode`
- **Changed** `variable_bindings: List` → `Dict[str, UNVariableBinding]` on `UNNode`
- **Fixed** `un_node_to_dict` / `un_node_from_dict` — full round-trip for `UNTextRun`, fill `blend_mode`, and `UNVariableBinding`
- **Removed** ~92 lines of dead code (unreachable duplicate factory functions after `return node`)

#### `adapters/figma/writer.py`
- **Fixed** `_rgba()` catastrophic bug — was dividing float channels by 255 again (channels are already 0.0–1.0); all colors were near-black
- **Fixed** `node.svg_data` → `node.geometry` (PATH nodes)
- **Fixed** `node.size.width/height` → `node.width.value / node.height.value` (`UNSize` objects)
- **Fixed** `node.layout_mode` → `node.layout` (correct field name)
- **Fixed** `node.item_spacing` → `node.gap`
- **Fixed** `figma.group(children)` — children now appended to `figma.currentPage` before grouping (Figma API requirement)
- **Added** `_emit_variable_bindings()` — emits `node.setBoundVariable(...)` Plugin API calls
- **Added** `_emit_text_runs()` — emits `setRangeFills`, `setRangeFontSize`, `setRangeFontName`, `setRangeTextDecoration` for non-base styled spans
- **Fixed** `TextAutoResize` enum mapped correctly to Figma's `textAutoResize` property values

#### `adapters/figma/reader.py`
- **Fixed** `_ALIGN_ITEMS_MAP["BASELINE"]` → `AlignItems.START` (was incorrectly `AlignItems.STRETCH`)
- **Added** `boundVariables` extraction into `UNVariableBinding` dict on all nodes
- **Added** image fill URL expiry warning (Figma CDN URLs expire ~1 hour)
- **Changed** `_convert_fills()` accepts `node_name` parameter for clearer warnings

#### `adapters/figma/client.py`
- **Fixed** rate limit handling — on HTTP 429, sleeps `Retry-After` seconds (default 30s) then continues instead of immediately re-raising `FigmaRateLimitError`

#### `adapters/paper/client.py`
- **Fixed** session ID now sent as `mcp-session-id` HTTP header (was incorrectly sent as `?sessionId=` query param — Paper MCP rejects query param)

#### `adapters/pencil/reader.py`
- **Added** calls `get_styles()` at connect time
- **Added** `_apply_style_bindings()` — populates `variable_bindings` from Pencil style data

#### `adapters/pencil/writer.py`
- **Added** `_variable_binding_ops()` — logs `WARNING` per binding (Pencil's `batch_design` has no `bind_variable` op; bindings cannot be round-tripped yet)

#### `utils/tokens.py` _(new file)_
- **Added** `extract_tokens(root)` — walks UNNode tree, returns DTCG 2025.10 dict with `color`, `typography`, `shadow`, `dimension` token categories
- **Added** `export_tokens_json(root, path)` — writes DTCG JSON to disk, returns counts per category
- **Added** `tokens_to_css_vars(tokens)` — converts color + dimension tokens to CSS `:root { --var: value; }` block

#### `converter.py`
- **Added** `--export-tokens OUTPUT` CLI flag — extract DTCG tokens from source design to JSON file

#### `docs/` _(new directory)_
- **Added** `UNNODE_DEEP_DIVE.md` — 784-line research document: executive summary, technical deep dive, competitive landscape (Octopus, pbdl, DTCG), gap analysis (G1–G10), 5-phase roadmap, implementation guide, appendices
- **Added** `UNNODE_DEEP_DIVE.html` — beautiful standalone HTML rendering of the deep dive with JetBrains Mono, highlight.js syntax highlighting, TOC sidebar, reading progress bar

#### `dashboards/figma-tools.html`
- **Added** IR Reference tab — all 9 UNNode deep dive sections embedded in the dashboard, styled with Geist fonts + emerald design system
- **Added** dynamic sidebar — switches between Quick Actions (Dashboard mode) and 9-section TOC (IR mode)
- **Added** IntersectionObserver active section tracking in TOC
- **Added** highlight.js syntax highlighting for code blocks
- **Added** copy buttons on all code blocks
- **Added** reading progress bar and scroll-to-top (active in IR mode)

#### `AGENTS.md` / `CLAUDE.md` / `SOUL.md`
- **Added** mandatory documentation rule: any change in `services/design-converter/` must update both `UNNODE_DEEP_DIVE.html` and the IR Reference tab in `figma-tools.html`
- **Added** change type → HTML section lookup table
- **Updated** `SOUL.md` with design-converter architecture, DTCG workflow, dashboard description, v1.1.0

---

## [0.3.0] — 2026-02-28

### Design Converter Service — Initial Commit

New Python service: `services/design-converter/` — 18 files, 12,636 lines.

#### `ir/nodes.py`
- **Added** `UNNode` dataclass — core IR node with geometry, layout, fills, strokes, effects, typography, components, variable bindings, children
- **Added** `NodeType` enum — DOCUMENT, CANVAS, FRAME, GROUP, COMPONENT, INSTANCE, RECTANGLE, ELLIPSE, PATH, TEXT, IMAGE, UNKNOWN
- **Added** `UNColor`, `UNSize`, `UNPadding`, `UNCornerRadius`, `UNLayout` structs
- **Added** `UNSolidFill`, `UNGradientFill`, `UNImageFill` fill union types
- **Added** `UNStroke`, `UNDropShadow`, `UNBlur` effect types
- **Added** `UNTextStyle` — full typography properties
- **Added** `UNVariableBinding` — design token binding struct
- **Added** `LayoutMode`, `SizingMode`, `JustifyContent`, `AlignItems`, `TextAlign`, `TextTransform`, `TextAutoResize`, `GradientType`, `ImageFillMode`, `StrokeAlign`, `BlendMode` enums
- **Added** factory helpers: `make_frame`, `make_text`, `make_rect`, `make_ellipse`, `make_path`, `make_solid_fill`, `make_gradient_fill`, `make_shadow`
- **Added** `un_node_to_dict` / `un_node_from_dict` serialisation

#### `adapters/figma/`
- **Added** `FigmaClient` — REST API client (GET files, nodes, images, styles; POST variables)
- **Added** `FigmaReader` — converts Figma REST JSON → UNNode tree (recursive `_figma_node_to_unnode`, fills, strokes, effects, text, auto-layout)
- **Added** `FigmaWriter` — converts UNNode tree → Figma Plugin API JavaScript IIFE (`mode="script"` saves `.js` file; `mode="bridge"` uses WebSocket to Desktop Bridge)

#### `adapters/paper/`
- **Added** `PaperClient` — HTTP JSON-RPC client for Paper Design MCP (`localhost:29979`, SSE protocol)
- **Added** `PaperReader` — parses Paper JSX/HTML component tree → UNNode (full CSS inline style parsing, Tailwind class mapping)
- **Added** `PaperWriter` — writes UNNode → HTML component file

#### `adapters/pencil/`
- **Added** `PencilClient` — HTTP REST client for Pencil.dev MCP (auto-probes ports 19000–19009)
- **Added** `PencilReader` — converts Pencil `.pen` JSON → UNNode
- **Added** `PencilWriter` — converts UNNode → Pencil `batch_design` API operations

#### `utils/`
- **Added** `color.py` — 20+ color conversion functions: hex, rgb float, Figma color, HSL, oklab, gradient stops, contrast ratio, dark detection
- **Added** `css.py` — CSS property mapping from UNNode: `node_to_css`, `parse_inline_style`, `parse_tailwind_classes`, `apply_css_to_node`, `merge_styles`
- **Added** `svg.py` — SVG path utilities: `normalize_svg_path`, `path_bbox`, `scale_path`, `translate_path`, shape-to-path converters
- **Added** `jsx_parser.py` — JSX/React component parser for Paper reader

#### `converter.py`
- **Added** `DesignConverter` orchestrator — `convert(spec)`, `list_sources()`, `list_destinations()`, `get_info()`
- **Added** `ConvertSpec`, `ConvertResult` typed dataclasses
- **Added** argparse CLI: `--source`, `--dest`, `--node-id`, `--output`, `--dry-run`, `--json`, `--list`, `--info`

#### `cli/bin/design-convert.sh`
- **Added** bash entry-point following same patterns as `figma-tokens.sh`; supports interactive mode, `--list`, `--info`, `--dry-run`, `--json`

---

## [0.2.2] — 2026-02-28

### Dashboard — Geist Design System

- **Changed** `dashboards/figma-tools.html` complete redesign
  - Vercel Geist Sans + Geist Mono fonts
  - shadcn/ui emerald design tokens (full CSS variable system)
  - Modern grid layout: 280px fixed sidebar + main content
  - Stats cards, server cards, searchable tools list
  - Pulsing status badge, hover micro-interactions

---

## [0.2.1] — 2026-02-28

### MCP Config Fixes + First Dashboard

- **Fixed** MCP package names (`figma-developer-mcp`, removed invalid `@figma/mcp-server`)
- **Added** `dashboards/figma-tools.html` — first version of the workspace dashboard
- **Updated** `mcps/add-to-opencode.sh` with correct package names and protocol info
- **Added** workspace protocols section: qmd-first, Ralph Loop, GSD, Browser Validation

---

## [0.2.0] — 2026-02-28

### Three Figma MCP Servers

- **Added** `mcps/figma-console/` — 56+ tools, full CRUD access via Desktop Bridge WebSocket plugin
- **Added** `mcps/claude-talk-to-figma/` — Claude-optimized MCP with accessibility linting and semantic variable extraction
- **Added** `mcps/official/` — Official Figma MCP with Dev Mode + Code Connect integration
- **Added** `mcps/add-to-opencode.sh` — one-command registration of all MCPs in OpenCode
- **Added** `mcps/mcp-config.json` — unified MCP configuration
- **Added** `docs/knowledge/FIGMA-MCPS.md` — comprehensive MCP integration guide
- **Updated** `AGENTS.md` with MCP server documentation and tool catalog

---

## [0.1.0] — 2026-02-28

### Initial DesignDev Consolidation

Unified all design tooling into a single repository, consolidated from: figma-ai-designer, Figma-AI-Plugin, Paper-design, and scattered CLI tools.

#### Plugins
- **Added** `plugins/ai-designer/` — AI-powered Figma plugin; TypeScript + Preact + Vite + Tailwind; multi-model support (GLM-5, Kimi, GPT-4o); generates designs from text prompts; exports tokens to CSS/JSON/Tailwind
- **Added** `plugins/desktop-bridge/` — MCP Bridge plugin; WebSocket connection to MCP servers; real-time bidirectional communication; `design-system-builder.js`

#### CLI Tools (`cli/bin/`)
- **Added** `figma-tokens.sh` — Extract design tokens; presets: shadcn, tailwind; export: CSS, JSON
- **Added** `figma-analyze.sh` — Analyze Figma files for colors, typography, all components
- **Added** `figma-workflow-runner.sh` — Run predefined workflows: design-system, component-library, a11y-audit, code-export
- **Added** `figma-smoke-test.sh` — E2E test suite (full 7-step, quick 3-step, skip-cleanup)

#### Skills
- **Added** `skills/ui-ux-pro-max/` — Design intelligence with 13 CSV databases: 67 UI styles, 96 color palettes, 57 typography pairings, product/chart/icon/landing page references, 13 framework stack guidelines
- **Added** `skills/will-designer/` — Designer-specialized agent for UI/UX recommendations

#### Knowledge Base (`docs/knowledge/`)
- **Added** `COMPONENT-ARCHITECTURE.md` — Figma component patterns and conventions
- **Added** `DESIGN-SYSTEM-PATTERNS.md` — Design system best practices
- **Added** `FIGMA-PLUGIN-API.md` — Plugin API reference and patterns
- **Added** `FIGMA-VARIABLES.md` — Variable system guide (collections, modes, scopes)
- **Added** `LLM-GENERATION-GUIDELINES.md` — AI generation rules for consistent output
- **Added** `TEXT-COMPONENTS.md` — Typography component patterns
- **Added** `TOKEN-SYSTEM.md` — Design token architecture reference

#### Project Files
- **Added** `AGENTS.md` — Comprehensive agent and session instructions (structure, conventions, workflows)
- **Added** `SOUL.md` — Project identity, core beliefs, architecture, anti-patterns
- **Added** `CLAUDE.md` — Claude Code guidance: commands, architecture, MCP details, conventions

---

[1.0.0]: https://github.com/willbnu/DesignDev/compare/aa61749...HEAD
[0.3.0]: https://github.com/willbnu/DesignDev/compare/01b9a42...aa61749
[0.2.2]: https://github.com/willbnu/DesignDev/compare/ebd40da...01b9a42
[0.2.1]: https://github.com/willbnu/DesignDev/compare/bff9624...d7934c4
[0.2.0]: https://github.com/willbnu/DesignDev/compare/eb7ca3b...bff9624
[0.1.0]: https://github.com/willbnu/DesignDev/compare/eb7ca3b...eb7ca3b
