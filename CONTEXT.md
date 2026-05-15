# Context

Design Converter is a local tool for moving visual design trees between Paper Design and Figma.

## Domain terms

- **Design tree** — hierarchical visual nodes from a design tool.
- **UNNode** — the repository's canonical intermediate representation for design tree nodes.
- **Reader** — reads a design tree from a tool and converts it into `UNNode`.
- **Writer** — writes a `UNNode` tree into a tool or emits code that does so.
- **Adapter** — a concrete reader/writer implementation for one tool.
- **Figma bridge** — local HTTP/WebSocket process that relays generated Figma Plugin API JavaScript into Figma Desktop.
- **Legacy direct path** — `paper_to_figma.py` plus `ptf/`; fast working Paper → Figma conversion without `UNNode`.
- **Canonical IR path** — `design_converter/`; the long-term path where adapters meet at `UNNode`.

## Current intent

Keep the working Paper → Figma path stable while gradually moving shared conversion behavior behind the `UNNode` seam.
