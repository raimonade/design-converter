# Design Converter Architecture Overview

> **Version**: 1.0.0 · **Date**: 2026-03-03 · **Status**: Draft

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Diagram](#2-architecture-diagram)
3. [IR-Based Flow](#3-ir-based-flow)
4. [Connection Modes](#4-connection-modes)
   - [4.1 Script Mode](#41-script-mode)
   - [4.2 Bridge Mode](#42-bridge-mode)
   - [4.3 MCP Mode](#43-mcp-mode)
5. [Workflow Examples](#5-workflow-examples)
6. [Status Matrix](#6-status-matrix)
7. [Known Issues](#7-known-issues)
8. [UNNode IR Reference](#8-unnode-ir-reference)
9. [File Location Index](#9-file-location-index)
10. [Appendices](#10-appendices)

---

## 1. Executive Summary

(Placeholder - to be populated in subsequent subtasks)

---

## 2. Architecture Diagram

### 2.1 High-Level System Architecture

The Design Converter uses a hub-and-spoke architecture with UNNode as the central
Intermediate Representation (IR). This design enables **O(n)** adapter development
rather than **O(n²)** direct tool-to-tool converters.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Design Converter                                    │
│                                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│   │  Figma   │     │  Paper   │     │  Pencil  │     │  Future  │          │
│   │  REST +  │     │   MCP    │     │   MCP    │     │  Tools   │          │
│   │  Plugin  │     │ :29979   │     │ :19002   │     │   ...    │          │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘          │
│        │                │                │                │                 │
│        ▼                ▼                ▼                ▼                 │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │                      Adapters Layer                          │          │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │          │
│   │  │ FigmaReader │  │ PaperReader │  │PencilReader │  ...     │          │
│   │  │ FigmaWriter │  │ PaperWriter │  │PencilWriter │          │          │
│   │  │ FigmaClient │  │ PaperClient │  │PencilClient │          │          │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │          │
│   │         │                │                │                 │          │
│   │         └────────────────┼────────────────┘                 │          │
│   │                          ▼                                  │          │
│   │  ┌───────────────────────────────────────────────────────┐ │          │
│   │  │                    UNNode IR                           │ │          │
│   │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐  │ │          │
│   │  │  │ UNNode  │  │ UNColor │  │UNFill   │  │UNTextStyle│ │ │          │
│   │  │  │ NodeType│  │ UNSize  │  │UNStroke │  │ UNTextRun │ │ │          │
│   │  │  │ Enums   │  │ Layouts │  │UNEffect │  │ Variables │ │ │          │
│   │  │  └─────────┘  └─────────┘  └─────────┘  └──────────┘  │ │          │
│   │  └───────────────────────────────────────────────────────┘ │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                    │                                         │
│   ┌────────────────────────────────┼────────────────────────────────┐      │
│   │                         Utilities                                │      │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │      │
│   │  │ color.py │  │  css.py  │  │  svg.py  │  │  tokens.py   │    │      │
│   │  │ Hex/RGB/ │  │ CSS/Tail │  │  Path    │  │  DTCG export │    │      │
│   │  │ HSL/OKLab│  │  wind    │  │  parsing │  │  W3C 2025.10 │    │      │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                    converter.py (CLI)                            │      │
│   │  DesignConverter · ConvertSpec · ConvertResult · argparse       │      │
│   └─────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Tool Interface** | FigmaClient | REST API + Plugin API bridge WebSocket |
| | PaperClient | MCP JSON-RPC over HTTP SSE at `:29979` |
| | PencilClient | HTTP REST MCP at `:19002` |
| **Reader** | `*Reader` | Native format → UNNode tree transformation |
| **Writer** | `*Writer` | UNNode tree → Native format generation |
| **IR Core** | `UNNode` | Canonical design node representation |
| | `NodeType` | Discriminator for node types (FRAME, TEXT, etc.) |
| | Dataclasses | Color, Fill, Stroke, Effect, TextStyle, etc. |
| **Utilities** | `color.py` | Color space conversions (hex, RGB, HSL, OKLab) |
| | `css.py` | CSS and Tailwind class generation |
| | `svg.py` | SVG path parsing and geometry utilities |
| | `tokens.py` | W3C DTCG 2025.10 design token export |
| **Orchestrator** | `converter.py` | CLI entry point + `DesignConverter` class |

---

## 3. IR-Based Flow

### 3.1 Core Conversion Flow

The IR-based architecture follows a classic compiler pattern: **Source → Reader → IR → Writer → Target**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IR-Based Conversion Flow                              │
└─────────────────────────────────────────────────────────────────────────────┘

  Source Tool                Reader                   IR                    Writer               Target Tool
  ───────────             ──────────              ──────────             ──────────            ───────────

  ┌─────────┐             ┌─────────┐             ┌─────────┐            ┌─────────┐            ┌─────────┐
  │  Figma  │ ──────────▶ │ Figma   │ ──────────▶ │         │ ─────────▶ │ Figma   │ ─────────▶ │  Figma  │
  │  File   │             │ Reader  │             │         │            │ Writer  │            │  Nodes  │
  └─────────┘             └─────────┘             │         │            └─────────┘            └─────────┘
                                                  │
  ┌─────────┐             ┌─────────┐             │  UNNode │            ┌─────────┐            ┌─────────┐
  │  Paper  │ ──────────▶ │ Paper   │ ──────────▶ │   IR    │ ─────────▶ │ Paper   │ ─────────▶ │  Paper  │
  │  Doc    │             │ Reader  │             │   Tree  │            │ Writer  │            │  Comp   │
  └─────────┘             └─────────┘             │         │            └─────────┘            └─────────┘
                                                  │         │
  ┌─────────┐             ┌─────────┐             │         │            ┌─────────┐            ┌─────────┐
  │  Pencil │ ──────────▶ │ Pencil  │ ──────────▶ │         │ ─────────▶ │ Pencil  │ ─────────▶ │  Pencil │
  │  .pen   │             │ Reader  │             │         │            │ Writer  │            │  Design │
  └─────────┘             └─────────┘             └─────────┘            └─────────┘            └─────────┘
```

### 3.2 Reader-to-IR Transformation

Each Reader implements `BaseReader.read_node()` and performs these steps:

1. **Connect** — Establish transport (REST, WebSocket, MCP JSON-RPC)
2. **Fetch** — Retrieve raw node data from source tool
3. **Parse** — Convert native format to intermediate dict
4. **Transform** — Map dict fields to UNNode dataclass
5. **Recurse** — Process children depth-first
6. **Return** — Complete UNNode tree

```python
# Example: FigmaReader transformation
def _figma_node_to_unnode(self, figma_node: dict) -> UNNode:
    node_type = self._map_node_type(figma_node["type"])

    node = UNNode(
        type=node_type,
        name=figma_node.get("name", "Untitled"),
        figma_id=figma_node.get("id", ""),
        x=figma_node.get("absoluteBoundingBox", {}).get("x", 0),
        y=figma_node.get("absoluteBoundingBox", {}).get("y", 0),
        # ... map all fields
    )

    # Recurse for children
    for child in figma_node.get("children", []):
        node.children.append(self._figma_node_to_unnode(child))

    return node
```

### 3.3 IR-to-Writer Transformation

Each Writer implements `BaseWriter.write_node()` and performs these steps:

1. **Connect** — Establish transport (file, WebSocket, MCP)
2. **Emit** — Generate native format from UNNode fields
3. **Recurse** — Process children depth-first
4. **Assemble** — Build final output (JS IIFE, HTML, API calls)
5. **Transmit** — Send to target tool or write to file

```python
# Example: FigmaWriter transformation (script mode)
def write_node(self, node: UNNode, *, parent_id: str = "") -> str:
    js_lines = []

    # Emit node creation
    if node.type == NodeType.FRAME:
        js_lines.append(f"const {var} = figma.createFrame();")
    elif node.type == NodeType.TEXT:
        js_lines.append(f"const {var} = figma.createText();")
    # ...

    # Emit properties
    js_lines.append(f'{var}.name = "{node.name}";')
    js_lines.append(f"{var}.resize({node.width.value}, {node.height.value});")

    # Recurse for children
    for child in node.children:
        js_lines.append(self.write_node(child, parent_id=var))

    return "\n".join(js_lines)
```

### 3.4 Cross-Tool Conversion Examples

| Source | Target | Reader | Writer | Output Format |
|--------|--------|--------|--------|---------------|
| Figma | Paper | `FigmaReader` | `PaperWriter` | HTML component |
| Paper | Figma | `PaperReader` | `FigmaWriter` | JS IIFE (paste into Console) |
| Figma | Pencil | `FigmaReader` | `PencilWriter` | Pencil API calls |
| Pencil | Figma | `PencilReader` | `FigmaWriter` | JS IIFE or WebSocket bridge |
| Figma | Figma | `FigmaReader` | `FigmaWriter` | Round-trip (copy/modify/paste) |

### 3.5 Benefits of IR Architecture

| Benefit | Explanation |
|---------|-------------|
| **O(n) Adapters** | Add a new tool with 1 Reader + 1 Writer, not n converters |
| **Lossy Detection** | IR field gaps reveal missing mappings during development |
| **Serialisation** | `un_node_to_dict()` enables caching, diffing, logging |
| **Validation** | Single point of schema enforcement in IR dataclasses |
| **Testing** | Test Reader → IR → Writer independently per tool |
| **Extensibility** | New fields added to UNNode propagate to all adapters |

---

## 4. Connection Modes

(Placeholder - to be populated in subsequent subtasks)

### 4.1 Script Mode

(Placeholder - to be populated in subsequent subtasks)

### 4.2 Bridge Mode

(Placeholder - to be populated in subsequent subtasks)

### 4.3 MCP Mode

(Placeholder - to be populated in subsequent subtasks)

---

## 5. Workflow Examples

(Placeholder - to be populated in subsequent subtasks)

---

## 6. Status Matrix

(Placeholder - to be populated in subsequent subtasks)

---

## 7. Known Issues

(Placeholder - to be populated in subsequent subtasks)

---

## 8. UNNode IR Reference

(Placeholder - to be populated in subsequent subtasks)

---

## 9. File Location Index

(Placeholder - to be populated in subsequent subtasks)

---

## 10. Appendices

(Placeholder - to be populated in subsequent subtasks)
