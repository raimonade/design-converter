# Architecture

Design Converter moves visual design trees between tools. The current production path is Paper Design → Figma, with a canonical intermediate representation being built around `UNNode`.

## Naming

- **UNNode** — the canonical in-memory design tree node.
- **Reader** — an adapter that reads from a design tool and returns `UNNode`.
- **Writer** — an adapter that accepts `UNNode` and writes to a design tool.
- **Adapter** — a concrete implementation for one design tool.
- **Figma bridge** — local HTTP/WebSocket server used to execute Figma Plugin API JavaScript in Figma Desktop.
- **Legacy direct path** — `paper_to_figma.py` + `ptf/`, which bypasses `UNNode` and emits Figma JavaScript directly.
- **Canonical IR path** — `design_converter/`, where tool adapters meet at the `UNNode` seam.

## Current layout

```text
design_converter/
  ir/                 # UNNode and design primitives
  adapters/
    base.py           # Reader/Writer contracts
    figma/            # Figma REST reader, JS writer, bridge clients/server
    paper/            # Paper MCP reader/writer
  utils/              # CSS, JSX, SVG, color, and token parsing

paper_to_figma.py     # Working legacy direct Paper → Figma CLI
ptf/                  # Legacy direct Paper tree + Figma JS codegen modules
tests/                # Test suite
tools/                # Operational helper scripts
docs/archive/         # Historical/planning docs; not necessarily current
```

## Conversion seams

### Legacy direct path

```text
Paper MCP → ptf.TreeNode → ptf.FigmaCodeGen → Figma bridge → Figma Desktop
```

This path is useful because it works today and is easy to run from the command line. Its drawback is that Paper parsing and Figma writing knowledge are coupled together.

### Canonical IR path

```text
Tool Reader → UNNode → Tool Writer
```

This is the preferred seam for future work. The benefit is locality: parsing details stay in readers, writing details stay in writers, and shared design semantics live in `design_converter/ir/`.

## Near-term direction

1. Keep the legacy direct path working while cleanup continues.
2. Make `UNNode` the default seam for new conversion behavior.
3. Move Paper → Figma conversion from `ptf/` onto `PaperReader → UNNode → FigmaWriter` once the IR path covers the same visual cases.
4. Keep archived planning docs separate from current docs so navigation stays trustworthy.
