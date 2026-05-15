# UNNode Deep Dive — The Universal Design Intermediate Representation

> **Version**: 1.0.0 · **Date**: 2026-03-01 · **Status**: Production-ready

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [UNNode Technical Deep Dive](#2-unnode-technical-deep-dive)
3. [Why Figma REST API is Read-Only](#3-why-figma-rest-api-is-read-only)
4. [Competitive Landscape](#4-competitive-landscape)
5. [Feature Comparison Matrix](#5-feature-comparison-matrix)
6. [Gap Analysis](#6-gap-analysis)
7. [Strategic Recommendations](#7-strategic-recommendations)
8. [Technical Implementation Guide](#8-technical-implementation-guide)
9. [Appendices](#9-appendices)

---

## 1. Executive Summary

### What UNNode Is

**UNNode** (Universal Node) is a Python dataclass-based Intermediate Representation (IR)
for design tool conversion. It occupies a single canonical layer between:

- **Figma** — industry-standard vector design tool (read/write via Plugin API + REST)
- **Paper Design** — HTML-first component system (read/write via MCP JSON-RPC at `:29979`)
- **Pencil.dev** — code-first declarative tool (read/write via HTTP REST MCP at `:19002`)

Every design node — frames, text, rectangles, ellipses, paths, components — maps to a
`UNNode` with a `NodeType` enum. The tree mirrors the design tool's layer hierarchy.

### Unique Advantages

| Advantage | Detail |
|-----------|--------|
| **Tri-tool coverage** | Only open-source IR targeting Figma + Paper + Pencil in one codebase |
| **Figma write support** | Generates Plugin API JavaScript — the only way to create nodes in Figma |
| **Rich text runs** | `UNTextRun` captures per-character style overrides from Figma's `characterStyleOverrides` |
| **DTCG token export** | `utils/tokens.py` emits W3C Design Tokens Community Group 2025.10 format |
| **Sizing modes** | `SizingMode.FIXED / HUG / FILL` per axis — mirrors Figma Auto Layout + CSS |
| **Pure Python** | No native deps, no binary wheels — works anywhere Python 3.9+ runs |
| **Serialisation** | `un_node_to_dict()` / `un_node_from_dict()` for JSON round-trips and caching |

### Market Position

UNNode is closest to **Octopus** (opendesigndev) in ambition, but tighter in scope. While
Octopus targets Figma + Sketch + XD + Adobe, UNNode targets Figma + Paper + Pencil —
the exact tools in the DesignDev workflow. Tighter scope enables faster iteration and
deeper integration per tool.

### Top Gaps (Prioritised)

1. **Component overrides** — deep instance overrides not fully captured (Octopus has `overrides[]`)
2. **Mask nodes** — `isMask` not preserved in UNNode
3. **Stroke dashes + line caps** — `UNStroke` missing `dashPattern`, `lineCap`, `lineJoin`
4. **Blend mode per fill** — `UNSolidFill` has no `blend_mode` field

---

## 2. UNNode Technical Deep Dive

### 2.1 Core Node Structure

```python
@dataclass
class UNNode:
    # ── Identity ─────────────────────────────────────────────────────
    type: NodeType                        # FRAME, TEXT, RECT, etc.
    name: str = "Untitled"
    figma_id: str = ""                   # Original Figma node ID
    locked: bool = False                 # Layer is locked in editor

    # ── Geometry ─────────────────────────────────────────────────────
    x: float = 0.0
    y: float = 0.0
    width: UNSize = field(default_factory=lambda: UNSize(100.0))
    height: UNSize = field(default_factory=lambda: UNSize(100.0))
    rotation: float = 0.0               # Degrees clockwise
    corner_radius: UNCornerRadius = field(default_factory=UNCornerRadius)

    # ── Layout (Auto Layout / Flexbox) ───────────────────────────────
    layout: LayoutMode = LayoutMode.NONE     # NONE / HORIZONTAL / VERTICAL / GRID
    gap: float = 0.0                         # itemSpacing (Figma) / gap (CSS)
    padding: UNPadding = field(default_factory=UNPadding)
    justify_content: JustifyContent = JustifyContent.START
    align_items: AlignItems = AlignItems.START
    layout_wrap: bool = False
    clip_content: bool = False               # clipsContent / overflow:hidden

    # ── Appearance ───────────────────────────────────────────────────
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    visible: bool = True

    # ── Fills, Strokes, Effects ───────────────────────────────────────
    fills:   List[UNFill]   = field(default_factory=list)
    strokes: List[UNStroke] = field(default_factory=list)
    effects: List[UNEffect] = field(default_factory=list)

    # ── Typography (TEXT nodes only) ─────────────────────────────────
    text_content: str = ""
    text_style: Optional[UNTextStyle] = None
    text_runs: List[UNTextRun] = field(default_factory=list)

    # ── Geometry (PATH / VECTOR nodes only) ──────────────────────────
    geometry: str = ""                       # SVG path data
    fill_rule: str = "nonzero"

    # ── Ellipse arcs ─────────────────────────────────────────────────
    inner_radius: float = 0.0
    start_angle: float = 0.0
    sweep_angle: float = 360.0

    # ── Components ───────────────────────────────────────────────────
    component_id: str = ""
    component_props: Dict = field(default_factory=dict)

    # ── Variables / Tokens ───────────────────────────────────────────
    variable_bindings: Dict[str, UNVariableBinding] = field(default_factory=dict)

    # ── Tree ─────────────────────────────────────────────────────────
    children: List["UNNode"] = field(default_factory=list)
```

### 2.2 NodeType Enum

```
DOCUMENT   — root wrapper (Figma document level)
CANVAS     — page / artboard container
FRAME      — auto-layout frame or plain group-with-clip
GROUP      — non-clipping group
COMPONENT  — component master definition
INSTANCE   — component instance (references a COMPONENT)
RECTANGLE  — rectangle shape
ELLIPSE    — ellipse / circle / arc / donut
PATH       — arbitrary vector (VECTOR / BOOLEAN_OPERATION / STAR / POLYGON)
TEXT       — text layer
IMAGE      — raster image node
UNKNOWN    — unrecognised type (preserved, not rendered)
```

### 2.3 UNSize — Per-Axis Sizing

```python
@dataclass
class UNSize:
    value: float = 100.0
    mode: SizingMode = SizingMode.FIXED

class SizingMode(str, Enum):
    FIXED = "fixed"   # explicit pixel size
    HUG   = "hug"     # shrink-wrap children  (CSS: width: fit-content)
    FILL  = "fill"    # fill available space   (CSS: flex-grow: 1 / width: 100%)
```

**Why per-axis?** Figma has independent `primaryAxisSizingMode` and `counterAxisSizingMode`.
A node can be `FIXED` width + `FILL` height. A single `sizing_mode` field cannot represent
this asymmetry — hence `UNNode.width: UNSize` and `UNNode.height: UNSize`.

### 2.4 UNFill Union Type

`UNFill = Union[UNSolidFill, UNGradientFill, UNImageFill]`

```python
@dataclass
class UNSolidFill:
    color: UNColor
    opacity: float = 1.0
    visible: bool = True

@dataclass
class UNGradientFill:
    gradient_type: GradientType      # LINEAR / RADIAL / ANGULAR / DIAMOND
    stops: List[UNGradientStop]
    angle: float = 0.0
    opacity: float = 1.0
    visible: bool = True

@dataclass
class UNImageFill:
    url: str = ""
    mode: ImageFillMode = ImageFillMode.FILL   # FILL / FIT / TILE / CROP
    opacity: float = 1.0
    visible: bool = True
```

`GradientType.DIAMOND` is Figma-specific — no direct CSS equivalent, rendered as radial in CSS export.

### 2.5 UNColor

```python
@dataclass
class UNColor:
    r: float    # 0.0–1.0
    g: float
    b: float
    a: float = 1.0
```

Float channels match Figma's internal representation. `utils/color.py` provides:
`figma_color_to_hex()`, `hex_to_figma_color()`, `rgb_float_to_hex()`, `is_dark_color()`, etc.

### 2.6 UNTextStyle

```python
@dataclass
class UNTextStyle:
    font_family: str = "Inter"
    font_size: float = 14.0
    font_weight: str = "400"          # CSS font-weight string
    font_style: str = "normal"        # "normal" | "italic"
    line_height: Optional[float] = None   # px; None = auto
    letter_spacing: float = 0.0
    text_align: TextAlign = TextAlign.LEFT
    text_transform: TextTransform = TextTransform.NONE
    text_auto_resize: TextAutoResize = TextAutoResize.WIDTH_HEIGHT
    underline: bool = False
    strikethrough: bool = False
```

### 2.7 UNTextRun — Rich Text Spans

```python
@dataclass
class UNTextRun:
    content: str = ""           # Substring of parent text_content
    start: int = 0              # Character start (inclusive)
    end: int = 0                # Character end (exclusive)
    fill: Optional[UNColor] = None
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[str] = None
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    letter_spacing: Optional[float] = None
    text_transform: Optional[TextTransform] = None
```

**Design**: `text_content` holds the full string. `text_runs` holds *only overridden spans*.
Characters using the base style (index == 0 in Figma's `characterStyleOverrides`) produce no run.
This keeps the list minimal and the diff semantics clean.

**Writing back via Plugin API**:
```js
node.characters = "Hello World";   // set content first
node.setRangeFills([{type:'SOLID',color:{r,g,b}}], start, end);
node.setRangeFontSize(size, start, end);
node.setRangeFontName({family:"Inter", style:"Bold"}, start, end);
node.setRangeTextDecoration("UNDERLINE", start, end);
node.setRangeLetterSpacing({unit:"PIXELS", value:ls}, start, end);
node.setRangeTextCase("UPPER", start, end);
```

### 2.8 Effects

```python
@dataclass
class UNDropShadow:
    color: UNColor
    offset_x: float = 0.0
    offset_y: float = 4.0
    blur: float = 8.0
    spread: float = 0.0
    visible: bool = True
    inner: bool = False           # True = inner shadow

@dataclass
class UNBlur:
    radius: float = 4.0
    visible: bool = True
    background: bool = False      # True = backdrop-filter blur
```

### 2.9 Variable Bindings (Design Tokens)

```python
@dataclass
class UNVariableBinding:
    variable_id: str             # Figma variable ID or token name
    variable_name: str           # Human-readable token name
    collection_name: str = ""    # Token collection / mode group
    resolved_type: str = "COLOR" # "COLOR" | "FLOAT" | "STRING" | "BOOLEAN"
    resolved_value: Any = None   # Resolved value at read time
```

Variable bindings record which Figma variables were bound to which properties.
On write-back, FigmaWriter restores bindings (`node.setBoundVariable(...)`) rather
than baking raw values — preserving the design token connection.

### 2.10 Factory Helpers

```python
make_frame(name, *, width, height, x=0, y=0) -> UNNode
make_text(name, content, *, font_size, font_weight, font_family, color) -> UNNode
make_rect(name, *, width, height, x=0, y=0, fill=None) -> UNNode
make_ellipse(name, *, width, height, x=0, y=0) -> UNNode
make_path(name, path_data, *, fill_rule="nonzero") -> UNNode
make_solid_fill(color_hex, opacity=1.0) -> UNSolidFill
make_gradient_fill(stops, *, angle=0.0, gradient_type=GradientType.LINEAR) -> UNGradientFill
make_shadow(color_hex, *, ox=0, oy=4, blur=8, spread=0) -> UNDropShadow
```

All factory functions use keyword-only args after `name` to prevent positional mistakes.

### 2.11 Serialisation

```python
un_node_to_dict(node: UNNode) -> dict       # Deep serialise to JSON-safe dict
un_node_from_dict(data: dict) -> UNNode     # Deserialise from dict
```

The format preserves all fields including `UNTextRun`, fill union types (via `__class__`
tag), and `UNVariableBinding`. Use cases: disk caching, jq inspection, inter-process
transport without re-reading from the design tool.

---

## 3. Why Figma REST API is Read-Only

### The Misconception

A common mistake is assuming `api.figma.com/v1/files/:key` can create or modify nodes.
It cannot. The Figma REST API is **read-only for design nodes**.

### What the REST API CAN Do

| Endpoint | Method | Capability |
|----------|--------|-----------|
| `GET /files/:key` | Read | Fetch full file tree |
| `GET /files/:key/nodes` | Read | Fetch specific nodes |
| `GET /files/:key/images` | Read | Get image CDN URLs |
| `GET /files/:key/styles` | Read | List published styles |
| `POST /files/:key/comments` | Write | Add a comment |
| `POST /v1/variables/:key` | **Write** | Create/update design variables |
| `DELETE /v1/variables/:key` | **Write** | Delete design variables |

**Node mutation is explicitly unavailable via REST.** Figma's official docs state:
*"The Figma plugin API is the only way to create, modify, or delete design nodes."*

### The Solution: Plugin API via JavaScript

The Figma Plugin API runs JavaScript inside Figma's plugin sandbox. To create nodes you must:
1. Write JavaScript using the `figma.*` global API
2. Execute it inside Figma via Figma Console (paste) or a packaged plugin

### FigmaWriter's Two Modes

| Mode | How | Use When |
|------|-----|----------|
| `script` | Generates `.js` IIFE → user pastes into Figma Console | One-off conversions, debugging, handoff |
| `bridge` | WebSocket server ↔ Desktop Bridge plugin | Automated pipelines, MCP tools, CI |

`FigmaClient.post_variables()` is the **one** REST write we do use — for design variable
(token) creation. Everything else — nodes, frames, text — goes through the Plugin API JS.
This is the industry-standard approach used by Anima, Figmania, and every serious Figma
code-export tool.

---

## 4. Competitive Landscape

### 4.1 Octopus (opendesigndev) — Closest Competitor

**Repo**: `opendesign/octopus` · TypeScript · MIT · Actively maintained

Octopus is a TypeScript IR targeting Figma, Sketch, XD, and Adobe Illustrator. Each node
is an `OctopusLayer` — a discriminated union type per layer kind.

**Strengths over UNNode**:
- Full component override capture (`overrides[]`)
- `$extensions` escape hatch for tool-specific metadata
- Typed discriminated union (TypeScript enforces structural invariants)
- Mask layer support (`role: "MASK"`)
- Battle-tested Sketch + XD converters

**Weaknesses vs UNNode**:
- TypeScript-only (no Python, no Dart)
- No Paper or Pencil.dev support
- No DTCG token export built-in
- No Figma node write capability
- Heavier, more verbose serialisation format

### 4.2 pbdl (Parabeac Design Language) — Archived

**Repo**: `Parabeac/Parabeac-Core` · Dart · MIT · Maintenance stopped 2024

Dart IR for Figma + Sketch → Flutter component generation. Structurally similar to UNNode.
Archived due to the project shutdown. Not a relevant competitive threat — relevant only as
a reference for Dart-side design IR patterns.

### 4.3 W3C DTCG — Token Standard (Not an IR)

**Spec**: `design-tokens.github.io/community-group/format/` · Version: 2025.10

DTCG is a *token exchange format*, not a full design node IR. Highly relevant because:
- Figma, Style Dictionary, Tokens Studio are all converging on DTCG
- UNNode's `utils/tokens.py` emits valid DTCG JSON
- `UNVariableBinding` captures the token → node binding for round-trip fidelity

DTCG token types: `color`, `dimension`, `fontFamily`, `fontWeight`, `fontSize`,
`duration`, `cubicBezier`, `number`, `strokeStyle`, `border`, `transition`,
`shadow`, `gradient`, `typography`, `fontStyle`, `textDecoration`, `letterSpacing`,
`lineHeight`, `textCase`

UNNode's token extractor emits: `color`, `typography`, `shadow`, `dimension`.
Remaining types (border, gradient tokens, transition) are Phase 2.

### 4.4 Tokens Studio for Figma

The dominant "tokens in Figma" plugin. Manages DTCG JSON in GitHub/GitLab.
Not an IR — but `UNVariableBinding` is designed to interop with Tokens Studio
token group naming conventions.

---

## 5. Feature Comparison Matrix

| Feature | UNNode | Octopus | pbdl |
|---------|:------:|:-------:|:----:|
| Language | Python | TypeScript | Dart |
| Figma reader | ✅ Full | ✅ Full | ✅ Partial |
| Figma writer (node creation) | ✅ Plugin JS | ❌ | ❌ |
| Paper Design | ✅ | ❌ | ❌ |
| Pencil.dev | ✅ | ❌ | ❌ |
| Sketch support | ❌ | ✅ | ✅ |
| Adobe XD support | ❌ | ✅ | ❌ |
| Auto Layout / Flex | ✅ Full | ✅ Full | ⚠️ |
| Rich text runs | ✅ UNTextRun | ✅ textRanges[] | ❌ |
| Component overrides | ⚠️ Partial | ✅ Full | ⚠️ |
| Design variable bindings | ✅ | ✅ | ❌ |
| DTCG token export | ✅ built-in | ❌ | ❌ |
| Gradient fills | ✅ All 4 types | ✅ | ⚠️ |
| Image fills | ✅ (URL) | ✅ | ⚠️ |
| Shadows + blur | ✅ | ✅ | ✅ |
| SVG path geometry | ✅ | ✅ | ✅ |
| JSON serialisation | ✅ | ✅ | ✅ |
| Factory helpers | ✅ Rich | ⚠️ Minimal | ❌ |
| Open source | ✅ | ✅ | ✅ (archived) |

**Legend**: ✅ Full · ⚠️ Partial · ❌ Not supported

### Key Differentiators

1. **Only IR with Figma write** — as generated Plugin JS (script or bridge mode)
2. **Only IR targeting Paper + Pencil** — unique to DesignDev workflow
3. **Built-in DTCG token extraction** — no other open-source IR includes this
4. **Python-native** — integrates with LLM tooling, data pipelines, MCP servers

---

## 6. Gap Analysis

### 6.1 Critical — Block Round-Trip Fidelity

#### G1 — Component Override Completeness

**Problem**: Figma INSTANCE nodes can have arbitrarily deep property overrides that don't
appear in `componentProperties` (the flat dict currently captured). Deep overrides —
e.g., changing the fill of a nested icon inside a button instance — are invisible to the
current reader and silently dropped on write.

**Fix**: Walk the instance subtree vs. the master subtree, diff differing properties, emit
`node.setProperties(...)` calls in FigmaWriter for each delta.

#### G2 — Mask Nodes

**Problem**: Figma's `isMask: bool` and `maskType: "ALPHA"|"VECTOR"|"LUMINANCE"` are not
in UNNode. Mask layers are read as plain nodes and the mask relationship is lost.

**Fix**: Add `is_mask: bool = False` and `mask_type: str = ""` to UNNode. Map in reader.
Emit `node.isMask = true; node.maskType = "VECTOR"` in FigmaWriter.

#### G3 — Multi-fill Text

**Problem**: `FigmaWriter` applies only the first fill when emitting TEXT nodes. Figma
supports multiple stacked fills on text (e.g., gradient overlay on text).

**Fix**: Emit all fills in `_emit_node_text()`, not just `fills[0]`.

### 6.2 Important — Reduce Fidelity

#### G4 — Stroke Dashes + Line Caps

**Problem**: `UNStroke` is missing `dash_pattern: List[float]`, `line_cap: str`,
`line_join: str`. These are common in icon and data-vis design.

**Fix**: Add fields to `UNStroke`. Map in all three readers/writers.

#### G5 — Blend Mode per Fill

**Problem**: `UNSolidFill` has `opacity` but no `blend_mode`. Per-fill blend modes
(e.g., multiply overlay) are lost in conversion.

**Fix**: Add `blend_mode: BlendMode = BlendMode.NORMAL` to all `UNFill` subclasses.

#### G6 — Export Settings

**Problem**: Figma `exportSettings` (resolution, format, suffix) are not captured.
These are central to handoff workflows.

**Fix**: Add `export_settings: List[UNExportSetting] = field(default_factory=list)`.

### 6.3 Nice-to-Have — Future Phases

- **G7 Interactions/Prototyping**: Figma `reactions[]` for click/hover/drag flows
- **G8 Annotations (Dev Mode)**: Figma 2024+ structured annotations
- **G9 Sections**: `type == "SECTION"` should map to distinct `NodeType.SECTION`
- **G10 Gradient matrix**: Store gradient as both `angle` and affine `transform` for
  lossless Figma ↔ Pencil round-trips

---

## 7. Strategic Recommendations

### Phase 1 — Complete ✅

- ✅ All field name bugs fixed (`node.geometry`, `node.layout`, `node.gap`, `UNSize`)
- ✅ `locked: bool` added to UNNode
- ✅ `UNTextRun` dataclass + `text_runs: List[UNTextRun]`
- ✅ Figma reader `_extract_text_runs()` from `characterStyleOverrides`
- ✅ FigmaWriter `_emit_text_runs()` via `setRange*` Plugin API
- ✅ `utils/tokens.py` — DTCG 2025.10 color + typography + shadow + dimension export
- ✅ `converter.py --export-tokens FILE` CLI flag

### Phase 2 — Next Sprint (Round-Trip Completeness)

**Target**: Fix the three critical gaps + two important gaps.

1. **Mask support** (G2) — 1 day
   - `is_mask: bool`, `mask_type: str` on UNNode → FigmaReader + FigmaWriter

2. **Multi-fill text** (G3) — half day
   - FigmaWriter: emit all fills for TEXT nodes

3. **Stroke dashes + caps** (G4) — 1 day
   - `UNStroke.dash_pattern`, `.line_cap`, `.line_join` → all adapters

4. **Blend mode per fill** (G5) — half day
   - `BlendMode` field on all `UNFill` subclasses

5. **Extended DTCG types** — 1 day
   - Add `border`, `strokeStyle`, `gradient` token types to `utils/tokens.py`

### Phase 3 — Month 2 (Token Ecosystem)

1. **Tokens Studio interop** — read Tokens Studio JSON → `UNVariableBinding` hydration
2. **Style Dictionary output** — emit `utils/tokens.py` in Style Dictionary format alongside DTCG
3. **`--import-tokens FILE`** CLI flag — apply token bindings from DTCG JSON to a UNNode tree
4. **CSS variables export** — `tokens_to_css_vars()` already in `utils/tokens.py`; add CLI flag

### Phase 4 — Month 3 (Component Intelligence)

1. **Deep override diffing** (G1) — instance vs. master subtree diff + override emission
2. **Component library index** — `DesignConverter.list_components()` returns all masters
3. **Auto-instantiation** — when writing, match UNNode names to existing Figma components
   and call `figma.createInstance()` instead of recreating from scratch

### Phase 5 — Ongoing (DX)

1. **UNNode validator** — `validate_node(node)` returns structured warnings
2. **Diff utility** — `diff_nodes(before, after)` structured change list for design review
3. **Markdown renderer** — `node_to_markdown(node)` for spec extraction and LLM context

---

## 8. Technical Implementation Guide

### 8.1 How to Add a New Field to UNNode

1. Add field to `@dataclass UNNode` in `ir/nodes.py`
2. Export from `ir/__init__.py` if it's a new type
3. Map in `adapters/figma/reader.py` → `_figma_node_to_unnode()`
4. Emit in `adapters/figma/writer.py` → appropriate `_emit_*` method
5. Map/emit in Paper and Pencil adapters if the concept exists there
6. Update `un_node_to_dict()` / `un_node_from_dict()` if type is not a primitive
7. Verify: `python3 -c "from converter import DesignConverter"` — no `AttributeError`

### 8.2 How Figma Rich Text Works Internally

Figma stores rich text via two parallel structures:

```json
{
  "characters": "Hello World",
  "characterStyleOverrides": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
  "styleOverrideTable": {
    "1": {
      "fontFamily": "Inter",
      "fontStyle": "Bold",
      "fontSize": 16,
      "fills": [{"type": "SOLID", "color": {"r": 0.8, "g": 0.1, "b": 0.1, "a": 1}}]
    }
  }
}
```

- `characterStyleOverrides[i]` = style index for character `i`. `0` means base style.
- `styleOverrideTable["1"]` = style properties that override the base for index `1`.

`_extract_text_runs()` groups consecutive characters by style index, skips index-0 spans,
and creates one `UNTextRun` per styled span — minimal, clean, diff-friendly.

Writing back: Figma's Plugin API `setRange*` methods take `[start, end)` indices (exclusive
end), same as Python slices. Font must be loaded via `await figma.loadFontAsync()` before
any character or range assignment.

### 8.3 DTCG Token Format (2025.10)

```json
{
  "color": {
    "brand/primary": {
      "$type": "color",
      "$value": "#5B4FFFFF",
      "$description": "Primary brand color (8-digit hex, alpha included)"
    }
  },
  "typography": {
    "heading/h1": {
      "$type": "typography",
      "$value": {
        "fontFamily": "Inter",
        "fontSize": "32px",
        "fontWeight": "700",
        "lineHeight": "40px",
        "letterSpacing": "0px"
      }
    }
  },
  "shadow": {
    "elevation/card": {
      "$type": "shadow",
      "$value": {
        "color": "#00000040",
        "offsetX": "0px",
        "offsetY": "4px",
        "blur": "8px",
        "spread": "0px"
      }
    }
  },
  "dimension": {
    "frame/gap": {
      "$type": "dimension",
      "$value": "16px"
    }
  }
}
```

**Color format**: 8-digit hex `#RRGGBBAA`. Alpha included. Supported in all modern browsers
since 2018 and in the DTCG spec since 2024.

### 8.4 FigmaWriter JS IIFE Structure

```js
// Generated by FigmaWriter — paste into Figma ▶ Plugins ▶ Development ▶ Console
(async () => {
  try {
    // 1. Utility functions
    function hexToRGBA(hex) { /* ... */ }
    function weightToStyle(w) { /* 400→Regular, 700→Bold, ... */ }

    // 2. Font loading (all unique fonts, collected first)
    await figma.loadFontAsync({family: "Inter", style: "Regular"});
    await figma.loadFontAsync({family: "Inter", style: "Bold"});

    // 3. Node creation
    const n0 = figma.createFrame();
    n0.name = "Root";
    n0.resize(800, 600);
    n0.layoutMode = "VERTICAL";
    n0.itemSpacing = 16;
    n0.fills = [{type:'SOLID', color: hexToRGBA("#3366CC")}];

    // 4. Text with rich runs
    const n1 = figma.createText();
    n1.characters = "Hello World";
    n1.setRangeFills([{type:'SOLID',color:{r:0.8,g:0.1,b:0.1}}], 5, 11);
    n1.setRangeFontName({family:"Inter", style:"Bold"}, 5, 11);

    // 5. Tree assembly
    n0.appendChild(n1);
    figma.currentPage.appendChild(n0);

    figma.notify("Created 'Root' (2 nodes)", {timeout: 3000});
  } catch (e) {
    figma.notify("Error: " + e.message, {error: true, timeout: 5000});
    console.error(e);
  }
})();
```

### 8.5 Desktop Bridge WebSocket Protocol

```
FigmaWriter (WebSocket SERVER, port 9224)
    ↕  RFC 6455 WebSocket (pure Python stdlib — no external library)
Desktop Bridge Plugin (WebSocket CLIENT inside Figma sandbox)
```

**Message format**:
```json
// Server → Plugin
{"id": "uuid-v4", "method": "EXECUTE_CODE", "params": {"code": "...", "timeout": 30000}}

// Plugin → Server (success)
{"id": "uuid-v4", "result": {"nodeId": "12:45", "nodeName": "Root"}}

// Plugin → Server (error)
{"id": "uuid-v4", "error": {"message": "Cannot read property 'resize' of null"}}
```

The WebSocket handshake uses only Python stdlib: `socket`, `hashlib`, `base64`, `struct`.
No `websockets` or `aiohttp` dependency required.

### 8.6 Adapter Architecture Pattern

```
adapters/{tool}/
  client.py     # Transport: HTTP, WebSocket, MCP JSON-RPC
  reader.py     # {Tool}Reader(BaseReader): native → UNNode
  writer.py     # {Tool}Writer(BaseWriter): UNNode → native

BaseReader interface:
  connect()    → None
  disconnect() → None
  read_node(node_id) → UNNode
  list_nodes() → List[Dict]
  get_file_info() → Dict

BaseWriter interface:
  connect()    → None
  disconnect() → None
  write_node(node, *, parent_id="", replace_id="") → str
```

`DesignConverter.convert()` always calls `disconnect()` in a `finally` block — preventing
resource leaks (open WebSocket connections, unreleased MCP sessions) even on error.

---

## 9. Appendices

### A. Project File Structure

```
design_converter/
├── ir/
│   ├── __init__.py          # Public exports
│   └── nodes.py             # All dataclasses, enums, factories, serialisation
├── adapters/
│   ├── base.py              # BaseReader, BaseWriter, ToolConnectionError
│   ├── figma/
│   │   ├── client.py        # FigmaClient — REST API + variables endpoint
│   │   ├── reader.py        # FigmaReader — Figma JSON → UNNode
│   │   └── writer.py        # FigmaWriter — UNNode → JS IIFE or bridge
│   ├── paper/
│   │   ├── client.py        # PaperClient — HTTP JSON-RPC MCP (:29979)
│   │   ├── reader.py        # PaperReader — JSX/HTML → UNNode
│   │   └── writer.py        # PaperWriter — UNNode → HTML component
│   └── pencil/
│       ├── client.py        # PencilClient — HTTP REST MCP (:19002)
│       ├── reader.py        # PencilReader — Pencil JSON → UNNode
│       └── writer.py        # PencilWriter — UNNode → Pencil API calls
├── utils/
│   ├── __init__.py          # Re-exports all utilities
│   ├── color.py             # Color conversion (hex, rgb, hsl, Figma, oklab)
│   ├── css.py               # CSS / Tailwind generation from UNNode
│   ├── svg.py               # SVG path parsing and geometry
│   ├── jsx_parser.py        # JSX/React parsing (Paper reader)
│   └── tokens.py            # W3C DTCG token extraction and export ← NEW
├── docs/
│   └── UNNODE_DEEP_DIVE.md  # This document
└── converter.py             # DesignConverter orchestrator + argparse CLI
```

### B. UNNode Quick Field Reference

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `type` | `NodeType` | — | Required |
| `name` | `str` | `"Untitled"` | |
| `figma_id` | `str` | `""` | Preserved from Figma |
| `locked` | `bool` | `False` | |
| `x`, `y` | `float` | `0.0` | Canvas-absolute position |
| `width`, `height` | `UNSize` | `UNSize(100)` | Per-axis value + mode |
| `rotation` | `float` | `0.0` | Degrees CW |
| `corner_radius` | `UNCornerRadius` | zeros | Per-corner |
| `layout` | `LayoutMode` | `NONE` | Flex direction |
| `gap` | `float` | `0.0` | itemSpacing / gap |
| `padding` | `UNPadding` | zeros | top/right/bottom/left |
| `justify_content` | `JustifyContent` | `START` | Main-axis alignment |
| `align_items` | `AlignItems` | `START` | Cross-axis alignment |
| `layout_wrap` | `bool` | `False` | flex-wrap |
| `clip_content` | `bool` | `False` | overflow:hidden |
| `opacity` | `float` | `1.0` | |
| `blend_mode` | `BlendMode` | `NORMAL` | |
| `visible` | `bool` | `True` | |
| `fills` | `List[UNFill]` | `[]` | |
| `strokes` | `List[UNStroke]` | `[]` | |
| `effects` | `List[UNEffect]` | `[]` | |
| `text_content` | `str` | `""` | Full text string |
| `text_style` | `Optional[UNTextStyle]` | `None` | Base typography |
| `text_runs` | `List[UNTextRun]` | `[]` | Per-span overrides |
| `geometry` | `str` | `""` | SVG path data |
| `fill_rule` | `str` | `"nonzero"` | |
| `inner_radius` | `float` | `0.0` | Ellipse donut |
| `start_angle` | `float` | `0.0` | Arc start (degrees) |
| `sweep_angle` | `float` | `360.0` | Arc sweep (degrees) |
| `component_id` | `str` | `""` | Master/instance ID |
| `component_props` | `Dict` | `{}` | Instance overrides |
| `variable_bindings` | `Dict[str,UNVariableBinding]` | `{}` | Token bindings |
| `children` | `List[UNNode]` | `[]` | |

### C. Enum Quick Reference

**NodeType**: `DOCUMENT CANVAS FRAME GROUP COMPONENT INSTANCE RECTANGLE ELLIPSE PATH TEXT IMAGE UNKNOWN`

**LayoutMode**: `NONE HORIZONTAL VERTICAL GRID`

**SizingMode**: `FIXED HUG FILL`

**JustifyContent**: `START CENTER END SPACE_BETWEEN SPACE_AROUND SPACE_EVENLY`

**AlignItems**: `START CENTER END STRETCH BASELINE`

**TextAlign**: `LEFT CENTER RIGHT JUSTIFIED`

**TextTransform**: `NONE UPPERCASE LOWERCASE CAPITALIZE`

**TextAutoResize**: `NONE WIDTH_HEIGHT HEIGHT TRUNCATE`

**GradientType**: `LINEAR RADIAL ANGULAR DIAMOND`

**ImageFillMode**: `FILL FIT TILE CROP`

**StrokeAlign**: `INSIDE CENTER OUTSIDE`

**BlendMode**: `NORMAL MULTIPLY SCREEN OVERLAY DARKEN LIGHTEN DODGE BURN HARD_LIGHT SOFT_LIGHT DIFFERENCE EXCLUSION HUE SATURATION COLOR LUMINOSITY`

### D. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-01 | Phase 1 complete: bugs fixed, UNTextRun, DTCG tokens, this doc |
| 0.9.0 | 2026-02-28 | Initial IR + all adapters (Figma reader/writer, Paper, Pencil) |

---

*UNNODE_DEEP_DIVE.md — DesignDev/design_converter/docs*
